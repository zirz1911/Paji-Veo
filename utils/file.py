import re
import time
from pathlib import Path

import requests


def unique_filename(folder: str, base: str, ext: str = ".mp4") -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^\w\-]', '_', base) if base else "video"
    candidate = folder / f"{safe}{ext}"
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = folder / f"{safe}_{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def download_video(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return dest
