from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtGui import QImage, QPixmap


def natural_key(path: Path) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def list_image_files(
    folder: str | Path,
    extensions: list[str],
    sort_strategy: str = "natural",
    recursive: bool = False,
) -> list[Path]:
    root = Path(folder)
    suffixes = {f".{ext.lower().lstrip('.')}" for ext in extensions}
    candidates = root.rglob("*") if recursive else root.iterdir()
    files = [path for path in candidates if path.is_file() and path.suffix.lower() in suffixes]

    if sort_strategy == "name_asc":
        return sorted(files, key=lambda item: item.name.lower())
    if sort_strategy == "name_desc":
        return sorted(files, key=lambda item: item.name.lower(), reverse=True)
    if sort_strategy == "mtime_asc":
        return sorted(files, key=lambda item: item.stat().st_mtime)
    if sort_strategy == "mtime_desc":
        return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)
    if sort_strategy == "size_asc":
        return sorted(files, key=lambda item: item.stat().st_size)
    if sort_strategy == "size_desc":
        return sorted(files, key=lambda item: item.stat().st_size, reverse=True)

    return sorted(files, key=natural_key)


def load_pixmap(path: str | Path) -> QPixmap:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGBA")
        data = image.tobytes("raw", "RGBA")
        q_image = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(q_image)
