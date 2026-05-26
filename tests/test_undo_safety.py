"""Tests for the COPY-undo modify check (P0-#3)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from magpie.core import TargetModifiedError, undo_operation
from magpie.models import Operation, OperationKind


def _make_pair(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "src.jpg"
    src.write_bytes(b"original")
    dst = tmp_path / "out" / "src.jpg"
    dst.parent.mkdir()
    # Simulate classify_image's shutil.copy2 which preserves mtime.
    dst.write_bytes(src.read_bytes())
    st = src.stat()
    os.utime(dst, (st.st_atime, st.st_mtime))
    return src, dst


def _make_op(src: Path, dst: Path, kind: OperationKind) -> Operation:
    return Operation(
        source_path=src,
        target_path=dst,
        category_folder="ok",
        index=0,
        kind=kind,
    )


def test_undo_copy_when_target_unchanged_deletes(tmp_path: Path) -> None:
    src, dst = _make_pair(tmp_path)
    op = _make_op(src, dst, OperationKind.COPY)
    undo_operation(op)
    assert not dst.exists()
    assert src.exists()  # source still intact


def test_undo_copy_when_target_modified_raises(tmp_path: Path) -> None:
    src, dst = _make_pair(tmp_path)
    # User edited the target after copy.
    dst.write_bytes(b"edited!")
    op = _make_op(src, dst, OperationKind.COPY)
    with pytest.raises(TargetModifiedError):
        undo_operation(op)
    # Target untouched on modify detection
    assert dst.read_bytes() == b"edited!"


def test_undo_copy_force_true_deletes_regardless(tmp_path: Path) -> None:
    src, dst = _make_pair(tmp_path)
    dst.write_bytes(b"edited!")
    op = _make_op(src, dst, OperationKind.COPY)
    undo_operation(op, force=True)
    assert not dst.exists()


def test_undo_copy_when_source_missing_still_deletes(tmp_path: Path) -> None:
    """If we can't compare (source moved out somehow), don't block undo."""
    src, dst = _make_pair(tmp_path)
    src.unlink()
    op = _make_op(src, dst, OperationKind.COPY)
    undo_operation(op)
    assert not dst.exists()


def test_undo_copy_with_mtime_within_tolerance(tmp_path: Path) -> None:
    src, dst = _make_pair(tmp_path)
    st = src.stat()
    # Shift mtime by 1 second (within 2 s tolerance) — same content/size.
    os.utime(dst, (st.st_atime, st.st_mtime + 1.0))
    op = _make_op(src, dst, OperationKind.COPY)
    undo_operation(op)
    assert not dst.exists()


def test_undo_move_still_moves_back(tmp_path: Path) -> None:
    """MOVE undo path should be unaffected by the new check."""
    src = tmp_path / "src.jpg"
    src.write_bytes(b"original")
    dst = tmp_path / "out" / "src.jpg"
    dst.parent.mkdir()
    # Simulate MOVE: target exists, source doesn't.
    dst.write_bytes(b"original")
    src.unlink()
    op = _make_op(src, dst, OperationKind.MOVE)
    undo_operation(op)
    assert src.exists()
    assert not dst.exists()
