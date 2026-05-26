from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"


TARGET_NAMES = {
    "windows-x64": "Magpie-1.0.0-windows-x64",
    "macos-x64": "Magpie-1.0.0-macos-x64",
    "macos-arm64": "Magpie-1.0.0-macos-arm64",
    "linux-x86_64": "Magpie-1.0.0-linux-x86_64",
}

# Heavy PyQt6 sub-packages we never import. Excluding them keeps the
# onefile build small AND prevents PyInstaller from following Qt plugin
# dependency chains into unrelated native libraries (libpq, krb5, icu,
# ffmpeg, ...) that pollute the bundle and break Qt's runtime.
EXCLUDED_PYQT6_MODULES = [
    "PyQt6.Qt3DAnimation",
    "PyQt6.Qt3DCore",
    "PyQt6.Qt3DExtras",
    "PyQt6.Qt3DInput",
    "PyQt6.Qt3DLogic",
    "PyQt6.Qt3DRender",
    "PyQt6.QtBluetooth",
    "PyQt6.QtCharts",
    "PyQt6.QtDataVisualization",
    "PyQt6.QtDesigner",
    "PyQt6.QtHelp",
    "PyQt6.QtLocation",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtNfc",
    "PyQt6.QtRemoteObjects",
    "PyQt6.QtSensors",
    "PyQt6.QtSerialBus",
    "PyQt6.QtSerialPort",
    "PyQt6.QtSpatialAudio",
    # QtSql drags libpq/krb5/openssl into the bundle from the build
    # machine's PATH; Magpie never uses a database backend so we drop
    # it explicitly to keep the dependency surface clean.
    "PyQt6.QtSql",
    "PyQt6.QtTextToSpeech",
    "PyQt6.QtWebChannel",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebSockets",
    "PyQt6.QtWebView",
]

# Directory name fragments that almost always carry an alternative
# Python/Qt stack. If any of them appears on PATH while PyInstaller is
# analyzing dependencies, those DLLs get sucked into the bundle and end
# up shadowing the ones shipped by the PyQt6 wheel at runtime. We strip
# them from the child process's PATH for the build step only.
PATH_BLOCKLIST_FRAGMENTS = (
    "anaconda",
    "miniconda",
    "miniforge",
    "mambaforge",
    "conda",
    "msys",
    "mingw",
)


def _sanitized_env() -> dict[str, str]:
    env = os.environ.copy()
    path_parts = env.get("PATH", "").split(os.pathsep)
    kept: list[str] = []
    dropped: list[str] = []
    for entry in path_parts:
        if not entry:
            continue
        lowered = entry.lower()
        if any(fragment in lowered for fragment in PATH_BLOCKLIST_FRAGMENTS):
            dropped.append(entry)
        else:
            kept.append(entry)
    env["PATH"] = os.pathsep.join(kept)
    if dropped:
        print(f"[build] removed {len(dropped)} PATH entries to keep the bundle clean:")
        for entry in dropped:
            print(f"  - {entry}")
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Magpie with PyInstaller")
    parser.add_argument("--target", required=True, choices=sorted(TARGET_NAMES))
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build with a console window so smoke tests can read stdout/stderr.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    name = TARGET_NAMES[args.target]
    entrypoint = ROOT / "magpie" / "ImageClassifierQt.py"
    icon_path = ROOT / "packaging" / "app.ico"
    separator = ";" if sys.platform.startswith("win") else ":"

    command: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console" if args.console else "--windowed",
        "--name",
        name,
        "--distpath",
        str(DIST_DIR),
        "--collect-all",
        "PyQt6",
        "--collect-all",
        "PIL",
        "--add-data",
        f"{ROOT / 'magpie' / 'resources'}{separator}magpie/resources",
    ]
    if icon_path.exists():
        command.extend(["--icon", str(icon_path)])
    for module in EXCLUDED_PYQT6_MODULES:
        command.extend(["--exclude-module", module])
    command.append(str(entrypoint))

    subprocess.run(command, cwd=ROOT, env=_sanitized_env(), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
