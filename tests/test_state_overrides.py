from __future__ import annotations

import json

from magpie.config.state import AppState


def test_overrides_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = AppState(image_folder="/data/a", current_index=3)
    state.add_recent_folder("/data/a")
    state.update_overrides(
        "/data/a",
        sort_preset_id="builtin:name",
        sort_descending=True,
        labels_selection="preset:lp1",
        classes_selection="preset:cp1",
        conflict_strategy="skip",
        recursive_scan=True,
        current_index=42,
    )
    state.save(path)

    loaded = AppState.load(path)
    overrides = loaded.overrides_for("/data/a")
    assert overrides == {
        "sort_preset_id": "builtin:name",
        "sort_descending": True,
        "labels_selection": "preset:lp1",
        "classes_selection": "preset:cp1",
        "conflict_strategy": "skip",
        "recursive_scan": True,
        "current_index": 42,
    }


def test_overrides_unknown_folder_returns_empty(tmp_path):
    state = AppState()
    assert state.overrides_for("/no/such") == {}


def test_legacy_sort_strategy_migrates(tmp_path):
    """Pre-split 'name_desc' / 'mtime_asc' / 'size_*' values stored in
    per_folder_overrides must split into (sort_preset_id, sort_descending)."""
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "per_folder_overrides": {
                    "/data/a": {"sort_strategy": "name_desc"},
                    "/data/b": {"sort_strategy": "mtime_asc"},
                    "/data/c": {"sort_strategy": "size_desc"},
                    "/data/d": {"sort_strategy": "natural"},
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.overrides_for("/data/a") == {
        "sort_preset_id": "builtin:name", "sort_descending": True,
    }
    assert loaded.overrides_for("/data/b") == {
        "sort_preset_id": "builtin:mtime", "sort_descending": False,
    }
    assert loaded.overrides_for("/data/c") == {
        "sort_preset_id": "builtin:name", "sort_descending": True,
    }
    assert loaded.overrides_for("/data/d") == {
        "sort_preset_id": "builtin:natural", "sort_descending": False,
    }


def test_legacy_labels_dir_migrates_to_path_selection(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "per_folder_overrides": {
                    "/data/a": {"labels_dir": "/abs/labels"},
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.overrides_for("/data/a") == {
        "labels_selection": "path:/abs/labels",
    }


def test_legacy_classes_mode_migrates(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "per_folder_overrides": {
                    "/data/custom": {"classes_mode": "custom", "classes_path": "/abs/c.txt"},
                    "/data/auto": {"classes_mode": "auto"},
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.overrides_for("/data/custom") == {"classes_selection": "preset:legacy"}
    assert loaded.overrides_for("/data/auto") == {"classes_selection": "none"}


def test_overrides_unknown_keys_dropped(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "per_folder_overrides": {
                    "/data/a": {
                        "sort_preset_id": "builtin:name",
                        "garbage_key": 1,
                    },
                    "not-a-dict": "should-be-skipped",
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.overrides_for("/data/a") == {"sort_preset_id": "builtin:name"}
    assert "not-a-dict" not in loaded.per_folder_overrides


def test_update_overrides_ignores_none_values():
    state = AppState()
    state.update_overrides("/data/a", sort_preset_id="builtin:natural", conflict_strategy=None)
    assert state.overrides_for("/data/a") == {"sort_preset_id": "builtin:natural"}
