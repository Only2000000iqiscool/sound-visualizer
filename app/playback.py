from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QObject

try:
    import pyaudio
except ImportError:  # pragma: no cover
    pyaudio = None  # type: ignore

from app.audio_engine import AudioEngineError, RATE, _silence_native_stderr
from app.output_devices import list_output_devices
from app.pyaudio_shared import get_pyaudio, terminate_pyaudio

logger = logging.getLogger(__name__)

OUTPUT_CHANNELS = 2
CHUNK_FRAMES = 2048


@dataclass
class PreparedAudio:
    samples: np.ndarray
    pcm_bytes: bytes


def expand_to_channels(data: np.ndarray, channels: int) -> np.ndarray:
    mono = np.asarray(data, dtype=np.float32).reshape(-1)
    if channels <= 1:
        return mono
    return np.repeat(mono[:, None], channels, axis=1).reshape(-1)


def samples_to_pcm_bytes(data: np.ndarray, sample_format_name: str) -> bytes:
    if sample_format_name == "Float":
        return np.asarray(data, dtype=np.float32).tobytes()
    if sample_format_name == "Int16":
        return (np.asarray(data, dtype=np.float32) * 32767.0).astype(np.int16).tobytes()
    if sample_format_name == "Int32":
        return (
            np.asarray(data, dtype=np.float64) * 2147483647.0
        ).astype(np.int32).tobytes()
    if sample_format_name == "UInt8":
        return ((np.asarray(data, dtype=np.float32) + 1.0) * 127.5).astype(np.uint8).tobytes()
    return np.asarray(data, dtype=np.float32).tobytes()


def prepare_pcm(samples: np.ndarray, spec: dict) -> PreparedAudio:
    """Prepare PCM bytes in a worker thread (no Qt objects here)."""
    output = np.asarray(samples, dtype=np.float32)
    target_rate = int(spec["sample_rate"])
    if target_rate != RATE:
        output_length = max(1, round(len(output) * target_rate / RATE))
        source_x = np.arange(len(output), dtype=np.float64)
        target_x = np.linspace(0, max(0, len(output) - 1), output_length)
        output = np.interp(target_x, source_x, output).astype(np.float32)

    channels = max(1, int(spec["channels"]))
    output = expand_to_channels(output, channels)

    sample_format = spec["sample_format"]
    if sample_format not in {"Float", "Int16", "Int32", "UInt8"}:
        raise AudioEngineError(f"Nicht unterstütztes Ausgabeformat: {sample_format}")

    return PreparedAudio(
        samples=samples,
        pcm_bytes=samples_to_pcm_bytes(output, sample_format),
    )


