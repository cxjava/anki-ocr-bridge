"""Per-engine virtual environment management (create / install / uninstall)."""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from typing import Callable, Optional

from . import paths
from .config import MIRRORS
from .engines import ENGINES, python_need
from .proc import popen_kwargs
from .pyfinder import PythonInfo, find_python

LogFn = Callable[[str], None]


class InstallError(Exception):
    pass


class PythonNotFound(InstallError):
    def __init__(self, need: str):
        super().__init__(need)
        self.need = need


class Cancelled(InstallError):
    pass


def is_installed(engine: str) -> bool:
    return paths.ready_marker(engine).is_file() and paths.venv_python(engine).is_file()


def installed_info(engine: str) -> dict:
    try:
        return json.loads(paths.ready_marker(engine).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _run(cmd: list[str], log: LogFn, cancel: Optional[threading.Event]) -> None:
    log("$ " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", **popen_kwargs())
    assert proc.stdout is not None
    for line in proc.stdout:
        log(line.rstrip())
        if cancel is not None and cancel.is_set():
            proc.terminate()
            proc.wait()
            raise Cancelled()
    if proc.wait() != 0:
        raise InstallError(f"exit code {proc.returncode}: {' '.join(cmd[:4])}")


def install(engine: str, mirror: str, log: LogFn, cancel: Optional[threading.Event] = None,
            python: Optional[PythonInfo] = None) -> None:
    info = ENGINES[engine]
    py = python or find_python(info.python_minors)
    if py is None:
        raise PythonNotFound(python_need(info))
    log(f"Python: {py.path} ({py.version})")
    env = paths.env_dir(engine)
    shutil.rmtree(env, ignore_errors=True)
    try:
        _run([py.path, "-m", "venv", str(env)], log, cancel)
        vpy = str(paths.venv_python(engine))
        index = MIRRORS.get(mirror, "")
        pip = [vpy, "-m", "pip", "install", "--disable-pip-version-check"]
        if index:
            pip += ["-i", index]
        _run(pip + ["--upgrade", "pip"], log, cancel)
        _run(pip + list(info.packages), log, cancel)
        _run([vpy, str(paths.WORKER_SCRIPT), "--engine", engine, "--selfcheck"], log, cancel)
        paths.ready_marker(engine).write_text(json.dumps({
            "python": py.version, "python_path": py.path,
            "packages": list(info.packages), "installed_at": int(time.time()),
        }), encoding="utf-8")
    except BaseException:
        shutil.rmtree(env, ignore_errors=True)
        raise


def uninstall(engine: str) -> None:
    shutil.rmtree(paths.env_dir(engine), ignore_errors=True)
