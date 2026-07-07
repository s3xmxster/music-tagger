from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, download_cover_default: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(360, 140)

        self.cover_checkbox = QCheckBox("Загружать и встраивать обложку")
        self.cover_checkbox.setChecked(download_cover_default)

        form = QFormLayout()
        form.addRow("Обложка:", self.cover_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addStretch(1)
        root.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            "download_cover": self.cover_checkbox.isChecked()
        }