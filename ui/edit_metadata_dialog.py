from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import TrackItem, TrackMetadata
from core.tag_writer import TagWriter
from localization.manager import LocalizationManager


class EditMetadataDialog(QDialog):
    def __init__(
        self,
        track: TrackItem,
        localization: LocalizationManager,
        parent=None,
    ):
        super().__init__(parent)
        self.track = track
        self.loc = localization

        self.selected_cover_path: str = ""
        self.remove_cover_flag = False

        self.setWindowTitle(self.loc.tr("edit_metadata_title"))
        self.setModal(True)
        self.resize(760, 520)

        self._build_ui()
        self._load_initial_data()

    def _build_ui(self):
        root = QVBoxLayout(self)

        grid = QGridLayout()
        root.addLayout(grid, stretch=1)

        form_box = QGroupBox(self.loc.tr("edit_metadata_title"))
        form_layout = QFormLayout(form_box)

        self.artist_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.album_edit = QLineEdit()
        self.genre_edit = QLineEdit()
        self.track_edit = QLineEdit()

        self.year_spin = QSpinBox()
        self.year_spin.setRange(0, 9999)
        self.year_spin.setSpecialValueText("")

        self.comment_edit = QPlainTextEdit()
        self.comment_edit.setMinimumHeight(120)

        form_layout.addRow(self.loc.tr("artist"), self.artist_edit)
        form_layout.addRow(self.loc.tr("title"), self.title_edit)
        form_layout.addRow(self.loc.tr("album"), self.album_edit)
        form_layout.addRow(self.loc.tr("year"), self.year_spin)
        form_layout.addRow(self.loc.tr("genre"), self.genre_edit)
        form_layout.addRow(self.loc.tr("track_number"), self.track_edit)
        form_layout.addRow(self.loc.tr("comment"), self.comment_edit)

        grid.addWidget(form_box, 0, 0)

        cover_box = QGroupBox(self.loc.tr("cover_preview"))
        cover_layout = QVBoxLayout(cover_box)

        self.cover_label = QLabel(self.loc.tr("no_cover_preview"))
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setMinimumSize(240, 240)
        self.cover_label.setStyleSheet(
            "QLabel { border: 1px solid #777; background: #1e1e1e; color: #cfcfcf; }"
        )
        cover_layout.addWidget(self.cover_label, stretch=1)

        cover_buttons = QHBoxLayout()
        self.select_cover_btn = QPushButton(self.loc.tr("select_cover"))
        self.remove_cover_btn = QPushButton(self.loc.tr("remove_cover"))
        cover_buttons.addWidget(self.select_cover_btn)
        cover_buttons.addWidget(self.remove_cover_btn)
        cover_layout.addLayout(cover_buttons)

        self.cover_hint = QLabel("")
        self.cover_hint.setWordWrap(True)
        cover_layout.addWidget(self.cover_hint)

        grid.addWidget(cover_box, 0, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.save_btn = QPushButton(self.loc.tr("save_metadata"))
        self.close_btn = QPushButton(self.loc.tr("close"))
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

        self.select_cover_btn.clicked.connect(self._select_cover)
        self.remove_cover_btn.clicked.connect(self._remove_cover)
        self.save_btn.clicked.connect(self._save)
        self.close_btn.clicked.connect(self.reject)

    def _load_initial_data(self):
        metadata = self.track.metadata

        self.artist_edit.setText(metadata.artist or "")
        self.title_edit.setText(metadata.title or "")
        self.album_edit.setText(metadata.album or "")
        self.genre_edit.setText(metadata.genre or "")
        self.track_edit.setText(metadata.track_number or "")
        self.comment_edit.setPlainText(metadata.comment or "")

        if metadata.year:
            self.year_spin.setValue(int(metadata.year))
        else:
            self.year_spin.setValue(0)

        if self.track.cover_path and Path(self.track.cover_path).exists():
            self._set_cover_preview(self.track.cover_path)
        else:
            self.cover_label.setText(self.loc.tr("no_cover_preview"))

    def _select_cover(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.loc.tr("choose_cover_file"),
            "",
            self.loc.tr("image_files"),
        )
        if not file_path:
            return

        self.selected_cover_path = file_path
        self.remove_cover_flag = False
        self._set_cover_preview(file_path)
        self.cover_hint.setText(self.loc.tr("custom_cover_selected"))

    def _remove_cover(self):
        self.selected_cover_path = ""
        self.remove_cover_flag = True
        self.cover_label.setText(self.loc.tr("no_cover_preview"))
        self.cover_label.setPixmap(QPixmap())
        self.cover_hint.setText(self.loc.tr("cover_removed"))

    def _set_cover_preview(self, image_path: str):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.cover_label.setText(self.loc.tr("no_cover_preview"))
            return

        scaled = pixmap.scaled(
            self.cover_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    def _build_metadata(self) -> TrackMetadata:
        year = self.year_spin.value()
        return TrackMetadata(
            artist=self.artist_edit.text().strip(),
            title=self.title_edit.text().strip(),
            album=self.album_edit.text().strip(),
            year=year if year > 0 else None,
            genre=self.genre_edit.text().strip(),
            track_number=self.track_edit.text().strip(),
            comment=self.comment_edit.toPlainText().strip(),
        )

    def _save(self):
        metadata = self._build_metadata()

        try:
            TagWriter.write_tags(
                self.track.file_path,
                metadata,
                cover_path=self.selected_cover_path or None,
                remove_cover=self.remove_cover_flag,
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.loc.tr("error"),
                f"{self.loc.tr('metadata_save_error')}: {e}",
            )
            return

        self.track.metadata = metadata

        if self.remove_cover_flag:
            self.track.cover_path = ""
            self.track.cover_embedded = False
            self.track.metadata_state.cover = False
        elif self.selected_cover_path:
            self.track.cover_path = self.selected_cover_path
            self.track.cover_embedded = True
            self.track.metadata_state.cover = True

        self.track.metadata_state.artist = bool(metadata.artist)
        self.track.metadata_state.title = bool(metadata.title)
        self.track.metadata_state.album = bool(metadata.album)
        self.track.metadata_state.year = metadata.year is not None

        QMessageBox.information(
            self,
            self.loc.tr("success"),
            self.loc.tr("metadata_saved"),
        )
        self.accept()