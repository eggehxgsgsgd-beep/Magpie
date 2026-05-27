from __future__ import annotations

import argparse
import atexit
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from magpie.config import AppState, Preferences, app_data_dir, log_dir
from magpie.ui import MainWindow
from magpie.font_config import apply_app_font
from magpie.ui.style import apply_app_style


_lock_file: Path | None = None


def _acquire_lock() -> bool:
    """Try to acquire a file-based single-instance lock.

    Returns ``True`` if this is the only instance, ``False`` otherwise.
    """
    global _lock_file  # noqa: PLW0603
    lock_path = app_data_dir() / "magpie.lock"
    if lock_path.exists():
        # Check if the PID inside is still alive.
        try:
            pid = int(lock_path.read_text().strip())
            # os.kill(pid, 0) doesn't send a signal — just checks existence.
            import os
            os.kill(pid, 0)
            return False  # Process still running.
        except (ValueError, OSError, ProcessLookupError):
            pass  # Stale lock — previous crash.
    lock_path.write_text(str(sys.modules.get("os", __import__("os")).getpid()))
    _lock_file = lock_path
    atexit.register(_release_lock)
    return True


def _release_lock() -> None:
    global _lock_file  # noqa: PLW0603
    if _lock_file is not None:
        _lock_file.unlink(missing_ok=True)
        _lock_file = None


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

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName("Magpie")
    app.setOrganizationName("Magpie")
    apply_app_font(app)

    if not _acquire_lock():
        QMessageBox.warning(None, "Magpie", "Magpie 已在运行中，请勿重复启动。")
        return 1
    apply_app_style(app)
    icon_path = Path(__file__).resolve().parent / "resources" / "icons" / "magpie_icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    preferences = Preferences.load()
    state = AppState.load()
    window = MainWindow(preferences=preferences, state=state)
    if args.path:
        window.open_image_folder(args.path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
