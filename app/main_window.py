from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStatusBar,
)

from app.audio_engine import AudioEngine
from app.canvas_widget import VisualizerCanvas
from app.settings_dialog import SettingsDialog
from app.visualizers import VISUALIZERS


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sound Visualizer")
        self.resize(1280, 800)

        self.audio = AudioEngine()
        self._gain = 1.4
        self._smoothing = 0.75
        self._particles = 1800
        self._auto_cycle = False
        self._viz_actions: list[QAction] = []

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(lambda _ms: None)

        self.canvas = VisualizerCanvas(self.audio, self)
        self.setCentralWidget(self.canvas)

        self._build_menu()
        self._build_status()
        self._apply_settings()

    def _build_status(self) -> None:
        status = QStatusBar(self)
        self.status_label = QLabel("Bereit")
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setFixedWidth(140)
        self.level_bar.setTextVisible(False)
        status.addWidget(self.status_label, 1)
        status.addPermanentWidget(self.level_bar)
        self.setStatusBar(status)

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Datei")
        open_action = QAction("Audio öffnen…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_audio_file)
        file_menu.addAction(open_action)

        mic_action = QAction("Mikrofon starten", self)
        mic_action.setShortcut("Ctrl+M")
        mic_action.triggered.connect(self.start_mic)
        file_menu.addAction(mic_action)

        stop_action = QAction("Stoppen", self)
        stop_action.triggered.connect(self.stop_audio)
        file_menu.addAction(stop_action)

        file_menu.addSeparator()
        quit_action = QAction("Beenden", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        viz_menu = menubar.addMenu("&Visualizer")
        group = QActionGroup(self)
        group.setExclusive(True)
        for i, viz in enumerate(VISUALIZERS):
            action = QAction(viz["name"], self)
            action.setCheckable(True)
            action.setData(i)
            if i == 0:
                action.setChecked(True)
            action.triggered.connect(lambda checked, idx=i: self.select_viz(idx) if checked else None)
            group.addAction(action)
            viz_menu.addAction(action)
            self._viz_actions.append(action)

        view_menu = menubar.addMenu("&Ansicht")
        fullscreen_action = QAction("Vollbild", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        settings_action = QAction("Einstellungen…", self)
        settings_action.triggered.connect(self.open_settings)
        view_menu.addAction(settings_action)

        help_menu = menubar.addMenu("&Hilfe")
        about_action = QAction("Über", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        prev_action = QAction(self)
        prev_action.setShortcut(Qt.Key.Key_Left)
        prev_action.triggered.connect(lambda: self._nav_viz(-1))
        self.addAction(prev_action)

        next_action = QAction(self)
        next_action.setShortcut(Qt.Key.Key_Right)
        next_action.triggered.connect(lambda: self._nav_viz(1))
        self.addAction(next_action)

        pause_action = QAction(self)
        pause_action.setShortcut(Qt.Key.Key_Space)
        pause_action.triggered.connect(self.toggle_pause)
        self.addAction(pause_action)

    def _apply_settings(self) -> None:
        self.audio.gain = self._gain
        self.audio.smoothing = self._smoothing
        self.canvas.set_particle_count(self._particles)
        self.canvas.set_auto_cycle(self._auto_cycle)

    def select_viz(self, index: int) -> None:
        self.canvas.set_viz_index(index)
        self.sync_viz_menu(index)
        self.status_label.setText(f"Visualizer: {VISUALIZERS[index]['name']}")

    def sync_viz_menu(self, index: int) -> None:
        if 0 <= index < len(self._viz_actions):
            self._viz_actions[index].setChecked(True)

    def _nav_viz(self, direction: int) -> None:
        name = self.canvas.next_viz(direction)
        self.sync_viz_menu(self.canvas.viz_index)
        self.status_label.setText(f"Visualizer: {name}")

    def open_audio_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Audio-Datei öffnen",
            str(Path.home()),
            "Audio (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;Alle Dateien (*)",
        )
        if not path:
            return
        self.load_audio_file(path)

    def load_audio_file(self, path: str) -> None:
        try:
            self.player.stop()
            self.audio.stop()
            self.player.setSource(QUrl.fromLocalFile(path))
            self.audio.start_file(path, self.player.position)
            self.player.play()
            self.status_label.setText(f"Wiedergabe: {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Audio konnte nicht geladen werden:\n{exc}")

    def start_mic(self) -> None:
        try:
            self.player.stop()
            self.audio.start_mic()
            self.status_label.setText("Mikrofon aktiv")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Mikrofon nicht verfügbar:\n{exc}")

    def stop_audio(self) -> None:
        self.player.stop()
        self.audio.stop()
        self.level_bar.setValue(0)
        self.status_label.setText("Gestoppt")
        self.canvas.update()

    def toggle_pause(self) -> None:
        if self.audio.mode != "file":
            return
        from PyQt6.QtMultimedia import QMediaPlayer

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.status_label.setText("Pause")
        else:
            self.player.play()
            self.status_label.setText("Wiedergabe")

    def toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def open_settings(self) -> None:
        dlg = SettingsDialog(self)
        dlg.load(self._gain, self._smoothing, self._particles, self._auto_cycle)
        if dlg.exec():
            self._gain = dlg.gain()
            self._smoothing = dlg.smoothing()
            self._particles = dlg.particles()
            self._auto_cycle = dlg.auto_cycle.isChecked()
            self._apply_settings()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "Sound Visualizer",
            "Native Desktop-App mit 17 Audio-Visualizern.\n\n"
            "Steuerung: ←/→ Visualizer, Leertaste Pause, F11 Vollbild.",
        )

    def update_level(self, level: float) -> None:
        self.level_bar.setValue(min(100, int(level * 140)))

    def closeEvent(self, event) -> None:
        self.player.stop()
        self.audio.shutdown()
        event.accept()


def create_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Sound Visualizer")
    app.setOrganizationName("SoundVisualizer")
    app.setStyle("Fusion")
    return app
