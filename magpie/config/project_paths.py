"""Output-directory template resolution and one-shot legacy path migration.

Labels and classes resolution now lives in ``preset_resolution.py``. This
module keeps only:

- ``resolve_output_dir`` — renders the global output-dir template against a
  source folder, honoring a per-folder ``output_dir`` override.
- ``ProjectPathError`` — raised for malformed templates.
- ``migrate_legacy_paths`` — startup helper that moves pre-1.x absolute path
  fields into per-folder overrides on the currently-remembered folder.
"""

from __future__ import annotations

import os
from pathlib import Path

from .preferences import Preferences
from .state import AppState


class ProjectPathError(ValueError):
    """Raised when a path template is malformed or cannot be rendered."""


def _resolve_path(value: str, folder: Path) -> Path:
    """Expand ``~`` and resolve a path string relative to ``folder``."""
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    joined = (folder / candidate) if folder else candidate
    return Path(os.path.normpath(str(joined)))


def resolve_output_dir(
    prefs: Preferences, overrides: dict | None, folder: Path
) -> Path:
    """Compute the effective output directory for ``folder``."""
    override = (overrides or {}).get("output_dir")
    if override:
        return _resolve_path(str(override), folder)

    template = prefs.output_dir_template or "{parent}/{name}_filtered"
    try:
        rendered = template.format(
            folder=str(folder),
            name=folder.name,
            parent=str(folder.parent),
            stem=folder.stem,
        )
    except (KeyError, IndexError) as exc:
        raise ProjectPathError(f"输出目录模板含未知占位符：{exc}") from exc
    except Exception as exc:  # noqa: BLE001 — surface formatting errors
        raise ProjectPathError(f"输出目录模板无效：{exc}") from exc
    if not rendered.strip():
        raise ProjectPathError("输出目录模板渲染为空字符串")
    return Path(os.path.normpath(rendered)).expanduser()


def migrate_legacy_paths(prefs: Preferences, state: AppState) -> bool:
    """Move legacy absolute paths from ``Preferences`` into per-folder overrides.

    Older Magpie versions stored ``source_dir``/``output_dir``/``labels_dir``/
    ``classes_path`` as global absolute strings. Those legacy fields are
    captured by ``Preferences.from_dict`` into ``legacy_*`` attributes; this
    function moves them into ``state.per_folder_overrides`` for the currently
    remembered ``image_folder`` (if any) using the new ``preset:``/``path:``
    encoding, then clears the legacy attributes.

    Returns ``True`` if any change was made (caller should persist).
    """
    changed = False
    folder = state.image_folder

    if prefs.legacy_output_dir:
        if folder:
            state.update_overrides(folder, output_dir=prefs.legacy_output_dir)
        prefs.legacy_output_dir = ""
        changed = True

    if prefs.legacy_labels_dir:
        if folder:
            state.update_overrides(
                folder, labels_selection=f"path:{prefs.legacy_labels_dir}"
            )
        prefs.legacy_labels_dir = ""
        changed = True

    if prefs.legacy_classes_path:
        # Preferences-level migration already created an inline "legacy" preset
        # by reading the file once; point the folder at it.
        if folder:
            state.update_overrides(folder, classes_selection="preset:legacy")
        prefs.legacy_classes_path = ""
        changed = True

    if prefs.legacy_source_dir:
        prefs.legacy_source_dir = ""
        changed = True

    return changed
