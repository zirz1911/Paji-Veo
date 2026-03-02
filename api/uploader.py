import os
import requests


def upload_to_catbox(filepath: str) -> str:
    """Upload image to a free host. Tries multiple services in order."""
    for fn in (_try_catbox, _try_litterbox, _try_tmpfiles, _try_transfersh):
        url = fn(filepath)
        if url:
            return url
    raise RuntimeError("All upload hosts failed (catbox / litterbox / tmpfiles / transfer.sh)")


def _try_catbox(filepath: str) -> str | None:
    try:
        with open(filepath, "rb") as f:
            r = requests.post(
                "https://catbox.moe/user.php",
                data={"reqtype": "fileupload", "userhash": ""},
                files={"fileToUpload": f},
                timeout=30,
            )
        if r.ok and r.text.strip().startswith("https://"):
            return r.text.strip()
    except Exception:
        pass
    return None


def _try_litterbox(filepath: str) -> str | None:
    """Litterbox = catbox temporary host (72h), no auth needed."""
    try:
        with open(filepath, "rb") as f:
            r = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": f},
                timeout=30,
            )
        if r.ok and r.text.strip().startswith("https://"):
            return r.text.strip()
    except Exception:
        pass
    return None


def _try_tmpfiles(filepath: str) -> str | None:
    """tmpfiles.org — free, 24h retention, no auth."""
    try:
        with open(filepath, "rb") as f:
            r = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=30,
            )
        if r.ok:
            data = r.json()
            page_url = data.get("data", {}).get("url", "")
            # convert https://tmpfiles.org/123/file.jpg → https://tmpfiles.org/dl/123/file.jpg
            if page_url:
                direct = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
                return direct
    except Exception:
        pass
    return None


def _try_transfersh(filepath: str) -> str | None:
    """transfer.sh — free, PUT binary, returns direct URL."""
    try:
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            r = requests.put(
                f"https://transfer.sh/{filename}",
                data=f,
                timeout=60,
            )
        if r.ok and r.text.strip().startswith("https://"):
            return r.text.strip()
    except Exception:
        pass
    return None
