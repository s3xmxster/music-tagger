from __future__ import annotations

import json
import locale
from dataclasses import asdict, dataclass
from pathlib import Path

from core.constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_LANGUAGE,
    DEFAULT_MIN_MATCH_SCORE,
    DEFAULT_NETWORK_TIMEOUT,
)


@dataclass
class AppConfig:
    language: str = DEFAULT_LANGUAGE
    last_folder: str = ""
    min_match_score: float = DEFAULT_MIN_MATCH_SCORE
    network_timeout: int = DEFAULT_NETWORK_TIMEOUT
    download_covers: bool = True
    create_backup: bool = True


def detect_system_language() -> str:
    try:
        system_locale = locale.getdefaultlocale()[0] or ""
    except Exception:
        system_locale = ""

    if system_locale.lower().startswith("ru"):
        return "ru"

    return "en"


class ConfigManager:
    def __init__(self, path: str = DEFAULT_CONFIG_PATH):
        self.path = Path(path)

    def load(self) -> AppConfig:
        default_language = detect_system_language()

        if not self.path.exists():
            config = AppConfig(language=default_language)
            self.save(config)
            return config

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            config = AppConfig(language=default_language)
            self.save(config)
            return config

        language = data.get("language")
        if not language:
            language = default_language

        return AppConfig(
            language=language,
            last_folder=data.get("last_folder", ""),
            min_match_score=float(data.get("min_match_score", DEFAULT_MIN_MATCH_SCORE)),
            network_timeout=int(data.get("network_timeout", DEFAULT_NETWORK_TIMEOUT)),
            download_covers=bool(data.get("download_covers", True)),
            create_backup=bool(data.get("create_backup", True)),
        )

    def save(self, config: AppConfig):
        self.path.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def set_last_folder(self, folder: str):
        cfg = self.load()
        cfg.last_folder = folder
        self.save(cfg)

    def set_language(self, language: str):
        cfg = self.load()
        cfg.language = language
        self.save(cfg)

    def update(self, config: AppConfig):
        self.save(config)