class AudioPlayback(QObject):
    """Stable PCM playback via PyAudio (avoids Qt/PipeWire crashes on Linux)."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pa = None
        self._output_device_index: int | None = None
        self._output_sink_name: str | None = None
        self._output_display_name = "Systemstandard"
        self._output_stream = None
        self._play_thread: threading.Thread | None = None
        self._play_stop = threading.Event()
        self._play_paused = threading.Event()
        self._play_position_frames = 0
        self._prepared_pcm: bytes | None = None
        self._lock = threading.Lock()

    def _ensure_pa(self):
        if pyaudio is None:
            raise AudioEngineError("PyAudio ist nicht installiert.")
        self._pa = get_pyaudio()
        return self._pa

    def list_output_devices(self) -> list[dict]:
        pa = self._ensure_pa()
        with _silence_native_stderr():
            return list_output_devices(pa)

    def initialize(self) -> None:
        """Warm up the shared PyAudio instance on the main thread."""
        try:
            pa = self._ensure_pa()
            name = pa.get_default_output_device_info().get("name", "Standard")
            logger.info("PyAudio ready, default output: %s", name)
        except Exception as exc:
            logger.warning("PyAudio warmup failed: %s", exc)

    def set_output_device(self, device: dict | None) -> None:
        self.stop()

        if device is None:
            self._output_sink_name = None
            self._output_device_index = None
            self._output_display_name = "Systemstandard"
        elif device.get("backend") == "pulse":
            self._output_sink_name = device.get("pulse_name") or device.get("id")
            self._output_device_index = None
            self._output_display_name = device.get("display_name", self._output_sink_name)
        else:
            self._output_sink_name = None
            self._output_device_index = int(device.get("pa_index", device.get("id", -1)))
            self._output_display_name = device.get("display_name", "Audio-Ausgang")

        logger.info(
            "Audio output set to: %s",
            device.get("display_name") if device else "Systemstandard",
        )

    def output_sink_name(self) -> str | None:
        return self._output_sink_name

    def current_device_name(self) -> str:
        return self._output_display_name

    def current_device_id(self) -> str | int | None:
        if self._output_sink_name:
            return self._output_sink_name
        return self._output_device_index

    def format_spec(self) -> dict:
        return {
            "sample_rate": RATE,
            "channels": OUTPUT_CHANNELS,
            "sample_format": "Float",
        }

    def _open_output_stream(
        self,
        rate: int,
        channels: int = OUTPUT_CHANNELS,
        sample_format=pyaudio.paFloat32,
        frames_per_buffer: int = CHUNK_FRAMES,
    ):
        pa = self._ensure_pa()
        kwargs: dict = {
            "format": sample_format,
            "channels": channels,
            "rate": rate,
            "output": True,
            "frames_per_buffer": frames_per_buffer,
        }
        if self._output_device_index is not None:
            kwargs["output_device_index"] = self._output_device_index

        old_sink = os.environ.get("PULSE_SINK")
        if self._output_sink_name:
            os.environ["PULSE_SINK"] = self._output_sink_name
        elif old_sink is not None:
            os.environ.pop("PULSE_SINK", None)

        try:
            with _silence_native_stderr():
                return pa.open(**kwargs)
        finally:
            if old_sink is not None:
                os.environ["PULSE_SINK"] = old_sink
            elif self._output_sink_name:
                os.environ.pop("PULSE_SINK", None)

    def play_prepared(self, prepared: PreparedAudio) -> None:
        self.stop()
        if prepared.samples.size == 0:
            raise AudioEngineError("Audiodatei enthält keine Samples")

        self._prepared_pcm = prepared.pcm_bytes
        self._play_stop.clear()
        self._play_paused.clear()
        self._play_position_frames = 0

        logger.info(
            "Starting playback on '%s': %d samples, %d PCM bytes",
            self.current_device_name(),
            prepared.samples.size,
            len(prepared.pcm_bytes),
        )

        self._play_thread = threading.Thread(
            target=self._playback_loop,
            name="file-playback",
            daemon=True,
        )
        self._play_thread.start()

    def _playback_loop(self) -> None:
        if not self._prepared_pcm:
            return

        frame_bytes = OUTPUT_CHANNELS * 4
        chunk_bytes = CHUNK_FRAMES * frame_bytes

        try:
            stream = self._open_output_stream(RATE)
            with self._lock:
                self._output_stream = stream

            offset = 0
            pcm = self._prepared_pcm
            while not self._play_stop.is_set() and offset < len(pcm):
                if self._play_paused.is_set():
                    time.sleep(0.01)
                    continue

                end = min(offset + chunk_bytes, len(pcm))
                chunk = pcm[offset:end]
                if len(chunk) < chunk_bytes:
                    chunk += b"\x00" * (chunk_bytes - len(chunk))

                stream.write(chunk)
                offset = end
                self._play_position_frames = offset // frame_bytes
        except Exception:
            logger.exception("Playback thread failed")
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                logger.debug("Stream close failed", exc_info=True)
            with self._lock:
                if self._output_stream is stream:
                    self._output_stream = None

    def stop(self) -> None:
        self._play_stop.set()
        if self._play_thread is not None:
            self._play_thread.join(timeout=2.0)
            self._play_thread = None
        with self._lock:
            stream = self._output_stream
            self._output_stream = None
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                logger.debug("Output stream close failed", exc_info=True)
        self._prepared_pcm = None
        self._play_paused.clear()

    def toggle_pause(self) -> bool:
        if self._play_thread is None or not self._play_thread.is_alive():
            return False
        if self._play_paused.is_set():
            self._play_paused.clear()
            return False
        self._play_paused.set()
        return True

    def position_ms(self) -> int:
        return max(0, int(self._play_position_frames / RATE * 1000))

    @property
    def playing(self) -> bool:
        return (
            self._play_thread is not None
            and self._play_thread.is_alive()
            and not self._play_stop.is_set()
        )

    def shutdown(self) -> None:
        self.stop()
        self._pa = None