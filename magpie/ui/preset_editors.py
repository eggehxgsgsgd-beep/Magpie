"""Dialog editors for category / labels / classes presets.

Sort presets are edited via ``CustomSortPresetEditor`` already living in
``preferences_dialog.py``; this module covers the three new preset kinds.

Categories are intentionally edited *inline* in the 类别 tab (the category
table reacts to selection in the preset list). The ``CategoryPresetEditor``
here only handles **naming**: new preset + rename.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from magpie.models import CategoryPreset, ClassesPreset, LabelsPreset


# ---------------------------------------------------------------------------
# Category preset (name-only)
# ---------------------------------------------------------------------------


class CategoryPresetEditor(QDialog):
    """Name-only editor for a category preset.

    Category contents are edited directly in the preferences 类别 tab when the
    preset is selected. This dialog handles "new preset" (provide a name) and
    "rename".
    """

    def __init__(self, preset: CategoryPreset | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑类别方案" if preset else "新建类别方案")
        self.resize(380, 140)
        self._original = preset
        self._result: CategoryPreset | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit(preset.name if preset else "")
        self.name_edit.setPlaceholderText("如：OK/NG · 5 级质量")
        form.addRow("方案名称", self.name_edit)
        layout.addLayout(form)

        hint = QLabel("方案名称仅用于显示；类别内容请在「类别」标签页中编辑。")
        hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #C62828; font-size: 11px;")
        layout.insertWidget(layout.count() - 1, self.error_label)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.error_label.setText("方案名称不能为空")
            return
        if self._original is None:
            self._result = CategoryPreset(id=CategoryPreset.new_id(), name=name, categories=[])
        else:
            self._result = CategoryPreset(
                id=self._original.id, name=name, categories=list(self._original.categories)
            )
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

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self.path_edit = QLineEdit(preset.path if preset else "")
        self.path_edit.setPlaceholderText("labels  或  ../shared/labels  或  /abs/path")
        self.path_edit.textChanged.connect(self._refresh_preview)
        path_row.addWidget(self.path_edit, stretch=1)
        browse = QPushButton("选择…")
        browse.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        browse.clicked.connect(self._on_browse)
        path_row.addWidget(browse)
        form.addRow("路径", path_row)
        layout.addLayout(form)

        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.preview_label)

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
            self.preview_label.setText("（留空表示不加载标签）")
            return
        p = Path(raw).expanduser()
        joined = p if p.is_absolute() else (self._preview_folder / p)
        normalized = os.path.normpath(str(joined))
        self.preview_label.setText(
            f"预览：{self._preview_folder} → <code>{normalized}</code>"
        )

    def _on_browse(self) -> None:
        start = self.path_edit.text() or str(self._preview_folder)
        chosen = QFileDialog.getExistingDirectory(self, "选择标签目录", start)
        if chosen:
            self.path_edit.setText(chosen)

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
