from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)


@dataclass(slots=True)
class ConflictDecision:
    strategy: str
    apply_to: str = "once"  # "once" | "folder"


def _short_path(full_path: str, max_parts: int = 3) -> str:
    """Return the last *max_parts* path components, prefixed with ``…/``."""
    try:
        parts = PureWindowsPath(full_path).parts if "\\" in full_path else PurePosixPath(full_path).parts
    except Exception:  # noqa: BLE001
        parts = full_path.replace("\\", "/").split("/")
    if len(parts) <= max_parts:
        return full_path
    return "…/" + "/".join(parts[-max_parts:])


class ConflictDialog(QDialog):
    def __init__(self, target_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("目标文件已存在")
        self.setMaximumWidth(480)
        self.decision = ConflictDecision("cancel", "once")

        layout = QVBoxLayout(self)
        short = _short_path(target_name)
        msg = QLabel(f"目标文件已存在：\n{short}\n\n请选择本次操作策略。")
        msg.setWordWrap(True)
        if short != target_name:
            msg.setToolTip(target_name)
        layout.addWidget(msg)

        scope_label = QLabel("应用范围：")
        layout.addWidget(scope_label)

        self.scope_group = QButtonGroup(self)
        self.scope_once = QRadioButton("仅这一次")
        self.scope_once.setChecked(True)
        self.scope_folder = QRadioButton("本目录后续冲突都这样处理")
        self.scope_group.addButton(self.scope_once)
        self.scope_group.addButton(self.scope_folder)
        layout.addWidget(self.scope_once)
        layout.addWidget(self.scope_folder)

        buttons = QDialogButtonBox()
        self.skip_button = buttons.addButton("跳过(&S)", QDialogButtonBox.ButtonRole.ActionRole)
        self.overwrite_button = buttons.addButton("覆盖(&O)", QDialogButtonBox.ButtonRole.ActionRole)
        self.rename_button = buttons.addButton("重命名(&R)", QDialogButtonBox.ButtonRole.ActionRole)
        self.cancel_button = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        self.skip_button.clicked.connect(lambda: self._choose("skip"))
        self.overwrite_button.clicked.connect(lambda: self._choose("overwrite"))
        self.rename_button.clicked.connect(lambda: self._choose("rename"))
        self.cancel_button.clicked.connect(lambda: self._choose("cancel"))
        self.rename_button.setDefault(True)
        layout.addWidget(buttons)

    def _scope(self) -> str:
        if self.scope_folder.isChecked():
            return "folder"
        return "once"

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_S:
            self._choose("skip")
        elif key == Qt.Key.Key_O:
            self._choose("overwrite")
        elif key == Qt.Key.Key_R:
            self._choose("rename")
        else:
            super().keyPressEvent(event)

    def _choose(self, strategy: str) -> None:
        self.decision = ConflictDecision(strategy, self._scope())
        if strategy == "cancel":
            self.reject()
        else:
            self.accept()
