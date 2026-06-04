from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
ICON_PATH = ROOT / "packaging" / "app.ico"
ICON_SVG = ROOT / "magpie" / "resources" / "icons" / "magpie_icon.svg"


# Supported PyInstaller targets. The artifact filename is derived at runtime
# as ``Magpie-<version>-<target>``; the version comes from the MAGPIE_VERSION
# env var (set by the release workflow from the pushed tag) when available,
# otherwise from ``magpie.__version__``.
TARGETS: tuple[str, ...] = (
    "windows-x64",
    "macos-x64",
    "macos-arm64",
    "linux-x86_64",
)


def _resolve_version() -> str:
    override = os.environ.get("MAGPIE_VERSION", "").strip()
    if override:
        # Strip a leading "v" so tags like v1.2.3 yield 1.2.3.
        return override.lstrip("v")
    sys.path.insert(0, str(ROOT))
    try:
        from magpie import __version__
        return __version__
    finally:
        sys.path.pop(0)


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

# System libraries required by PyQt6 on Ubuntu/Debian.
DEB_DEPENDS = (
    "libegl1",
    "libgl1",
    "libdbus-1-3",
    "libfontconfig1",
    "libxkbcommon-x11-0",
    "libxcb-cursor0",
    "libxcb-icccm4",
    "libxcb-image0",
    "libxcb-keysyms1",
    "libxcb-randr0",
    "libxcb-render-util0",
    "libxcb-shape0",
    "libxcb-xinerama0",
    "libxcb-xkb1",
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


def _generate_icons() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "generate_icons.py")],
        cwd=ROOT,
        check=True,
    )


def _pyinstaller_command(
    *,
    target: str,
    name: str,
    onefile: bool,
    console: bool,
) -> list[str]:
    """Build the PyInstaller command line."""
    entrypoint = ROOT / "magpie" / "ImageClassifierQt.py"
    separator = ";" if sys.platform.startswith("win") else ":"

    command: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile" if onefile else "--onedir",
        "--console" if console else "--windowed",
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
    if ICON_PATH.exists():
        command.extend(["--icon", str(ICON_PATH)])
    for module in EXCLUDED_PYQT6_MODULES:
        command.extend(["--exclude-module", module])
    command.append(str(entrypoint))
    return command


def _build_onedir(*, target: str, version: str, console: bool) -> Path:
    """Build in onedir mode. Returns the output directory path."""
    name = f"Magpie-{version}-{target}"
    print(f"[build] onedir target={target} version={version} -> {name}/")
    command = _pyinstaller_command(
        target=target, name=name, onefile=False, console=console,
    )
    subprocess.run(command, cwd=ROOT, env=_sanitized_env(), check=True)
    return DIST_DIR / name


def _build_portable(*, version: str, console: bool) -> Path:
    """Build Windows portable (onefile) exe. Returns the output file path."""
    name = f"Magpie-{version}-windows-x64-portable"
    print(f"[build] portable version={version} -> {name}")
    command = _pyinstaller_command(
        target="windows-x64", name=name, onefile=True, console=console,
    )
    subprocess.run(command, cwd=ROOT, env=_sanitized_env(), check=True)
    exe_path = DIST_DIR / f"{name}.exe"
    print(f"[build] portable exe: {exe_path}")
    return exe_path


def _build_inno_setup(*, version: str, onedir_path: Path) -> Path:
    """Run Inno Setup compiler to produce the Windows installer."""
    iss_path = ROOT / "packaging" / "installer.iss"
    print(f"[build] Inno Setup: {iss_path}")
    command: list[str] = [
        "iscc",
        str(iss_path),
        f"/DAppVersion={version}",
        f"/DSourceDir={onedir_path}",
        f"/DOutputDir={DIST_DIR}",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    output = DIST_DIR / f"Magpie-{version}-windows-x64-setup.exe"
    print(f"[build] installer: {output}")
    return output


def _build_deb(*, version: str, onedir_path: Path) -> Path:
    """Build a .deb package from the onedir output."""
    deb_name = f"Magpie-{version}-linux-x86_64"
    deb_file = DIST_DIR / f"{deb_name}.deb"
    print(f"[build] deb: {deb_file}")

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / deb_name
        # Application files
        app_dir = staging / "opt" / "magpie"
        app_dir.mkdir(parents=True)
        shutil.copytree(onedir_path, app_dir, dirs_exist_ok=True)
        bundled_executable = app_dir / onedir_path.name
        desktop_executable = app_dir / "Magpie"
        if not bundled_executable.exists():
            raise FileNotFoundError(
                f"Expected PyInstaller executable not found: {bundled_executable}"
            )
        bundled_executable.rename(desktop_executable)
        desktop_executable.chmod(0o755)

        # Desktop entry
        apps_dir = staging / "usr" / "share" / "applications"
        apps_dir.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging" / "magpie.desktop", apps_dir)

        # Icon
        icon_dir = staging / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps"
        icon_dir.mkdir(parents=True)
        shutil.copy2(ICON_SVG, icon_dir / "magpie.svg")

        # DEBIAN/control
        debian_dir = staging / "DEBIAN"
        debian_dir.mkdir()
        control = debian_dir / "control"
        control.write_text(
            f"Package: magpie\n"
            f"Version: {version}\n"
            f"Section: graphics\n"
            f"Priority: optional\n"
            f"Architecture: amd64\n"
            f"Depends: {', '.join(DEB_DEPENDS)}\n"
            f"Maintainer: mangoa <3508312371@qq.com>\n"
            f"Description: A keyboard-driven desktop image classification tool\n",
            encoding="utf-8",
        )

        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(staging), str(deb_file)],
            check=True,
        )

    print(f"[build] deb: {deb_file}")
    return deb_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Magpie with PyInstaller")
    parser.add_argument("--target", required=True, choices=sorted(TARGETS))
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build with a console window so smoke tests can read stdout/stderr.",
    )
    parser.add_argument(
        "--portable",
        action="store_true",
        help="(Windows only) Build a single-file portable exe using --onefile.",
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="After building onedir, create an installer "
             "(Inno Setup on Windows, .deb on Linux).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    version = _resolve_version()
    print(f"[build] target={args.target} version={version}")

    _generate_icons()

    # --- Portable (Windows onefile) ---
    if args.portable:
        if not args.target.startswith("windows"):
            print("[build] --portable is only supported for Windows targets")
            return 1
        _build_portable(version=version, console=args.console)
        return 0

    # --- Default: onedir build ---
    onedir_path = _build_onedir(
        target=args.target, version=version, console=args.console,
    )

    # --- Installer (optional post-step) ---
    if args.installer:
        if args.target.startswith("windows"):
            _build_inno_setup(version=version, onedir_path=onedir_path)
        elif args.target.startswith("linux"):
            _build_deb(version=version, onedir_path=onedir_path)
        else:
            print(f"[build] --installer not yet supported for {args.target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
