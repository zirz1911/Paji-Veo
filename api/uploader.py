import requests


CATBOX_URL = "https://catbox.moe/user.php"


def upload_to_catbox(filepath: str) -> str:
    """Upload a local file to catbox.moe and return the public URL."""
    with open(filepath, "rb") as f:
        response = requests.post(
            CATBOX_URL,
            data={"reqtype": "fileupload", "userhash": ""},
            files={"fileToUpload": f},
            timeout=120,
        )
    response.raise_for_status()
    url = response.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"catbox.moe upload failed: {url}")
    return url
