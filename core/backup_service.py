from __future__ import annotations

import shutil
from pathlib import Path


def create_backup(file_path: str | Path) -> Path:
    src = Path(file_path)

    if not src.exists():
        raise FileNotFoundError(f"Файл не найден: {src}")

    backup_path = src.with_name(f"{src.stem}.backup{src.suffix}")
    shutil.copy2(src, backup_path)
    return backup_path