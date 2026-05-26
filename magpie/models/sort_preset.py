from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class SortPreset:
    """A named sort option.

    Two kinds:
    - ``builtin``: id like ``builtin:natural``/``builtin:name``/``builtin:mtime``;
      ``field`` selects the comparator (natural/name/mtime). Always seeded into
      ``Preferences.sort_presets`` by ``Preferences.default()``.
    - ``custom``: id is an 8-char hex; ``expression`` is a Python expression
      evaluated against each file in a sandbox (see
      ``magpie.core.image_loader.compile_custom_sort_key``).
    """

    id: str
    name: str
    kind: str            # "builtin" | "custom"
    field: str = ""      # "natural" | "name" | "mtime" (builtin only)
    expression: str = ""  # python expression (custom only)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:8]

    @property
    def is_builtin(self) -> bool:
        return self.kind == "builtin"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "field": self.field,
            "expression": self.expression,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SortPreset":
        kind = str(data.get("kind") or "").strip()
        # Accept legacy CustomSortPreset payloads (no 'kind' key, has 'expression').
        if not kind:
            kind = "custom"
        preset_id = str(data.get("id") or "").strip() or cls.new_id()
        return cls(
            id=preset_id,
            name=str(data.get("name") or "").strip() or "未命名方案",
            kind=kind if kind in ("builtin", "custom") else "custom",
            field=str(data.get("field") or ""),
            expression=str(data.get("expression") or ""),
        )


# Backward-compatible alias used by callers that haven't been updated yet.
CustomSortPreset = SortPreset


BUILTIN_SORT_PRESETS: tuple[SortPreset, ...] = (
    SortPreset(id="builtin:natural", name="文件名（自然，1, 2, 10）", kind="builtin", field="natural"),
    SortPreset(id="builtin:name", name="文件名（字母序，1, 10, 2）", kind="builtin", field="name"),
    SortPreset(id="builtin:mtime", name="修改时间", kind="builtin", field="mtime"),
)
