# anki-ocr-bridge

[English](README.en.md) | **简体中文**

一个 Anki 插件（需要 Anki 26.08+），为卡片模板提供本地 **OCR REST 服务**，例如 DeckMasterPro 图片遮挡题型里的“自动识别文字”按钮。
各 OCR 引擎运行在各自独立的虚拟环境里，以子进程方式工作，不会影响 Anki 自带的 Python。

* 引擎：**RapidOCR**（使用 PP-OCR 的 ONNX 模型，默认）和 **PaddleOCR**
* 在 **工具 → OCR Bridge 设置** 中安装、卸载、切换引擎，可选择 pip 镜像
* 监听地址和端口可配置（默认 `127.0.0.1:8866`，无认证）
* 界面语言：中文 / English
* 需要系统已安装 **Python 3.10-3.13**（优先 3.12，不使用 3.14）。Windows 用户请先从 python.org 安装。

## REST 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | `{ok, engine, installed, running, version}` |
| GET | `/engines` | 引擎列表及安装状态 |
| POST | `/engines/select` | `{"engine": "rapidocr"}` |
| POST | `/ocr` | `{"image": "<base64 或 data URL>", "engine"?: "..."}` → `{width, height, boxes:[{x,y,w,h,text,conf}], engine, elapsed_ms}` |

坐标为原图像素。出错时返回 `{"error": "..."}`，文字使用当前界面语言。

## 目录结构

```
src/anki_ocr_bridge/        插件包（原样打包，zip 内无顶层文件夹）
  __init__.py               Anki 入口（菜单、自动启动）；在 Anki 之外导入也安全
  manifest.json config.json config.md
  core/                     纯标准库：配置、i18n、REST 服务、服务编排、venv 管理、worker 通信
  ui/settings.py            Qt6 设置对话框
  worker/                   运行在引擎 venv 内：worker_main.py + engines/
  user_files/               venv、日志（升级插件时 Anki 会保留；已被 git 忽略）
scripts/build.py            -> dist/anki_ocr_bridge.ankiaddon
scripts/dev_link.py         开发时软链接到 addons21
tests/                      python -m unittest discover -s tests
```

## 开发

```bash
python3 scripts/dev_link.py   # 然后重启 Anki
python3 -m unittest discover -s tests
python3 scripts/build.py
```

也可以使用 [just](https://github.com/casey/just)：`just install`（测试、打包并安装到本机 Anki，需先退出 Anki）、`just link`（开发用软链接）、`just --list` 查看全部命令。
