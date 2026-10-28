addon := "anki_ocr_bridge"
anki_dir := if os() == "macos" { env_var("HOME") + "/Library/Application Support/Anki2" } else if os() == "windows" { env_var("APPDATA") + "/Anki2" } else { env_var("HOME") + "/.local/share/Anki2" }

default:
    @just --list

# 运行测试
test:
    python3 -m unittest discover -s tests

# 打包为 dist/anki_ocr_bridge.ankiaddon
build:
    python3 scripts/build.py

# 打包并安装到本机 Anki（复制模式，保留 user_files 中已装的引擎）。需先退出 Anki
install: test build
    #!/usr/bin/env bash
    set -euo pipefail
    dest="{{anki_dir}}/addons21/{{addon}}"
    if [ ! -d "{{anki_dir}}/addons21" ]; then echo "找不到 {{anki_dir}}/addons21，请先运行一次 Anki"; exit 1; fi
    if pgrep -x -i anki >/dev/null 2>&1; then echo "检测到 Anki 正在运行，请先退出再安装"; exit 1; fi
    if [ -L "$dest" ]; then rm "$dest"; fi
    mkdir -p "$dest"
    keep="$dest/user_files"
    find "$dest" -mindepth 1 -maxdepth 1 ! -name user_files -exec rm -rf {} +
    unzip -q -o dist/{{addon}}.ankiaddon -d "$dest"
    mkdir -p "$keep"
    echo "已安装到 $dest ，现在启动 Anki，在 工具 → OCR Bridge 设置 中使用"

# 开发模式：符号链接源码（改代码后重启 Anki 即可）
link:
    python3 scripts/dev_link.py

# 卸载本机 Anki 中的插件（连同已安装的引擎环境）
uninstall:
    rm -rf "{{anki_dir}}/addons21/{{addon}}"

# 查看插件 worker 日志
logs:
    tail -n 100 "{{anki_dir}}/addons21/{{addon}}/user_files/logs/"*.log

clean:
    rm -rf dist
