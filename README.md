# picfly

开源图片工具集，支持截图上传图床、OCR 文字识别，通过全局热键快速调用。现已兼容 Windows / Linux（Wayland & X11），Wayland 环境自动调用 XDG Portal，自带系统截图 UI。

## 功能特性

- **截图上传**：框选屏幕区域截图，自动上传至 PicLab 图床，返回图片链接
- **粘贴上传**：将剪贴板中的图片（或图片 URL）上传至图床
- **OCR 截图识别**：框选屏幕区域，调用白描 OCR 识别文字
- **OCR 粘贴板识别**：识别剪贴板中的图片文字
- **全局热键**：后台运行，随时通过热键触发功能

## 安装

```bash
pip install picfly
```

> **提示**：若使用 Conda/Mamba，请先 `mamba activate base` 后再安装。

### Linux 额外依赖

Wayland/X11 下需要额外的 DBus 绑定与截图依赖，可直接使用 Mamba：

```bash
mamba activate base
mamba install pillow mss dbus-next dbus-python -c conda-forge
```

若使用系统包管理器，请确保已安装 `dbus-python`（或 `python3-dbus`）以及图形环境的 DBus 服务。

## 环境变量配置

使用前需配置以下环境变量：

### PicLab 图床（截图/粘贴上传）

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `PICLAB_BASE_URL` | ✅ | 上传接口地址 |
| `PICLAB_API_KEY` | ✅ | Bearer Token 认证密钥 |
| `PICLAB_VERIFY_SSL` | ❌ | 设为 `false` 跳过证书校验 |
| `PICLAB_TIMEOUT` | ❌ | 请求超时时间（秒），默认 30 |
| `PICLAB_USE_SYSTEM_PROXY` | ❌ | 设为 `true` 使用系统代理 |

### OCR（文字识别）

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `BAIMIAO_BASE_URL` | ✅ | OCR 服务地址 |
| `BAIMIAO_API_KEY` | ✅ | API 密钥 |

## 使用方法

### 命令行启动

```bash
picfly
```

### Python 代码调用

```python
from picfly import main

main()
```

### 热键说明

启动后，程序在后台监听以下热键：

| 热键 | 功能 |
|------|------|
| `F8 + 9` | 截图上传 |
| `F8 + 0` | 粘贴上传 |
| `F8 + -` | OCR 截图识别 |
| `F8 + =` | OCR 粘贴板识别 |
| `F8 + ESC` | 退出程序 |

## 模块说明

### 工具类

```python
from picfly.utils import PicLabUploader, BaimiaoApiClient

# 图床上传
uploader = PicLabUploader()
result = uploader.upload("path/to/image.png")  # 本地文件
result = uploader.upload("https://example.com/image.png")  # 远程 URL
result = uploader.upload(image_bytes)  # 二进制数据

# OCR 识别
ocr = BaimiaoApiClient()
text = ocr.recognize("path/to/image.png")
text = ocr.recognize(pil_image)  # PIL Image 对象
text = ocr.recognize(image_bytes)  # 二进制数据
```

### 截图选择器

```python
from picfly.utils import RegionSelector

selector = RegionSelector()
image = selector.screenshot()  # Wayland 自动调用 Portal，X11/Windows 弹出 Tk 拖拽
```

## 系统要求

- **操作系统**：Windows 10/11，Linux 桌面（Wayland 或 X11）
- **Python**：3.9+

## 依赖

- `requests` - HTTP 请求
- `Pillow` - 图像处理 / Tk 画布截图
- `mss` - X11/Windows 截图抓取
- `dbus-next` - Wayland Portal 截图
- `dbus-python` - Linux 桌面通知所需 DBus 绑定（仅 Linux）
- `pynput` - 全局热键监听
- `pyclip` - 剪贴板操作
- `plyer` - 跨平台桌面通知

## 许可证

[MIT License](LICENSE)

## 作者

**mofanx** - yanwuning@live.cn
