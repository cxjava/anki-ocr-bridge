from __future__ import annotations

from .common import load_image, quad_to_box


def selfcheck() -> None:
    import rapidocr_onnxruntime, PIL, numpy  # noqa: F401


class Engine:
    def __init__(self, options: dict):
        from rapidocr_onnxruntime import RapidOCR

        self._ocr = RapidOCR()

    def ocr(self, data: bytes) -> dict:
        arr, w, h = load_image(data)
        result, _ = self._ocr(arr)
        boxes = [quad_to_box(it[0], it[1], it[2]) for it in (result or [])]
        return {"width": w, "height": h, "boxes": boxes}
