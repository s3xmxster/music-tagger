from __future__ import annotations

import os
from typing import Optional

from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, TDRC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from mutagen import File


def write_tags(
    file_path: str,
    artist: str = "",
    title: str = "",
    album: str = "",
    year: Optional[int] = None,
    cover_bytes: Optional[bytes] = None,
) -> None:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".mp3":
        _write_mp3(file_path, artist, title, album, year, cover_bytes)
    elif ext == ".flac":
        _write_flac(file_path, artist, title, album, year, cover_bytes)
    elif ext in {".m4a", ".aac"}:
        _write_mp4(file_path, artist, title, album, year, cover_bytes)
    elif ext in {".ogg", ".oga"}:
        _write_ogg(file_path, artist, title, album, year, cover_bytes)
    elif ext == ".wav":
        _write_wav(file_path, artist, title, album, year, cover_bytes)
    else:
        raise RuntimeError(f"Формат файла не поддерживается для записи тегов: {ext}")


def _detect_cover_mime(cover_bytes: bytes) -> str:
    if cover_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "image/jpeg"


def _write_mp3(
    file_path: str,
    artist: str,
    title: str,
    album: str,
    year: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = ID3(file_path)

    audio.delall("TPE1")
    audio.delall("TIT2")
    audio.delall("TALB")
    audio.delall("TDRC")
    audio.delall("APIC")

    if artist:
        audio.add(TPE1(encoding=3, text=artist))
    if title:
        audio.add(TIT2(encoding=3, text=title))
    if album:
        audio.add(TALB(encoding=3, text=album))
    if year:
        audio.add(TDRC(encoding=3, text=str(year)))

    if cover_bytes:
        mime = _detect_cover_mime(cover_bytes)
        audio.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3,
                desc="Cover",
                data=cover_bytes,
            )
        )

    audio.save(v2_version=3)


def _write_flac(
    file_path: str,
    artist: str,
    title: str,
    album: str,
    year: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = FLAC(file_path)

    if artist:
        audio["artist"] = [artist]
    else:
        audio.pop("artist", None)

    if title:
        audio["title"] = [title]
    else:
        audio.pop("title", None)

    if album:
        audio["album"] = [album]
    else:
        audio.pop("album", None)

    if year:
        audio["date"] = [str(year)]
    else:
        audio.pop("date", None)

    if cover_bytes:
        audio.clear_pictures()

        pic = Picture()
        pic.data = cover_bytes
        pic.type = 3
        pic.mime = _detect_cover_mime(cover_bytes)
        pic.desc = "Cover"
        audio.add_picture(pic)

    audio.save()


def _write_mp4(
    file_path: str,
    artist: str,
    title: str,
    album: str,
    year: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = MP4(file_path)

    if artist:
        audio["\xa9ART"] = [artist]
    else:
        audio.pop("\xa9ART", None)

    if title:
        audio["\xa9nam"] = [title]
    else:
        audio.pop("\xa9nam", None)

    if album:
        audio["\xa9alb"] = [album]
    else:
        audio.pop("\xa9alb", None)

    if year:
        audio["\xa9day"] = [str(year)]
    else:
        audio.pop("\xa9day", None)

    if cover_bytes:
        if _detect_cover_mime(cover_bytes) == "image/png":
            fmt = MP4Cover.FORMAT_PNG
        else:
            fmt = MP4Cover.FORMAT_JPEG

        audio["covr"] = [MP4Cover(cover_bytes, imageformat=fmt)]
    else:
        audio.pop("covr", None)

    audio.save()


def _write_ogg(
    file_path: str,
    artist: str,
    title: str,
    album: str,
    year: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = File(file_path)

    if audio is None:
        raise RuntimeError("Не удалось открыть OGG-файл")

    if not isinstance(audio, (OggVorbis, OggOpus)):
        raise RuntimeError("Формат OGG не поддерживается для записи тегов")

    if artist:
        audio["artist"] = [artist]
    else:
        audio.pop("artist", None)

    if title:
        audio["title"] = [title]
    else:
        audio.pop("title", None)

    if album:
        audio["album"] = [album]
    else:
        audio.pop("album", None)

    if year:
        audio["date"] = [str(year)]
    else:
        audio.pop("date", None)

    # Обложки в OGG/Vorbis/Opus через mutagen — отдельная история,
    # поэтому пока оставляем только текстовые теги.
    audio.save()


def _write_wav(
    file_path: str,
    artist: str,
    title: str,
    album: str,
    year: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = WAVE(file_path)

    try:
        tags = ID3(file_path)
    except Exception:
        tags = ID3()

    tags.delall("TPE1")
    tags.delall("TIT2")
    tags.delall("TALB")
    tags.delall("TDRC")
    tags.delall("APIC")

    if artist:
        tags.add(TPE1(encoding=3, text=artist))
    if title:
        tags.add(TIT2(encoding=3, text=title))
    if album:
        tags.add(TALB(encoding=3, text=album))
    if year:
        tags.add(TDRC(encoding=3, text=str(year)))

    if cover_bytes:
        mime = _detect_cover_mime(cover_bytes)
        tags.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3,
                desc="Cover",
                data=cover_bytes,
            )
        )

    audio.tags = tags
    audio.save()