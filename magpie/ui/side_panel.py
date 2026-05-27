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
    QTabWidget,
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
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    padding: 0;
}
QPushButton#panelLinkButton {
    color: #2563eb;
    border: none;
    background: transparent;
    padding: 2px 4px;
    font-size: 12px;
}
QPushButton#panelLinkButton:hover {
    color: #1d4ed8;
    text-decoration: underline;
}
QFrame#categoryRow {
    background: #ffffff;
    border: 0;
    border-bottom: 1px solid #e5e7eb;
    border-radius: 0;
}
QFrame#categoryRow:hover {
    background: #ffffff;
}
QFrame#categoryRow[active="true"] {
    background: #ecfdf5;
    border-bottom: 1px solid #bbf7d0;
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
QLabel#categoryKeyBadge[missing="true"] {
    color: #b45309;
    border-color: #f59e0b;
    background: #fffbeb;
}
QLabel#categoryLabel {
    color: #111827;
    font-size: 13px;
}
QLabel#categoryCount {
    color: #9ca3af;
    font-size: 12px;
    min-width: 38px;
}
QFrame#categoryEmptyHint {
    color: #6b7280;
    font-size: 12px;
    padding: 10px;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
}
QPushButton#emptyActionButton {
    color: #1f2937;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 12px;
}
QPushButton#emptyActionButton:hover {
    background: #f3f4f6;
}
QLabel#recentEmptyHint {
    color: #9ca3af;
    font-size: 12px;
    padding: 4px 2px;
}
QTabWidget#sidePanelTabs::pane {
    border: 0;
}
QTabWidget#sidePanelTabs QTabBar::tab {
    padding: 5px 12px;
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
    """One display row in the side panel representing a Category."""

    def __init__(self, category: Category, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.category = category
        self.setObjectName("categoryRow")
        self._active = False
        self.setProperty("active", "false")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(8)

        self.swatch = QLabel()
        self.swatch.setFixedSize(14, 14)
        self.swatch.setStyleSheet(
            f"background: {self.category.color}; border-radius: 3px; border: 1px solid rgba(0,0,0,0.15);"
        )
        layout.addWidget(self.swatch)

        shortcut = self.category.key.strip()
        self.key_badge = QLabel(shortcut or "!")
        self.key_badge.setObjectName("categoryKeyBadge")
        self.key_badge.setProperty("missing", "true" if not shortcut else "false")
        self.key_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_badge.setFixedWidth(28)
        layout.addWidget(self.key_badge)

        self.label = QLabel(self.category.label)
        self.label.setObjectName("categoryLabel")
        tooltip_prefix = f"快捷键 {shortcut} · " if shortcut else "缺少快捷键 · "
        self.label.setToolTip(f"{tooltip_prefix}文件夹 {self.category.folder_name}")
        layout.addWidget(self.label, stretch=1)

        self.count = QLabel("0")
        self.count.setObjectName("categoryCount")
        self.count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.count)

    def update_state(self, count: int, active: bool) -> None:
        self.count.setText(f"{count} 张")
        if self._active != active:
            self._active = active
            self.setProperty("active", "true" if active else "false")
            self.style().unpolish(self)
            self.style().polish(self)

