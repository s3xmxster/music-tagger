from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class TrackStatus:
    NEW = "new"
    SEARCHING = "searching"
    DONE = "done"
    NOT_FOUND = "not_found"
    NETWORK_ERROR = "network_error"
    WRITE_ERROR = "write_error"
    SKIPPED = "skipped"
    STOPPED = "stopped"


@dataclass
class MetadataStatus:
    artist: bool = False
    title: bool = False
    album: bool = False
    year: bool = False
    cover: bool = False

    def reset(self) -> None:
        self.artist = False
        self.title = False
        self.album = False
        self.year = False
        self.cover = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "artist": self.artist,
            "title": self.title,
            "album": self.album,
            "year": self.year,
            "cover": self.cover,
        }


@dataclass
class TrackItem:
    file_path: str
    file_name: str

    parsed_artist: str = ""
    parsed_title: str = ""

    mb_artist: str = ""
    mb_title: str = ""
    mb_album: str = ""
    mb_year: Optional[int] = None
    mb_release_id: str = ""

    match_score: float = 0.0

    status: str = TrackStatus.NEW
    note_key: str = ""
    note: str = ""

    meta_status: MetadataStatus = field(default_factory=MetadataStatus)

    cover_bytes: bytes = b""
    cover_preview_bytes: bytes = b""

    file_size: int = 0
    duration: float = 0.0
    bitrate: int = 0
    bitrate_mode: str = ""
    sample_rate: int = 0
    channels: int = 0
    channel_mode: str = ""

    applied: bool = False

    def display_artist(self) -> str:
        return self.mb_artist or self.parsed_artist or ""

    def display_title(self) -> str:
        return self.mb_title or self.parsed_title or ""

    def has_parsed_data(self) -> bool:
        return bool(self.parsed_artist and self.parsed_title)

    def has_found_metadata(self) -> bool:
        return bool(self.mb_artist or self.mb_title or self.mb_album or self.mb_year)

    def clear_found_metadata(self) -> None:
        self.mb_artist = ""
        self.mb_title = ""
        self.mb_album = ""
        self.mb_year = None
        self.mb_release_id = ""
        self.match_score = 0.0
        self.cover_bytes = b""
        self.cover_preview_bytes = b""
        self.meta_status.reset()

    def set_note(self, note_key: str = "", note: str = "") -> None:
        self.note_key = note_key
        self.note = note