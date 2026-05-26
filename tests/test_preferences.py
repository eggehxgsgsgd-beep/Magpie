from magpie.config import Preferences
from magpie.models import Category, OperationKind


def test_preferences_round_trip(tmp_path):
    preferences = Preferences(
        categories=[Category(key="1", folder_name="cat", display_name="cat label", color="#00ff00")],
        output_dir=str(tmp_path / "out"),
        source_dir=str(tmp_path / "src"),
        default_operation=OperationKind.MOVE,
        recursive_scan=True,
        remember_recursive_scan=True,
    )
    path = tmp_path / "preferences.json"

    preferences.save(path)
    loaded = Preferences.load(path)

    assert loaded.categories[0].folder_name == "cat"
    assert loaded.categories[0].display_name == "cat label"
    assert loaded.source_dir == str(tmp_path / "src")
    assert loaded.default_operation == OperationKind.MOVE
    assert loaded.recursive_scan is True
