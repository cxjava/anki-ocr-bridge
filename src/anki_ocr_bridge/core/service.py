"""Ties config, worker lifecycle and the REST server together. No Anki imports."""
from __future__ import annotations

import json
import threading
import time
from typing import Callable, Optional

from . import envmgr, paths
from .config import Config, ConfigStore
from .engines import ENGINES
from .i18n import t
from .server import RestServer
from .worker_client import WorkerClient, WorkerDied, WorkerError, WorkerTimeout

Launcher = Callable[[str, Config], list[str]]


class OcrError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def default_launcher(engine: str, cfg: Config) -> list[str]:
    options = {"lang": cfg.paddleocr_lang} if engine == "paddleocr" else {}
    return [str(paths.venv_python(engine)), str(paths.WORKER_SCRIPT), "--engine", engine,
            "--options", json.dumps(options)]


class Service:
    def __init__(self, store: ConfigStore, launcher: Launcher = default_launcher,
                 installed: Callable[[str], bool] = envmgr.is_installed):
        self.store = store
        self._launcher = launcher
        self._installed = installed
        self._client: Optional[WorkerClient] = None
        self._client_key: Optional[list[str]] = None
        self._last_used = 0.0
        self._lock = threading.Lock()
        self._ocr_serial = threading.Lock()
        self._server: Optional[RestServer] = None
        self._stop_reaper = threading.Event()
        self._reaper: Optional[threading.Thread] = None

    # ---- config ----
    @property
    def cfg(self) -> Config:
        return self.store.get()

    # ---- server ----
    @property
    def server_running(self) -> bool:
        return self._server is not None

    @property
    def url(self) -> str:
        c = self.cfg
        return f"http://{c.host}:{c.port}"

    def start_server(self) -> None:
        if self._server:
            return
        c = self.cfg
        try:
            srv = RestServer(c.host, c.port, self)
            srv.start()
        except OSError as exc:
            raise OcrError(500, t("err_port_in_use", port=c.port)) from exc
        self._server = srv
        self._stop_reaper.clear()
        self._reaper = threading.Thread(target=self._reap_loop, daemon=True)
        self._reaper.start()

    def stop_server(self) -> None:
        srv, self._server = self._server, None
        if srv:
            srv.stop()
        self._stop_reaper.set()
        self.stop_worker()

    def shutdown(self) -> None:
        self.stop_server()

    # ---- worker ----
    def stop_worker(self) -> None:
        with self._lock:
            client, self._client, self._client_key = self._client, None, None
        if client:
            client.stop()

    def _reap_loop(self) -> None:
        while not self._stop_reaper.wait(15):
            minutes = self.cfg.idle_timeout_minutes
            if minutes and self._client and time.time() - self._last_used > minutes * 60:
                self.stop_worker()

    def _ensure_client(self, engine: str) -> WorkerClient:
        if engine not in ENGINES and engine != "fake":
            raise OcrError(400, t("err_unknown_engine", engine=engine))
        if not self._installed(engine):
            raise OcrError(409, t("err_not_installed", engine=ENGINES[engine].display if engine in ENGINES else engine))
        cmd = self._launcher(engine, self.cfg)
        with self._lock:
            if self._client and self._client.alive and self._client_key == cmd:
                return self._client
            old, self._client = self._client, None
        if old:
            old.stop()
        client = WorkerClient(cmd, paths.user_files() / "logs" / f"worker-{engine}.log")
        try:
            client.start()
        except WorkerError as exc:
            raise OcrError(500, t("err_worker_start", err=exc)) from exc
        with self._lock:
            self._client, self._client_key = client, cmd
        return client

    # ---- operations ----
    def ocr(self, image_b64: str, engine: Optional[str] = None) -> dict:
        engine = engine or self.cfg.engine
        started = time.time()
        with self._ocr_serial:
            client = self._ensure_client(engine)
            try:
                result = client.call({"op": "ocr", "image": image_b64})
            except WorkerTimeout as exc:
                self.stop_worker()
                raise OcrError(504, t("err_timeout")) from exc
            except WorkerDied as exc:
                self.stop_worker()
                raise OcrError(500, t("err_worker_died")) from exc
            except WorkerError as exc:
                raise OcrError(500, t("err_ocr", err=exc)) from exc
            finally:
                self._last_used = time.time()
        result["engine"] = engine
        result["elapsed_ms"] = int((time.time() - started) * 1000)
        return result

    def engines(self) -> list[dict]:
        cur = self.cfg.engine
        return [{"key": e.key, "display": e.display, "installed": self._installed(e.key),
                 "current": e.key == cur, "size": e.size_hint} for e in ENGINES.values()]

    def select_engine(self, engine: str) -> None:
        if engine not in ENGINES:
            raise OcrError(400, t("err_unknown_engine", engine=engine))
        if not self._installed(engine):
            raise OcrError(409, t("err_not_installed", engine=ENGINES[engine].display))
        c = self.cfg
        c.engine = engine
        self.store.put(c)
        self.stop_worker()

    def health(self) -> dict:
        c = self.cfg
        return {"ok": True, "engine": c.engine, "installed": self._installed(c.engine),
                "running": bool(self._client and self._client.alive), "version": 1}
