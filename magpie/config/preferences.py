from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from magpie.models import Category, CustomSortPreset, OperationKind

from .paths import preferences_path


DEFAULT_EXTENSIONS = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]


def _load_sort_presets(data: dict) -> list[CustomSortPreset]:
    presets: list[CustomSortPreset] = []
    seen_ids: set[str] = set()
    for raw in data.get("custom_sort_presets") or []:
        if not isinstance(raw, dict):
            continue
        preset = CustomSortPreset.from_dict(raw)
        if preset.id in seen_ids:
            preset.id = CustomSortPreset.new_id()
        seen_ids.add(preset.id)
        presets.append(preset)

    legacy_expr = str(data.get("custom_sort_expr") or "").strip()
    if legacy_expr and not any(p.id == "legacy" for p in presets):
        presets.append(
            CustomSortPreset(id="legacy", name="自定义", expression=legacy_expr)
        )
    return presets


_SORT_FIELD_MIGRATION = {
    "natural": ("natural", False),
    "name_asc": ("name", False),
    "name_desc": ("name", True),
    "mtime_asc": ("mtime", False),
    "mtime_desc": ("mtime", True),
    # Size sort was removed; fall back to name with the equivalent direction.
    "size_asc": ("name", False),
    "size_desc": ("name", True),
}


def _unpack_sort(data: dict) -> dict:
    field, desc = _migrate_sort_strategy(data)
    return {"sort_strategy": field, "sort_descending": desc}


def _migrate_sort_strategy(data: dict) -> tuple[str, bool]:
    """Resolve the (field, descending) pair from raw preferences data.

    Accepts:
    - new format: ``sort_strategy`` ∈ {natural, name, mtime, custom:<id>}
      plus optional ``sort_descending: bool``
    - legacy format: combined strings like ``name_desc``, ``mtime_asc``,
      or the old ``custom`` shorthand backed by ``custom_sort_expr``.
    """
    value = str(data.get("sort_strategy") or "natural").strip()
    desc_explicit = data.get("sort_descending")

    if value in _SORT_FIELD_MIGRATION:
        field, desc = _SORT_FIELD_MIGRATION[value]
        if isinstance(desc_explicit, bool):
            desc = desc_explicit
        return field, desc

    if value == "custom":
        legacy_expr = str(data.get("custom_sort_expr") or "").strip()
        if legacy_expr:
            return "custom:legacy", bool(desc_explicit) if desc_explicit is not None else False
        return "natural", False

    if value.startswith("custom:") or value in ("name", "mtime"):
        return value, bool(desc_explicit) if desc_explicit is not None else False

    return "natural", False
DEFAULT_PALETTE = [
    "#22C55E",
    "#3B82F6",
    "#F59E0B",
    "#EF4444",
    "#A855F7",
    "#EC4899",
    "#14B8A6",
    "#F97316",
    "#6366F1",
    "#84CC16",
    "#06B6D4",
    "#78716C",
]


DEFAULT_OUTPUT_DIR_TEMPLATE = "{parent}/{name}_filtered"


