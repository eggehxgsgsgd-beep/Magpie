# Magpie

Magpie 是一个键盘驱动的本地图像分类桌面工具，适合数据清洗和快速分桶。

## 技术架构

- UI 层：React + Babel Standalone（运行在 `QWebEngineView` 中的本地 HTML/JSX，资源位于
  `magpie/resources/web/`）。
- 后端：PyQt6 + Pillow，通过 `QWebChannel` 暴露文件夹扫描、图像加载、分类执行、
  撤销/重做、偏好读写、冲突处理等接口（实现见 `magpie/ui/web_bridge.py`）。
- React/Babel/qwebchannel.js 已离线打包到 `resources/web/vendor/`，应用无需联网即可工作。

## 安装开发环境

```bash
uv venv --python 3.11 .venv
uv pip install -e ".[dev]"
```

## 启动

```bash
magpie
```

## 使用

1. 打开 `编辑 → 首选项`，在“类别”中配置单键快捷键、类别文件夹名、显示名称和颜色。
2. 在“文件夹”中配置默认图片来源目录、输出目录、标签目录和可选的 `classes.txt`。
3. 点击 `文件 → 打开图片文件夹`，或把文件夹拖入窗口。
4. 使用 `← / →` 浏览，按配置的类别快捷键把图片复制或移动到输出目录。

## 主要快捷键

- `← / →`：上一张 / 下一张
- `Space`：自动播放 / 暂停
- `Ctrl+G`：跳转
- `Ctrl+Z / Ctrl+Y`：撤销 / 重做
- `Ctrl+C`：复制当前图片名
- `F`：适应窗口
- `0`：1:1 实际大小
- `+` / `-`：放大 / 缩小
- 滚轮：以鼠标位置为中心缩放
- 拖拽：平移已放大的图片
- `B`：切换 BBox 显示
- `Ctrl+O`：打开图片文件夹
- `Ctrl+,`：首选项

## 配置存储

应用不再使用 YAML。用户偏好、运行状态和每个源目录的分类记录会自动保存在 Qt 标准 AppData 目录中：

- `preferences.json`：类别、目录、显示和行为偏好
- `state.json`：上次图片目录、索引、窗口状态
- `classifications/<hash>.json`：源目录分类记录

用户可以通过首选项中的“导出预设 / 导入预设”分享 `.magpie-preset.json`。

## 打包

```bash
python packaging/build.py --target windows-x64
```
