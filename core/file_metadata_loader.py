from __future__ import annotations

import os
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

from core.models import TrackItem


def load_file_metadata_into_track(track: TrackItem) -> None:
    """
    Подгружает существующие метаданные и встроенную обложку из аудиофайла в TrackItem.
    Ничего не записывает в файл — только читает.
    """
    path = track.file_path
    ext = os.path.splitext(path)[1].lower()

    audio = MutagenFile(path)
    if audio is None:
        return

    if ext == ".mp3":
        _load_mp3(track, path)
        return

    if ext == ".flac":
        _load_flac(track, audio)
        return

    if ext in {".m4a", ".aac", ".mp4"}:
        _load_mp4(track, audio)
        return

    if ext in {".ogg", ".oga"}:
        _load_ogg(track, audio)
        return

    if ext == ".wav":
        _load_generic_tags(track, audio)
        return

    _load_generic_tags(track, audio)

def _load_mp3(track: TrackItem, path: str) -> None:
    try:
        tags = ID3(path)
    except Exception:
        return

    artist = _first_id3_text(tags, "TPE1")
    title = _first_id3_text(tags, "TIT2")
    album = _first_id3_text(tags, "TALB")
    year = _extract_id3_year(tags)

    _apply_basic_metadata(track, artist, title, album, year)

    for apic in tags.getall("APIC"):
        if getattr(apic, "data", None):
            track.cover_bytes = apic.data
            track.cover_preview_bytes = apic.data
            track.meta_status.cover = True
            break


def _first_id3_text(tags, frame_id: str) -> str:
    frame = tags.get(frame_id)
    if not frame:
        return ""
    text = getattr(frame, "text", None)
    if isinstance(text, list) and text:
        return str(text[0]).strip()
    if text:
        return str(text).strip()
    return ""


def _extract_id3_year(tags) -> Optional[int]:
    for key in ("TDRC", "TYER", "TDOR"):
        frame = tags.get(key)
        if not frame:
            continue
        text = getattr(frame, "text", None)
        value = ""
        if isinstance(text, list) and text:
            value = str(text[0]).strip()
        elif text:
            value = str(text).strip()

        year = _extract_year_from_string(value)
        if year is not None:
            return year
    return None

def _load_flac(track: TrackItem, audio) -> None:
    if not isinstance(audio, FLAC):
        return

    artist = _first_list_value(audio.get("artist"))
    title = _first_list_value(audio.get("title"))
    album = _first_list_value(audio.get("album"))
    year = _extract_year_from_string(
        _first_list_value(audio.get("date"))
        or _first_list_value(audio.get("year"))
    )

    _apply_basic_metadata(track, artist, title, album, year)

    if getattr(audio, "pictures", None):
        for picture in audio.pictures:
            data = getattr(picture, "data", None)
            if data:
                track.cover_bytes = data
                track.cover_preview_bytes = data
                track.meta_status.cover = True
                break

def _load_mp4(track: TrackItem, audio) -> None:
    if not isinstance(audio, MP4):
        return

    artist = _first_list_value(audio.tags.get("\xa9ART")) if audio.tags else ""
    title = _first_list_value(audio.tags.get("\xa9nam")) if audio.tags else ""
    album = _first_list_value(audio.tags.get("\xa9alb")) if audio.tags else ""

    year_value = _first_list_value(audio.tags.get("\xa9day")) if audio.tags else ""
    year = _extract_year_from_string(year_value)

    _apply_basic_metadata(track, artist, title, album, year)

    # cover: covr
    if audio.tags and "covr" in audio.tags:
        covers = audio.tags.get("covr") or []
        if covers:
            data = bytes(covers[0])
            if data:
                track.cover_bytes = data
                track.cover_preview_bytes = data
                track.meta_status.cover = True

def _load_ogg(track: TrackItem, audio) -> None:
    if not isinstance(audio, OggVorbis):
        return

    artist = _first_list_value(audio.get("artist"))
    title = _first_list_value(audio.get("title"))
    album = _first_list_value(audio.get("album"))
    year = _extract_year_from_string(
        _first_list_value(audio.get("date"))
        or _first_list_value(audio.get("year"))
    )

    _apply_basic_metadata(track, artist, title, album, year)

def _load_generic_tags(track: TrackItem, audio) -> None:
    tags = getattr(audio, "tags", None)
    if not tags:
        return

    artist = ""
    title = ""
    album = ""
    year = None

    # пытаемся читать общие ключи
    if hasattr(tags, "get"):
        artist = _first_list_value(tags.get("artist")) or _first_list_value(tags.get("ARTIST"))
        title = _first_list_value(tags.get("title")) or _first_list_value(tags.get("TITLE"))
        album = _first_list_value(tags.get("album")) or _first_list_value(tags.get("ALBUM"))

        year_text = (
            _first_list_value(tags.get("date"))
            or _first_list_value(tags.get("DATE"))
            or _first_list_value(tags.get("year"))
            or _first_list_value(tags.get("YEAR"))
        )
        year = _extract_year_from_string(year_text)

    _apply_basic_metadata(track, artist, title, album, year)

def _apply_basic_metadata(
    track: TrackItem,
    artist: str,
    title: str,
    album: str,
    year: Optional[int],
) -> None:
    # Заполняем "найденные" поля тем, что уже есть в файле
    if artist:
        track.mb_artist = artist
        track.meta_status.artist = True

    if title:
        track.mb_title = title
        track.meta_status.title = True

    if album:
        track.mb_album = album
        track.meta_status.album = True

    if year is not None:
        track.mb_year = year
        track.meta_status.year = True


def _first_list_value(value) -> str:
    if not value:
        return ""
    if isinstance(value, (list, tuple)):
        if not value:
            return ""
        return str(value[0]).strip()
    return str(value).strip()


def _extract_year_from_string(value: str) -> Optional[int]:
    if not value:
        return None

    value = str(value).strip()
    if len(value) >= 4 and value[:4].isdigit():
        try:
            return int(value[:4])
        except Exception:
            return None
    return None