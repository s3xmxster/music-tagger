from __future__ import annotations

import re
from typing import Optional, Tuple


def clean_filename_text(text: str) -> str:
    text = text.replace("_", " ")
    text = text.replace("—", "-").replace("–", "-")

    text = re.sub(r"[_\-\s]*\d{5,}$", "", text)

    text = re.sub(
        r"\s*[\(\[]\s*(official audio|official video|lyrics|lyric video|audio|video|hq)\s*[\)\]]\s*$",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" _-")
    return text


def parse_artist_title(filename: str) -> Optional[Tuple[str, str]]:
    lower = filename.lower()
    if not lower.endswith(".mp3"):
        return None

    stem = filename[:-4]
    stem = clean_filename_text(stem)

    match = re.match(r"^(?P<artist>.+?)\s*-\s*(?P<title>.+?)$", stem)
    if match:
        artist = clean_filename_text(match.group("artist"))
        title = clean_filename_text(match.group("title"))
        if artist and title:
            return artist, title

    stem_wo_track_num = re.sub(r"^\d+\s*[-.]\s*", "", stem).strip()
    match = re.match(r"^(?P<artist>.+?)\s*-\s*(?P<title>.+?)$", stem_wo_track_num)
    if match:
        artist = clean_filename_text(match.group("artist"))
        title = clean_filename_text(match.group("title"))
        if artist and title:
            return artist, title

    if "-" in stem:
        parts = [p.strip() for p in stem.split("-", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            artist = clean_filename_text(parts[0])
            title = clean_filename_text(parts[1])
            if artist and title:
                return artist, title

    return None