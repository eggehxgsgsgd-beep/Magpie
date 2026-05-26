from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from magpie.config.classifications import ClassificationRecord
from magpie.models import Category


class SidePanel(QWidget):
    undoRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setStyleSheet(
            """
            QWidget#sidePanel {
                background: #ffffff;
            }
            QLabel {
                color: #27313f;
            }
            QPushButton#undoButton {
                background: #ff5722;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: 600;
            }
            QPushButton#undoButton:hover {
                background: #f4511e;
            }
            QPushButton#undoButton:disabled {
                background: #bdbdbd;
                color: #f5f5f5;
            }
            """
        )
        self.setFixedWidth(250)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(15)

        title = QLabel("分类标签")
        title.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            color: #333;
            padding: 5px;
            border-bottom: 2px solid #2196f3;
            """
        )
        self.layout.addWidget(title)

        self.content = QLabel("")
        self.content.setWordWrap(True)
        self.content.setTextFormat(Qt.TextFormat.RichText)
        self.content.setStyleSheet(
            """
            font-size: 14px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            line-height: 160%;
            """
        )
        self.layout.addWidget(self.content)
        self.layout.addStretch()

        self.undo_button = QPushButton("撤销 (Ctrl+Z)")
        self.undo_button.setObjectName("undoButton")
        self.undo_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.undo_button.clicked.connect(self.undoRequested.emit)
        self.undo_button.setEnabled(False)
        self.layout.addWidget(self.undo_button)

        shortcuts = QLabel(
            "快捷键说明：\n"
            "← / →：上一张 / 下一张\n"
            "空格：自动播放 / 暂停\n"
            "Ctrl+Z / Ctrl+Y：撤销 / 重做\n"
            "滚轮：缩放图片\n"
            "右键：适应窗口"
        )
        shortcuts.setStyleSheet(
            """
            font-size: 12px;
            color: #666;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            """
        )
        self.layout.addWidget(shortcuts)

    def set_undo_enabled(self, enabled: bool) -> None:
        self.undo_button.setEnabled(enabled)

    def refresh(self, categories: list[Category], output_dir: str = "", record: ClassificationRecord | None = None) -> None:
        if not categories:
            self.content.setText("尚未配置类别。<br>请进入 编辑 → 首选项 添加类别。")
            return

        lines: list[str] = []
        for category in categories:
            count = record.count_for_category(category.folder_name) if record else 0
            lines.append(
                f"<b>{category.key}</b>: {category.label} "
                f"<span style='color:#777;'>({count})</span>"
            )
        self.content.setText("<br>".join(lines))
