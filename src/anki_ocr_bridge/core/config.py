"""Config model. Storage is injected so the core stays independent of Anki."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Callable, Optional

MIRRORS = {
    "pypi": "",
    "tsinghua": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "aliyun": "https://mirrors.aliyun.com/pypi/simple/",
}


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 8866
    auto_start: bool = True
    engine: str = "rapidocr"
    language: str = "auto"
    mirror: str = "pypi"
    idle_timeout_minutes: int = 10
    paddleocr_lang: str = "ch"

    @classmethod
    def from_dict(cls, d: Optional[dict[str, Any]]) -> "Config":
        d = d or {}
        cfg = cls()
        for f in fields(cls):
            if f.name in d and d[f.name] is not None:
                try:
                    setattr(cfg, f.name, type(getattr(cfg, f.name))(d[f.name]))
                except (TypeError, ValueError):
                    pass
        if not 1 <= cfg.port <= 65535:
            cfg.port = 8866
        if cfg.mirror not in MIRRORS:
            cfg.mirror = "pypi"
        cfg.idle_timeout_minutes = max(0, cfg.idle_timeout_minutes)
        return cfg

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_loopback(self) -> bool:
        return self.host in ("127.0.0.1", "localhost", "::1")


class ConfigStore:
    def __init__(self, load: Callable[[], Optional[dict]], save: Callable[[dict], None]):
        self._load, self._save = load, save

    def get(self) -> Config:
        return Config.from_dict(self._load())

    def put(self, cfg: Config) -> None:
        self._save(cfg.to_dict())
