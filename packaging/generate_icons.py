from __future__ import annotations

from pathlib import Path

from PIL import Image
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "magpie" / "resources" / "icons" / "magpie_icon.svg"
OUTPUT_DIR = ROOT / "packaging"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _render_svg(size: int) -> Image.Image:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer = QSvgRenderer(str(SVG_PATH))
    renderer.render(painter)
    painter.end()

    # Keep the bytes alive by taking a copy before constructing PIL's Image.
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    return Image.frombuffer(
        "RGBA",
        (image.width(), image.height()),
        bytes(ptr),
        "raw",
        "BGRA",
        0,
        1,
    )


def main() -> int:
    if not SVG_PATH.exists():
        raise FileNotFoundError(SVG_PATH)

    app = QApplication.instance() or QApplication([])  # noqa: F841

    rendered = [_render_svg(size) for size in ICON_SIZES]
    for size, image in zip(ICON_SIZES, rendered, strict=True):
        image.save(OUTPUT_DIR / f"app_{size}.png")

    rendered[-1].save(OUTPUT_DIR / "app.png")
    rendered[-1].save(
        OUTPUT_DIR / "app.ico",
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
