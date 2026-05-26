from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from magpie.config.classifications import ClassificationRecord
from magpie.models import Category, Operation


PANEL_QSS = """
QWidget#sidePanel {
    background: #ffffff;
}
QLabel#panelTitle {
    font-size: 13px;
    font-weight: 600;
    color: #1f2937;
    padding: 4px 2px 4px 2px;
    border-bottom: 1px solid #e5e7eb;
}
QFrame#categoryRow {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
}
QFrame#categoryRow:hover {
    background: #eef2ff;
    border-color: #c7d2fe;
}
QFrame#categoryRow[active="true"] {
    background: #ecfdf5;
    border: 1px solid #34d399;
}
QLabel#categoryKeyBadge {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 3px;
    color: #111827;
    font-weight: 700;
    font-size: 12px;
    padding: 1px 0;
}
QLabel#categoryLabel {
    color: #111827;
    font-size: 13px;
}
QLabel#categoryCount {
    color: #6b7280;
    font-size: 12px;
    font-weight: 600;
    min-width: 28px;
}
QLabel#categoryEmptyHint {
    color: #6b7280;
    font-size: 12px;
    padding: 12px;
    background: #f9fafb;
    border: 1px dashed #d1d5db;
    border-radius: 6px;
}
QListWidget#recentList {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 2px;
    font-size: 12px;
    color: #1f2937;
}
QListWidget#recentList::item {
    padding: 3px 4px;
}
QPushButton#undoButton {
    background: #ff5722;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px;
    font-weight: 600;
}
QPushButton#undoButton:hover { background: #f4511e; }
QPushButton#undoButton:disabled { background: #d1d5db; color: #ffffff; }
"""


def _color_pixmap(color: str, size: int = 12) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(0, 0, size, size, 3, 3)
    painter.end()
    return pixmap


class CategoryRow(QFrame):
    """One clickable row in the side panel representing a Category."""

    clicked = pyqtSignal(object)  # Category

    def __init__(self, category: Category, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.category = category
        self.setObjectName("categoryRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active = False
        self.setProperty("active", "false")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.swatch = QLabel()
        self.swatch.setFixedSize(14, 14)
        self.swatch.setStyleSheet(
            f"background: {self.category.color}; border-radius: 3px; border: 1px solid rgba(0,0,0,0.15);"
        )
        layout.addWidget(self.swatch)

        self.key_badge = QLabel(self.category.key or "·")
        self.key_badge.setObjectName("categoryKeyBadge")
        self.key_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_badge.setFixedWidth(22)
        layout.addWidget(self.key_badge)

        self.label = QLabel(self.category.label)
        self.label.setObjectName("categoryLabel")
        self.label.setToolTip(
            f"快捷键 {self.category.key} · 文件夹 {self.category.folder_name}"
        )
        layout.addWidget(self.label, stretch=1)

        self.count = QLabel("0")
        self.count.setObjectName("categoryCount")
        self.count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.count)

    def update_state(self, count: int, active: bool) -> None:
        self.count.setText(str(count))
        if self._active != active:
            self._active = active
            self.setProperty("active", "true" if active else "false")
            self.style().unpolish(self)
            self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.category)
            event.accept()
            return
        super().mousePressEvent(event)


class SidePanel(QWidget):
    """Side panel with clickable categories, recent operations and undo."""

    undoRequested = pyqtSignal()
    classifyRequested = pyqtSignal(object)  # Category

    RECENT_LIMIT = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setStyleSheet(PANEL_QSS)
        self.setFixedWidth(260)

        self._rows: list[CategoryRow] = []
        self._record: ClassificationRecord | None = None
        self._current_image_name: str = ""

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        category_title = QLabel("类别")
        category_title.setObjectName("panelTitle")
        layout.addWidget(category_title)

        self.empty_label = QLabel("尚未配置类别。\n请进入 文件 → 首选项 添加类别。")
        self.empty_label.setObjectName("categoryEmptyHint")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        self.category_container = QWidget()
        self.category_layout = QVBoxLayout(self.category_container)
        self.category_layout.setContentsMargins(0, 0, 0, 0)
        self.category_layout.setSpacing(4)
        self.category_layout.addStretch(1)

        self.category_scroll = QScrollArea()
        self.category_scroll.setWidget(self.category_container)
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.category_scroll, stretch=1)

        recent_title = QLabel("最近操作")
        recent_title.setObjectName("panelTitle")
        layout.addWidget(recent_title)

        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentList")
        self.recent_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.recent_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.recent_list.setIconSize(QSize(12, 12))
        self.recent_list.setMaximumHeight(200)
        self.recent_list.setUniformItemSizes(True)
        layout.addWidget(self.recent_list)

        self.undo_button = QPushButton("撤销 Ctrl+Z")
        self.undo_button.setObjectName("undoButton")
        self.undo_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.undo_button.clicked.connect(self.undoRequested.emit)
        self.undo_button.setEnabled(False)
        layout.addWidget(self.undo_button)

    # ---- Categories ----

    def refresh(
        self,
        categories: list[Category],
        output_dir: str = "",
        record: ClassificationRecord | None = None,
        current_image_name: str = "",
    ) -> None:
        self._record = record
        self._current_image_name = current_image_name or ""

        signature = [(c.key, c.folder_name, c.color, c.label) for c in categories]
        existing_signature = [
            (r.category.key, r.category.folder_name, r.category.color, r.category.label)
            for r in self._rows
        ]
        if signature != existing_signature:
            self._rebuild_rows(categories)

        labels = (
            record.labels_for(self._current_image_name)
            if record and self._current_image_name
            else []
        )
        for row in self._rows:
            count = record.count_for_category(row.category.folder_name) if record else 0
            active = row.category.folder_name in labels
            row.update_state(count, active)

        has_categories = bool(categories)
        self.empty_label.setVisible(not has_categories)
        self.category_scroll.setVisible(has_categories)

    def _rebuild_rows(self, categories: list[Category]) -> None:
        for row in self._rows:
            self.category_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        for category in categories:
            row = CategoryRow(category)
            row.clicked.connect(self.classifyRequested.emit)
            self.category_layout.insertWidget(self.category_layout.count() - 1, row)
            self._rows.append(row)

    def set_undo_enabled(self, enabled: bool) -> None:
        self.undo_button.setEnabled(enabled)

    # ---- Recent operations ----

    def add_recent_operation(self, operation: Operation, category: Category) -> None:
        text = f"{category.label}  ←  {operation.source_path.name}"
        item = QListWidgetItem(QIcon(_color_pixmap(category.color)), text)
        item.setData(Qt.ItemDataRole.UserRole, self._operation_key(operation))
        item.setToolTip(text)
        self.recent_list.insertItem(0, item)
        while self.recent_list.count() > self.RECENT_LIMIT:
            self.recent_list.takeItem(self.recent_list.count() - 1)

    def remove_recent_operation(self, operation: Operation) -> None:
        """Drop the matching entry from the list (called after an undo)."""
        key = self._operation_key(operation)
        for i in range(self.recent_list.count()):
            if self.recent_list.item(i).data(Qt.ItemDataRole.UserRole) == key:
                self.recent_list.takeItem(i)
                return

    def clear_recent_operations(self) -> None:
        self.recent_list.clear()

    @staticmethod
    def _operation_key(operation: Operation) -> tuple:
        return (
            str(operation.source_path),
            operation.category_folder,
            operation.index,
            operation.kind.value,
        )
