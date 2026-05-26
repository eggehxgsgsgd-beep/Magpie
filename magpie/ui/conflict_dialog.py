from __future__ import annotations

from dataclasses import dataclass

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
    apply_to: str = "once"  # "once" | "session" | "batch"


class ConflictDialog(QDialog):
    def __init__(self, target_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("目标文件已存在")
        self.decision = ConflictDecision("cancel", "once")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"目标文件已存在：\n{target_name}\n\n请选择本次操作策略。"))

        scope_label = QLabel("应用范围：")
        layout.addWidget(scope_label)

        self.scope_group = QButtonGroup(self)
        self.scope_once = QRadioButton("仅这一次")
        self.scope_once.setChecked(True)
        self.scope_batch = QRadioButton("对本批剩余冲突")
        self.scope_session = QRadioButton("对本次会话所有冲突")
        self.scope_group.addButton(self.scope_once)
        self.scope_group.addButton(self.scope_batch)
        self.scope_group.addButton(self.scope_session)
        layout.addWidget(self.scope_once)
        layout.addWidget(self.scope_batch)
        layout.addWidget(self.scope_session)

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

    def _scope(self) -> str:
        if self.scope_batch.isChecked():
            return "batch"
        if self.scope_session.isChecked():
            return "session"
        return "once"

    def _choose(self, strategy: str) -> None:
        self.decision = ConflictDecision(strategy, self._scope())
        if strategy == "cancel":
            self.reject()
        else:
            self.accept()
