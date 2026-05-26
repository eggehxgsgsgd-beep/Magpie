from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class LabelsPreset:
    """A named labels-directory path.

    ``path`` is either absolute or relative to the source folder; resolution
    happens at folder open time in ``magpie.config.preset_resolution``.
    """

    id: str
    name: str
    path: str = ""

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:8]

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "path": self.path}

    @classmethod
    def from_dict(cls, data: dict) -> "LabelsPreset":
        preset_id = str(data.get("id") or "").strip() or cls.new_id()
        return cls(
            id=preset_id,
            name=str(data.get("name") or "").strip() or "未命名方案",
            path=str(data.get("path") or ""),
        )
