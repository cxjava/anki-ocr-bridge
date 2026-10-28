"""Manages one OCR worker subprocess and the JSON-line protocol."""
from __future__ import annotations

import json
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any, Optional

from .proc import popen_kwargs


class WorkerError(Exception):
    pass


class WorkerDied(WorkerError):
    pass


class WorkerTimeout(WorkerError):
    pass


class WorkerClient:
    def __init__(self, cmd: list[str], log_path: Optional[Path] = None):
        self.cmd = cmd
        self._log_path = log_path
        self._proc: Optional[subprocess.Popen] = None
        self._q: "queue.Queue[Optional[dict]]" = queue.Queue()
        self._lock = threading.Lock()
        self._next_id = 0
        self._log_fh = None

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, startup_timeout: float = 600) -> None:
        stderr: Any = subprocess.DEVNULL
        if self._log_path:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            if self._log_path.exists() and self._log_path.stat().st_size > 1_000_000:
                self._log_path.unlink()
            self._log_fh = open(self._log_path, "ab")
            stderr = self._log_fh
        self._proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                                      **popen_kwargs())
        threading.Thread(target=self._read_loop, args=(self._proc,), daemon=True).start()
        try:
            msg = self._q.get(timeout=startup_timeout)
        except queue.Empty:
            self.stop()
            raise WorkerTimeout("startup timeout") from None
        if msg is None:
            raise WorkerDied("worker exited during startup")
        if msg.get("event") != "ready":
            self.stop()
            raise WorkerError(msg.get("error") or "worker failed to start")

    def _read_loop(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            try:
                self._q.put(json.loads(raw.decode("utf-8")))
            except ValueError:
                continue
        self._q.put(None)

    def call(self, payload: dict, timeout: float = 120) -> Any:
        with self._lock:
            if not self.alive:
                raise WorkerDied("worker not running")
            self._next_id += 1
            rid = self._next_id
            assert self._proc is not None and self._proc.stdin is not None
            try:
                self._proc.stdin.write((json.dumps({"id": rid, **payload}) + "\n").encode("utf-8"))
                self._proc.stdin.flush()
            except OSError as exc:
                raise WorkerDied(str(exc)) from exc
            while True:
                try:
                    msg = self._q.get(timeout=timeout)
                except queue.Empty:
                    self.stop()
                    raise WorkerTimeout("timeout") from None
                if msg is None:
                    raise WorkerDied("worker exited")
                if msg.get("id") != rid:
                    continue
                if not msg.get("ok"):
                    raise WorkerError(msg.get("error") or "unknown error")
                return msg.get("result")

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.poll() is None and proc.stdin:
                try:
                    proc.stdin.write(b'{"op":"shutdown"}\n')
                    proc.stdin.flush()
                except OSError:
                    pass
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        finally:
            for fh in (proc.stdin, proc.stdout, self._log_fh):
                try:
                    if fh:
                        fh.close()
                except OSError:
                    pass
            self._log_fh = None
