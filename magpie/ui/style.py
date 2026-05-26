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
    font-size: 12px;
    color: #6b7280;
    padding: 2px 0;
}

QLabel#indexLabel {
    font-size: 12px;
    color: #1f2937;
    font-weight: 600;
    padding: 0 8px;
}

QLabel#pathLabel {
    font-size: 12px;
    color: #6b7280;
    padding: 0 6px;
}

QLabel#countsLabel {
    font-size: 12px;
    color: #1f2937;
    padding: 0 8px;
}

QProgressBar#statusProgressBar {
    border: 1px solid #d4d8df;
    border-radius: 3px;
    background: #ffffff;
    text-align: center;
    height: 14px;
}

QProgressBar#statusProgressBar::chunk {
    background: #3b82f6;
    border-radius: 2px;
}

QPushButton#undoButton {
    background: #ff5722;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton#undoButton:hover { background: #f4511e; }
QPushButton#undoButton:disabled { background: #d1d5db; color: #ffffff; }
"""


def apply_app_style(app: QApplication) -> None:
    app.setStyleSheet(APP_QSS)
