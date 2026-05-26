from __future__ import annotations

import json
import string
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from magpie.config import DEFAULT_EXTENSIONS, DEFAULT_PALETTE, Preferences
from magpie.core.classifier import validate_folder_name
from magpie.models import Category, OperationKind


RESERVED_SHORTCUTS = {"f", "0", "b", "+", "-"}
VISIBLE_SINGLE_KEYS = set(string.ascii_letters + string.digits + "-=[];',./`\\")


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
        self.tabs.addTab(self._create_folders_tab(), "文件夹")
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

    def _create_categories_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.category_table = QTableWidget(0, 3)
        self.category_table.setHorizontalHeaderLabels(["快捷键", "类别文件夹名", "显示名称"])
        self.category_table.horizontalHeader().setStretchLastSection(True)
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
        return tab

    def _create_folders_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.source_dir_edit = self._path_row(
            layout,
            "默认图片来源目录",
            self.preferences.source_dir,
            "选择默认图片来源目录",
        )
        self.output_dir_edit = self._path_row(layout, "默认输出目录", self.preferences.output_dir, "选择输出目录")
        self.labels_dir_edit = self._path_row(layout, "默认标签目录", self.preferences.labels_dir, "选择标签目录")
        self.classes_path_edit = self._file_row(layout, "classes.txt 路径", self.preferences.classes_path)

        self.recursive_scan_check = QCheckBox("递归扫描子目录")
        self.recursive_scan_check.setChecked(self.preferences.recursive_scan)
        layout.addRow(self.recursive_scan_check)

        self.remember_recursive_check = QCheckBox("记住递归扫描选择")
        self.remember_recursive_check.setChecked(self.preferences.remember_recursive_scan)
        layout.addRow(self.remember_recursive_check)
        return tab

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

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("每次询问", "ask")
        self.conflict_combo.addItem("自动重命名", "rename")
        self.conflict_combo.addItem("跳过", "skip")
        self.conflict_combo.addItem("覆盖", "overwrite")
        self._set_combo_by_data(self.conflict_combo, self.preferences.conflict_strategy)
        layout.addRow("目标文件已存在", self.conflict_combo)

        self.sort_combo = QComboBox()
        for label, value in [
            ("文件名（自然排序）", "natural"),
            ("文件名升序", "name_asc"),
            ("文件名降序", "name_desc"),
            ("修改时间升序", "mtime_asc"),
            ("修改时间降序", "mtime_desc"),
            ("大小升序", "size_asc"),
            ("大小降序", "size_desc"),
        ]:
            self.sort_combo.addItem(label, value)
        self._set_combo_by_data(self.sort_combo, self.preferences.sort_strategy)
        layout.addRow("排序策略", self.sort_combo)

        ext_widget = QWidget()
        ext_layout = QHBoxLayout(ext_widget)
        ext_layout.setContentsMargins(0, 0, 0, 0)
        self.extension_checks: dict[str, QCheckBox] = {}
        for extension in DEFAULT_EXTENSIONS:
            checkbox = QCheckBox(extension)
            checkbox.setChecked(extension in self.preferences.file_extensions)
            self.extension_checks[extension] = checkbox
            ext_layout.addWidget(checkbox)
        layout.addRow("支持的文件类型", ext_widget)
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
        row = self.category_table.rowCount()
        self.category_table.insertRow(row)
        category = category or Category(
            key=str(row + 1),
            folder_name=f"class_{row + 1}",
            display_name=f"class_{row + 1}",
            color=DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)],
        )
        for column, value in enumerate([category.key, category.folder_name, category.display_name]):
            item = QTableWidgetItem(value)
            self.category_table.setItem(row, column, item)

    def _delete_selected_category(self) -> None:
        row = self.category_table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "确认删除", "确定删除选中的类别吗？") == QMessageBox.StandardButton.Yes:
            self.category_table.removeRow(row)

    def _collect_categories(self) -> list[Category]:
        categories: list[Category] = []
        for row in range(self.category_table.rowCount()):
            key = self._table_text(row, 0)
            folder_name = self._table_text(row, 1)
            display_name = self._table_text(row, 2) or folder_name
            color = DEFAULT_PALETTE[row % len(DEFAULT_PALETTE)]
            categories.append(Category(key=key, folder_name=folder_name, display_name=display_name, color=color))
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
        self.preferences.source_dir = self.source_dir_edit.text().strip()
        self.preferences.output_dir = self.output_dir_edit.text().strip()
        self.preferences.labels_dir = self.labels_dir_edit.text().strip()
        self.preferences.classes_path = self.classes_path_edit.text().strip()
        self.preferences.autoplay_interval_ms = self.autoplay_spin.value()
        self.preferences.show_bboxes = self.show_bboxes_check.isChecked()
        self.preferences.show_classified_marker = self.show_classified_check.isChecked()
        self.preferences.theme = self.theme_combo.currentText()
        self.preferences.default_operation = OperationKind(self.operation_combo.currentData())
        self.preferences.undo_prompt = self.undo_prompt_check.isChecked()
        self.preferences.end_behavior = self.end_behavior_combo.currentData()
        self.preferences.conflict_strategy = self.conflict_combo.currentData()
        self.preferences.sort_strategy = self.sort_combo.currentData()
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
