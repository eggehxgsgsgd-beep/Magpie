"""Resolve "active" values from presets + per-folder overrides.

Each resolver takes ``prefs`` plus optional ``overrides`` (the per-folder
dict from ``AppState.per_folder_overrides``) and returns the concrete value
in use right now. Pure logic, no Qt or filesystem I/O for class names.
"""

from __future__ import annotations

import os
from pathlib import Path

from magpie.models import (
    BUILTIN_SORT_PRESETS,
    Category,
    ClassesPreset,
    LabelsPreset,
    SortPreset,
)

from .preferences import Preferences


# ---------------------------------------------------------------------------
# Categories (global only, no per-project override in this revision)
# ---------------------------------------------------------------------------


def resolve_active_categories(prefs: Preferences) -> list[Category]:
    for preset in prefs.category_presets:
        if preset.id == prefs.active_category_preset:
            return list(preset.categories)
    if prefs.category_presets:
        return list(prefs.category_presets[0].categories)
    return []


# ---------------------------------------------------------------------------
# Labels directory
# ---------------------------------------------------------------------------


def _resolve_relative_path(value: str, folder: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    joined = (folder / candidate) if folder else candidate
    return Path(os.path.normpath(str(joined)))


def resolve_labels_dir(
    prefs: Preferences, overrides: dict | None, folder: Path
) -> Path | None:
    """Compute the effective labels directory.

    Encoding (both ``overrides["labels_selection"]`` and
    ``prefs.default_labels_selection``):
    - ``preset:<id>`` — look up LabelsPreset.path and join to folder
    - ``path:<value>`` — explicit path (override only)
    - ``none`` — None
    """
    overrides = overrides or {}
    selection = (overrides.get("labels_selection") or prefs.default_labels_selection or "none").strip()
    if not selection or selection == "none":
        return None
    if selection.startswith("path:"):
        raw = selection[len("path:"):].strip()
        if not raw:
            return None
        return _resolve_relative_path(raw, folder)
    if selection.startswith("preset:"):
        preset_id = selection.split(":", 1)[1]
        preset = _find_labels_preset(prefs.labels_presets, preset_id)
        if preset is None or not preset.path.strip():
            return None
        return _resolve_relative_path(preset.path, folder)
    return None


def _find_labels_preset(presets: list[LabelsPreset], preset_id: str) -> LabelsPreset | None:
    for preset in presets:
        if preset.id == preset_id:
            return preset
    return None


# ---------------------------------------------------------------------------
# Class names (inline-only, no file/auto modes)
# ---------------------------------------------------------------------------


def resolve_class_names(
    prefs: Preferences, overrides: dict | None
) -> list[str]:
    """Return the class-name list in effect right now.

    Encoding (overrides["classes_selection"] / prefs.default_classes_selection):
    - ``preset:<id>`` — the preset's ``names``
    - ``none`` — empty list
    """
    overrides = overrides or {}
    selection = (
        overrides.get("classes_selection")
        or prefs.default_classes_selection
        or "none"
    ).strip()
    if not selection or selection == "none":
        return []
    if selection.startswith("preset:"):
        preset_id = selection.split(":", 1)[1]
        preset = _find_classes_preset(prefs.classes_presets, preset_id)
        if preset is None:
            return []
        return list(preset.names)
    return []


def _find_classes_preset(
    presets: list[ClassesPreset], preset_id: str
) -> ClassesPreset | None:
    for preset in presets:
        if preset.id == preset_id:
            return preset
    return None


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------


def _find_sort_preset(presets: list[SortPreset], preset_id: str) -> SortPreset | None:
    for preset in presets:
        if preset.id == preset_id:
            return preset
    return None


def resolve_active_sort(
    prefs: Preferences, overrides: dict | None
) -> tuple[SortPreset, bool]:
    """Return (sort preset, descending)."""
    overrides = overrides or {}
    preset_id = (overrides.get("sort_preset_id") or prefs.active_sort_preset_id).strip()
    preset = _find_sort_preset(prefs.sort_presets, preset_id)
    if preset is None:
        # Fallback to the very first builtin.
        preset = SortPreset(
            id=BUILTIN_SORT_PRESETS[0].id,
            name=BUILTIN_SORT_PRESETS[0].name,
            kind=BUILTIN_SORT_PRESETS[0].kind,
            field=BUILTIN_SORT_PRESETS[0].field,
        )
    descending = overrides.get("sort_descending")
    if descending is None:
        descending = prefs.sort_descending
    return preset, bool(descending)
