from __future__ import annotations

import json

from magpie.config.state import AppState


def test_overrides_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = AppState(image_folder="/data/a", current_index=3)
    state.add_recent_folder("/data/a")
    state.update_overrides(
        "/data/a",
        sort_strategy="name",
        sort_descending=True,
        conflict_strategy="skip",
        recursive_scan=True,
        current_index=42,
    )
    state.save(path)

    loaded = AppState.load(path)
    overrides = loaded.overrides_for("/data/a")
    assert overrides["sort_strategy"] == "name"
    assert overrides["sort_descending"] is True
    assert overrides["conflict_strategy"] == "skip"
    assert overrides["recursive_scan"] is True
    assert overrides["current_index"] == 42


def test_overrides_unknown_folder_returns_empty(tmp_path):
    state = AppState()
    assert state.overrides_for("/no/such") == {}


def test_legacy_sort_value_migrates(tmp_path):
    """Pre-split 'name_desc' / 'mtime_asc' / 'size_*' values stored in
    per_folder_overrides must split into (sort_strategy, sort_descending) on
    load. 'size_*' falls back to name with the same direction."""
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "per_folder_overrides": {
                    "/data/a": {"sort_strategy": "name_desc"},
                    "/data/b": {"sort_strategy": "mtime_asc"},
                    "/data/c": {"sort_strategy": "size_desc"},
                    "/data/d": {"sort_strategy": "natural"},
                    "/data/e": {
                        "sort_strategy": "name",
                        "sort_descending": True,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.overrides_for("/data/a") == {
        "sort_strategy": "name", "sort_descending": True,
    }
    assert loaded.overrides_for("/data/b") == {
        "sort_strategy": "mtime", "sort_descending": False,
    }
    assert loaded.overrides_for("/data/c") == {
        "sort_strategy": "name", "sort_descending": True,
    }
    assert loaded.overrides_for("/data/d") == {
        "sort_strategy": "natural", "sort_descending": False,
    }
    # Already new format: untouched
    assert loaded.overrides_for("/data/e") == {
        "sort_strategy": "name", "sort_descending": True,
    }


def test_overrides_unknown_keys_dropped(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "per_folder_overrides": {
                    "/data/a": {
                        "sort_strategy": "name",
                        "garbage_key": 1,
                    },
                    "not-a-dict": "should-be-skipped",
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.overrides_for("/data/a") == {"sort_strategy": "name"}
    assert "not-a-dict" not in loaded.per_folder_overrides


def test_legacy_state_without_overrides_loads(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "image_folder": "/data/legacy",
                "current_index": 1,
                "recent_folders": ["/data/legacy"],
            }
        ),
        encoding="utf-8",
    )
    loaded = AppState.load(path)
    assert loaded.image_folder == "/data/legacy"
    assert loaded.per_folder_overrides == {}


def test_update_overrides_ignores_none_values():
    state = AppState()
    state.update_overrides("/data/a", sort_strategy="natural", conflict_strategy=None)
    assert state.overrides_for("/data/a") == {"sort_strategy": "natural"}
