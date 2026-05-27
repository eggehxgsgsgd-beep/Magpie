from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import QApplication

UI_FONT_FAMILY = "Microsoft YaHei UI"


def configure_high_dpi() -> None:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def apply_app_font(app: QApplication) -> None:
    font = QFont(UI_FONT_FAMILY, 9)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)


def overlay_font(*, bold: bool = False, point_size: int = 12) -> QFont:
    font = QFont(UI_FONT_FAMILY, point_size)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    if bold:
        font.setBold(True)
    return font
