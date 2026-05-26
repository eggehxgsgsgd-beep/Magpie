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
