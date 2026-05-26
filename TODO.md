# Magpie TODO

待修复 / 待优化项，按严重度分级。完整背景见 1.1.0 时期审计报告。
P0 (5 项) 已在 1.1.x 时期处理，列出来仅作历史；当前 backlog 从 P1 起。

---

## P0 — 已修复（1.1.x）

- [x] **#1** MOVE 模式 classify 后跳一张 bug — `main_window.py:801-809`
- [x] **#2** 递归扫描下 basename 冲突 — ClassificationRecord 改为相对路径 key (schema v2)
- [x] **#3** 撤销 COPY 无差别 unlink target — 加 size/mtime 差异检测 + 二次确认
- [x] **#4** classification_record 每次按键全量写盘 — DebouncedSaver
- [x] **#5** 分类操作无崩溃恢复 — state 也用 DebouncedSaver

---

## P1 — 阻塞 UI / 影响流畅度

- [ ] **#6** 图片加载 / 文件操作全部在 UI 线程
  - `magpie/core/image_loader.py:139` PIL 同步打开
  - `magpie/core/classifier.py:65` `shutil.move/copy2` 同步阻塞
  - 修复：`QThreadPool` + ImageLoadTask + WriteQueue，UI 乐观推进

- [ ] **#7** 无预取 / 无 LRU 缓存
  - 每次切图都重新解码
  - 修复：`dict[Path, QPixmap]` 大小 3–5，预取下一张

- [ ] **#8** BBox pixmap 每次重画
  - `magpie/ui/main_window.py:627-636`
  - 修复：BBox 用 QGraphicsItem overlay，pixmap 不变

- [ ] **#9** `list_image_files` mtime/size 排序时 N 次 stat
  - `magpie/core/image_loader.py:117-128`
  - 修复：`os.scandir()` 一次拿到 mtime/size

---

## P2 — 工作流 / UX 缺口

- [ ] **#10** 没有批量分类（`Shift+→` 选区间 + 应用快捷键）

- [ ] **#11** 没有"跳到下一张未分类" — 加快捷键 `J` 用 `classification_record.entries` 反查

- [ ] **#12** 加载失败不自动跳过
  - `main_window.py:632` 解码失败 → toast 但 index 不变
  - 修复：catch 后 `next_image()`，累计坏图计数

- [ ] **#13** "最近操作"是死面板 — 点击行 → cursor 跳回那张图

- [ ] **#14** 没有进度条
  - `main_window._create_status_bar` 里 `progress_bar` 搭了壳没用
  - 接上 "已分 N / 总 M" 比例显示

- [ ] **#15** 单 process 检测缺失 — 加 `.lock` 文件 + 已有实例时拒绝启动

---

## P3 — 代码组织 / 重构债

- [ ] **#16** `main_window.py` 1042 行 — 拆 widgets / actions / handlers

- [ ] **#17** `preferences_dialog.py` 919 行 — `CustomSortPresetEditor` 挪到 `preset_editors.py`，各 tab 拆 mixin

- [ ] **#18** 中文字符串硬编码 — 拽到 `magpie/ui/strings.py`；主题 light/dark 当前不生效

- [ ] **#19** `active_*` 多字段散落 — 封装 `ActiveProjectState` dataclass

- [ ] **#20** preset 解析 / 错误反馈不一致 — 4 个 resolver 找不到的语义不同

- [ ] **#21** `CustomSortError` 触发后没真把 active_sort_preset_id 改回 — 下次开同一目录还撞同样的错

---

## P4 — BBox / 标签 / 边缘场景

- [ ] **#22** BBox class_id 超出已配置类别数 → 全灰
  - `magpie/core/bbox.py:79-82`
  - 修复：`hash(class_id) % len(palette)` 选 fallback 色（3 行）

- [ ] **#23** 没有"只看某类 BBox"过滤

- [ ] **#24** classes / categories 解耦造成的概念混乱 — 需要文档

---

## P5 — 测试 / 工程

- [ ] **#25** UI 测试覆盖几乎为 0
  - 加 `pytest-qt`，至少覆盖：classify 主路径、preset CRUD、排序变更弹框两分支

- [ ] **#26** 用户自定义排序的沙箱没有 fuzz 测试
  - 加 `hypothesis` property test，确认 whitelist 真拦得住所有逃逸

---

## 建议执行顺序

1. P1 异步化是单 PR 大块（#6+#7+#8 一起做），用户感知最明显
2. P2 小修小补可以一周 1–2 个慢慢做（#11/#12/#13/#22 都是 < 30 行）
3. P3 重构等代码再涨一波再考虑（< 1500 行还 OK）
4. P4 文档 + P5 测试是持续工作
