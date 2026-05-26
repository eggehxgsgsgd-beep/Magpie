from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .paths import state_path


_OVERRIDE_KEYS = (
    # path overrides
    "output_dir",
    # preset-based selections (encoded as "preset:<id>" / "path:<v>" / "none" / "auto")
    "labels_selection",
    "classes_selection",
    # sort
    "sort_preset_id",
    "sort_descending",
    # behavior overrides
    "conflict_strategy",
    "recursive_scan",
    "current_index",
)


# Legacy combined values like "name_desc"/"mtime_asc"/"size_*" map to a
# builtin sort preset id + descending flag. Used only at load time to migrate
# old per_folder_overrides entries.
_LEGACY_SORT_MIGRATION = {
    "natural": ("builtin:natural", False),
    "name": ("builtin:name", False),
    "mtime": ("builtin:mtime", False),
    "name_asc": ("builtin:name", False),
    "name_desc": ("builtin:name", True),
    "mtime_asc": ("builtin:mtime", False),
    "mtime_desc": ("builtin:mtime", True),
    "size_asc": ("builtin:name", False),
    "size_desc": ("builtin:name", True),
}


def _migrate_override_keys(entry: dict) -> dict:
    """Translate legacy per-folder override keys to the new schema.

    - ``sort_strategy`` (string) → ``sort_preset_id`` (+ ``sort_descending`` if combined)
    - ``labels_dir`` → ``labels_selection`` as ``path:<value>``
    - ``classes_mode`` + ``classes_path`` → ``classes_selection`` as ``preset:legacy`` (data not preserved)
      or ``none``
    """
    out = dict(entry)

    legacy_sort = out.pop("sort_strategy", None)
    if isinstance(legacy_sort, str) and "sort_preset_id" not in out:
        if legacy_sort in _LEGACY_SORT_MIGRATION:
            preset_id, desc = _LEGACY_SORT_MIGRATION[legacy_sort]
            out["sort_preset_id"] = preset_id
            if "sort_descending" not in out:
                out["sort_descending"] = desc
        elif legacy_sort.startswith("custom:"):
            out["sort_preset_id"] = legacy_sort.split(":", 1)[1]

    legacy_labels = out.pop("labels_dir", None)
    if isinstance(legacy_labels, str) and legacy_labels and "labels_selection" not in out:
        out["labels_selection"] = f"path:{legacy_labels}"

    legacy_classes_mode = out.pop("classes_mode", None)
    legacy_classes_path = out.pop("classes_path", None)
    if "classes_selection" not in out:
        if legacy_classes_mode == "custom" and legacy_classes_path:
            # Cannot read here without filesystem; preferences-level migration
            # already created a "legacy" preset if applicable. Best effort.
            out["classes_selection"] = "preset:legacy"
        elif legacy_classes_mode == "auto":
            # Auto mode is gone; users will recreate as a preset if needed.
            out["classes_selection"] = "none"

    return out


@dataclass
class AppState:
    image_folder: str = ""
    current_index: int = 0
    recent_folders: list[str] = field(default_factory=list)
    geometry_hex: str = ""
    window_state_hex: str = ""
    per_folder_overrides: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "AppState":
        path = path or state_path()
        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw_overrides = data.get("per_folder_overrides", {}) or {}
            overrides: dict[str, dict] = {}
            if isinstance(raw_overrides, dict):
                for folder, entry in raw_overrides.items():
                    if not isinstance(entry, dict):
                        continue
                    migrated = _migrate_override_keys(entry)
                    overrides[str(folder)] = {
                        key: migrated[key] for key in _OVERRIDE_KEYS if key in migrated
                    }
            return cls(
                image_folder=str(data.get("image_folder", "")),
                current_index=int(data.get("current_index", 0)),
                recent_folders=list(data.get("recent_folders", [])),
                geometry_hex=str(data.get("geometry_hex", "")),
                window_state_hex=str(data.get("window_state_hex", "")),
                per_folder_overrides=overrides,
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
                    "per_folder_overrides": self.per_folder_overrides,
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

    def overrides_for(self, folder: str) -> dict:
        return dict(self.per_folder_overrides.get(folder, {}))

    def update_overrides(self, folder: str, **values) -> None:
        if not folder:
            return
        entry = dict(self.per_folder_overrides.get(folder, {}))
        for key, value in values.items():
            if key not in _OVERRIDE_KEYS or value is None:
                continue
            entry[key] = value
        if entry:
            self.per_folder_overrides[folder] = entry
        # Prune overrides for folders no longer in recent list, keep cap at 32.
        if len(self.per_folder_overrides) > 32:
            allowed = set(self.recent_folders) | {folder}
            self.per_folder_overrides = {
                key: val for key, val in self.per_folder_overrides.items() if key in allowed
            }
