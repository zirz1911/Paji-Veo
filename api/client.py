import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import requests

from utils.file import unique_filename, download_video


BASE_URL = "https://kie.ai/api/v1"


@dataclass
class VeoTask:
    prompt: str
    image_url: Optional[str] = None
    video_name: Optional[str] = None
    model: str = "veo3_fast"
    generation_type: str = "FIRST_AND_LAST_FRAMES_2_VIDEO"
    aspect_ratio: str = "9:16"
    seed: Optional[int] = None
    watermark: Optional[str] = None
    enable_translation: bool = True
    # runtime fields
    task_id: Optional[str] = None
    status: str = "pending"
    local_image_path: Optional[str] = None  # set if user picked a local file
    uid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


class VeoClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def generate(self, task: VeoTask) -> str:
        """Submit a generation request. Returns taskId."""
        payload: dict = {
            "model": task.model,
            "prompt": task.prompt,
            "generationType": task.generation_type,
            "aspectRatio": task.aspect_ratio,
            "enableTranslation": task.enable_translation,
        }
        if task.seed is not None:
            payload["seed"] = task.seed
        if task.watermark:
            payload["watermark"] = task.watermark

        if task.image_url:
            if task.generation_type == "FIRST_AND_LAST_FRAMES_2_VIDEO":
                payload["imageUrls"] = [task.image_url, task.image_url]
            elif task.generation_type == "IMAGE_2_VIDEO":
                payload["imageUrls"] = [task.image_url]
            # TEXT_2_VIDEO — no imageUrls

        resp = self.session.post(f"{BASE_URL}/veo/generate", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("data", {}).get("taskId") or data.get("taskId")
        if not task_id:
            raise RuntimeError(f"No taskId in response: {data}")
        return task_id

    def get_1080p(self, task_id: str) -> Optional[str]:
        """Poll once for the 1080P video URL. Returns URL or None if not ready."""
        resp = self.session.get(
            f"{BASE_URL}/veo/get-1080p-video",
            params={"taskId": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("resultUrl") or data.get("resultUrl")

    def run_task(
        self,
        task: VeoTask,
        output_folder: str,
        wait_minutes: int,
        poll_interval: int,
        on_status: Callable[[str], None],
    ) -> Path:
        """Full flow: generate → wait → poll → download. Returns saved Path."""
        on_status("generating")
        task_id = self.generate(task)
        task.task_id = task_id

        on_status(f"waiting {wait_minutes}m for 1080P")
        time.sleep(wait_minutes * 60)

        on_status("polling")
        result_url = None
        max_attempts = 20
        for attempt in range(max_attempts):
            result_url = self.get_1080p(task_id)
            if result_url:
                break
            on_status(f"polling ({attempt + 1}/{max_attempts})")
            time.sleep(poll_interval)

        if not result_url:
            raise RuntimeError("1080P not ready after max polling attempts")

        base_name = task.video_name or f"video_{task.uid}"
        dest = unique_filename(output_folder, base_name)
        on_status("downloading")
        download_video(result_url, dest)
        on_status(f"done:{dest.name}")
        return dest
