from __future__ import annotations

import json
from pathlib import Path

import pytest

from magpie.config import (
    AppState,
    Preferences,
    ProjectPathError,
    migrate_legacy_paths,
    resolve_classes_path,
    resolve_labels_dir,
    resolve_output_dir,
)


def test_output_default_template_renders_sibling_filtered(tmp_path: Path) -> None:
    prefs = Preferences.default()
    folder = tmp_path / "cats"
    folder.mkdir()
    out = resolve_output_dir(prefs, {}, folder)
    assert out == tmp_path / "cats_filtered"


def test_output_template_with_folder_placeholder(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.output_dir_template = "{folder}/__out__"
    folder = tmp_path / "dogs"
    folder.mkdir()
    out = resolve_output_dir(prefs, {}, folder)
    assert out == tmp_path / "dogs" / "__out__"


def test_output_template_with_unknown_placeholder_raises(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.output_dir_template = "{nope}/x"
    with pytest.raises(ProjectPathError):
        resolve_output_dir(prefs, {}, tmp_path)


def test_output_override_wins(tmp_path: Path) -> None:
    prefs = Preferences.default()
    overrides = {"output_dir": str(tmp_path / "explicit")}
    out = resolve_output_dir(prefs, overrides, tmp_path / "cats")
    assert out == tmp_path / "explicit"


def test_labels_relative_to_folder(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_dir_relative = "labels"
    folder = tmp_path / "cats"
    folder.mkdir()
    labels = resolve_labels_dir(prefs, {}, folder)
    assert labels == (folder / "labels").resolve()


def test_labels_relative_parent_ref(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_dir_relative = "../shared/labels"
    folder = tmp_path / "cats"
    folder.mkdir()
    labels = resolve_labels_dir(prefs, {}, folder)
    assert labels == (tmp_path / "shared" / "labels").resolve()


def test_labels_empty_returns_none(tmp_path: Path) -> None:
    prefs = Preferences.default()
    assert resolve_labels_dir(prefs, {}, tmp_path) is None


def test_labels_override_absolute(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_dir_relative = "labels"  # ignored when override present
    overrides = {"labels_dir": str(tmp_path / "elsewhere")}
    assert resolve_labels_dir(prefs, overrides, tmp_path / "cats") == (
        tmp_path / "elsewhere"
    )


def test_classes_auto_returns_path_even_if_missing(tmp_path: Path) -> None:
    prefs = Preferences.default()  # classes_mode == "auto"
    labels = tmp_path / "labels"
    # Caller will warn the user; the resolver itself does not check existence.
    assert resolve_classes_path(prefs, {}, labels) == labels / "classes.txt"


def test_classes_auto_no_labels_returns_none() -> None:
    prefs = Preferences.default()
    assert resolve_classes_path(prefs, {}, None) is None


def test_classes_custom_returns_path() -> None:
    prefs = Preferences.default()
    prefs.classes_mode = "custom"
    prefs.classes_path = "/abs/classes.txt"
    assert resolve_classes_path(prefs, {}, None) == Path("/abs/classes.txt")


def test_classes_override_mode_custom_wins_over_global_auto() -> None:
    prefs = Preferences.default()  # auto
    overrides = {"classes_mode": "custom", "classes_path": "/a.txt"}
    assert resolve_classes_path(prefs, overrides, None) == Path("/a.txt")


def test_legacy_paths_migrate_into_overrides(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    path.write_text(
        json.dumps(
            {
                "source_dir": "/old/source",
                "output_dir": "/old/output",
                "labels_dir": "/old/labels",
                "classes_path": "/old/classes.txt",
            }
        ),
        encoding="utf-8",
    )
    prefs = Preferences.load(path)
    state = AppState(image_folder="/data/legacy")
    changed = migrate_legacy_paths(prefs, state)
    assert changed
    overrides = state.overrides_for("/data/legacy")
    assert overrides == {
        "output_dir": "/old/output",
        "labels_dir": "/old/labels",
        "classes_mode": "custom",
        "classes_path": "/old/classes.txt",
    }
    # Legacy fields cleared so future to_dict doesn't echo them.
    assert prefs.legacy_source_dir == ""
    assert prefs.legacy_output_dir == ""
    assert prefs.legacy_labels_dir == ""
    assert prefs.legacy_classes_path == ""


def test_migration_is_noop_when_clean() -> None:
    prefs = Preferences.default()
    state = AppState()
    assert migrate_legacy_paths(prefs, state) is False


def test_preferences_roundtrip_drops_legacy_keys(tmp_path: Path) -> None:
    # After saving a fresh Preferences, the JSON should not contain source_dir/
    # output_dir/labels_dir (only the new template fields).
    path = tmp_path / "preferences.json"
    prefs = Preferences.default()
    prefs.save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "source_dir" not in raw
    assert "output_dir" not in raw
    assert "labels_dir" not in raw
    assert raw["output_dir_template"] == "{parent}/{name}_filtered"
    assert raw["labels_dir_relative"] == ""
    assert raw["classes_mode"] == "auto"
