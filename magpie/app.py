from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from magpie.config import AppState, Preferences, log_dir, migrate_legacy_paths
from magpie.ui import MainWindow
from magpie.ui.style import apply_app_style


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
    apply_app_style(app)
    icon_path = Path(__file__).resolve().parent / "resources" / "icons" / "magpie_icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Load preferences + state, then run one-off legacy path migration before
    # the main window touches anything. This moves any pre-1.x absolute paths
    # (output_dir / labels_dir / classes_path) into per-folder overrides on the
    # currently-remembered image folder, so old users don't lose their config.
    preferences = Preferences.load()
    state = AppState.load()
    if migrate_legacy_paths(preferences, state):
        preferences.save()
        state.save()

    window = MainWindow(preferences=preferences, state=state)
    if args.path:
        window.open_image_folder(args.path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
