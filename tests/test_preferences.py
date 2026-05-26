from magpie.config import Preferences
from magpie.models import Category, OperationKind


def test_preferences_round_trip(tmp_path):
    preferences = Preferences(
        categories=[Category(key="1", folder_name="cat", display_name="cat label", color="#00ff00")],
        output_dir_template="{folder}/__out__",
        labels_dir_relative="labels",
        classes_mode="custom",
        classes_path=str(tmp_path / "classes.txt"),
        default_operation=OperationKind.MOVE,
        recursive_scan=True,
        remember_recursive_scan=True,
    )
    path = tmp_path / "preferences.json"

    preferences.save(path)
    loaded = Preferences.load(path)

    assert loaded.categories[0].folder_name == "cat"
    assert loaded.categories[0].display_name == "cat label"
    assert loaded.output_dir_template == "{folder}/__out__"
    assert loaded.labels_dir_relative == "labels"
    assert loaded.classes_mode == "custom"
    assert loaded.classes_path == str(tmp_path / "classes.txt")
    assert loaded.default_operation == OperationKind.MOVE
    assert loaded.recursive_scan is True
