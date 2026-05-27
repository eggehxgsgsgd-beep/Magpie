"""Dialog editors for category / labels / classes presets.

Sort presets are edited via ``CustomSortPresetEditor`` in
``preferences_dialog.py``; this module covers the other three:

- ``CategoryPresetEditor`` — name + full category table (shortcut/folder/
  display/color, drag-reorder, conflict highlight). Uses ``CategoryTableWidget``.
- ``LabelsPresetEditor`` — name + a relative path (typed; no directory
  picker, since the value is conceptually a relative-to-source path).
- ``ClassesPresetEditor`` — name + multi-line names (one per line, paste-style).
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from magpie.models import Category, CategoryPreset, ClassesPreset, LabelsPreset
from magpie.ui.widgets import CategoryTableWidget


# ---------------------------------------------------------------------------
# Category preset (name-only)
# ---------------------------------------------------------------------------


class CategoryPresetEditor(QDialog):
    """Full editor for a category preset: name + category table."""

    def __init__(self, preset: CategoryPreset | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑类别方案" if preset else "新建类别方案")
        self.resize(680, 480)
        self._original = preset
        self._result: CategoryPreset | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit(preset.name if preset else "")
        self.name_edit.setCursor(Qt.CursorShape.ArrowCursor)
        self.name_edit.setPlaceholderText("如：OK/NG · 5 级质量")
        form.addRow("方案名称", self.name_edit)
        layout.addLayout(form)

        hint = QLabel("可拖动整行调整顺序。每个类别必须填写快捷键；双击颜色列可选择类别颜色。")
        hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = CategoryTableWidget()
        if preset is not None and preset.categories:
            self.table.set_categories([Category(**c.to_dict()) for c in preset.categories])
        layout.addWidget(self.table, stretch=1)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #C62828; font-size: 11px;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.error_label.setText("方案名称不能为空")
            return
        error = self.table.validate()
        if error:
            self.error_label.setText(error)
            return
        categories = self.table.categories()
        preset_id = self._original.id if self._original is not None else CategoryPreset.new_id()
        self._result = CategoryPreset(id=preset_id, name=name, categories=categories)
        self.accept()

    def result_preset(self) -> CategoryPreset | None:
        return self._result


# ---------------------------------------------------------------------------
# Labels preset (name + path)
# ---------------------------------------------------------------------------


class LabelsPresetEditor(QDialog):
    def __init__(
        self,
        preset: LabelsPreset | None = None,
        preview_folder: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑标签目录方案" if preset else "新建标签目录方案")
        self.resize(500, 220)
        self.setMinimumSize(500, 220)
        self.setMaximumWidth(500)
        self._original = preset
        self._preview_folder = preview_folder or Path("/data/dataset_A")
        self._result: LabelsPreset | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit(preset.name if preset else "")
        self.name_edit.setPlaceholderText("如：本地 · 共享标注")
        form.addRow("方案名称", self.name_edit)

        self.path_edit = QLineEdit(preset.path if preset else "")
        self.path_edit.setPlaceholderText("labels  或  ../shared/labels")
        self.path_edit.textChanged.connect(self._refresh_preview)
        form.addRow("相对路径", self.path_edit)
        layout.addLayout(form)

        path_hint = QLabel(
            "相对源目录的路径。例如 <code>labels</code> 表示源目录下的 labels 子目录，"
            "<code>../shared/labels</code> 表示源目录同级的 shared/labels。"
        )
        path_hint.setTextFormat(Qt.TextFormat.RichText)
        path_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        path_hint.setWordWrap(True)
        layout.addWidget(path_hint)

        layout.addWidget(QLabel("<b>预览</b>"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setAcceptRichText(False)
        self.preview_text.setFixedHeight(58)
        self.preview_text.setStyleSheet(
            "QTextEdit { color: #6b7280; font-size: 11px;"
            " background: #f9fafb; border: 1px solid #e5e7eb;"
            " border-radius: 4px; padding: 4px; }"
        )
        layout.addWidget(self.preview_text)

        layout.addStretch()

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #C62828; font-size: 11px;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_preview()

    def _refresh_preview(self) -> None:
        raw = self.path_edit.text().strip()
        if not raw:
            self.preview_text.setPlainText("（留空表示不加载标签）")
            self.preview_text.setToolTip("")
            return
        # Path/-with-absolute or ~ still gets handled by the runtime resolver;
        # match its behavior here so the preview never lies.
        p = Path(raw).expanduser()
        joined = p if p.is_absolute() else (self._preview_folder / p)
        normalized = os.path.normpath(str(joined))
        self.preview_text.setPlainText(normalized)
        self.preview_text.setToolTip(normalized)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.error_label.setText("方案名称不能为空")
            return
        path = self.path_edit.text().strip()
        if not path:
            self.error_label.setText("路径不能为空")
            return
        preset_id = self._original.id if self._original else LabelsPreset.new_id()
        self._result = LabelsPreset(id=preset_id, name=name, path=path)
        self.accept()

    def result_preset(self) -> LabelsPreset | None:
        return self._result


# ---------------------------------------------------------------------------
# Classes preset (inline only)
# ---------------------------------------------------------------------------


class ClassesPresetEditor(QDialog):
    def __init__(
        self, preset: ClassesPreset | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑 classes 方案" if preset else "新建 classes 方案")
        self.resize(520, 460)
        self._original = preset
        self._result: ClassesPreset | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit(preset.name if preset else "")
        self.name_edit.setPlaceholderText("如：COCO 80 类 · 自建 5 类")
        form.addRow("方案名称", self.name_edit)
        outer.addLayout(form)

        outer.addWidget(QLabel("<b>类别名（一行一个，从 classes.txt 复制即可）</b>"))

        self.names_edit = QPlainTextEdit()
        self.names_edit.setPlaceholderText("person\ncar\ndog\n…")
        if preset and preset.names:
            self.names_edit.setPlainText("\n".join(preset.names))
        self.names_edit.textChanged.connect(self._refresh_count)
        outer.addWidget(self.names_edit, stretch=1)

        self.count_label = QLabel("0 项")
        self.count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        outer.addWidget(self.count_label)

        hint = QLabel(
            "提示：空行会被忽略；前后空格自动裁掉。"
        )
        hint.setStyleSheet("color: #9ca3af; font-size: 11px;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #C62828; font-size: 11px;")
        outer.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._refresh_count()

    def _refresh_count(self) -> None:
        text = self.names_edit.toPlainText()
        names = [line.strip() for line in text.splitlines() if line.strip()]
        self.count_label.setText(f"{len(names)} 项")

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.error_label.setText("方案名称不能为空")
            return
        names = [line.strip() for line in self.names_edit.toPlainText().splitlines() if line.strip()]
        if not names:
            self.error_label.setText("类别名不能为空")
            return
        preset_id = self._original.id if self._original else ClassesPreset.new_id()
        self._result = ClassesPreset(id=preset_id, name=name, names=names)
        self.accept()

    def result_preset(self) -> ClassesPreset | None:
        return self._result
