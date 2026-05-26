from __future__ import annotations

import json
import os
import string
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
    QListWidget,
    QListWidgetItem,
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
from magpie.models import Category, CustomSortPreset, OperationKind


RESERVED_SHORTCUTS = {"f", "0", "b", "+", "-"}
VISIBLE_SINGLE_KEYS = set(string.ascii_letters + string.digits + "-=[];',./`\\")


class CustomSortPresetEditor(QDialog):
    """Edit one CustomSortPreset (name + python expression)."""

    def __init__(self, preset: CustomSortPreset | None = None, parent: QDialog | None = None) -> None:
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
            "通常返回数字或元组（元组按位比较）。"
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        examples = QLabel(
            "示例：<br>"
            "&nbsp;&nbsp;<code>(int(re.search(r'\\d+', stem).group() or 0), name)</code> — 按文件名第一个数字排序<br>"
            "&nbsp;&nbsp;<code>mtime</code> — 按修改时间升序<br>"
            "&nbsp;&nbsp;<code>-size</code> — 按文件大小降序<br>"
            "&nbsp;&nbsp;<code>(suffix, name.lower())</code> — 先按扩展名再按文件名"
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
        except Exception as exc:  # noqa: BLE001 — surface to the user
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

    def result_preset(self) -> CustomSortPreset | None:
        name = self.name_edit.text().strip()
        expr = self.expr_edit.toPlainText().strip()
        if not name or not expr:
            return None
        if self._original is not None:
            return CustomSortPreset(id=self._original.id, name=name, expression=expr)
        return CustomSortPreset(id=CustomSortPreset.new_id(), name=name, expression=expr)


class PreferencesDialog(QDialog):
    def __init__(self, preferences: Preferences, parent=None):
        super().__init__(parent)
        self.setWindowTitle("首选项")
        self.resize(840, 560)
        self.preferences = Preferences.from_dict(preferences.to_dict())

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
        self.tabs.addTab(self._create_display_tab(), "显示")
        self.tabs.addTab(self._create_behavior_tab(), "行为")
        self.tabs.addTab(self._create_scan_write_tab(), "扫描与写入")
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

    def _create_categories_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        hint = QLabel("可拖动整行调整顺序。双击颜色列可选择类别颜色。")
        hint.setStyleSheet("color: #6b7280;")
        layout.addWidget(hint)

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
        layout.addWidget(self.category_table)

        row = QHBoxLayout()
        add_button = QPushButton("添加类别")
        delete_button = QPushButton("删除选中类别")
        add_button.clicked.connect(self._add_category_row)
        delete_button.clicked.connect(self._delete_selected_category)
        row.addWidget(add_button)
        row.addWidget(delete_button)
        row.addStretch()
        layout.addLayout(row)

        for category in self.preferences.categories:
            self._add_category_row(category)
        self._highlight_shortcut_conflicts()
        return tab

    def _create_folders_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        intro = QLabel(
            "下面是<b>全局默认</b>：每打开一个图片目录都按这里的规则计算路径。"
            "<br>每个源目录都可以在 <b>分类 → 本目录设置…</b> 单独覆盖。"
        )
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setStyleSheet("color: #374151;")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # ----- Output template -----
        self.output_template_edit = QLineEdit(self.preferences.output_dir_template)
        self.output_template_edit.setPlaceholderText("{parent}/{name}_filtered")
        self.output_template_edit.textChanged.connect(self._refresh_path_previews)
        form.addRow("输出目录模板", self.output_template_edit)

        self.output_template_hint = QLabel(
            "可用变量：<code>{folder}</code> <code>{name}</code> "
            "<code>{parent}</code> <code>{stem}</code>"
        )
        self.output_template_hint.setTextFormat(Qt.TextFormat.RichText)
        self.output_template_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        form.addRow("", self.output_template_hint)

        self.output_template_preview = QLabel("")
        self.output_template_preview.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.output_template_preview.setWordWrap(True)
        form.addRow("", self.output_template_preview)

        # ----- Labels relative -----
        self.labels_relative_edit = QLineEdit(self.preferences.labels_dir_relative)
        self.labels_relative_edit.setPlaceholderText("labels")
        self.labels_relative_edit.textChanged.connect(self._refresh_path_previews)
        form.addRow("标签目录（相对源目录）", self.labels_relative_edit)

        self.labels_relative_preview = QLabel("")
        self.labels_relative_preview.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.labels_relative_preview.setWordWrap(True)
        form.addRow("", self.labels_relative_preview)

        # ----- classes.txt mode -----
        self.classes_auto_radio = QRadioButton("自动 — 使用 <标签目录>/classes.txt")
        self.classes_custom_radio = QRadioButton("自定义路径")
        if self.preferences.classes_mode == "custom":
            self.classes_custom_radio.setChecked(True)
        else:
            self.classes_auto_radio.setChecked(True)
        self.classes_auto_radio.toggled.connect(self._refresh_classes_mode_state)
        self.classes_custom_radio.toggled.connect(self._refresh_classes_mode_state)

        classes_box = QVBoxLayout()
        classes_box.setSpacing(4)
        classes_box.addWidget(self.classes_auto_radio)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(6)
        self.classes_path_edit = QLineEdit(self.preferences.classes_path)
        self.classes_path_edit.setPlaceholderText("/path/to/classes.txt")
        self.classes_path_browse = QPushButton("选择…")
        self.classes_path_browse.clicked.connect(self._choose_classes_file)
        custom_row.addWidget(self.classes_custom_radio)
        custom_row.addWidget(self.classes_path_edit, stretch=1)
        custom_row.addWidget(self.classes_path_browse)
        classes_box.addLayout(custom_row)

        self.classes_mode_hint = QLabel("")
        self.classes_mode_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.classes_mode_hint.setWordWrap(True)
        classes_box.addWidget(self.classes_mode_hint)

        form.addRow("classes.txt", classes_box)

        outer.addLayout(form)
        outer.addStretch()

        self._refresh_path_previews()
        self._refresh_classes_mode_state()
        return tab

    # ----- helpers for the 目录 tab -----

    def _preview_folder(self) -> Path:
        """The folder we use to render path previews in the 目录 tab.

        Uses the parent's currently-opened folder when available, otherwise a
        generic example path so users still see a meaningful preview.
        """
        parent = self.parent()
        folder = getattr(parent, "state", None)
        if folder is not None:
            opened = getattr(folder, "image_folder", "")
            if opened:
                return Path(opened)
        return Path("/data/dataset_A")

    def _refresh_path_previews(self) -> None:
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
        except Exception as exc:  # noqa: BLE001 — show formatting errors inline
            self.output_template_preview.setText(f"模板错误：{exc}")
            self.output_template_preview.setStyleSheet("color: #C62828; font-size: 11px;")

        relative = self.labels_relative_edit.text().strip()
        if not relative:
            self.labels_relative_preview.setText("（留空 → 不加载标签 / BBox）")
        else:
            p = Path(relative).expanduser()
            joined = p if p.is_absolute() else (folder / p)
            normalized_labels = os.path.normpath(str(joined))
            self.labels_relative_preview.setText(
                f"预览：{folder} → <code>{normalized_labels}</code>"
            )
            self.labels_relative_preview.setTextFormat(Qt.TextFormat.RichText)

    def _refresh_classes_mode_state(self) -> None:
        if not hasattr(self, "classes_custom_radio"):
            return
        custom = self.classes_custom_radio.isChecked()
        self.classes_path_edit.setEnabled(custom)
        self.classes_path_browse.setEnabled(custom)
        if custom:
            self.classes_mode_hint.setText("使用指定的 classes.txt（绝对路径）。")
            return
        labels_set = bool(self.labels_relative_edit.text().strip())
        if not labels_set:
            parent = self.parent()
            labels_set = bool(getattr(parent, "active_labels_dir", None)) if parent else False
        if labels_set:
            self.classes_mode_hint.setText(
                "将取 <标签目录>/classes.txt。如未找到，打开时会提示选择。"
            )
        else:
            self.classes_mode_hint.setText("（未设置标签目录，自动模式将不生效）")

    def _choose_classes_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 classes.txt",
            self.classes_path_edit.text(),
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            self.classes_path_edit.setText(path)
            self.classes_custom_radio.setChecked(True)

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
        return tab

    def _create_scan_write_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.sort_combo = QComboBox()
        self._rebuild_sort_combo()
        layout.addRow("默认排序字段", self.sort_combo)

        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItem("升序", False)
        self.sort_order_combo.addItem("降序", True)
        for i in range(self.sort_order_combo.count()):
            if self.sort_order_combo.itemData(i) == self.preferences.sort_descending:
                self.sort_order_combo.setCurrentIndex(i)
                break
        layout.addRow("排序顺序", self.sort_order_combo)

        self.preset_box = QGroupBox("自定义排序方案")
        preset_layout = QVBoxLayout(self.preset_box)
        preset_layout.setContentsMargins(10, 8, 10, 10)
        preset_layout.setSpacing(6)

        hint = QLabel(
            "可在此新建多个排序方案，并在上方默认排序中选择。<br>"
            "方案中可用变量：<code>path</code>(Path) · <code>name</code> · <code>stem</code> · "
            "<code>suffix</code> · <code>mtime</code>(秒) · <code>size</code>(字节) · <code>re</code>。<br>"
            "表达式将用于 <code>sorted(key=...)</code>，通常返回数字或元组。"
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint.setWordWrap(True)
        preset_layout.addWidget(hint)

        self.preset_list = QListWidget()
        self.preset_list.setMaximumHeight(140)
        self.preset_list.itemDoubleClicked.connect(lambda _it: self._on_edit_preset())
        preset_layout.addWidget(self.preset_list)

        preset_buttons = QHBoxLayout()
        add_preset_button = QPushButton("新建…")
        edit_preset_button = QPushButton("编辑…")
        delete_preset_button = QPushButton("删除")
        add_preset_button.clicked.connect(self._on_add_preset)
        edit_preset_button.clicked.connect(self._on_edit_preset)
        delete_preset_button.clicked.connect(self._on_delete_preset)
        preset_buttons.addWidget(add_preset_button)
        preset_buttons.addWidget(edit_preset_button)
        preset_buttons.addWidget(delete_preset_button)
        preset_buttons.addStretch()
        preset_layout.addLayout(preset_buttons)

        layout.addRow(self.preset_box)
        self._refresh_preset_list()

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

    def _path_row(self, layout: QFormLayout, label: str, value: str, title: str) -> QLineEdit:
        edit = QLineEdit(value)
        button = QPushButton("选择...")
        button.clicked.connect(lambda: self._choose_directory(edit, title))
        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(button)
        layout.addRow(label, row)
        return edit

    def _file_row(self, layout: QFormLayout, label: str, value: str) -> QLineEdit:
        edit = QLineEdit(value)
        button = QPushButton("选择...")
        button.clicked.connect(lambda: self._choose_file(edit))
        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(button)
        layout.addRow(label, row)
        return edit

    def _choose_directory(self, edit: QLineEdit, title: str) -> None:
        folder = QFileDialog.getExistingDirectory(self, title, edit.text())
        if folder:
            edit.setText(folder)

    def _choose_file(self, edit: QLineEdit) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "选择 classes.txt", edit.text(), "Text Files (*.txt)")
        if file:
            edit.setText(file)

    def _set_combo_by_data(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _add_category_row(self, category: Category | None = None) -> None:
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

    def _on_category_item_changed(self, item: QTableWidgetItem) -> None:
        column = item.column()
        if column == 0:
            self._highlight_shortcut_conflicts()
            return
        if column == 1:
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
            return
        if column == 2:
            folder_item = self.category_table.item(item.row(), 1)
            same_as_folder = bool(folder_item) and folder_item.text() == item.text()
            item.setData(Qt.ItemDataRole.UserRole, same_as_folder)
            return

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

    BUILT_IN_SORTS: tuple[tuple[str, str], ...] = (
        ("文件名（自然，1, 2, 10）", "natural"),
        ("文件名（字母序，1, 10, 2）", "name"),
        ("修改时间", "mtime"),
    )

    def _rebuild_sort_combo(self) -> None:
        current = self.sort_combo.currentData() if self.sort_combo.count() else None
        target = current or self.preferences.sort_strategy
        self.sort_combo.blockSignals(True)
        try:
            self.sort_combo.clear()
            for label, value in self.BUILT_IN_SORTS:
                self.sort_combo.addItem(label, value)
            if self.preferences.custom_sort_presets:
                self.sort_combo.insertSeparator(self.sort_combo.count())
                for preset in self.preferences.custom_sort_presets:
                    self.sort_combo.addItem(f"自定义 · {preset.name}", f"custom:{preset.id}")
            index = self.sort_combo.findData(target)
            if index < 0:
                index = self.sort_combo.findData("natural")
            if index >= 0:
                self.sort_combo.setCurrentIndex(index)
        finally:
            self.sort_combo.blockSignals(False)

    def _refresh_preset_list(self) -> None:
        self.preset_list.clear()
        if not self.preferences.custom_sort_presets:
            placeholder = QListWidgetItem("（暂无自定义方案，点击下方「新建…」添加）")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.preset_list.addItem(placeholder)
            return
        for preset in self.preferences.custom_sort_presets:
            preview = preset.expression.splitlines()[0] if preset.expression else "(空表达式)"
            if len(preview) > 60:
                preview = preview[:57] + "…"
            item = QListWidgetItem(f"{preset.name}  ·  {preview}")
            item.setData(Qt.ItemDataRole.UserRole, preset.id)
            item.setToolTip(preset.expression or "(空表达式)")
            self.preset_list.addItem(item)

    def _selected_preset_id(self) -> str | None:
        item = self.preset_list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return str(data) if data else None

    def _on_add_preset(self) -> None:
        editor = CustomSortPresetEditor(parent=self)
        if editor.exec():
            preset = editor.result_preset()
            if preset is None:
                return
            self.preferences.custom_sort_presets.append(preset)
            self._refresh_preset_list()
            self._rebuild_sort_combo()
            index = self.sort_combo.findData(f"custom:{preset.id}")
            if index >= 0:
                self.sort_combo.setCurrentIndex(index)

    def _on_edit_preset(self) -> None:
        preset_id = self._selected_preset_id()
        if not preset_id:
            return
        existing = next(
            (p for p in self.preferences.custom_sort_presets if p.id == preset_id), None
        )
        if existing is None:
            return
        editor = CustomSortPresetEditor(preset=existing, parent=self)
        if editor.exec():
            updated = editor.result_preset()
            if updated is None:
                return
            for idx, preset in enumerate(self.preferences.custom_sort_presets):
                if preset.id == preset_id:
                    self.preferences.custom_sort_presets[idx] = updated
                    break
            self._refresh_preset_list()
            self._rebuild_sort_combo()

    def _on_delete_preset(self) -> None:
        preset_id = self._selected_preset_id()
        if not preset_id:
            return
        existing = next(
            (p for p in self.preferences.custom_sort_presets if p.id == preset_id), None
        )
        if existing is None:
            return
        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除方案「{existing.name}」吗？",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.preferences.custom_sort_presets = [
            p for p in self.preferences.custom_sort_presets if p.id != preset_id
        ]
        # If the deleted preset was selected as default, fall back to natural.
        if self.sort_combo.currentData() == f"custom:{preset_id}":
            index = self.sort_combo.findData("natural")
            if index >= 0:
                self.sort_combo.setCurrentIndex(index)
        self._refresh_preset_list()
        self._rebuild_sort_combo()

    def _delete_selected_category(self) -> None:
        row = self.category_table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "确认删除", "确定删除选中的类别吗？") == QMessageBox.StandardButton.Yes:
            self.category_table.removeRow(row)
            self._highlight_shortcut_conflicts()

    def _collect_categories(self) -> list[Category]:
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

    def _update_preferences_from_ui(self) -> bool:
        categories = self._collect_categories()
        error = self._validate_categories(categories)
        if error:
            self.error_label.setText(error)
            return False

        self.preferences.categories = categories

        template = self.output_template_edit.text().strip() or "{parent}/{name}_filtered"
        # Validate the template against the preview folder. If formatting fails,
        # block save with a useful message.
        try:
            preview_folder = self._preview_folder()
            template.format(
                folder=str(preview_folder),
                name=preview_folder.name,
                parent=str(preview_folder.parent),
                stem=preview_folder.stem,
            )
        except Exception as exc:  # noqa: BLE001
            self.error_label.setText(f"输出目录模板无效：{exc}")
            return False
        self.preferences.output_dir_template = template
        self.preferences.labels_dir_relative = self.labels_relative_edit.text().strip()
        self.preferences.classes_mode = (
            "custom" if self.classes_custom_radio.isChecked() else "auto"
        )
        self.preferences.classes_path = self.classes_path_edit.text().strip()
        self.preferences.autoplay_interval_ms = self.autoplay_spin.value()
        self.preferences.show_bboxes = self.show_bboxes_check.isChecked()
        self.preferences.show_classified_marker = self.show_classified_check.isChecked()
        self.preferences.theme = self.theme_combo.currentText()
        self.preferences.default_operation = OperationKind(self.operation_combo.currentData())
        self.preferences.undo_prompt = self.undo_prompt_check.isChecked()
        self.preferences.end_behavior = self.end_behavior_combo.currentData()
        self.preferences.conflict_strategy = self.conflict_combo.currentData()
        sort_strategy = self.sort_combo.currentData() or "natural"
        if sort_strategy.startswith("custom:"):
            preset_id = sort_strategy.split(":", 1)[1]
            preset = next(
                (p for p in self.preferences.custom_sort_presets if p.id == preset_id),
                None,
            )
            if preset is None:
                self.error_label.setText("选中的自定义排序方案已不存在")
                return False
            try:
                compile_custom_sort_key(preset.expression)
            except CustomSortError as exc:
                self.error_label.setText(
                    f"自定义排序方案「{preset.name}」无效：{exc}"
                )
                return False
        self.preferences.sort_strategy = sort_strategy
        self.preferences.sort_descending = bool(self.sort_order_combo.currentData())
        self.preferences.recursive_scan = self.recursive_scan_check.isChecked()
        self.preferences.remember_recursive_scan = self.remember_recursive_check.isChecked()
        self.preferences.file_extensions = [
            extension for extension, checkbox in self.extension_checks.items() if checkbox.isChecked()
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
            Path(file).write_text(json.dumps(self.preferences.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

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
