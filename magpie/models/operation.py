from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OperationKind(str, Enum):
    COPY = "copy"
    MOVE = "move"


@dataclass(slots=True)
class Operation:
    source_path: Path
    target_path: Path
    category_folder: str
    index: int
    kind: OperationKind
