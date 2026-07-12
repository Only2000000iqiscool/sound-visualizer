from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


def configure_runtime() -> None:
    """Reduce noisy Qt/PulseAudio logs."""
    os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false;qt.qpa.*=false")
    if sys.platform.startswith("linux"):
        os.environ.setdefault("PULSE_LOG", "0")

    def _qt_handler(mode, _context, message):
        if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtInfoMsg):
            text = message
            if any(
                s in text
                for s in (
                    "VDPAU",
                    "spaVisitChoice",
                    "grabbing the mouse",
                    "ALSA lib",
                    "jack server",
                    "Unknown PCM",
                )
            ):
                return
        if mode == QtMsgType.QtCriticalMsg:
            logger.warning("Qt: %s", message)
        elif mode == QtMsgType.QtFatalMsg:
            logger.critical("Qt fatal: %s", message)

    qInstallMessageHandler(_qt_handler)


def hsl(h: float, s: float, l: float, a: float = 1.0) -> QColor:
    c = QColor()
    c.setHslF(
        (h % 360) / 360.0,
        max(0.0, min(1.0, s / 100.0)),
        max(0.0, min(1.0, l / 100.0)),
        max(0.0, min(1.0, a)),
    )
    return c


def viz_hsl(state: dict, h: float, s: float, l: float, a: float = 1.0) -> QColor:
    """Apply user hue shift; saturation overrides the per-call value when set."""
    shift = float(state.get("hue_shift", 0))
    if "saturation" in state:
        s = float(state["saturation"])
    return hsl((h + shift) % 360, s, l, a)


def bin_at(arr, ratio: float) -> int:
    """Map ratio in [0, 1] to a safe array index."""
    length = len(arr)
    if length == 0:
        return 0
    ratio = max(0.0, min(1.0, float(ratio)))
    return min(int(ratio * (length - 1)), length - 1)


def val_at(arr, ratio: float) -> float:
    return float(arr[bin_at(arr, ratio)])


def band_energy(smooth_freq, start_ratio: float, end_ratio: float) -> float:
    length = len(smooth_freq)
    if length == 0:
        return 0.0
    i0 = bin_at(smooth_freq, start_ratio)
    i1 = max(i0 + 1, min(int(end_ratio * length), length))
    return float(smooth_freq[i0:i1].mean() / 255.0)


def bass(smooth_freq) -> float:
    return band_energy(smooth_freq, 0.0, 0.08)


def mid(smooth_freq) -> float:
    return band_energy(smooth_freq, 0.08, 0.45)


def treble(smooth_freq) -> float:
    return band_energy(smooth_freq, 0.45, 1.0)


def avg_level(smooth_freq) -> float:
    if len(smooth_freq) == 0:
        return 0.0
    return float(smooth_freq.mean() / 255.0)
