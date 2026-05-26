from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from magpie.config import AppState, ClassificationRecord, Preferences
from magpie.core import (
    OperationHistory,
    classify_image,
    draw_bboxes_on_pixmap,
    ensure_category_folders,
    label_path_for_image,
    list_image_files,
    load_class_names,
    load_pixmap,
    load_yolo_labels,
    redo_operation,
    resolve_target_path,
    undo_operation,
)
from magpie.models import Category, OperationKind
from magpie.ui.conflict_dialog import ConflictDialog
from magpie.ui.image_view import ImageView
from magpie.ui.preferences_dialog import PreferencesDialog
from magpie.ui.side_panel import SidePanel


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

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_image)

        self.setWindowTitle("Magpie")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self._create_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._register_category_shortcuts()
        self._restore_window_state()

        if self.state.image_folder:
            self.open_image_folder(self.state.image_folder, reset_index=False)
        else:
            self._show_empty_state()

    def _create_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.image_view = ImageView()
        self.image_view.folderDropped.connect(self._handle_dropped_path)
        self.side_panel = SidePanel()
        self.side_panel.setMinimumWidth(240)
        self.side_panel.setMaximumWidth(400)
        splitter.addWidget(self.image_view)
        splitter.addWidget(self.side_panel)
        splitter.setStretchFactor(0, 1)
        self.setCentralWidget(splitter)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._refresh_side_panel()

    def _create_actions(self) -> None:
        self.open_folder_action = QAction("打开图片文件夹", self)
        self.open_folder_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Open))
        self.open_folder_action.triggered.connect(self.choose_image_folder)

        self.open_labels_action = QAction("打开标签目录", self)
        self.open_labels_action.triggered.connect(self.choose_labels_folder)

        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        self.exit_action.triggered.connect(self.close)

        self.previous_action = QAction("上一张", self)
        self.previous_action.setShortcut(QKeySequence(Qt.Key.Key_Left))
        self.previous_action.triggered.connect(self.previous_image)

        self.next_action = QAction("下一张", self)
        self.next_action.setShortcut(QKeySequence(Qt.Key.Key_Right))
        self.next_action.triggered.connect(self.next_image)

        self.autoplay_action = QAction("自动播放", self)
        self.autoplay_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
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

        self.redo_action = QAction("重做", self)
        self.redo_action.setShortcuts([QKeySequence(QKeySequence.StandardKey.Redo), QKeySequence("Ctrl+Shift+Z")])
        self.redo_action.triggered.connect(self.redo)

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

        self.update_action = QAction("检查更新", self)
        self.update_action.triggered.connect(lambda: self.status.showMessage("当前版本暂不支持自动检查更新", 3000))

        self._update_action_states()

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.open_folder_action)
        file_menu.addAction(self.open_labels_action)
        self.recent_menu = file_menu.addMenu("最近打开")
        self._refresh_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = self.menuBar().addMenu("编辑")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addAction(self.copy_name_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.preferences_action)

        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.fit_action)
        view_menu.addAction(self.actual_size_action)
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.show_bbox_action)

        operation_menu = self.menuBar().addMenu("操作")
        operation_menu.addAction(self.mode_action)
        clear_record_action = operation_menu.addAction("清除本文件夹的分类记录")
        clear_record_action.triggered.connect(self.clear_current_classification_record)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction(self.shortcuts_action)
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.update_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for action in [
            self.open_folder_action,
            self.previous_action,
            self.next_action,
            self.autoplay_action,
            self.jump_action,
            self.undo_action,
            self.redo_action,
            self.mode_action,
            self.fit_action,
            self.preferences_action,
        ]:
            toolbar.addAction(action)

    def _register_category_shortcuts(self) -> None:
        for shortcut in self.category_shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.category_shortcuts.clear()

        for category in self.preferences.categories:
            shortcut = QShortcut(QKeySequence(category.key), self)
            shortcut.activated.connect(lambda category=category: self.classify_current_image(category))
            self.category_shortcuts.append(shortcut)

    def _restore_window_state(self) -> None:
        if self.state.geometry_hex:
            self.restoreGeometry(QByteArray.fromHex(self.state.geometry_hex.encode("ascii")))
        if self.state.window_state_hex:
            self.restoreState(QByteArray.fromHex(self.state.window_state_hex.encode("ascii")))

    def choose_image_folder(self) -> None:
        default_dir = self.preferences.source_dir or self.state.image_folder
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹", default_dir)
        if folder:
            self.open_image_folder(folder)

    def choose_labels_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择标签目录", self.preferences.labels_dir)
        if folder:
            self.preferences.labels_dir = folder
            self.preferences.save()
            self._load_current_image(fit=False)

    def open_image_folder(self, folder: str, reset_index: bool = True) -> None:
        folder_path = Path(folder)
        if not folder_path.is_dir():
            QMessageBox.warning(self, "打开失败", f"{folder} 不是有效文件夹")
            return

        try:
            recursive = self._resolve_recursive_scan(folder_path)
            self.image_files = list_image_files(
                folder_path,
                self.preferences.file_extensions,
                self.preferences.sort_strategy,
                recursive=recursive,
            )
        except Exception as exc:
            QMessageBox.warning(self, "打开失败", f"读取图片文件夹失败：{exc}")
            return

        self.state.image_folder = str(folder_path)
        self.state.add_recent_folder(str(folder_path))
        self.classification_record = ClassificationRecord.load(folder_path)
        self._refresh_recent_menu()
        ensure_category_folders(self.preferences.output_dir, self.preferences.categories)
        self.history.clear()

        if reset_index:
            self.current_index = 0
        else:
            self.current_index = min(self.current_index, max(len(self.image_files) - 1, 0))

        if self.image_files:
            self._load_current_image()
        else:
            self._show_empty_state("当前文件夹没有可支持的图片文件。")

        self._refresh_side_panel()
        self._update_action_states()

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
        try:
            pixmap = load_pixmap(image_path)
            if self.show_bbox_action.isChecked() and self.preferences.labels_dir:
                boxes = load_yolo_labels(label_path_for_image(self.preferences.labels_dir, image_path))
                self.class_names = load_class_names(self.preferences.classes_path)
                pixmap = draw_bboxes_on_pixmap(pixmap, boxes, self.preferences.categories, self.class_names)
        except Exception as exc:
            self.status.showMessage(f"图片加载失败：{exc}", 5000)
            return

        self.image_view.set_pixmap(pixmap, fit=fit)
        labels = self.classification_record.labels_for(image_path.name) if self.classification_record else []
        self.image_view.set_badge(labels if self.preferences.show_classified_marker else [])
        self.state.current_index = self.current_index
        self._update_status()
        self._update_action_states()

    def _show_empty_state(self, message: str | None = None) -> None:
        self.image_view.clear()
        self.image_view.set_badge([])
        self.status.showMessage(
            message
            or "欢迎使用 Magpie。请先在 编辑 → 首选项 中定义分类按键，然后点击 打开图片文件夹。",
            0,
        )
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

    def classify_current_image(self, category: Category) -> None:
        if not self.image_files:
            return
        if not self.preferences.output_dir:
            QMessageBox.warning(self, "缺少输出目录", "请先在 编辑 → 首选项 中设置默认输出目录。")
            return

        image_path = self.image_files[self.current_index]
        target_path, strategy = self._resolve_conflict_target(image_path, category)
        if target_path is None or strategy == "cancel":
            self.status.showMessage("已取消分类", 2000)
            return

        operation = classify_image(
            image_path=image_path,
            output_dir=self.preferences.output_dir,
            category=category,
            kind=self.operation_kind,
            conflict_strategy=strategy,
            index=self.current_index,
            target_path=target_path,
        )
        if operation is None:
            self.status.showMessage(f"已跳过：{image_path.name}", 2000)
            return

        self.history.push(operation)
        if self.classification_record:
            self.classification_record.add(image_path.name, category.folder_name)
        self._refresh_side_panel()
        self.status.showMessage(f"已分类到 {category.folder_name}", 2000)

        if self.operation_kind == OperationKind.MOVE:
            self.image_files.pop(self.current_index)
            if self.current_index >= len(self.image_files):
                self.current_index = max(0, len(self.image_files) - 1)
            if not self.image_files:
                self._show_empty_state("图片列表已处理完成。")
                return

        self.next_image()
        self._restart_autoplay_tick()
        self._update_action_states()

    def _resolve_conflict_target(self, image_path: Path, category: Category) -> tuple[Path | None, str]:
        target = Path(self.preferences.output_dir) / category.folder_name / image_path.name
        if not target.exists():
            return target, "rename"

        strategy = self.remembered_conflict_strategy or self.preferences.conflict_strategy
        if strategy == "ask":
            dialog = ConflictDialog(str(target), self)
            if not dialog.exec():
                return None, "cancel"
            strategy = dialog.decision.strategy
            if dialog.decision.remember:
                self.remembered_conflict_strategy = strategy

        return resolve_target_path(target, strategy), strategy

    def undo(self) -> None:
        self._pause_autoplay()
        operation = self.history.pop_undo()
        if operation is None:
            return
        try:
            undo_operation(operation)
            if operation.kind == OperationKind.MOVE and operation.source_path not in self.image_files:
                self.image_files.insert(min(operation.index, len(self.image_files)), operation.source_path)
            if self.classification_record:
                self.classification_record.remove(operation.source_path.name, operation.category_folder)
            self.current_index = min(operation.index, max(len(self.image_files) - 1, 0))
            self._load_current_image()
            self._refresh_side_panel()
            if self.preferences.undo_prompt:
                QMessageBox.information(self, "撤销成功", f"已撤销 {operation.source_path.name}")
            else:
                self.status.showMessage("已撤销", 2000)
        except Exception as exc:
            QMessageBox.warning(self, "撤销失败", str(exc))
        self._update_action_states()

    def redo(self) -> None:
        self._pause_autoplay()
        operation = self.history.pop_redo()
        if operation is None:
            return
        try:
            redo_operation(operation)
            if operation.kind == OperationKind.MOVE and operation.source_path in self.image_files:
                self.image_files.remove(operation.source_path)
            if self.classification_record:
                self.classification_record.add(operation.source_path.name, operation.category_folder)
            self.current_index = min(operation.index, max(len(self.image_files) - 1, 0))
            if self.image_files:
                self._load_current_image()
            else:
                self._show_empty_state("图片列表已处理完成。")
            self._refresh_side_panel()
            self.status.showMessage("已重做", 2000)
        except Exception as exc:
            QMessageBox.warning(self, "重做失败", str(exc))
        self._update_action_states()

    def open_preferences(self) -> None:
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec():
            self.preferences = dialog.preferences
            self.operation_kind = self.preferences.default_operation
            self.mode_action.setChecked(self.operation_kind == OperationKind.MOVE)
            self.show_bbox_action.setChecked(self.preferences.show_bboxes)
            self.timer.setInterval(self.preferences.autoplay_interval_ms)
            self._refresh_side_panel()
            self._register_category_shortcuts()
            ensure_category_folders(self.preferences.output_dir, self.preferences.categories)
            if self.state.image_folder:
                self.open_image_folder(self.state.image_folder, reset_index=False)

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
        if QMessageBox.question(self, "确认清除", "清除本文件夹的分类记录？不会删除输出目录中的图片。") != QMessageBox.StandardButton.Yes:
            return
        self.classification_record.clear()
        self._load_current_image(fit=False)
        self._refresh_side_panel()
        self._update_status("已清除分类记录")

    def show_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "快捷键速查",
            "← / →：上一张 / 下一张\n"
            "Space：自动播放 / 暂停\n"
            "Ctrl+G：跳转\n"
            "Ctrl+Z / Ctrl+Y：撤销 / 重做\n"
            "Ctrl+C：复制图片名\n"
            "F：适应窗口\n"
            "0：1:1 实际大小\n"
            "B：切换 BBox 显示\n"
            "Ctrl+O：打开图片文件夹\n"
            "Ctrl+,：首选项",
        )

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
        self.side_panel.refresh(self.preferences.categories, self.preferences.output_dir, self.classification_record)

    def _update_status(self, message: str | None = None) -> None:
        if not self.image_files:
            return
        image_path = self.image_files[self.current_index]
        labels = self.classification_record.labels_for(image_path.name) if self.classification_record else []
        classified_count = self.classification_record.classified_image_count() if self.classification_record else 0
        classified = f"已分类: {', '.join(labels)}" if labels else "未分类"
        parts = [
            f"{self.current_index + 1} / {len(self.image_files)}",
            image_path.name,
            str(image_path.parent),
            classified,
            f"已分类 {classified_count} / 总数 {len(self.image_files)}",
            f"撤销可用: {self.history.undo_count}",
        ]
        self.status.showMessage((message + " · " if message else "") + " · ".join(parts), 0)

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
        self.undo_action.setEnabled(self.history.undo_count > 0)
        self.redo_action.setEnabled(self.history.redo_count > 0)
        self.mode_action.setText("移动模式" if self.operation_kind == OperationKind.MOVE else "复制模式")

    def closeEvent(self, event) -> None:
        self.state.current_index = self.current_index
        self.state.geometry_hex = bytes(self.saveGeometry().toHex()).decode("ascii")
        self.state.window_state_hex = bytes(self.saveState().toHex()).decode("ascii")
        self.state.save()
        self.preferences.save()
        super().closeEvent(event)
