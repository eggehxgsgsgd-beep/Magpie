from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from magpie.models import (
    BUILTIN_SORT_PRESETS,
    Category,
    CategoryPreset,
    ClassesPreset,
    LabelsPreset,
    OperationKind,
    SortPreset,
)

from .paths import preferences_path


DEFAULT_EXTENSIONS = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]

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


def _default_sort_presets() -> list[SortPreset]:
    """Always include the 3 built-in sort presets at the top of the list."""
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
    autoplay_interval_ms: int = 100
    show_bboxes: bool = True
    show_classified_marker: bool = True
    theme: str = "system"
    default_operation: OperationKind = OperationKind.COPY
    undo_prompt: bool = False
    end_behavior: str = "stay"
    file_extensions: list[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    conflict_strategy: str = "ask"
    recursive_scan: bool = False
    remember_recursive_scan: bool = False

    # ---- Legacy raw values (cleared after one-shot migration) ----
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

        category_presets, active_category = _load_or_migrate_category_presets(data)
        labels_presets, default_labels_sel = _load_or_migrate_labels_presets(data)
        classes_presets, default_classes_sel = _load_or_migrate_classes_presets(data)
        sort_presets, active_sort_id, sort_desc = _load_or_migrate_sort_presets(data)

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
            autoplay_interval_ms=int(data.get("autoplay_interval_ms", 100)),
            show_bboxes=bool(data.get("show_bboxes", True)),
            show_classified_marker=bool(data.get("show_classified_marker", True)),
            theme=str(data.get("theme", "system")),
            default_operation=default_operation,
            undo_prompt=bool(data.get("undo_prompt", False)),
            end_behavior=str(data.get("end_behavior", "stay")),
            file_extensions=list(data.get("file_extensions", DEFAULT_EXTENSIONS)),
            conflict_strategy=str(data.get("conflict_strategy", "ask")),
            recursive_scan=bool(data.get("recursive_scan", False)),
            remember_recursive_scan=bool(data.get("remember_recursive_scan", False)),
            legacy_source_dir=str(data.get("source_dir", "")),
            legacy_output_dir=str(data.get("output_dir", "")),
            legacy_labels_dir=str(data.get("labels_dir", "")),
            legacy_classes_path=str(data.get("classes_path", "")) if "classes_presets" not in data else "",
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
            "autoplay_interval_ms": self.autoplay_interval_ms,
            "show_bboxes": self.show_bboxes,
            "show_classified_marker": self.show_classified_marker,
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
# Migration helpers
# ---------------------------------------------------------------------------


def _load_or_migrate_category_presets(data: dict) -> tuple[list[CategoryPreset], str]:
    """Return (presets, active_id). Migrates legacy flat ``categories`` list."""
    raw_presets = data.get("category_presets")
    if isinstance(raw_presets, list) and raw_presets:
        presets = [CategoryPreset.from_dict(item) for item in raw_presets if isinstance(item, dict)]
        if not presets:
            presets = _default_category_presets()
        active = str(data.get("active_category_preset") or "").strip()
        if not any(p.id == active for p in presets):
            active = presets[0].id
        return presets, active

    legacy = data.get("categories")
    if isinstance(legacy, list) and legacy:
        cats = [Category.from_dict(item) for item in legacy]
        return [CategoryPreset(id="default", name="默认", categories=cats)], "default"

    return _default_category_presets(), "default"


def _load_or_migrate_labels_presets(data: dict) -> tuple[list[LabelsPreset], str]:
    raw_presets = data.get("labels_presets")
    if isinstance(raw_presets, list):
        presets = [LabelsPreset.from_dict(item) for item in raw_presets if isinstance(item, dict)]
        selection = str(data.get("default_labels_selection") or "").strip() or "none"
        if selection.startswith("preset:") and not any(
            p.id == selection.split(":", 1)[1] for p in presets
        ):
            selection = "none"
        return presets, selection

    legacy_relative = str(data.get("labels_dir_relative") or "").strip()
    if legacy_relative:
        legacy_preset = LabelsPreset(id="legacy", name="默认标签目录", path=legacy_relative)
        return [legacy_preset], "preset:legacy"
    return [], "none"


def _load_or_migrate_classes_presets(data: dict) -> tuple[list[ClassesPreset], str]:
    raw_presets = data.get("classes_presets")
    if isinstance(raw_presets, list):
        presets = [ClassesPreset.from_dict(item) for item in raw_presets if isinstance(item, dict)]
        selection = str(data.get("default_classes_selection") or "").strip() or "none"
        if selection.startswith("preset:") and not any(
            p.id == selection.split(":", 1)[1] for p in presets
        ):
            selection = "none"
        return presets, selection

    # Legacy: classes_mode = "custom" + classes_path → read once into inline preset.
    legacy_mode = str(data.get("classes_mode") or "").strip()
    legacy_path = str(data.get("classes_path") or "").strip()
    if legacy_mode == "custom" and legacy_path:
        names: list[str] = []
        try:
            content = Path(legacy_path).expanduser().read_text(encoding="utf-8", errors="ignore")
            names = [line.strip() for line in content.splitlines() if line.strip()]
        except OSError as exc:
            print(f"[migration] could not read legacy classes file {legacy_path}: {exc}")
        legacy_preset = ClassesPreset(id="legacy", name="默认 classes.txt", names=names)
        return [legacy_preset], "preset:legacy"
    return [], "none"


_LEGACY_SORT_FIELD_MIGRATION = {
    "natural": ("builtin:natural", False),
    "name_asc": ("builtin:name", False),
    "name_desc": ("builtin:name", True),
    "mtime_asc": ("builtin:mtime", False),
    "mtime_desc": ("builtin:mtime", True),
    # Size sort removed; fall back to name in the equivalent direction.
    "size_asc": ("builtin:name", False),
    "size_desc": ("builtin:name", True),
    "name": ("builtin:name", False),
    "mtime": ("builtin:mtime", False),
}


def _load_or_migrate_sort_presets(data: dict) -> tuple[list[SortPreset], str, bool]:
    """Return (presets, active_id, descending)."""
    raw_presets = data.get("sort_presets")
    if isinstance(raw_presets, list) and raw_presets:
        # New-format file.
        presets = [SortPreset.from_dict(item) for item in raw_presets if isinstance(item, dict)]
        # Ensure built-ins are present (in case user-managed JSON dropped them).
        _ensure_builtin_sort_presets(presets)
        active = str(data.get("active_sort_preset_id") or "").strip()
        if not any(p.id == active for p in presets):
            active = "builtin:natural"
        desc = bool(data.get("sort_descending", False))
        return presets, active, desc

    # Legacy: sort_strategy + custom_sort_presets + custom_sort_expr
    presets = list(_default_sort_presets())
    raw_custom = data.get("custom_sort_presets") or []
    for raw in raw_custom:
        if not isinstance(raw, dict):
            continue
        preset = SortPreset.from_dict({**raw, "kind": "custom"})
        if not any(p.id == preset.id for p in presets):
            presets.append(preset)

    legacy_expr = str(data.get("custom_sort_expr") or "").strip()
    if legacy_expr and not any(p.id == "legacy" for p in presets):
        presets.append(
            SortPreset(id="legacy", name="自定义", kind="custom", expression=legacy_expr)
        )

    raw_strategy = str(data.get("sort_strategy") or "").strip()
    desc_explicit = data.get("sort_descending")

    if raw_strategy.startswith("custom:"):
        active = raw_strategy
        desc = bool(desc_explicit) if desc_explicit is not None else False
    elif raw_strategy in _LEGACY_SORT_FIELD_MIGRATION:
        active, mapped_desc = _LEGACY_SORT_FIELD_MIGRATION[raw_strategy]
        desc = bool(desc_explicit) if isinstance(desc_explicit, bool) else mapped_desc
    elif raw_strategy == "custom" and legacy_expr:
        active = "legacy"
        desc = bool(desc_explicit) if desc_explicit is not None else False
    else:
        active = "builtin:natural"
        desc = bool(desc_explicit) if desc_explicit is not None else False

    if not any(p.id == active for p in presets):
        active = "builtin:natural"

    return presets, active, desc


def _ensure_builtin_sort_presets(presets: list[SortPreset]) -> None:
    """Insert any missing builtins at the front, preserving user-set names if any."""
    existing_ids = {p.id for p in presets}
    for default in BUILTIN_SORT_PRESETS:
        if default.id not in existing_ids:
            presets.insert(0, SortPreset(
                id=default.id, name=default.name, kind=default.kind,
                field=default.field, expression=default.expression,
            ))
