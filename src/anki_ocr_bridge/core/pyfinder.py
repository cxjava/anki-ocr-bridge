"""Find a usable system Python (never the interpreter embedded in Anki)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .proc import popen_kwargs

_PROBE = "import sys, venv, ensurepip; print('%d.%d.%d' % sys.version_info[:3])"


@dataclass(frozen=True)
class PythonInfo:
    path: str
    major: int
    minor: int
    micro: int

    @property
    def version(self) -> str:
        return f"{self.major}.{self.minor}.{self.micro}"


def _candidates(minor: int) -> Iterable[str]:
    name = f"python3.{minor}"
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        for root in (os.path.join(local, "Programs", "Python"), pf):
            yield os.path.join(root, f"Python3{minor}", "python.exe")
        py = shutil.which("py")
        if py:
            try:
                out = subprocess.run([py, f"-3.{minor}", "-c", "import sys;print(sys.executable)"],
                                     capture_output=True, text=True, timeout=15, **popen_kwargs())
                if out.returncode == 0 and out.stdout.strip():
                    yield out.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                pass
        w = shutil.which(name) or shutil.which("python")
        if w:
            yield w
    else:
        w = shutil.which(name)
        if w:
            yield w
        for d in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin",
                  str(Path.home() / ".pyenv" / "shims"), str(Path.home() / ".local" / "bin")):
            yield os.path.join(d, name)
        for fw in (f"/Library/Frameworks/Python.framework/Versions/3.{minor}/bin/{name}",):
            yield fw


def probe(path: str) -> Optional[PythonInfo]:
    if not path or not os.path.isfile(path):
        return None
    try:
        out = subprocess.run([path, "-c", _PROBE], capture_output=True, text=True, timeout=20, **popen_kwargs())
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        major, minor, micro = (int(x) for x in out.stdout.strip().split("."))
    except ValueError:
        return None
    return PythonInfo(path, major, minor, micro)


def find_python(minors: Iterable[int]) -> Optional[PythonInfo]:
    """Return the first working Python whose minor version is in `minors` (by preference)."""
    for minor in minors:
        seen: set[str] = set()
        for cand in _candidates(minor):
            if cand in seen:
                continue
            seen.add(cand)
            info = probe(cand)
            if info and info.major == 3 and info.minor == minor:
                return info
    return None