class SidePanel(QWidget):
    """Side panel with clickable categories and a recent operations list.

    The undo button used to live at the bottom of this panel; it has moved
    to a footer row in the main window so its bottom can align with the
    image-display area's bottom.
    """

    manageCategoriesRequested = pyqtSignal()

    RECENT_LIMIT = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setStyleSheet(PANEL_QSS)
        self.setFixedWidth(320)

        self._rows: list[CategoryRow] = []
        self._record: ClassificationRecord | None = None
        self._current_image_name: str = ""

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("sidePanelTabs")
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        category_tab = QWidget()
        category_layout = QVBoxLayout(category_tab)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(6)

        category_header = QHBoxLayout()
        category_header.setContentsMargins(0, 0, 0, 0)
        category_header.addStretch()
        manage_button = QPushButton("管理")
        manage_button.setObjectName("panelLinkButton")
        manage_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        manage_button.setCursor(Qt.CursorShape.PointingHandCursor)
        manage_button.clicked.connect(self.manageCategoriesRequested.emit)
        category_header.addWidget(manage_button)
        category_layout.addLayout(category_header)

        self.empty_widget = QFrame()
        self.empty_widget.setObjectName("categoryEmptyHint")
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(10, 10, 10, 10)
        empty_layout.setSpacing(8)
        self.empty_label = QLabel("尚未配置类别。\n添加后可用快捷键快速分类。")
        self.empty_label.setObjectName("categoryEmptyHint")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.empty_label.setStyleSheet("border: none; background: transparent; padding: 0;")
        empty_layout.addWidget(self.empty_label)
        empty_action = QPushButton("打开首选项")
        empty_action.setObjectName("emptyActionButton")
        empty_action.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        empty_action.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_action.clicked.connect(self.manageCategoriesRequested.emit)
        empty_layout.addWidget(empty_action, alignment=Qt.AlignmentFlag.AlignLeft)
        category_layout.addWidget(self.empty_widget)

        self.category_container = QWidget()
        self.category_layout = QVBoxLayout(self.category_container)
        self.category_layout.setContentsMargins(0, 0, 0, 0)
        self.category_layout.setSpacing(0)
        self.category_layout.addStretch(1)

        self.category_scroll = QScrollArea()
        self.category_scroll.setWidget(self.category_container)
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        category_layout.addWidget(self.category_scroll, stretch=1)

        self.tabs.addTab(category_tab, "类别")

        recent_tab = QWidget()
        recent_layout = QVBoxLayout(recent_tab)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(6)

        self.recent_empty_label = QLabel("暂无操作记录")
        self.recent_empty_label.setObjectName("recentEmptyHint")
        recent_layout.addWidget(self.recent_empty_label)

        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentList")
        self.recent_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.recent_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.recent_list.setIconSize(QSize(12, 12))
        self.recent_list.setMaximumHeight(200)
        self.recent_list.setUniformItemSizes(True)
        recent_layout.addWidget(self.recent_list)
        recent_layout.addStretch()
        self.tabs.addTab(recent_tab, "最近操作")
        # The undo button used to live here; it has moved to the bottom of the
        # main window so its bottom aligns with the image-display area's
        # bottom. Main window owns it now.

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
        self.empty_widget.setVisible(not has_categories)
        self.category_scroll.setVisible(has_categories)

    def _rebuild_rows(self, categories: list[Category]) -> None:
        for row in self._rows:
            self.category_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        for category in categories:
            row = CategoryRow(category)
            self.category_layout.insertWidget(self.category_layout.count() - 1, row)
            self._rows.append(row)

    # ---- Recent operations ----

    def add_recent_operation(self, operation: Operation, category: Category) -> None:
        text = f"{category.label}  ←  {operation.source_path.name}"
        item = QListWidgetItem(QIcon(_color_pixmap(category.color)), text)
        item.setData(Qt.ItemDataRole.UserRole, self._operation_key(operation))
        item.setToolTip(text)
        self.recent_list.insertItem(0, item)
        while self.recent_list.count() > self.RECENT_LIMIT:
            self.recent_list.takeItem(self.recent_list.count() - 1)
        self._update_recent_empty_state()

    def remove_recent_operation(self, operation: Operation) -> None:
        """Drop the matching entry from the list (called after an undo)."""
        key = self._operation_key(operation)
        for i in range(self.recent_list.count()):
            if self.recent_list.item(i).data(Qt.ItemDataRole.UserRole) == key:
                self.recent_list.takeItem(i)
                self._update_recent_empty_state()
                return

    def clear_recent_operations(self) -> None:
        self.recent_list.clear()
        self._update_recent_empty_state()

    def _update_recent_empty_state(self) -> None:
        has_items = self.recent_list.count() > 0
        self.recent_empty_label.setVisible(not has_items)
        self.recent_list.setVisible(has_items)

    @staticmethod
    def _operation_key(operation: Operation) -> tuple:
        return (
            str(operation.source_path),
            operation.category_folder,
            operation.index,
            operation.kind.value,
        )
