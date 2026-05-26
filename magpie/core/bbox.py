from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

from magpie.models import Category


@dataclass(slots=True)
class BBox:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    def to_rect(self, image_width: int, image_height: int) -> QRectF:
        width = self.width * image_width
        height = self.height * image_height
        x = self.x_center * image_width - width / 2
        y = self.y_center * image_height - height / 2
        return QRectF(x, y, width, height)


def label_path_for_image(labels_dir: str | Path, image_path: str | Path) -> Path:
    return Path(labels_dir) / Path(image_path).with_suffix(".txt").name


def load_yolo_labels(label_path: str | Path) -> list[BBox]:
    path = Path(label_path)
    if not path.exists():
        return []

    boxes: list[BBox] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()[:5]
        if len(parts) != 5:
            continue

        try:
            class_id, x_center, y_center, width, height = parts
            boxes.append(
                BBox(
                    class_id=int(float(class_id)),
                    x_center=float(x_center),
                    y_center=float(y_center),
                    width=float(width),
                    height=float(height),
                )
            )
        except ValueError:
            continue

    return boxes


def load_class_names(path: str | Path) -> list[str]:
    if not path:
        return []

    file_path = Path(path)
    if not file_path.exists():
        return []

    return [line.strip() for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines()]


def class_label(class_id: int, class_names: list[str], categories: list[Category]) -> str:
    if class_id < len(class_names) and class_names[class_id]:
        return class_names[class_id]
    if class_id < len(categories):
        return categories[class_id].label
    return str(class_id)


def class_color(class_id: int, categories: list[Category]) -> QColor:
    if class_id < len(categories):
        return QColor(categories[class_id].color)
    return QColor("#9E9E9E")


def draw_bboxes_on_pixmap(
    pixmap: QPixmap,
    boxes: list[BBox],
    categories: list[Category],
    class_names: list[str],
) -> QPixmap:
    if pixmap.isNull() or not boxes:
        return pixmap

    output = QPixmap(pixmap)
    painter = QPainter(output)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPointSize(12)
    painter.setFont(font)

    for box in boxes:
        color = class_color(box.class_id, categories)
        pen = QPen(color, 3)
        painter.setPen(pen)
        rect = box.to_rect(output.width(), output.height())
        painter.drawRect(rect)
        painter.drawText(rect.topLeft().toPoint(), class_label(box.class_id, class_names, categories))

    painter.end()
    return output
