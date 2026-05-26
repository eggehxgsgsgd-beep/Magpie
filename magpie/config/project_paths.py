"""Output-directory template resolution.

Labels and classes resolution lives in ``preset_resolution.py``. This module
keeps the output-template resolver (template + placeholders → concrete Path)
and the ``ProjectPathError`` raised for malformed templates.
"""

from __future__ import annotations

import os
from pathlib import Path

from .preferences import Preferences


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
    except Exception as exc:  # noqa: BLE001
        raise ProjectPathError(f"输出目录模板无效：{exc}") from exc
    if not rendered.strip():
        raise ProjectPathError("输出目录模板渲染为空字符串")
    return Path(os.path.normpath(rendered)).expanduser()
