from .web_main_window import WebMainWindow

# Keep the historical name for callers/tests; the web window is now the canonical
# main window after the React/QWebEngine port.
MainWindow = WebMainWindow

__all__ = ["MainWindow", "WebMainWindow"]
