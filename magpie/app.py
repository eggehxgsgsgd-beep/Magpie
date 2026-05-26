from __future__ import annotations

import argparse
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from magpie.config import log_dir
from magpie.ui import MainWindow


def configure_logging() -> None:
    handler = TimedRotatingFileHandler(
        log_dir() / "app.log",
        when="D",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler],
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Magpie")
    parser.add_argument("path", nargs="?", default=None, help="Path to an image folder")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.version:
        try:
            from importlib.metadata import version

            print(version("magpie"))
        except Exception:
            from magpie import __version__

            print(__version__)
        return 0

    configure_logging()

    # QtWebEngine requires a software-friendly OpenGL backend on some Windows
    # drivers; setting ShareOpenGLContexts here is required to use the engine
    # alongside other Qt OpenGL surfaces and must be done before QApplication.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName("Magpie")
    app.setOrganizationName("Magpie")
    icon_path = Path(__file__).resolve().parent / "resources" / "icons" / "magpie_icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    if args.path:
        window.open_image_folder(args.path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
