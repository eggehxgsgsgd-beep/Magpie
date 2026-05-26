from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .category import Category


@dataclass(slots=True)
class CategoryPreset:
    """A named set of categories.

    Multiple presets allow switching between e.g. "OK/NG" and "5 grade quality"
    classifiers. Exactly one is active globally (no per-project override).
    """

    id: str
    name: str
    categories: list[Category] = field(default_factory=list)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:8]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "categories": [c.to_dict() for c in self.categories],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CategoryPreset":
        preset_id = str(data.get("id") or "").strip() or cls.new_id()
        return cls(
            id=preset_id,
            name=str(data.get("name") or "").strip() or "未命名方案",
            categories=[
                Category.from_dict(item) for item in (data.get("categories") or [])
            ],
        )
