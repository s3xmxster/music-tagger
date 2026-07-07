from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple

import eyed3
import musicbrainzngs
import requests

from .models import FileProcessResult


class TaggerService:
    def __init__(self, user_agent_email: str = "example@example.com"):
        musicbrainzngs.set_useragent(
            "music-tagger",
            "0.3.4",
            user_agent_email
        )
        self.filename_pattern = re.compile(
            r"^(?P<artist>.+?)\s*-\s*(?P<title>.+?)\.mp3$",
            re.IGNORECASE
        )

    @staticmethod
    def similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def parse_filename(self, file_name: str) -> Tuple[str, str]:
        match = self.filename_pattern.match(file_name)
        if not match:
            return "", ""
        return match.group("artist").strip(), match.group("title").strip()

    def inspect_file_name(self, file_path: str) -> FileProcessResult:
        file_name = os.path.basename(file_path)
        artist, title = self.parse_filename(file_name)

        result = FileProcessResult(
            file_path=file_path,
            file_name=file_name,
            parsed_artist=artist,
            parsed_title=title,
        )

        if not artist or not title:
            result.status = "Пропуск"
            result.comment = "Имя файла не соответствует шаблону: Исполнитель - Название.mp3"
            return result

        result.status = "Готов к обработке"
        result.comment = "Файл распознан по имени и готов к поиску метаданных"
        return result

    def process_file(self, file_path: str, download_cover: bool = True) -> FileProcessResult:
        result = self.inspect_file_name(file_path)

        if result.status == "Пропуск":
            return result

        artist = result.parsed_artist
        title = result.parsed_title

        try:
            search = musicbrainzngs.search_recordings(
                artist=artist,
                recording=title,
                limit=10
            )
        except Exception as e:
            result.status = "Ошибка"
            result.comment = f"Не удалось обратиться к MusicBrainz: {e}"
            return result

        recordings = search.get("recording-list", [])
        if not recordings:
            result.status = "Не найдено"
            result.comment = "Совпадений в MusicBrainz не найдено"
            return result

        best = None
        best_score = 0.0

        for rec in recordings:
            found_title = rec.get("title", "")
            score = self.similarity(title, found_title)
            if score > best_score:
                best_score = score
                best = rec

        if not best:
            result.status = "Не найдено"
            result.comment = "Подходящий результат не найден"
            return result

        result.similarity = best_score

        if best_score < 0.60:
            result.status = "Слабое совпадение"
            result.comment = f"Низкая похожесть найденного названия: {round(best_score * 100)}%"
            return result

        found_title = best.get("title", "") or title
        found_artist = artist

        if "artist-credit" in best:
            try:
                found_artist = ", ".join(
                    x["artist"]["name"]
                    for x in best["artist-credit"]
                    if isinstance(x, dict) and "artist" in x
                )
            except Exception:
                pass

        found_album = ""
        found_year = None
        release_id = None

        releases = best.get("release-list", [])
        if releases:
            release = releases[0]
            found_album = release.get("title", "") or ""

            date = release.get("date", "") or ""
            if len(date) >= 4:
                try:
                    found_year = int(date[:4])
                except ValueError:
                    found_year = None

            release_id = release.get("id")

        result.found_artist = found_artist
        result.found_title = found_title
        result.found_album = found_album
        result.found_year = found_year

        result.proposed.artist = found_artist
        result.proposed.title = found_title
        result.proposed.album = found_album
        result.proposed.year = found_year

        result.metadata_status.artist = bool(found_artist)
        result.metadata_status.title = bool(found_title)
        result.metadata_status.album = bool(found_album)
        result.metadata_status.year = found_year is not None

        if download_cover and release_id:
            cover_bytes = self._download_cover(release_id)
            if cover_bytes:
                result.proposed.cover_bytes = cover_bytes
                result.cover_preview_bytes = cover_bytes
                result.metadata_status.cover = True

        if any(result.metadata_status.as_dict().values()):
            result.status = "Готово"
            result.comment = "Метаданные найдены и готовы к записи"
        else:
            result.status = "Не найдено"
            result.comment = "Не удалось получить подходящие метаданные"

        return result

    def apply_result_to_file(self, result: FileProcessResult) -> FileProcessResult:
        try:
            audio = eyed3.load(result.file_path)
            if audio is None:
                result.status = "Ошибка"
                result.comment = "Не удалось открыть mp3-файл"
                return result

            if audio.tag is None:
                audio.initTag()

            if result.proposed.artist:
                audio.tag.artist = result.proposed.artist

            if result.proposed.title:
                audio.tag.title = result.proposed.title

            if result.proposed.album:
                audio.tag.album = result.proposed.album

            if result.proposed.year is not None:
                audio.tag.recording_date = eyed3.core.Date(result.proposed.year)

            if result.proposed.cover_bytes:
                audio.tag.images.set(
                    3,
                    result.proposed.cover_bytes,
                    "image/jpeg",
                    "Cover"
                )

            audio.tag.save(version=eyed3.id3.ID3_V2_3)
            result.status = "Применено"
            result.comment = "Метаданные успешно записаны в файл"
            return result

        except Exception as e:
            result.status = "Ошибка"
            result.comment = f"Ошибка записи тегов: {e}"
            return result

    @staticmethod
    def _download_cover(release_id: str) -> Optional[bytes]:
        cover_url = f"https://coverartarchive.org/release/{release_id}/front"

        try:
            response = requests.get(
                cover_url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if response.status_code == 200 and response.content:
                return response.content
        except Exception:
            return None

        return None