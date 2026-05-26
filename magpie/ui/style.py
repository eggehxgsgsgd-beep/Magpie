from __future__ import annotations

from PyQt6.QtWidgets import QApplication


APP_QSS = """
QMainWindow,
QDialog {
    background: #ffffff;
    color: #20242a;
}

QMenuBar {
    background: #f7f8fa;
    border-bottom: 1px solid #dde2ea;
}

QToolBar {
    background: #f7f8fa;
    border: 0;
    border-bottom: 1px solid #dde2ea;
    padding: 4px;
}

QTableWidget {
    background: #ffffff;
    gridline-color: #e6ebf2;
}

QHeaderView::section {
    background: #f1f5f9;
    border: 0;
    border-right: 1px solid #d9e0ea;
    border-bottom: 1px solid #d9e0ea;
    padding: 5px 6px;
    font-weight: 600;
}

QStatusBar {
    background: #ffffff;
    border-top: 1px solid #dde2ea;
}

QLabel#imageNameLabel {
    font-size: 14px;
    color: #333333;
}

QLabel#indexLabel {
    font-size: 14px;
    color: #222222;
}

QLabel#pathLabel,
QLabel#messageLabel {
    font-size: 12px;
    color: #666666;
}

QPushButton#copyNameButton {
    background: #4caf50;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
}

QPushButton#copyNameButton:hover {
    background: #45a049;
}

QPushButton#copyNameButton:disabled {
    background: #bdbdbd;
}

QPushButton#jumpButton {
    background: #2196f3;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px;
}

QPushButton#jumpButton:hover {
    background: #1976d2;
}

QPushButton#jumpButton:disabled {
    background: #bdbdbd;
}
"""


def apply_app_style(app: QApplication) -> None:
    app.setStyleSheet(APP_QSS)
