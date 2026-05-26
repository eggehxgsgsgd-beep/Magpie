"""Per-source-folder classification ledger.

Schema v2: ``entries`` is keyed by the image's POSIX relative path from the
source folder (so ``subA/0001.jpg`` and ``subB/0001.jpg`` don't collide under
recursive scans). For non-recursive folders the key is just the file name —
identical-looking to v1 — but the key space is now path-aware.

v1 files (basename-keyed) are dropped on load: they're ambiguous for
recursive datasets, and trying to migrate without knowing the historical
list of files is unsafe.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from .paths import classifications_dir


SCHEMA_VERSION = 2


def record_path_for_source(source_folder: str | Path) -> Path:
    source = str(Path(source_folder).resolve())
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return classifications_dir() / f"{digest}.json"


def image_key(image_path: str | Path, source_folder: str | Path) -> str:
    """Return the POSIX relative-path key used to address an image in the
    record. Falls back to the basename if ``image_path`` is not under
    ``source_folder`` (shouldn't happen in normal flow, but be robust)."""
    img = Path(image_path)
    src = Path(source_folder)
    try:
        rel = img.relative_to(src)
    except ValueError:
        return img.name
    return rel.as_posix()


@dataclass
class ClassificationRecord:
    source_folder: str
    entries: dict[str, list[str]] = field(default_factory=dict)
    path: Path | None = None
    # Optional callback invoked whenever entries change. Main window wires
    # this to a debounced disk writer (no per-keystroke I/O).
    _on_dirty: Callable[[], None] | None = field(default=None, repr=False)

    @classmethod
    def load(cls, source_folder: str | Path) -> "ClassificationRecord":
        source = str(Path(source_folder).resolve())
        path = record_path_for_source(source)
        if not path.exists():
            return cls(source_folder=source, path=path)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            version = int(data.get("schema_version", 1))
            if version != SCHEMA_VERSION:
                # Old basename-keyed file; drop the entries (lookups would
                # silently miss under the new path-keyed scheme).
                print(
                    f"[classification_record] dropping legacy v{version} record at {path}; "
                    "entries will rebuild as you classify."
                )
                return cls(source_folder=source, path=path)
            entries = {
                str(name): [str(category) for category in categories]
                for name, categories in data.get("entries", {}).items()
                if isinstance(categories, list)
            }
            return cls(
                source_folder=str(data.get("source_folder") or source),
                entries=entries,
                path=path,
            )
        except Exception as exc:
            print(f"Failed to load classification record, using empty record: {exc}")
            return cls(source_folder=source, path=path)

    def set_dirty_callback(self, fn: Callable[[], None] | None) -> None:
        """Install a callback called whenever the record is mutated.

        Used by main window to debounce disk writes — instead of every
        ``add()/remove()`` synchronously writing JSON, the callback nudges
        a ``QTimer`` that flushes after a short idle period.
        """
        self._on_dirty = fn

    def save(self) -> None:
        path = self.path or record_path_for_source(self.source_folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_folder": self.source_folder,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "entries": self.entries,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.path = path

    def _mark_dirty(self) -> None:
        if self._on_dirty is not None:
            self._on_dirty()
        else:
            self.save()

    def add(self, key: str, category_folder: str) -> None:
        categories = self.entries.setdefault(key, [])
        if category_folder not in categories:
            categories.append(category_folder)
        self._mark_dirty()

    def remove(self, key: str, category_folder: str) -> None:
        categories = self.entries.get(key)
        if not categories:
            return
        if category_folder in categories:
            categories.remove(category_folder)
        if not categories:
            self.entries.pop(key, None)
        self._mark_dirty()

    def labels_for(self, key: str) -> list[str]:
        return self.entries.get(key, [])

    def count_for_category(self, category_folder: str) -> int:
        return sum(1 for categories in self.entries.values() if category_folder in categories)

    def classified_image_count(self) -> int:
        return len(self.entries)

    def clear(self) -> None:
        self.entries.clear()
        if self.path and self.path.exists():
            self.path.unlink()
