"""FastAPI app: JSON API + static single-page GUI."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import random
import re
import secrets
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import storage
from .ai import AIError, generate_ai, list_models
from .generators import TOPICS, generate_set
from .generators.core import (COURSE_UNITS, COURSES, MC_COURSE, PLACE_NAMES, Ctx, norm_question, problem_key, sig,
                              supports_mc)

log = logging.getLogger("worksheets")
STATIC = Path(__file__).parent / "static"

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
# Host names the app answers to (e.g. your tailnet name), comma-separated; empty = any. Refusing
# other names stops a DNS-rebinding web page from reaching the app through your browser.
ALLOWED_HOSTS = {h.strip().lower() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()}
if ALLOWED_HOSTS:
    ALLOWED_HOSTS |= {"localhost", "127.0.0.1", "[::1]"}  # the container healthcheck
SESSION_DAYS = 30
COOKIE = "ws_session"
MAX_BODY = 10_000_000  # bytes; the largest worksheet the generator can build is about 7 MB
# Per client: failed logins allowed per window (seconds), and the pause after each failure.
LOGIN_MAX_FAILS, LOGIN_WINDOW, FAIL_DELAY = 10, 300, 1.5

app = FastAPI(title="Worksheet Generator", docs_url=None, redoc_url=None)

if not APP_PASSWORD:
    log.warning("APP_PASSWORD is not set — the app (and your Ollama instance) is open to anyone who can reach it.")
if not ALLOWED_HOSTS:
    log.warning("ALLOWED_HOSTS is not set — the app answers to any host name.")


# ------------------------------------------------------------------ auth

def _session_key() -> bytes:
    """Cookie signing key: SESSION_SECRET (else a random one kept in DATA_DIR) mixed with the password,
    so changing the password logs everyone out. Never the password alone: anyone holding a cookie
    could then test password guesses offline."""
    secret = os.environ.get("SESSION_SECRET", "").encode() or storage.session_secret()
    return hashlib.sha256(secret + b"\0" + APP_PASSWORD.encode()).digest()


SESSION_KEY = _session_key() if APP_PASSWORD else b""


def _sign(exp: int) -> str:
    mac = hmac.new(SESSION_KEY, str(exp).encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{mac}"


def _valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, _ = token.split(".", 1)
    return exp.isdigit() and int(exp) > time.time() and hmac.compare_digest(token, _sign(int(exp)))


PUBLIC_PATHS = {"/login", "/healthz"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def guard(request: Request, call_next):
    # Decide on the path the router will serve. request.url is rebuilt from the Host header, so a
    # crafted Host could make it say /login while the router serves /api/... (CVE-2026-48710).
    path = request.scope["path"]
    api = path.startswith("/api/")
    host = re.sub(r":\d+$", "", request.headers.get("host", "")).lower()
    if ALLOWED_HOSTS and host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Unknown host"}, status_code=400)
    # Browsers label requests that another site's page makes; refuse those (CSRF), password or not.
    if (api or request.method not in SAFE_METHODS) and \
            request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
        return JSONResponse({"detail": "Cross-site request refused"}, status_code=403)
    if APP_PASSWORD and path not in PUBLIC_PATHS and not _valid(request.cookies.get(COOKIE)):
        if api:
            return JSONResponse({"detail": "Not logged in"}, status_code=401)
        return RedirectResponse("/login")
    resp = await call_next(request)
    if path == "/" or path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"  # revalidate (cheap via ETag) so redeploys show up at once
    return resp


class LimitBody:
    """Refuse request bodies over MAX_BODY before anything reads them (uvicorn sets no limit)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            length = headers.get(b"content-length")
            if length is None and b"transfer-encoding" in headers:
                return await JSONResponse({"detail": "Content-Length required"}, status_code=411)(scope, receive, send)
            if length is not None and (not length.isdigit() or int(length) > MAX_BODY):
                return await JSONResponse({"detail": "Request too large"}, status_code=413)(scope, receive, send)
        await self.app(scope, receive, send)


app.add_middleware(LimitBody)  # added last, so it runs before the guard


@app.get("/login")
def login_page():
    return FileResponse(STATIC / "login.html")