@dataclass
class Preferences:
    categories: list[Category] = field(default_factory=list)
    output_dir_template: str = DEFAULT_OUTPUT_DIR_TEMPLATE
    labels_dir_relative: str = ""
    classes_mode: str = "auto"  # "auto" | "custom"
    classes_path: str = ""
    autoplay_interval_ms: int = 100
    show_bboxes: bool = True
    show_classified_marker: bool = True
    theme: str = "system"
    default_operation: OperationKind = OperationKind.COPY
    undo_prompt: bool = False
    end_behavior: str = "stay"
    file_extensions: list[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    conflict_strategy: str = "ask"
    sort_strategy: str = "natural"  # natural | name | mtime | custom:<id>
    sort_descending: bool = False
    custom_sort_presets: list[CustomSortPreset] = field(default_factory=list)
    recursive_scan: bool = False
    remember_recursive_scan: bool = False
    # Legacy raw values, populated only by from_dict() when loading a pre-1.x
    # JSON. The startup migration reads these, moves them into AppState
    # per-folder overrides, and clears them. Not serialized back to disk.
    legacy_source_dir: str = ""
    legacy_output_dir: str = ""
    legacy_labels_dir: str = ""
    legacy_classes_path: str = ""

    @classmethod
    def default(cls) -> "Preferences":
        return cls()

    @classmethod
    def load(cls, path: Path | None = None) -> "Preferences":
        path = path or preferences_path()
        if not path.exists():
            return cls.default()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except Exception as exc:
            print(f"Failed to load preferences, using defaults: {exc}")
            return cls.default()

    @classmethod
    def from_dict(cls, data: dict) -> "Preferences":
        operation = data.get("default_operation", OperationKind.COPY.value)
        try:
            default_operation = OperationKind(operation)
        except ValueError:
            default_operation = OperationKind.COPY

        classes_mode = str(data.get("classes_mode") or "").strip()
        classes_path_value = str(data.get("classes_path", ""))
        # Legacy preferences had no classes_mode; if classes_path was set,
        # treat it as a custom path. Migration to per-folder overrides happens
        # in project_paths.migrate_legacy_paths() during startup.
        if not classes_mode:
            classes_mode = "custom" if classes_path_value else "auto"

        return cls(
            categories=[Category.from_dict(item) for item in data.get("categories", [])],
            output_dir_template=str(
                data.get("output_dir_template") or DEFAULT_OUTPUT_DIR_TEMPLATE
            ),
            labels_dir_relative=str(data.get("labels_dir_relative", "")),
            classes_mode=classes_mode if classes_mode in ("auto", "custom") else "auto",
            classes_path=classes_path_value,
            autoplay_interval_ms=int(data.get("autoplay_interval_ms", 100)),
            show_bboxes=bool(data.get("show_bboxes", True)),
            show_classified_marker=bool(data.get("show_classified_marker", True)),
            theme=str(data.get("theme", "system")),
            default_operation=default_operation,
            undo_prompt=bool(data.get("undo_prompt", False)),
            end_behavior=str(data.get("end_behavior", "stay")),
            file_extensions=list(data.get("file_extensions", DEFAULT_EXTENSIONS)),
            conflict_strategy=str(data.get("conflict_strategy", "ask")),
            **_unpack_sort(data),
            custom_sort_presets=_load_sort_presets(data),
            recursive_scan=bool(data.get("recursive_scan", False)),
            remember_recursive_scan=bool(data.get("remember_recursive_scan", False)),
            legacy_source_dir=str(data.get("source_dir", "")),
            legacy_output_dir=str(data.get("output_dir", "")),
            legacy_labels_dir=str(data.get("labels_dir", "")),
            legacy_classes_path=classes_path_value if "classes_mode" not in data else "",
        )

    def to_dict(self) -> dict:
        return {
            "categories": [category.to_dict() for category in self.categories],
            "output_dir_template": self.output_dir_template,
            "labels_dir_relative": self.labels_dir_relative,
            "classes_mode": self.classes_mode,
            "classes_path": self.classes_path,
            "autoplay_interval_ms": self.autoplay_interval_ms,
            "show_bboxes": self.show_bboxes,
            "show_classified_marker": self.show_classified_marker,
            "theme": self.theme,
            "default_operation": self.default_operation.value,
            "undo_prompt": self.undo_prompt,
            "end_behavior": self.end_behavior,
            "file_extensions": self.file_extensions,
            "conflict_strategy": self.conflict_strategy,
            "sort_strategy": self.sort_strategy,
            "sort_descending": self.sort_descending,
            "custom_sort_presets": [preset.to_dict() for preset in self.custom_sort_presets],
            "recursive_scan": self.recursive_scan,
            "remember_recursive_scan": self.remember_recursive_scan,
        }

    def save(self, path: Path | None = None) -> None:
        path = path or preferences_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
