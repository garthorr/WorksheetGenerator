"""FastAPI app: JSON API + static single-page GUI."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import random
import secrets
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import storage
from .ai import AIError, generate_ai, list_models
from .generators import TOPICS, generate_set
from .generators.core import COURSE_UNITS, COURSES, PLACE_NAMES, norm_question

log = logging.getLogger("worksheets")
STATIC = Path(__file__).parent / "static"

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SESSION_SECRET = (os.environ.get("SESSION_SECRET") or hashlib.sha256(
    f"worksheets:{APP_PASSWORD}".encode()).hexdigest()).encode()
SESSION_DAYS = 30
COOKIE = "ws_session"

app = FastAPI(title="Worksheet Generator", docs_url=None, redoc_url=None)

if not APP_PASSWORD:
    log.warning("APP_PASSWORD is not set — the app (and your Ollama instance) is open to anyone who can reach it.")


# ------------------------------------------------------------------ auth

def _sign(exp: int) -> str:
    mac = hmac.new(SESSION_SECRET, str(exp).encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{mac}"


def _valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, _ = token.split(".", 1)
    return exp.isdigit() and int(exp) > time.time() and hmac.compare_digest(token, _sign(int(exp)))


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if not APP_PASSWORD or path in ("/login", "/healthz") or path.startswith("/static/login"):
        return await call_next(request)
    if _valid(request.cookies.get(COOKIE)):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Not logged in"}, status_code=401)
    return RedirectResponse("/login")


@app.middleware("http")
async def revalidate_static(request: Request, call_next):
    """Make browsers revalidate the GUI files (cheap via ETag) so redeploys show up immediately."""
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/login")
def login_page():
    return FileResponse(STATIC / "login.html")


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if not APP_PASSWORD or secrets.compare_digest(password.encode(), APP_PASSWORD.encode()):
        resp = RedirectResponse("/", status_code=303)
        exp = int(time.time()) + SESSION_DAYS * 86400
        resp.set_cookie(COOKIE, _sign(exp), max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https")
        return resp
    await asyncio.sleep(1.5)  # slow down guessing
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login")
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/api/session")
def session():
    return {"auth": bool(APP_PASSWORD)}


@app.get("/healthz")
def healthz():
    return {"ok": True}


# ------------------------------------------------------------------ topics

@app.get("/api/topics")
def topics():
    return [t.meta() for t in TOPICS.values()]


@app.get("/api/courses")
def courses():
    return [{"id": cid, "name": name, "subject": subject, "units": COURSE_UNITS[cid]}
            for cid, (name, subject) in COURSES.items()]


# ------------------------------------------------------------------ generation

class Section(BaseModel):
    title: str = ""
    subject: Literal["math", "physics"] = "math"
    topic: str  # a topic id, or "custom" (AI only)
    custom_topic: str = Field("", max_length=300)
    count: int = Field(5, ge=1, le=50)
    difficulty: int = Field(2, ge=1, le=3)
    source: Literal["builtin", "ai"] = "builtin"
    ai_prompt: str = Field("", max_length=1000)
    # Only these skills (ids from /api/topics); None or empty = every skill at the difficulty.
    skills: list[str] | None = Field(None, max_length=50)
    # Options below: None = use the Setup page default.
    g: Literal[9.8, 10] | None = None  # physics
    nice: bool | None = None  # physics: whole-number values
    answer_form: Literal["both", "exact", "decimal"] | None = None  # math: exact (π, radicals) and/or decimal
    places: Literal[0, 1, 2, 3] | None = None  # math: decimal places to round to


class GenerateRequest(BaseModel):
    sections: list[Section] = Field(..., min_length=1, max_length=20)
    seed: int | None = None
    # Questions already on the worksheet outside these sections, so nothing is repeated.
    avoid: list[str] = Field(default_factory=list, max_length=1000)


class ProblemRequest(Section):
    avoid: list[str] = Field(default_factory=list, max_length=1000)


def _options(sec: Section, settings: dict) -> dict:
    """Generation options for a section: its own choices, else the Setup page defaults."""
    def pick(value, key):
        return value if value is not None else settings[key]
    return {"sig": int(settings["sig_figs"]), "g": float(pick(sec.g, "physics_g")),
            "nice": bool(pick(sec.nice, "physics_nice")), "form": pick(sec.answer_form, "math_answer_form"),
            "places": int(pick(sec.places, "math_places"))}


def _ai_instructions(sec: Section, opts: dict) -> str:
    extra = sec.ai_prompt
    if sec.subject == "physics":
        extra += f" Use g = {opts['g']:g} m/s^2 and state it in problems that need it."
        if opts["nice"]:
            extra += " Choose simple values so that every answer is a whole number or has one decimal place."
    else:
        place = PLACE_NAMES[opts["places"]]
        extra += {"exact": " Give exact answers (simplest radical form, in terms of pi) rather than decimals.",
                  "decimal": f" Round decimal answers to the nearest {place}.",
                  "both": f" Where an answer has an exact form (radical or pi), give it and a decimal "
                          f"rounded to the nearest {place}."}[opts["form"]]
    return extra.strip()


async def _make(sec: Section, rng: random.Random, settings: dict, count: int, seen: set[str]) -> list[dict]:
    opts = _options(sec, settings)
    if sec.source == "builtin":
        if sec.topic not in TOPICS:
            raise HTTPException(400, f"Unknown topic {sec.topic!r} (custom topics need the AI source)")
        try:
            probs = generate_set(sec.topic, sec.difficulty, count, rng, skills=sec.skills, seen=seen, **opts)
        except KeyError as e:
            raise HTTPException(400, str(e).strip("'\"")) from e
        return [p.to_dict() for p in probs]
    if sec.topic == "custom":
        if not sec.custom_topic.strip():
            raise HTTPException(400, "Enter a custom topic for AI generation")
        topic_text = sec.custom_topic
    elif sec.topic in TOPICS:
        t = TOPICS[sec.topic]
        chosen = [t.skills[s].label for s in sec.skills or [] if s in t.skills]
        topic_text = f"{t.name}" + (f", specifically: {'; '.join(chosen)}" if chosen else f" ({t.description})")
        topic_text += f", for a high school {' / '.join(COURSES[c][0] for c in t.courses)} class"
    else:
        raise HTTPException(400, f"Unknown topic {sec.topic!r}")
    extra = _ai_instructions(sec, opts)
    probs = await generate_ai(settings, subject=sec.subject, topic=topic_text, difficulty=sec.difficulty,
                              count=count, extra=extra)
    for p in probs:
        p.topic = sec.topic
        seen.add(norm_question(p.question))
    return [p.to_dict() for p in probs]


def _section_title(sec: Section) -> str:
    if sec.title.strip():
        return sec.title.strip()
    if sec.topic == "custom":
        return sec.custom_topic.strip()[:80]
    return TOPICS[sec.topic].name if sec.topic in TOPICS else sec.topic


@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    settings = storage.load_settings()
    seed = req.seed if req.seed is not None else random.randint(1, 999_999)
    seen = {norm_question(q) for q in req.avoid}  # shared across sections: no repeats on the worksheet
    out = []
    for i, sec in enumerate(req.sections):
        entry = {"config": sec.model_dump(), "title": _section_title(sec), "problems": [], "error": ""}
        try:
            entry["problems"] = await _make(sec, random.Random(f"{seed}:{i}"), settings, sec.count, seen)
        except AIError as e:
            entry["error"] = str(e)
        except HTTPException as e:
            entry["error"] = e.detail
        out.append(entry)
    return {"seed": seed, "sections": out}


@app.post("/api/problem")
async def api_one_problem(req: ProblemRequest):
    """Generate a single replacement problem for a section, different from everything in ``avoid``."""
    try:
        probs = await _make(req, random.Random(), storage.load_settings(), 1,
                            {norm_question(q) for q in req.avoid})
    except AIError as e:
        raise HTTPException(502, str(e)) from e
    return probs[0]


# ------------------------------------------------------------------ settings & Ollama

class SettingsIn(BaseModel):
    ollama_url: str | None = None
    ollama_model: str | None = None
    ollama_temperature: float | None = Field(None, ge=0, le=2)
    ollama_timeout: int | None = Field(None, ge=10, le=1800)
    ai_strict: bool | None = None
    default_title: str | None = Field(None, max_length=200)
    header_line: str | None = Field(None, max_length=200)
    paper: Literal["letter", "a4"] | None = None
    columns: Literal[1, 2] | None = None
    work_space: Literal["none", "small", "medium", "large"] | None = None
    show_name_date: bool | None = None
    key_solutions: bool | None = None
    sig_figs: int | None = Field(None, ge=1, le=6)
    physics_g: Literal[9.8, 10] | None = None
    physics_nice: bool | None = None
    math_answer_form: Literal["both", "exact", "decimal"] | None = None
    math_places: Literal[0, 1, 2, 3] | None = None

    @field_validator("ollama_url")
    @classmethod
    def _url(cls, v):
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://")
        return v


@app.get("/api/settings")
def get_settings():
    return storage.load_settings()


@app.put("/api/settings")
def put_settings(s: SettingsIn):
    return storage.save_settings(s.model_dump(exclude_none=True))


@app.get("/api/ollama/status")
async def ollama_status(url: str | None = None):
    s = storage.load_settings()
    base = url or s["ollama_url"]
    if not base.startswith(("http://", "https://")):
        return {"ok": False, "error": "URL must start with http:// or https://", "models": []}
    try:
        models = await list_models(base)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "models": []}
    return {"ok": True, "models": models, "model_available": s["ollama_model"] in models}


# ------------------------------------------------------------------ saved worksheets

@app.get("/api/worksheets")
def worksheets():
    return storage.list_sheets()


@app.get("/api/worksheets/{sid}")
def worksheet(sid: str):
    sheet = storage.get_sheet(sid)
    if not sheet:
        raise HTTPException(404, "Not found")
    return sheet


@app.post("/api/worksheets")
async def save_worksheet(request: Request):
    body = await request.json()
    if not isinstance(body, dict) or not isinstance(body.get("sections"), list):
        raise HTTPException(400, "Invalid worksheet")
    if len(await request.body()) > 2_000_000:
        raise HTTPException(413, "Worksheet too large")
    return storage.save_sheet(body)


@app.delete("/api/worksheets/{sid}")
def delete_worksheet(sid: str):
    if not storage.delete_sheet(sid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ------------------------------------------------------------------ GUI

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
