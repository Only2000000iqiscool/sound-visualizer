from __future__ import annotations

import math

import numpy as np

CHUNK = 2048
FREQ_BINS = CHUNK // 2 + 1


class DemoSampleGenerator:
    """Synthetic audio for live visualizer preview when no source is active."""

    def __init__(self, chunk: int = CHUNK) -> None:
        self.chunk = chunk
        self._smooth_freq = np.zeros(FREQ_BINS, dtype=np.float32)
        self._smooth_time = np.zeros(chunk, dtype=np.float32)

    def sample(self, t_ms: float, gain: float = 1.4, smoothing: float = 0.75) -> dict:
        t = t_ms / 1000.0
        inv = 1.0 - smoothing
        n = np.arange(self.chunk, dtype=np.float32)

        wave = (
            0.55 * np.sin(2 * math.pi * 2.5 * n / self.chunk + t * 5.0)
            + 0.35 * np.sin(2 * math.pi * 5.0 * n / self.chunk + t * 3.2)
            + 0.2 * np.sin(2 * math.pi * 11.0 * n / self.chunk + t * 7.5)
        ).astype(np.float32)
        wave *= 0.65 + 0.35 * math.sin(t * 1.8)
        wave = (wave * gain).clip(-1.0, 1.0)

        time = ((wave + 1.0) * 0.5 * 255.0).clip(0, 255)
        windowed = wave * np.hanning(len(wave))
        spectrum = np.abs(np.fft.rfft(windowed, n=self.chunk))
        peak = float(spectrum.max()) or 1.0
        spectrum = spectrum / peak * 255.0
        freq = spectrum.astype(np.float32)

        self._smooth_freq += (freq - self._smooth_freq) * inv
        self._smooth_time += (time - self._smooth_time) * inv

        level = float(np.mean(freq[::8]) / 255.0) if freq.size else 0.0

        return {
            "freq": freq,
            "time": time.astype(np.float32),
            "smooth_freq": self._smooth_freq,
            "smooth_time": self._smooth_time,
            "level": level,
            "bin_count": len(freq),
            "fft_size": self.chunk,
        }
