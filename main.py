from __future__ import annotations

import sys
import ctypes
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from config.config import ConfigManager
from ui.main_window import MainWindow


def main() -> int:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "music_tagger.app.1.0"
        )
    except Exception:
        pass

    app = QApplication(sys.argv)

    icon_path = Path(__file__).resolve().parent / "assets" / "app.ico"
    app_icon = QIcon(str(icon_path))
    app.setWindowIcon(app_icon)

    config_manager = ConfigManager()
    config = config_manager.load()

    window = MainWindow(config=config, config_manager=config_manager)
    window.setWindowIcon(app_icon)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())