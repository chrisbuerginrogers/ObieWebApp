"""
config.py — read/write interface for config.json.

Usage:
    from config import load, save

    cfg = load("audio")          # load one section
    cfg = load()                 # load entire file

    save("audio", {"device_name": "My Device", "sample_rate": 48000, ...})
    save(None, entire_dict)      # overwrite whole file

example:
    from config import load, save
    cfg = load("trigger")
    cfg["threshold"] = 8000
    save("trigger", cfg)
"""

import json
from pathlib import Path

_PATH = Path(__file__).parent / "config.json"


def load(section: str | None = None) -> dict:
    with open(_PATH) as f:
        cfg = json.load(f)
    return cfg[section] if section else cfg


def save(section: str | None, data: dict) -> None:
    cfg = load()
    if section:
        cfg[section] = data
    else:
        cfg = data
    with open(_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
