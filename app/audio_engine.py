from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
import pyaudio

CHUNK = 2048
RATE = 44100


def decode_file(path: str | Path) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sw = wf.getsampwidth()
            if sw == 2:
                data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sw == 4:
                data = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sw}")
            if wf.getnchannels() > 1:
                data = data.reshape(-1, wf.getnchannels()).mean(axis=1)
            if wf.getframerate() != RATE:
                ratio = wf.getframerate() / RATE
                idx = (np.arange(int(len(data) / ratio)) * ratio).astype(np.int64)
                data = data[np.clip(idx, 0, len(data) - 1)]
            return data

    proc = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            str(RATE),
            "-v",
            "quiet",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


class AudioEngine:
    def __init__(self) -> None:
        self.chunk = CHUNK
        self.rate = RATE
        self.mode = "idle"
        self.running = False

        self.gain = 1.4
        self.smoothing = 0.75

        self.freq = np.zeros(CHUNK // 2, dtype=np.float32)
        self.time = np.zeros(CHUNK, dtype=np.float32)
        self.smooth_freq = np.zeros(CHUNK // 2, dtype=np.float32)
        self.smooth_time = np.zeros(CHUNK, dtype=np.float32)

        self._pa: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._file_samples: np.ndarray | None = None
        self._position_ms: callable[[], int] | None = None

    def _ensure_pa(self) -> pyaudio.PyAudio:
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        return self._pa

    def _close_stream(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def stop(self) -> None:
        self._close_stream()
        self._file_samples = None
        self._position_ms = None
        self.running = False
        self.mode = "idle"

    def shutdown(self) -> None:
        self.stop()
        if self._pa is not None:
            self._pa.terminate()
            self._pa = None

    def start_mic(self) -> None:
        self.stop()
        pa = self._ensure_pa()
        self._stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
        )
        self.mode = "mic"
        self.running = True

    def start_file(self, path: str | Path, position_ms: callable[[], int]) -> None:
        self.stop()
        self._file_samples = decode_file(path)
        self._position_ms = position_ms
        self.mode = "file"
        self.running = True

    def _read_chunk(self) -> np.ndarray:
        if self.mode == "mic":
            assert self._stream is not None
            raw = self._stream.read(self.chunk, exception_on_overflow=False)
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return data

        assert self._file_samples is not None and self._position_ms is not None
        pos = max(0, self._position_ms())
        start = int((pos / 1000.0) * self.rate)
        end = start + self.chunk
        chunk = self._file_samples[start:end]
        if len(chunk) < self.chunk:
            pad = np.zeros(self.chunk - len(chunk), dtype=np.float32)
            chunk = np.concatenate([chunk, pad])
        return chunk

    def sample(self, smooth_alpha: float | None = None) -> dict | None:
        if not self.running:
            return None

        alpha = self.smoothing if smooth_alpha is None else smooth_alpha
        inv = 1.0 - alpha

        data = self._read_chunk() * self.gain
        self.time = ((data + 1.0) * 0.5 * 255.0).clip(0, 255)

        spectrum = np.abs(np.fft.rfft(data * np.hanning(len(data))))
        if spectrum.max() > 0:
            spectrum = spectrum / spectrum.max() * 255.0
        self.freq = spectrum.astype(np.float32)

        self.smooth_freq += (self.freq - self.smooth_freq) * inv
        self.smooth_time += (self.time - self.smooth_time) * inv

        level = float(np.mean(self.freq[::8]) / 255.0)

        return {
            "freq": self.freq,
            "time": self.time,
            "smooth_freq": self.smooth_freq,
            "smooth_time": self.smooth_time,
            "level": level,
            "bin_count": len(self.freq),
            "fft_size": self.chunk,
        }
