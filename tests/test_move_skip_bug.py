"""Regression test for the MOVE-mode classify-skips-one-image bug.

Bug: after `image_files.pop(current_index)`, the slot already holds what
used to be at index+1; calling `next_image()` again advanced past it. Fix
loads the same index instead.
"""

from __future__ import annotations

import os

import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from magpie.config import AppState, Preferences  # noqa: E402
from magpie.models import Category, CategoryPreset, OperationKind  # noqa: E402
from magpie.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_move_classify_does_not_skip(qapp, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for n in ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]:
        Image.new("RGB", (4, 4), (200, 50, 50)).save(src / n)

    prefs = Preferences.default()
    prefs.category_presets = [
        CategoryPreset(
            id="default", name="默认",
            categories=[Category(key="1", folder_name="ok", display_name="OK")],
        )
    ]
    prefs.active_category_preset = "default"
    prefs.default_operation = OperationKind.MOVE
    prefs.output_dir_template = str(tmp_path / "out")

    win = MainWindow(preferences=prefs, state=AppState())
    win.open_image_folder(str(src), reset_index=True)

    assert [p.name for p in win.image_files] == ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]
    assert win.current_index == 0  # showing a.jpg

    # Classify a.jpg → MOVE moves it out of src. We expect the cursor to
    # now be on b.jpg (not c.jpg, which would be the skip-bug behavior).
    win.classify_current_image(prefs.category_presets[0].categories[0])

    assert win.image_files[win.current_index].name == "b.jpg"
    assert "a.jpg" not in [p.name for p in win.image_files]
