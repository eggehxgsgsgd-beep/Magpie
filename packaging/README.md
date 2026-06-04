# Packaging

Build a local Magpie executable with PyInstaller. Build Linux release packages
on Ubuntu 22.04 or older so the resulting binary keeps a low enough glibc
baseline for Ubuntu 20.04 users.

```bash
python packaging/build.py --target windows-x64
```

Supported targets:

- `windows-x64`
- `macos-x64`
- `macos-arm64`
- `linux-x86_64`

The build output is written to `dist/`.
