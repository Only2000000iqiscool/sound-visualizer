from __future__ import annotations

from contextlib import contextmanager
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path
from typing import Callable

import numpy as np

try:
    import pyaudio
except ImportError:  # pragma: no cover
    pyaudio = None  # type: ignore

from app.output_devices import list_input_devices, resolve_default_input_device, resolve_input_device
from app.pyaudio_shared import get_pyaudio, terminate_pyaudio

logger = logging.getLogger(__name__)

CHUNK = 2048
RATE = 44100
FREQ_BINS = CHUNK // 2 + 1


class AudioEngineError(Exception):
    pass


@contextmanager
def _silence_native_stderr():
    """Silence noisy ALSA/JACK device probing while preserving exceptions."""
    if not sys.platform.startswith("linux"):
        yield
        return

    saved_stderr = os.dup(2)
    try:
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), 2)
            yield
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)


def _ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise AudioEngineError(
            "ffmpeg wurde nicht gefunden. Installiere ffmpeg (Linux: pacman -S ffmpeg, Windows: ffmpeg.org)."
        )
    return path


ProgressCallback = Callable[[int, int, int], None]


def _probe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError:
        return 0.0


def decode_file(
    path: str | Path,
    progress_callback: ProgressCallback | None = None,
) -> np.ndarray:
    path = Path(path)
    if not path.is_file():
        raise AudioEngineError(f"Datei nicht gefunden: {path}")

    if path.suffix.lower() == ".wav":
        data = _decode_wav(path)
        if progress_callback:
            progress_callback(100, data.nbytes, data.nbytes)
        return data

    ffmpeg = _ffmpeg_path()
    duration = _probe_duration(path)
    total_bytes = max(1, int(duration * RATE * 4))
    if progress_callback:
        progress_callback(0, 0, total_bytes)
    output_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            prefix="sound-visualizer-",
            suffix=".pcm",
            delete=False,
        ) as output:
            output_path = output.name

        command = [
            ffmpeg,
            "-y",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            str(RATE),
            "-stats_period",
            "0.1",
            "-progress",
            "pipe:1",
            output_path,
        ]
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        assert proc.stdout is not None
        last_percent = -1
        for line in proc.stdout:
            key, separator, value = line.strip().partition("=")
            if not separator:
                continue
            if key in ("out_time_us", "out_time_ms") and duration > 0:
                # Current FFmpeg versions report both values in microseconds.
                seconds = int(value or 0) / 1_000_000
                percent = min(99, max(0, int(seconds / duration * 100)))
                if percent != last_percent:
                    done = min(total_bytes, int(seconds * RATE * 4))
                    if progress_callback:
                        progress_callback(percent, done, total_bytes)
                    last_percent = percent

        return_code = proc.wait()
        stderr = proc.stderr.read().strip() if proc.stderr else ""
        if return_code != 0:
            raise AudioEngineError(stderr or f"ffmpeg konnte {path.name} nicht dekodieren")

        data = np.fromfile(output_path, dtype=np.float32)
        if data.size == 0:
            raise AudioEngineError(f"Keine Audiodaten in {path.name}")
        if progress_callback:
            progress_callback(100, data.nbytes, max(total_bytes, data.nbytes))
        return data
    finally:
        if output_path:
            try:
                Path(output_path).unlink(missing_ok=True)
            except OSError:
                logger.debug("Temporary PCM cleanup failed", exc_info=True)


def _decode_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        sw = wf.getsampwidth()
        if sw == 2:
            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sw == 4:
            data = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise AudioEngineError(f"Nicht unterstütztes WAV-Format (sample width {sw})")
        if wf.getnchannels() > 1:
            data = data.reshape(-1, wf.getnchannels()).mean(axis=1)
        if wf.getframerate() != RATE:
            ratio = wf.getframerate() / RATE
            idx = (np.arange(int(len(data) / ratio)) * ratio).astype(np.int64)
            data = data[np.clip(idx, 0, len(data) - 1)]
        if data.size == 0:
            raise AudioEngineError(f"Leere WAV-Datei: {path.name}")
        return data


