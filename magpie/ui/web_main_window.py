from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QByteArray, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMainWindow

from magpie.config import AppState, Preferences

from .web_bridge import MagpieBridge


def web_assets_root() -> Path:
    """Resolve the bundled `magpie/resources/web/` directory.

    Works both in dev mode (importing the package straight from source) and
    inside a PyInstaller --onefile bundle, where the package gets extracted to
    ``sys._MEIPASS``.
    """
    candidates: list[Path] = []
    here = Path(__file__).resolve().parent.parent
    candidates.append(here / "resources" / "web")

    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.append(Path(base) / "magpie" / "resources" / "web")
        candidates.append(Path(base) / "resources" / "web")

    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate magpie/resources/web; checked: " + ", ".join(str(c) for c in candidates))


class WebMainWindow(QMainWindow):
    """Hosts a QWebEngineView that renders the React UI shipped with Magpie."""

    def __init__(self, preferences: Preferences | None = None, state: AppState | None = None) -> None:
        super().__init__()
        self.preferences = preferences or Preferences.load()
        self.state = state or AppState.load()

        self.setWindowTitle("Magpie")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self._restore_window_state()

        icon_path = Path(__file__).resolve().parent.parent / "resources" / "icons" / "magpie_icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        # Off-the-record profile keeps cookies/cache from polluting the user
        # AppData with browser noise; the UI does not need persistent storage.
        profile = QWebEngineProfile("magpie-profile", self.view)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, True)

        self.bridge = MagpieBridge(window=self, preferences=self.preferences, state=self.state, parent=self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("magpieApi", self.bridge)
        self.view.page().setWebChannel(self.channel)

        assets = web_assets_root()
        url = QUrl.fromLocalFile(str(assets / "index.html"))
        self.view.load(url)

    def _restore_window_state(self) -> None:
        if self.state.geometry_hex:
            try:
                self.restoreGeometry(QByteArray.fromHex(self.state.geometry_hex.encode("ascii")))
            except Exception:
                pass
        if self.state.window_state_hex:
            try:
                self.restoreState(QByteArray.fromHex(self.state.window_state_hex.encode("ascii")))
            except Exception:
                pass

    def open_image_folder(self, folder: str) -> None:
        # Bootstrap path used by CLI argument: tell the bridge to load it after
        # the page is ready. The page bootstrap calls getInitialState() which
        # already includes the last-used folder, so we just stash it there.
        self.bridge.state.image_folder = folder
        self.bridge.state.save()

    def closeEvent(self, event) -> None:
        self.state.geometry_hex = bytes(self.saveGeometry().toHex()).decode("ascii")
        self.state.window_state_hex = bytes(self.saveState().toHex()).decode("ascii")
        self.state.save()
        self.preferences.save()
        super().closeEvent(event)


__all__ = ["WebMainWindow"]
