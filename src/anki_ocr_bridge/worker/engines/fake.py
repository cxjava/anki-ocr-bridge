"""Dependency-free engine used by the test-suite."""
from __future__ import annotations

import struct


def selfcheck() -> None:
    pass


class Engine:
    def __init__(self, options: dict):
        pass

    def ocr(self, data: bytes) -> dict:
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a PNG")
        w, h = struct.unpack(">II", data[16:24])
        return {"width": w, "height": h,
                "boxes": [{"x": 1, "y": 2, "w": w // 2, "h": h // 2, "text": "fake", "conf": 0.99}]}
