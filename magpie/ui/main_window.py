from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, QPoint, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFontMetrics, QKeyEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from magpie.config import (
    AppState,
    ClassificationRecord,
    Preferences,
    ProjectPathError,
    image_key,
    resolve_active_categories,
    resolve_active_sort,
    resolve_class_names,
    resolve_labels_dir,
    resolve_output_dir,
)
from magpie.core import (
    CustomSortError,
    OperationHistory,
    TargetModifiedError,
    classify_image,
    draw_bboxes_on_pixmap,
    ensure_category_folders,
    label_path_for_image,
    list_image_files,
    load_pixmap,
    load_yolo_labels,
    resolve_target_path,
    undo_operation,
)
from magpie.models import BUILTIN_SORT_PRESETS, Category, OperationKind, SortPreset
from magpie.ui.conflict_dialog import ConflictDialog
from magpie.ui.debounced_saver import DebouncedSaver
from magpie.ui.image_view import ImageView
from magpie.ui.preferences_dialog import PreferencesDialog
from magpie.ui.project_settings_dialog import ProjectSettingsDialog
from magpie.ui.shortcuts_dialog import ShortcutsDialog
from magpie.ui.side_panel import SidePanel


class StatusProxy:
    def __init__(self, window: "MainWindow") -> None:
        self.window = window

    def showMessage(self, message: str, timeout: int = 0) -> None:
        self.window.set_message(message, timeout)


