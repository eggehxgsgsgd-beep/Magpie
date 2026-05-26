from __future__ import annotations

from pathlib import Path

import pytest

from magpie.config import Preferences
from magpie.core import CustomSortError, compile_custom_sort_key, list_image_files
from magpie.models import BUILTIN_SORT_PRESETS, SortPreset


def _custom_preset(expression: str, name: str = "p") -> SortPreset:
    return SortPreset(id=SortPreset.new_id(), name=name, kind="custom", expression=expression)


def _builtin(field: str) -> SortPreset:
    for p in BUILTIN_SORT_PRESETS:
        if p.field == field:
            return SortPreset(id=p.id, name=p.name, kind=p.kind, field=p.field)
    raise AssertionError(f"unknown builtin field {field}")


def test_custom_sort_natural_digits(tmp_path: Path) -> None:
    for name in ["frame_10.jpg", "frame_2.jpg", "frame_001.jpg"]:
        (tmp_path / name).write_bytes(b"")
    preset = _custom_preset("int(re.search(r'\\d+', stem).group())")
    files = list_image_files(tmp_path, extensions=["jpg"], sort_preset=preset)
    assert [p.name for p in files] == ["frame_001.jpg", "frame_2.jpg", "frame_10.jpg"]


def test_custom_sort_by_suffix_then_name(tmp_path: Path) -> None:
    for name in ["b.png", "a.jpg", "c.png", "d.jpg"]:
        (tmp_path / name).write_bytes(b"")
    preset = _custom_preset("(suffix, name)")
    files = list_image_files(tmp_path, extensions=["jpg", "png"], sort_preset=preset)
    assert [p.name for p in files] == ["a.jpg", "d.jpg", "b.png", "c.png"]


def test_custom_sort_empty_expression_raises(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"")
    preset = _custom_preset("")
    with pytest.raises(CustomSortError):
        list_image_files(tmp_path, extensions=["jpg"], sort_preset=preset)


def test_compile_empty_raises() -> None:
    with pytest.raises(CustomSortError):
        compile_custom_sort_key("")


def test_compile_syntax_error_raises() -> None:
    with pytest.raises(CustomSortError) as excinfo:
        compile_custom_sort_key("int(")
    assert "语法错误" in str(excinfo.value)


def test_sandbox_blocks_import() -> None:
    key_fn = compile_custom_sort_key("__import__('os').getcwd()")
    with pytest.raises(NameError):
        key_fn(Path("anything.jpg"))


def test_sandbox_blocks_open() -> None:
    key_fn = compile_custom_sort_key("open('/etc/passwd').read()")
    with pytest.raises(NameError):
        key_fn(Path("anything.jpg"))


def test_sort_descending_reverses_built_in_fields(tmp_path: Path) -> None:
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        (tmp_path / name).write_bytes(b"")
    asc = list_image_files(tmp_path, extensions=["jpg"], sort_preset=_builtin("name"))
    desc = list_image_files(
        tmp_path, extensions=["jpg"], sort_preset=_builtin("name"), sort_descending=True,
    )
    assert [p.name for p in asc] == ["a.jpg", "b.jpg", "c.jpg"]
    assert [p.name for p in desc] == ["c.jpg", "b.jpg", "a.jpg"]


def test_sort_descending_works_with_custom(tmp_path: Path) -> None:
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        (tmp_path / name).write_bytes(b"")
    preset = _custom_preset("name")
    desc = list_image_files(
        tmp_path, extensions=["jpg"], sort_preset=preset, sort_descending=True,
    )
    assert [p.name for p in desc] == ["c.jpg", "b.jpg", "a.jpg"]


def test_legacy_sort_strategy_migrates_in_preferences(tmp_path: Path) -> None:
    import json
    path = tmp_path / "preferences.json"
    for legacy, expected in [
        ("name_desc", ("builtin:name", True)),
        ("mtime_asc", ("builtin:mtime", False)),
        ("size_desc", ("builtin:name", True)),
        ("natural", ("builtin:natural", False)),
    ]:
        path.write_text(json.dumps({"sort_strategy": legacy}), encoding="utf-8")
        prefs = Preferences.load(path)
        assert (prefs.active_sort_preset_id, prefs.sort_descending) == expected


def test_legacy_custom_sort_expr_migrates(tmp_path: Path) -> None:
    import json
    path = tmp_path / "preferences.json"
    path.write_text(
        json.dumps({"sort_strategy": "custom", "custom_sort_expr": "name.lower()"}),
        encoding="utf-8",
    )
    prefs = Preferences.load(path)
    assert prefs.active_sort_preset_id == "legacy"
    legacy_preset = next(p for p in prefs.sort_presets if p.id == "legacy")
    assert legacy_preset.expression == "name.lower()"


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

    preset = _custom_preset("mtime")
    files = list_image_files(tmp_path, extensions=["jpg"], sort_preset=preset)
    assert [p.name for p in files] == ["older.jpg", "newer.jpg"]
