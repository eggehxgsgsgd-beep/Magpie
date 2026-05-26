from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(slots=True)
class ClassesPreset:
    """A named list of class names (one per line, à la YOLO classes.txt).

    Inline-only by design: the user pastes the names rather than pointing at a
    file on disk. This keeps the preset self-contained and portable across
    projects/machines.
    """

    id: str
    name: str
    names: list[str] = field(default_factory=list)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:8]

    @classmethod
    def from_text(cls, preset_id: str, name: str, raw_text: str) -> "ClassesPreset":
        """Parse a multi-line text block: one class per line, trimmed, drop empties."""
        names = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return cls(id=preset_id, name=name, names=names)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "names": list(self.names)}

    @classmethod
    def from_dict(cls, data: dict) -> "ClassesPreset":
        preset_id = str(data.get("id") or "").strip() or cls.new_id()
        raw_names = data.get("names") or []
        if not isinstance(raw_names, list):
            raw_names = []
        names = [str(item).strip() for item in raw_names if str(item).strip()]
        return cls(
            id=preset_id,
            name=str(data.get("name") or "").strip() or "未命名方案",
            names=names,
        )
