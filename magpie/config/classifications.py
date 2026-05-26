from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .paths import classifications_dir


def record_path_for_source(source_folder: str | Path) -> Path:
    source = str(Path(source_folder).resolve())
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return classifications_dir() / f"{digest}.json"


@dataclass
class ClassificationRecord:
    source_folder: str
    entries: dict[str, list[str]] = field(default_factory=dict)
    path: Path | None = None

    @classmethod
    def load(cls, source_folder: str | Path) -> "ClassificationRecord":
        source = str(Path(source_folder).resolve())
        path = record_path_for_source(source)
        if not path.exists():
            return cls(source_folder=source, path=path)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = {
                str(name): [str(category) for category in categories]
                for name, categories in data.get("entries", {}).items()
                if isinstance(categories, list)
            }
            return cls(source_folder=str(data.get("source_folder") or source), entries=entries, path=path)
        except Exception as exc:
            print(f"Failed to load classification record, using empty record: {exc}")
            return cls(source_folder=source, path=path)

    def save(self) -> None:
        path = self.path or record_path_for_source(self.source_folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
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

    def add(self, image_name: str, category_folder: str) -> None:
        categories = self.entries.setdefault(image_name, [])
        if category_folder not in categories:
            categories.append(category_folder)
        self.save()

    def remove(self, image_name: str, category_folder: str) -> None:
        categories = self.entries.get(image_name)
        if not categories:
            return
        if category_folder in categories:
            categories.remove(category_folder)
        if not categories:
            self.entries.pop(image_name, None)
        self.save()

    def labels_for(self, image_name: str) -> list[str]:
        return self.entries.get(image_name, [])

    def count_for_category(self, category_folder: str) -> int:
        return sum(1 for categories in self.entries.values() if category_folder in categories)

    def classified_image_count(self) -> int:
        return len(self.entries)

    def clear(self) -> None:
        self.entries.clear()
        if self.path and self.path.exists():
            self.path.unlink()
