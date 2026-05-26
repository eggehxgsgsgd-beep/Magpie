from magpie.config import Preferences
from magpie.models import (
    Category,
    CategoryPreset,
    ClassesPreset,
    LabelsPreset,
    OperationKind,
    SortPreset,
)


def test_preferences_round_trip(tmp_path):
    preferences = Preferences(
        category_presets=[
            CategoryPreset(
                id="default",
                name="默认",
                categories=[
                    Category(key="1", folder_name="cat", display_name="cat label", color="#00ff00"),
                ],
            )
        ],
        active_category_preset="default",
        labels_presets=[LabelsPreset(id="lp1", name="本地", path="labels")],
        default_labels_selection="preset:lp1",
        classes_presets=[ClassesPreset(id="cp1", name="COCO", names=["person", "car"])],
        default_classes_selection="preset:cp1",
        sort_presets=[
            SortPreset(id="builtin:natural", name="自然", kind="builtin", field="natural"),
            SortPreset(id="builtin:name", name="字母序", kind="builtin", field="name"),
            SortPreset(id="builtin:mtime", name="修改时间", kind="builtin", field="mtime"),
            SortPreset(id="x1", name="按帧号", kind="custom", expression="int(stem)"),
        ],
        active_sort_preset_id="x1",
        sort_descending=True,
        output_dir_template="{folder}/__out__",
        default_operation=OperationKind.MOVE,
        recursive_scan=True,
        remember_recursive_scan=True,
    )
    path = tmp_path / "preferences.json"

    preferences.save(path)
    loaded = Preferences.load(path)

    assert [p.name for p in loaded.category_presets] == ["默认"]
    assert loaded.active_category_preset == "default"
    assert loaded.category_presets[0].categories[0].folder_name == "cat"
    assert loaded.labels_presets[0].name == "本地"
    assert loaded.default_labels_selection == "preset:lp1"
    assert loaded.classes_presets[0].names == ["person", "car"]
    assert loaded.default_classes_selection == "preset:cp1"
    assert loaded.active_sort_preset_id == "x1"
    assert loaded.sort_descending is True
    assert any(p.id == "x1" and p.kind == "custom" for p in loaded.sort_presets)
    # Built-ins always re-seeded.
    assert all(any(p.id == bid for p in loaded.sort_presets)
               for bid in ("builtin:natural", "builtin:name", "builtin:mtime"))
    assert loaded.output_dir_template == "{folder}/__out__"
    assert loaded.default_operation == OperationKind.MOVE
    assert loaded.recursive_scan is True
