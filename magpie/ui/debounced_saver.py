"""QTimer-backed debounced saver.

Use cases:
- ClassificationRecord — every 1/2/3 keypress mutates the dict; we don't want
  to fsync JSON on every press.
- AppState — current_index / per_folder_overrides should survive a crash, but
  hammering disk on every navigation is wasteful.

Pattern:

    saver = DebouncedSaver(record.save, interval_ms=500)
    record.set_dirty_callback(saver.request)
    # ... user classifies many images in a row ...
    saver.flush()  # call on closeEvent so nothing's lost
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, QTimer


class DebouncedSaver(QObject):
    """Coalesce frequent save requests into one disk write per idle window."""

    def __init__(
        self,
        save_fn: Callable[[], None],
        interval_ms: int = 500,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._save_fn = save_fn
        self._pending = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._fire)

    def request(self) -> None:
        """Mark dirty; if no save is queued, schedule one after the idle window."""
        self._pending = True
        self._timer.start()  # restarts the countdown if already running

    def flush(self) -> None:
        """Run any pending save right now (call from closeEvent)."""
        if self._pending:
            self._timer.stop()
            self._pending = False
            self._save_fn()

    def _fire(self) -> None:
        if self._pending:
            self._pending = False
            self._save_fn()
