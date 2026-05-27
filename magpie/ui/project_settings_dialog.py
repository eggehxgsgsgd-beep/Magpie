"""`分类 → 本目录设置…` — per-folder overrides for output / labels / classes / sort."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from magpie.config import (
    Preferences,
    ProjectPathError,
    resolve_labels_dir,
    resolve_output_dir,
)


@dataclass
class ProjectSettingsResult:
    """Result of editing per-folder overrides for the currently-opened folder."""
    output_dir: str | None
    labels_selection: str | None    # "preset:<id>" | "path:<v>" | "none" | None (=follow default)
    classes_selection: str | None   # "preset:<id>" | "labels" | "none" | None
    conflict_strategy: str | None   # "ask" | "skip" | "overwrite" | "rename" | None (=follow default)
    sort_preset_id: str | None
    sort_descending: bool | None


class ProjectSettingsDialog(QDialog):
    """Per-folder path/sort overrides selector dialog."""

    def __init__(
        self,
        folder: Path,
        prefs: Preferences,
        current_overrides: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("本目录设置")
        self.resize(640, 520)
        self._folder = folder
        self._prefs = prefs
        self._initial_overrides = dict(current_overrides or {})
        self._reset_clicked = False
        self._result: ProjectSettingsResult | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)
        header.addWidget(QLabel("<b>当前源目录</b>"))
        path_label = QLabel(f"<code>{folder}</code>")
        path_label.setTextFormat(Qt.TextFormat.RichText)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header.addWidget(path_label, stretch=1)
        copy_button = QPushButton("复制")
        copy_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        copy_button.clicked.connect(lambda: self._copy(str(folder)))
        header.addWidget(copy_button)
        outer.addLayout(header)

        outer.addWidget(self._hr())

        # ----- 输出目录 (radio: default / custom) -----
        outer.addWidget(QLabel("<b>输出目录</b>"))
        default_output = self._safe_resolve_output(prefs, folder)
        out_box = QVBoxLayout()
        out_box.setSpacing(4)
        self.output_default_radio = QRadioButton(f"默认 → {default_output}")
        self.output_custom_radio = QRadioButton("自定义路径")
        out_group = QButtonGroup(self)
        out_group.addButton(self.output_default_radio)
        out_group.addButton(self.output_custom_radio)
        if self._initial_overrides.get("output_dir"):
            self.output_custom_radio.setChecked(True)
        else:
            self.output_default_radio.setChecked(True)
        out_box.addWidget(self.output_default_radio)
        out_custom_row = QHBoxLayout()
        out_custom_row.setContentsMargins(20, 0, 0, 0)
        out_custom_row.addWidget(self.output_custom_radio)
        self.output_path_edit = QLineEdit(str(self._initial_overrides.get("output_dir") or ""))
        self.output_path_edit.setPlaceholderText("绝对或相对源目录的路径")
        self.output_browse_btn = QPushButton("选择…")
        self.output_browse_btn.clicked.connect(self._on_output_browse)
        self.output_path_edit.textEdited.connect(lambda _t: self.output_custom_radio.setChecked(True))
        out_custom_row.addWidget(self.output_path_edit, stretch=1)
        out_custom_row.addWidget(self.output_browse_btn)
        out_box.addLayout(out_custom_row)
        outer.addLayout(out_box)
        self.output_default_radio.toggled.connect(self._sync_output_enabled)
        self._sync_output_enabled()

        outer.addWidget(self._hr())

        # ----- 标签目录 (combo of presets + one-shot path + none) -----
        outer.addWidget(QLabel("<b>标签目录</b>"))
        labels_row = QHBoxLayout()
        labels_row.addWidget(QLabel("选择"))
        self.labels_combo = QComboBox()
        labels_row.addWidget(self.labels_combo, stretch=1)
        outer.addLayout(labels_row)
        self.labels_path_row = QWidget()
        labels_path_layout = QHBoxLayout(self.labels_path_row)
        labels_path_layout.setContentsMargins(20, 0, 0, 0)
        labels_path_layout.addWidget(QLabel("路径"))
        self.labels_path_edit = QLineEdit()
        self.labels_path_edit.setPlaceholderText("labels  或  ../shared  或  /abs/path")
        labels_browse = QPushButton("选择…")
        labels_browse.clicked.connect(self._on_labels_browse)
        labels_path_layout.addWidget(self.labels_path_edit, stretch=1)
        labels_path_layout.addWidget(labels_browse)
        outer.addWidget(self.labels_path_row)
        self.labels_combo.currentIndexChanged.connect(self._on_labels_combo_changed)
        self._populate_labels_combo()

        outer.addWidget(self._hr())

        # ----- classes.txt (combo of presets / none, no one-shot path) -----
        outer.addWidget(QLabel("<b>classes.txt</b>"))
        classes_row = QHBoxLayout()
        classes_row.addWidget(QLabel("选择"))
        self.classes_combo = QComboBox()
        classes_row.addWidget(self.classes_combo, stretch=1)
        outer.addLayout(classes_row)
        self._populate_classes_combo()

        outer.addWidget(self._hr())

        # ----- 冲突策略 -----
        outer.addWidget(QLabel("<b>冲突策略</b>"))
        conflict_row = QHBoxLayout()
        conflict_row.addWidget(QLabel("策略"))
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem(f"跟随默认（{self._describe_conflict(prefs.conflict_strategy)}）", "")
        self.conflict_combo.addItem("询问", "ask")
        self.conflict_combo.addItem("跳过", "skip")
        self.conflict_combo.addItem("覆盖", "overwrite")
        self.conflict_combo.addItem("重命名", "rename")
        conflict_row.addWidget(self.conflict_combo, stretch=1)
        outer.addLayout(conflict_row)
        current_conflict = self._initial_overrides.get("conflict_strategy") or ""
        cidx = self.conflict_combo.findData(current_conflict)
        if cidx < 0:
            cidx = 0
        self.conflict_combo.setCurrentIndex(cidx)

        outer.addWidget(self._hr())

        # ----- 排序 (combo of presets + direction radio) -----
        outer.addWidget(QLabel("<b>排序</b>"))
        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("方案"))
        self.sort_combo = QComboBox()
        for preset in prefs.sort_presets:
            self.sort_combo.addItem(preset.name, preset.id)
        active_id = (
            self._initial_overrides.get("sort_preset_id")
            or prefs.active_sort_preset_id
        )
        idx = self.sort_combo.findData(active_id)
        if idx >= 0:
            self.sort_combo.setCurrentIndex(idx)
        sort_row.addWidget(self.sort_combo, stretch=1)
        outer.addLayout(sort_row)

        direction_row = QHBoxLayout()
        direction_row.addWidget(QLabel("方向"))
        self.sort_asc_radio = QRadioButton("升序")
        self.sort_desc_radio = QRadioButton("降序")
        descending = self._initial_overrides.get("sort_descending")
        if descending is None:
            descending = prefs.sort_descending
        if descending:
            self.sort_desc_radio.setChecked(True)
        else:
            self.sort_asc_radio.setChecked(True)
        dir_group = QButtonGroup(self)
        dir_group.addButton(self.sort_asc_radio)
        dir_group.addButton(self.sort_desc_radio)
        direction_row.addWidget(self.sort_asc_radio)
        direction_row.addWidget(self.sort_desc_radio)
        direction_row.addStretch()
        outer.addLayout(direction_row)

        outer.addStretch()
        outer.addWidget(self._hr())

        # Footer
        footer = QHBoxLayout()
        reset_button = QPushButton("重置为默认")
        reset_button.clicked.connect(self._on_reset)
        footer.addWidget(reset_button)
        footer.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        outer.addLayout(footer)

    # ---- helpers ----

    def _hr(self) -> QLabel:
        label = QLabel()
        label.setFixedHeight(1)
        label.setStyleSheet("background: #e5e7eb;")
        return label

    def _copy(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    def _safe_resolve_output(self, prefs: Preferences, folder: Path) -> str:
        try:
            return str(resolve_output_dir(prefs, {}, folder))
        except ProjectPathError as exc:
            return f"（模板错误：{exc}）"

    def _safe_resolve_labels_preview(self, raw: str) -> str:
        p = Path(raw).expanduser()
        joined = p if p.is_absolute() else (self._folder / p)
        return os.path.normpath(str(joined))

    def _sync_output_enabled(self) -> None:
        custom = self.output_custom_radio.isChecked()
        self.output_path_edit.setEnabled(custom)
        self.output_browse_btn.setEnabled(custom)

    def _on_output_browse(self) -> None:
        start = self.output_path_edit.text() or str(self._folder.parent)
        chosen = QFileDialog.getExistingDirectory(self, "选择输出目录", start)
        if chosen:
            self.output_path_edit.setText(chosen)
            self.output_custom_radio.setChecked(True)

    # ---- labels combo ----

    def _populate_labels_combo(self) -> None:
        default_sel = self._prefs.default_labels_selection or "none"
        default_label = self._describe_labels_selection(default_sel)
        self.labels_combo.addItem(f"跟随默认（{default_label}）", "")
        for preset in self._prefs.labels_presets:
            self.labels_combo.addItem(preset.name, f"preset:{preset.id}")
        self.labels_combo.insertSeparator(self.labels_combo.count())
        self.labels_combo.addItem("一次性自定义路径…", "path:")
        self.labels_combo.addItem("不加载", "none")

        # Restore selection from overrides.
        current = self._initial_overrides.get("labels_selection") or ""
        if current.startswith("path:"):
            self.labels_path_edit.setText(current[len("path:"):])
            idx = self.labels_combo.findData("path:")
        elif current.startswith("preset:") or current == "none":
            idx = self.labels_combo.findData(current)
        else:
            idx = 0  # follow default
        if idx < 0:
            idx = 0
        self.labels_combo.setCurrentIndex(idx)
        self._on_labels_combo_changed()

    def _on_labels_combo_changed(self) -> None:
        value = self.labels_combo.currentData() or ""
        self.labels_path_row.setVisible(value == "path:")

    def _on_labels_browse(self) -> None:
        start = self.labels_path_edit.text() or str(self._folder)
        chosen = QFileDialog.getExistingDirectory(self, "选择标签目录", start)
        if chosen:
            self.labels_path_edit.setText(chosen)

    def _describe_labels_selection(self, selection: str) -> str:
        selection = (selection or "").strip()
        if not selection or selection == "none":
            return "不加载"
        if selection.startswith("preset:"):
            preset_id = selection.split(":", 1)[1]
            preset = next((p for p in self._prefs.labels_presets if p.id == preset_id), None)
            if preset is None:
                return "未配置"
            try:
                resolved = resolve_labels_dir(self._prefs, {}, self._folder)
                return f"{preset.name} → {resolved}"
            except Exception:  # noqa: BLE001
                return preset.name
        if selection.startswith("path:"):
            return selection[len("path:"):]
        return selection

    # ---- classes combo ----

    def _populate_classes_combo(self) -> None:
        default_sel = self._prefs.default_classes_selection or "none"
        default_label = self._describe_classes_selection(default_sel)
        self.classes_combo.addItem(f"跟随默认（{default_label}）", "")
        for preset in self._prefs.classes_presets:
            self.classes_combo.addItem(f"{preset.name}（{len(preset.names)} 项）", f"preset:{preset.id}")
        self.classes_combo.insertSeparator(self.classes_combo.count())
        self.classes_combo.addItem("从标签目录加载 classes.txt", "labels")
        self.classes_combo.addItem("不加载", "none")

        current = self._initial_overrides.get("classes_selection") or ""
        idx = self.classes_combo.findData(current)
        if idx < 0:
            idx = 0
        self.classes_combo.setCurrentIndex(idx)

    def _describe_classes_selection(self, selection: str) -> str:
        selection = (selection or "").strip()
        if not selection or selection == "none":
            return "不加载"
        if selection == "labels":
            return "从标签目录加载"
        if selection.startswith("preset:"):
            preset_id = selection.split(":", 1)[1]
            preset = next((p for p in self._prefs.classes_presets if p.id == preset_id), None)
            if preset is None:
                return "未配置"
            return f"{preset.name}（{len(preset.names)} 项）"
        return selection

    @staticmethod
    def _describe_conflict(strategy: str) -> str:
        return {"ask": "询问", "skip": "跳过", "overwrite": "覆盖", "rename": "重命名"}.get(strategy, strategy)

    # ---- reset ----

    def _on_reset(self) -> None:
        if QMessageBox.question(
            self,
            "确认重置",
            "将清除本目录的所有覆盖，全部回到全局默认，确定吗？",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._reset_clicked = True
        self._result = ProjectSettingsResult(
            output_dir=None,
            labels_selection=None,
            classes_selection=None,
            conflict_strategy=None,
            sort_preset_id=None,
            sort_descending=None,
        )
        self.accept()

    # ---- accept ----

    def accept(self) -> None:
        if self._reset_clicked:
            super().accept()
            return

        # Output
        if self.output_custom_radio.isChecked():
            output_dir = self.output_path_edit.text().strip() or None
        else:
            output_dir = None

        # Labels
        labels_value = self.labels_combo.currentData() or ""
        if not labels_value:
            labels_selection = None
        elif labels_value == "path:":
            raw = self.labels_path_edit.text().strip()
            labels_selection = f"path:{raw}" if raw else None
        else:
            labels_selection = labels_value

        # Classes
        classes_value = self.classes_combo.currentData() or ""
        classes_selection = classes_value or None

        # Conflict strategy
        conflict_value = self.conflict_combo.currentData() or ""
        conflict_strategy = conflict_value or None

        # Sort
        sort_preset_id = self.sort_combo.currentData()
        if sort_preset_id == self._prefs.active_sort_preset_id:
            # Not different from global; don't store an override.
            sort_preset_id_to_store = None
        else:
            sort_preset_id_to_store = sort_preset_id

        desc = self.sort_desc_radio.isChecked()
        if desc == self._prefs.sort_descending:
            sort_descending_to_store = None
        else:
            sort_descending_to_store = desc

        self._result = ProjectSettingsResult(
            output_dir=output_dir,
            labels_selection=labels_selection,
            classes_selection=classes_selection,
            conflict_strategy=conflict_strategy,
            sort_preset_id=sort_preset_id_to_store,
            sort_descending=sort_descending_to_store,
        )
        super().accept()

    def result_overrides(self) -> ProjectSettingsResult | None:
        return self._result
