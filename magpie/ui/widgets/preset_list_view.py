"""Reusable preset list widget used in preferences for all four preset types
(sort / category / labels / classes).

Visual: a vertical list. Each row has:
- left "selected" indicator bar
- icon (single character or emoji)
- title + optional subtitle stacked
- right-side action buttons (edit / duplicate / delete), only shown for
  non-builtin rows
- "内置" tag for builtin rows

Selection is single-row, signaled via ``selectionChanged(preset_id)``. Edits
emit specific request signals — the parent dialog handles them.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass
class PresetItem:
    id: str
    title: str
    subtitle: str = ""
    icon: str = ""           # emoji or single character
    builtin: bool = False
    builtin_badge: str = "内置"


_ROW_QSS = """
QFrame#presetRow {
    background: #ffffff;
    border: 1px solid transparent;
    border-radius: 6px;
}
QFrame#presetRow:hover {
    background: #f3f4f6;
}
QFrame#presetRow[active="true"] {
    background: #eef2ff;
    border: 1px solid #c7d2fe;
}
QLabel#presetIcon {
    font-size: 20px;
    min-width: 24px;
    padding-right: 4px;
}
QLabel#presetSelectedBar {
    background: #3b82f6;
    border-radius: 2px;
    min-width: 3px;
    max-width: 3px;
}
QLabel#presetTitle {
    color: #111827;
    font-size: 14px;
    font-weight: 600;
}
QLabel#presetSubtitle {
    color: #6b7280;
    font-size: 12px;
}
QLabel#presetBuiltinBadge {
    color: #6b7280;
    font-size: 10px;
    background: #f3f4f6;
    border-radius: 3px;
    padding: 2px 6px;
}
QPushButton#presetRowButton {
    color: #2563eb;
    border: none;
    background: transparent;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
}
QPushButton#presetRowButton:hover {
    background: #dbeafe;
}
QPushButton#presetRowButton[danger="true"] {
    color: #dc2626;
}
QPushButton#presetRowButton[danger="true"]:hover {
    background: #fee2e2;
}
"""


class _PresetRow(QFrame):
    clicked = pyqtSignal(str)
    requestEdit = pyqtSignal(str)
    requestDuplicate = pyqtSignal(str)
    requestDelete = pyqtSignal(str)

    def __init__(self, item: PresetItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setObjectName("presetRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active = False
        self.setProperty("active", "false")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 10, 6)
        layout.setSpacing(8)

        self.selected_bar = QLabel()
        self.selected_bar.setObjectName("presetSelectedBar")
        self.selected_bar.setFixedHeight(28)
        self.selected_bar.setVisible(False)
        layout.addWidget(self.selected_bar)

        if item.icon:
            icon_label = QLabel(item.icon)
            icon_label.setObjectName("presetIcon")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(item.title)
        self.title_label.setObjectName("presetTitle")
        title_box.addWidget(self.title_label)
        if item.subtitle:
            self.subtitle_label = QLabel(item.subtitle)
            self.subtitle_label.setObjectName("presetSubtitle")
            self.subtitle_label.setWordWrap(False)
            title_box.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None
        layout.addLayout(title_box, stretch=1)

        if item.builtin:
            badge = QLabel(item.builtin_badge)
            badge.setObjectName("presetBuiltinBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(badge)
        else:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("presetRowButton")
            edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.requestEdit.emit(self.item.id))
            layout.addWidget(edit_btn)
            dup_btn = QPushButton("复制")
            dup_btn.setObjectName("presetRowButton")
            dup_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            dup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dup_btn.clicked.connect(lambda: self.requestDuplicate.emit(self.item.id))
            layout.addWidget(dup_btn)
            del_btn = QPushButton("删除")
            del_btn.setObjectName("presetRowButton")
            del_btn.setProperty("danger", "true")
            del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda: self.requestDelete.emit(self.item.id))
            layout.addWidget(del_btn)

    def set_active(self, active: bool) -> None:
        if self._active == active:
            return
        self._active = active
        self.selected_bar.setVisible(active)
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item.id)
            event.accept()
            return
        super().mousePressEvent(event)


class PresetListView(QWidget):
    """Vertical list of preset rows with single-select + edit/dup/delete signals."""

    selectionChanged = pyqtSignal(str)
    requestEdit = pyqtSignal(str)
    requestDuplicate = pyqtSignal(str)
    requestDelete = pyqtSignal(str)
    requestNew = pyqtSignal()

    def __init__(self, *, new_button_text: str = "新建…", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_ROW_QSS)
        self._rows: list[_PresetRow] = []
        self._active_id: str = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # Scroll area for rows.
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidget(self._container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)
        scroll.setStyleSheet("QScrollArea { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; }")
        scroll.setMinimumHeight(220)
        scroll.setMaximumHeight(430)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(scroll, stretch=1)

        new_button = QPushButton(new_button_text)
        new_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        new_button.setStyleSheet(
            "QPushButton { color: #1f2937; background: #ffffff;"
            " border: 1px solid #d1d5db; border-radius: 4px;"
            " padding: 5px 12px; }"
            "QPushButton:hover { background: #f3f4f6; border-color: #c7ccd4; }"
            "QPushButton:pressed { background: #e5e7eb; }"
        )
        new_button.clicked.connect(self.requestNew.emit)
        outer.addWidget(new_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def set_presets(self, items: list[PresetItem], active_id: str) -> None:
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

        # Group builtins first, then a separator, then customs (only if both exist).
        builtins = [it for it in items if it.builtin]
        customs = [it for it in items if not it.builtin]

        def _add(item: PresetItem) -> None:
            row = _PresetRow(item)
            row.clicked.connect(self._on_row_clicked)
            row.requestEdit.connect(self.requestEdit.emit)
            row.requestDuplicate.connect(self.requestDuplicate.emit)
            row.requestDelete.connect(self.requestDelete.emit)
            self._container_layout.addWidget(row)
            self._rows.append(row)

        for item in builtins:
            _add(item)
        if builtins and customs:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #e5e7eb;")
            self._container_layout.addWidget(sep)
        for item in customs:
            _add(item)

        if not items:
            placeholder = QLabel("（尚无方案，点击下方按钮新建）")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #9ca3af; padding: 24px;")
            self._container_layout.addWidget(placeholder)
            self._rows.append(placeholder)  # so cleanup grabs it next time

        self._container_layout.addStretch(1)

        self.set_active(active_id)

    def set_active(self, active_id: str) -> None:
        self._active_id = active_id
        for row in self._rows:
            if isinstance(row, _PresetRow):
                row.set_active(row.item.id == active_id)

    def active_id(self) -> str:
        return self._active_id

    def _on_row_clicked(self, preset_id: str) -> None:
        if preset_id == self._active_id:
            return
        self.set_active(preset_id)
        self.selectionChanged.emit(preset_id)
