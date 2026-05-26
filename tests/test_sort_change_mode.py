"""Tests for ``MainWindow.open_image_folder(sort_change_mode=...)``.

Covers the "tail-freeze" behavior: after a sort change, callers can ask the
main window to keep the prefix [0:current_index] in the user's original
traversal order and only re-sort what comes after.
"""

from __future__ import annotations

import os
import pytest

# Run headless on hosts without an X server.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402  (after env var)

from magpie.config import AppState, Preferences  # noqa: E402
from magpie.models import Category, CategoryPreset  # noqa: E402
from magpie.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_prefs() -> Preferences:
    prefs = Preferences.default()
    prefs.category_presets = [
        CategoryPreset(
            id="default", name="默认",
            categories=[
                Category(key="1", folder_name="ok", display_name="OK"),
            ],
        )
    ]
    prefs.active_category_preset = "default"
    return prefs


def _make_files(tmp_path, names: list[str]) -> None:
    for name in names:
        (tmp_path / name).write_bytes(b"")


def test_tail_mode_keeps_prefix_then_resorts_remainder(qapp, tmp_path):
    """Open folder with one sort, advance cursor, then reopen with a new
    sort using sort_change_mode='tail'. The prefix should keep its original
    order; the tail should be in the new sort order."""
    _make_files(tmp_path, ["c.jpg", "a.jpg", "e.jpg", "b.jpg", "d.jpg"])

    prefs = _make_prefs()
    # Start with name-asc: [a, b, c, d, e]
    prefs.active_sort_preset_id = "builtin:name"
    prefs.sort_descending = False

    state = AppState()
    win = MainWindow(preferences=prefs, state=state)
    win.open_image_folder(str(tmp_path), reset_index=True)
    assert [p.name for p in win.image_files] == [
        "a.jpg", "b.jpg", "c.jpg", "d.jpg", "e.jpg",
    ]
    # Pretend the user paged through a, b, c — cursor now at index 3.
    win.current_index = 3

    # Switch sort to name-DESC. Old order was a→b→c→d→e; the prefix a,b,c
    # was visited and must be preserved. Tail re-sort of {d, e} in descending
    # → e, d. So final list: a, b, c, e, d.
    prefs.sort_descending = True
    win.open_image_folder(str(tmp_path), reset_index=False, sort_change_mode="tail")

    assert [p.name for p in win.image_files] == [
        "a.jpg", "b.jpg", "c.jpg", "e.jpg", "d.jpg",
    ]
    # Cursor at the prefix/tail boundary.
    assert win.current_index == 3


def test_full_mode_resets_cursor_to_zero(qapp, tmp_path):
    _make_files(tmp_path, ["a.jpg", "b.jpg", "c.jpg"])
    prefs = _make_prefs()
    prefs.active_sort_preset_id = "builtin:name"

    state = AppState()
    win = MainWindow(preferences=prefs, state=state)
    win.open_image_folder(str(tmp_path), reset_index=True)
    win.current_index = 2

    prefs.sort_descending = True
    win.open_image_folder(str(tmp_path), reset_index=False, sort_change_mode="full")

    assert [p.name for p in win.image_files] == ["c.jpg", "b.jpg", "a.jpg"]
    assert win.current_index == 0


def test_tail_mode_drops_prefix_entries_that_disappeared(qapp, tmp_path):
    """If a file in the prefix was removed from disk (e.g., MOVE-classified),
    tail mode should silently drop it from the rebuilt prefix."""
    _make_files(tmp_path, ["a.jpg", "b.jpg", "c.jpg", "d.jpg"])
    prefs = _make_prefs()
    prefs.active_sort_preset_id = "builtin:name"

    state = AppState()
    win = MainWindow(preferences=prefs, state=state)
    win.open_image_folder(str(tmp_path), reset_index=True)
    assert [p.name for p in win.image_files] == ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]
    win.current_index = 2  # prefix = [a, b]

    # Simulate "a.jpg" being moved out before we resort.
    (tmp_path / "a.jpg").unlink()

    prefs.sort_descending = True
    win.open_image_folder(str(tmp_path), reset_index=False, sort_change_mode="tail")

    # Prefix shrinks to just [b]; tail = {c, d} re-sorted desc → [d, c].
    assert [p.name for p in win.image_files] == ["b.jpg", "d.jpg", "c.jpg"]
    # Boundary still uses original prefix length (2), clamped to list length.
    # New list length is 3, so 2 is fine.
    assert win.current_index == 2


def test_tail_mode_with_zero_index_acts_like_full(qapp, tmp_path):
    _make_files(tmp_path, ["a.jpg", "b.jpg", "c.jpg"])
    prefs = _make_prefs()
    prefs.active_sort_preset_id = "builtin:name"

    state = AppState()
    win = MainWindow(preferences=prefs, state=state)
    win.open_image_folder(str(tmp_path), reset_index=True)
    # cursor never moved past 0
    assert win.current_index == 0

    prefs.sort_descending = True
    win.open_image_folder(str(tmp_path), reset_index=False, sort_change_mode="tail")

    # No prefix to keep → entire list is just the new sort.
    assert [p.name for p in win.image_files] == ["c.jpg", "b.jpg", "a.jpg"]
    assert win.current_index == 0
