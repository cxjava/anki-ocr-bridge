from __future__ import annotations

import os

from .common import load_image, quad_to_box

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def selfcheck() -> None:
    import paddle, paddleocr, PIL, numpy  # noqa: F401


class Engine:
    def __init__(self, options: dict):
        from paddleocr import PaddleOCR

        lang = options.get("lang") or "ch"
        self._v3 = hasattr(PaddleOCR, "predict")
        if self._v3:
            self._ocr = PaddleOCR(lang=lang, use_doc_orientation_classify=False,
                                  use_doc_unwarping=False, use_textline_orientation=False)
        else:
            self._ocr = PaddleOCR(lang=lang, use_angle_cls=False, show_log=False)

    def ocr(self, data: bytes) -> dict:
        arr, w, h = load_image(data)
        boxes: list[dict] = []
        if self._v3:
            for res in self._ocr.predict(arr):
                d = res.get("res", res) if hasattr(res, "get") else res
                polys = d.get("rec_polys")
                if polys is None:
                    polys = d.get("dt_polys")
                texts, scores = d.get("rec_texts"), d.get("rec_scores")
                if polys is None or texts is None:
                    continue
                for poly, text, score in zip(polys, texts, scores):
                    boxes.append(quad_to_box(poly, text, score))
        else:
            for page in self._ocr.ocr(arr, cls=False) or []:
                for item in page or []:
                    boxes.append(quad_to_box(item[0], item[1][0], item[1][1]))
        return {"width": w, "height": h, "boxes": boxes}
