from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from PyQt6.QtGui import QImage


class ImageLoaderSignals(QObject):
    """Signals emitted by :class:`ImageLoadTask`.

    ``finished`` carries ``(request_id, path, qimage)``.
    ``error`` carries ``(request_id, path, error_message)``.
    """

    finished = pyqtSignal(int, object, object)  # request_id, Path, QImage
    error = pyqtSignal(int, object, str)         # request_id, Path, msg


class ImageLoadTask(QRunnable):
    """Decode an image file into a :class:`QImage` on a worker thread.

    The heavy work (PIL decode, EXIF transpose, RGBA conversion) happens in
    :meth:`run`; the caller converts the resulting ``QImage`` → ``QPixmap``
    on the GUI thread.
    """

    def __init__(self, request_id: int, path: Path) -> None:
        super().__init__()
        self.request_id = request_id
        self.path = path
        self.signals = ImageLoaderSignals()
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            with Image.open(self.path) as image:
                image = ImageOps.exif_transpose(image).convert("RGBA")
                data = image.tobytes("raw", "RGBA")
                q_image = QImage(
                    data, image.width, image.height,
                    QImage.Format.Format_RGBA8888,
                ).copy()
            self.signals.finished.emit(self.request_id, self.path, q_image)
        except RuntimeError:
            # Signals object was garbage-collected (e.g. window closed while
            # a decode was in flight). Nothing to do.
            pass
        except Exception as exc:  # noqa: BLE001
            try:
                self.signals.error.emit(self.request_id, self.path, str(exc))
            except RuntimeError:
                pass
