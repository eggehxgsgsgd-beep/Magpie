from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from magpie.config.classifications import ClassificationRecord
from magpie.models import Category


class SidePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)

        title = QLabel("类别速查")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title)

        self.content = QLabel("")
        self.content.setWordWrap(True)
        self.layout.addWidget(self.content)
        self.layout.addStretch()

    def refresh(self, categories: list[Category], output_dir: str = "", record: ClassificationRecord | None = None) -> None:
        if not categories:
            self.content.setText("尚未配置类别。<br>请进入 编辑 → 首选项 添加类别。")
            return

        lines: list[str] = []
        for category in categories:
            count = record.count_for_category(category.folder_name) if record else 0
            lines.append(
                f"<span style='color:{category.color};'>■</span> "
                f"<b>{category.key}</b>  {category.label}  "
                f"<span style='color:#777;'>({count})</span>"
            )
        self.content.setText("<br>".join(lines))
