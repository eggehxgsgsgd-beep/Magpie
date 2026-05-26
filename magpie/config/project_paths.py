"""Per-project path resolution.

The :class:`Preferences` only stores global *templates* (e.g.
``{parent}/{name}_filtered`` for the output directory, ``labels`` for the
relative labels dir, ``auto`` / ``custom`` for ``classes.txt`` lookup).  The
actual effective paths used while a folder is open are resolved at folder open
time by the functions below, taking per-folder overrides from
``AppState.per_folder_overrides`` into account.

These functions are pure and Qt-free so they can be unit tested directly.
"""

from __future__ import annotations

from pathlib import Path

from .preferences import Preferences
from .state import AppState


class ProjectPathError(ValueError):
    """Raised when a path template is malformed or cannot be rendered."""


def _resolve_path(value: str, folder: Path) -> Path:
    """Expand ``~`` and resolve a path string relative to ``folder``.

    Absolute paths are returned as-is (with ``~`` expanded). Relative paths
    are joined under ``folder``.
    """
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (folder / candidate).resolve() if folder else candidate


def resolve_output_dir(
    prefs: Preferences, overrides: dict, folder: Path
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
    return Path(rendered).expanduser()


def resolve_labels_dir(
    prefs: Preferences, overrides: dict, folder: Path
) -> Path | None:
    """Compute the effective labels directory.

    Returns ``None`` when no override and no global relative path is configured
    — in that case BBox rendering is disabled.
    """
    override = (overrides or {}).get("labels_dir")
    if override:
        return _resolve_path(str(override), folder)

    relative = (prefs.labels_dir_relative or "").strip()
    if not relative:
        return None
    return _resolve_path(relative, folder)


def resolve_classes_path(
    prefs: Preferences, overrides: dict, labels_dir: Path | None
) -> Path | None:
    """Compute the effective ``classes.txt`` path.

    Honors ``classes_mode`` (auto/custom) and the corresponding override or
    global fields. In ``auto`` mode the returned path is
    ``<labels_dir>/classes.txt`` *regardless* of whether that file exists; the
    caller decides whether to warn the user about a missing file.
    """
    overrides = overrides or {}
    mode = overrides.get("classes_mode") or prefs.classes_mode or "auto"

    if mode == "custom":
        raw = overrides.get("classes_path") or prefs.classes_path or ""
        raw = str(raw).strip()
        if not raw:
            return None
        return Path(raw).expanduser()

    # auto
    if labels_dir is None:
        return None
    return labels_dir / "classes.txt"


def migrate_legacy_paths(prefs: Preferences, state: AppState) -> bool:
    """Move legacy absolute paths from ``Preferences`` into per-folder overrides.

    Older Magpie versions stored ``source_dir``/``output_dir``/``labels_dir``/
    ``classes_path`` as global absolute strings.  This function:

    1. Drops the (read-only / dead) ``source_dir``.
    2. For each remaining legacy field that is non-empty, if ``state.image_folder``
       is set, writes it as a per-folder override for that folder so re-opening
       that folder still uses the old path.
    3. Clears the ``legacy_*`` attributes on the Preferences instance so
       subsequent ``to_dict()`` calls don't keep echoing them.

    Returns ``True`` if any changes were made (the caller should persist
    Preferences + AppState).
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
            state.update_overrides(folder, labels_dir=prefs.legacy_labels_dir)
        prefs.legacy_labels_dir = ""
        changed = True

    if prefs.legacy_classes_path:
        if folder:
            state.update_overrides(
                folder,
                classes_mode="custom",
                classes_path=prefs.legacy_classes_path,
            )
        prefs.legacy_classes_path = ""
        changed = True

    if prefs.legacy_source_dir:
        # Just drop it — no longer used anywhere.
        prefs.legacy_source_dir = ""
        changed = True

    return changed
