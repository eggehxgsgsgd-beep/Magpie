from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView


class ImageView(QGraphicsView):
    folderDropped = pyqtSignal(str)
    fitRequested = pyqtSignal()
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    autoplayRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.badge_bg = QGraphicsRectItem()
        self.badge_text = QGraphicsSimpleTextItem()
        self.scene.addItem(self.pixmap_item)
        self.scene.addItem(self.badge_bg)
        self.scene.addItem(self.badge_text)
        self.badge_bg.setBrush(QBrush(QColor(0, 0, 0, 180)))
        self.badge_bg.setPen(QPen(Qt.PenStyle.NoPen))
        self.badge_text.setBrush(QBrush(QColor("white")))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.badge_text.setFont(font)
        self.set_badge([])
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

    def set_pixmap(self, pixmap: QPixmap, fit: bool = True) -> None:
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self._position_badge()
        if fit:
            self.fit_to_window()

    def clear(self) -> None:
        self.pixmap_item.setPixmap(QPixmap())
        self.scene.setSceneRect(0, 0, 0, 0)
        self.set_badge([])

    def set_badge(self, labels: list[str]) -> None:
        if not labels:
            self.badge_bg.hide()
            self.badge_text.hide()
            return

        self.badge_text.setText(f"已分类: {', '.join(labels)}")
        self.badge_bg.show()
        self.badge_text.show()
        self._position_badge()

    def _position_badge(self) -> None:
        rect = self.badge_text.boundingRect().adjusted(-8, -4, 8, 4)
        self.badge_bg.setRect(rect)
        self.badge_bg.setPos(12, 12)
        self.badge_text.setPos(20, 16)

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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.fit_to_window()
            self.fitRequested.emit()
            return
        super().mousePressEvent(event)

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
