from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap

from magpie.font_config import overlay_font


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


def label_path_for_image(
    labels_dir: str | Path,
    image_path: str | Path,
    source_folder: str | Path | None = None,
) -> Path:
    """Locate the YOLO ``.txt`` label file for ``image_path``.

    When ``source_folder`` is given, the relative position of the image is
    preserved under ``labels_dir`` (so ``src/subA/0001.jpg`` →
    ``labels_dir/subA/0001.txt``). Without it we fall back to the legacy
    flat lookup (``labels_dir/<basename>.txt``).
    """
    image_path = Path(image_path)
    label_name = image_path.with_suffix(".txt").name
    if source_folder is None:
        return Path(labels_dir) / label_name
    try:
        rel = image_path.relative_to(Path(source_folder))
    except ValueError:
        return Path(labels_dir) / label_name
    return Path(labels_dir) / rel.with_suffix(".txt")


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


def class_label(class_id: int, class_names: list[str]) -> str:
    if class_id < len(class_names) and class_names[class_id]:
        return class_names[class_id]
    return str(class_id)


_BBOX_PALETTE = [
    "#F44336", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
    "#00BCD4", "#FFEB3B", "#E91E63", "#3F51B5", "#8BC34A",
    "#FF5722", "#009688", "#673AB7", "#CDDC39", "#795548",
    "#607D8B", "#FFC107", "#03A9F4", "#76FF03", "#FF4081",
]


def class_color(class_id: int) -> QColor:
    return QColor(_BBOX_PALETTE[class_id % len(_BBOX_PALETTE)])


def draw_bboxes_on_pixmap(
    pixmap: QPixmap,
    boxes: list[BBox],
    class_names: list[str],
) -> QPixmap:
    if pixmap.isNull() or not boxes:
        return pixmap

    output = QPixmap(pixmap)
    painter = QPainter(output)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Scale font to image size so labels are readable on high-res images.
    font_size = max(12, min(output.width(), output.height()) // 50)
    painter.setFont(overlay_font(point_size=font_size))

    for box in boxes:
        color = class_color(box.class_id)
        pen = QPen(color, max(3, min(output.width(), output.height()) // 300))
        painter.setPen(pen)
        rect = box.to_rect(output.width(), output.height())
        painter.drawRect(rect)
        painter.drawText(rect.topLeft().toPoint(), class_label(box.class_id, class_names))

    painter.end()
    return output
