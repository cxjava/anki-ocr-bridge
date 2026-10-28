#!/usr/bin/env python3
"""Symlink src/anki_ocr_bridge into Anki's addons21 folder for development (macOS / Linux)."""
import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "anki_ocr_bridge"
base = {"darwin": Path.home() / "Library/Application Support/Anki2",
        "linux": Path.home() / ".local/share/Anki2"}.get(sys.platform)
if base is None:
    sys.exit("Windows: use `mklink /D %APPDATA%\\Anki2\\addons21\\anki_ocr_bridge <repo>\\src\\anki_ocr_bridge` in an admin shell")
dst = base / "addons21" / "anki_ocr_bridge"
if dst.is_symlink() or dst.exists():
    sys.exit(f"{dst} already exists")
os.symlink(SRC, dst)
print("linked", dst, "->", SRC)
