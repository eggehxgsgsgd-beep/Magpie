from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class ImageView(QGraphicsView):
    folderDropped = pyqtSignal(str)
    fitRequested = pyqtSignal()
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    autoplayRequested = pyqtSignal()
    contextMenuRequested = pyqtSignal(QPoint)  # global pos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.scene.addItem(self.pixmap_item)
        self.setScene(self.scene)

        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#f0f0f0")))
        self.setFrameShape(QGraphicsView.Shape.StyledPanel)
        self.setStyleSheet("QGraphicsView { border: 1px solid #dddddd; border-radius: 4px; }")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def set_pixmap(self, pixmap: QPixmap, fit: bool = True) -> None:
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        if fit:
            self.fit_to_window()

    def clear(self) -> None:
        self.pixmap_item.setPixmap(QPixmap())
        self.scene.setSceneRect(0, 0, 0, 0)

    def fit_to_window(self) -> None:
        if not self.pixmap_item.pixmap().isNull():
            self.resetTransform()
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def actual_size(self) -> None:
        self.resetTransform()

    def zoom(self, factor: float) -> None:
        if not self.pixmap_item.pixmap().isNull():
            self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.pixmap_item.pixmap().isNull():
            return
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.zoom(factor)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Left:
            self.previousRequested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self.nextRequested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space:
            self.autoplayRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.pixmap_item.pixmap().isNull():
            self.fit_to_window()
            self.fitRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self.contextMenuRequested.emit(event.globalPos())
        event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.folderDropped.emit(path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)
