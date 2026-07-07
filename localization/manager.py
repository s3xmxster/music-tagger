from __future__ import annotations

from localization.strings import STRINGS


class LocalizationManager:
    LANGUAGE_NAMES = {
        "ru": "Русский",
        "en": "English",
    }

    def __init__(self, language: str = "ru"):
        self.language = language if language in STRINGS else "ru"

    def set_language(self, language: str) -> None:
        if language in STRINGS:
            self.language = language

    def tr(self, key: str) -> str:
        return STRINGS.get(self.language, {}).get(key, key)

    def available_languages(self) -> dict[str, str]:
        return {
            code: self.LANGUAGE_NAMES.get(code, code)
            for code in STRINGS.keys()
        }