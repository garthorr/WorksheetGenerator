"""JSON-file persistence for settings and saved worksheets (in DATA_DIR)."""

from __future__ import annotations

import json
import os
import re
import secrets
import time
import uuid
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
SHEETS = DATA_DIR / "worksheets"
SETTINGS_FILE = DATA_DIR / "settings.json"
SECRET_FILE = DATA_DIR / "session_secret"

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


def session_secret() -> bytes:
    """Random key for signing login cookies, made on first run and kept in DATA_DIR."""
    _ensure()
    if SECRET_FILE.exists():
        return SECRET_FILE.read_bytes()
    key = secrets.token_hex(32).encode()
    fd = os.open(SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


# Library summaries by file path, reused while the file's mtime and size are unchanged.
_summaries: dict[str, tuple[tuple[int, int], dict | None]] = {}


def _summary(f: Path) -> dict | None:
    st = f.stat()
    stamp = (st.st_mtime_ns, st.st_size)
    cached = _summaries.get(str(f))
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        d = json.loads(f.read_text())
        summary = {"id": d["id"], "title": str(d.get("title", "")), "updated": float(d.get("updated", 0)),
                   "problems": sum(len(s.get("problems", [])) for s in d.get("sections", []))}
    except (ValueError, KeyError, TypeError, AttributeError):
        summary = None  # malformed file: leave it out of the list rather than break the whole list
    _summaries[str(f)] = (stamp, summary)
    return summary


def list_sheets() -> list[dict]:
    _ensure()
    out = []
    files = list(SHEETS.glob("*.json"))
    for f in files:
        try:
            summary = _summary(f)
        except OSError:  # deleted since the glob
            continue
        if summary:
            out.append(summary)
    for name in _summaries.keys() - {str(f) for f in files}:
        _summaries.pop(name, None)  # another request may have pruned it already
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
