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


def undo_operation(operation: Operation) -> None:
    if operation.kind == OperationKind.MOVE:
        if operation.target_path.exists():
            operation.source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(operation.target_path), str(operation.source_path))
    elif operation.target_path.exists():
        operation.target_path.unlink()


def redo_operation(operation: Operation) -> None:
    operation.target_path.parent.mkdir(parents=True, exist_ok=True)
    if operation.kind == OperationKind.MOVE:
        if operation.source_path.exists():
            shutil.move(str(operation.source_path), str(operation.target_path))
    elif operation.source_path.exists():
        shutil.copy2(operation.source_path, operation.target_path)