_login_fails: dict[str, list[float]] = {}  # client address -> times of recent failed logins


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if not APP_PASSWORD:
        return RedirectResponse("/", status_code=303)
    now = time.time()
    for c in [c for c, times in _login_fails.items() if now - times[-1] >= LOGIN_WINDOW]:
        del _login_fails[c]
    client = request.client.host if request.client else "?"
    fails = [t for t in _login_fails.get(client, []) if now - t < LOGIN_WINDOW]
    if len(fails) >= LOGIN_MAX_FAILS:  # parallel guesses all land here: no await since the check
        return RedirectResponse("/login?error=wait", status_code=303)
    if secrets.compare_digest(password.encode(), APP_PASSWORD.encode()):
        _login_fails.pop(client, None)
        resp = RedirectResponse("/", status_code=303)
        exp = int(time.time()) + SESSION_DAYS * 86400
        resp.set_cookie(COOKIE, _sign(exp), max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https")
        return resp
    _login_fails[client] = [*fails, now]
    await asyncio.sleep(FAIL_DELAY)  # slow down guessing
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
    figures: bool | None = None  # include figures (problems read off a figure always keep theirs)
    # Multiple choice: AP Physics 1 only, built-in problems only.
    format: Literal["free", "mc"] = "free"
    course: str = Field("", max_length=20)  # the course view the section was added from, if any


class GenerateRequest(BaseModel):
    sections: list[Section] = Field(..., min_length=1, max_length=20)
    seed: int | None = None
    # Problem keys (or questions, for older worksheets) already on the worksheet outside these
    # sections, so nothing is repeated.
    avoid: list[str] = Field(default_factory=list, max_length=1000)


class ProblemRequest(Section):
    avoid: list[str] = Field(default_factory=list, max_length=1000)


def _options(sec: Section, settings: dict) -> dict:
    """Generation options for a section: its own choices, else the Setup page defaults."""
    def pick(value, key):
        return value if value is not None else settings[key]
    return {"sig": int(settings["sig_figs"]), "g": float(pick(sec.g, "physics_g")),
            "nice": bool(pick(sec.nice, "physics_nice")), "form": pick(sec.answer_form, "math_answer_form"),
            "places": int(pick(sec.places, "math_places")), "figures": bool(pick(sec.figures, "figures"))}


CONCEPTUAL = ('Write conceptual written-response questions: ask students to explain, predict or compare, '
              'using proportional reasoning where it helps ("if the distance doubles, what happens to the '
              'force?") and little or no calculation. "answer" is a 2-3 sentence model answer that states the '
              'result and the reasoning. Set "given" to {}, "answer_formula" to "", "answer_value" to null '
              'and "solution" to "".')


def _written(sec: Section) -> bool:
    """Conceptual Physics: written-response questions with a model answer, no calculation."""
    t = TOPICS.get(sec.topic)
    return bool(t and t.written) or (sec.subject == "physics" and sec.course == "conceptual")


def _ai_instructions(sec: Section, opts: dict) -> str:
    extra = sec.ai_prompt
    if _written(sec):
        return f"{CONCEPTUAL} {extra}".strip()
    if sec.subject == "physics":
        extra += f" Use g = {opts['g']:g} m/s^2 and state it in problems that need it."
        if opts["nice"]:
            extra += " Choose simple values so that every answer is a whole number or has one decimal place."
    else:
        place = PLACE_NAMES[opts["places"]]
        extra += {"exact": " Give exact answers (simplest radical form, in terms of pi) rather than decimals, "
                           "written out in full.",
                  "decimal": f" Decimal answers are rounded to the nearest {place}.",
                  "both": f" Where an answer has an exact form (radical or pi), give it, then ≈ [[ANSWER]] "
                          f"for the decimal (rounded to the nearest {place})."}[opts["form"]]
    return extra.strip()


def _number_format(sec: Section, opts: dict):
    """How the app writes the numbers it fills in for an AI answer: sig figs (physics), else rounded."""
    if sec.subject == "physics":
        return lambda v: sig(v, opts["sig"])
    return Ctx(rng=random.Random(), places=opts["places"]).rnd


async def _make(sec: Section, rng: random.Random, settings: dict, count: int, seen: set[str]) -> list[dict]:
    opts = _options(sec, settings)
    mc = sec.format == "mc"
    if mc and (sec.source != "builtin" or sec.topic not in TOPICS or not supports_mc(sec.topic)
               or sec.course not in ("", MC_COURSE)):
        raise HTTPException(400, "Multiple choice is only for built-in AP Physics 1 topics")
    if sec.source == "builtin":
        if sec.topic not in TOPICS:
            raise HTTPException(400, f"Unknown topic {sec.topic!r} (custom topics need the AI source)")
        try:
            # CPU-bound (sympy): a thread keeps the server answering other requests meanwhile.
            probs = await asyncio.to_thread(generate_set, sec.topic, sec.difficulty, count, rng,
                                            skills=sec.skills, seen=seen, mc=mc, **opts)
        except KeyError as e:
            raise HTTPException(400, str(e).strip("'\"")) from e
        return [p.to_dict() for p in probs]
    if sec.topic == "custom":
        if not sec.custom_topic.strip():
            raise HTTPException(400, "Enter a custom topic for AI generation")
        topic_text = sec.custom_topic
        if _written(sec):
            topic_text += ", for a high school Conceptual Physics class"
    elif sec.topic in TOPICS:
        t = TOPICS[sec.topic]
        chosen = [t.skills[s].label for s in sec.skills or [] if s in t.skills]
        topic_text = f"{t.name}" + (f", specifically: {'; '.join(chosen)}" if chosen else f" ({t.description})")
        topic_text += f", for a high school {' / '.join(COURSES[c][0] for c in t.courses)} class"
    else:
        raise HTTPException(400, f"Unknown topic {sec.topic!r}")
    extra = _ai_instructions(sec, opts)
    probs = await generate_ai(settings, subject="conceptual physics" if _written(sec) else sec.subject,
                              topic=topic_text, difficulty=sec.difficulty, count=count, extra=extra,
                              constants={"g": opts["g"]}, number=_number_format(sec, opts))
    for p in probs:
        p.topic = sec.topic
        p.key = problem_key(p.question)
        seen.add(p.key)
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
        except Exception:  # noqa: BLE001  (one failing section shouldn't sink the rest)
            log.exception("Generating section %d (%s) failed", i + 1, sec.topic)
            entry["error"] = "Something went wrong generating this section (details are in the server log)."
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
    ai_think: bool | None = None
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
    figures: bool | None = None

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


class SavedSection(BaseModel):
    model_config = ConfigDict(extra="allow")
    config: dict
    problems: list[dict] = []
    error: str = ""


class Worksheet(BaseModel):
    """A worksheet as the GUI saves it; fields not listed here are kept as they are."""
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    title: str = ""
    instructions: str = ""
    seed: int | None = None
    sections: list[SavedSection]


@app.post("/api/worksheets")
def save_worksheet(sheet: Worksheet):
    return storage.save_sheet(sheet.model_dump())


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
