# OCR Bridge

Most options are edited in **Tools → OCR Bridge**. / 大部分选项在 **工具 → OCR Bridge** 中修改。

- `host` / `port`: REST listen address. Use `127.0.0.1` unless you know what you are doing. / 监听地址，非必要请保持 `127.0.0.1`。
- `auto_start`: start the REST service with Anki. / 随 Anki 启动服务。
- `engine`: `rapidocr` or `paddleocr`.
- `language`: `auto`, `zh` or `en`. / 界面语言。
- `mirror`: `pypi`, `tsinghua` or `aliyun` (pip index used when installing engines). / 安装引擎时使用的 pip 镜像。
- `idle_timeout_minutes`: stop the OCR worker after this many idle minutes, `0` = never. / 空闲多少分钟后释放 OCR 进程，0 为不释放。
- `paddleocr_lang`: PaddleOCR language code, e.g. `ch`, `en`, `chinese_cht`, `japan`. / PaddleOCR 语言代码。

Engines, virtual environments and logs live in `user_files/`, which Anki keeps across add-on upgrades.
