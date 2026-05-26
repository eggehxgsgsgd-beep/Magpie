# Packaging

Build a local Magpie executable with PyInstaller:

```bash
python packaging/build.py --target windows-x64
```

Supported targets:

- `windows-x64`
- `macos-x64`
- `macos-arm64`
- `linux-x86_64`

The build output is written to `dist/`.
