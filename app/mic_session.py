from __future__ import annotations

import logging
import os
import threading

import numpy as np

try:
    import pyaudio
except ImportError:  # pragma: no cover
    pyaudio = None  # type: ignore

from app.audio_engine import AudioEngineError, RATE, _silence_native_stderr
from app.output_devices import pulse_sink_sample_rate

logger = logging.getLogger(__name__)

CAPTURE_FRAMES = 1024


class MicSession:
    """Hardware input capture with monitor on a separate Pulse sink."""

    def __init__(
        self,
        pa,
        chunk: int,
        latest_mic: np.ndarray,
        mic_lock: threading.Lock,
    ) -> None:
        self._pa = pa
        self._chunk = chunk
        self._latest_mic = latest_mic
        self._mic_lock = mic_lock

        self._input = None
        self._output = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._rate = RATE
        self._channels = 1
        self._monitor_gain = 1.0

        self._mono = np.zeros(chunk, dtype=np.float32)
        self._out_bytes = bytearray(chunk * 2 * 4)
        self._out = np.frombuffer(self._out_bytes, dtype=np.float32).reshape(chunk, 2)

    @property
    def rate(self) -> int:
        return self._rate

    @property
    def monitor_active(self) -> bool:
        return self._output is not None

    def start(
        self,
        input_device_index: int,
        input_channels: int,
        preferred_rate: int,
        output_sink: str | None,
        monitor_gain: float,
    ) -> None:
        self.stop()
        self._monitor_gain = monitor_gain
        self._channels = max(1, min(input_channels, 2))

        rates: list[int] = []
        if output_sink:
            sink_rate = pulse_sink_sample_rate(output_sink)
            if sink_rate:
                rates.append(sink_rate)
        for candidate in (preferred_rate, RATE, 48000, 44100):
            if candidate not in rates:
                rates.append(candidate)

        last_exc: Exception | None = None
        for rate in rates:
            try:
                self._input = self._open_input(input_device_index, rate, self._channels)
                self._rate = rate
                break
            except Exception as exc:
                last_exc = exc
                self._input = None
        else:
            message = "Mikrofon konnte nicht geöffnet werden"
            if last_exc is not None:
                message = f"{message}: {last_exc}"
            raise AudioEngineError(message) from last_exc

        self._output = self._open_monitor_output(self._rate, output_sink)
        if self._output is None:
            logger.error("Monitor-Ausgang konnte nicht geöffnet werden (sink=%s)", output_sink)

        self._stop.clear()
        self._thread = threading.Thread(target=self._capture_loop, name="mic-session", daemon=True)
        self._thread.start()
        logger.info(
            "Mic session: input=%d rate=%d ch=%d monitor=%s sink=%s",
            input_device_index,
            self._rate,
            self._channels,
            self._output is not None,
            output_sink or "default",
        )

    def _open_input(self, device_index: int, rate: int, channels: int):
        if pyaudio is None:
            raise AudioEngineError("PyAudio ist nicht installiert.")
        with _silence_native_stderr():
            return self._pa.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CAPTURE_FRAMES,
            )

    def _open_monitor_output(self, rate: int, output_sink: str | None):
        if pyaudio is None:
            return None

        sink_candidates: list[str | None] = []
        if output_sink:
            sink_candidates.append(output_sink)
        sink_candidates.append(None)

        for sink in sink_candidates:
            old_sink = os.environ.get("PULSE_SINK")
            if sink:
                os.environ["PULSE_SINK"] = sink
            try:
                with _silence_native_stderr():
                    stream = self._pa.open(
                        format=pyaudio.paFloat32,
                        channels=2,
                        rate=rate,
                        output=True,
                        frames_per_buffer=CAPTURE_FRAMES,
                    )
                logger.info("Monitor output opened: rate=%d sink=%s", rate, sink or "system default")
                return stream
            except Exception as exc:
                logger.warning("Monitor open failed (rate=%d sink=%s): %s", rate, sink, exc)
            finally:
                if old_sink is not None:
                    os.environ["PULSE_SINK"] = old_sink
                elif sink:
                    os.environ.pop("PULSE_SINK", None)

        return None

    def _capture_loop(self) -> None:
        input_stream = self._input
        output_stream = self._output
        if input_stream is None:
            return

        chunk = self._chunk
        channels = self._channels
        gain = self._monitor_gain
        mono = self._mono
        out = self._out
        out_pcm = self._out_bytes
        latest = self._latest_mic
        mic_lock = self._mic_lock

        pending = np.zeros(0, dtype=np.float32)

        try:
            while not self._stop.is_set():
                raw = input_stream.read(CAPTURE_FRAMES, exception_on_overflow=False)
                frame_count = len(raw) // (channels * 4)
                if frame_count <= 0:
                    continue

                samples = np.frombuffer(raw, dtype=np.float32, count=frame_count * channels)
                if channels == 2:
                    stereo = samples.reshape(frame_count, 2)
                    np.mean(stereo, axis=1, out=mono[:frame_count])
                else:
                    mono[:frame_count] = samples[:frame_count]

                if frame_count < chunk:
                    pending = np.concatenate([pending, mono[:frame_count]])
                else:
                    pending = mono[:frame_count]

                while pending.size >= chunk:
                    block = pending[:chunk]
                    pending = pending[chunk:]

                    with mic_lock:
                        np.copyto(latest, block)

                    if output_stream is not None:
                        if gain != 1.0:
                            np.multiply(block, gain, out=out[:, 0])
                        else:
                            out[:, 0] = block
                        out[:, 1] = out[:, 0]
                        np.clip(out, -0.98, 0.98, out=out)
                        output_stream.write(
                            bytes(out_pcm[: chunk * 2 * 4]),
                            exception_on_underflow=False,
                        )
        except Exception:
            if not self._stop.is_set():
                logger.exception("Mic session loop failed")
        finally:
            for stream in (input_stream, output_stream):
                if stream is None:
                    continue
                try:
                    if stream.is_active():
                        stream.stop_stream()
                    stream.close()
                except Exception:
                    logger.debug("Mic stream close failed", exc_info=True)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._input = None
        self._output = None
