from __future__ import annotations

import shutil
from pathlib import Path

from magpie.models import Category, Operation, OperationKind


INVALID_FOLDER_CHARS = set('/\\:*?"<>|')


def validate_folder_name(folder_name: str) -> str | None:
    if not folder_name.strip():
        return "类别文件夹名不能为空"
    if any(char in INVALID_FOLDER_CHARS for char in folder_name):
        return '类别文件夹名不能包含 / \\ : * ? " < > |'
    return None


def ensure_category_folders(output_dir: str | Path, categories: list[Category]) -> None:
    if not output_dir:
        return
    root = Path(output_dir)
    for category in categories:
        (root / category.folder_name).mkdir(parents=True, exist_ok=True)


def resolve_target_path(target_path: Path, strategy: str) -> Path | None:
    if not target_path.exists():
        return target_path

    if strategy == "skip":
        return None
    if strategy == "overwrite":
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def classify_image(
    image_path: str | Path,
    output_dir: str | Path,
    category: Category,
    kind: OperationKind,
    conflict_strategy: str,
    index: int,
    target_path: str | Path | None = None,
) -> Operation | None:
    source_path = Path(image_path)
    category_dir = Path(output_dir) / category.folder_name
    category_dir.mkdir(parents=True, exist_ok=True)
    target_path = Path(target_path) if target_path else resolve_target_path(category_dir / source_path.name, conflict_strategy)

    if target_path is None:
        return None

    # Caller may have computed a target inside a subdirectory mirror (when
    # the source was found via a recursive scan). Make sure intermediate
    # directories exist before move/copy — shutil doesn't create them.
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if kind == OperationKind.MOVE:
        shutil.move(str(source_path), str(target_path))
    else:
        shutil.copy2(source_path, target_path)

    return Operation(
        source_path=source_path,
        target_path=target_path,
        category_folder=category.folder_name,
        index=index,
        kind=kind,
    )


class TargetModifiedError(Exception):
    """Raised by ``undo_operation`` when the COPY target has diverged from
    its source on disk (mtime/size mismatch). Caller should ask the user
    whether to delete it anyway and retry with ``force=True``."""

    def __init__(self, target_path: Path) -> None:
        super().__init__(str(target_path))
        self.target_path = target_path


# Treat target as "modified" if size differs at all, or mtime differs by
# more than this many seconds. mtime tolerance covers FAT32 / SMB clock skew.
_MTIME_TOLERANCE_S = 2.0


def undo_operation(operation: Operation, *, force: bool = False) -> None:
    if operation.kind == OperationKind.MOVE:
        if operation.target_path.exists():
            operation.source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(operation.target_path), str(operation.source_path))
        return

    # COPY undo = delete the copy at target_path. But the user might have
    # edited that copy externally; deleting would silently destroy their
    # work. Compare against the (still-existing) source to detect that.
    if not operation.target_path.exists():
        return
    if not force and operation.source_path.exists():
        src_stat = operation.source_path.stat()
        tgt_stat = operation.target_path.stat()
        if src_stat.st_size != tgt_stat.st_size or \
                abs(src_stat.st_mtime - tgt_stat.st_mtime) > _MTIME_TOLERANCE_S:
            raise TargetModifiedError(operation.target_path)
    operation.target_path.unlink()
