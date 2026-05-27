from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from magpie.models import (
    BUILTIN_SORT_PRESETS,
    CategoryPreset,
    ClassesPreset,
    LabelsPreset,
    OperationKind,
    SortPreset,
)

from .paths import preferences_path


DEFAULT_EXTENSIONS = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]

DEFAULT_OUTPUT_DIR_TEMPLATE = "{parent}/{name}_filtered"


def _default_sort_presets() -> list[SortPreset]:
    return [
        SortPreset(id=p.id, name=p.name, kind=p.kind, field=p.field, expression=p.expression)
        for p in BUILTIN_SORT_PRESETS
    ]


def _default_category_presets() -> list[CategoryPreset]:
    return [CategoryPreset(id="default", name="默认", categories=[])]


@dataclass
class Preferences:
    # ---- Category presets (global active) ----
    category_presets: list[CategoryPreset] = field(default_factory=_default_category_presets)
    active_category_preset: str = "default"

    # ---- Labels presets ----
    labels_presets: list[LabelsPreset] = field(default_factory=list)
    default_labels_selection: str = "none"   # "preset:<id>" | "none"

    # ---- Classes presets (inline only) ----
    classes_presets: list[ClassesPreset] = field(default_factory=list)
    default_classes_selection: str = "none"  # "preset:<id>" | "none"

    # ---- Sort ----
    sort_presets: list[SortPreset] = field(default_factory=_default_sort_presets)
    active_sort_preset_id: str = "builtin:natural"
    sort_descending: bool = False

    # ---- Output directory template ----
    output_dir_template: str = DEFAULT_OUTPUT_DIR_TEMPLATE

    # ---- Display / behavior ----
    prefetch_count: int = 3
    autoplay_interval_ms: int = 100
    show_bboxes: bool = True
    theme: str = "system"
    default_operation: OperationKind = OperationKind.COPY
    undo_prompt: bool = False
    end_behavior: str = "stay"
    file_extensions: list[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    conflict_strategy: str = "ask"
    recursive_scan: bool = False
    remember_recursive_scan: bool = False

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
        operation_raw = data.get("default_operation", OperationKind.COPY.value)
        try:
            default_operation = OperationKind(operation_raw)
        except ValueError:
            default_operation = OperationKind.COPY

        category_presets, active_category = _load_category_presets(data)
        labels_presets, default_labels_sel = _load_labels_presets(data)
        classes_presets, default_classes_sel = _load_classes_presets(data)
        sort_presets, active_sort_id, sort_desc = _load_sort_presets(data)

        return cls(
            category_presets=category_presets,
            active_category_preset=active_category,
            labels_presets=labels_presets,
            default_labels_selection=default_labels_sel,
            classes_presets=classes_presets,
            default_classes_selection=default_classes_sel,
            sort_presets=sort_presets,
            active_sort_preset_id=active_sort_id,
            sort_descending=sort_desc,
            output_dir_template=str(
                data.get("output_dir_template") or DEFAULT_OUTPUT_DIR_TEMPLATE
            ),
            prefetch_count=max(1, min(int(data.get("prefetch_count", 3)), 20)),
            autoplay_interval_ms=int(data.get("autoplay_interval_ms", 100)),
            show_bboxes=bool(data.get("show_bboxes", True)),
            theme=str(data.get("theme", "system")),
            default_operation=default_operation,
            undo_prompt=bool(data.get("undo_prompt", False)),
            end_behavior=str(data.get("end_behavior", "stay")),
            file_extensions=list(data.get("file_extensions", DEFAULT_EXTENSIONS)),
            conflict_strategy=str(data.get("conflict_strategy", "ask")),
            recursive_scan=bool(data.get("recursive_scan", False)),
            remember_recursive_scan=bool(data.get("remember_recursive_scan", False)),
        )

    def to_dict(self) -> dict:
        return {
            "category_presets": [p.to_dict() for p in self.category_presets],
            "active_category_preset": self.active_category_preset,
            "labels_presets": [p.to_dict() for p in self.labels_presets],
            "default_labels_selection": self.default_labels_selection,
            "classes_presets": [p.to_dict() for p in self.classes_presets],
            "default_classes_selection": self.default_classes_selection,
            "sort_presets": [p.to_dict() for p in self.sort_presets],
            "active_sort_preset_id": self.active_sort_preset_id,
            "sort_descending": self.sort_descending,
            "output_dir_template": self.output_dir_template,
            "prefetch_count": self.prefetch_count,
            "autoplay_interval_ms": self.autoplay_interval_ms,
            "show_bboxes": self.show_bboxes,
            "theme": self.theme,
            "default_operation": self.default_operation.value,
            "undo_prompt": self.undo_prompt,
            "end_behavior": self.end_behavior,
            "file_extensions": self.file_extensions,
            "conflict_strategy": self.conflict_strategy,
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


# ---------------------------------------------------------------------------
# Preset loaders. Each only understands the new schema; unknown / missing
# keys fall back to empty defaults. There is no legacy migration here on
# purpose — see plans/memoized-seeking-sedgewick.md.
# ---------------------------------------------------------------------------


def _load_category_presets(data: dict) -> tuple[list[CategoryPreset], str]:
    raw_presets = data.get("category_presets")
    if isinstance(raw_presets, list) and raw_presets:
        presets = [
            CategoryPreset.from_dict(item)
            for item in raw_presets if isinstance(item, dict)
        ]
        if not presets:
            presets = _default_category_presets()
        active = str(data.get("active_category_preset") or "").strip()
        if not any(p.id == active for p in presets):
            active = presets[0].id
        return presets, active
    return _default_category_presets(), "default"


def _load_labels_presets(data: dict) -> tuple[list[LabelsPreset], str]:
    raw_presets = data.get("labels_presets")
    if isinstance(raw_presets, list):
        presets = [
            LabelsPreset.from_dict(item)
            for item in raw_presets if isinstance(item, dict)
        ]
        selection = str(data.get("default_labels_selection") or "").strip() or "none"
        if selection.startswith("preset:") and not any(
            p.id == selection.split(":", 1)[1] for p in presets
        ):
            selection = "none"
        return presets, selection
    return [], "none"


def _load_classes_presets(data: dict) -> tuple[list[ClassesPreset], str]:
    raw_presets = data.get("classes_presets")
    if isinstance(raw_presets, list):
        presets = [
            ClassesPreset.from_dict(item)
            for item in raw_presets if isinstance(item, dict)
        ]
        selection = str(data.get("default_classes_selection") or "").strip() or "none"
        if selection.startswith("preset:") and not any(
            p.id == selection.split(":", 1)[1] for p in presets
        ):
            selection = "none"
        return presets, selection
    return [], "none"


def _load_sort_presets(data: dict) -> tuple[list[SortPreset], str, bool]:
    raw_presets = data.get("sort_presets")
    presets: list[SortPreset] = []
    if isinstance(raw_presets, list):
        presets = [
            SortPreset.from_dict(item)
            for item in raw_presets if isinstance(item, dict)
        ]
    _ensure_builtin_sort_presets(presets)
    active = str(data.get("active_sort_preset_id") or "").strip()
    if not any(p.id == active for p in presets):
        active = "builtin:natural"
    desc = bool(data.get("sort_descending", False))
    return presets, active, desc


def _ensure_builtin_sort_presets(presets: list[SortPreset]) -> None:
    """Always keep the 3 built-in presets in the list, prepending any that
    are missing. Users can rename them in their JSON if they really want,
    but the IDs are stable."""
    existing_ids = {p.id for p in presets}
    for default in BUILTIN_SORT_PRESETS:
        if default.id not in existing_ids:
            presets.insert(0, SortPreset(
                id=default.id, name=default.name, kind=default.kind,
                field=default.field, expression=default.expression,
            ))
