from __future__ import annotations

from pathlib import Path
from typing import Optional

import eyed3
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QFrame,
)

from core.tag_writer import write_tags


class MetadataEditorDialog(QDialog):
    def __init__(self, loc, parent=None):
        super().__init__(parent)
        self.loc = loc

        self.file_path: str = ""
        self.cover_bytes: Optional[bytes] = None
        self.cover_removed: bool = False

        self._build_ui()
        self._apply_texts()

    # ---------------- UI ----------------

    def _build_ui(self):
        self.resize(760, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # верхняя строка: файл + кнопка открытия
        top = QHBoxLayout()
        self.file_label_title = QLabel()
        self.file_path_label = QLabel("—")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setFrameShape(QFrame.StyledPanel)

        self.open_file_btn = QPushButton()
        self.open_file_btn.clicked.connect(self.choose_mp3)

        top.addWidget(self.file_label_title)
        top.addWidget(self.file_path_label, 1)
        top.addWidget(self.open_file_btn)
        root.addLayout(top)

        # форма
        form = QFormLayout()
        form.setSpacing(8)

        self.artist_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.album_edit = QLineEdit()

        self.year_spin = QSpinBox()
        self.year_spin.setRange(0, 3000)
        self.year_spin.setSpecialValueText("")

        self.artist_label = QLabel()
        self.title_label = QLabel()
        self.album_label = QLabel()
        self.year_label = QLabel()

        form.addRow(self.artist_label, self.artist_edit)
        form.addRow(self.title_label, self.title_edit)
        form.addRow(self.album_label, self.album_edit)
        form.addRow(self.year_label, self.year_spin)

        root.addLayout(form)

        # блок обложки
        cover_top = QHBoxLayout()
        self.cover_title = QLabel()
        cover_top.addWidget(self.cover_title)
        cover_top.addStretch()

        self.select_cover_btn = QPushButton()
        self.remove_cover_btn = QPushButton()

        self.select_cover_btn.clicked.connect(self.choose_cover)
        self.remove_cover_btn.clicked.connect(self.remove_cover)

        cover_top.addWidget(self.select_cover_btn)
        cover_top.addWidget(self.remove_cover_btn)

        root.addLayout(cover_top)

        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setMinimumHeight(220)
        self.cover_label.setFrameShape(QFrame.Box)
        self.cover_label.setText("—")
        root.addWidget(self.cover_label)

        # нижние кнопки
        buttons = QHBoxLayout()
        buttons.addStretch()

        self.save_btn = QPushButton()
        self.close_btn = QPushButton()

        self.save_btn.clicked.connect(self.save_metadata)
        self.close_btn.clicked.connect(self.reject)

        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

    def _apply_texts(self):
        tr = self.loc.tr

        self.setWindowTitle(tr("edit_metadata_title"))

        self.file_label_title.setText(tr("file") + ":")
        self.open_file_btn.setText(tr("open_mp3"))

        self.artist_label.setText(tr("artist") + ":")
        self.title_label.setText(tr("title") + ":")
        self.album_label.setText(tr("album") + ":")
        self.year_label.setText(tr("year") + ":")

        self.cover_title.setText(tr("cover_preview"))
        self.select_cover_btn.setText(tr("select_cover"))
        self.remove_cover_btn.setText(tr("remove_cover"))

        self.save_btn.setText(tr("save_metadata"))
        self.close_btn.setText(tr("close"))

        if not self.file_path:
            self.file_path_label.setText("—")
        if self.cover_label.pixmap() is None:
            self.cover_label.setText(tr("no_cover_preview"))

    # ---------------- загрузка mp3 ----------------

    def choose_mp3(self):
        tr = self.loc.tr

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("open_mp3"),
            "",
            "MP3 Files (*.mp3)"
        )
        if not file_path:
            return

        self.load_mp3(file_path)

    def load_mp3(self, file_path: str):
        tr = self.loc.tr

        audio = eyed3.load(file_path)
        if audio is None:
            QMessageBox.warning(self, tr("edit_metadata_title"), tr("cannot_open_file"))
            return

        self.file_path = file_path
        self.file_path_label.setText(file_path)

        tag = audio.tag
        if tag is None:
            self.artist_edit.setText("")
            self.title_edit.setText("")
            self.album_edit.setText("")
            self.year_spin.setValue(0)
            self.cover_bytes = None
            self.cover_removed = False
            self._set_cover_preview(None)
            return

        self.artist_edit.setText(tag.artist or "")
        self.title_edit.setText(tag.title or "")
        self.album_edit.setText(tag.album or "")

        year_value = 0
        try:
            if tag.recording_date and tag.recording_date.year:
                year_value = int(tag.recording_date.year)
        except Exception:
            year_value = 0
        self.year_spin.setValue(year_value)

        self.cover_removed = False
        self.cover_bytes = self._extract_front_cover_bytes(tag)
        self._set_cover_preview(self.cover_bytes)

    def _extract_front_cover_bytes(self, tag) -> Optional[bytes]:
        try:
            for image in tag.images:
                if image.picture_type == 3:  # FRONT_COVER
                    return image.image_data
        except Exception:
            pass
        return None

    # ---------------- обложка ----------------

    def choose_cover(self):
        tr = self.loc.tr

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("choose_cover_file"),
            "",
            tr("image_files"),
        )
        if not file_path:
            return

        try:
            data = Path(file_path).read_bytes()
        except Exception as e:
            QMessageBox.warning(self, tr("edit_metadata_title"), str(e))
            return

        self.cover_bytes = data
        self.cover_removed = False
        self._set_cover_preview(data)

    def remove_cover(self):
        self.cover_bytes = None
        self.cover_removed = True
        self._set_cover_preview(None)

    def _set_cover_preview(self, image_bytes: Optional[bytes]):
        tr = self.loc.tr

        if not image_bytes:
            self.cover_label.clear()
            self.cover_label.setText(tr("no_cover_preview"))
            return

        pix = QPixmap()
        if not pix.loadFromData(image_bytes):
            self.cover_label.clear()
            self.cover_label.setText(tr("no_cover_preview"))
            return

        pix = pix.scaled(
            260, 260,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.cover_label.setPixmap(pix)

    # ---------------- сохранение ----------------

    def save_metadata(self):
        tr = self.loc.tr

        if not self.file_path:
            QMessageBox.warning(self, tr("edit_metadata_title"), tr("cannot_open_file"))
            return

        artist = self.artist_edit.text().strip()
        title = self.title_edit.text().strip()
        album = self.album_edit.text().strip()
        year = self.year_spin.value() or None

        try:
            # обычная запись полей + обложки
            write_tags(
                file_path=self.file_path,
                artist=artist,
                title=title,
                album=album,
                year=year,
                cover_bytes=self.cover_bytes if not self.cover_removed else None,
            )

            # если пользователь явно удалил обложку — eyed3 через write_tags её сам не удаляет,
            # поэтому дочищаем отдельно
            if self.cover_removed:
                self._remove_cover_from_file(self.file_path)

        except Exception as e:
            QMessageBox.critical(
                self,
                tr("edit_metadata_title"),
                f"{tr('metadata_save_error')}: {e}"
            )
            return

        QMessageBox.information(self, tr("edit_metadata_title"), tr("metadata_saved"))
        self.accept()

    def _remove_cover_from_file(self, file_path: str):
        audio = eyed3.load(file_path)
        if audio is None:
            return
        if audio.tag is None:
            return

        try:
            audio.tag.images.remove("FRONT_COVER")
        except Exception:
            pass

        audio.tag.save(version=eyed3.id3.ID3_V2_3)