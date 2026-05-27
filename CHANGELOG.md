# Changelog

## 1.1.1

修复 1.1.0 系统审计里列出的 5 个 P0 问题，剩余 P1-P5 在 TODO.md 里追踪。

- **MOVE 模式跳图 bug**：classify 后会跳过一张图，已修复。
- **递归扫描下同名文件冲突**：分类记录 / BBox 标签查找 / 输出路径都改为按
  「相对源目录」路径区分；schema bump 到 v2，旧文件会被丢弃重建。
- **撤销 COPY 静默删覆盖**：撤销前先比对 source/target 的 size+mtime；
  目标被外部修改过会弹二次确认。
- **每次按键全量写盘**：用 QTimer 做了 500ms 防抖合并，关闭时强制 flush。
- **崩溃位置丢失**：每次切图都把 state 入队保存（防抖），不再只在关闭时写。

## 1.1.0

- 把"全局单值 + 项目级覆盖"配置整体改造为**多个具名方案**：类别 / 标签 / classes / 排序
  四类配置都有 PresetListView，编辑弹独立对话框。
- classes.txt 配置只支持**内联**（粘贴一行一个），不再读文件、不再从 labels 目录自动取。
- **换排序时弹提示**：current_index > 0 时可选"从头开始"或"保留前 N 张不动"两种生效范围。
- 类别 / 标签 / classes / 排序 UI 完全统一（同款 PresetListView）；类别编辑器内嵌完整
  4 列表格（拖排、双击改色、快捷键冲突高亮）。
- 标签方案编辑器去掉了"选择目录"按钮——值本质是相对源目录的字符串。
- 删除所有 pre-1.0 时期的迁移代码（约 250 行）；旧 JSON 解析失败时直接落回默认。

## 1.0.1

- CI: Linux Qt 系统依赖修复；Windows cp1252 print 编码兼容。

## 1.0.0

- Rebuilt the desktop app around JSON preferences/state, Pillow image loading, and a QGraphicsView image canvas.
- Added preferences UI, preset import/export, undo/redo, configurable end-of-folder behavior, BBox rendering, and packaging workflows.
