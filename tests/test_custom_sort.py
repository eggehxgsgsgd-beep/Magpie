from __future__ import annotations

import json
from pathlib import Path

import pytest

from magpie.config import Preferences
from magpie.core import CustomSortError, compile_custom_sort_key, list_image_files
from magpie.models import CustomSortPreset


def _make_preset(preset_id: str, expression: str, name: str = "preset") -> CustomSortPreset:
    return CustomSortPreset(id=preset_id, name=name, expression=expression)


def test_custom_sort_natural_digits(tmp_path: Path) -> None:
    for name in ["frame_10.jpg", "frame_2.jpg", "frame_001.jpg"]:
        (tmp_path / name).write_bytes(b"")

    preset = _make_preset("p1", "int(re.search(r'\\d+', stem).group())")
    files = list_image_files(
        tmp_path,
        extensions=["jpg"],
        sort_strategy="custom:p1",
        custom_sort_presets=[preset],
    )
    assert [p.name for p in files] == ["frame_001.jpg", "frame_2.jpg", "frame_10.jpg"]


def test_sort_descending_reverses_built_in_fields(tmp_path: Path) -> None:
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        (tmp_path / name).write_bytes(b"")
    asc = list_image_files(tmp_path, extensions=["jpg"], sort_strategy="name")
    desc = list_image_files(
        tmp_path, extensions=["jpg"], sort_strategy="name", sort_descending=True,
    )
    assert [p.name for p in asc] == ["a.jpg", "b.jpg", "c.jpg"]
    assert [p.name for p in desc] == ["c.jpg", "b.jpg", "a.jpg"]


def test_sort_descending_works_with_custom(tmp_path: Path) -> None:
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        (tmp_path / name).write_bytes(b"")
    preset = _make_preset("p", "name")
    desc = list_image_files(
        tmp_path,
        extensions=["jpg"],
        sort_strategy="custom:p",
        custom_sort_presets=[preset],
        sort_descending=True,
    )
    assert [p.name for p in desc] == ["c.jpg", "b.jpg", "a.jpg"]


def test_legacy_sort_strategy_migrates_in_preferences(tmp_path: Path) -> None:
    from magpie.config import Preferences
    import json
    path = tmp_path / "preferences.json"
    # Old "name_desc" should split into ("name", True). "size_*" falls back to name.
    for legacy, expected in [
        ("name_desc", ("name", True)),
        ("mtime_asc", ("mtime", False)),
        ("size_desc", ("name", True)),
        ("natural", ("natural", False)),
    ]:
        path.write_text(json.dumps({"sort_strategy": legacy}), encoding="utf-8")
        prefs = Preferences.load(path)
        assert (prefs.sort_strategy, prefs.sort_descending) == expected


def test_custom_sort_by_suffix_then_name(tmp_path: Path) -> None:
    for name in ["b.png", "a.jpg", "c.png", "d.jpg"]:
        (tmp_path / name).write_bytes(b"")

    preset = _make_preset("p2", "(suffix, name)")
    files = list_image_files(
        tmp_path,
        extensions=["jpg", "png"],
        sort_strategy="custom:p2",
        custom_sort_presets=[preset],
    )
    assert [p.name for p in files] == ["a.jpg", "d.jpg", "b.png", "c.png"]


def test_unknown_preset_id_raises(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"")
    with pytest.raises(CustomSortError) as excinfo:
        list_image_files(
            tmp_path,
            extensions=["jpg"],
            sort_strategy="custom:does_not_exist",
            custom_sort_presets=[],
        )
    assert "does_not_exist" in str(excinfo.value)


def test_custom_sort_empty_expression_raises() -> None:
    with pytest.raises(CustomSortError):
        compile_custom_sort_key("")


def test_custom_sort_syntax_error_raises() -> None:
    with pytest.raises(CustomSortError) as excinfo:
        compile_custom_sort_key("int(")
    assert "语法错误" in str(excinfo.value)


def test_custom_sort_sandbox_blocks_import() -> None:
    key_fn = compile_custom_sort_key("__import__('os').getcwd()")
    with pytest.raises(NameError):
        key_fn(Path("anything.jpg"))


def test_custom_sort_sandbox_blocks_open() -> None:
    key_fn = compile_custom_sort_key("open('/etc/passwd').read()")
    with pytest.raises(NameError):
        key_fn(Path("anything.jpg"))


def test_legacy_custom_sort_expr_migrates(tmp_path: Path) -> None:
    """Preferences saved with the old custom_sort_expr field should migrate
    into a single CustomSortPreset with id='legacy'."""
    legacy_path = tmp_path / "preferences.json"
    legacy_path.write_text(
        json.dumps(
            {
                "sort_strategy": "custom",
                "custom_sort_expr": "name.lower()",
            }
        ),
        encoding="utf-8",
    )
    prefs = Preferences.load(legacy_path)
    assert prefs.sort_strategy == "custom:legacy"
    assert len(prefs.custom_sort_presets) == 1
    assert prefs.custom_sort_presets[0].id == "legacy"
    assert prefs.custom_sort_presets[0].expression == "name.lower()"


def test_preferences_roundtrip_with_presets(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    prefs = Preferences.default()
    prefs.custom_sort_presets = [
        CustomSortPreset(id="abc", name="按数字", expression="int(stem)"),
        CustomSortPreset(id="def", name="按时间", expression="mtime"),
    ]
    prefs.sort_strategy = "custom:def"
    prefs.save(path)

    loaded = Preferences.load(path)
    assert loaded.sort_strategy == "custom:def"
    assert [p.id for p in loaded.custom_sort_presets] == ["abc", "def"]
    assert loaded.custom_sort_presets[0].name == "按数字"


def test_custom_sort_can_use_mtime(tmp_path: Path) -> None:
    import os
    import time

    older = tmp_path / "older.jpg"
    newer = tmp_path / "newer.jpg"
    older.write_bytes(b"")
    newer.write_bytes(b"")
    now = time.time()
    os.utime(older, (now - 1000, now - 1000))
    os.utime(newer, (now, now))

    preset = _make_preset("p3", "mtime")
    files = list_image_files(
        tmp_path,
        extensions=["jpg"],
        sort_strategy="custom:p3",
        custom_sort_presets=[preset],
    )
    assert [p.name for p in files] == ["older.jpg", "newer.jpg"]
