from __future__ import annotations

APP_NAME = "Music Tagger"
APP_VERSION = "0.3.3 Alpha"
APP_AUTHOR = "OpenAI + User"

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {
    "Русский": "ru",
    "English": "en",
}

SUPPORTED_AUDIO_EXTENSIONS = {".mp3"}

DEFAULT_MIN_MATCH_SCORE = 0.90
DEFAULT_NETWORK_TIMEOUT = 20

DEFAULT_CONFIG_PATH = "config.json"
LOGS_DIR = "logs"
LOG_FILE_NAME = "music_tagger.log"

SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".m4a",
    ".aac",
    ".ogg",
    ".wav",
}