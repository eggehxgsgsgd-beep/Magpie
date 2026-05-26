from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from magpie.models import Category, OperationKind

from .paths import preferences_path


DEFAULT_EXTENSIONS = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]
DEFAULT_PALETTE = [
    "#4CAF50",
    "#2196F3",
    "#FF9800",
    "#E91E63",
    "#9C27B0",
    "#00BCD4",
    "#8BC34A",
    "#FFC107",
    "#795548",
    "#607D8B",
    "#F44336",
    "#3F51B5",
]


@dataclass
class Preferences:
    categories: list[Category] = field(default_factory=list)
    source_dir: str = ""
    output_dir: str = ""
    labels_dir: str = ""
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
    sort_strategy: str = "natural"
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
        operation = data.get("default_operation", OperationKind.COPY.value)
        try:
            default_operation = OperationKind(operation)
        except ValueError:
            default_operation = OperationKind.COPY

        return cls(
            categories=[Category.from_dict(item) for item in data.get("categories", [])],
            source_dir=str(data.get("source_dir", "")),
            output_dir=str(data.get("output_dir", "")),
            labels_dir=str(data.get("labels_dir", "")),
            classes_path=str(data.get("classes_path", "")),
            autoplay_interval_ms=int(data.get("autoplay_interval_ms", 100)),
            show_bboxes=bool(data.get("show_bboxes", True)),
            show_classified_marker=bool(data.get("show_classified_marker", True)),
            theme=str(data.get("theme", "system")),
            default_operation=default_operation,
            undo_prompt=bool(data.get("undo_prompt", False)),
            end_behavior=str(data.get("end_behavior", "stay")),
            file_extensions=list(data.get("file_extensions", DEFAULT_EXTENSIONS)),
            conflict_strategy=str(data.get("conflict_strategy", "ask")),
            sort_strategy=str(data.get("sort_strategy", "natural")),
            recursive_scan=bool(data.get("recursive_scan", False)),
            remember_recursive_scan=bool(data.get("remember_recursive_scan", False)),
        )

    def to_dict(self) -> dict:
        return {
            "categories": [category.to_dict() for category in self.categories],
            "source_dir": self.source_dir,
            "output_dir": self.output_dir,
            "labels_dir": self.labels_dir,
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
