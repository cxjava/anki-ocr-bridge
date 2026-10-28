"""Settings dialog (Tools -> OCR Bridge). Qt6 / Anki 26.08+."""
from __future__ import annotations

import threading
from typing import Optional

from aqt.qt import (QAbstractItemView, QCheckBox, QColor, QComboBox, QDialog, QFileDialog, QFormLayout,
                    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QObject, QPainter, QPen,
                    QPixmap, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, Qt, QTableWidget,
                    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, pyqtSignal)

from ..core import envmgr
from ..core.config import MIRRORS
from ..core.engines import ENGINES, python_need
from ..core.i18n import apply_config_language, t
from ..core.pyfinder import find_python
from ..core.service import OcrError, Service


class _Bridge(QObject):
    log = pyqtSignal(str)
    install_done = pyqtSignal(str, str)      # engine, error ("" = ok, "cancelled" handled by text)
    python_info = pyqtSignal(str, str)       # engine, text
    ocr_done = pyqtSignal(object, str, str)  # result, error, image path


class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], service: Service, system_lang: str):
        super().__init__(parent)
        self.service = service
        self.system_lang = system_lang
        self._cancel: Optional[threading.Event] = None
        self._bridge = _Bridge()
        self._bridge.log.connect(self._append_log)
        self._bridge.install_done.connect(self._on_install_done)
        self._bridge.python_info.connect(self._on_python_info)
        self._bridge.ocr_done.connect(self._on_ocr_done)
        self._py_text: dict[str, str] = {}
        self.setWindowTitle(t("title"))
        self.resize(680, 560)

        tabs = QTabWidget()
        tabs.addTab(self._build_service_tab(), t("tab_service"))
        tabs.addTab(self._build_engines_tab(), t("tab_engines"))
        tabs.addTab(self._build_test_tab(), t("tab_test"))
        close = QPushButton(t("close"))
        close.clicked.connect(self.close)
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)

        self._refresh_service()
        self._refresh_engines()
        threading.Thread(target=self._detect_python, daemon=True).start()

    # ------------------------------------------------------------ service tab
    def _build_service_tab(self) -> QWidget:
        c = self.service.cfg
        w = QWidget()
        form = QFormLayout(w)
        self.host = QLineEdit(c.host)
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(c.port)
        self.auto_start = QCheckBox(t("auto_start"))
        self.auto_start.setChecked(c.auto_start)
        self.idle = QSpinBox()
        self.idle.setRange(0, 1440)
        self.idle.setValue(c.idle_timeout_minutes)
        self.language = QComboBox()
        for code, label in (("auto", t("lang_auto")), ("zh", "中文"), ("en", "English")):
            self.language.addItem(label, code)
        self.language.setCurrentIndex(max(0, self.language.findData(c.language)))
        form.addRow(t("host"), self.host)
        form.addRow(t("port"), self.port)
        form.addRow("", self.auto_start)
        form.addRow(t("idle_timeout"), self.idle)
        form.addRow(t("language"), self.language)
        self.status = QLabel()
        form.addRow(self.status)
        btns = QHBoxLayout()
        save = QPushButton(t("save"))
        save.clicked.connect(self._save)
        self.toggle_btn = QPushButton()
        self.toggle_btn.clicked.connect(self._toggle_server)
        btns.addWidget(save)
        btns.addWidget(self.toggle_btn)
        btns.addStretch(1)
        form.addRow(btns)
        return w

    def _save(self) -> bool:
        c = self.service.cfg
        host = self.host.text().strip() or "127.0.0.1"
        if host not in ("127.0.0.1", "localhost", "::1") and host != c.host:
            if QMessageBox.question(self, t("title"), t("non_loopback_warn", host=host)) != QMessageBox.StandardButton.Yes:
                return False
        changed_addr = (host, self.port.value()) != (c.host, c.port)
        c.host, c.port = host, self.port.value()
        c.auto_start = self.auto_start.isChecked()
        c.idle_timeout_minutes = self.idle.value()
        c.language = self.language.currentData()
        self.service.store.put(c)
        apply_config_language(c.language, self.system_lang)
        if changed_addr and self.service.server_running:
            self.service.stop_server()
            return self._start()
        self._refresh_service()
        self.status.setText(self.status.text() + "  ✓ " + t("saved"))
        return True

    def _start(self) -> bool:
        try:
            self.service.start_server()
        except OcrError as exc:
            QMessageBox.warning(self, t("title"), exc.message)
            self._refresh_service()
            return False
        self._refresh_service()
        return True

    def _toggle_server(self) -> None:
        if self.service.server_running:
            self.service.stop_server()
            self._refresh_service()
        elif self._save():
            self._start()

    def _refresh_service(self) -> None:
        running = self.service.server_running
        self.status.setText(t("status_running", url=self.service.url) if running else t("status_stopped"))
        self.toggle_btn.setText(t("stop") if running else t("start"))

    # ------------------------------------------------------------ engines tab
    def _build_engines_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.table = QTableWidget(len(ENGINES), 4)
        self.table.setHorizontalHeaderLabels([t("engine_col"), t("status_col"), t("size_col"), t("current_col")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._update_engine_buttons)
        lay.addWidget(self.table)
        self.engine_desc = QLabel()
        self.engine_desc.setWordWrap(True)
        lay.addWidget(self.engine_desc)

        mrow = QHBoxLayout()
        mrow.addWidget(QLabel(t("mirror")))
        self.mirror = QComboBox()
        labels = {"pypi": t("mirror_pypi"), "tsinghua": t("mirror_tsinghua"), "aliyun": t("mirror_aliyun")}
        for key in MIRRORS:
            self.mirror.addItem(labels[key], key)
        self.mirror.setCurrentIndex(max(0, self.mirror.findData(self.service.cfg.mirror)))
        self.mirror.currentIndexChanged.connect(self._mirror_changed)
        mrow.addWidget(self.mirror)
        mrow.addStretch(1)
        lay.addLayout(mrow)

        brow = QHBoxLayout()
        self.btn_install = QPushButton(t("install"))
        self.btn_uninstall = QPushButton(t("uninstall"))
        self.btn_current = QPushButton(t("set_current"))
        self.btn_cancel = QPushButton(t("cancel"))
        self.btn_install.clicked.connect(self._install)
        self.btn_uninstall.clicked.connect(self._uninstall)
        self.btn_current.clicked.connect(self._set_current)
        self.btn_cancel.clicked.connect(lambda: self._cancel and self._cancel.set())
        for b in (self.btn_install, self.btn_uninstall, self.btn_current, self.btn_cancel):
            brow.addWidget(b)
        brow.addStretch(1)
        lay.addLayout(brow)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        lay.addWidget(self.progress)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        lay.addWidget(self.log_view, 1)
        return w

    def _selected_engine(self) -> Optional[str]:
        rows = self.table.selectionModel().selectedRows()
        return list(ENGINES)[rows[0].row()] if rows else None

    def _refresh_engines(self) -> None:
        cur = self.service.cfg.engine
        keep = self._selected_engine()
        for row, (key, info) in enumerate(ENGINES.items()):
            vals = [info.display, t("installed") if envmgr.is_installed(key) else t("not_installed"),
                    info.size_hint, "●" if key == cur else ""]
            for col, v in enumerate(vals):
                self.table.setItem(row, col, QTableWidgetItem(v))
        if keep:
            self.table.selectRow(list(ENGINES).index(keep))
        self._update_engine_buttons()

    def _update_engine_buttons(self) -> None:
        key = self._selected_engine()
        busy = self._cancel is not None
        inst = bool(key) and envmgr.is_installed(key)
        self.btn_install.setEnabled(bool(key) and not busy)
        self.btn_install.setText(t("install") if not inst else t("install") + " (↻)")
        self.btn_uninstall.setEnabled(inst and not busy)
        self.btn_current.setEnabled(inst and not busy and key != self.service.cfg.engine)
        self.btn_cancel.setVisible(busy)
        self.progress.setVisible(busy)
        if key:
            info = ENGINES[key]
            from ..core.i18n import get_language
            desc = info.description_zh if get_language() == "zh" else info.description_en
            self.engine_desc.setText(desc + "\n" + self._py_text.get(key, ""))
        else:
            self.engine_desc.setText("")

    def _detect_python(self) -> None:
        for key, info in ENGINES.items():
            py = find_python(info.python_minors)
            text = (t("python_found", path=py.path, version=py.version) if py
                    else t("python_missing", need=python_need(info)))
            self._bridge.python_info.emit(key, text)

    def _on_python_info(self, engine: str, text: str) -> None:
        self._py_text[engine] = text
        self._update_engine_buttons()

    def _mirror_changed(self) -> None:
        c = self.service.cfg
        c.mirror = self.mirror.currentData()
        self.service.store.put(c)

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def _install(self) -> None:
        key = self._selected_engine()
        if not key or self._cancel is not None:
            return
        self.service.stop_worker()
        self._cancel = threading.Event()
        cancel, mirror = self._cancel, self.service.cfg.mirror
        self.log_view.clear()
        self._update_engine_buttons()

        def run() -> None:
            err = ""
            try:
                envmgr.install(key, mirror, self._bridge.log.emit, cancel)
            except envmgr.Cancelled:
                err = "cancelled"
            except envmgr.PythonNotFound as exc:
                err = t("python_missing", need=exc.need)
            except Exception as exc:  # noqa: BLE001
                err = str(exc) or type(exc).__name__
            self._bridge.install_done.emit(key, err)

        threading.Thread(target=run, daemon=True).start()

    def _on_install_done(self, engine: str, err: str) -> None:
        self._cancel = None
        name = ENGINES[engine].display
        if not err:
            self._append_log(t("install_done", engine=name))
            if not envmgr.is_installed(self.service.cfg.engine):
                c = self.service.cfg
                c.engine = engine
                self.service.store.put(c)
        elif err == "cancelled":
            self._append_log(t("install_cancelled"))
        else:
            self._append_log(t("install_failed", engine=name, err=err))
            QMessageBox.warning(self, t("title"), t("install_failed", engine=name, err=err))
        self._refresh_engines()

    def _uninstall(self) -> None:
        key = self._selected_engine()
        if not key:
            return
        if QMessageBox.question(self, t("title"), t("confirm_uninstall", engine=ENGINES[key].display)) \
                != QMessageBox.StandardButton.Yes:
            return
        self.service.stop_worker()
        envmgr.uninstall(key)
        self._refresh_engines()

    def _set_current(self) -> None:
        key = self._selected_engine()
        if not key:
            return
        try:
            self.service.select_engine(key)
        except OcrError as exc:
            QMessageBox.warning(self, t("title"), exc.message)
        self._refresh_engines()

    # --------------------------------------------------------------- test tab
    def _build_test_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.test_btn = QPushButton(t("choose_image"))
        self.test_btn.clicked.connect(self._choose_image)
        self.test_label = QLabel()
        self.test_label.setWordWrap(True)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(260)
        lay.addWidget(self.test_btn)
        lay.addWidget(self.test_label)
        lay.addWidget(self.preview, 1)
        return w

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("choose_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not path:
            return
        self.test_btn.setEnabled(False)
        self.test_label.setText("…")

        def run() -> None:
            import base64
            try:
                with open(path, "rb") as fh:
                    res = self.service.ocr(base64.b64encode(fh.read()).decode())
                self._bridge.ocr_done.emit(res, "", path)
            except OcrError as exc:
                self._bridge.ocr_done.emit(None, exc.message, path)
            except Exception as exc:  # noqa: BLE001
                self._bridge.ocr_done.emit(None, str(exc), path)

        threading.Thread(target=run, daemon=True).start()

    def _on_ocr_done(self, res, err: str, path: str) -> None:
        self.test_btn.setEnabled(True)
        if err or not res:
            self.test_label.setText(t("test_failed", err=err))
            return
        self.test_label.setText(t("test_result", n=len(res["boxes"]), ms=res["elapsed_ms"], engine=res["engine"]))
        pix = QPixmap(path)
        painter = QPainter(pix)
        painter.setPen(QPen(QColor(220, 38, 38), max(2, pix.width() // 400)))
        for b in res["boxes"]:
            painter.drawRect(b["x"], b["y"], b["w"], b["h"])
        painter.end()
        self.preview.setPixmap(pix.scaled(self.preview.width(), self.preview.height(),
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
