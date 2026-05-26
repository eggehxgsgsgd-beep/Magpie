from __future__ import annotations

from collections import deque

from magpie.models import Operation


class OperationHistory:
    """Undo stack for classify operations.

    Redo was intentionally removed: in this app each new classify wipes the
    redo path anyway, so the redo button was almost always either greyed out
    or one keystroke away from being re-applied by hand. See
    plans/memoized-seeking-sedgewick.md for the rationale.
    """

    def __init__(self, limit: int = 100):
        self.undo_stack: deque[Operation] = deque(maxlen=limit)

    def push(self, operation: Operation) -> None:
        self.undo_stack.append(operation)

    def pop_undo(self) -> Operation | None:
        if not self.undo_stack:
            return None
        return self.undo_stack.pop()

    def clear(self) -> None:
        self.undo_stack.clear()

    @property
    def undo_count(self) -> int:
        return len(self.undo_stack)
