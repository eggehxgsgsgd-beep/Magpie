from magpie.core.bbox import label_path_for_image, load_yolo_labels


def test_label_path_uses_image_stem_for_any_extension(tmp_path):
    assert label_path_for_image(tmp_path, "demo.webp") == tmp_path / "demo.txt"


def test_load_yolo_labels_ignores_extra_fields(tmp_path):
    label_file = tmp_path / "demo.txt"
    label_file.write_text("1 0.5 0.5 0.2 0.3 0.99\nbad line\n", encoding="utf-8")

    labels = load_yolo_labels(label_file)

    assert len(labels) == 1
    assert labels[0].class_id == 1
    assert labels[0].width == 0.2
