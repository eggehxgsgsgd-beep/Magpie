from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class CustomSortPreset:
    """A user-defined Python expression used as a sort key."""

    id: str
    name: str
    expression: str

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:8]

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "expression": self.expression}

    @classmethod
    def from_dict(cls, data: dict) -> "CustomSortPreset":
        preset_id = str(data.get("id") or "").strip() or cls.new_id()
        return cls(
            id=preset_id,
            name=str(data.get("name") or "").strip() or "未命名方案",
            expression=str(data.get("expression") or ""),
        )
