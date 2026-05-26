from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ShortcutsDialog(QDialog):
    """Searchable, dynamically populated shortcuts reference dialog."""

    def __init__(
        self,
        groups: list[tuple[str, list[tuple[str, str, str]]]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("快捷键速查")
        self.resize(560, 600)
        self._entry_widgets: list[tuple[QWidget, str]] = []
        self._group_widgets: list[tuple[QWidget, list[QWidget]]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索快捷键、动作或类别...")
        self.search.textChanged.connect(self._on_search)
        layout.addWidget(self.search)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        for group_title, entries in groups:
            group_widget, child_items = self._make_group(group_title, entries)
            body_layout.addWidget(group_widget)
            self._group_widgets.append((group_widget, child_items))
        body_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        close_btn.setText("关闭")
        close_btn.setFocusPolicy(buttons.focusPolicy())
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _make_group(
        self, title: str, entries: list[tuple[str, str, str]]
    ) -> tuple[QWidget, list[QWidget]]:
        group = QWidget()
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(2)

        header = QLabel(title)
        header.setStyleSheet(
            "font-weight: 600; color: #1f2937; padding: 4px 0;"
            " border-bottom: 1px solid #e5e7eb; margin-bottom: 4px;"
        )
        group_layout.addWidget(header)

        child_items: list[QWidget] = []
        for label, shortcut, hint in entries:
            item = QWidget()
            row = QHBoxLayout(item)
            row.setContentsMargins(4, 3, 4, 3)
            row.setSpacing(8)

            shortcut_label = QLabel(shortcut or "—")
            shortcut_label.setMinimumWidth(120)
            shortcut_label.setStyleSheet(
                "font-family: 'JetBrains Mono', Consolas, monospace;"
                " color: #2563eb; font-weight: 600;"
            )
            row.addWidget(shortcut_label)

            text_label = QLabel(label)
            text_label.setStyleSheet("color: #111827;")
            text_label.setWordWrap(True)
            row.addWidget(text_label, stretch=1)

            if hint:
                hint_label = QLabel(hint)
                hint_label.setStyleSheet("color: #6b7280; font-size: 11px;")
                hint_label.setWordWrap(True)
                row.addWidget(hint_label, stretch=1)

            keywords = f"{label} {shortcut} {hint}".lower()
            item.setProperty("keywords", keywords)
            group_layout.addWidget(item)
            child_items.append(item)
            self._entry_widgets.append((item, keywords))

        return group, child_items

    def _on_search(self, text: str) -> None:
        needle = text.strip().lower()
        if not needle:
            # Show everything. Show groups before items so the items' parents
            # are live; otherwise Qt's effective `isVisible()` stays False even
            # after setVisible(True) on each item.
            for group_widget, items in self._group_widgets:
                group_widget.setVisible(True)
                for item in items:
                    item.setVisible(True)
            return

        # Per-item match decided from stored keywords (not effective isVisible,
        # which depends on parent state and can mislead).
        for widget, keywords in self._entry_widgets:
            widget.setVisible(needle in keywords)
        for group_widget, items in self._group_widgets:
            any_match = any(
                needle in (item.property("keywords") or "") for item in items
            )
            group_widget.setVisible(any_match)
