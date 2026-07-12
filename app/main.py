from __future__ import annotations

import os


def main() -> int:
    import logging

    from PyQt6.QtWidgets import QMessageBox

    from app.audio_engine import AudioEngineError
    from app.logging_config import LATEST_LOG
    from app.main_window import MainWindow, create_app
    from app.utils import configure_runtime

    log = logging.getLogger("app.main")
    log.info("Application main() starting")

    # These variables must be set before importing Qt Multimedia.
    os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")
    os.environ.setdefault("QT_FFMPEG_ENCODING_HW_DEVICE_TYPES", ",")
    os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false;qt.qpa.*=false")

    configure_runtime()
    app = create_app()
    try:
        window = MainWindow()
    except AudioEngineError as exc:
        log.error("Startup failed (audio): %s", exc)
        QMessageBox.critical(None, "Sound Visualizer", str(exc))
        return 1
    except Exception as exc:
        log.exception("Startup failed")
        QMessageBox.critical(
            None,
            "Sound Visualizer",
            f"Die App konnte nicht starten:\n{exc}\n\nLog: {LATEST_LOG}",
        )
        return 1
    window.show()
    log.info("Main window shown")
    return app.exec()
