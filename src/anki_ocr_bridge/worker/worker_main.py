"""OCR worker. Runs inside an engine's venv, talks JSON lines over stdin/stdout.

Protocol (one JSON object per line):
  worker -> {"event": "ready"} | {"event": "error", "error": "..."}   (after startup)
  client -> {"id": N, "op": "ocr", "image": "<base64>"}
  worker -> {"id": N, "ok": true, "result": {...}} | {"id": N, "ok": false, "error": "..."}
  client -> {"op": "shutdown"}
Anything libraries print to stdout is redirected to stderr so it cannot corrupt the protocol.
"""
from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_engine(name: str, options: dict):
    mod = importlib.import_module(f"engines.{name}")
    return mod.Engine(options)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--options", default="{}")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()

    proto = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr

    def send(obj: dict) -> None:
        proto.write(json.dumps(obj, ensure_ascii=False) + "\n")
        proto.flush()

    options = json.loads(args.options)
    try:
        if args.selfcheck:
            # Import-only check: model downloads (PaddleOCR) happen on first real start.
            importlib.import_module(f"engines.{args.engine}").selfcheck()
            print("selfcheck ok")
            return 0
        engine = load_engine(args.engine, options)
    except BaseException as exc:  # noqa: BLE001
        traceback.print_exc()
        if args.selfcheck:
            return 1
        send({"event": "error", "error": f"{type(exc).__name__}: {exc}"})
        return 1
    send({"event": "ready"})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        op = req.get("op")
        if op == "shutdown":
            return 0
        rid = req.get("id")
        if op == "ping":
            send({"id": rid, "ok": True, "result": "pong"})
        elif op == "ocr":
            try:
                result = engine.ocr(base64.b64decode(req["image"]))
                send({"id": rid, "ok": True, "result": result})
            except BaseException as exc:  # noqa: BLE001
                traceback.print_exc()
                send({"id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
