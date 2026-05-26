"""Compatibility entrypoint kept for users who ran the old v1 script."""

import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from magpie.app import main, parse_args
from magpie.config import AppState, Preferences
from magpie.models import Category, Operation, OperationKind
from magpie.ui import MainWindow


ImageClassifier = MainWindow


__all__ = [
    "AppState",
    "Category",
    "ImageClassifier",
    "MainWindow",
    "Operation",
    "OperationKind",
    "Preferences",
    "main",
    "parse_args",
]


if __name__ == "__main__":
    main()
