from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4


def _format_seconds(seconds: float | int | None) -> str:
    if not seconds:
        return "—"
    total = int(seconds)
    minutes = total // 60
    secs = total % 60
    hours = minutes // 60
    minutes = minutes % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


class TrackPropertiesDialog(QDialog):
    def __init__(self, file_path: str, loc, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.loc = loc

        self._build_ui()
        self._apply_texts()
        self._load_properties()

    # ---------------- UI ----------------

    def _build_ui(self):
        self.resize(620, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        def make_name_label() -> QLabel:
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            lbl.setMinimumWidth(130)
            lbl.setMaximumWidth(160)
            return lbl

        def make_value_label(selectable=False, wrap=False, expand=False) -> QLabel:
            lbl = QLabel("—")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            lbl.setWordWrap(wrap)

            if selectable:
                lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            if expand:
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            else:
                lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                lbl.setMinimumWidth(0)
                lbl.setMaximumWidth(260)

            return lbl

        # значения
        self.value_file_name = make_value_label()
        self.value_full_path = make_value_label(selectable=True, wrap=True, expand=True)
        self.value_file_size = make_value_label()
        self.value_duration = make_value_label()
        self.value_bitrate = make_value_label()
        self.value_bitrate_mode = make_value_label()
        self.value_sample_rate = make_value_label()
        self.value_channels = make_value_label()
        self.value_channel_mode = make_value_label()
        self.value_mpeg = make_value_label()
        self.value_has_cover = make_value_label()

        # подписи
        self.label_file_name = make_name_label()
        self.label_full_path = make_name_label()
        self.label_file_size = make_name_label()
        self.label_duration = make_name_label()
        self.label_bitrate = make_name_label()
        self.label_bitrate_mode = make_name_label()
        self.label_sample_rate = make_name_label()
        self.label_channels = make_name_label()
        self.label_channel_mode = make_name_label()
        self.label_mpeg = make_name_label()
        self.label_has_cover = make_name_label()

        rows = [
            (self.label_file_name, self.value_file_name),
            (self.label_full_path, self.value_full_path),
            (self.label_file_size, self.value_file_size),
            (self.label_duration, self.value_duration),
            (self.label_bitrate, self.value_bitrate),
            (self.label_bitrate_mode, self.value_bitrate_mode),
            (self.label_sample_rate, self.value_sample_rate),
            (self.label_channels, self.value_channels),
            (self.label_channel_mode, self.value_channel_mode),
            (self.label_mpeg, self.value_mpeg),
            (self.label_has_cover, self.value_has_cover),
        ]

        for row, (label_widget, value_widget) in enumerate(rows):
            grid.addWidget(label_widget, row, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
            grid.addWidget(value_widget, row, 1, alignment=Qt.AlignTop | Qt.AlignLeft)

        root.addLayout(grid)

        bottom = QHBoxLayout()
        bottom.addStretch()

        self.close_btn = QPushButton()
        self.close_btn.clicked.connect(self.accept)
        bottom.addWidget(self.close_btn)

        root.addLayout(bottom)

    def _apply_texts(self):
        tr = self.loc.tr
        self.setWindowTitle(tr("track_properties"))

        self.label_file_name.setText(tr("file") + ":")
        self.label_full_path.setText(tr("full_path") + ":")
        self.label_file_size.setText(tr("file_size") + ":")
        self.label_duration.setText(tr("duration") + ":")
        self.label_bitrate.setText(tr("bitrate") + ":")
        self.label_bitrate_mode.setText(tr("bitrate_mode") + ":")
        self.label_sample_rate.setText(tr("sample_rate") + ":")
        self.label_channels.setText(tr("channels") + ":")
        self.label_channel_mode.setText(tr("channel_mode") + ":")
        self.label_mpeg.setText(tr("mpeg_info") + ":")
        self.label_has_cover.setText(tr("embedded_cover") + ":")

        self.close_btn.setText(tr("close"))

    # ---------------- load ----------------

    def _load_properties(self):
        tr = self.loc.tr

        if not self.file_path or not os.path.isfile(self.file_path):
            QMessageBox.warning(self, tr("track_properties"), tr("cannot_open_file"))
            return

        self.value_file_name.setText(os.path.basename(self.file_path))
        self.value_full_path.setText(self.file_path)

        try:
            size_bytes = os.path.getsize(self.file_path)
            self.value_file_size.setText(_format_size(size_bytes))
        except Exception:
            self.value_file_size.setText("—")

        try:
            audio = MutagenFile(self.file_path)
        except Exception:
            audio = None

        if audio is None:
            QMessageBox.warning(self, tr("track_properties"), tr("cannot_open_file"))
            return

        info = getattr(audio, "info", None)

        # duration
        duration = getattr(info, "length", None)
        self.value_duration.setText(_format_seconds(duration))

        # bitrate
        self.value_bitrate.setText(self._extract_bitrate_text(info))

        # bitrate mode
        self.value_bitrate_mode.setText(self._extract_bitrate_mode(info))

        # sample rate
        sample_rate = getattr(info, "sample_rate", None)
        if sample_rate:
            self.value_sample_rate.setText(f"{sample_rate} Hz")
        else:
            self.value_sample_rate.setText("—")

        # channels
        channels_value = getattr(info, "channels", None)
        if channels_value:
            self.value_channels.setText(str(channels_value))
        else:
            self.value_channels.setText("—")

        # channel mode
        self.value_channel_mode.setText(self._extract_channel_mode(info))

        # format / codec info
        self.value_mpeg.setText(self._extract_codec_text(audio, info))

        # cover
        has_cover = self._has_cover(audio)
        self.value_has_cover.setText(tr("yes") if has_cover else tr("no"))

    # ---------------- helpers ----------------

    def _extract_bitrate_text(self, info) -> str:
        if info is None:
            return "—"

        bitrate = getattr(info, "bitrate", None)
        if bitrate:
            try:
                return f"{int(bitrate / 1000)} kbps"
            except Exception:
                return "—"

        return "—"

    def _extract_bitrate_mode(self, info) -> str:
        if info is None:
            return "—"

        # У mutagen нет полностью унифицированного поля для всех форматов,
        # поэтому для MP3 пробуем угадать по наличию bitrate_mode / encoder_info
        bitrate_mode = getattr(info, "bitrate_mode", None)
        if bitrate_mode is not None:
            text = str(bitrate_mode).upper()
            if "VBR" in text:
                return "VBR"
            if "CBR" in text:
                return "CBR"
            return text

        return "—"

    def _extract_channel_mode(self, info) -> str:
        if info is None:
            return "—"

        channels = getattr(info, "channels", None)
        if channels == 1:
            return "Mono"
        if channels == 2:
            return "Stereo"
        if channels:
            return f"{channels} ch"

        return "—"

    def _extract_codec_text(self, audio, info) -> str:
        if audio is None:
            return "—"

        ext = os.path.splitext(self.file_path)[1].lower().lstrip(".")
        codec_parts = []

        if ext:
            codec_parts.append(ext.upper())

        # для mp3 можно дополнительно показать MPEG/layer, если mutagen это знает
        version = getattr(info, "version", None)
        layer = getattr(info, "layer", None)

        if version:
            codec_parts.append(str(version))
        if layer:
            codec_parts.append(f"Layer {layer}")

        return ", ".join(codec_parts) if codec_parts else "—"

    def _has_cover(self, audio) -> bool:
        if audio is None:
            return False

        try:
            # MP3 / ID3
            if isinstance(audio.tags, ID3):
                for key in audio.tags.keys():
                    if str(key).startswith("APIC"):
                        return True

            # FLAC
            if isinstance(audio, FLAC):
                if getattr(audio, "pictures", None):
                    return len(audio.pictures) > 0

            # MP4 / M4A
            if isinstance(audio, MP4):
                tags = audio.tags or {}
                if "covr" in tags and tags["covr"]:
                    return True

            # OGG / Opus / Vorbis — некоторые файлы содержат coverart metadata block
            tags = getattr(audio, "tags", None)
            if tags:
                lowered = {str(k).lower() for k in tags.keys()}
                if "metadata_block_picture" in lowered or "coverart" in lowered:
                    return True

        except Exception:
            pass

        return False