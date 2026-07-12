from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class MicrophoneDialog(QDialog):
    def __init__(
        self,
        devices: list[dict],
        selected_id: str | int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.devices = devices
        self.setWindowTitle("Mikrofon auswählen")
        self.setModal(True)
        self.setMinimumWidth(520)

        title = QLabel("Welchen Eingang möchtest du verwenden?")
        title.setObjectName("dialogTitle")
        subtitle = QLabel(
            "Die Bezeichnungen zeigen dir, ob es sich um Headset, Line-In, "
            "Front-Mikrofon oder einen USB-Eingang handelt."
        )
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)

        self.combo = QComboBox()
        self.combo.setMinimumHeight(42)
        current = 0
        for i, device in enumerate(devices):
            suffix = "  ·  Standard" if device["default"] else ""
            self.combo.addItem(f"{device['display_name']}{suffix}", device)
            if selected_id is not None and device.get("id") == selected_id:
                current = i
            elif selected_id is None and device["default"]:
                current = i
        self.combo.setCurrentIndex(current)

        self.description = QLabel()
        self.description.setObjectName("deviceDescription")
        self.description.setWordWrap(True)
        self.combo.currentIndexChanged.connect(self._update_description)
        self._update_description()

        hint = QLabel(
            "Tipp: Falls du unsicher bist, wähle „Automatisch – Systemstandard“. "
            "Das ist in den meisten Fällen die richtige Wahl."
        )
        hint.setObjectName("hintCard")
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Mikrofon verwenden"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(self.combo)
        layout.addWidget(self.description)
        layout.addWidget(hint)
        layout.addSpacing(8)
        layout.addWidget(buttons)

    def _update_description(self) -> None:
        device = self.combo.currentData()
        if not device:
            self.description.clear()
            return
        rate = device["sample_rate"]
        channels = device.get("channels", 1)
        self.description.setText(
            f"{device['description']}\n"
            f"Abtastrate: {rate:,} Hz · Kanäle: {channels}"
        )

    def selected_device(self) -> dict:
        return self.combo.currentData()
