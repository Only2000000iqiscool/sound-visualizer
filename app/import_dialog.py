from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QWidget


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = float(max(0, value))
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{amount:.1f} GB"


def _format_eta(seconds: float) -> str:
    if seconds < 0:
        return "Berechne Restzeit …"
    if seconds < 1:
        return "Fast fertig …"
    minutes, secs = divmod(round(seconds), 60)
    if minutes:
        return f"Noch ca. {minutes}:{secs:02d} Min."
    return f"Noch ca. {secs} Sek."


class ImportDialog(QDialog):
    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Audio wird vorbereitet")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setFixedWidth(500)

        file_path = Path(path)
        try:
            file_size = _format_bytes(file_path.stat().st_size)
        except OSError:
            file_size = "unbekannte Größe"

        title = QLabel("Audio wird vorbereitet")
        title.setObjectName("importTitle")
        file_label = QLabel(file_path.name)
        file_label.setObjectName("importFile")
        file_label.setWordWrap(True)
        source_label = QLabel(f"Dateigröße: {file_size}")
        source_label.setObjectName("importMuted")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p %")
        self.progress.setTextVisible(True)

        self.detail = QLabel("Audiodaten werden analysiert …")
        self.detail.setObjectName("importDetail")
        self.eta = QLabel("Berechne Restzeit …")
        self.eta.setObjectName("importMuted")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(file_label)
        layout.addWidget(source_label)
        layout.addSpacing(8)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail)
        layout.addWidget(self.eta)

    def update_progress(
        self,
        percent: int,
        done: int,
        total: int,
        eta_seconds: float,
        cached: bool,
    ) -> None:
        self.progress.setValue(max(0, min(100, percent)))
        if cached:
            self.detail.setText("Im schnellen Cache gefunden")
            self.eta.setText("Starte Wiedergabe …")
            return
        self.detail.setText(f"Analysiert: {_format_bytes(done)} / {_format_bytes(total)}")
        self.eta.setText(_format_eta(eta_seconds))

    def set_finalizing(self) -> None:
        self.progress.setValue(96)
        self.detail.setText("Audio-Ausgabe wird vorbereitet")
        self.eta.setText("Einen kurzen Moment …")

    def set_complete(self) -> None:
        self.progress.setValue(100)
        self.detail.setText("Audio ist bereit")
        self.eta.setText("Wiedergabe gestartet")
