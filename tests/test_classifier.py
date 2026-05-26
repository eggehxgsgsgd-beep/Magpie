from magpie.core.classifier import classify_image, resolve_target_path, undo_operation
from magpie.models import Category, OperationKind


def test_resolve_target_path_renames_existing_file(tmp_path):
    target = tmp_path / "image.jpg"
    target.write_text("old", encoding="utf-8")

    assert resolve_target_path(target, "rename") == tmp_path / "image_1.jpg"


def test_copy_classification_can_be_undone(tmp_path):
    image = tmp_path / "image.jpg"
    image.write_text("data", encoding="utf-8")
    output = tmp_path / "out"
    category = Category(key="1", folder_name="cat")

    operation = classify_image(image, output, category, OperationKind.COPY, "rename", 0)

    assert operation is not None
    assert operation.target_path.exists()
    undo_operation(operation)
    assert not operation.target_path.exists()
    assert image.exists()
