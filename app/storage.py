"""JSON-file persistence for settings and saved worksheets (in DATA_DIR)."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
SHEETS = DATA_DIR / "worksheets"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    # Ollama
    "ollama_url": os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
    "ollama_model": os.environ.get("OLLAMA_MODEL", "qwen2.5:14b"),
    "ollama_temperature": 0.7,
    "ollama_timeout": 240,
    "ai_strict": True,  # drop & retry AI problems that fail the answer check
    # Worksheet defaults
    "default_title": "Practice Worksheet",
    "header_line": "",  # e.g. teacher / class name
    "paper": "letter",  # letter | a4
    "columns": 1,
    "work_space": "medium",  # none | small | medium | large
    "show_name_date": True,
    "key_solutions": True,
    "sig_figs": 3,
    "figures": True,  # draw figures for problems that have them
    # Physics defaults (each section can override)
    "physics_g": 9.8,  # 9.8 or 10 m/s^2
    "physics_nice": False,  # whole-number givens/answers, e.g. for conceptual physics
    # Math defaults (each section can override)
    "math_answer_form": "both",  # exact (π, radicals) | decimal | both
    "math_places": 1,  # round decimal answers to the nearest tenth
}

_ID = re.compile(r"^[a-f0-9]{32}$")


def _ensure() -> None:
    SHEETS.mkdir(parents=True, exist_ok=True)


def _write(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def load_settings() -> dict:
    _ensure()
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        s.update({k: v for k, v in json.loads(SETTINGS_FILE.read_text()).items() if k in DEFAULT_SETTINGS})
    return s


def save_settings(new: dict) -> dict:
    s = load_settings()
    s.update({k: v for k, v in new.items() if k in DEFAULT_SETTINGS})
    _write(SETTINGS_FILE, s)
    return s


def list_sheets() -> list[dict]:
    _ensure()
    out = []
    for f in SHEETS.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        out.append({"id": d["id"], "title": d.get("title", ""), "updated": d.get("updated", 0),
                    "problems": sum(len(s.get("problems", [])) for s in d.get("sections", []))})
    return sorted(out, key=lambda d: d["updated"], reverse=True)


def get_sheet(sheet_id: str) -> dict | None:
    if not _ID.match(sheet_id):
        return None
    f = SHEETS / f"{sheet_id}.json"
    return json.loads(f.read_text()) if f.exists() else None


def save_sheet(sheet: dict) -> dict:
    _ensure()
    sid = sheet.get("id")
    if not sid or not _ID.match(sid):
        sid = uuid.uuid4().hex
    sheet = {**sheet, "id": sid, "updated": time.time()}
    _write(SHEETS / f"{sid}.json", sheet)
    return sheet


def delete_sheet(sheet_id: str) -> bool:
    if not _ID.match(sheet_id):
        return False
    f = SHEETS / f"{sheet_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False
