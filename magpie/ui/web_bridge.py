from __future__ import annotations

import base64
import json
import logging
import mimetypes
from io import BytesIO
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from magpie.config import AppState, ClassificationRecord, Preferences
from magpie.core import (
    OperationHistory,
    classify_image,
    ensure_category_folders,
    label_path_for_image,
    list_image_files,
    load_yolo_labels,
    redo_operation,
    resolve_target_path,
    undo_operation,
    validate_folder_name,
)
from magpie.models import Category, Operation, OperationKind


LOGGER = logging.getLogger(__name__)

# Cap base64 image data we hand to the renderer; anything larger gets downscaled
# to keep the JS side responsive (Chromium tops out around 20MB per data URL).
MAX_IMAGE_BYTES = 6 * 1024 * 1024


def _json(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _category_to_dict(category: Category) -> dict:
    return {
        "key": category.key,
        "folder_name": category.folder_name,
        "display_name": category.display_name or category.folder_name,
        "color": category.color,
    }


def _preferences_to_dict(prefs: Preferences) -> dict:
    data = prefs.to_dict()
    # Categories come back with normalized display_name for convenience on the JS side.
    data["categories"] = [_category_to_dict(c) for c in prefs.categories]
    return data


def _operation_to_dict(op: Operation) -> dict:
    return {
        "source_path": str(op.source_path),
        "target_path": str(op.target_path),
        "category_folder": op.category_folder,
        "index": op.index,
        "kind": op.kind.value,
    }


def _image_to_data_url(path: Path) -> tuple[str, int, int]:
    """Load an image and return (data_url, width, height).

    Large images are downscaled to keep the channel payload small. JPEG/PNG/etc
    are re-encoded to JPEG when source is > MAX_IMAGE_BYTES to bound the size.
    """
    raw_size = path.stat().st_size
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"

    if raw_size <= MAX_IMAGE_BYTES and mime in {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}:
        data = path.read_bytes()
        with Image.open(path) as im:
            w, h = im.size
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{encoded}", w, h

    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        long_side = max(w, h)
        # Stay under ~2400px long edge for very big images — preserves preview
        # quality while cutting the payload by ~10x for 4K-class photos.
        max_side = 2400
        if long_side > max_side:
            scale = max_side / long_side
            new_size = (int(w * scale), int(h * scale))
            im = im.resize(new_size, Image.Resampling.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=82, optimize=True)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}", w, h


