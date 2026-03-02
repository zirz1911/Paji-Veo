import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict


CONFIG_DIR = Path.home() / ".paji-veo"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    api_key: str = ""
    output_folder: str = str(Path.home() / "Videos")
    max_concurrent: int = 5
    wait_minutes: int = 5
    poll_interval: int = 25

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()
