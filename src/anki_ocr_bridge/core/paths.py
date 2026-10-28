from __future__ import annotations

import os
import sys
from pathlib import Path

ADDON_DIR = Path(__file__).resolve().parent.parent
WORKER_SCRIPT = ADDON_DIR / "worker" / "worker_main.py"


def user_files() -> Path:
    # Anki preserves user_files/ across add-on upgrades.
    override = os.environ.get("ANKI_OCR_BRIDGE_HOME")
    p = Path(override) if override else ADDON_DIR / "user_files"
    p.mkdir(parents=True, exist_ok=True)
    return p


def env_dir(engine: str) -> Path:
    return user_files() / "envs" / engine


def venv_python(engine: str) -> Path:
    base = env_dir(engine)
    return base / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def ready_marker(engine: str) -> Path:
    return env_dir(engine) / "ready.json"
