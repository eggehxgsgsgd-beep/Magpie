from magpie.core.history import OperationHistory
from magpie.models import Operation, OperationKind


def _make_op(tmp_path, name="a.jpg"):
    return Operation(
        source_path=tmp_path / name,
        target_path=tmp_path / "out" / name,
        category_folder="cat",
        index=0,
        kind=OperationKind.COPY,
    )


def test_push_and_pop_undo(tmp_path):
    op = _make_op(tmp_path)
    history = OperationHistory()
    history.push(op)
    assert history.undo_count == 1
    assert history.pop_undo() is op
    assert history.undo_count == 0


def test_pop_undo_when_empty_returns_none():
    history = OperationHistory()
    assert history.pop_undo() is None
    assert history.undo_count == 0


def test_clear(tmp_path):
    history = OperationHistory()
    history.push(_make_op(tmp_path))
    history.push(_make_op(tmp_path, "b.jpg"))
    history.clear()
    assert history.undo_count == 0
    assert history.pop_undo() is None


def test_limit_evicts_oldest(tmp_path):
    history = OperationHistory(limit=3)
    ops = [_make_op(tmp_path, f"{i}.jpg") for i in range(5)]
    for op in ops:
        history.push(op)
    assert history.undo_count == 3
    # LIFO order: pop the most recent first.
    assert history.pop_undo() is ops[4]
    assert history.pop_undo() is ops[3]
    assert history.pop_undo() is ops[2]
    assert history.pop_undo() is None
