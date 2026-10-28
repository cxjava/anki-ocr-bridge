"""OCR Bridge - local OCR REST service for Anki card templates (Anki 26.08+)."""
from __future__ import annotations

try:  # Allow importing the package's core outside Anki (unit tests, tooling).
    from aqt import gui_hooks, mw
    from aqt.qt import QAction, QApplication
    from aqt.utils import showWarning
except ImportError:  # pragma: no cover
    mw = None

if mw is not None:
    import anki.lang

    from .core.config import ConfigStore
    from .core.i18n import apply_config_language, t
    from .core.service import OcrError, Service

    _pkg = __name__.split(".")[0]

    def _system_lang() -> str:
        return str(getattr(anki.lang, "current_lang", "") or "en")

    _store = ConfigStore(lambda: mw.addonManager.getConfig(_pkg),
                         lambda d: mw.addonManager.writeConfig(_pkg, d))
    service = Service(_store)

    def _apply_lang() -> None:
        apply_config_language(service.cfg.language, _system_lang())

    def _open_settings() -> None:
        from .ui.settings import SettingsDialog

        _apply_lang()
        SettingsDialog(mw, service, _system_lang()).exec()

    def _setup() -> None:
        _apply_lang()
        action = QAction(t("menu"), mw)
        action.triggered.connect(_open_settings)
        mw.form.menuTools.addAction(action)
        QApplication.instance().aboutToQuit.connect(service.shutdown)
        if service.cfg.auto_start:
            try:
                service.start_server()
            except OcrError as exc:
                showWarning(exc.message, title="OCR Bridge")

    gui_hooks.main_window_did_init.append(_setup)
