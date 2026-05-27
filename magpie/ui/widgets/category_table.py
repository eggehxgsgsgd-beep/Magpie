"""Reusable category table widget.

Editable table with 4 columns (shortcut / folder / display / color):
- drag-and-drop row reorder
- double-click the color cell to pick a color
- shortcut column highlights conflicts in red as user types
- display-name column auto-syncs with folder-name column until the user
  edits display manually
- ``+ 添加类别`` / ``- 删除选中类别`` buttons below the table
- ``validate()`` returns a Chinese error string or ``None`` if every row is
  legal (used by the dialog to block accept).
"""

from __future__ import annotations

import string

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from magpie.config import DEFAULT_PALETTE
from magpie.core.classifier import validate_folder_name
from magpie.models import Category


APP_RESERVED_SHORTCUTS = {
    " ",
    "+",
    "-",
    "0",
    "b",
    "f",
}
APP_RESERVED_SHORTCUT_LABELS = {
    " ": "自动播放",
    "+": "放大",
    "-": "缩小",
    "0": "1:1",
    "b": "显示 BBox",
    "f": "适应窗口",
}
VISIBLE_SINGLE_KEYS = set(string.ascii_letters + string.digits + "-=[];',./`\\")


class CategoryTableWidget(QWidget):
    categoriesChanged = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["快捷键", "类别文件夹名", "显示名称", "颜色"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.viewport().setAcceptDrops(True)
        self.table.setDragDropOverwriteMode(False)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setSectionsMovable(False)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self.table, stretch=1)

        buttons_row = QHBoxLayout()
        add_button = QPushButton("+ 添加类别")
        delete_button = QPushButton("- 删除选中类别")
        add_button.clicked.connect(self._on_add_clicked)
        delete_button.clicked.connect(self._on_delete_clicked)
        buttons_row.addWidget(add_button)
        buttons_row.addWidget(delete_button)
        buttons_row.addStretch()
        layout.addLayout(buttons_row)

    # ---- public API ----

    def set_categories(self, items: list[Category]) -> None:
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            for category in items:
                self._append_row(category, mark_clean=True)
        finally:
            self.table.blockSignals(False)
        self._highlight_shortcut_conflicts()

    def categories(self) -> list[Category]:
        result: list[Category] = []
        for row in range(self.table.rowCount()):
            key = self._text(row, 0)
            folder_name = self._text(row, 1)
            display_name = self._text(row, 2) or folder_name
            color_item = self.table.item(row, 3)
            color = (
                color_item.text().strip()
                if color_item and color_item.text().strip()
                else DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)]
            )
            result.append(
                Category(key=key, folder_name=folder_name, display_name=display_name, color=color)
            )
        return result

    def validate(self) -> str | None:
        seen_keys: set[str] = set()
        seen_folders: set[str] = set()
        for category in self.categories():
            key = category.key
            if not key:
                return "快捷键不能为空：请为每个类别设置一个单键快捷键"
            if len(key) != 1 or key not in VISIBLE_SINGLE_KEYS:
                return f"快捷键 {key} 无效：仅支持单个可见字符"
            reserved_for = APP_RESERVED_SHORTCUT_LABELS.get(key.lower(), "软件功能")
            if key.lower() in APP_RESERVED_SHORTCUTS:
                return f"快捷键 {key} 与「{reserved_for}」冲突"
            if key in seen_keys:
                return f"快捷键 {key} 重复"
            seen_keys.add(key)
            error = validate_folder_name(category.folder_name)
            if error:
                return error
            if category.folder_name in seen_folders:
                return f"类别文件夹 {category.folder_name} 重复"
            seen_folders.add(category.folder_name)
        return None

    # ---- internal helpers ----

    def _on_add_clicked(self) -> None:
        self._append_row(None, mark_clean=False)
        self.categoriesChanged.emit()

    def _on_delete_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(
            self, "确认删除", "确定删除选中的类别吗？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.table.removeRow(row)
        self._highlight_shortcut_conflicts()
        self.categoriesChanged.emit()

    def _append_row(self, category: Category | None, mark_clean: bool) -> None:
        self.table.blockSignals(True)
        try:
            row = self.table.rowCount()
            self.table.insertRow(row)
            if category is None:
                category = Category(
                    key="",
                    folder_name=f"class_{row + 1}",
                    display_name=f"class_{row + 1}",
                    color=DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)],
                )
            synced = (
                not category.display_name
                or category.display_name == category.folder_name
            )
            display_value = category.display_name or category.folder_name
            key_item = QTableWidgetItem(category.key)
            folder_item = QTableWidgetItem(category.folder_name)
            display_item = QTableWidgetItem(display_value)
            display_item.setData(Qt.ItemDataRole.UserRole, bool(synced))
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, folder_item)
            self.table.setItem(row, 2, display_item)
            self._set_color_cell(row, category.color or DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)])
        finally:
            self.table.blockSignals(False)
        self._highlight_shortcut_conflicts()

    def _set_color_cell(self, row: int, color_hex: str) -> None:
        color = QColor(color_hex)
        if not color.isValid():
            color = QColor(DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)])
        item = QTableWidgetItem(color.name())
        item.setBackground(QBrush(color))
        item.setForeground(QBrush(QColor("#111827" if color.lightnessF() > 0.6 else "#ffffff")))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setToolTip("双击修改颜色")
        self.table.setItem(row, 3, item)

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        if column != 3:
            return
        item = self.table.item(row, column)
        current = item.text() if item else DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)]
        chosen = QColorDialog.getColor(QColor(current), self, "选择类别颜色")
        if chosen.isValid():
            self.table.blockSignals(True)
            try:
                self._set_color_cell(row, chosen.name())
            finally:
                self.table.blockSignals(False)
            self.categoriesChanged.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        column = item.column()
        if column == 0:
            self._highlight_shortcut_conflicts()
        elif column == 1:
            display_item = self.table.item(item.row(), 2)
            if display_item is not None:
                synced_flag = display_item.data(Qt.ItemDataRole.UserRole)
                synced = bool(synced_flag) if synced_flag is not None else True
                if synced or not display_item.text().strip():
                    self.table.blockSignals(True)
                    try:
                        display_item.setText(item.text())
                        display_item.setData(Qt.ItemDataRole.UserRole, True)
                    finally:
                        self.table.blockSignals(False)
        elif column == 2:
            folder_item = self.table.item(item.row(), 1)
            same_as_folder = bool(folder_item) and folder_item.text() == item.text()
            item.setData(Qt.ItemDataRole.UserRole, same_as_folder)
        self.categoriesChanged.emit()

    def _highlight_shortcut_conflicts(self) -> None:
        seen: dict[str, list[int]] = {}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item:
                continue
            seen.setdefault(item.text().strip(), []).append(row)
        for value, rows in seen.items():
            conflict = len(rows) > 1 and value != ""
            reserved_for = APP_RESERVED_SHORTCUT_LABELS.get(value.lower())
            for row in rows:
                item = self.table.item(row, 0)
                if not item:
                    continue
                if value and reserved_for:
                    item.setBackground(QBrush(QColor("#fed7aa")))
                    item.setToolTip(f"快捷键与「{reserved_for}」冲突")
                elif conflict:
                    item.setBackground(QBrush(QColor("#fecaca")))
                    item.setToolTip("快捷键与其他行重复")
                else:
                    item.setBackground(QBrush())
                    item.setToolTip("")

    def _text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item else ""
