from __future__ import annotations

import json
from pathlib import Path

import pytest

from magpie.config import (
    AppState,
    Preferences,
    ProjectPathError,
    migrate_legacy_paths,
    resolve_active_categories,
    resolve_active_sort,
    resolve_class_names,
    resolve_labels_dir,
    resolve_output_dir,
)
from magpie.models import Category, CategoryPreset, ClassesPreset, LabelsPreset, SortPreset


# ---- Output template ----

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


# ---- Labels (preset / path / none) ----

def test_labels_default_none(tmp_path: Path) -> None:
    prefs = Preferences.default()
    assert resolve_labels_dir(prefs, {}, tmp_path) is None


def test_labels_preset_relative(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_presets = [LabelsPreset(id="a", name="本地", path="labels")]
    prefs.default_labels_selection = "preset:a"
    folder = tmp_path / "cats"
    assert resolve_labels_dir(prefs, {}, folder) == Path(str(folder / "labels"))


def test_labels_preset_with_parent_ref(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_presets = [LabelsPreset(id="a", name="共享", path="../shared/labels")]
    prefs.default_labels_selection = "preset:a"
    folder = tmp_path / "cats"
    expected = Path(str((tmp_path / "shared" / "labels")))
    assert resolve_labels_dir(prefs, {}, folder) == expected


def test_labels_override_path_wins(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_presets = [LabelsPreset(id="a", name="本地", path="labels")]
    prefs.default_labels_selection = "preset:a"
    folder = tmp_path / "cats"
    out = resolve_labels_dir(
        prefs, {"labels_selection": "path:/abs/elsewhere"}, folder
    )
    assert out == Path("/abs/elsewhere")


def test_labels_override_none(tmp_path: Path) -> None:
    prefs = Preferences.default()
    prefs.labels_presets = [LabelsPreset(id="a", name="本地", path="labels")]
    prefs.default_labels_selection = "preset:a"
    out = resolve_labels_dir(prefs, {"labels_selection": "none"}, tmp_path)
    assert out is None


# ---- Class names (preset / none, NO auto, NO file mode) ----

def test_class_names_default_none() -> None:
    prefs = Preferences.default()
    assert resolve_class_names(prefs, {}) == []


def test_class_names_preset_returns_inline() -> None:
    prefs = Preferences.default()
    prefs.classes_presets = [ClassesPreset(id="x", name="C", names=["cat", "dog"])]
    prefs.default_classes_selection = "preset:x"
    assert resolve_class_names(prefs, {}) == ["cat", "dog"]


def test_class_names_override_wins() -> None:
    prefs = Preferences.default()
    prefs.classes_presets = [
        ClassesPreset(id="a", name="A", names=["one"]),
        ClassesPreset(id="b", name="B", names=["two", "three"]),
    ]
    prefs.default_classes_selection = "preset:a"
    assert resolve_class_names(prefs, {"classes_selection": "preset:b"}) == ["two", "three"]


def test_class_names_unknown_preset_falls_back_to_empty() -> None:
    prefs = Preferences.default()
    assert resolve_class_names(prefs, {"classes_selection": "preset:nope"}) == []


# ---- Active categories ----

def test_active_categories_default_empty() -> None:
    prefs = Preferences.default()
    assert resolve_active_categories(prefs) == []


def test_active_categories_picks_active_preset() -> None:
    prefs = Preferences.default()
    prefs.category_presets = [
        CategoryPreset(id="a", name="A", categories=[Category(key="1", folder_name="ok", display_name="OK")]),
        CategoryPreset(id="b", name="B", categories=[Category(key="2", folder_name="ng", display_name="NG")]),
    ]
    prefs.active_category_preset = "b"
    cats = resolve_active_categories(prefs)
    assert [c.folder_name for c in cats] == ["ng"]


def test_active_categories_falls_back_to_first_when_active_missing() -> None:
    prefs = Preferences.default()
    prefs.category_presets = [
        CategoryPreset(id="a", name="A", categories=[Category(key="1", folder_name="ok", display_name="OK")])
    ]
    prefs.active_category_preset = "does-not-exist"
    cats = resolve_active_categories(prefs)
    assert [c.folder_name for c in cats] == ["ok"]


# ---- Active sort ----

def test_active_sort_returns_builtin_by_default() -> None:
    prefs = Preferences.default()
    preset, desc = resolve_active_sort(prefs, {})
    assert preset.id == "builtin:natural"
    assert desc is False


def test_active_sort_override_changes_preset_and_direction() -> None:
    prefs = Preferences.default()
    overrides = {"sort_preset_id": "builtin:mtime", "sort_descending": True}
    preset, desc = resolve_active_sort(prefs, overrides)
    assert preset.id == "builtin:mtime"
    assert desc is True


def test_active_sort_unknown_falls_back_to_natural() -> None:
    prefs = Preferences.default()
    prefs.active_sort_preset_id = "does-not-exist"
    preset, _ = resolve_active_sort(prefs, {})
    assert preset.id == "builtin:natural"


def test_active_sort_resolves_custom_preset() -> None:
    prefs = Preferences.default()
    prefs.sort_presets.append(SortPreset(id="c1", name="C1", kind="custom", expression="name"))
    prefs.active_sort_preset_id = "c1"
    preset, _ = resolve_active_sort(prefs, {})
    assert preset.id == "c1"
    assert preset.kind == "custom"


# ---- Legacy migration ----

def test_legacy_paths_migrate_into_overrides(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    path.write_text(
        json.dumps(
            {
                "source_dir": "/old/source",
                "output_dir": "/old/output",
                "labels_dir": "/old/labels",
                "classes_mode": "custom",
                "classes_path": "/nonexistent/classes.txt",
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
        "labels_selection": "path:/old/labels",
        "classes_selection": "preset:legacy",
    }
    assert prefs.legacy_source_dir == ""
    assert prefs.legacy_output_dir == ""
    assert prefs.legacy_labels_dir == ""
    assert prefs.legacy_classes_path == ""


def test_migration_is_noop_when_clean() -> None:
    prefs = Preferences.default()
    state = AppState()
    assert migrate_legacy_paths(prefs, state) is False


def test_preferences_roundtrip_drops_legacy_keys(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    prefs = Preferences.default()
    prefs.save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "source_dir" not in raw
    assert "output_dir" not in raw
    assert "labels_dir" not in raw
    assert "classes_path" not in raw or raw["classes_path"] == ""
    assert raw["output_dir_template"] == "{parent}/{name}_filtered"
    assert raw["default_labels_selection"] == "none"
    assert raw["default_classes_selection"] == "none"
    assert raw["active_sort_preset_id"] == "builtin:natural"
