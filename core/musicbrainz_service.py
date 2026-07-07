from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

import musicbrainzngs


musicbrainzngs.set_useragent(
    "music-tagger-app",
    "1.0",
    "example@example.com",
)


@dataclass
class MBSearchResult:
    artist: str
    title: str
    album: str
    year: Optional[int]
    release_id: str
    match_score: float


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def search_best_recording(
    artist: str,
    title: str,
    min_score: float = 0.90,
) -> Optional[MBSearchResult]:
    result = musicbrainzngs.search_recordings(
        artist=artist,
        recording=title,
        limit=10,
    )

    recordings = result.get("recording-list", [])
    if not recordings:
        return None

    best = None
    best_score = 0.0

    for rec in recordings:
        found_title = rec.get("title", "")
        score = similarity(title, found_title)
        if score > best_score:
            best_score = score
            best = rec

    if best is None or best_score < min_score:
        return None

    mb_title = best.get("title", "") or title

    mb_artist = artist
    if "artist-credit" in best:
        try:
            names = []
            for item in best["artist-credit"]:
                if isinstance(item, dict) and "artist" in item:
                    names.append(item["artist"]["name"])
            if names:
                mb_artist = ", ".join(names)
        except Exception:
            pass

    mb_album = ""
    mb_year = None
    release_id = ""

    releases = best.get("release-list", [])
    if releases:
        release = releases[0]
        mb_album = release.get("title", "") or ""

        date = release.get("date", "")
        if len(date) >= 4:
            try:
                mb_year = int(date[:4])
            except ValueError:
                mb_year = None

        release_id = release.get("id", "") or ""

    return MBSearchResult(
        artist=mb_artist,
        title=mb_title,
        album=mb_album,
        year=mb_year,
        release_id=release_id,
        match_score=best_score,
    )