class ElidedLabel(QLabel):
    """QLabel that elides its text in the middle to fit the available width."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = text or ""
        self.setToolTip(self._full_text if self._full_text else "")
        self._update_elided()

    def fullText(self) -> str:
        return self._full_text

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self) -> None:
        metrics: QFontMetrics = self.fontMetrics()
        available = max(0, self.width() - 4)
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideMiddle, available)
        super().setText(elided)


class MainWindow(QMainWindow):
    def __init__(self, preferences: Preferences | None = None, state: AppState | None = None):
        super().__init__()
        self.preferences = preferences or Preferences.load()
        self.state = state or AppState.load()
        self.operation_kind = self.preferences.default_operation
        self.history = OperationHistory()
        self.image_files: list[Path] = []
        self.current_index = max(0, self.state.current_index)
        self.category_shortcuts: list[QShortcut] = []
        self.class_names: list[str] = []
        self.classification_record: ClassificationRecord | None = None
        self.remembered_conflict_strategy: str | None = None
        self.batch_conflict_strategy: str | None = None
        # Active project-resolved state. Re-resolved every time a folder opens.
        self.active_sort_preset, self.active_sort_descending = resolve_active_sort(
            self.preferences, None
        )
        self.active_conflict_strategy: str = self.preferences.conflict_strategy
        self.active_recursive_scan: bool = self.preferences.recursive_scan
        self.active_output_dir: Path | None = None
        self.active_labels_dir: Path | None = None
        self.active_categories: list[Category] = resolve_active_categories(self.preferences)

        # Coalesce disk writes so high-frequency keyboard flow doesn't fsync
        # on every keystroke. Each saver has a 500 ms idle window; closeEvent
        # flushes both.
        self._record_saver: DebouncedSaver | None = None
        self._state_saver = DebouncedSaver(self.state.save, interval_ms=500, parent=self)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_image)

        self.setWindowTitle("Magpie")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self._create_ui()
        self._create_status_bar()
        self._create_actions()
        self._create_menus()
        self._register_category_shortcuts()
        self._restore_window_state()

        if self.state.image_folder:
            self.open_image_folder(self.state.image_folder, reset_index=False)
        else:
            self._show_empty_state()

    # Right-column (side panel) width — also used to size the footer's
    # right-side undo button so the visual columns line up.
    _RIGHT_COLUMN_WIDTH = 320

    def _create_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root = QVBoxLayout(central_widget)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ---- Top row: image area + side panel ----
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self.image_view = ImageView()
        self.image_view.folderDropped.connect(self._handle_dropped_path)
        self.image_view.fitRequested.connect(lambda: self.set_message("已适应窗口", 1500))
        self.image_view.previousRequested.connect(self.previous_image)
        self.image_view.nextRequested.connect(self.next_image)
        self.image_view.autoplayRequested.connect(lambda: self.autoplay_action.trigger())
        self.image_view.contextMenuRequested.connect(self._show_image_context_menu)
        top_row.addWidget(self.image_view, stretch=1)

        self.side_panel = SidePanel()
        self.side_panel.manageCategoriesRequested.connect(self.open_preferences)
        top_row.addWidget(self.side_panel)

        root.addLayout(top_row, stretch=1)

        # ---- Footer row: image-name label (left) + undo button (right) ----
        footer_row = QHBoxLayout()
        footer_row.setSpacing(12)

        self.image_name_label = QLabel("")
        self.image_name_label.setObjectName("imageNameLabel")
        self.image_name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        footer_row.addWidget(self.image_name_label, stretch=1)

        self.undo_button = QPushButton("撤销 Ctrl+Z")
        self.undo_button.setObjectName("undoButton")
        self.undo_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.undo_button.setEnabled(False)
        self.undo_button.setFixedWidth(self._RIGHT_COLUMN_WIDTH)
        self.undo_button.clicked.connect(self.undo)
        footer_row.addWidget(self.undo_button)

        root.addLayout(footer_row)

        self.image_view.setFocus()
        self._refresh_side_panel()

    def _create_status_bar(self) -> None:
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("statusProgressBar")
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.setVisible(False)
        status_bar.addWidget(self.progress_bar)

        self.index_label = QLabel("0 / 0")
        self.index_label.setObjectName("indexLabel")
        status_bar.addPermanentWidget(self.index_label)

        self.path_label = ElidedLabel()
        self.path_label.setObjectName("pathLabel")
        status_bar.addPermanentWidget(self.path_label, 1)

        self.status = StatusProxy(self)

    def set_message(self, message: str, timeout: int = 0) -> None:
        bar = self.statusBar()
        if not message:
            bar.clearMessage()
            return
        bar.showMessage(message, timeout if timeout > 0 else 0)

    def _create_actions(self) -> None:
        self.open_folder_action = QAction("打开图片文件夹", self)
        self.open_folder_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Open))
        self.open_folder_action.triggered.connect(self.choose_image_folder)

        self.project_settings_action = QAction("本目录设置…", self)
        self.project_settings_action.triggered.connect(self.open_project_settings)
        self.project_settings_action.setEnabled(False)

        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        self.exit_action.triggered.connect(self.close)

        self.previous_action = QAction("上一张", self)
        self.previous_action.triggered.connect(self.previous_image)

        self.next_action = QAction("下一张", self)
        self.next_action.triggered.connect(self.next_image)

        self.autoplay_action = QAction("自动播放", self)
        self.autoplay_action.setCheckable(True)
        self.autoplay_action.triggered.connect(self.toggle_autoplay)

        self.jump_action = QAction("跳转", self)
        self.jump_action.setShortcut(QKeySequence("Ctrl+G"))
        self.jump_action.triggered.connect(self.jump_to_image)

        self.copy_name_action = QAction("复制图片名", self)
        self.copy_name_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Copy))
        self.copy_name_action.triggered.connect(self.copy_image_name)

        self.undo_action = QAction("撤销", self)
        self.undo_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Undo))
        self.undo_action.triggered.connect(self.undo)

        self.preferences_action = QAction("首选项", self)
        self.preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        self.preferences_action.triggered.connect(self.open_preferences)

        self.fit_action = QAction("适应窗口", self)
        self.fit_action.setShortcut(QKeySequence("F"))
        self.fit_action.triggered.connect(self.image_view.fit_to_window)

        self.actual_size_action = QAction("1:1", self)
        self.actual_size_action.setShortcut(QKeySequence("0"))
        self.actual_size_action.triggered.connect(self.image_view.actual_size)

        self.zoom_in_action = QAction("放大", self)
        self.zoom_in_action.setShortcut(QKeySequence("+"))
        self.zoom_in_action.triggered.connect(lambda: self.image_view.zoom(1.25))

        self.zoom_out_action = QAction("缩小", self)
        self.zoom_out_action.setShortcut(QKeySequence("-"))
        self.zoom_out_action.triggered.connect(lambda: self.image_view.zoom(0.8))

        self.show_bbox_action = QAction("显示 BBox", self)
        self.show_bbox_action.setShortcut(QKeySequence("B"))
        self.show_bbox_action.setCheckable(True)
        self.show_bbox_action.setChecked(self.preferences.show_bboxes)
        self.show_bbox_action.triggered.connect(self.toggle_bboxes)

        self.mode_action = QAction("复制模式", self)
        self.mode_action.setCheckable(True)
        self.mode_action.setChecked(self.operation_kind == OperationKind.MOVE)
        self.mode_action.triggered.connect(self.toggle_operation_mode)

        self.shortcuts_action = QAction("快捷键速查", self)
        self.shortcuts_action.triggered.connect(self.show_shortcuts)

        self.about_action = QAction("关于", self)
        self.about_action.triggered.connect(self.show_about)

        self._update_action_states()

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.open_folder_action)
        self.recent_menu = file_menu.addMenu("最近打开")
        self._refresh_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(self.preferences_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        browse_menu = self.menuBar().addMenu("浏览")
        browse_menu.addAction(self.previous_action)
        browse_menu.addAction(self.next_action)
        browse_menu.addAction(self.autoplay_action)
        browse_menu.addAction(self.jump_action)
        browse_menu.addSeparator()
        browse_menu.addAction(self.fit_action)
        browse_menu.addAction(self.actual_size_action)
        browse_menu.addAction(self.zoom_in_action)
        browse_menu.addAction(self.zoom_out_action)
        browse_menu.addSeparator()
        browse_menu.addAction(self.show_bbox_action)

        classify_menu = self.menuBar().addMenu("分类")
        classify_menu.addAction(self.undo_action)
        classify_menu.addSeparator()
        classify_menu.addAction(self.mode_action)
        classify_menu.addSeparator()
        classify_menu.addAction(self.project_settings_action)
        clear_record_action = classify_menu.addAction("清除本目录分类记录")
        clear_record_action.triggered.connect(self.clear_current_classification_record)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction(self.shortcuts_action)
        help_menu.addAction(self.about_action)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Left:
            self.previous_image()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self.next_image()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space:
            self.autoplay_action.trigger()
            event.accept()
            return
        super().keyPressEvent(event)

    def _register_category_shortcuts(self) -> None:
        for shortcut in self.category_shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.category_shortcuts.clear()

        for category in self.active_categories:
            if not category.key.strip():
                continue
            shortcut = QShortcut(QKeySequence(category.key), self)
            shortcut.activated.connect(lambda category=category: self.classify_current_image(category))
            self.category_shortcuts.append(shortcut)

    def _restore_window_state(self) -> None:
        if self.state.geometry_hex:
            self.restoreGeometry(QByteArray.fromHex(self.state.geometry_hex.encode("ascii")))
        if self.state.window_state_hex:
            self.restoreState(QByteArray.fromHex(self.state.window_state_hex.encode("ascii")))

    def choose_image_folder(self) -> None:
        default_dir = self.state.image_folder or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹", default_dir)
        if folder:
            self.open_image_folder(folder)

    def open_project_settings(self) -> None:
        if not self.state.image_folder:
            return
        folder_path = Path(self.state.image_folder)
        overrides = self.state.overrides_for(self.state.image_folder)
        dialog = ProjectSettingsDialog(folder_path, self.preferences, overrides, self)
        if not dialog.exec():
            return
        result = dialog.result_overrides()
        if result is None:
            return

        # Snapshot the effective sort before applying overrides, so we can
        # detect a sort change and prompt the user.
        prev_sort_id = self.active_sort_preset.id
        prev_sort_desc = self.active_sort_descending

        # Clear preset-related override keys then re-apply only those the user
        # actually set (None = revert to global default).
        existing = dict(self.state.per_folder_overrides.get(self.state.image_folder, {}))
        for key in (
            "output_dir",
            "labels_selection",
            "classes_selection",
            "sort_preset_id",
            "sort_descending",
        ):
            existing.pop(key, None)
        for key, value in {
            "output_dir": result.output_dir,
            "labels_selection": result.labels_selection,
            "classes_selection": result.classes_selection,
            "sort_preset_id": result.sort_preset_id,
            "sort_descending": result.sort_descending,
        }.items():
            if value is None:
                continue
            existing[key] = value
        if existing:
            self.state.per_folder_overrides[self.state.image_folder] = existing
        else:
            self.state.per_folder_overrides.pop(self.state.image_folder, None)

        # Determine the new effective sort to compare.
        new_overrides = self.state.overrides_for(self.state.image_folder)
        new_sort_preset, new_sort_desc = resolve_active_sort(
            self.preferences, new_overrides,
        )
        sort_changed = (
            prev_sort_id != new_sort_preset.id or prev_sort_desc != new_sort_desc
        )
        mode = self._ask_sort_change_mode_if_needed(sort_changed)
        self.open_image_folder(
            self.state.image_folder, reset_index=False, sort_change_mode=mode,
        )

    def _ask_sort_change_mode_if_needed(self, sort_changed: bool) -> str | None:
        """When sort actually changed AND the user has navigated past index 0,
        pop a 2-button dialog and return ``"full"`` or ``"tail"``. Otherwise
        return ``None`` (no special handling needed)."""
        if not sort_changed:
            return None
        if self.current_index <= 0 or not self.image_files:
            return None
        prefix_count = self.current_index
        tail_count = len(self.image_files) - self.current_index
        box = QMessageBox(self)
        box.setWindowTitle("排序方案已更改")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(
            f"当前位置：第 {self.current_index + 1} 张（共 {len(self.image_files)}）。\n"
            "新排序如何生效？"
        )
        full_btn = box.addButton(
            "从头开始（重排全部）", QMessageBox.ButtonRole.AcceptRole
        )
        tail_btn = box.addButton(
            f"保留前 {prefix_count} 张不动（仅重排剩余 {tail_count} 张）",
            QMessageBox.ButtonRole.AcceptRole,
        )
        box.setDefaultButton(tail_btn)
        box.exec()
        if box.clickedButton() is full_btn:
            return "full"
        return "tail"

    def open_image_folder(
        self,
        folder: str,
        reset_index: bool = True,
        sort_change_mode: str | None = None,
    ) -> None:
        """Open ``folder`` and refresh the image list.

        ``sort_change_mode`` is only used when reloading the *same* folder
        after the user changed the active sort preset:
        - ``"full"`` — re-sort everything, cursor → 0.
        - ``"tail"`` — keep ``image_files[0:current_index]`` (the prefix the
          user has already paged past) in the OLD order; only re-sort what
          comes after. Cursor stays at the boundary.

        When ``sort_change_mode`` is set, ``reset_index`` is ignored.
        """
        folder_path = Path(folder)
        if not folder_path.is_dir():
            QMessageBox.warning(self, "打开失败", f"{folder} 不是有效文件夹")
            return

        folder_key = str(folder_path)
        overrides = self.state.overrides_for(folder_key)

        # Snapshot the existing prefix BEFORE we touch image_files. Used
        # only when sort_change_mode == "tail" and we're reopening the
        # SAME folder.
        prefix_names: list[str] = []
        if sort_change_mode == "tail" and folder_key == self.state.image_folder:
            prefix_names = [p.name for p in self.image_files[: self.current_index]]

        # Resolve active sort preset (built-in or custom) + descending flag.
        self.active_sort_preset, self.active_sort_descending = resolve_active_sort(
            self.preferences, overrides
        )
        self.active_conflict_strategy = overrides.get(
            "conflict_strategy", self.preferences.conflict_strategy
        )
        # Refresh categories from current global active (no per-project override).
        self.active_categories = resolve_active_categories(self.preferences)

        if "recursive_scan" in overrides:
            recursive = bool(overrides["recursive_scan"])
        else:
            recursive = None  # decided below

        try:
            if recursive is None:
                recursive = self._resolve_recursive_scan(folder_path)
            self.active_recursive_scan = recursive
            scanned = list_image_files(
                folder_path,
                self.preferences.file_extensions,
                self.active_sort_preset,
                recursive=recursive,
                sort_descending=self.active_sort_descending,
            )
        except CustomSortError as exc:
            QMessageBox.warning(
                self,
                "自定义排序失败",
                f"{exc}\n\n请到 文件 → 首选项 → 排序 检查方案，已临时回退为自然排序。",
            )
            self.active_sort_preset = SortPreset(
                id=BUILTIN_SORT_PRESETS[0].id,
                name=BUILTIN_SORT_PRESETS[0].name,
                kind="builtin",
                field=BUILTIN_SORT_PRESETS[0].field,
            )
            self.active_sort_descending = False
            scanned = list_image_files(
                folder_path,
                self.preferences.file_extensions,
                self.active_sort_preset,
                recursive=recursive,
            )
        except Exception as exc:
            QMessageBox.warning(self, "打开失败", f"读取图片文件夹失败：{exc}")
            return

        # Splice the kept prefix in front (tail mode), else replace wholesale.
        if sort_change_mode == "tail" and prefix_names:
            name_to_path = {p.name: p for p in scanned}
            kept_prefix = [name_to_path[n] for n in prefix_names if n in name_to_path]
            visited_set = set(prefix_names)
            new_tail = [p for p in scanned if p.name not in visited_set]
            self.image_files = kept_prefix + new_tail
        else:
            self.image_files = scanned

        self.state.image_folder = folder_key
        self.state.add_recent_folder(folder_key)
        # Flush any pending writes from the previous record before swapping.
        if self._record_saver is not None:
            self._record_saver.flush()
        self.classification_record = ClassificationRecord.load(folder_path)
        self._record_saver = DebouncedSaver(
            self.classification_record.save, interval_ms=500, parent=self,
        )
        self.classification_record.set_dirty_callback(self._record_saver.request)
        self._refresh_recent_menu()

        # Resolve effective project paths (output / labels / classes).
        used_default_output = "output_dir" not in overrides
        try:
            self.active_output_dir = resolve_output_dir(self.preferences, overrides, folder_path)
        except ProjectPathError as exc:
            QMessageBox.warning(
                self,
                "输出目录模板错误",
                f"{exc}\n请在 文件 → 首选项 → 目录 修改模板，或用「分类 → 本目录设置」指定输出目录。",
            )
            self.active_output_dir = folder_path.parent / f"{folder_path.name}_filtered"
        self.active_labels_dir = resolve_labels_dir(self.preferences, overrides, folder_path)
        self.class_names = resolve_class_names(self.preferences, overrides)

        ensure_category_folders(self.active_output_dir, self.active_categories)
        self.history.clear()
        self.remembered_conflict_strategy = None
        self.batch_conflict_strategy = None
        self.side_panel.clear_recent_operations()

        if sort_change_mode == "tail":
            # Cursor sits at the boundary between kept prefix and new tail.
            boundary = len(prefix_names)
            self.current_index = max(0, min(boundary, max(len(self.image_files) - 1, 0)))
        elif sort_change_mode == "full":
            self.current_index = 0
        elif reset_index:
            saved_index = int(overrides.get("current_index", 0))
            self.current_index = max(0, min(saved_index, max(len(self.image_files) - 1, 0)))
        else:
            self.current_index = min(self.current_index, max(len(self.image_files) - 1, 0))

        if self.image_files:
            self._load_current_image()
        else:
            self._show_empty_state("当前文件夹没有可支持的图片文件。")

        self._refresh_side_panel()
        self._update_action_states()

        # First-time hint when the output dir comes from the template.
        if used_default_output:
            self.status.showMessage(
                f"默认输出 → {self.active_output_dir}（分类 → 本目录设置 可修改）",
                5000,
            )

    def _resolve_recursive_scan(self, folder_path: Path) -> bool:
        if self.preferences.remember_recursive_scan:
            return self.preferences.recursive_scan
        if not any(path.is_dir() for path in folder_path.iterdir()):
            return False

        checkbox = QCheckBox("记住此选择")
        box = QMessageBox(self)
        box.setWindowTitle("递归扫描")
        box.setText("所选目录包含子目录，是否递归扫描子目录中的图片？")
        box.setIcon(QMessageBox.Icon.Question)
        yes_button = box.addButton("递归扫描", QMessageBox.ButtonRole.YesRole)
        box.addButton("仅当前目录", QMessageBox.ButtonRole.NoRole)
        box.setCheckBox(checkbox)
        box.exec()
        recursive = box.clickedButton() == yes_button
        if checkbox.isChecked():
            self.preferences.recursive_scan = recursive
            self.preferences.remember_recursive_scan = True
            self.preferences.save()
        return recursive

    def _handle_dropped_path(self, path: str) -> None:
        dropped_path = Path(path)
        folder = dropped_path if dropped_path.is_dir() else dropped_path.parent
        self.open_image_folder(str(folder))

    def _load_current_image(self, fit: bool = True) -> None:
        if not self.image_files:
            self._show_empty_state()
            return

        image_path = self.image_files[self.current_index]
        source_folder = self.state.image_folder
        try:
            pixmap = load_pixmap(image_path)
            if self.show_bbox_action.isChecked() and self.active_labels_dir:
                boxes = load_yolo_labels(
                    label_path_for_image(
                        self.active_labels_dir, image_path, source_folder,
                    )
                )
                pixmap = draw_bboxes_on_pixmap(
                    pixmap, boxes, self.active_categories, self.class_names
                )
        except Exception as exc:
            self.status.showMessage(f"图片加载失败：{exc}", 5000)
            return

        self.image_view.set_pixmap(pixmap, fit=fit)
        record_key = image_key(image_path, source_folder) if source_folder else image_path.name
        labels = self.classification_record.labels_for(record_key) if self.classification_record else []
        self.image_view.set_badge(labels if self.preferences.show_classified_marker else [])
        self.state.current_index = self.current_index
        # Persist navigation progress so a crash / kill doesn't drop us back
        # to index 0. Debounced — actual writes happen at most every 500 ms.
        self._state_saver.request()
        self._update_status()
        self._refresh_side_panel()
        self._update_action_states()

    def _show_empty_state(self, message: str | None = None) -> None:
        self.image_view.clear()
        self.image_view.set_badge([])
        self.image_name_label.setText("")
        self.index_label.setText("0 / 0")
        self.path_label.setText("")
        self.status.showMessage(message or "请先打开图片文件夹。", 0)
        self._update_action_states()

    def previous_image(self) -> None:
        if not self.image_files:
            return
        if self.current_index > 0:
            self.current_index -= 1
        elif self.preferences.end_behavior == "loop":
            self.current_index = len(self.image_files) - 1
        self._load_current_image()

    def next_image(self) -> None:
        if not self.image_files:
            return

        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self._load_current_image()
            return

        if self.preferences.end_behavior == "loop":
            self.current_index = 0
            self._load_current_image()
        elif self.preferences.end_behavior == "prompt":
            QMessageBox.information(self, "提示", "已经是最后一张图像。")
        else:
            self._update_status("已经是最后一张图像")

    def toggle_autoplay(self, checked: bool) -> None:
        if checked:
            self.timer.start(self.preferences.autoplay_interval_ms)
        else:
            self.timer.stop()

    def _restart_autoplay_tick(self) -> None:
        if self.autoplay_action.isChecked():
            self.timer.start(self.preferences.autoplay_interval_ms)

    def _pause_autoplay(self) -> None:
        if self.autoplay_action.isChecked():
            self.autoplay_action.setChecked(False)
            self.timer.stop()

    def jump_to_image(self) -> None:
        if not self.image_files:
            return
        new_index, ok = QInputDialog.getInt(
            self,
            "跳转",
            "请输入要跳转的图像序号:",
            value=self.current_index + 1,
            min=1,
            max=len(self.image_files),
        )
        if ok:
            self.current_index = new_index - 1
            self._load_current_image()

    def copy_image_name(self) -> None:
        if not self.image_files:
            return
        QApplication.clipboard().setText(self.image_files[self.current_index].name)
        self.status.showMessage("已复制图片名", 2000)

    def reveal_current_image(self) -> None:
        if not self.image_files:
            return
        parent = self.image_files[self.current_index].parent
        if not parent.exists():
            self.status.showMessage("目录不存在", 2000)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent)))

    def _show_image_context_menu(self, global_pos: QPoint) -> None:
        if not self.image_files:
            return
        menu = QMenu(self)
        menu.addAction(self.previous_action)
        menu.addAction(self.next_action)
        menu.addSeparator()
        menu.addAction(self.fit_action)
        menu.addAction(self.actual_size_action)
        menu.addAction(self.zoom_in_action)
        menu.addAction(self.zoom_out_action)
        menu.addSeparator()
        menu.addAction(self.show_bbox_action)
        menu.addAction(self.copy_name_action)
        reveal_action = QAction("在文件管理器中显示", menu)
        reveal_action.triggered.connect(self.reveal_current_image)
        menu.addAction(reveal_action)

        if self.active_categories:
            menu.addSeparator()
            classify_menu = menu.addMenu("分类到")
            for category in self.active_categories:
                label = f"{category.label}  [{category.key}]"
                action = QAction(label, classify_menu)
                action.triggered.connect(
                    lambda checked=False, cat=category: self.classify_current_image(cat)
                )
                classify_menu.addAction(action)
        menu.exec(global_pos)

    def classify_current_image(self, category: Category) -> None:
        if not self.image_files:
            return
        if self.active_output_dir is None:
            QMessageBox.warning(self, "缺少输出目录", "无法确定输出目录。请重新打开图片文件夹。")
            return

        image_path = self.image_files[self.current_index]
        target_path, strategy = self._resolve_conflict_target(image_path, category)
        if target_path is None and strategy == "skip":
            self.status.showMessage(f"已跳过：{image_path.name}（目标已存在）", 2000)
            self._update_status()
            self.next_image()
            return
        if target_path is None or strategy == "cancel":
            self.status.showMessage("已取消分类", 2000)
            return

        try:
            operation = classify_image(
                image_path=image_path,
                output_dir=self.active_output_dir,
                category=category,
                kind=self.operation_kind,
                conflict_strategy=strategy,
                index=self.current_index,
                target_path=target_path,
            )
        except Exception as exc:
            QMessageBox.warning(self, "分类失败", f"写入失败：{exc}")
            return
        if operation is None:
            self.status.showMessage(f"已跳过：{image_path.name}", 2000)
            self._update_status()
            self.next_image()
            return

        self.history.push(operation)
        if self.classification_record:
            self.classification_record.add(
                image_key(image_path, self.state.image_folder),
                category.folder_name,
            )
        self.side_panel.add_recent_operation(operation, category)
        self._refresh_side_panel()
        self.status.showMessage(f"已分类到 {category.folder_name}", 2000)

        if self.operation_kind == OperationKind.MOVE:
            # After popping at current_index, the slot already points at what
            # *was* the next image (list shrank under us). Don't call
            # next_image() — that would skip a row.
            self.image_files.pop(self.current_index)
            if not self.image_files:
                self._show_empty_state("图片列表已处理完成。")
                return
            if self.current_index >= len(self.image_files):
                self.current_index = len(self.image_files) - 1
            self._load_current_image()
        else:
            self.next_image()
        self._restart_autoplay_tick()
        self._update_action_states()

    def _resolve_conflict_target(self, image_path: Path, category: Category) -> tuple[Path | None, str]:
        output_dir = self.active_output_dir or Path(".")
        # Mirror the source subdirectory layout under the category folder so
        # recursive scans don't collide on basename.
        rel = Path(image_key(image_path, self.state.image_folder)) if self.state.image_folder else Path(image_path.name)
        target = output_dir / category.folder_name / rel
        if not target.exists():
            return target, "rename"

        strategy = (
            self.batch_conflict_strategy
            or self.remembered_conflict_strategy
            or self.active_conflict_strategy
        )
        if strategy == "ask":
            dialog = ConflictDialog(str(target), self)
            if not dialog.exec():
                return None, "cancel"
            strategy = dialog.decision.strategy
            if dialog.decision.apply_to == "session":
                self.remembered_conflict_strategy = strategy
            elif dialog.decision.apply_to == "batch":
                self.batch_conflict_strategy = strategy

        return resolve_target_path(target, strategy), strategy

    def undo(self) -> None:
        self._pause_autoplay()
        operation = self.history.pop_undo()
        if operation is None:
            return

        try:
            self._perform_undo(operation, force=False)
        except TargetModifiedError as exc:
            reply = QMessageBox.warning(
                self,
                "目标文件已被外部修改",
                f"<b>{exc.target_path}</b> 与源文件的大小/修改时间不一致——"
                "可能是你在外部编辑过这份副本。\n\n仍要撤销（会删除这份副本）吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                # Re-push so user doesn't lose the undo entry.
                self.history.push(operation)
                self.status.showMessage("已取消撤销", 2000)
                self._update_action_states()
                return
            try:
                self._perform_undo(operation, force=True)
            except Exception as exc2:  # noqa: BLE001
                QMessageBox.warning(self, "撤销失败", str(exc2))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "撤销失败", str(exc))
        self._update_action_states()

    def _perform_undo(self, operation, force: bool) -> None:
        undo_operation(operation, force=force)
        if operation.kind == OperationKind.MOVE and operation.source_path not in self.image_files:
            self.image_files.insert(min(operation.index, len(self.image_files)), operation.source_path)
        if self.classification_record:
            key = image_key(operation.source_path, self.state.image_folder) if self.state.image_folder else operation.source_path.name
            self.classification_record.remove(key, operation.category_folder)
        self.current_index = min(operation.index, max(len(self.image_files) - 1, 0))
        self.side_panel.remove_recent_operation(operation)
        self._load_current_image()
        self._refresh_side_panel()
        if self.preferences.undo_prompt:
            QMessageBox.information(self, "撤销成功", f"已撤销 {operation.source_path.name}")
        else:
            self.status.showMessage("已撤销", 2000)

    def open_preferences(self) -> None:
        prev_sort_id = self.active_sort_preset.id
        prev_sort_desc = self.active_sort_descending
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec():
            self.preferences = dialog.preferences
            self.operation_kind = self.preferences.default_operation
            self.mode_action.setChecked(self.operation_kind == OperationKind.MOVE)
            self.show_bbox_action.setChecked(self.preferences.show_bboxes)
            self.timer.setInterval(self.preferences.autoplay_interval_ms)
            self.active_categories = resolve_active_categories(self.preferences)
            self._refresh_side_panel()
            self._register_category_shortcuts()
            if self.state.image_folder:
                # Detect a sort change before triggering the reload, so the
                # user can opt into "freeze prefix" if they've already worked
                # past index 0.
                new_overrides = self.state.overrides_for(self.state.image_folder)
                new_sort_preset, new_sort_desc = resolve_active_sort(
                    self.preferences, new_overrides,
                )
                sort_changed = (
                    prev_sort_id != new_sort_preset.id
                    or prev_sort_desc != new_sort_desc
                )
                mode = self._ask_sort_change_mode_if_needed(sort_changed)
                self.open_image_folder(
                    self.state.image_folder,
                    reset_index=False,
                    sort_change_mode=mode,
                )
            else:
                self.active_sort_preset, self.active_sort_descending = resolve_active_sort(
                    self.preferences, None
                )
                self.active_conflict_strategy = self.preferences.conflict_strategy
                self.active_recursive_scan = self.preferences.recursive_scan

    def toggle_bboxes(self) -> None:
        self.preferences.show_bboxes = self.show_bbox_action.isChecked()
        self.preferences.save()
        self._load_current_image(fit=False)

    def toggle_operation_mode(self, checked: bool) -> None:
        self.operation_kind = OperationKind.MOVE if checked else OperationKind.COPY
        self.mode_action.setText("移动模式" if checked else "复制模式")
        self.status.showMessage(f"已切换到{'移动' if checked else '复制'}模式", 2000)

    def clear_current_classification_record(self) -> None:
        if not self.classification_record:
            return
        if QMessageBox.question(self, "确认清除", "清除本目录分类记录？不会删除输出目录中的图片。") != QMessageBox.StandardButton.Yes:
            return
        self.classification_record.clear()
        self._load_current_image(fit=False)
        self._refresh_side_panel()
        self._update_status("已清除分类记录")

    def show_shortcuts(self) -> None:
        dialog = ShortcutsDialog(self._build_shortcut_groups(), self)
        dialog.exec()

    def _build_shortcut_groups(self) -> list[tuple[str, list[tuple[str, str, str]]]]:
        def text(action: QAction) -> str:
            return action.shortcut().toString() or "—"

        file_actions = [
            ("打开图片文件夹", text(self.open_folder_action), ""),
            ("首选项", text(self.preferences_action), ""),
            ("退出", text(self.exit_action), ""),
        ]
        browse = [
            ("上一张", "←", ""),
            ("下一张", "→", ""),
            ("自动播放 / 暂停", "Space", ""),
            ("跳转到指定序号", text(self.jump_action), ""),
            ("适应窗口", text(self.fit_action), "或 双击图片"),
            ("1:1 实际大小", text(self.actual_size_action), ""),
            ("放大", text(self.zoom_in_action), "或 Ctrl+滚轮"),
            ("缩小", text(self.zoom_out_action), ""),
            ("显示 BBox", text(self.show_bbox_action), ""),
            ("复制图片名", text(self.copy_name_action), "或 右键菜单"),
        ]
        classify = [
            ("撤销", text(self.undo_action), ""),
        ]

        output_dir = self.active_output_dir
        categories: list[tuple[str, str, str]] = []
        for category in self.active_categories:
            target = (
                str(output_dir / category.folder_name)
                if output_dir is not None
                else category.folder_name
            )
            categories.append((category.label, category.key or "—", target))
        if not categories:
            categories = [("（尚未配置类别）", "—", "前往 文件 → 首选项 添加")]

        return [
            ("文件", file_actions),
            ("浏览", browse),
            ("分类", classify),
            ("类别快捷键", categories),
        ]

    def show_about(self) -> None:
        QMessageBox.about(self, "关于", "Magpie\n键盘驱动的本地图像分类工具。")

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        if not self.state.recent_folders:
            empty_action = self.recent_menu.addAction("无")
            empty_action.setEnabled(False)
            return
        for folder in self.state.recent_folders[:10]:
            action = self.recent_menu.addAction(folder)
            action.triggered.connect(lambda checked=False, folder=folder: self.open_image_folder(folder))

    def _refresh_side_panel(self) -> None:
        if self.image_files and 0 <= self.current_index < len(self.image_files):
            current_path = self.image_files[self.current_index]
            current_key = (
                image_key(current_path, self.state.image_folder)
                if self.state.image_folder
                else current_path.name
            )
        else:
            current_key = ""
        self.side_panel.refresh(
            self.active_categories,
            str(self.active_output_dir or ""),
            self.classification_record,
            current_key,
        )

    def _update_status(self, message: str | None = None) -> None:
        if not self.image_files:
            return
        image_path = self.image_files[self.current_index]
        record_key = image_key(image_path, self.state.image_folder) if self.state.image_folder else image_path.name
        labels = self.classification_record.labels_for(record_key) if self.classification_record else []
        total = len(self.image_files)
        classified_suffix = f" · 已标 {', '.join(labels)}" if labels else ""
        # When recursive scanning, show the relative subpath so users can tell
        # `subA/0001.jpg` from `subB/0001.jpg`.
        display_name = record_key if "/" in record_key else image_path.name
        self.image_name_label.setText(f"{display_name}{classified_suffix}")
        self.index_label.setText(f"{self.current_index + 1} / {total}")
        self.path_label.setText(str(image_path.parent))
        if message:
            self.status.showMessage(message, 3000)

    def _update_action_states(self) -> None:
        has_images = bool(self.image_files)
        for action in [
            self.previous_action,
            self.next_action,
            self.autoplay_action,
            self.jump_action,
            self.copy_name_action,
            self.fit_action,
            self.actual_size_action,
            self.zoom_in_action,
            self.zoom_out_action,
        ]:
            action.setEnabled(has_images)
        if hasattr(self, "project_settings_action"):
            self.project_settings_action.setEnabled(bool(self.state.image_folder))
        self.undo_action.setEnabled(self.history.undo_count > 0)
        if hasattr(self, "undo_button"):
            self.undo_button.setEnabled(self.history.undo_count > 0)
        self.mode_action.setText("移动模式" if self.operation_kind == OperationKind.MOVE else "复制模式")

    def closeEvent(self, event) -> None:
        # Flush any pending debounced record save before final state save —
        # the queue may have unwritten classify/undo events from the last
        # ~500ms of keypresses.
        if self._record_saver is not None:
            self._record_saver.flush()
        self.state.current_index = self.current_index
        self.state.geometry_hex = bytes(self.saveGeometry().toHex()).decode("ascii")
        self.state.window_state_hex = bytes(self.saveState().toHex()).decode("ascii")
        if self.state.image_folder:
            self.state.update_overrides(
                self.state.image_folder,
                sort_preset_id=self.active_sort_preset.id,
                sort_descending=self.active_sort_descending,
                conflict_strategy=self.active_conflict_strategy,
                recursive_scan=self.active_recursive_scan,
                current_index=self.current_index,
            )
        # Cancel any in-flight debounce timer and write state right now (close
        # is the one place we want a synchronous, guaranteed write).
        self._state_saver.flush()
        self.state.save()
        self.preferences.save()
        super().closeEvent(event)
