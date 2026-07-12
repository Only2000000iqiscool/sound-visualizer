from __future__ import annotations

import math

from PyQt6.QtGui import QColor


def hsl(h: float, s: float, l: float, a: float = 1.0) -> QColor:
    c = QColor()
    c.setHslF((h % 360) / 360.0, s / 100.0, l / 100.0, a)
    return c


def band_energy(smooth_freq, start_ratio: float, end_ratio: float) -> float:
    length = len(smooth_freq)
    i0 = int(start_ratio * length)
    i1 = int(end_ratio * length)
    if i1 <= i0:
        return 0.0
    return float(smooth_freq[i0:i1].mean() / 255.0)


def bass(smooth_freq) -> float:
    return band_energy(smooth_freq, 0.0, 0.08)


def mid(smooth_freq) -> float:
    return band_energy(smooth_freq, 0.08, 0.45)


def treble(smooth_freq) -> float:
    return band_energy(smooth_freq, 0.45, 1.0)


def avg_level(smooth_freq) -> float:
    return float(smooth_freq.mean() / 255.0)


def tau(t: float) -> float:
    return t * 0.001
