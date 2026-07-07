from __future__ import annotations

import os
from typing import List, Optional
from core.file_metadata_loader import load_file_metadata_into_track

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.config import ConfigManager
from core.models import TrackItem, TrackStatus
from core.parser import parse_artist_title
from localization.manager import LocalizationManager
from ui.settings_dialog import SettingsDialog
from workers.processing_worker import ProcessingWorker
from core.constants import SUPPORTED_AUDIO_EXTENSIONS

from pathlib import Path
from PySide6.QtGui import QIcon

from ui.metadata_editor_dialog import MetadataEditorDialog
from ui.track_properties_dialog import TrackPropertiesDialog

class MainWindow(QMainWindow):
    def __init__(self, config, config_manager, parent=None):
        super().__init__(parent)

        self.config = config
        self.config_manager = config_manager
        self.loc = LocalizationManager(self.config.language)

        base_dir = Path(__file__).resolve().parent.parent
        icon_path = base_dir / "assets" / "app.ico"
        self.setWindowIcon(QIcon(str(icon_path)))

        self.setWindowTitle("Music Tagger")
        self.resize(1320, 860)

        self.tracks: List[TrackItem] = []
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[ProcessingWorker] = None

        self._build_ui()
        self._connect_signals()
        self._apply_language_texts()

        self.log("Приложение запущено. Откройте папку или отдельный mp3-файл и запустите обработку.")

        self._update_log_toggle_text()
        self.log_box.setVisible(False)

    def on_language_changed(self) -> None:
        language = self.lang_combo.currentData()
        if not language:
            return

        self.loc.set_language(language)
        self.config.language = language
        self.config_manager.save(self.config)

        self._apply_language_texts()

    def _get_selected_track(self):
        row = self.files_table.currentRow()
        if row < 0 or row >= len(self.tracks):
            return None
        return self.tracks[row]


    def open_selected_track_properties(self):
        track = self._get_selected_track()
        if track is None:
            return

        dialog = TrackPropertiesDialog(track.file_path, self.loc, self)
        dialog.exec()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        root.addLayout(self._build_top_bar())

        self.version_label = QLabel("v1.0")
        root.addWidget(self.version_label)

        self.progress_box = QGroupBox("Прогресс обработки")
        progress_layout = QHBoxLayout(self.progress_box)
        progress_layout.setContentsMargins(10, 10, 10, 10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.progress_label = QLabel("0 / 0")
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.progress_label.setMinimumWidth(70)

        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_label)
        root.addWidget(self.progress_box)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setChildrenCollapsible(False)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 5)
        content_splitter.setStretchFactor(1, 3)
        content_splitter.setSizes([840, 480])

        root.addWidget(content_splitter, 1)

    def _build_top_bar(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.path_label = QLabel("Папка с музыкой:")
        self.path_value = QLabel("Выберите папку ...")
        self.path_value.setMinimumWidth(240)
        self.path_value.setFrameShape(QFrame.StyledPanel)

        self.open_folder_btn = QPushButton("Открыть папку")
        self.open_file_btn = QPushButton("Открыть файл")
        self.show_files_btn = QPushButton("Показать файлы")
        self.stop_btn = QPushButton("Остановить")
        self.clear_btn = QPushButton("Очистить список")
        self.settings_btn = QPushButton("Настройки")

        self.stop_btn.setEnabled(False)

        self.lang_label = QLabel("Язык:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")

        current_lang = self.config.language if hasattr(self, "config") else "ru"
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)

        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)

        layout.addWidget(self.path_label)
        layout.addWidget(self.path_value, 1)
        layout.addWidget(self.open_folder_btn)
        layout.addWidget(self.open_file_btn)
        layout.addWidget(self.show_files_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.clear_btn)
        layout.addWidget(self.settings_btn)

        layout.addSpacing(10)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_combo)

        return layout

    def _build_left_panel(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.files_box = QGroupBox("Список файлов")
        files_layout = QVBoxLayout(self.files_box)
        files_layout.setContentsMargins(8, 8, 8, 8)

        self.files_table = QTableWidget(0, 6)
        self.files_table.setHorizontalHeaderLabels([
            "Файл",
            "Артист",
            "Название",
            "Статус",
            "Совпадение",
            "Комментарий",
        ])
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SingleSelection)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setMinimumHeight(320)
        self.files_table.setAlternatingRowColors(False)

        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        files_layout.addWidget(self.files_table)
        layout.addWidget(self.files_box, 3)

        # Панель управления логом
        log_controls = QHBoxLayout()
        self.toggle_log_btn = QPushButton("Скрыть лог")
        self.toggle_log_btn.setCheckable(True)
        self.toggle_log_btn.setChecked(True)
        log_controls.addStretch()
        log_controls.addWidget(self.toggle_log_btn)
        layout.addLayout(log_controls)

        self.log_box = QGroupBox("Лог")
        log_layout = QVBoxLayout(self.log_box)
        log_layout.setContentsMargins(8, 8, 8, 8)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)
        self.log_edit.setMaximumHeight(170)
        log_layout.addWidget(self.log_edit)

        layout.addWidget(self.log_box, 1)

        return wrapper

    def _build_right_panel(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.info_box = QGroupBox("Информация о файле")
        self.info_form_layout = QFormLayout(self.info_box)
        self.info_form_layout.setContentsMargins(10, 10, 10, 10)
        self.info_form_layout.setSpacing(6)

        self.file_info_name = QLabel("—")
        self.file_info_artist = QLabel("—")
        self.file_info_title = QLabel("—")
        self.file_info_album = QLabel("—")
        self.file_info_year = QLabel("—")
        self.file_info_status = QLabel("—")
        self.file_info_comment = QLabel("—")

        # Чтобы длинные комментарии и имена не ломали форму
        self.file_info_name.setWordWrap(True)
        self.file_info_artist.setWordWrap(True)
        self.file_info_title.setWordWrap(True)
        self.file_info_album.setWordWrap(True)
        self.file_info_comment.setWordWrap(True)

        # Лейблы слева в форме
        self.info_label_file = QLabel("Файл:")
        self.info_label_artist = QLabel("Артист:")
        self.info_label_title = QLabel("Название:")
        self.info_label_album = QLabel("Альбом:")
        self.info_label_year = QLabel("Год:")
        self.info_label_status = QLabel("Статус:")
        self.info_label_comment = QLabel("Комментарий:")

        self.info_form_layout.addRow(self.info_label_file, self.file_info_name)
        self.info_form_layout.addRow(self.info_label_artist, self.file_info_artist)
        self.info_form_layout.addRow(self.info_label_title, self.file_info_title)
        self.info_form_layout.addRow(self.info_label_album, self.file_info_album)
        self.info_form_layout.addRow(self.info_label_year, self.file_info_year)
        self.info_form_layout.addRow(self.info_label_status, self.file_info_status)
        self.info_form_layout.addRow(self.info_label_comment, self.file_info_comment)

        layout.addWidget(self.info_box, 2)

        self.cover_box = QGroupBox("Обложка")
        cover_layout = QVBoxLayout(self.cover_box)
        cover_layout.setContentsMargins(10, 10, 10, 10)

        self.cover_label = QLabel("Обложка не загружена")
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setFrameShape(QFrame.Box)
        self.cover_label.setMinimumHeight(260)
        self.cover_label.setMaximumHeight(420)

        cover_layout.addWidget(self.cover_label)
        layout.addWidget(self.cover_box, 4)

        # Блок действий над выбранным треком
        self.actions_box = QGroupBox("Действия")
        actions_layout = QVBoxLayout(self.actions_box)
        actions_layout.setContentsMargins(10, 10, 10, 10)
        actions_layout.setSpacing(8)

        self.apply_selected_btn = QPushButton()
        self.apply_all_btn = QPushButton()
        self.manual_edit_btn = QPushButton()
        self.properties_btn = QPushButton()

        self.apply_selected_btn.setEnabled(False)
        self.manual_edit_btn.setEnabled(False)
        self.properties_btn.setEnabled(False)

        actions_layout.addWidget(self.apply_selected_btn)
        actions_layout.addWidget(self.apply_all_btn)
        actions_layout.addWidget(self.manual_edit_btn)
        actions_layout.addWidget(self.properties_btn)
        actions_layout.addStretch()

        layout.addWidget(self.actions_box, 1)

        return wrapper
    
    def _rebuild_info_form_labels(self):
        tr = self.loc.tr

        self.info_label_file.setText(tr("file") + ":")
        self.info_label_artist.setText(tr("artist") + ":")
        self.info_label_title.setText(tr("title") + ":")
        self.info_label_album.setText(tr("album") + ":")
        self.info_label_year.setText(tr("year") + ":")
        self.info_label_status.setText(tr("status") + ":")
        self.info_label_comment.setText(tr("comment") + ":")

    def toggle_log_visibility(self):
        self.log_box.setVisible(not self.log_box.isVisible())
        self._update_log_toggle_text()

    def _connect_signals(self):
        self.open_folder_btn.clicked.connect(self.choose_folder)
        self.open_file_btn.clicked.connect(self.choose_file)
        self.show_files_btn.clicked.connect(self.show_loaded_files)
        self.apply_selected_btn.clicked.connect(self.apply_selected_file)
        self.apply_all_btn.clicked.connect(self.apply_all_files)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.clear_btn.clicked.connect(self.clear_all)
        self.settings_btn.clicked.connect(self.open_settings)

        self.files_table.itemSelectionChanged.connect(self.on_file_selection_changed)

        self.manual_edit_btn.clicked.connect(self.open_manual_metadata_editor)
        self.properties_btn.clicked.connect(self.open_selected_track_properties)

        self.files_table.itemDoubleClicked.connect(self.open_selected_file)

        self.toggle_log_btn.clicked.connect(self.toggle_log_visibility)

    def open_selected_file(self, item):
        row = item.row()
        if row < 0 or row >= len(self.tracks):
            return

        track = self.tracks[row]

        try:
            os.startfile(str(track.file_path))
        except Exception as exc:
            self.log(f"Не удалось открыть файл: {exc}")

    def _apply_language_texts(self):
        tr = self.loc.tr

        # окно
        self.setWindowTitle(tr("app_title"))

        # верхняя панель
        self.path_label.setText(tr("music_folder"))
        if not self.tracks:
            self.path_value.setText(tr("folder_placeholder"))

        self.open_folder_btn.setText(tr("select_folder"))
        self.open_file_btn.setText(tr("open_mp3"))
        self.show_files_btn.setText(tr("scan_folder"))
        self.apply_all_btn.setText(tr("fix_all"))
        self.stop_btn.setText(tr("stop_processing"))
        self.clear_btn.setText(tr("clear_list"))
        self.settings_btn.setText(tr("settings"))
        self.lang_label.setText(tr("language") + ":")

        # правая панель: действия с выбранным треком
        self.apply_selected_btn.setText(tr("fix_selected"))
        self.manual_edit_btn.setText(tr("edit_metadata"))
        self.properties_btn.setText(tr("show_properties"))

        # версия
        self.version_label.setText(tr("app_version"))

        # group boxes
        self.progress_box.setTitle(tr("progress"))
        self.files_box.setTitle(tr("tracks"))
        self.log_box.setTitle(tr("log"))
        self.info_box.setTitle(tr("track_info"))
        self.cover_box.setTitle(tr("cover_preview"))
        self.actions_box.setTitle(tr("actions"))

        # кнопка скрытия/показа лога
        if self.log_box.isVisible():
            self.toggle_log_btn.setText(tr("hide_log"))
        else:
            self.toggle_log_btn.setText(tr("show_log"))

        # подписи справа
        self.info_label_file.setText(tr("file") + ":")
        self.info_label_artist.setText(tr("artist") + ":")
        self.info_label_title.setText(tr("title") + ":")
        self.info_label_album.setText(tr("album") + ":")
        self.info_label_year.setText(tr("year") + ":")
        self.info_label_status.setText(tr("status") + ":")
        self.info_label_comment.setText(tr("note") + ":")

        # таблица файлов
        self.files_table.setHorizontalHeaderLabels([
            tr("file"),
            tr("artist"),
            tr("title"),
            tr("status"),
            tr("match"),
            tr("note"),
        ])

        # если обложка не загружена — показываем локализованный текст
        if self.cover_label.pixmap() is None or self.cover_label.pixmap().isNull():
            current_text = self.cover_label.text().strip()
            if current_text in {
                "",
                "Обложка не загружена",
                "Cover not loaded",
                "Обложка не найдена",
                "Cover not found",
                "Нет обложки",
                "No cover",
            }:
                self.cover_label.setText(tr("no_cover_preview"))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с mp3")
        if not folder:
            return

        self.path_value.setText(folder)
        self.tracks = self._collect_tracks_from_folder(folder)
        self._fill_files_table_initial()
        self.log(f"Загружена папка: {folder}")
        self.log(f"Найдено mp3-файлов: {len(self.tracks)}")

    def _update_log_toggle_text(self):
        tr = self.loc.tr if hasattr(self, "loc") else lambda x: x

        if self.log_box.isVisible():
            self.toggle_log_btn.setText(tr("hide_log") if hasattr(self, "loc") else "Скрыть лог")
        else:
            self.toggle_log_btn.setText(tr("show_log") if hasattr(self, "loc") else "Показать лог")

    def choose_file(self):
        file_filter = (
            "Audio files (*.mp3 *.flac *.m4a *.aac *.ogg *.wav);;"
            "MP3 files (*.mp3);;"
            "FLAC files (*.flac);;"
            "M4A files (*.m4a);;"
            "AAC files (*.aac);;"
            "OGG files (*.ogg);;"
            "WAV files (*.wav)"
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аудиофайл",
            "",
            file_filter,
        )
        if not file_path:
            return

        self.path_value.setText(file_path)
        self.tracks = [self._build_track(file_path)]
        self._fill_files_table_initial()
        self.log(f"Загружен файл: {file_path}")

    def _collect_tracks_from_folder(self, folder: str) -> List[TrackItem]:
        supported_extensions = {
            ".mp3",
            ".flac",
            ".m4a",
            ".aac",
            ".ogg",
            ".wav",
        }

        tracks: List[TrackItem] = []
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            ext = os.path.splitext(name)[1].lower()

            if os.path.isfile(path) and ext in supported_extensions:
                tracks.append(self._build_track(path))

        return tracks

    def _build_track(self, file_path: str) -> TrackItem:
        file_name = os.path.basename(file_path)

        parsed = parse_artist_title(file_name)
        if parsed:
            artist, title = parsed
        else:
            artist, title = "", ""

        track = TrackItem(file_path=file_path, file_name=file_name)
        track.parsed_artist = artist or ""
        track.parsed_title = title or ""

        # Сразу подтягиваем уже существующие теги и встроенную обложку из файла
        try:
            load_file_metadata_into_track(track)
        except Exception as exc:
            pass

        has_any_title_data = bool(
            track.parsed_artist and track.parsed_title
        ) or bool(
            track.mb_artist and track.mb_title
        )

        if not has_any_title_data:
            track.status = TrackStatus.SKIPPED
            track.note_key = "note_no_artist_title"
        else:
            track.status = TrackStatus.NEW
            if track.note_key == "note_no_artist_title":
                track.note_key = ""
                track.note = ""

        return track

    def _fill_track_audio_properties(self, track: TrackItem) -> None:
        try:
            from mutagen import File as MutagenFile
            import os

            track.file_size = os.path.getsize(track.file_path)

            audio = MutagenFile(track.file_path)
            if audio is None:
                return

            info = getattr(audio, "info", None)
            if info is not None:
                length = getattr(info, "length", None)
                if length:
                    track.duration = float(length)

                sample_rate = getattr(info, "sample_rate", None)
                if sample_rate:
                    track.sample_rate = int(sample_rate)

                bitrate = getattr(info, "bitrate", None)
                if bitrate:
                    track.bitrate = int(bitrate)

                channels = getattr(info, "channels", None)
                if channels:
                    track.channels = int(channels)

            track.channel_mode = self._detect_channel_mode(track.channels)

            # попытка определить наличие обложки
            if self._track_has_cover(audio):
                track.meta_status.cover = True

        except Exception as exc:
            self.log(f"Не удалось прочитать свойства файла {track.file_name}: {exc}")


    def _track_has_cover(self, audio) -> bool:
        try:
            # MP3 / WAV (ID3 APIC)
            tags = getattr(audio, "tags", None)
            if tags:
                if hasattr(tags, "getall"):
                    if tags.getall("APIC"):
                        return True

                # MP4/M4A covr
                if "covr" in tags:
                    return True

            # FLAC pictures
            pictures = getattr(audio, "pictures", None)
            if pictures:
                return len(pictures) > 0

        except Exception:
            pass

        return False
    
    def _detect_channel_mode(self, channels: int | None) -> str:
        if channels == 1:
            return "Mono"
        if channels == 2:
            return "Stereo"
        if channels and channels > 2:
            return f"{channels} channels"
        return ""

    def _fill_files_table_initial(self):
        self.files_table.setRowCount(0)

        for track in self.tracks:
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)

            self._set_table_item(row, 0, track.file_name)
            self._set_table_item(row, 1, track.parsed_artist or "—")
            self._set_table_item(row, 2, track.parsed_title or "—")
            self._set_table_item(row, 3, self._status_to_text(track.status))
            self._set_table_item(row, 4, "—")
            self._set_table_item(row, 5, self._note_to_text(track.note_key, track.note))

        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0 / {len(self.tracks)}")
        self._reset_file_info()

    def show_loaded_files(self):
        if not self.tracks:
            QMessageBox.information(self, "Music Tagger", "Список файлов пуст.")
            return

        self.log("Текущие загруженные файлы:")
        for track in self.tracks:
            self.log(f"  • {track.file_path}")

    def apply_selected_file(self):
        row = self.files_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Music Tagger", "Сначала выберите файл в таблице.")
            return
        if row >= len(self.tracks):
            return

        self._start_worker(single_row=row)

    def apply_all_files(self):
        if not self.tracks:
            QMessageBox.information(self, "Music Tagger", "Список файлов пуст.")
            return

        self._start_worker(single_row=None)

    def _start_worker(self, single_row: int | None):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Music Tagger", "Обработка уже выполняется.")
            return

        total = 1 if single_row is not None else len(self.tracks)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0 / {total}")

        self.worker_thread = QThread(self)
        self.worker = ProcessingWorker(self.tracks, self.config, single_row=single_row)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self.on_worker_progress)
        self.worker.track_updated.connect(self.on_worker_track_updated)
        self.worker.log_message.connect(self.log)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.single_finished.connect(self.on_worker_single_finished)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.single_finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.stop_btn.setEnabled(True)
        self.worker_thread.start()

    def stop_processing(self):
        if self.worker:
            self.worker.request_stop()
            self.stop_btn.setEnabled(False)

    def on_worker_progress(self, current: int, total: int):
        percent = int((current / total) * 100) if total else 0
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"{current} / {total}")

    def on_worker_track_updated(self, row: int, track: TrackItem):
        if row < 0 or row >= len(self.tracks):
            return
        self.tracks[row] = track
        self._update_row(row, track)
        if self.files_table.currentRow() == row:
            self._show_track_details(track)

    def on_worker_finished(self, processed: int, success_count: int, stopped: bool):
        self.stop_btn.setEnabled(False)
        self.worker = None
        self.worker_thread = None

        if stopped:
            self.log("Обработка остановлена пользователем.")
        else:
            self.log(f"Обработка завершена. Успешно: {success_count}/{processed}")

    def on_worker_single_finished(self, row: int, ok: bool, message: str):
        self.stop_btn.setEnabled(False)
        self.worker = None
        self.worker_thread = None

        track = None
        if 0 <= row < len(self.tracks):
            track = self.tracks[row]
            self._update_row(row, track)
            if self.files_table.currentRow() == row:
                self._show_track_details(track)

        if ok:
            self.log(self._note_to_text(message, message))
            return

        if track and track.note_key == "network_error_help":
            self.log(
                "Проверьте подключение к интернету. "
                "В некоторых регионах доступ к сервисам, которые использует программа, "
                "может быть ограничен. Используйте средства обхода ограничений "
                "(например, zapret) с доменами, указанными на странице проекта Music Tagger на GitHub."
            )
        else:
            self.log(self._note_to_text(message, message))

    def _update_row(self, row: int, track: TrackItem):
        self._set_table_item(row, 1, track.mb_artist or track.parsed_artist or "—")
        self._set_table_item(row, 2, track.mb_title or track.parsed_title or "—")
        self._set_table_item(row, 3, self._status_to_text(track.status))
        self._set_table_item(row, 4, self._score_to_text(track.match_score))
        self._set_table_item(row, 5, self._note_to_text(track.note_key, track.note))
        

    def on_file_selection_changed(self):
        row = self.files_table.currentRow()
        has_track = 0 <= row < len(self.tracks)

        self.apply_selected_btn.setEnabled(has_track)
        self.manual_edit_btn.setEnabled(has_track)
        self.properties_btn.setEnabled(has_track)

        if has_track:
            self._show_track_details(self.tracks[row])
        else:
            self._clear_track_details()

    def _show_track_details(self, track: TrackItem):
        self.file_info_name.setText(track.file_name or "—")
        self.file_info_artist.setText(track.mb_artist or track.parsed_artist or "—")
        self.file_info_title.setText(track.mb_title or track.parsed_title or "—")
        self.file_info_album.setText(track.mb_album or "—")
        self.file_info_year.setText(str(track.mb_year) if track.mb_year else "—")
        self.file_info_status.setText(self._status_to_text(track.status))

        comment_text = self._note_to_text(track.note_key, track.note)

        # Сетевую подсказку больше не показываем в карточке файла — только в логах
        if track.note_key == "network_error_help":
            self.file_info_comment.setText("—")
        else:
            self.file_info_comment.setText(comment_text or "—")

        if track.cover_preview_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(track.cover_preview_bytes)
            scaled = pixmap.scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_label.setPixmap(scaled)
            self.cover_label.setText("")
        else:
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("Обложка не найдена")

    def _clear_track_details(self):
        self.file_info_name.setText("—")
        self.file_info_artist.setText("—")
        self.file_info_title.setText("—")
        self.file_info_album.setText("—")
        self.file_info_year.setText("—")
        self.file_info_status.setText("—")
        self.file_info_comment.setText("—")

        self.cover_label.setPixmap(QPixmap())
        self.cover_label.setText("Обложка не загружена")

    def _reset_file_info(self):
        self.file_info_name.setText("—")
        self.file_info_artist.setText("—")
        self.file_info_title.setText("—")
        self.file_info_album.setText("—")
        self.file_info_year.setText("—")
        self.file_info_status.setText("—")
        self.file_info_comment.setText("—")
        self.cover_label.setPixmap(QPixmap())
        self.cover_label.setText("Обложка не загружена")

    def open_settings(self):
        dialog = SettingsDialog(self, download_cover_default=self.config.download_covers)
        if dialog.exec():
            values = dialog.get_values()
            self.config.download_covers = values["download_cover"]
            self.config_manager.update(self.config)
            self.log(
                "Настройки обновлены: "
                f"загрузка обложки = {'вкл' if self.config.download_covers else 'выкл'}"
            )

    def clear_all(self):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Music Tagger", "Нельзя очистить список во время обработки.")
            return

        self.tracks.clear()
        self.path_value.setText("Выберите папку ...")
        self.files_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.progress_label.setText("0 / 0")
        self._reset_file_info()
        self.log("Список файлов очищен.")

    def log(self, text: str):
        self.log_edit.append(text)

    def _set_table_item(self, row: int, col: int, text: str):
        self.files_table.setItem(row, col, QTableWidgetItem(text))

    def open_manual_metadata_editor(self):
        dialog = MetadataEditorDialog(self.loc, self)
        dialog.exec()

    @staticmethod
    def _score_to_text(score: float) -> str:
        if score <= 0:
            return "—"
        return f"{round(score * 100)}%"
    
    def _status_to_text(self, status: str) -> str:
        tr = self.loc.tr
        mapping = {
            TrackStatus.NEW: tr("status_new"),
            TrackStatus.SEARCHING: tr("status_searching"),
            TrackStatus.DONE: tr("status_done"),
            TrackStatus.NOT_FOUND: tr("status_not_found"),
            TrackStatus.NETWORK_ERROR: tr("status_network_error"),
            TrackStatus.WRITE_ERROR: tr("status_write_error"),
            TrackStatus.SKIPPED: tr("status_skipped"),
            TrackStatus.STOPPED: tr("status_stopped"),
        }
        return mapping.get(status, status or "—")

    def _note_to_text(self, note_key: str | None, fallback: str = "") -> str:
        tr = self.loc.tr

        if note_key == "note_no_artist_title":
            return tr("note_no_artist_title")
        if note_key == "note_not_found":
            return tr("note_not_found")
        if note_key == "note_network_error":
            return tr("note_network_error")
        if note_key == "network_error_help":
            return tr("status_network_error")   # коротко: "Ошибка сети"
        if note_key == "note_write_error":
            return tr("note_write_error")
        if note_key == "note_stopped":
            return tr("note_stopped")

        return fallback or "—"