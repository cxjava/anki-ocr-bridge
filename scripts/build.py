#!/usr/bin/env python3
"""Package src/anki_ocr_bridge into dist/anki_ocr_bridge.ankiaddon (no top-level folder, no __pycache__)."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "anki_ocr_bridge"
OUT = ROOT / "dist" / "anki_ocr_bridge.ankiaddon"
SKIP_DIRS = {"__pycache__", "user_files"}


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SRC.rglob("*")):
            rel = p.relative_to(SRC)
            if p.is_dir() or SKIP_DIRS & set(rel.parts) or p.suffix == ".pyc":
                continue
            z.write(p, rel.as_posix())
    print("built", OUT)


if __name__ == "__main__":
    main()
