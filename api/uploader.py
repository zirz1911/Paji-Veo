import requests


def upload_to_catbox(filepath: str) -> str:
    """Upload image to a free host. Tries catbox → litterbox → 0x0.st."""
    return _try_catbox(filepath) or _try_litterbox(filepath) or _try_0x0(filepath)


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


def _try_0x0(filepath: str) -> str:
    """0x0.st — free file host, no auth, permanent until unused."""
    with open(filepath, "rb") as f:
        r = requests.post(
            "https://0x0.st",
            files={"file": f},
            timeout=60,
        )
    r.raise_for_status()
    url = r.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"All upload hosts failed. Last response: {url}")
    return url
