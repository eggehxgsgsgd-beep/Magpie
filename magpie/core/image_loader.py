from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps
from PyQt6.QtGui import QImage, QPixmap


def natural_key(path: Path) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


# Whitelist of safe Python builtins exposed to user-defined sort expressions.
# Notable omissions: __import__, open, eval, exec, compile, input, exit, quit,
# getattr/setattr/delattr, globals/locals, vars, type, object — these would
# either allow filesystem access or bypass the sandbox.
_SAFE_BUILTINS: dict[str, object] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "hash": hash,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "ord": ord,
    "pow": pow,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


class CustomSortError(ValueError):
    """Raised when a user-defined sort expression fails to compile or run."""


def compile_custom_sort_key(expr: str) -> Callable[[Path], object]:
    """Compile a user-provided Python expression into a sort key function.

    The expression is evaluated for each path with a restricted namespace that
    exposes only ``path``, ``name``, ``stem``, ``suffix``, ``mtime``, ``size``,
    ``re``, and the whitelisted builtins above. ``__import__`` and direct file
    I/O are not available.

    Raises ``CustomSortError`` with a useful message if the expression fails to
    compile.
    """
    expr = (expr or "").strip()
    if not expr:
        raise CustomSortError("自定义排序表达式为空")
    try:
        code = compile(expr, "<magpie-sort-expr>", "eval")
    except SyntaxError as exc:
        raise CustomSortError(f"语法错误：{exc.msg} (col {exc.offset})") from exc

    def key(path: Path):
        namespace = {
            "__builtins__": _SAFE_BUILTINS,
            "path": path,
            "name": path.name,
            "stem": path.stem,
            "suffix": path.suffix,
            "re": re,
        }
        # mtime/size are looked up lazily via properties on a wrapper would be
        # nicer, but dict eval needs concrete values; we always compute them.
        try:
            stat = path.stat()
            namespace["mtime"] = stat.st_mtime
            namespace["size"] = stat.st_size
        except OSError:
            namespace["mtime"] = 0.0
            namespace["size"] = 0
        return eval(code, namespace)  # noqa: S307 — sandboxed by namespace

    return key


def list_image_files(
    folder: str | Path,
    extensions: list[str],
    sort_preset,
    recursive: bool = False,
    sort_descending: bool = False,
) -> list[Path]:
    """List image files in ``folder``, sorted by ``sort_preset``.

    ``sort_preset`` is a :class:`magpie.models.SortPreset`:
    - ``kind="builtin"``: ``field`` ∈ {natural, name, mtime}
    - ``kind="custom"``: ``expression`` is the Python expr (sandboxed eval)
    """
    root = Path(folder)
    suffixes = {f".{ext.lower().lstrip('.')}" for ext in extensions}
    candidates = root.rglob("*") if recursive else root.iterdir()
    files = [path for path in candidates if path.is_file() and path.suffix.lower() in suffixes]

    if getattr(sort_preset, "kind", "builtin") == "custom":
        expression = getattr(sort_preset, "expression", "") or ""
        if not expression.strip():
            raise CustomSortError(
                f"自定义排序方案「{getattr(sort_preset, 'name', '?')}」表达式为空"
            )
        key_fn = compile_custom_sort_key(expression)
    else:
        field = getattr(sort_preset, "field", "natural") or "natural"
        if field == "name":
            key_fn = lambda item: item.name.lower()  # noqa: E731
        elif field == "mtime":
            key_fn = lambda item: item.stat().st_mtime  # noqa: E731
        else:  # natural
            key_fn = natural_key

    return sorted(files, key=key_fn, reverse=sort_descending)


def load_pixmap(path: str | Path) -> QPixmap:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGBA")
        data = image.tobytes("raw", "RGBA")
        q_image = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(q_image)
