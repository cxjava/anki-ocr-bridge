from __future__ import annotations

import subprocess
import sys
from typing import Any


def popen_kwargs() -> dict[str, Any]:
    """Hide console windows on Windows."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}
