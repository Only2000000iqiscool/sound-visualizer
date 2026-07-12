from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.visualizers import VISUALIZERS


class ControlPanel(QWidget):
    file_requested = pyqtSignal()
    microphone_requested = pyqtSignal()
    output_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    visualizer_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("controlPanel")
        self.setMinimumWidth(270)
        self.setMaximumWidth(320)

        logo = QLabel("SPECTRA")
        logo.setObjectName("logo")
        tagline = QLabel("SOUND VISUALIZER")
        tagline.setObjectName("tagline")

        source_title = QLabel("AUDIOQUELLE")
        source_title.setObjectName("sectionTitle")
        file_button = QPushButton("  Audio-Datei öffnen")
        file_button.setObjectName("primaryButton")
        file_button.setMinimumHeight(46)
        file_button.clicked.connect(self.file_requested)
        mic_button = QPushButton("  Mikrofon auswählen")
        mic_button.setObjectName("secondaryButton")
        mic_button.setMinimumHeight(46)
        mic_button.clicked.connect(self.microphone_requested)
        output_button = QPushButton("  Audio-Ausgang wählen")
        output_button.setObjectName("secondaryButton")
        output_button.setMinimumHeight(46)
        output_button.clicked.connect(self.output_requested)

        self.source_status = QLabel("Keine Quelle aktiv")
        self.source_status.setObjectName("sourceStatus")
        self.source_status.setWordWrap(True)

        visualizer_title = QLabel("VISUALIZER")
        visualizer_title.setObjectName("sectionTitle")
        self.visualizer_list = QListWidget()
        self.visualizer_list.setObjectName("visualizerList")
        for i, visualizer in enumerate(VISUALIZERS):
            self.visualizer_list.addItem(
                f"{i + 1:02d}   {visualizer['name']}"
            )
        self.visualizer_list.setCurrentRow(0)
        self.visualizer_list.currentRowChanged.connect(
            self.visualizer_selected
        )

        settings_button = QPushButton("Einstellungen")
        settings_button.setObjectName("ghostButton")
        settings_button.clicked.connect(self.settings_requested)
        stop_button = QPushButton("Audio stoppen")
        stop_button.setObjectName("dangerButton")
        stop_button.clicked.connect(self.stop_requested)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")

        shortcuts = QLabel(
            "← →  Visualizer     Leertaste  Pause\n"
            "F11  Vollbild       Esc  Zurück"
        )
        shortcuts.setObjectName("shortcuts")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 22, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(logo)
        layout.addWidget(tagline)
        layout.addSpacing(18)
        layout.addWidget(source_title)
        layout.addWidget(file_button)
        layout.addWidget(mic_button)
        layout.addWidget(output_button)
        layout.addWidget(self.source_status)
        layout.addSpacing(12)
        layout.addWidget(visualizer_title)
        layout.addWidget(self.visualizer_list, 1)
        layout.addWidget(settings_button)
        layout.addWidget(stop_button)
        layout.addWidget(divider)
        layout.addWidget(shortcuts)

    def set_visualizer(self, index: int) -> None:
        self.visualizer_list.blockSignals(True)
        self.visualizer_list.setCurrentRow(index)
        self.visualizer_list.blockSignals(False)

    def set_source(self, text: str, active: bool = True) -> None:
        self.source_status.setText(text)
        self.source_status.setProperty("active", active)
        self.source_status.style().unpolish(self.source_status)
        self.source_status.style().polish(self.source_status)
