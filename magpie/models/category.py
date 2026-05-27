from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    key: str
    folder_name: str
    display_name: str = ""

    @property
    def label(self) -> str:
        return self.display_name or self.folder_name

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "folder_name": self.folder_name,
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        folder_name = str(data.get("folder_name", "")).strip()
        return cls(
            key=str(data.get("key", "")).strip(),
            folder_name=folder_name,
            display_name=str(data.get("display_name") or folder_name).strip(),
        )
