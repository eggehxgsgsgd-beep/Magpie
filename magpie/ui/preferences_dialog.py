from __future__ import annotations

import json
import os
import string
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from magpie.config import DEFAULT_EXTENSIONS, DEFAULT_PALETTE, Preferences
from magpie.core import CustomSortError, compile_custom_sort_key
from magpie.core.classifier import validate_folder_name
from magpie.models import (
    Category,
    CategoryPreset,
    ClassesPreset,
    LabelsPreset,
    OperationKind,
    SortPreset,
)
from magpie.ui.preset_editors import (
    CategoryPresetEditor,
    ClassesPresetEditor,
    LabelsPresetEditor,
)
from magpie.ui.widgets import PresetItem, PresetListView


RESERVED_SHORTCUTS = {"f", "0", "b", "+", "-"}
VISIBLE_SINGLE_KEYS = set(string.ascii_letters + string.digits + "-=[];',./`\\")


# ---------------------------------------------------------------------------
# CustomSortPresetEditor — name + python expression, used by 排序 tab when the
# user clicks "新建" or "编辑" on a custom sort preset row.
# ---------------------------------------------------------------------------


class CustomSortPresetEditor(QDialog):
    def __init__(self, preset: SortPreset | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑排序方案" if preset else "新建排序方案")
        self.resize(560, 420)
        self._original = preset

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit(preset.name if preset else "")
        self.name_edit.setPlaceholderText("如：按帧号 / 按修改时间倒序")
        form.addRow("方案名称", self.name_edit)
        outer.addLayout(form)

        hint = QLabel(
            "可用变量：<code>path</code>(Path) · <code>name</code> · <code>stem</code> · "
            "<code>suffix</code> · <code>mtime</code>(秒) · <code>size</code>(字节) · "
            "<code>re</code>。<br>表达式将作为 <code>sorted(key=...)</code> 调用，"
            "通常返回数字或元组。"
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        examples = QLabel(
            "示例：<br>"
            "&nbsp;&nbsp;<code>(int(re.search(r'\\d+', stem).group() or 0), name)</code> — 按文件名第一个数字排序<br>"
            "&nbsp;&nbsp;<code>mtime</code> — 按修改时间升序<br>"
            "&nbsp;&nbsp;<code>-size</code> — 按文件大小降序"
        )
        examples.setTextFormat(Qt.TextFormat.RichText)
        examples.setStyleSheet("color: #6b7280; font-size: 11px;")
        examples.setWordWrap(True)
        outer.addWidget(examples)

        self.expr_edit = QPlainTextEdit(preset.expression if preset else "")
        self.expr_edit.setPlaceholderText(
            "(int(re.search(r'\\d+', stem).group() or 0), name)"
        )
        self.expr_edit.setMinimumHeight(100)
        outer.addWidget(self.expr_edit, stretch=1)

        test_row = QHBoxLayout()
        test_button = QPushButton("测试表达式")
        test_button.clicked.connect(self._test_expression)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.status_label.setWordWrap(True)
        test_row.addWidget(test_button)
        test_row.addWidget(self.status_label, stretch=1)
        outer.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _test_expression(self) -> None:
        expr = self.expr_edit.toPlainText().strip()
        if not expr:
            self.status_label.setText("（空表达式）")
            self.status_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            return
        try:
            key_fn = compile_custom_sort_key(expr)
        except CustomSortError as exc:
            self.status_label.setText(f"编译失败：{exc}")
            self.status_label.setStyleSheet("color: #C62828; font-size: 11px;")
            return
        sample = [
            Path("frame_001.jpg"),
            Path("frame_010.jpg"),
            Path("preview_002.png"),
        ]
        try:
            ordered = sorted(sample, key=key_fn)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"运行失败：{type(exc).__name__}: {exc}")
            self.status_label.setStyleSheet("color: #C62828; font-size: 11px;")
            return
        self.status_label.setText("OK · 示例排序：" + " → ".join(p.name for p in ordered))
        self.status_label.setStyleSheet("color: #047857; font-size: 11px;")

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        expr = self.expr_edit.toPlainText().strip()
        if not name:
            self.status_label.setText("方案名称不能为空")
            self.status_label.setStyleSheet("color: #C62828; font-size: 11px;")
            return
        if not expr:
            self.status_label.setText("表达式不能为空")
            self.status_label.setStyleSheet("color: #C62828; font-size: 11px;")
            return
        try:
            compile_custom_sort_key(expr)
        except CustomSortError as exc:
            self.status_label.setText(f"编译失败：{exc}")
            self.status_label.setStyleSheet("color: #C62828; font-size: 11px;")
            return
        self.accept()

    def result_preset(self) -> SortPreset | None:
        name = self.name_edit.text().strip()
        expr = self.expr_edit.toPlainText().strip()
        if not name or not expr:
            return None
        preset_id = self._original.id if self._original is not None else SortPreset.new_id()
        return SortPreset(id=preset_id, name=name, kind="custom", expression=expr)


# ---------------------------------------------------------------------------
# Main preferences dialog
# ---------------------------------------------------------------------------


class PreferencesDialog(QDialog):
    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("首选项")
        self.resize(880, 600)
        self.preferences = Preferences.from_dict(preferences.to_dict())

        # Per-tab transient state.
        self._active_category_preset_id = self.preferences.active_category_preset
        if not any(p.id == self._active_category_preset_id for p in self.preferences.category_presets):
            self._active_category_preset_id = (
                self.preferences.category_presets[0].id
                if self.preferences.category_presets
                else ""
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #C62828;")
        layout.addWidget(self.error_label)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._create_categories_tab(), "类别")
        self.tabs.addTab(self._create_folders_tab(), "目录")
        self.tabs.addTab(self._create_sort_tab(), "排序")
        self.tabs.addTab(self._create_display_tab(), "显示")
        self.tabs.addTab(self._create_behavior_tab(), "行为")
        self.tabs.addTab(self._create_import_export_tab(), "导入/导出")
        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("应用")
        layout.addWidget(buttons)

    # ===================================================================
    # 类别 tab
    # ===================================================================

    def _create_categories_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(QLabel("<b>类别方案</b>"))
        layout.addWidget(self._make_hint(
            "管理多套类别。选中某个方案，下面的表格就编辑该方案的类别。"
        ))

        self.category_preset_view = PresetListView(new_button_text="+ 新建方案…")
        self.category_preset_view.setMinimumHeight(160)
        self.category_preset_view.selectionChanged.connect(self._on_category_preset_selected)
        self.category_preset_view.requestNew.connect(self._on_category_preset_new)
        self.category_preset_view.requestEdit.connect(self._on_category_preset_rename)
        self.category_preset_view.requestDuplicate.connect(self._on_category_preset_duplicate)
        self.category_preset_view.requestDelete.connect(self._on_category_preset_delete)
        layout.addWidget(self.category_preset_view, stretch=1)

        layout.addWidget(QLabel(""))
        self.category_table_title = QLabel("")
        self.category_table_title.setStyleSheet("font-weight: 600; color: #1f2937;")
        layout.addWidget(self.category_table_title)
        layout.addWidget(self._make_hint(
            "可拖动整行调整顺序。双击颜色列可选择类别颜色。"
        ))

        self.category_table = QTableWidget(0, 4)
        self.category_table.setHorizontalHeaderLabels(
            ["快捷键", "类别文件夹名", "显示名称", "颜色"]
        )
        header = self.category_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.category_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.category_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.category_table.setDragEnabled(True)
        self.category_table.setAcceptDrops(True)
        self.category_table.viewport().setAcceptDrops(True)
        self.category_table.setDragDropOverwriteMode(False)
        self.category_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.category_table.verticalHeader().setVisible(True)
        self.category_table.verticalHeader().setSectionsMovable(False)
        self.category_table.itemChanged.connect(self._on_category_item_changed)
        self.category_table.cellDoubleClicked.connect(self._on_category_cell_double_clicked)
        layout.addWidget(self.category_table, stretch=2)

        row = QHBoxLayout()
        add_button = QPushButton("添加类别")
        delete_button = QPushButton("删除选中类别")
        add_button.clicked.connect(self._add_category_row)
        delete_button.clicked.connect(self._delete_selected_category)
        row.addWidget(add_button)
        row.addWidget(delete_button)
        row.addStretch()
        layout.addLayout(row)

        self._refresh_category_preset_view()
        self._populate_category_table_from_active_preset()
        return tab

    def _refresh_category_preset_view(self) -> None:
        items = [
            PresetItem(
                id=p.id,
                title=p.name,
                subtitle=f"{len(p.categories)} 类别",
                icon="📁",
                builtin=False,
            )
            for p in self.preferences.category_presets
        ]
        self.category_preset_view.set_presets(items, self._active_category_preset_id)

    def _populate_category_table_from_active_preset(self) -> None:
        preset = self._find_category_preset(self._active_category_preset_id)
        self.category_table_title.setText(
            f"编辑方案：「{preset.name if preset else '（无）'}」"
        )
        self.category_table.blockSignals(True)
        try:
            self.category_table.setRowCount(0)
            if preset:
                for category in preset.categories:
                    self._add_category_row(category, mark_clean=True)
        finally:
            self.category_table.blockSignals(False)
        self._highlight_shortcut_conflicts()

    def _on_category_preset_selected(self, preset_id: str) -> None:
        # Persist the current table edits back to the old active preset first.
        self._sync_table_to_active_preset()
        self._active_category_preset_id = preset_id
        self._populate_category_table_from_active_preset()
        # Update count subtitles to reflect any edits.
        self._refresh_category_preset_view()

    def _on_category_preset_new(self) -> None:
        editor = CategoryPresetEditor(parent=self)
        if editor.exec():
            preset = editor.result_preset()
            if preset is None:
                return
            self._sync_table_to_active_preset()
            self.preferences.category_presets.append(preset)
            self._active_category_preset_id = preset.id
            self._refresh_category_preset_view()
            self._populate_category_table_from_active_preset()

    def _on_category_preset_rename(self, preset_id: str) -> None:
        preset = self._find_category_preset(preset_id)
        if preset is None:
            return
        editor = CategoryPresetEditor(preset=preset, parent=self)
        if editor.exec():
            result = editor.result_preset()
            if result is None:
                return
            preset.name = result.name
            self._refresh_category_preset_view()
            if preset.id == self._active_category_preset_id:
                self.category_table_title.setText(f"编辑方案：「{preset.name}」")

    def _on_category_preset_duplicate(self, preset_id: str) -> None:
        original = self._find_category_preset(preset_id)
        if original is None:
            return
        self._sync_table_to_active_preset()
        clone = CategoryPreset(
            id=CategoryPreset.new_id(),
            name=f"{original.name} 副本",
            categories=[Category(**c.to_dict()) for c in original.categories],
        )
        self.preferences.category_presets.append(clone)
        self._active_category_preset_id = clone.id
        self._refresh_category_preset_view()
        self._populate_category_table_from_active_preset()

    def _on_category_preset_delete(self, preset_id: str) -> None:
        if len(self.preferences.category_presets) <= 1:
            QMessageBox.information(self, "无法删除", "至少需要保留一个类别方案。")
            return
        preset = self._find_category_preset(preset_id)
        if preset is None:
            return
        if QMessageBox.question(
            self, "确认删除",
            f"确定删除方案「{preset.name}」？此操作不可撤销。",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.preferences.category_presets = [
            p for p in self.preferences.category_presets if p.id != preset_id
        ]
        if self._active_category_preset_id == preset_id:
            self._active_category_preset_id = self.preferences.category_presets[0].id
        self._refresh_category_preset_view()
        self._populate_category_table_from_active_preset()

    def _find_category_preset(self, preset_id: str) -> CategoryPreset | None:
        for preset in self.preferences.category_presets:
            if preset.id == preset_id:
                return preset
        return None

    def _sync_table_to_active_preset(self) -> None:
        preset = self._find_category_preset(self._active_category_preset_id)
        if preset is None:
            return
        preset.categories = self._collect_categories_from_table()

    # ---- Category table helpers (preserved from old impl) ----

    def _add_category_row(self, category: Category | None = None, mark_clean: bool = False) -> None:
        self.category_table.blockSignals(True)
        try:
            row = self.category_table.rowCount()
            self.category_table.insertRow(row)
            category = category or Category(
                key=str(row + 1),
                folder_name=f"class_{row + 1}",
                display_name=f"class_{row + 1}",
                color=DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)],
            )
            display_value = category.display_name or category.folder_name
            synced = (
                not category.display_name
                or category.display_name == category.folder_name
            )
            key_item = QTableWidgetItem(category.key)
            folder_item = QTableWidgetItem(category.folder_name)
            display_item = QTableWidgetItem(display_value)
            display_item.setData(Qt.ItemDataRole.UserRole, bool(synced))
            self.category_table.setItem(row, 0, key_item)
            self.category_table.setItem(row, 1, folder_item)
            self.category_table.setItem(row, 2, display_item)
            self._set_color_cell(row, category.color or DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)])
        finally:
            self.category_table.blockSignals(False)
        self._highlight_shortcut_conflicts()
        if not mark_clean:
            # Mutated: refresh the count subtitle on the preset row.
            self._sync_table_to_active_preset()
            self._refresh_category_preset_view()

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
        self.category_table.setItem(row, 3, item)

    def _on_category_cell_double_clicked(self, row: int, column: int) -> None:
        if column != 3:
            return
        item = self.category_table.item(row, column)
        current = item.text() if item else DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)]
        chosen = QColorDialog.getColor(QColor(current), self, "选择类别颜色")
        if chosen.isValid():
            self.category_table.blockSignals(True)
            try:
                self._set_color_cell(row, chosen.name())
            finally:
                self.category_table.blockSignals(False)
            self._sync_table_to_active_preset()

    def _on_category_item_changed(self, item: QTableWidgetItem) -> None:
        column = item.column()
        if column == 0:
            self._highlight_shortcut_conflicts()
        elif column == 1:
            display_item = self.category_table.item(item.row(), 2)
            if display_item is None:
                return
            synced_flag = display_item.data(Qt.ItemDataRole.UserRole)
            synced = bool(synced_flag) if synced_flag is not None else True
            if synced or not display_item.text().strip():
                self.category_table.blockSignals(True)
                try:
                    display_item.setText(item.text())
                    display_item.setData(Qt.ItemDataRole.UserRole, True)
                finally:
                    self.category_table.blockSignals(False)
        elif column == 2:
            folder_item = self.category_table.item(item.row(), 1)
            same_as_folder = bool(folder_item) and folder_item.text() == item.text()
            item.setData(Qt.ItemDataRole.UserRole, same_as_folder)
        self._sync_table_to_active_preset()

    def _highlight_shortcut_conflicts(self) -> None:
        seen: dict[str, list[int]] = {}
        for row in range(self.category_table.rowCount()):
            item = self.category_table.item(row, 0)
            if not item:
                continue
            seen.setdefault(item.text().strip(), []).append(row)
        for value, rows in seen.items():
            conflict = len(rows) > 1 and value != ""
            for row in rows:
                item = self.category_table.item(row, 0)
                if not item:
                    continue
                if conflict:
                    item.setBackground(QBrush(QColor("#fecaca")))
                    item.setToolTip("快捷键与其他行重复")
                else:
                    item.setBackground(QBrush())
                    item.setToolTip("")

    def _delete_selected_category(self) -> None:
        row = self.category_table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "确认删除", "确定删除选中的类别吗？") == QMessageBox.StandardButton.Yes:
            self.category_table.removeRow(row)
            self._highlight_shortcut_conflicts()
            self._sync_table_to_active_preset()
            self._refresh_category_preset_view()

    def _collect_categories_from_table(self) -> list[Category]:
        categories: list[Category] = []
        for row in range(self.category_table.rowCount()):
            key = self._table_text(row, 0)
            folder_name = self._table_text(row, 1)
            display_name = self._table_text(row, 2) or folder_name
            color_item = self.category_table.item(row, 3)
            color = (
                color_item.text().strip()
                if color_item and color_item.text().strip()
                else DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)]
            )
            categories.append(
                Category(key=key, folder_name=folder_name, display_name=display_name, color=color)
            )
        return categories

    def _table_text(self, row: int, column: int) -> str:
        item = self.category_table.item(row, column)
        return item.text().strip() if item else ""

    def _validate_categories(self, categories: list[Category]) -> str | None:
        seen_keys: set[str] = set()
        seen_folders: set[str] = set()
        for category in categories:
            key = category.key
            if len(key) != 1 or key not in VISIBLE_SINGLE_KEYS:
                return f"快捷键 {key or '<空>'} 无效：仅支持单个可见字符"
            if key.lower() in RESERVED_SHORTCUTS:
                return f"快捷键 {key} 与系统快捷键冲突"
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

    # ===================================================================
    # 目录 tab — output template + labels presets + classes presets
    # ===================================================================

    def _create_folders_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        outer.addWidget(self._make_hint(
            "下面是全局默认；每个源目录可在 <b>分类 → 本目录设置</b> 单独覆盖。"
        ))

        # Output template
        outer.addWidget(QLabel("<b>输出目录模板</b>"))
        self.output_template_edit = QLineEdit(self.preferences.output_dir_template)
        self.output_template_edit.setPlaceholderText("{parent}/{name}_filtered")
        self.output_template_edit.textChanged.connect(self._refresh_output_preview)
        outer.addWidget(self.output_template_edit)
        self.output_template_hint = QLabel(
            "可用变量：<code>{folder}</code> <code>{name}</code> "
            "<code>{parent}</code> <code>{stem}</code>"
        )
        self.output_template_hint.setTextFormat(Qt.TextFormat.RichText)
        self.output_template_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        outer.addWidget(self.output_template_hint)
        self.output_template_preview = QLabel("")
        self.output_template_preview.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.output_template_preview.setWordWrap(True)
        outer.addWidget(self.output_template_preview)

        # Labels presets
        labels_group = QGroupBox("标签目录方案")
        labels_layout = QVBoxLayout(labels_group)
        labels_layout.setContentsMargins(10, 10, 10, 10)
        labels_layout.setSpacing(6)
        labels_layout.addWidget(self._make_hint(
            "每个方案是一个路径（绝对或相对源目录）。选择哪个作为默认在「目录」tab 下方决定，"
            "或在「本目录设置」里按项目覆盖。"
        ))
        self.labels_preset_view = PresetListView(new_button_text="+ 新建标签方案…")
        self.labels_preset_view.selectionChanged.connect(self._on_labels_selection_changed)
        self.labels_preset_view.requestNew.connect(self._on_labels_preset_new)
        self.labels_preset_view.requestEdit.connect(self._on_labels_preset_edit)
        self.labels_preset_view.requestDuplicate.connect(self._on_labels_preset_duplicate)
        self.labels_preset_view.requestDelete.connect(self._on_labels_preset_delete)
        labels_layout.addWidget(self.labels_preset_view)
        outer.addWidget(labels_group)

        # Classes presets
        classes_group = QGroupBox("classes.txt 方案（仅内联）")
        classes_layout = QVBoxLayout(classes_group)
        classes_layout.setContentsMargins(10, 10, 10, 10)
        classes_layout.setSpacing(6)
        classes_layout.addWidget(self._make_hint(
            "每个方案是一份类别名列表（一行一个，从 classes.txt 复制粘贴）。"
            "不读取磁盘文件，方案可在不同项目间复用。"
        ))
        self.classes_preset_view = PresetListView(new_button_text="+ 新建 classes 方案…")
        self.classes_preset_view.selectionChanged.connect(self._on_classes_selection_changed)
        self.classes_preset_view.requestNew.connect(self._on_classes_preset_new)
        self.classes_preset_view.requestEdit.connect(self._on_classes_preset_edit)
        self.classes_preset_view.requestDuplicate.connect(self._on_classes_preset_duplicate)
        self.classes_preset_view.requestDelete.connect(self._on_classes_preset_delete)
        classes_layout.addWidget(self.classes_preset_view)
        outer.addWidget(classes_group)

        outer.addStretch()

        self._refresh_labels_preset_view()
        self._refresh_classes_preset_view()
        self._refresh_output_preview()
        return tab

    def _preview_folder(self) -> Path:
        parent = self.parent()
        state = getattr(parent, "state", None)
        if state is not None:
            opened = getattr(state, "image_folder", "")
            if opened:
                return Path(opened)
        return Path("/data/dataset_A")

    def _refresh_output_preview(self) -> None:
        if not hasattr(self, "output_template_preview"):
            return
        folder = self._preview_folder()
        template = self.output_template_edit.text().strip() or "{parent}/{name}_filtered"
        try:
            rendered = template.format(
                folder=str(folder),
                name=folder.name,
                parent=str(folder.parent),
                stem=folder.stem,
            )
            normalized = os.path.normpath(rendered)
            self.output_template_preview.setText(
                f"预览：{folder} → <code>{normalized}</code>"
            )
            self.output_template_preview.setTextFormat(Qt.TextFormat.RichText)
            self.output_template_preview.setStyleSheet("color: #6b7280; font-size: 11px;")
        except Exception as exc:  # noqa: BLE001
            self.output_template_preview.setText(f"模板错误：{exc}")
            self.output_template_preview.setStyleSheet("color: #C62828; font-size: 11px;")

    # ---- Labels preset helpers ----

    def _current_default_labels_id(self) -> str:
        sel = (self.preferences.default_labels_selection or "none").strip()
        if sel.startswith("preset:"):
            return sel.split(":", 1)[1]
        return ""

    def _refresh_labels_preset_view(self) -> None:
        items = [
            PresetItem(
                id=p.id,
                title=p.name,
                subtitle=p.path or "(空)",
                icon="📁",
                builtin=False,
            )
            for p in self.preferences.labels_presets
        ]
        self.labels_preset_view.set_presets(items, self._current_default_labels_id())

    def _on_labels_selection_changed(self, preset_id: str) -> None:
        self.preferences.default_labels_selection = f"preset:{preset_id}"

    def _on_labels_preset_new(self) -> None:
        editor = LabelsPresetEditor(preview_folder=self._preview_folder(), parent=self)
        if editor.exec():
            preset = editor.result_preset()
            if preset is None:
                return
            self.preferences.labels_presets.append(preset)
            self.preferences.default_labels_selection = f"preset:{preset.id}"
            self._refresh_labels_preset_view()

    def _on_labels_preset_edit(self, preset_id: str) -> None:
        preset = next((p for p in self.preferences.labels_presets if p.id == preset_id), None)
        if preset is None:
            return
        editor = LabelsPresetEditor(preset=preset, preview_folder=self._preview_folder(), parent=self)
        if editor.exec():
            updated = editor.result_preset()
            if updated is None:
                return
            preset.name = updated.name
            preset.path = updated.path
            self._refresh_labels_preset_view()

    def _on_labels_preset_duplicate(self, preset_id: str) -> None:
        original = next((p for p in self.preferences.labels_presets if p.id == preset_id), None)
        if original is None:
            return
        clone = LabelsPreset(
            id=LabelsPreset.new_id(), name=f"{original.name} 副本", path=original.path
        )
        self.preferences.labels_presets.append(clone)
        self._refresh_labels_preset_view()

    def _on_labels_preset_delete(self, preset_id: str) -> None:
        preset = next((p for p in self.preferences.labels_presets if p.id == preset_id), None)
        if preset is None:
            return
        if QMessageBox.question(self, "确认删除", f"确定删除方案「{preset.name}」？") != QMessageBox.StandardButton.Yes:
            return
        self.preferences.labels_presets = [
            p for p in self.preferences.labels_presets if p.id != preset_id
        ]
        if self._current_default_labels_id() == preset_id:
            self.preferences.default_labels_selection = "none"
        self._refresh_labels_preset_view()

    # ---- Classes preset helpers ----

    def _current_default_classes_id(self) -> str:
        sel = (self.preferences.default_classes_selection or "none").strip()
        if sel.startswith("preset:"):
            return sel.split(":", 1)[1]
        return ""

    def _refresh_classes_preset_view(self) -> None:
        items = [
            PresetItem(
                id=p.id,
                title=p.name,
                subtitle=f"{len(p.names)} 类别",
                icon="📋",
                builtin=False,
            )
            for p in self.preferences.classes_presets
        ]
        self.classes_preset_view.set_presets(items, self._current_default_classes_id())

    def _on_classes_selection_changed(self, preset_id: str) -> None:
        self.preferences.default_classes_selection = f"preset:{preset_id}"

    def _on_classes_preset_new(self) -> None:
        editor = ClassesPresetEditor(parent=self)
        if editor.exec():
            preset = editor.result_preset()
            if preset is None:
                return
            self.preferences.classes_presets.append(preset)
            self.preferences.default_classes_selection = f"preset:{preset.id}"
            self._refresh_classes_preset_view()

    def _on_classes_preset_edit(self, preset_id: str) -> None:
        preset = next((p for p in self.preferences.classes_presets if p.id == preset_id), None)
        if preset is None:
            return
        editor = ClassesPresetEditor(preset=preset, parent=self)
        if editor.exec():
            updated = editor.result_preset()
            if updated is None:
                return
            preset.name = updated.name
            preset.names = list(updated.names)
            self._refresh_classes_preset_view()

    def _on_classes_preset_duplicate(self, preset_id: str) -> None:
        original = next((p for p in self.preferences.classes_presets if p.id == preset_id), None)
        if original is None:
            return
        clone = ClassesPreset(
            id=ClassesPreset.new_id(),
            name=f"{original.name} 副本",
            names=list(original.names),
        )
        self.preferences.classes_presets.append(clone)
        self._refresh_classes_preset_view()

    def _on_classes_preset_delete(self, preset_id: str) -> None:
        preset = next((p for p in self.preferences.classes_presets if p.id == preset_id), None)
        if preset is None:
            return
        if QMessageBox.question(self, "确认删除", f"确定删除方案「{preset.name}」？") != QMessageBox.StandardButton.Yes:
            return
        self.preferences.classes_presets = [
            p for p in self.preferences.classes_presets if p.id != preset_id
        ]
        if self._current_default_classes_id() == preset_id:
            self.preferences.default_classes_selection = "none"
        self._refresh_classes_preset_view()

    # ===================================================================
    # 排序 tab
    # ===================================================================

    def _create_sort_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        outer.addWidget(QLabel("<b>默认排序方案</b>"))
        outer.addWidget(self._make_hint(
            "前三项是内置方案；下方是用户自定义（Python 表达式，沙箱执行）。"
        ))

        self.sort_preset_view = PresetListView(new_button_text="+ 新建自定义方案…")
        self.sort_preset_view.selectionChanged.connect(self._on_sort_selection_changed)
        self.sort_preset_view.requestNew.connect(self._on_sort_preset_new)
        self.sort_preset_view.requestEdit.connect(self._on_sort_preset_edit)
        self.sort_preset_view.requestDuplicate.connect(self._on_sort_preset_duplicate)
        self.sort_preset_view.requestDelete.connect(self._on_sort_preset_delete)
        outer.addWidget(self.sort_preset_view, stretch=1)

        # Sort direction
        direction_group = QGroupBox("排序顺序")
        dir_layout = QHBoxLayout(direction_group)
        dir_layout.setContentsMargins(10, 10, 10, 10)
        dir_layout.setSpacing(16)
        self.sort_asc_radio = QRadioButton("升序")
        self.sort_desc_radio = QRadioButton("降序")
        if self.preferences.sort_descending:
            self.sort_desc_radio.setChecked(True)
        else:
            self.sort_asc_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.sort_asc_radio)
        group.addButton(self.sort_desc_radio)
        dir_layout.addWidget(self.sort_asc_radio)
        dir_layout.addWidget(self.sort_desc_radio)
        dir_layout.addStretch()
        outer.addWidget(direction_group)

        self._refresh_sort_preset_view()
        return tab

    def _refresh_sort_preset_view(self) -> None:
        items = []
        for preset in self.preferences.sort_presets:
            if preset.kind == "builtin":
                subtitle = {
                    "natural": "1, 2, 10",
                    "name": "1, 10, 2",
                    "mtime": "最新→最旧（升序）",
                }.get(preset.field, "")
                icon = {"natural": "📄", "name": "📝", "mtime": "🕒"}.get(preset.field, "📄")
                items.append(PresetItem(
                    id=preset.id, title=preset.name, subtitle=subtitle, icon=icon, builtin=True,
                ))
            else:
                expr = preset.expression or ""
                if len(expr) > 60:
                    expr = expr[:57] + "…"
                items.append(PresetItem(
                    id=preset.id, title=preset.name, subtitle=expr, icon="🐍", builtin=False,
                ))
        self.sort_preset_view.set_presets(items, self.preferences.active_sort_preset_id)

    def _on_sort_selection_changed(self, preset_id: str) -> None:
        self.preferences.active_sort_preset_id = preset_id

    def _on_sort_preset_new(self) -> None:
        editor = CustomSortPresetEditor(parent=self)
        if editor.exec():
            preset = editor.result_preset()
            if preset is None:
                return
            self.preferences.sort_presets.append(preset)
            self.preferences.active_sort_preset_id = preset.id
            self._refresh_sort_preset_view()

    def _on_sort_preset_edit(self, preset_id: str) -> None:
        preset = next((p for p in self.preferences.sort_presets if p.id == preset_id), None)
        if preset is None or preset.kind == "builtin":
            return
        editor = CustomSortPresetEditor(preset=preset, parent=self)
        if editor.exec():
            updated = editor.result_preset()
            if updated is None:
                return
            preset.name = updated.name
            preset.expression = updated.expression
            self._refresh_sort_preset_view()

    def _on_sort_preset_duplicate(self, preset_id: str) -> None:
        original = next((p for p in self.preferences.sort_presets if p.id == preset_id), None)
        if original is None or original.kind == "builtin":
            return
        clone = SortPreset(
            id=SortPreset.new_id(),
            name=f"{original.name} 副本",
            kind="custom",
            expression=original.expression,
        )
        self.preferences.sort_presets.append(clone)
        self._refresh_sort_preset_view()

    def _on_sort_preset_delete(self, preset_id: str) -> None:
        preset = next((p for p in self.preferences.sort_presets if p.id == preset_id), None)
        if preset is None or preset.kind == "builtin":
            return
        if QMessageBox.question(self, "确认删除", f"确定删除方案「{preset.name}」？") != QMessageBox.StandardButton.Yes:
            return
        self.preferences.sort_presets = [
            p for p in self.preferences.sort_presets if p.id != preset_id
        ]
        if self.preferences.active_sort_preset_id == preset_id:
            self.preferences.active_sort_preset_id = "builtin:natural"
        self._refresh_sort_preset_view()

    # ===================================================================
    # 显示 tab
    # ===================================================================

    def _create_display_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.autoplay_slider = QSlider(Qt.Orientation.Horizontal)
        self.autoplay_slider.setRange(50, 2000)
        self.autoplay_slider.setValue(self.preferences.autoplay_interval_ms)
        self.autoplay_spin = QSpinBox()
        self.autoplay_spin.setRange(50, 2000)
        self.autoplay_spin.setValue(self.preferences.autoplay_interval_ms)
        self.autoplay_slider.valueChanged.connect(self.autoplay_spin.setValue)
        self.autoplay_spin.valueChanged.connect(self.autoplay_slider.setValue)
        autoplay_row = QHBoxLayout()
        autoplay_row.addWidget(self.autoplay_slider)
        autoplay_row.addWidget(self.autoplay_spin)
        layout.addRow("自动播放间隔(ms)", autoplay_row)

        self.show_bboxes_check = QCheckBox("默认显示 BBox")
        self.show_bboxes_check.setChecked(self.preferences.show_bboxes)
        layout.addRow(self.show_bboxes_check)

        self.show_classified_check = QCheckBox("显示已分类标记")
        self.show_classified_check.setChecked(self.preferences.show_classified_marker)
        layout.addRow(self.show_classified_check)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.theme_combo.setCurrentText(self.preferences.theme)
        layout.addRow("主题", self.theme_combo)
        return tab

    # ===================================================================
    # 行为 tab (now also holds conflict / extensions / recursive)
    # ===================================================================

    def _create_behavior_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.operation_combo = QComboBox()
        self.operation_combo.addItem("复制", OperationKind.COPY.value)
        self.operation_combo.addItem("移动", OperationKind.MOVE.value)
        self._set_combo_by_data(self.operation_combo, self.preferences.default_operation.value)
        layout.addRow("默认操作", self.operation_combo)

        self.undo_prompt_check = QCheckBox("撤销后弹提示框")
        self.undo_prompt_check.setChecked(self.preferences.undo_prompt)
        layout.addRow(self.undo_prompt_check)

        self.end_behavior_combo = QComboBox()
        self.end_behavior_combo.addItem("停留", "stay")
        self.end_behavior_combo.addItem("提示", "prompt")
        self.end_behavior_combo.addItem("循环", "loop")
        self._set_combo_by_data(self.end_behavior_combo, self.preferences.end_behavior)
        layout.addRow("到达末尾时", self.end_behavior_combo)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("每次询问", "ask")
        self.conflict_combo.addItem("自动重命名", "rename")
        self.conflict_combo.addItem("跳过", "skip")
        self.conflict_combo.addItem("覆盖", "overwrite")
        self._set_combo_by_data(self.conflict_combo, self.preferences.conflict_strategy)
        layout.addRow("目标文件已存在", self.conflict_combo)

        ext_widget = QWidget()
        ext_layout = QGridLayout(ext_widget)
        ext_layout.setContentsMargins(0, 0, 0, 0)
        ext_layout.setHorizontalSpacing(12)
        ext_layout.setVerticalSpacing(4)
        self.extension_checks: dict[str, QCheckBox] = {}
        for index, extension in enumerate(DEFAULT_EXTENSIONS):
            checkbox = QCheckBox(extension)
            checkbox.setChecked(extension in self.preferences.file_extensions)
            self.extension_checks[extension] = checkbox
            ext_layout.addWidget(checkbox, index // 4, index % 4)
        ext_layout.setColumnStretch(4, 1)
        layout.addRow("支持的文件类型", ext_widget)

        self.recursive_scan_check = QCheckBox("默认递归扫描子目录")
        self.recursive_scan_check.setChecked(self.preferences.recursive_scan)
        layout.addRow(self.recursive_scan_check)

        self.remember_recursive_check = QCheckBox("记住递归扫描选择（不再询问）")
        self.remember_recursive_check.setChecked(self.preferences.remember_recursive_scan)
        layout.addRow(self.remember_recursive_check)
        return tab

    # ===================================================================
    # 导入/导出 tab
    # ===================================================================

    def _create_import_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        export_button = QPushButton("导出预设")
        import_button = QPushButton("导入预设")
        reset_button = QPushButton("重置为默认")
        export_button.clicked.connect(self._export_preset)
        import_button.clicked.connect(self._import_preset)
        reset_button.clicked.connect(self._reset_preferences)
        layout.addWidget(export_button)
        layout.addWidget(import_button)
        layout.addWidget(reset_button)
        layout.addStretch()
        return tab

    # ===================================================================
    # Misc helpers
    # ===================================================================

    def _make_hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet("color: #6b7280; font-size: 11px;")
        label.setWordWrap(True)
        return label

    def _set_combo_by_data(self, combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    # ===================================================================
    # Apply / accept — gather all UI state into self.preferences
    # ===================================================================

    def _update_preferences_from_ui(self) -> bool:
        # Sync the category table edits back to the active preset first.
        self._sync_table_to_active_preset()

        # Validate every category preset.
        for preset in self.preferences.category_presets:
            error = self._validate_categories(preset.categories)
            if error:
                self.error_label.setText(
                    f"方案「{preset.name}」校验失败：{error}"
                )
                return False
        self.preferences.active_category_preset = self._active_category_preset_id

        # Output template — try rendering against a sample folder to validate.
        template = self.output_template_edit.text().strip() or "{parent}/{name}_filtered"
        try:
            sample = self._preview_folder()
            template.format(
                folder=str(sample), name=sample.name,
                parent=str(sample.parent), stem=sample.stem,
            )
        except Exception as exc:  # noqa: BLE001
            self.error_label.setText(f"输出目录模板无效：{exc}")
            return False
        self.preferences.output_dir_template = template

        # Labels / classes: presets already mutated live via editor handlers;
        # default selection persisted on selectionChanged. Nothing extra here.

        # Sort direction
        self.preferences.sort_descending = self.sort_desc_radio.isChecked()
        # active_sort_preset_id persisted live.

        # Display
        self.preferences.autoplay_interval_ms = self.autoplay_spin.value()
        self.preferences.show_bboxes = self.show_bboxes_check.isChecked()
        self.preferences.show_classified_marker = self.show_classified_check.isChecked()
        self.preferences.theme = self.theme_combo.currentText()

        # Behavior
        self.preferences.default_operation = OperationKind(self.operation_combo.currentData())
        self.preferences.undo_prompt = self.undo_prompt_check.isChecked()
        self.preferences.end_behavior = self.end_behavior_combo.currentData()
        self.preferences.conflict_strategy = self.conflict_combo.currentData()
        self.preferences.recursive_scan = self.recursive_scan_check.isChecked()
        self.preferences.remember_recursive_scan = self.remember_recursive_check.isChecked()
        self.preferences.file_extensions = [
            extension
            for extension, checkbox in self.extension_checks.items()
            if checkbox.isChecked()
        ]
        self.error_label.setText("")
        return True

    def apply(self) -> None:
        if self._update_preferences_from_ui():
            self.preferences.save()

    def accept(self) -> None:
        if self._update_preferences_from_ui():
            self.preferences.save()
            super().accept()

    # ---- Import/export ----

    def _export_preset(self) -> None:
        if not self._update_preferences_from_ui():
            return
        file, _ = QFileDialog.getSaveFileName(
            self,
            "导出预设",
            "magpie.magpie-preset.json",
            "Magpie Preset (*.magpie-preset.json)",
        )
        if file:
            Path(file).write_text(
                json.dumps(self.preferences.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _import_preset(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self,
            "导入预设",
            "",
            "Magpie Preset (*.magpie-preset.json *.json)",
        )
        if not file:
            return
        if QMessageBox.question(self, "确认导入", "导入会覆盖当前设置，是否继续？") != QMessageBox.StandardButton.Yes:
            return
        data = json.loads(Path(file).read_text(encoding="utf-8"))
        self.preferences = Preferences.from_dict(data)
        QMessageBox.information(self, "导入成功", "预设已导入，点击确定保存并生效。")
        self.accept()

    def _reset_preferences(self) -> None:
        if QMessageBox.question(self, "确认重置", "确定清空所有偏好并恢复默认吗？") == QMessageBox.StandardButton.Yes:
            self.preferences = Preferences.default()
            self.accept()
