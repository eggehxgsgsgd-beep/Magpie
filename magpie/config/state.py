from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .paths import state_path


@dataclass
class AppState:
    image_folder: str = ""
    current_index: int = 0
    recent_folders: list[str] = field(default_factory=list)
    geometry_hex: str = ""
    window_state_hex: str = ""

    @classmethod
    def load(cls, path: Path | None = None) -> "AppState":
        path = path or state_path()
        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                image_folder=str(data.get("image_folder", "")),
                current_index=int(data.get("current_index", 0)),
                recent_folders=list(data.get("recent_folders", [])),
                geometry_hex=str(data.get("geometry_hex", "")),
                window_state_hex=str(data.get("window_state_hex", "")),
            )
        except Exception as exc:
            print(f"Failed to load state, using defaults: {exc}")
            return cls()

    def save(self, path: Path | None = None) -> None:
        path = path or state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "image_folder": self.image_folder,
                    "current_index": self.current_index,
                    "recent_folders": self.recent_folders[:10],
                    "geometry_hex": self.geometry_hex,
                    "window_state_hex": self.window_state_hex,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def add_recent_folder(self, folder: str) -> None:
        self.recent_folders = [item for item in self.recent_folders if item != folder]
        self.recent_folders.insert(0, folder)
        self.recent_folders = self.recent_folders[:10]