class AudioEngine:
    def __init__(self) -> None:
        self.chunk = CHUNK
        self.rate = RATE
        self.mode = "idle"
        self.running = False

        self.gain = 1.4
        self.smoothing = 0.75

        self.freq = np.zeros(FREQ_BINS, dtype=np.float32)
        self.time = np.zeros(CHUNK, dtype=np.float32)
        self.smooth_freq = np.zeros(FREQ_BINS, dtype=np.float32)
        self.smooth_time = np.zeros(CHUNK, dtype=np.float32)

        self._pa = None
        self._mic_session = None
        self._mic_lock = threading.Lock()
        self._latest_mic = np.zeros(CHUNK, dtype=np.float32)
        self._capture_channels = 1
        self._file_samples: np.ndarray | None = None
        self._position_ms: callable[[], int] | None = None

    def _ensure_pa(self):
        if pyaudio is None:
            raise AudioEngineError("PyAudio ist nicht installiert.")
        self._pa = get_pyaudio()
        return self._pa

    def _close_stream(self) -> None:
        if self._mic_session is not None:
            self._mic_session.stop()
            self._mic_session = None

    def list_input_devices(self) -> list[dict]:
        pa = self._ensure_pa()
        with _silence_native_stderr():
            return list_input_devices(pa)

    def stop(self) -> None:
        self._close_stream()
        self._file_samples = None
        self._position_ms = None
        self.running = False
        self.mode = "idle"

    def shutdown(self) -> None:
        self.stop()
        self._pa = None
        terminate_pyaudio()

    def start_mic(
        self,
        device: dict | None = None,
        device_index: int | None = None,
        *,
        output_sink: str | None = None,
        monitor_gain: float = 1.0,
    ) -> None:
        self.stop()
        pa = self._ensure_pa()

        if device is not None:
            device = resolve_input_device(pa, device)

        capture_rate = RATE
        capture_channels = 1

        if device is not None:
            capture_rate = int(device.get("sample_rate", RATE))
            capture_channels = max(1, min(int(device.get("channels", 1)), 2))
            backend = device.get("backend", "pyaudio")
            if backend == "default":
                resolved = resolve_default_input_device(pa)
                if resolved is None:
                    raise AudioEngineError("Kein Mikrofon-Gerät gefunden.")
                device = resolved
                device_index = int(resolved["pa_index"])
            elif backend == "pyaudio":
                device_index = int(device.get("pa_index", device.get("index", -1)))
            else:
                device_index = int(device.get("pa_index", device.get("index", -1)))

        if device_index is None:
            try:
                device_info = pa.get_default_input_device_info()
                device_index = int(device_info["index"])
            except Exception as exc:
                raise AudioEngineError("Kein Standard-Mikrofon gefunden.") from exc
        else:
            try:
                device_info = pa.get_device_info_by_index(device_index)
            except Exception as exc:
                raise AudioEngineError(f"Ungültiges Mikrofon: {device_index}") from exc

        if int(device_info.get("maxInputChannels", 0)) < 1:
            raise AudioEngineError("Das gewählte Gerät besitzt keinen Audio-Eingang")

        capture_rate = int(device_info.get("defaultSampleRate", capture_rate))
        max_channels = int(device_info.get("maxInputChannels", capture_channels))
        capture_channels = max(1, min(capture_channels, max_channels, 2))

        self._capture_channels = capture_channels
        self._latest_mic.fill(0)

        from app.mic_session import MicSession

        self._mic_session = MicSession(pa, self.chunk, self._latest_mic, self._mic_lock)
        self._mic_session.start(
            input_device_index=device_index,
            input_channels=capture_channels,
            preferred_rate=capture_rate,
            output_sink=output_sink,
            monitor_gain=monitor_gain,
        )

        self.rate = self._mic_session.rate
        self.mode = "mic"
        self.running = True
        logger.info(
            "Microphone started: index=%d rate=%d channels=%d sink=%s monitor=%s",
            device_index,
            self.rate,
            capture_channels,
            output_sink or "default",
            self._mic_session.monitor_active if self._mic_session else False,
        )

    def mic_monitor_active(self) -> bool:
        return self._mic_session is not None and self._mic_session.monitor_active

    def set_file_samples(self, samples: np.ndarray, position_ms: callable[[], int]) -> None:
        self.stop()
        if samples.size == 0:
            raise AudioEngineError("Audiodatei enthält keine Samples")
        self.rate = RATE
        self._file_samples = np.asarray(samples, dtype=np.float32)
        self._position_ms = position_ms
        self.mode = "file"
        self.running = True

    def _read_chunk(self) -> np.ndarray:
        if self.mode == "mic":
            with self._mic_lock:
                return self._latest_mic.copy()

        assert self._file_samples is not None and self._position_ms is not None
        start = max(0, int(self._position_ms() / 1000.0 * self.rate))
        end = start + self.chunk
        chunk = self._file_samples[start:end]
        if chunk.size < self.chunk:
            pad = np.zeros(self.chunk - chunk.size, dtype=np.float32)
            chunk = np.concatenate([chunk, pad])
        return chunk

    def sample(self, smooth_alpha: float | None = None) -> dict | None:
        if not self.running:
            return None

        try:
            alpha = self.smoothing if smooth_alpha is None else smooth_alpha
            inv = 1.0 - alpha

            data = self._read_chunk() * self.gain
            self.time = ((data + 1.0) * 0.5 * 255.0).clip(0, 255)

            windowed = data * np.hanning(len(data))
            spectrum = np.abs(np.fft.rfft(windowed, n=self.chunk))
            peak = float(spectrum.max())
            if peak > 0:
                spectrum = spectrum / peak * 255.0
            self.freq = spectrum.astype(np.float32)

            self.smooth_freq += (self.freq - self.smooth_freq) * inv
            self.smooth_time += (self.time - self.smooth_time) * inv

            level = float(np.mean(self.freq[::8]) / 255.0) if self.freq.size else 0.0

            return {
                "freq": self.freq,
                "time": self.time,
                "smooth_freq": self.smooth_freq,
                "smooth_time": self.smooth_time,
                "level": level,
                "bin_count": len(self.freq),
                "fft_size": self.chunk,
            }
        except AudioEngineError:
            raise
        except Exception as exc:
            logger.warning("Audio sample failed: %s", exc)
            return None
