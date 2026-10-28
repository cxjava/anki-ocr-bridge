"""Tiny zh/en translation table. Pure stdlib so it can be unit-tested outside Anki."""
from __future__ import annotations

_lang = "en"

STRINGS: dict[str, dict[str, str]] = {
    "menu": {"zh": "OCR Bridge 设置", "en": "OCR Bridge Settings"},
    "title": {"zh": "OCR Bridge", "en": "OCR Bridge"},
    "tab_service": {"zh": "服务", "en": "Service"},
    "tab_engines": {"zh": "引擎", "en": "Engines"},
    "tab_test": {"zh": "测试", "en": "Test"},
    "host": {"zh": "监听地址", "en": "Listen address"},
    "port": {"zh": "端口", "en": "Port"},
    "auto_start": {"zh": "随 Anki 启动服务", "en": "Start service with Anki"},
    "idle_timeout": {"zh": "空闲释放 OCR 进程（分钟，0 为不释放）", "en": "Release OCR worker when idle (minutes, 0 = never)"},
    "language": {"zh": "界面语言", "en": "Language"},
    "lang_auto": {"zh": "自动", "en": "Auto"},
    "start": {"zh": "启动服务", "en": "Start service"},
    "stop": {"zh": "停止服务", "en": "Stop service"},
    "save": {"zh": "保存", "en": "Save"},
    "close": {"zh": "关闭", "en": "Close"},
    "status_running": {"zh": "运行中：{url}", "en": "Running: {url}"},
    "status_stopped": {"zh": "未运行", "en": "Stopped"},
    "non_loopback_warn": {
        "zh": "监听地址 {host} 不是本机回环地址，局域网内任何人都可以调用本机 OCR（无认证）。确定继续吗？",
        "en": "{host} is not a loopback address. Anyone on your network could call this OCR service (no authentication). Continue?",
    },
    "saved": {"zh": "已保存", "en": "Saved"},
    "engine_col": {"zh": "引擎", "en": "Engine"},
    "status_col": {"zh": "状态", "en": "Status"},
    "size_col": {"zh": "体积", "en": "Size"},
    "current_col": {"zh": "当前", "en": "Current"},
    "installed": {"zh": "已安装", "en": "Installed"},
    "not_installed": {"zh": "未安装", "en": "Not installed"},
    "install": {"zh": "安装", "en": "Install"},
    "uninstall": {"zh": "卸载", "en": "Uninstall"},
    "set_current": {"zh": "设为当前", "en": "Set as current"},
    "cancel": {"zh": "取消安装", "en": "Cancel install"},
    "mirror": {"zh": "pip 镜像", "en": "pip mirror"},
    "mirror_pypi": {"zh": "官方 PyPI", "en": "PyPI (official)"},
    "mirror_tsinghua": {"zh": "清华大学", "en": "Tsinghua"},
    "mirror_aliyun": {"zh": "阿里云", "en": "Aliyun"},
    "python_found": {"zh": "将使用 Python：{path}（{version}）", "en": "Using Python: {path} ({version})"},
    "python_missing": {
        "zh": "未找到可用的 Python（需要 {need}），请安装后重启 Anki。",
        "en": "No suitable Python found (need {need}). Please install it and restart Anki.",
    },
    "confirm_uninstall": {"zh": "确定卸载 {engine}？将删除其虚拟环境。", "en": "Uninstall {engine}? Its virtual environment will be deleted."},
    "install_done": {"zh": "{engine} 安装完成", "en": "{engine} installed"},
    "install_failed": {"zh": "{engine} 安装失败：{err}", "en": "{engine} install failed: {err}"},
    "install_cancelled": {"zh": "安装已取消", "en": "Install cancelled"},
    "busy": {"zh": "已有安装任务在进行中", "en": "An install is already running"},
    "choose_image": {"zh": "选择图片并识别", "en": "Choose image and recognize"},
    "test_result": {"zh": "识别到 {n} 个文字框，用时 {ms} ms（{engine}）", "en": "{n} boxes in {ms} ms ({engine})"},
    "test_failed": {"zh": "识别失败：{err}", "en": "OCR failed: {err}"},
    # REST / runtime errors
    "err_bad_request": {"zh": "请求格式错误", "en": "Bad request"},
    "err_no_image": {"zh": "缺少 image 字段", "en": "Missing 'image' field"},
    "err_too_large": {"zh": "图片为空或过大", "en": "Image is empty or too large"},
    "err_not_found": {"zh": "接口不存在", "en": "Not found"},
    "err_not_installed": {"zh": "引擎 {engine} 尚未安装，请在 工具 → OCR Bridge 中安装", "en": "Engine {engine} is not installed. Install it in Tools → OCR Bridge"},
    "err_unknown_engine": {"zh": "未知引擎：{engine}", "en": "Unknown engine: {engine}"},
    "err_worker_start": {"zh": "OCR 进程启动失败：{err}", "en": "Failed to start OCR worker: {err}"},
    "err_worker_died": {"zh": "OCR 进程意外退出", "en": "OCR worker exited unexpectedly"},
    "err_timeout": {"zh": "识别超时", "en": "OCR timed out"},
    "err_port_in_use": {"zh": "端口 {port} 已被占用，请更换端口", "en": "Port {port} is in use, choose another"},
    "err_ocr": {"zh": "识别失败：{err}", "en": "OCR failed: {err}"},
}


def set_language(lang: str) -> None:
    global _lang
    _lang = "zh" if str(lang).lower().startswith("zh") else "en"


def get_language() -> str:
    return _lang


def t(key: str, **kw: object) -> str:
    entry = STRINGS.get(key)
    text = entry.get(_lang) or entry["en"] if entry else key
    return text.format(**kw) if kw else text


def apply_config_language(cfg_lang: str, system_lang: str = "") -> None:
    """cfg_lang is 'auto' | 'zh' | 'en'. 'auto' follows `system_lang` (e.g. Anki's UI language)."""
    if cfg_lang in ("zh", "en"):
        set_language(cfg_lang)
    else:
        set_language(system_lang or "en")
