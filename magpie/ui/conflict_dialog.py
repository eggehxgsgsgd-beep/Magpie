from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout


@dataclass(slots=True)
class ConflictDecision:
    strategy: str
    remember: bool = False


class ConflictDialog(QDialog):
    def __init__(self, target_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("目标文件已存在")
        self.decision = ConflictDecision("cancel", False)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"目标文件已存在：\n{target_name}\n\n请选择本次操作策略。"))
        self.remember_check = QCheckBox("对本次会话记住此选择")
        layout.addWidget(self.remember_check)

        buttons = QDialogButtonBox()
        self.skip_button = buttons.addButton("跳过", QDialogButtonBox.ButtonRole.ActionRole)
        self.overwrite_button = buttons.addButton("覆盖", QDialogButtonBox.ButtonRole.ActionRole)
        self.rename_button = buttons.addButton("重命名", QDialogButtonBox.ButtonRole.ActionRole)
        self.cancel_button = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)

        self.skip_button.clicked.connect(lambda: self._choose("skip"))
        self.overwrite_button.clicked.connect(lambda: self._choose("overwrite"))
        self.rename_button.clicked.connect(lambda: self._choose("rename"))
        self.cancel_button.clicked.connect(lambda: self._choose("cancel"))
        layout.addWidget(buttons)

    def _choose(self, strategy: str) -> None:
        self.decision = ConflictDecision(strategy, self.remember_check.isChecked())
        if strategy == "cancel":
            self.reject()
        else:
            self.accept()
