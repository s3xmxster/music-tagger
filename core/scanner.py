from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from core.models import TrackItem, TrackStatus
from core.parser import parse_artist_title


def _build_track_item(path: Path) -> Optional[TrackItem]:
    if not path.exists() or not path.is_file():
        return None

    if path.suffix.lower() != ".mp3":
        return None

    item = TrackItem(
        file_path=path,
        file_name=path.name,
    )

    parsed = parse_artist_title(path.name)
    if parsed:
        artist, title = parsed
        item.parsed_artist = artist
        item.parsed_title = title
        item.status = TrackStatus.READY
        item.note_key = "note_parsed_ok"
        item.meta_status.artist = True
        item.meta_status.title = True
    else:
        item.status = TrackStatus.SKIPPED
        item.note_key = "note_parsed_fail"

    return item


def scan_music_folder(folder: str) -> List[TrackItem]:
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        return []

    tracks: List[TrackItem] = []

    for path in sorted(folder_path.iterdir(), key=lambda p: p.name.lower()):
        item = _build_track_item(path)
        if item is not None:
            tracks.append(item)

    return tracks


def scan_single_file(file_path: str) -> Optional[TrackItem]:
    return _build_track_item(Path(file_path))