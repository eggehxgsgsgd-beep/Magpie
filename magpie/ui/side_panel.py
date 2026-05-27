from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from magpie.config.classifications import ClassificationRecord
from magpie.models import Category


PANEL_QSS = """
QWidget#sidePanel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QLabel#panelTitle {
    font-size: 13px;
    font-weight: 700;
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
    border-bottom: 1px solid #f3f4f6;
    border-radius: 0;
}
QFrame#categoryRow:hover {
    background: #f9fafb;
}
QFrame#categoryRow[active="true"] {
    background: #ecfdf5;
    border-bottom: 1px solid #bbf7d0;
}
QLabel#categoryKeyBadge {
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    color: #111827;
    font-weight: 700;
    font-size: 12px;
    padding: 2px 0;
}
QLabel#categoryKeyBadge[missing="true"] {
    color: #b45309;
    border-color: #f59e0b;
    background: #fffbeb;
}
QLabel#categoryLabel {
    color: #374151;
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
"""


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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

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
    """Side panel showing category list for quick classification."""

    manageCategoriesRequested = pyqtSignal()

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
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header: title + manage button
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("分类")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()
        manage_button = QPushButton("管理")
        manage_button.setObjectName("panelLinkButton")
        manage_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        manage_button.setCursor(Qt.CursorShape.PointingHandCursor)
        manage_button.clicked.connect(self.manageCategoriesRequested.emit)
        header.addWidget(manage_button)
        layout.addLayout(header)

        # Empty state
        self.empty_widget = QFrame()
        self.empty_widget.setObjectName("categoryEmptyHint")
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(10, 10, 10, 10)
        empty_layout.setSpacing(8)
        self.empty_label = QLabel("尚未配置类别。\n添加后可用快捷键快速分类。")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.empty_label.setStyleSheet("border: none; background: transparent; padding: 0; color: #6b7280;")
        empty_layout.addWidget(self.empty_label)
        empty_action = QPushButton("打开首选项")
        empty_action.setObjectName("emptyActionButton")
        empty_action.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        empty_action.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_action.clicked.connect(self.manageCategoriesRequested.emit)
        empty_layout.addWidget(empty_action, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.empty_widget)

        # Category list (scrollable)
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
        layout.addWidget(self.category_scroll, stretch=1)

    # ---- Public API ----

    def refresh(
        self,
        categories: list[Category],
        output_dir: str = "",
        record: ClassificationRecord | None = None,
        current_image_name: str = "",
    ) -> None:
        self._record = record
        self._current_image_name = current_image_name or ""

        signature = [(c.key, c.folder_name, c.label) for c in categories]
        existing_signature = [
            (r.category.key, r.category.folder_name, r.category.label)
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
