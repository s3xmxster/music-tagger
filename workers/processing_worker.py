from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QObject, Signal, Slot

from config.config import AppConfig
from core.models import TrackItem, TrackStatus
from core.processor import process_track


class ProcessingWorker(QObject):
    progress_changed = Signal(int, int)
    track_updated = Signal(int, object)
    log_message = Signal(str)
    finished = Signal(int, int, bool)
    single_finished = Signal(int, bool, str)

    def __init__(
        self,
        tracks: Sequence[TrackItem],
        config: AppConfig,
        single_row: int | None = None,
    ) -> None:
        super().__init__()
        self._tracks = list(tracks)
        self._config = config
        self._single_row = single_row
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    @Slot()
    def run(self) -> None:
        try:
            if self._single_row is not None:
                self._run_single()
            else:
                self._run_all()
        except Exception as exc:
            self.log_message.emit(f"Критическая ошибка worker: {exc}")
            if self._single_row is not None:
                row = self._single_row if self._single_row >= 0 else 0
                self.single_finished.emit(row, False, str(exc))
            else:
                self.finished.emit(0, 0, False)

    def _run_single(self) -> None:
        row = self._single_row if self._single_row is not None else 0

        if row < 0 or row >= len(self._tracks):
            self.single_finished.emit(row, False, "Некорректный индекс трека.")
            return

        track = self._tracks[row]

        if self._stop_requested:
            track.status = TrackStatus.STOPPED
            track.set_note("stopped", "Обработка остановлена пользователем.")
            self.track_updated.emit(row, track)
            self.single_finished.emit(row, False, "Обработка остановлена.")
            return

        if not self._can_process(track):
            message = self._skip_message(track)
            self.single_finished.emit(row, False, message)
            return

        try:
            track.status = TrackStatus.SEARCHING
            self.track_updated.emit(row, track)
            self.log_message.emit(f"Обработка файла: {track.file_name}")

            ok, message = process_track(track, self._config)

            if self._stop_requested and track.status == TrackStatus.SEARCHING:
                track.status = TrackStatus.STOPPED
                track.set_note("stopped", "Обработка остановлена пользователем.")
                ok = False
                message = "Обработка остановлена."

            self.track_updated.emit(row, track)
            self.single_finished.emit(row, ok, message)
            
        except Exception as exc:
            self._apply_worker_exception(track, exc)
            self.track_updated.emit(row, track)
            self.single_finished.emit(row, False, str(exc))

    def _run_all(self) -> None:
        total = len(self._tracks)
        if total == 0:
            self.finished.emit(0, 0, False)
            return

        processed = 0
        success_count = 0
        stopped = False

        self.log_message.emit(f"Запуск обработки: {total} файл(ов).")

        for index, track in enumerate(self._tracks):
            if self._stop_requested:
                stopped = True
                self._mark_remaining_as_stopped(start_index=index)
                self.log_message.emit("Обработка остановлена пользователем.")
                break

            if not self._can_process(track):
                message = self._skip_message(track)
                self.log_message.emit(f"{track.file_name}: {message}")
                self.track_updated.emit(index, track)
                self.progress_changed.emit(index + 1, total)
                continue

            try:
                track.status = TrackStatus.SEARCHING
                self.track_updated.emit(index, track)
                self.log_message.emit(f"Обработка файла: {track.file_name}")

                ok, message = process_track(track, self._config)
                processed += 1

                if ok:
                    success_count += 1
                    self.log_message.emit(f"Готово: {track.file_name} — {message}")
                else:
                    if track.note_key == "network_error_help":
                        self.log_message.emit(
                            f"{track.file_name}: "
                            "Проверьте подключение к интернету. "
                            "В некоторых регионах доступ к сервисам, которые использует программа, "
                            "может быть ограничен. Используйте средства обхода ограничений "
                            "(например, zapret) с доменами, указанными на странице проекта Music Tagger на GitHub."
                        )
                    else:
                        self.log_message.emit(f"{track.file_name}: {message}")

            except Exception as exc:
                self._apply_worker_exception(track, exc)
                self.log_message.emit(f"Ошибка при обработке {track.file_name}: {exc}")

            self.track_updated.emit(index, track)
            self.progress_changed.emit(index + 1, total)

        if not stopped:
            self.log_message.emit("Обработка завершена.")

        self.finished.emit(processed, success_count, stopped)

    def _can_process(self, track: TrackItem) -> bool:
        if track.status in (TrackStatus.SEARCHING, TrackStatus.DONE):
            return False
        if not track.has_parsed_data():
            return False
        return True

    def _skip_message(self, track: TrackItem) -> str:
        if track.status == TrackStatus.SEARCHING:
            return "Файл уже находится в обработке."
        if track.status == TrackStatus.DONE:
            return "Файл уже обработан."
        if not track.has_parsed_data():
            return "Не удалось определить исполнителя и название."
        return "Файл пропущен."
    
    def _network_help_message(self) -> str:
        return (
            "Проверьте подключение к интернету. "
            "В некоторых регионах доступ к сервисам, которые использует программа, "
            "может быть ограничен. Используйте средства обхода ограничений "
            "(например, zapret) с доменами, указанными на странице проекта Music Tagger на GitHub."
    )
    
    def _is_network_error(self, exc: Exception) -> bool:
        text = str(exc).lower()

        network_markers = [
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

            # важно для urllib / MusicBrainz
            "urlopen error",
            "winerror 10060",
            "10060",
            "10061",
            "10054",
            "forcibly closed",
            "connection aborted",
            "connection reset",

            # http-ошибки / ограничения
            "403",
            "429",
            "451",
            "500",
            "502",
            "503",
            "504",
        ]

        return any(marker in text for marker in network_markers)

    def _apply_worker_exception(self, track: TrackItem, exc: Exception) -> None:
        if self._is_network_error(exc):
            track.status = TrackStatus.NETWORK_ERROR
            track.set_note("network_error_help", "")
        else:
            track.status = TrackStatus.NETWORK_ERROR
            track.set_note("worker_error", f"Ошибка обработки: {exc}")

    def _mark_remaining_as_stopped(self, start_index: int) -> None:
        for index in range(start_index, len(self._tracks)):
            track = self._tracks[index]
            if track.status in (
                TrackStatus.NEW,
                TrackStatus.SEARCHING,
                TrackStatus.NOT_FOUND,
                TrackStatus.NETWORK_ERROR,
                TrackStatus.WRITE_ERROR,
                TrackStatus.SKIPPED,
            ):
                track.status = TrackStatus.STOPPED
                track.set_note("stopped", "Обработка остановлена пользователем.")
                self.track_updated.emit(index, track)