class MagpieBridge(QObject):
    """Backend exposed to the React UI over QWebChannel.

    Every slot accepts JSON-safe primitives and returns JSON strings (decoded
    on the JS side). Returning strings instead of dicts avoids QVariant edge
    cases with nested dataclasses across the channel.
    """

    toast = pyqtSignal(str, str)
    preferencesChanged = pyqtSignal(str)

    def __init__(self, window, preferences: Preferences, state: AppState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self.preferences = preferences
        self.state = state
        self.history = OperationHistory()
        self.image_files: list[Path] = []
        self.current_folder: str = ""
        self.classification_record: ClassificationRecord | None = None
        self._remembered_conflict: str | None = None

    # ── helpers ─────────────────────────────────────────────────────────────
    def _images_payload(self) -> list[dict]:
        items: list[dict] = []
        for path in self.image_files:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            items.append({
                "name": path.name,
                "path": str(path),
                "size": size,
            })
        return items

    def _record_payload(self) -> dict:
        if not self.classification_record:
            return {}
        return {name: list(cats) for name, cats in self.classification_record.entries.items()}

    def _index_for_path(self, path: Path) -> int:
        for index, candidate in enumerate(self.image_files):
            if candidate == path:
                return index
        return 0

    # ── initial state ───────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getInitialState(self) -> str:
        return _json({
            "preferences": _preferences_to_dict(self.preferences),
            "image_folder": self.state.image_folder,
            "recent_folders": self.state.recent_folders,
        })

    # ── folder / file pickers ───────────────────────────────────────────────
    @pyqtSlot(str, result=str)
    def pickFolder(self, kind: str) -> str:
        defaults = {
            "source": self.preferences.source_dir or self.state.image_folder or str(Path.home()),
            "output_dir": self.preferences.output_dir or str(Path.home()),
            "labels_dir": self.preferences.labels_dir or str(Path.home()),
            "source_dir": self.preferences.source_dir or str(Path.home()),
        }
        start = defaults.get(kind, str(Path.home()))
        path = QFileDialog.getExistingDirectory(self._window, "选择目录", start)
        return _json({"ok": bool(path), "path": path or ""})

    @pyqtSlot(str, result=str)
    def pickFile(self, kind: str) -> str:
        start = self.preferences.classes_path or str(Path.home())
        filt = "Text files (*.txt);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(self._window, "选择文件", start, filt)
        return _json({"ok": bool(path), "path": path or ""})

    # ── folder loading ──────────────────────────────────────────────────────
    def _scan_folder(self, folder: Path, recursive: bool) -> dict:
        try:
            self.image_files = list_image_files(
                folder,
                self.preferences.file_extensions,
                self.preferences.sort_strategy,
                recursive=recursive,
            )
        except Exception as exc:
            LOGGER.exception("Failed to scan %s", folder)
            return {"ok": False, "error": f"读取图片文件夹失败：{exc}"}

        self.current_folder = str(folder)
        self.state.image_folder = str(folder)
        self.state.add_recent_folder(str(folder))
        self.state.current_index = 0
        self.state.save()
        self.classification_record = ClassificationRecord.load(folder)
        self.history.clear()
        if self.preferences.output_dir:
            ensure_category_folders(self.preferences.output_dir, self.preferences.categories)

        return {
            "ok": True,
            "folder": str(folder),
            "images": self._images_payload(),
            "record": self._record_payload(),
            "recursive": recursive,
        }

    @pyqtSlot(str, result=str)
    def loadImageFolder(self, folder: str) -> str:
        folder_path = Path(folder)
        if not folder_path.is_dir():
            return _json({"ok": False, "error": f"{folder} 不是有效文件夹"})

        if self.preferences.remember_recursive_scan:
            return _json(self._scan_folder(folder_path, self.preferences.recursive_scan))

        try:
            has_subfolders = any(item.is_dir() for item in folder_path.iterdir())
        except OSError:
            has_subfolders = False

        if not has_subfolders:
            return _json(self._scan_folder(folder_path, False))

        return _json({
            "ok": False,
            "needs_recursive_prompt": True,
            "folder": str(folder_path),
        })

    @pyqtSlot(str, bool, bool, result=str)
    def confirmRecursive(self, folder: str, recursive: bool, remember: bool) -> str:
        folder_path = Path(folder)
        if remember:
            self.preferences.recursive_scan = recursive
            self.preferences.remember_recursive_scan = True
            self.preferences.save()
        return _json(self._scan_folder(folder_path, recursive))

    # ── image loading ───────────────────────────────────────────────────────
    @pyqtSlot(str, result=str)
    def getImageData(self, path: str) -> str:
        image_path = Path(path)
        if not image_path.is_file():
            return _json({"ok": False, "error": "文件不存在"})

        try:
            data_url, w, h = _image_to_data_url(image_path)
        except Exception as exc:
            LOGGER.exception("Failed to load image %s", image_path)
            return _json({"ok": False, "error": f"读取图像失败：{exc}"})

        boxes: list[dict] = []
        if self.preferences.show_bboxes and self.preferences.labels_dir:
            label_file = label_path_for_image(self.preferences.labels_dir, image_path)
            for bbox in load_yolo_labels(label_file):
                boxes.append({
                    "cls": bbox.class_id,
                    "cx": bbox.x_center,
                    "cy": bbox.y_center,
                    "w": bbox.width,
                    "h": bbox.height,
                })

        return _json({"ok": True, "dataUrl": data_url, "w": w, "h": h, "boxes": boxes})

    # ── classification ──────────────────────────────────────────────────────
    def _find_category(self, folder_name: str) -> Category | None:
        for cat in self.preferences.categories:
            if cat.folder_name == folder_name:
                return cat
        return None

    @pyqtSlot(str, str, str, str, bool, result=str)
    def classifyImage(self, image_path: str, folder_name: str, mode: str, conflict_action: str, remember: bool) -> str:
        if not self.preferences.output_dir:
            return _json({"ok": False, "error": "请先在设置中配置默认输出目录"})

        category = self._find_category(folder_name)
        if category is None:
            return _json({"ok": False, "error": f"未找到类别：{folder_name}"})

        src = Path(image_path)
        if not src.exists():
            return _json({"ok": False, "error": "源文件不存在"})

        kind = OperationKind.MOVE if mode == "move" else OperationKind.COPY
        target = Path(self.preferences.output_dir) / category.folder_name / src.name

        if conflict_action:
            strategy = conflict_action
            if remember:
                self._remembered_conflict = strategy
        else:
            if not target.exists():
                strategy = "rename"
            else:
                strategy = self._remembered_conflict or self.preferences.conflict_strategy
                if strategy == "ask":
                    return _json({
                        "ok": False,
                        "conflict": True,
                        "target": str(target),
                    })

        if strategy == "cancel":
            return _json({"ok": False, "skipped": True})

        resolved = resolve_target_path(target, strategy)
        if resolved is None:
            return _json({"ok": False, "skipped": True, "message": "已跳过"})

        index = self._index_for_path(src)
        try:
            operation = classify_image(
                image_path=src,
                output_dir=self.preferences.output_dir,
                category=category,
                kind=kind,
                conflict_strategy=strategy,
                index=index,
                target_path=resolved,
            )
        except Exception as exc:
            LOGGER.exception("classify_image failed")
            return _json({"ok": False, "error": f"分类失败：{exc}"})

        if operation is None:
            return _json({"ok": False, "skipped": True, "message": "已跳过"})

        self.history.push(operation)
        if self.classification_record:
            self.classification_record.add(src.name, category.folder_name)

        removed = False
        if kind == OperationKind.MOVE:
            try:
                self.image_files.pop(index)
                removed = True
            except IndexError:
                pass

        return _json({
            "ok": True,
            "removed": removed,
            "undos": self.history.undo_count,
            "redos": self.history.redo_count,
            "images": self._images_payload() if removed else None,
            "record": self._record_payload(),
            "target": str(operation.target_path),
            "message": f"已分类到 {category.display_name or category.folder_name}",
        })

    @pyqtSlot(result=str)
    def undo(self) -> str:
        operation = self.history.pop_undo()
        if operation is None:
            return _json({"ok": False})
        try:
            undo_operation(operation)
        except Exception as exc:
            LOGGER.exception("undo_operation failed")
            return _json({"ok": False, "error": f"撤销失败：{exc}"})

        if operation.kind == OperationKind.MOVE and operation.source_path not in self.image_files:
            self.image_files.insert(min(operation.index, len(self.image_files)), operation.source_path)
        if self.classification_record:
            self.classification_record.remove(operation.source_path.name, operation.category_folder)

        new_index = min(operation.index, max(len(self.image_files) - 1, 0))
        return _json({
            "ok": True,
            "undos": self.history.undo_count,
            "redos": self.history.redo_count,
            "images": self._images_payload(),
            "record": self._record_payload(),
            "index": new_index,
            "folder": operation.category_folder,
        })

    @pyqtSlot(result=str)
    def redo(self) -> str:
        operation = self.history.pop_redo()
        if operation is None:
            return _json({"ok": False})
        try:
            redo_operation(operation)
        except Exception as exc:
            LOGGER.exception("redo_operation failed")
            return _json({"ok": False, "error": f"重做失败：{exc}"})

        if operation.kind == OperationKind.MOVE and operation.source_path in self.image_files:
            self.image_files.remove(operation.source_path)
        if self.classification_record:
            self.classification_record.add(operation.source_path.name, operation.category_folder)

        new_index = min(operation.index, max(len(self.image_files) - 1, 0))
        return _json({
            "ok": True,
            "undos": self.history.undo_count,
            "redos": self.history.redo_count,
            "images": self._images_payload(),
            "record": self._record_payload(),
            "index": new_index,
            "folder": operation.category_folder,
        })

    # ── preferences ─────────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getPreferences(self) -> str:
        return _json(_preferences_to_dict(self.preferences))

    @pyqtSlot("QVariant", result=str)
    def savePreferences(self, prefs_data) -> str:
        try:
            if hasattr(prefs_data, "toVariant"):
                prefs_data = prefs_data.toVariant()
            if isinstance(prefs_data, str):
                prefs_data = json.loads(prefs_data)
            new_prefs = Preferences.from_dict(prefs_data)
        except Exception as exc:
            LOGGER.exception("savePreferences parse failed")
            return _json({"ok": False, "error": f"保存设置失败：{exc}"})

        for category in new_prefs.categories:
            error = validate_folder_name(category.folder_name)
            if error:
                return _json({"ok": False, "error": f"类别 {category.label}: {error}"})

        new_prefs.save()
        self.preferences = new_prefs
        if self.preferences.output_dir:
            ensure_category_folders(self.preferences.output_dir, self.preferences.categories)
        self.preferencesChanged.emit(_json(_preferences_to_dict(self.preferences)))
        return _json({"ok": True, "preferences": _preferences_to_dict(self.preferences)})

    @pyqtSlot(result=str)
    def clearRecord(self) -> str:
        if not self.classification_record:
            return _json({"ok": False})
        if QMessageBox.question(
            self._window,
            "确认清除",
            "清除本文件夹的分类记录？不会删除输出目录中的图片。",
        ) != QMessageBox.StandardButton.Yes:
            return _json({"ok": False, "cancelled": True})
        self.classification_record.clear()
        return _json({"ok": True, "record": {}})

    @pyqtSlot(str)
    def copyToClipboard(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text or "")

    @pyqtSlot(str)
    def addRecentFolder(self, folder: str) -> None:
        if folder:
            self.state.add_recent_folder(folder)
            self.state.save()

    @pyqtSlot(int)
    def saveAppState(self, current_index: int) -> None:
        self.state.current_index = int(current_index)
        self.state.save()

    @pyqtSlot()
    def showAbout(self) -> None:
        QMessageBox.about(self._window, "关于", "Magpie\n键盘驱动的本地图像分类工具。")

    @pyqtSlot()
    def showShortcuts(self) -> None:
        QMessageBox.information(
            self._window,
            "快捷键速查",
            "← / →：上一张 / 下一张\n"
            "Space：自动播放 / 暂停\n"
            "Ctrl+G：跳转\n"
            "Ctrl+Z / Ctrl+Y：撤销 / 重做\n"
            "Ctrl+C：复制图片名\n"
            "B：切换 BBox 显示\n"
            "Ctrl+O：打开图片文件夹\n"
            "Ctrl+,：首选项",
        )


__all__ = ["MagpieBridge"]
