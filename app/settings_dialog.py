from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setModal(True)
        self.resize(380, 320)

        self.gain_slider = self._make_slider(50, 300, 140)
        self.smooth_slider = self._make_slider(0, 95, 75)
        self.particles_slider = self._make_slider(200, 4000, 1800, step=100)
        self.hue_slider = self._make_slider(0, 360, 0)
        self.saturation_slider = self._make_slider(20, 100, 85)

        self.gain_label = QLabel()
        self.smooth_label = QLabel()
        self.particles_label = QLabel()
        self.hue_label = QLabel()
        self.saturation_label = QLabel()
        self._update_labels()

        self.gain_slider.valueChanged.connect(self._update_labels)
        self.smooth_slider.valueChanged.connect(self._update_labels)
        self.particles_slider.valueChanged.connect(self._update_labels)
        self.hue_slider.valueChanged.connect(self._update_labels)
        self.saturation_slider.valueChanged.connect(self._update_labels)

        form = QFormLayout()
        form.addRow("Empfindlichkeit", self._row(self.gain_slider, self.gain_label))
        form.addRow("Glättung", self._row(self.smooth_slider, self.smooth_label))
        form.addRow("Partikel", self._row(self.particles_slider, self.particles_label))
        form.addRow("Farbton", self._row(self.hue_slider, self.hue_label))
        form.addRow("Sättigung", self._row(self.saturation_slider, self.saturation_label))

        self.auto_cycle = QCheckBox("Auto-Wechsel alle 12 Sekunden")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.auto_cycle)
        layout.addWidget(buttons)

    def _make_slider(self, low: int, high: int, value: int, step: int = 1) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(value)
        slider.setSingleStep(step)
        slider.setPageStep(step * 5)
        return slider

    def _row(self, slider: QSlider, label: QLabel) -> QWidget:
        box = QHBoxLayout()
        wrap = QWidget()
        box.addWidget(slider, 1)
        box.addWidget(label)
        wrap.setLayout(box)
        return wrap

    def _update_labels(self) -> None:
        self.gain_label.setText(f"{self.gain_slider.value() / 100:.2f}")
        self.smooth_label.setText(f"{self.smooth_slider.value() / 100:.2f}")
        self.particles_label.setText(str(self.particles_slider.value()))
        self.hue_label.setText(f"{self.hue_slider.value()}°")
        self.saturation_label.setText(f"{self.saturation_slider.value()}%")

    def gain(self) -> float:
        return self.gain_slider.value() / 100.0

    def smoothing(self) -> float:
        return self.smooth_slider.value() / 100.0

    def particles(self) -> int:
        return self.particles_slider.value()

    def hue_shift(self) -> float:
        return float(self.hue_slider.value())

    def saturation(self) -> float:
        return float(self.saturation_slider.value())

    def load(
        self,
        gain: float,
        smoothing: float,
        particles: int,
        auto_cycle: bool,
        hue_shift: float = 0.0,
        saturation: float = 85.0,
    ) -> None:
        self.gain_slider.setValue(int(gain * 100))
        self.smooth_slider.setValue(int(smoothing * 100))
        self.particles_slider.setValue(particles)
        self.hue_slider.setValue(int(hue_shift) % 360)
        self.saturation_slider.setValue(int(saturation))
        self.auto_cycle.setChecked(auto_cycle)
