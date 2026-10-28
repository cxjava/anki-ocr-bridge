"""Shared helpers for engine adapters. Runs inside the engine venv (not inside Anki)."""
from __future__ import annotations

import io


def load_image(data: bytes):
    """Return (numpy RGB array, width, height)."""
    import numpy as np
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    return np.array(img.convert("RGB")), w, h


def quad_to_box(points, text, conf) -> dict:
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    return {"x": round(x0), "y": round(y0), "w": round(x1 - x0), "h": round(y1 - y0),
            "text": str(text), "conf": round(float(conf), 4)}
