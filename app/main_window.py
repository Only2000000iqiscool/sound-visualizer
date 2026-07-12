from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QWidget,
)

from app.audio_engine import AudioEngine, AudioEngineError
from app.audio_formats import AUDIO_EXTENSIONS, is_audio_file
from app.canvas_widget import VisualizerCanvas
from app.control_panel import ControlPanel
from app.decode_worker import DecodeWorker
from app.import_dialog import ImportDialog
from app.microphone_dialog import MicrophoneDialog
from app.output_dialog import OutputDialog
from app.playback import AudioPlayback
from app.settings_dialog import SettingsDialog
from app.theme import PURPLE_STYLESHEET
from app.visualizers import VISUALIZERS

ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "spectra-app-icon.png"
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sound Visualizer")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self.audio = AudioEngine()
        self._gain = 1.4
        self._smoothing = 0.75
        self._particles = 1800
        self._hue_shift = 0.0
        self._saturation = 85.0
        self._auto_cycle = False
        self._viz_actions: list[QAction] = []
        self._fullscreen = False
        self._saved_geometry = None
        self.fullscreen_action: QAction | None = None
        self._decode_worker: DecodeWorker | None = None
        self._pending_path: str | None = None
        self._selected_mic_id: str | int | None = None
        self._last_mic_device: dict | None = None
        self._selected_output_id: str | int | None = None
        self._import_dialog: ImportDialog | None = None

        self.playback = AudioPlayback(self)

        self.canvas = VisualizerCanvas(self.audio, self)
        self.canvas.setAcceptDrops(True)
        self.setCentralWidget(self.canvas)

        self._build_menu()
        self._build_sidebar()
        self._build_status()
        self._apply_settings()
        QTimer.singleShot(200, self._initialize_audio_output)

    def _build_sidebar(self) -> None:
        self.control_panel = ControlPanel(self)
        self.control_panel.file_requested.connect(self.open_audio_file)
        self.control_panel.microphone_requested.connect(self.choose_microphone)
        self.control_panel.output_requested.connect(self.choose_output_device)
        self.control_panel.stop_requested.connect(self.stop_audio)
        self.control_panel.settings_requested.connect(self.open_settings)
        self.control_panel.visualizer_selected.connect(self.select_viz)

        self.sidebar = QDockWidget(self)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.sidebar.setTitleBarWidget(QWidget())
        self.sidebar.setWidget(self.control_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar)

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

        mic_action = QAction("Mikrofon auswählen…", self)
        mic_action.setShortcut("Ctrl+M")
        mic_action.triggered.connect(self.choose_microphone)
        file_menu.addAction(mic_action)

        output_action = QAction("Audio-Ausgang auswählen…", self)
        output_action.setShortcut("Ctrl+Shift+O")
        output_action.triggered.connect(self.choose_output_device)
        file_menu.addAction(output_action)

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
        fullscreen_action = QAction("Randloses Vollbild", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        self.fullscreen_action = fullscreen_action

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

        esc_action = QAction(self)
        esc_action.setShortcut(Qt.Key.Key_Escape)
        esc_action.triggered.connect(self.exit_fullscreen)
        self.addAction(esc_action)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._drag_has_audio(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        path = self._first_audio_from_drop(event)
        if path:
            event.acceptProposedAction()
            # Defer loading: calling Qt Multimedia during a Wayland drop event
            # deadlocks PipeWire and crashes the process.
            logger.info("Drop accepted, scheduling load: %s", path)
            QTimer.singleShot(0, lambda p=path: self.load_audio_file(p))
        else:
            event.ignore()

    def _drag_has_audio(self, event: QDragEnterEvent | QDropEvent) -> bool:
        mime = event.mimeData()
        if not mime.hasUrls():
            return False
        return any(url.isLocalFile() and is_audio_file(url.toLocalFile()) for url in mime.urls())

    def _first_audio_from_drop(self, event: QDropEvent) -> str | None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if is_audio_file(path):
                    return path
        return None

    def _apply_settings(self) -> None:
        self.audio.gain = self._gain
        self.audio.smoothing = self._smoothing
        self.canvas.set_particle_count(self._particles)
        self.canvas.set_color_settings(self._hue_shift, self._saturation)
        self.canvas.set_auto_cycle(self._auto_cycle)

    def select_viz(self, index: int) -> None:
        self.canvas.set_viz_index(index)
        self.sync_viz_menu(index)
        self.control_panel.set_visualizer(index)
        self.status_label.setText(f"Visualizer: {VISUALIZERS[index]['name']}")

    def sync_viz_menu(self, index: int) -> None:
        if 0 <= index < len(self._viz_actions):
            self._viz_actions[index].setChecked(True)

    def _nav_viz(self, direction: int) -> None:
        name = self.canvas.next_viz(direction)
        self.sync_viz_menu(self.canvas.viz_index)
        self.status_label.setText(f"Visualizer: {name}")

    def open_audio_file(self) -> None:
        extensions = " ".join(f"*{ext}" for ext in sorted(AUDIO_EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Audio-Datei öffnen",
            str(Path.home()),
            f"Audio ({extensions});;Alle Dateien (*)",
        )
        if not path:
            return
        self.load_audio_file(path)

    def load_audio_file(self, path: str) -> None:
        # Never touch Qt Multimedia synchronously from UI events (clicks, drops).
        QTimer.singleShot(0, lambda p=path: self._begin_load_audio(p))

    def _begin_load_audio(self, path: str) -> None:
        if self._decode_worker and self._decode_worker.isRunning():
            logger.warning("Load skipped, decode already running: %s", path)
            self.status_label.setText("Ladevorgang läuft bereits…")
            return

        logger.info("Loading audio file: %s", path)
        self._pending_path = path
        self.playback.stop()
        self.audio.stop()
        self.status_label.setText(f"Lade {Path(path).name}…")
        self.level_bar.setRange(0, 0)

        try:
            playback_spec = self.playback.format_spec()
        except AudioEngineError as exc:
            logger.error("Audio output unavailable: %s", exc)
            self.level_bar.setRange(0, 100)
            QMessageBox.critical(self, "Fehler", str(exc))
            self.status_label.setText("Kein Audio-Ausgang")
            return

        self._decode_worker = DecodeWorker(
            path,
            playback_spec,
            self,
        )
        self._import_dialog = ImportDialog(path, self)
        self._import_dialog.show()
        self._decode_worker.finished_ok.connect(self._on_decode_ok)
        self._decode_worker.failed.connect(self._on_decode_failed)
        self._decode_worker.progress_changed.connect(
            self._import_dialog.update_progress
        )
        self._decode_worker.finished.connect(self._clear_decode_worker)
        self._decode_worker.start()

    def _on_decode_ok(self, prepared) -> None:
        path = self._pending_path
        if not path:
            return
        dialog = self._import_dialog
        try:
            logger.info("Decode finished, starting playback: %s", path)
            if dialog:
                dialog.set_finalizing()
            self.playback.play_prepared(prepared)
            self.audio.set_file_samples(
                prepared.samples,
                self.playback.position_ms,
            )
            self.level_bar.setRange(0, 100)
            self.status_label.setText(f"Wiedergabe: {Path(path).name}")
            self.control_panel.set_source(f"DATEI\n{Path(path).name}")
            if dialog:
                dialog.set_complete()
                QTimer.singleShot(220, dialog.accept)
            logger.info("Playback started: %s", path)
        except (AudioEngineError, Exception) as exc:
            logger.exception("Playback failed for %s", path)
            self.level_bar.setRange(0, 100)
            QMessageBox.critical(self, "Fehler", f"Audio konnte nicht gestartet werden:\n{exc}")
            self.status_label.setText("Fehler beim Laden")

    def _on_decode_failed(self, message: str) -> None:
        logger.error("Decode failed: %s", message)
        self.level_bar.setRange(0, 100)
        if self._import_dialog:
            self._import_dialog.reject()
        QMessageBox.critical(self, "Fehler", f"Audio konnte nicht geladen werden:\n{message}")
        self.status_label.setText("Laden fehlgeschlagen")

    def _clear_decode_worker(self) -> None:
        self._decode_worker = None
        self._pending_path = None
        self._import_dialog = None

    def choose_microphone(self) -> None:
        QTimer.singleShot(0, self._open_microphone_dialog)

    def _open_microphone_dialog(self) -> None:
        try:
            devices = self.audio.list_input_devices()
        except AudioEngineError as exc:
            QMessageBox.critical(self, "Mikrofon", str(exc))
            return
        if not devices:
            QMessageBox.warning(self, "Mikrofon", "Keine Audio-Eingabegeräte gefunden.")
            return

        dialog = MicrophoneDialog(devices, self._selected_mic_id, self)
        if not dialog.exec():
            return
        selected = dialog.selected_device()
        self._selected_mic_id = selected["id"]
        QTimer.singleShot(0, lambda dev=selected: self.start_mic(dev))

    def choose_output_device(self) -> None:
        QTimer.singleShot(0, self._open_output_dialog)

    def _open_output_dialog(self) -> None:
        try:
            devices = self.playback.list_output_devices()
        except AudioEngineError as exc:
            QMessageBox.critical(self, "Audio-Ausgang", str(exc))
            return
        if not devices:
            QMessageBox.warning(self, "Audio-Ausgang", "Keine Ausgabegeräte gefunden.")
            return

        dialog = OutputDialog(devices, self._selected_output_id, self)
        if not dialog.exec():
            return
        selected = dialog.selected_device()
        self._selected_output_id = selected["id"]
        self.playback.set_output_device(selected)
        self.status_label.setText(f"Ausgabe: {selected['display_name']}")
        logger.info("User selected output: %s", selected["display_name"])
        if self.audio.mode == "mic" and self._last_mic_device is not None:
            QTimer.singleShot(0, lambda dev=self._last_mic_device: self.start_mic(dev))

    def _initialize_audio_output(self) -> None:
        self.playback.initialize()
        self._auto_select_default_output()
        logger.info("Audio output engine started (PyAudio)")

    def _auto_select_default_output(self) -> None:
        try:
            devices = self.playback.list_output_devices()
            default = next((d for d in devices if d.get("default")), None)
            if default:
                self._selected_output_id = default["id"]
                self.playback.set_output_device(default)
                logger.info("Default output: %s", default["display_name"])
        except Exception as exc:
            logger.warning("Could not auto-select output device: %s", exc)

    def start_mic(self, device: dict) -> None:
        try:
            self.playback.stop()
            if self._decode_worker and self._decode_worker.isRunning():
                self._decode_worker.wait(2000)
            self._last_mic_device = device
            monitor_gain = min(self._gain, 1.0)
            self.audio.start_mic(
                device=device,
                output_sink=self.playback.output_sink_name(),
                monitor_gain=monitor_gain,
            )
            name = device.get("display_name", "Standardgerät")
            output_name = self.playback.current_device_name()
            if not self.audio.mic_monitor_active():
                self.status_label.setText(f"Mikrofon aktiv (ohne Ton): {name}")
                logger.warning("Mic monitor inactive for sink %s", self.playback.output_sink_name())
            else:
                self.status_label.setText(f"Mikrofon aktiv: {name}")
            self.control_panel.set_source(
                f"MIKROFON\n{name}\n→ {output_name}"
            )
            logger.info("Mic started on input %s, output '%s'", name, output_name)
        except AudioEngineError as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
        except Exception as exc:
            logger.exception("Mic start failed")
            QMessageBox.critical(self, "Fehler", f"Mikrofon nicht verfügbar:\n{exc}")

    def stop_audio(self) -> None:
        self.playback.stop()
        self.audio.stop()
        self._last_mic_device = None
        self.level_bar.setValue(0)
        self.status_label.setText("Gestoppt")
        self.control_panel.set_source("Keine Quelle aktiv", False)
        self.canvas.update()

    def toggle_pause(self) -> None:
        if self.audio.mode != "file":
            return
        paused = self.playback.toggle_pause()
        self.status_label.setText("Pause" if paused else "Wiedergabe")

    def toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.enter_fullscreen()
        else:
            self.exit_fullscreen()

    def enter_fullscreen(self) -> None:
        if self._fullscreen:
            return
        self._fullscreen = True
        self._saved_geometry = self.geometry()
        self.menuBar().hide()
        self.statusBar().hide()
        self.sidebar.hide()
        # showFullScreen is borderless on Linux/Wayland and Windows. Changing
        # window flags while visible destroys the native window and can race
        # with repainting, which caused crashes in QWaylandShmBackingStore.
        self.showFullScreen()
        if self.fullscreen_action:
            self.fullscreen_action.setChecked(True)

    def exit_fullscreen(self) -> None:
        if not self._fullscreen:
            return
        self._fullscreen = False
        self.menuBar().show()
        self.statusBar().show()
        self.sidebar.show()
        self.showNormal()
        if self._saved_geometry is not None:
            self.setGeometry(self._saved_geometry)
        if self.fullscreen_action:
            self.fullscreen_action.setChecked(False)

    def open_settings(self) -> None:
        dlg = SettingsDialog(self)
        old_gain = self._gain
        dlg.load(
            self._gain,
            self._smoothing,
            self._particles,
            self._auto_cycle,
            self._hue_shift,
            self._saturation,
        )
        if dlg.exec():
            self._gain = dlg.gain()
            self._smoothing = dlg.smoothing()
            self._particles = dlg.particles()
            self._hue_shift = dlg.hue_shift()
            self._saturation = dlg.saturation()
            self._auto_cycle = dlg.auto_cycle.isChecked()
            self._apply_settings()
            if (
                self.audio.mode == "mic"
                and self._last_mic_device is not None
                and abs(self._gain - old_gain) > 0.001
            ):
                QTimer.singleShot(0, lambda dev=self._last_mic_device: self.start_mic(dev))

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "Sound Visualizer",
            "Native Desktop-App mit 17 Audio-Visualizern.\n\n"
            "Steuerung: ←/→ Visualizer, Leertaste Pause, F11 randloses Vollbild, Esc beenden.\n"
            "Audio-Dateien per Drag & Drop auf das Fenster ziehen.",
        )

    def update_level(self, level: float) -> None:
        self.level_bar.setValue(min(100, int(level * 140)))

    def closeEvent(self, event) -> None:
        if self._decode_worker and self._decode_worker.isRunning():
            self._decode_worker.wait(3000)
        self.playback.stop()
        self.audio.shutdown()
        event.accept()


def create_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Sound Visualizer")
    app.setOrganizationName("SoundVisualizer")
    app.setStyle("Fusion")
    app.setStyleSheet(PURPLE_STYLESHEET)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    return app
