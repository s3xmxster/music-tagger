from __future__ import annotations

from typing import Optional

import requests

from core.constants import DEFAULT_NETWORK_TIMEOUT


def download_cover(release_id: str, timeout: int = DEFAULT_NETWORK_TIMEOUT) -> Optional[bytes]:
    if not release_id:
        return None

    url = f"https://coverartarchive.org/release/{release_id}/front"

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if response.status_code == 200 and response.content:
            return response.content
    except Exception:
        return None

    return None