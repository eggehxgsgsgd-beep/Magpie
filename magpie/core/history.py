from __future__ import annotations

from collections import deque

from magpie.models import Operation


class OperationHistory:
    def __init__(self, limit: int = 100):
        self.undo_stack: deque[Operation] = deque(maxlen=limit)
        self.redo_stack: deque[Operation] = deque(maxlen=limit)

    def push(self, operation: Operation) -> None:
        self.undo_stack.append(operation)
        self.redo_stack.clear()

    def pop_undo(self) -> Operation | None:
        if not self.undo_stack:
            return None
        operation = self.undo_stack.pop()
        self.redo_stack.append(operation)
        return operation

    def pop_redo(self) -> Operation | None:
        if not self.redo_stack:
            return None
        operation = self.redo_stack.pop()
        self.undo_stack.append(operation)
        return operation

    def clear(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()

    @property
    def undo_count(self) -> int:
        return len(self.undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self.redo_stack)
