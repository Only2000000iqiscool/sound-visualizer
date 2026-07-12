from __future__ import annotations

from app.main_window import MainWindow, create_app


def main() -> int:
    app = create_app()
    window = MainWindow()
    window.show()
    return app.exec()
