from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.visualizers import VISUALIZERS


class VisualizerEditorPanel(QWidget):
    """Live editor – every change is applied immediately to the main canvas."""

    settings_changed = pyqtSignal(dict)
    visualizer_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("visualizerEditor")
        self._block_emit = False

        hint = QLabel(
            "Änderungen werden sofort in der Live-Vorschau übernommen. "
            "Ohne Audioquelle läuft eine Demo-Animation."
        )
        hint.setObjectName("editorHint")
        hint.setWordWrap(True)

        self.viz_combo = QComboBox()
        self.viz_combo.setMinimumHeight(38)
        for i, viz in enumerate(VISUALIZERS):
            self.viz_combo.addItem(viz["name"], i)
        self.viz_combo.currentIndexChanged.connect(self._on_viz_changed)

        self.gain_slider = self._slider(50, 300, 140)
        self.smooth_slider = self._slider(0, 95, 75)
        self.particles_slider = self._slider(200, 4000, 1800, step=100)
        self.hue_slider = self._slider(0, 360, 0)
        self.saturation_slider = self._slider(20, 100, 85)
        self.fade_slider = self._slider(2, 50, 22)

        self.gain_label = QLabel()
        self.smooth_label = QLabel()
        self.particles_label = QLabel()
        self.hue_label = QLabel()
        self.saturation_label = QLabel()
        self.fade_label = QLabel()

        for slider in (
            self.gain_slider,
            self.smooth_slider,
            self.particles_slider,
            self.hue_slider,
            self.saturation_slider,
            self.fade_slider,
        ):
            slider.valueChanged.connect(self._emit_settings)

        reset_button = QPushButton("Standardwerte")
        reset_button.setObjectName("ghostButton")
        reset_button.clicked.connect(self._reset_defaults)

        form = QFormLayout()
        form.addRow("Visualizer", self.viz_combo)
        form.addRow("Empfindlichkeit", self._row(self.gain_slider, self.gain_label))
        form.addRow("Glättung", self._row(self.smooth_slider, self.smooth_label))
        form.addRow("Nachleuchtung", self._row(self.fade_slider, self.fade_label))
        form.addRow("Partikel", self._row(self.particles_slider, self.particles_label))
        form.addRow("Farbton", self._row(self.hue_slider, self.hue_label))
        form.addRow("Sättigung", self._row(self.saturation_slider, self.saturation_label))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(reset_button)
        layout.addStretch(1)

        self._update_labels()

    def _slider(self, low: int, high: int, value: int, step: int = 1) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(value)
        slider.setSingleStep(step)
        slider.setPageStep(max(step * 5, 5))
        return slider

    def _row(self, slider: QSlider, label: QLabel) -> QWidget:
        box = QHBoxLayout()
        wrap = QWidget()
        box.addWidget(slider, 1)
        box.addWidget(label)
        wrap.setLayout(box)
        return wrap

    def _on_viz_changed(self, _index: int) -> None:
        viz_index = self.viz_combo.currentData()
        if viz_index is None:
            return
        self.set_fade_for_visualizer(VISUALIZERS[viz_index]["fade"])
        self.visualizer_changed.emit(int(viz_index))
        self._emit_settings()

    def _reset_defaults(self) -> None:
        viz_index = self.viz_combo.currentData() or 0
        self.load(
            {
                "gain": 1.4,
                "smoothing": 0.75,
                "particles": 1800,
                "hue_shift": 0.0,
                "saturation": 85.0,
                "fade": VISUALIZERS[viz_index]["fade"],
                "viz_index": viz_index,
            }
        )
        self._emit_settings()

    def _update_labels(self) -> None:
        self.gain_label.setText(f"{self.gain_slider.value() / 100:.2f}")
        self.smooth_label.setText(f"{self.smooth_slider.value() / 100:.2f}")
        self.particles_label.setText(str(self.particles_slider.value()))
        self.hue_label.setText(f"{self.hue_slider.value()}°")
        self.saturation_label.setText(f"{self.saturation_slider.value()}%")
        self.fade_label.setText(f"{self.fade_slider.value() / 100:.2f}")

    def _emit_settings(self) -> None:
        self._update_labels()
        if self._block_emit:
            return
        self.settings_changed.emit(self.values())

    def values(self) -> dict:
        return {
            "gain": self.gain_slider.value() / 100.0,
            "smoothing": self.smooth_slider.value() / 100.0,
            "particles": self.particles_slider.value(),
            "hue_shift": float(self.hue_slider.value()),
            "saturation": float(self.saturation_slider.value()),
            "fade": self.fade_slider.value() / 100.0,
            "viz_index": int(self.viz_combo.currentData() or 0),
        }

    def load(self, values: dict) -> None:
        self._block_emit = True
        viz_index = int(values.get("viz_index", 0))
        if self.viz_combo.currentData() != viz_index:
            self.viz_combo.setCurrentIndex(viz_index)
        self.gain_slider.setValue(int(values.get("gain", 1.4) * 100))
        self.smooth_slider.setValue(int(values.get("smoothing", 0.75) * 100))
        self.particles_slider.setValue(int(values.get("particles", 1800)))
        self.hue_slider.setValue(int(values.get("hue_shift", 0)) % 360)
        self.saturation_slider.setValue(int(values.get("saturation", 85)))
        fade = values.get("fade")
        if fade is None:
            fade = VISUALIZERS[viz_index]["fade"]
        self.fade_slider.setValue(max(2, min(50, int(fade * 100))))
        self._block_emit = False
        self._update_labels()

    def set_visualizer_index(self, index: int) -> None:
        index = index % len(VISUALIZERS)
        if self.viz_combo.currentData() == index:
            return
        self._block_emit = True
        self.viz_combo.setCurrentIndex(index)
        self._block_emit = False

    def set_fade_for_visualizer(self, fade: float) -> None:
        self._block_emit = True
        self.fade_slider.setValue(max(2, min(50, int(fade * 100))))
        self._block_emit = False
        self._update_labels()
