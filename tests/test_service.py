import base64
import json
import os
import socket
import struct
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from anki_ocr_bridge.core import i18n, paths  # noqa: E402
from anki_ocr_bridge.core.config import Config, ConfigStore  # noqa: E402
from anki_ocr_bridge.core.service import OcrError, Service  # noqa: E402


def png(w, h):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def call(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        finally:
            e.close()


class ServiceTest(unittest.TestCase):
    def setUp(self):
        i18n.set_language("en")
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ANKI_OCR_BRIDGE_HOME"] = self.tmp.name
        self.state = Config(port=free_port(), engine="rapidocr").to_dict()
        store = ConfigStore(lambda: self.state, lambda d: self.state.update(d))
        launcher = lambda engine, cfg: [sys.executable, str(paths.WORKER_SCRIPT), "--engine", "fake"]  # noqa: E731
        self.installed = {"rapidocr": True, "paddleocr": False}
        self.svc = Service(store, launcher, lambda e: self.installed.get(e, False))
        self.svc.start_server()
        self.url = self.svc.url

    def tearDown(self):
        self.svc.shutdown()
        self.tmp.cleanup()

    def test_health_and_engines(self):
        code, body = call(self.url + "/health")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        _, eng = call(self.url + "/engines")
        self.assertEqual({e["key"]: e["installed"] for e in eng["engines"]}, {"rapidocr": True, "paddleocr": False})

    def test_ocr_roundtrip_and_data_url(self):
        img = base64.b64encode(png(40, 20)).decode()
        code, body = call(self.url + "/ocr", {"image": "data:image/png;base64," + img})
        self.assertEqual(code, 200)
        self.assertEqual((body["width"], body["height"]), (40, 20))
        self.assertEqual(body["boxes"][0]["w"], 20)
        self.assertEqual(body["engine"], "rapidocr")
        code, _ = call(self.url + "/ocr", {"image": img})  # reuse running worker
        self.assertEqual(code, 200)

    def test_errors(self):
        self.assertEqual(call(self.url + "/ocr", {})[0], 400)
        self.assertEqual(call(self.url + "/nope")[0], 404)
        img = base64.b64encode(png(4, 4)).decode()
        code, body = call(self.url + "/ocr", {"image": img, "engine": "paddleocr"})
        self.assertEqual(code, 409)
        self.assertIn("not installed", body["error"])
        code, _ = call(self.url + "/ocr", {"image": base64.b64encode(b"junk").decode()})
        self.assertEqual(code, 500)

    def test_select_engine(self):
        self.assertEqual(call(self.url + "/engines/select", {"engine": "paddleocr"})[0], 409)
        self.installed["paddleocr"] = True
        self.assertEqual(call(self.url + "/engines/select", {"engine": "paddleocr"})[0], 200)
        self.assertEqual(self.state["engine"], "paddleocr")

    def test_chinese_errors(self):
        i18n.set_language("zh")
        code, body = call(self.url + "/ocr", {})
        self.assertEqual(code, 400)
        self.assertIn("缺少", body["error"])

    def test_port_in_use(self):
        svc2 = Service(ConfigStore(lambda: self.state, lambda d: None))
        with self.assertRaises(OcrError):
            svc2.start_server()


class ConfigTest(unittest.TestCase):
    def test_sanitize(self):
        c = Config.from_dict({"port": 99999, "mirror": "x", "idle_timeout_minutes": -3, "host": "0.0.0.0"})
        self.assertEqual((c.port, c.mirror, c.idle_timeout_minutes), (8866, "pypi", 0))
        self.assertFalse(c.is_loopback)


if __name__ == "__main__":
    unittest.main()
