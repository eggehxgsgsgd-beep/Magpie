from magpie.config.classifications import ClassificationRecord


def test_classification_record_add_remove_and_count(tmp_path):
    record = ClassificationRecord(source_folder=str(tmp_path), path=tmp_path / "record.json")

    record.add("image_001.jpg", "cat")
    record.add("image_001.jpg", "dog")

    assert record.labels_for("image_001.jpg") == ["cat", "dog"]
    assert record.count_for_category("cat") == 1
    assert record.classified_image_count() == 1

    record.remove("image_001.jpg", "cat")

    assert record.labels_for("image_001.jpg") == ["dog"]
