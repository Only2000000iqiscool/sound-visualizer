from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from app.audio_engine import AudioEngine
from app.visualizers import VISUALIZERS


class VisualizerCanvas(QWidget):
    def __init__(self, audio: AudioEngine, parent=None) -> None:
        super().__init__(parent)
        self.audio = audio
        self.viz_index = 0
        self.state: dict = {"particle_count": 1800}
        self._last_ms = 0.0
        self._auto_cycle = False
        self._auto_timer = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAutoFillBackground(False)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

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

    def _reset_viz_state(self) -> None:
        keep = {"particle_count": self.state.get("particle_count", 1800)}
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

        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        t = time.perf_counter() * 1000.0
        viz = VISUALIZERS[self.viz_index]
        data = self.audio.sample()

        if data is None:
            self._paint_idle(p, w, h, t)
        else:
            fade = viz["fade"]
            p.fillRect(self.rect(), QColor(6, 6, 12, int(255 * fade)))
            viz["draw"](p, w, h, data, self.state, t)
            if self.window():
                self.window().update_level(data["level"])  # type: ignore[attr-defined]

        p.end()

    def _paint_idle(self, p: QPainter, w: float, h: float, t: float) -> None:
        p.fillRect(self.rect(), QColor(6, 6, 12))
        cx, cy = w / 2, h / 2
        p.setPen(QPen(QColor(124, 92, 255, 64), 1))
        for i in range(5):
            r = 40 + i * 30 + math.sin(t * 0.001 + i) * 10
            p.drawEllipse(QPointF(cx, cy), r, r)

        p.setPen(QPen(QColor(136, 136, 160, 153)))
        p.setFont(QFont("Sans Serif", 14, QFont.Weight.DemiBold))
        p.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "\n\nMikrofon oder Audio-Datei starten\n(Datei → Audio öffnen)",
        )
