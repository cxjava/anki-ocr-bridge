"""Static engine metadata (what to install, which Python versions work)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineInfo:
    key: str
    display: str
    packages: tuple[str, ...]
    # Python minor versions in order of preference.
    python_minors: tuple[int, ...]
    size_hint: str
    description_zh: str
    description_en: str


ENGINES: dict[str, EngineInfo] = {
    "rapidocr": EngineInfo(
        "rapidocr", "RapidOCR (PP-OCR ONNX)",
        ("rapidocr-onnxruntime", "pillow", "numpy"),
        (12, 11, 13, 10), "~100 MB",
        "轻量快速，使用 PP-OCR 的 ONNX 模型，默认引擎",
        "Lightweight and fast, runs PP-OCR ONNX models. Default.",
    ),
    "paddleocr": EngineInfo(
        "paddleocr", "PaddleOCR",
        ("paddlepaddle", "paddleocr", "pillow", "numpy"),
        (12, 11, 10, 13), "~1 GB",
        "完整的 PaddleOCR，精度更高但体积大、首次需下载模型",
        "Full PaddleOCR. More accurate, but large; downloads models on first use.",
    ),
}


def python_need(info: EngineInfo) -> str:
    return " / ".join(f"3.{m}" for m in sorted(info.python_minors))
