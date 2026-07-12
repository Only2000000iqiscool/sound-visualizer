from __future__ import annotations

import logging
import math
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QColor,
    QFont,
    QPainter,
    QPen,
    QRadialGradient,
)

from app.audio_engine import AudioEngine, AudioEngineError
from app.visualizers import VISUALIZERS

logger = logging.getLogger(__name__)


from PyQt6.QtWidgets import QWidget


class VisualizerCanvas(QWidget):
    def __init__(self, audio: AudioEngine, parent=None) -> None:
        super().__init__(parent)
        self.audio = audio
        self.viz_index = 0
        self.state: dict = {"particle_count": 1800, "hue_shift": 0.0, "saturation": 85.0}
        self._last_ms = 0.0
        self._last_level = 0.0
        self._last_sample_ms = 0.0
        self._cached_sample: dict | None = None
        self._auto_cycle = False
        self._auto_timer = 0.0
        self._drag_active = False
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAutoFillBackground(False)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        window = self.window()
        if window and hasattr(window, "_drag_has_audio") and window._drag_has_audio(event):  # type: ignore[attr-defined]
            self._drag_active = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drag_active = False
        self.update()
        window = self.window()
        if window and hasattr(window, "_first_audio_from_drop"):
            path = window._first_audio_from_drop(event)  # type: ignore[attr-defined]
            if path:
                logger.info("Canvas drop accepted, scheduling load: %s", path)
                event.acceptProposedAction()
                QTimer.singleShot(0, lambda p=path: window.load_audio_file(p))  # type: ignore[attr-defined]
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drag_active = False
        self.update()
        event.accept()

    def set_viz_index(self, index: int) -> None:
        self.viz_index = index % len(VISUALIZERS)
        self._reset_viz_state()

    def next_viz(self, direction: int = 1) -> str:
        self.set_viz_index(self.viz_index + direction)
        return VISUALIZERS[self.viz_index]["name"]

    def set_auto_cycle(self, enabled: bool) -> None:
        self._auto_cycle = enabled
        self._auto_timer = 0.0

    def set_particle_count(self, count: int) -> None:
        self.state["particle_count"] = count
        self.state.pop("particles", None)
        self.state.pop("particles_count", None)

    def set_color_settings(self, hue_shift: float, saturation: float) -> None:
        self.state["hue_shift"] = hue_shift
        self.state["saturation"] = saturation

    def _reset_viz_state(self) -> None:
        keep = {
            "particle_count": self.state.get("particle_count", 1800),
            "hue_shift": self.state.get("hue_shift", 0.0),
            "saturation": self.state.get("saturation", 85.0),
        }
        self.state = keep

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, now - self._last_ms) if self._last_ms else 0.016
        self._last_ms = now

        if self._auto_cycle:
            self._auto_timer += dt
            if self._auto_timer >= 12.0:
                self._auto_timer = 0.0
                self.next_viz(1)
                if self.window():
                    self.window().sync_viz_menu(self.viz_index)  # type: ignore[attr-defined]

        if self.window():
            self.window().update_level(self._last_level)  # type: ignore[attr-defined]
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = max(1, self.width())
        h = max(1, self.height())
        t = time.perf_counter() * 1000.0
        viz = VISUALIZERS[self.viz_index]

        try:
            now = time.perf_counter()
            sample_interval = 0.016 if self.audio.mode == "mic" else 0.0
            if sample_interval <= 0.0 or now - self._last_sample_ms >= sample_interval:
                self._cached_sample = self.audio.sample()
                self._last_sample_ms = now
            data = self._cached_sample
        except AudioEngineError as exc:
            self._paint_error(p, w, h, str(exc))
            p.end()
            return

        if data is None:
            self._paint_idle(p, w, h, t)
        else:
            try:
                fade = viz["fade"]
                p.fillRect(self.rect(), QColor(6, 6, 12, int(255 * fade)))
                viz["draw"](p, w, h, data, self.state, t)
                self._last_level = data["level"]
            except Exception:
                logger.exception("Visualizer '%s' failed", viz["name"])
                self._paint_error(p, w, h, f"Visualizer-Fehler: {viz['name']}")

        p.end()

    def _paint_error(self, p: QPainter, w: float, h: float, message: str) -> None:
        p.fillRect(self.rect(), QColor(6, 6, 12))
        p.setPen(QPen(QColor(255, 100, 100)))
        p.setFont(QFont("Sans Serif", 13))
        p.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            f"\n{message}\n",
        )

    def _paint_idle(self, p: QPainter, w: float, h: float, t: float) -> None:
        background = QRadialGradient(w * 0.55, h * 0.45, max(w, h) * 0.7)
        background.setColorAt(0, QColor(36, 18, 63))
        background.setColorAt(0.45, QColor(16, 10, 29))
        background.setColorAt(1, QColor(6, 5, 11))
        p.fillRect(self.rect(), background)
        cx, cy = w / 2, h / 2
        p.setPen(QPen(QColor(157, 94, 255, 72), 1.3))
        for i in range(5):
            r = 40 + i * 30 + math.sin(t * 0.001 + i) * 10
            p.drawEllipse(QPointF(cx, cy), r, r)

        box_w = min(560.0, w * 0.7)
        box_h = 210.0
        drop_rect = QRectF(cx - box_w / 2, cy - box_h / 2, box_w, box_h)
        border = QColor(181, 127, 255, 220 if self._drag_active else 105)
        pen = QPen(border, 2 if self._drag_active else 1.2)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(QColor(112, 61, 190, 45 if self._drag_active else 18))
        p.drawRoundedRect(drop_rect, 18, 18)

        p.setPen(QColor(224, 210, 248))
        p.setFont(QFont("Sans Serif", 18, QFont.Weight.Bold))
        p.drawText(
            QRectF(drop_rect.left() + 20, cy - 45, box_w - 40, 36),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "Audio hierher ziehen",
        )
        p.setPen(QColor(151, 137, 170))
        p.setFont(QFont("Sans Serif", 12))
        p.drawText(
            QRectF(drop_rect.left() + 20, cy + 8, box_w - 40, 54),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "MP3, WAV, FLAC, OGG und weitere Formate\n"
            "oder links Audio-Datei bzw. Mikrofon auswählen",
        )
