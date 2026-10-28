# anki-ocr-bridge

**English** | [简体中文](README.md)

Anki add-on (Anki 26.08+) that exposes a local **OCR REST service** for card templates, e.g. the image-occlusion
"auto detect text" button of DeckMasterPro. Engines run in their own virtual environments as subprocesses, so they
never touch Anki's bundled Python.

* Engines: **RapidOCR** (PP-OCR ONNX models, default) and **PaddleOCR**
* Install / uninstall / switch engines from **Tools → OCR Bridge Settings** (pip mirror selectable)
* Configurable listen address and port (default `127.0.0.1:8866`, no authentication)
* UI languages: 中文 / English
* Requires a system **Python 3.10-3.13** (3.12 preferred; 3.14 is not used). Windows: install from python.org first.

## REST API

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{ok, engine, installed, running, version}` |
| GET | `/engines` | engine list with install state |
| POST | `/engines/select` | `{"engine": "rapidocr"}` |
| POST | `/ocr` | `{"image": "<base64 or data URL>", "engine"?: "..."}` → `{width, height, boxes:[{x,y,w,h,text,conf}], engine, elapsed_ms}` |

Coordinates are pixels of the original image. Errors return `{"error": "..."}` in the UI language.

## Layout

```
src/anki_ocr_bridge/        add-on package (zipped as-is, no top-level folder)
  __init__.py               Anki entry (menu, auto start); import-safe outside Anki
  manifest.json config.json config.md
  core/                     pure stdlib: config, i18n, REST server, service, venv manager, worker client
  ui/settings.py            Qt6 settings dialog
  worker/                   runs INSIDE the engine venv: worker_main.py + engines/
  user_files/               venvs, logs (kept by Anki across upgrades; git-ignored)
scripts/build.py            -> dist/anki_ocr_bridge.ankiaddon
scripts/dev_link.py         symlink into addons21 for development
tests/                      python -m unittest discover -s tests
```

## Develop

```bash
python3 scripts/dev_link.py   # then restart Anki
python3 -m unittest discover -s tests
python3 scripts/build.py
```

Or with [just](https://github.com/casey/just): `just install` (test, build and install into your local Anki; quit Anki first), `just link` (symlink for development), `just --list` for all recipes.
