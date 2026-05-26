from magpie.core.history import OperationHistory
from magpie.models import Operation, OperationKind


def test_history_moves_items_between_undo_and_redo(tmp_path):
    operation = Operation(
        source_path=tmp_path / "a.jpg",
        target_path=tmp_path / "out" / "a.jpg",
        category_folder="cat",
        index=0,
        kind=OperationKind.COPY,
    )
    history = OperationHistory()

    history.push(operation)
    assert history.undo_count == 1
    assert history.redo_count == 0

    assert history.pop_undo() == operation
    assert history.undo_count == 0
    assert history.redo_count == 1

    assert history.pop_redo() == operation
    assert history.undo_count == 1
    assert history.redo_count == 0
