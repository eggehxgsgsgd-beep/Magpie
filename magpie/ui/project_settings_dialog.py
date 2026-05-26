"""Per-project (per source folder) path overrides dialog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QButtonGroup,
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
    resolve_classes_path,
    resolve_labels_dir,
    resolve_output_dir,
)


@dataclass
class ProjectSettingsResult:
    output_dir: str | None
    labels_dir: str | None
    classes_mode: str | None
    classes_path: str | None

    def as_override_kwargs(self) -> dict:
        """Map to kwargs passable to AppState.update_overrides."""
        kwargs: dict = {}
        # update_overrides keeps existing keys when a value is None; to
        # actually delete an override (revert to default) we pass the empty
        # string and the caller strips it after.
        kwargs["output_dir"] = self.output_dir or ""
        kwargs["labels_dir"] = self.labels_dir or ""
        kwargs["classes_mode"] = self.classes_mode or ""
        kwargs["classes_path"] = self.classes_path or ""
        return kwargs


class _PathOverrideRow(QWidget):
    """A reusable (default vs. custom) row used three times in this dialog."""

    def __init__(
        self,
        title: str,
        default_preview: str,
        initial_custom: str,
        active_custom: bool,
        chooser,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._chooser = chooser
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        title_label = QLabel(f"<b>{title}</b>")
        title_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title_label)

        self.default_radio = QRadioButton("默认")
        self.custom_radio = QRadioButton("自定义")
        self.group = QButtonGroup(self)
        self.group.addButton(self.default_radio)
        self.group.addButton(self.custom_radio)
        if active_custom:
            self.custom_radio.setChecked(True)
        else:
            self.default_radio.setChecked(True)

        default_row = QHBoxLayout()
        default_row.setContentsMargins(0, 0, 0, 0)
        default_row.setSpacing(6)
        default_row.addWidget(self.default_radio)
        self.default_preview_label = QLabel(default_preview)
        self.default_preview_label.setStyleSheet("color: #6b7280;")
        self.default_preview_label.setWordWrap(True)
        default_row.addWidget(self.default_preview_label, stretch=1)
        layout.addLayout(default_row)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(0, 0, 0, 0)
        custom_row.setSpacing(6)
        custom_row.addWidget(self.custom_radio)
        self.custom_edit = QLineEdit(initial_custom)
        self.custom_edit.setPlaceholderText("绝对路径或相对源目录的路径")
        self.choose_button = QPushButton("选择…")
        self.choose_button.clicked.connect(self._on_choose_clicked)
        custom_row.addWidget(self.custom_edit, stretch=1)
        custom_row.addWidget(self.choose_button)
        layout.addLayout(custom_row)

        self.default_radio.toggled.connect(self._sync_enabled)
        self._sync_enabled()
        # If user starts typing in the custom field while default is selected,
        # auto-promote to custom.
        self.custom_edit.textEdited.connect(lambda _t: self.custom_radio.setChecked(True))

    def _sync_enabled(self) -> None:
        custom = self.custom_radio.isChecked()
        self.custom_edit.setEnabled(custom)
        self.choose_button.setEnabled(custom)

    def _on_choose_clicked(self) -> None:
        path = self._chooser(self.custom_edit.text())
        if path:
            self.custom_edit.setText(path)
            self.custom_radio.setChecked(True)

    def set_default_preview(self, text: str) -> None:
        self.default_preview_label.setText(text)

    def is_custom(self) -> bool:
        return self.custom_radio.isChecked()

    def custom_value(self) -> str:
        return self.custom_edit.text().strip()


class ProjectSettingsDialog(QDialog):
    """`分类 → 本目录设置…` — per-folder path overrides."""

    def __init__(
        self,
        folder: Path,
        prefs: Preferences,
        current_overrides: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("本目录设置")
        self.resize(640, 460)
        self._folder = folder
        self._prefs = prefs
        self._initial_overrides = dict(current_overrides or {})

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # Header: current source folder + copy button.
        header = QHBoxLayout()
        header.setSpacing(6)
        header.addWidget(QLabel("<b>当前源目录</b>"))
        path_label = QLabel(f"<code>{folder}</code>")
        path_label.setTextFormat(Qt.TextFormat.RichText)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header.addWidget(path_label, stretch=1)
        copy_button = QPushButton("复制")
        copy_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        copy_button.clicked.connect(lambda: self._copy_path(str(folder)))
        header.addWidget(copy_button)
        outer.addLayout(header)

        # Resolve current defaults (ignoring per-folder overrides) so the
        # "default" radios can show the actual computed default.
        default_output = self._safe_resolve_output(prefs, folder)
        default_labels = self._safe_resolve_labels(prefs, folder)
        default_classes = self._safe_resolve_classes(prefs, default_labels)

        # ----- Output dir row -----
        self.output_row = _PathOverrideRow(
            title="输出目录",
            default_preview=f"默认 → {default_output}",
            initial_custom=str(self._initial_overrides.get("output_dir") or ""),
            active_custom=bool(self._initial_overrides.get("output_dir")),
            chooser=self._choose_output_dir,
            parent=self,
        )
        outer.addWidget(self.output_row)

        # ----- Labels dir row -----
        self.labels_row = _PathOverrideRow(
            title="标签目录",
            default_preview=(
                f"默认 → {default_labels}" if default_labels else "默认 → （未配置）"
            ),
            initial_custom=str(self._initial_overrides.get("labels_dir") or ""),
            active_custom=bool(self._initial_overrides.get("labels_dir")),
            chooser=self._choose_labels_dir,
            parent=self,
        )
        outer.addWidget(self.labels_row)

        # ----- classes.txt row (slightly different: auto vs custom + file picker) -----
        self.classes_row = _ClassesRow(
            default_preview=(
                f"自动 → {default_classes}" if default_classes
                else "自动 → （未配置标签目录）"
            ),
            initial_mode=self._initial_overrides.get("classes_mode")
            or (prefs.classes_mode or "auto"),
            initial_custom=str(
                self._initial_overrides.get("classes_path") or prefs.classes_path or ""
            ),
            override_present=bool(self._initial_overrides.get("classes_mode")
                                  or self._initial_overrides.get("classes_path")),
            parent=self,
        )
        outer.addWidget(self.classes_row)

        outer.addStretch()

        # Footer: reset + cancel/ok
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

        self._result: ProjectSettingsResult | None = None
        self._reset_clicked = False

    # ----- helpers -----

    def _safe_resolve_output(self, prefs: Preferences, folder: Path) -> str:
        try:
            return str(resolve_output_dir(prefs, {}, folder))
        except ProjectPathError as exc:
            return f"（模板错误：{exc}）"

    def _safe_resolve_labels(self, prefs: Preferences, folder: Path) -> Path | None:
        try:
            return resolve_labels_dir(prefs, {}, folder)
        except Exception:  # noqa: BLE001 — never let resolution kill the dialog
            return None

    def _safe_resolve_classes(self, prefs: Preferences, labels: Path | None) -> str:
        try:
            p = resolve_classes_path(prefs, {}, labels)
        except Exception:  # noqa: BLE001
            return ""
        return str(p) if p else ""

    def _copy_path(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    def _choose_output_dir(self, current: str) -> str:
        start = current or str(self._folder.parent)
        chosen = QFileDialog.getExistingDirectory(self, "选择输出目录", start)
        return chosen or ""

    def _choose_labels_dir(self, current: str) -> str:
        start = current or str(self._folder)
        chosen = QFileDialog.getExistingDirectory(self, "选择标签目录", start)
        return chosen or ""

    def _on_reset(self) -> None:
        if QMessageBox.question(
            self,
            "确认重置",
            "将清除本目录的所有路径覆盖，是否继续？",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._reset_clicked = True
        self._result = ProjectSettingsResult(
            output_dir=None, labels_dir=None, classes_mode=None, classes_path=None,
        )
        self.accept()

    # ----- accept -----

    def accept(self) -> None:
        if self._reset_clicked:
            super().accept()
            return
        self._result = ProjectSettingsResult(
            output_dir=(self.output_row.custom_value() if self.output_row.is_custom() else None),
            labels_dir=(self.labels_row.custom_value() if self.labels_row.is_custom() else None),
            classes_mode=self.classes_row.mode_value(),
            classes_path=self.classes_row.custom_path_value(),
        )
        super().accept()

    def result_overrides(self) -> ProjectSettingsResult | None:
        return self._result


class _ClassesRow(QWidget):
    """classes.txt row: auto / custom radio + file picker."""

    def __init__(
        self,
        default_preview: str,
        initial_mode: str,
        initial_custom: str,
        override_present: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        layout.addWidget(QLabel("<b>classes.txt</b>"))

        self.auto_radio = QRadioButton("自动 — 取自标签目录")
        self.custom_radio = QRadioButton("自定义")
        self.group = QButtonGroup(self)
        self.group.addButton(self.auto_radio)
        self.group.addButton(self.custom_radio)
        if override_present and initial_mode == "custom":
            self.custom_radio.setChecked(True)
        else:
            self.auto_radio.setChecked(True)

        auto_row = QHBoxLayout()
        auto_row.setSpacing(6)
        auto_row.addWidget(self.auto_radio)
        self.preview_label = QLabel(default_preview)
        self.preview_label.setStyleSheet("color: #6b7280;")
        self.preview_label.setWordWrap(True)
        auto_row.addWidget(self.preview_label, stretch=1)
        layout.addLayout(auto_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(6)
        custom_row.addWidget(self.custom_radio)
        self.custom_edit = QLineEdit(initial_custom)
        self.custom_edit.setPlaceholderText("/path/to/classes.txt")
        self.choose_button = QPushButton("选择…")
        self.choose_button.clicked.connect(self._on_choose_clicked)
        custom_row.addWidget(self.custom_edit, stretch=1)
        custom_row.addWidget(self.choose_button)
        layout.addLayout(custom_row)

        self._override_present = override_present
        self.auto_radio.toggled.connect(self._sync_enabled)
        self.custom_edit.textEdited.connect(lambda _t: self.custom_radio.setChecked(True))
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        custom = self.custom_radio.isChecked()
        self.custom_edit.setEnabled(custom)
        self.choose_button.setEnabled(custom)

    def _on_choose_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 classes.txt", self.custom_edit.text(),
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            self.custom_edit.setText(path)
            self.custom_radio.setChecked(True)

    def mode_value(self) -> str | None:
        """Return the override value for classes_mode.

        Returns ``None`` when the row reflects the *default* (auto + no
        prior override) so the caller can avoid recording a redundant key.
        """
        if self.custom_radio.isChecked():
            return "custom"
        # Auto: only treat as an explicit override if user had previously set one.
        return "auto" if self._override_present else None

    def custom_path_value(self) -> str | None:
        if not self.custom_radio.isChecked():
            return None
        return self.custom_edit.text().strip() or None
