from __future__ import annotations

from typing import Tuple

from config.config import AppConfig
from core.backup_service import create_backup
from core.cover_service import download_cover
from core.models import TrackItem, TrackStatus
from core.musicbrainz_service import search_best_recording
from core.tag_writer import write_tags


def _is_network_error_text(text: str) -> bool:
    text = (text or "").lower()

    markers = [
        "timeout",
        "timed out",
        "connection",
        "connectionerror",
        "proxy",
        "ssl",
        "certificate",
        "dns",
        "name or service not known",
        "temporary failure in name resolution",
        "failed to establish a new connection",
        "max retries exceeded",
        "read timed out",
        "connect timeout",
        "urlopen error",
        "winerror 10060",
        "10060",
        "10061",
        "10054",
        "forcibly closed",
        "connection aborted",
        "connection reset",
        "403",
        "429",
        "451",
        "500",
        "502",
        "503",
        "504",
    ]
    return any(marker in text for marker in markers)


def process_track(track: TrackItem, app_config: AppConfig) -> Tuple[bool, str]:
    if not track.parsed_artist or not track.parsed_title:
        track.status = TrackStatus.SKIPPED
        track.note_key = "note_no_artist_title"
        track.note = ""
        return False, track.note_key

    track.status = TrackStatus.SEARCHING
    track.note_key = "note_searching_mb"
    track.note = ""

    # --- поиск релиза в MusicBrainz ---
    try:
        result = search_best_recording(
            track.parsed_artist,
            track.parsed_title,
            min_score=app_config.min_match_score,
        )
    except Exception as e:
        err_text = str(e)
        track.status = TrackStatus.NETWORK_ERROR

        if _is_network_error_text(err_text):
            track.note_key = "network_error_help"
            track.note = ""
            return False, track.note_key

        track.note_key = ""
        track.note = f"MusicBrainz: {err_text}"
        return False, track.note

    if result is None:
        track.status = TrackStatus.NOT_FOUND
        track.note_key = "note_not_found"
        track.note = ""
        track.match_score = 0.0
        return False, track.note_key

    track.mb_artist = result.artist
    track.mb_title = result.title
    track.mb_album = result.album
    track.mb_year = result.year
    track.mb_release_id = result.release_id
    track.match_score = result.match_score

    # --- загрузка обложки ---
    cover_bytes = None
    if result.release_id and app_config.download_covers:
        track.note_key = "note_loading_cover"
        track.note = ""

        try:
            cover_bytes = download_cover(result.release_id)
        except Exception as e:
            err_text = str(e)
            track.status = TrackStatus.NETWORK_ERROR

            if _is_network_error_text(err_text):
                track.note_key = "network_error_help"
                track.note = ""
                return False, track.note_key

            track.note_key = ""
            track.note = f"Cover: {err_text}"
            return False, track.note

    # --- запись тегов ---
    try:
        if app_config.create_backup:
            create_backup(track.file_path)

        write_tags(
            file_path=track.file_path,
            artist=track.mb_artist,
            title=track.mb_title,
            album=track.mb_album,
            year=track.mb_year,
            cover_bytes=cover_bytes,
        )
    except Exception as e:
        track.status = TrackStatus.WRITE_ERROR
        track.note = str(e)
        track.note_key = ""
        return False, track.note

    track.meta_status.artist = bool(track.mb_artist)
    track.meta_status.title = bool(track.mb_title)
    track.meta_status.album = bool(track.mb_album)
    track.meta_status.year = track.mb_year is not None
    track.meta_status.cover = cover_bytes is not None

    track.cover_bytes = cover_bytes or b""
    track.cover_preview_bytes = cover_bytes or b""

    track.status = TrackStatus.DONE
    track.applied = True
    track.note = ""

    if cover_bytes is not None:
        track.note_key = "note_tags_and_cover_written"
    else:
        track.note_key = "note_tags_written_no_cover"

    return True, track.note_key