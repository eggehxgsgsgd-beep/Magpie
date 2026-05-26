from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QStandardPaths


APP_NAME = "Magpie"


def app_data_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not location:
        location = str(Path.home() / ".local" / "share" / APP_NAME)

    path = Path(location)
    path.mkdir(parents=True, exist_ok=True)
    return path


def preferences_path() -> Path:
    return app_data_dir() / "preferences.json"


def state_path() -> Path:
    return app_data_dir() / "state.json"


def log_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def classifications_dir() -> Path:
    path = app_data_dir() / "classifications"
    path.mkdir(parents=True, exist_ok=True)
    return path
