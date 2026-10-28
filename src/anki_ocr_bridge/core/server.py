"""REST server (stdlib http.server). Endpoints: /health /ocr /engines /engines/select."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

from .i18n import t

if TYPE_CHECKING:
    from .service import Service

MAX_BODY = 50 * 1024 * 1024


def make_handler(service: "Service"):
    from .service import OcrError

    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def _json(self, code: int, obj) -> None:
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                raise OcrError(413, t("err_too_large"))
            try:
                data = json.loads(self.rfile.read(length))
            except ValueError as exc:
                raise OcrError(400, t("err_bad_request")) from exc
            if not isinstance(data, dict):
                raise OcrError(400, t("err_bad_request"))
            return data

        def _dispatch(self, fn) -> None:
            try:
                self._json(200, fn())
            except OcrError as exc:
                self._json(exc.status, {"error": exc.message})
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"error": t("err_ocr", err=exc)})

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._dispatch(service.health)
            elif self.path == "/engines":
                self._dispatch(lambda: {"engines": service.engines()})
            else:
                self._json(404, {"error": t("err_not_found")})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/ocr":
                def run():
                    body = self._body()
                    img = body.get("image")
                    if not isinstance(img, str) or not img:
                        raise OcrError(400, t("err_no_image"))
                    if img.startswith("data:") and "," in img[:200]:
                        img = img.split(",", 1)[1]
                    return service.ocr(img, body.get("engine"))
                self._dispatch(run)
            elif self.path == "/engines/select":
                def sel():
                    service.select_engine(str(self._body().get("engine", "")))
                    return {"ok": True, "engines": service.engines()}
                self._dispatch(sel)
            else:
                self._json(404, {"error": t("err_not_found")})

        def log_message(self, fmt, *args) -> None:  # silence default stderr logging
            pass

    return Handler


class RestServer:
    def __init__(self, host: str, port: int, service: "Service"):
        self._httpd = ThreadingHTTPServer((host, port), make_handler(service))
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
