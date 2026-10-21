"""Problem generation through an Ollama instance.

The model writes the problem and a machine-checkable formula for its answer (given
values + an arithmetic expression), and leaves the number itself as [[ANSWER]]. We
evaluate the formula and fill the number in, because models get the reasoning right
far more often than the arithmetic. The model's own estimate is compared with the
formula, so every AI problem is tagged verified / review / unverifiable in the GUI
instead of being trusted blindly.
"""

from __future__ import annotations

import difflib
import json
import math
import re
from typing import Callable

import httpx

from .generators import Problem
from .generators.core import norm_question, sig
from .safe_eval import safe_eval

LEVELS = {1: "easy (introductory, one step)", 2: "medium (two or three steps)",
          3: "hard (multi-step, exam level)"}

PROBLEM_SCHEMA = {
    "type": "object",
    "properties": {
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "solution": {"type": "string"},
                    "given": {"type": "object", "additionalProperties": {"type": "number"}},
                    "answer_formula": {"type": "string"},
                    "answer_value": {"type": ["number", "null"]},
                },
                "required": ["question", "answer", "solution", "given", "answer_formula", "answer_value"],
            },
        }
    },
    "required": ["problems"],
}

SYSTEM_PROMPT = """You are an expert {subject} teacher writing worksheet problems.
Return ONLY JSON matching: {{"problems": [{{"question", "answer", "solution", "given", "answer_formula", "answer_value"}}]}}.

Rules:
- Write math in LaTeX inside $...$ (inline) or $$...$$ (display) in EVERY field, including "answer" and
  "solution" (e.g. "$a = 7.1\\,\\mathrm{{m/s^2}}$"). Never use a bare $ for money; write "dollars".
- In JSON strings, backslashes must be escaped (write \\\\frac, \\\\times).
- "given": the numeric inputs of the problem as {{"name": number}} (simple identifiers like v0, m, theta_deg).
- "answer_formula": a plain arithmetic expression using only the names in "given" that computes the
  main numeric answer. Allowed: + - * / ** sqrt sin cos tan asin acos atan exp ln log10 abs pi radians degrees.
  Trig functions take RADIANS, so use sin(radians(theta_deg)). g (gravitational acceleration) may be used.
- Don't do the arithmetic yourself: the app evaluates answer_formula and puts the result wherever you
  write [[ANSWER]]. Write [[ANSWER]] in place of the main numeric result in "answer" and in the last step
  of "solution", e.g. "$h = [[ANSWER]]\\,\\mathrm{{m}}$".
- "answer": the final answer with units, concise.
- "solution": worked steps, one per line: the knowns, the equation, the equation with the numbers
  substituted, then the result with [[ANSWER]]. Don't work out intermediate numbers either.
- "answer_value": your own estimate of the main numeric answer (SI units as in "answer"); the app
  compares it with the formula.
- If the answer is not numeric (an expression, proof, explanation), set "given" to {{}},
  "answer_formula" to "" and "answer_value" to null, and write the answer in full.
- Every problem must be self-contained, unambiguous and have exactly one correct answer."""

USER_PROMPT = """Write {count} {level} {subject} problem(s) on: {topic}.
{plan}
{extra}
Remember: every problem must be about {topic}."""

PLACEHOLDER = "[[ANSWER]]"
BATCH = 5  # problems per request: short replies stay valid JSON, and each batch sees the ones before it
TOKENS_PER_PROBLEM = 500  # reply cap per problem; a typical problem takes 150-300 tokens

def _plan(topic: str, earlier: list[str]) -> str:
    """Variety instructions: the topic comes first, and the problems so far are listed to steer clear of.
    (Suggesting a setting per problem made small models drift off the topic, so the model picks its own.)"""
    lines = [f"Every problem must practice the topic above ({topic}). Make each problem different from the others: "
             "a different real-world situation and, where the topic allows, a different quantity to find."]
    if earlier:
        lines.append("These problems already exist; don't repeat their situations or their openings: "
                     + " | ".join(q[:80] for q in earlier[-25:]))
    return "\n".join(lines)


class AIError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status  # Ollama's HTTP status, when it answered with an error


async def list_models(base_url: str, timeout: float = 10) -> list[str]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{base_url.rstrip('/')}/api/tags")
        r.raise_for_status()
        return sorted(m["name"] for m in r.json().get("models", []))


_thinks: dict[tuple[str, str], bool] = {}  # (Ollama URL, model) -> whether the model has a thinking pass


async def _can_think(settings: dict) -> bool:
    """Whether the model has a thinking pass that Ollama's ``think`` flag controls (asked once per model)."""
    key = (settings["ollama_url"].rstrip("/"), settings["ollama_model"])
    if key not in _thinks:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(f"{key[0]}/api/show", json={"model": key[1]})
            r.raise_for_status()
            _thinks[key] = "thinking" in (r.json().get("capabilities") or [])
        except (httpx.HTTPError, ValueError, AttributeError):
            return False  # unknown for now (Ollama down, model missing): leave the flag out, ask next time
    return _thinks[key]


async def _chat(settings: dict, messages: list[dict], fmt, limit: int | None = None) -> str:
    """``limit`` caps the reply's length in tokens, so a model stuck repeating itself stops early
    instead of running until the timeout (not while thinking, which needs the room)."""
    payload = {
        "model": settings["ollama_model"],
        "messages": messages,
        "stream": False,
        "format": fmt,
        "options": {"temperature": float(settings.get("ollama_temperature", 0.7))},
    }
    thinking = False
    if await _can_think(settings):
        # Thinking models reason at length before answering: one problem took ~50 s instead of ~3 s.
        thinking = payload["think"] = bool(settings.get("ai_think", False))
    if limit and not thinking:
        payload["options"]["num_predict"] = limit
    url = f"{settings['ollama_url'].rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=float(settings.get("ollama_timeout", 180))) as client:
            r = await client.post(url, json=payload)
    except httpx.HTTPError as e:
        raise AIError(f"Could not reach Ollama at {settings['ollama_url']}: {e}") from e
    if r.status_code >= 400:
        raise AIError(f"Ollama returned {r.status_code}: {r.text[:300]}", status=r.status_code)
    try:
        return r.json()["message"]["content"]
    except (ValueError, KeyError, TypeError) as e:
        raise AIError(f"Ollama returned an unexpected response: {r.text[:300]}") from e


def _parse(raw: str) -> list[dict]:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Models often emit LaTeX with single backslashes (\frac) which is invalid JSON.
        data = json.loads(re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r"\\\\", raw))
    if isinstance(data, list):
        return data
    probs = data.get("problems")
    if not isinstance(probs, list):
        raise AIError("model response did not contain a 'problems' list")
    return probs


_CTRL_FIX = {"\f": "\\f", "\b": "\\b", "\t": "\\t", "\r": "\\r", "\v": "\\v"}


def _fix_latex(s: str) -> str:
    r"""Undo JSON escapes that ate a LaTeX backslash: "\frac" parses as formfeed + "rac"."""
    for ch, rep in _CTRL_FIX.items():
        s = s.replace(ch, rep)
    s = re.sub(r"\n(?=(?:eq|e\b|u\b|abla|ot|leq|geq|i\b|exists|mid|parallel)\b)", r"\\n", s)
    # An odd number of math delimiters ("$24.00 feet") would render as a literal dollar sign:
    # drop the last unpaired single "$".
    singles = [m.start() for m in re.finditer(r"(?<![\\$])\$(?!\$)", s)]
    if len(singles) % 2:
        i = singles[-1]
        s = (s[:i] + s[i + 1:]).strip()
    return _tidy_math(s)


# What follows the "n" in LaTeX commands like \\nu or \\neq — anything else after a literal
# backslash-n is a line break the model double-escaped ("15 N\\n2) Apply ...").
_N_COMMAND_REST = r"(?:u|eq|e|ot|abla|eg|i|leq|geq|mid|parallel|ewline|oindent)\b"

# Readable stand-ins for LaTeX that a model left outside $...$ in prose.
_UNICODE = {
    "times": "×", "cdot": "·", "pm": "±", "mp": "∓", "approx": "≈", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥",
    "neq": "≠", "ne": "≠", "circ": "°", "degree": "°", "infty": "∞", "to": "→", "rightarrow": "→",
    "Rightarrow": "⇒", "implies": "⇒", "pi": "π", "theta": "θ", "mu": "μ", "Delta": "Δ", "delta": "δ",
    "alpha": "α", "beta": "β", "gamma": "γ", "omega": "ω", "Omega": "Ω", "lambda": "λ", "rho": "ρ",
    "sigma": "σ", "tau": "τ", "phi": "φ", "epsilon": "ε", "sin": "sin", "cos": "cos", "tan": "tan",
    "ln": "ln", "log": "log", "left": "", "right": "", "quad": " ", "qquad": " ", "displaystyle": "",
}
_SUPERSCRIPT = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
_MATH_SPAN = re.compile(r"\$\$.+?\$\$|\$[^$]+\$", re.S)


def _latex_to_text(t: str) -> str:
    """Turn stray LaTeX in prose into readable plain text: \frac{a}{b} -> a/b, x^{2} -> x², \times -> ×."""
    def fraction(m: re.Match) -> str:
        simple = re.fullmatch(r"[\w.]+", m[1]) and re.fullmatch(r"[\w.]+", m[2])
        f = f"{m[1]}/{m[2]}" if simple else f"({m[1]})/({m[2]})"
        followed = m.end() < len(t) and (t[m.end()].isalnum() or t[m.end()] == "(")
        return f"({f})" if simple and followed else f  # "(1/2)mv²", not "1/2mv²"

    for _ in range(3):  # unwrap nested \frac / \sqrt / \text
        t = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}", fraction, t)
        t = re.sub(r"\\sqrt\{([^{}]*)\}", lambda m: f"√{m[1]}" if re.fullmatch(r"[\w.]+", m[1]) else f"√({m[1]})", t)
        t = re.sub(r"\\(?:text|mathrm|mathbf|textbf|operatorname)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\^\{?([-+]?\d+)\}?", lambda m: m[1].translate(_SUPERSCRIPT), t)
    t = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", t)
    t = re.sub(r"_\{([^{}]*)\}", r"_\1", t)
    t = re.sub(r"\\[,;:! ]", " ", t)

    def command(m: re.Match) -> str:
        name = m[1]
        out = _UNICODE.get(name, name)
        if name in ("sin", "cos", "tan", "ln", "log") and m.start() and t[m.start() - 1].isalnum():
            out = " " + out  # "mg\sin" -> "mg sin"
        return out
    t = re.sub(r"\\([A-Za-z]+)", command, t)
    return re.sub(r"\\(?!\$)", "", t)  # keep escaped dollars (\$5)


def _tidy_math(s: str) -> str:
    """Make AI text render: real line breaks, formula-only answers in $...$, and no raw LaTeX in prose."""
    s = re.sub(r"\\n(?!" + _N_COMMAND_REST + ")", "\n", s)
    if "$" not in s and re.search(r"\\[A-Za-z]+|\^|_\{", s):
        words = re.findall(r"(?<!\\)\b[A-Za-z]{4,}\b", re.sub(r"\\[A-Za-z]+(\{[^{}]*\})?", " ", s))
        if len(words) <= 2 and "\n" not in s and len(s) <= 80:
            return "$" + s.strip().replace("°", "^\\circ") + "$"  # a bare formula: "a = g\sin(45°) = 7.1"
    # Convert LaTeX that sits outside math spans.
    out, last = [], 0
    for m in _MATH_SPAN.finditer(s):
        out += [_latex_to_text(s[last:m.start()]), m[0]]
        last = m.end()
    out.append(_latex_to_text(s[last:]))
    return "".join(out)


_NUM = r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


def _numbers_in(text: str) -> list[float]:
    """Numbers appearing in an answer string, understanding LaTeX fractions and x10^n."""
    t = text.replace(",", "").replace("{,}", "").replace("−", "-")
    t = re.sub(r"\\[dt]?frac\{(%s)\}\{(%s)\}" % (_NUM, _NUM),
               lambda m: repr(float(m[1]) / float(m[2])) if float(m[2]) else m[0], t)
    # Float arithmetic only: 10 ** int(...) on a model-written exponent can overflow or hang.
    t = re.sub(r"(%s)\s*(?:\\times|\\cdot|×|x)\s*10\^\{?(-?\d{1,3})(?!\d)\}?" % _NUM,
               lambda m: repr(float(m[1]) * float(f"1e{m[2]}")), t)
    return [float(n) for n in re.findall(_NUM, t)]


def _text_matches(text: str, value: float) -> bool:
    for n in _numbers_in(text):
        for cand in (n, n / 100, n * 100):  # "75%" vs 0.75
            if math.isclose(cand, value, rel_tol=0.02, abs_tol=1e-9):
                return True
    return False


def _verify(item: dict, constants: dict[str, float] | None = None) -> tuple[str, str, float | None]:
    """Return (status, note, value); status is pass | computed | fail | error | nonnumeric, and value is
    the number to write where the problem says [[ANSWER]].

    With [[ANSWER]] the app supplies the number from the model's formula: "pass" when the model's own
    estimate agrees with it, "computed" when it doesn't (the arithmetic slipped, or the formula doesn't
    say what the model meant). Without it, passing needs three things to agree: the formula evaluated
    by us, the model's stated value, and a number in the answer text the student actually sees."""
    formula = (item.get("answer_formula") or "").strip()
    stated = item.get("answer_value")
    slot = PLACEHOLDER in str(item.get("answer", "")) + str(item.get("solution", ""))
    try:
        stated = float(stated) if stated is not None else None
    except (TypeError, ValueError):
        stated = None
    if not formula and slot:
        return "error", "No check formula, so the number shown is the model's own estimate.", stated
    if not formula or (stated is None and not slot):
        return "nonnumeric", "Non-numeric answer — not auto-checked.", None
    formula = re.sub(r"""given(?:\.(\w+)|\[['"](\w+)['"]\])""", lambda m: m[1] or m[2], formula)
    try:
        # Standard constants (e.g. the section's g) fill in names the model used but didn't list.
        computed = safe_eval(formula, {**(constants or {}), **(item.get("given") or {})})
    except Exception as e:  # noqa: BLE001
        return "error", f"Could not evaluate check formula ({e}); the problem may be missing a given value.", stated
    agrees = stated is not None and math.isclose(computed, stated, rel_tol=0.02, abs_tol=1e-9)
    if slot:
        if agrees:
            return "pass", f"Answer computed from the formula ({formula} = {computed:.4g}); the model's estimate agrees.", \
                computed
        estimate = "gave no estimate" if stated is None else f"estimated {stated:.4g}"
        return "computed", (f"Answer computed from the formula ({formula} = {computed:.4g}), but the model "
                            f"{estimate}: check that the formula fits the problem."), computed
    if not agrees:
        return "fail", f"Mismatch: stated {stated:.4g}, but {formula} = {computed:.4g}. Review this answer.", computed
    try:
        text_ok = _text_matches(str(item.get("answer", "")), computed)
    except Exception:  # noqa: BLE001  (model-written text; never let it sink the request)
        text_ok = False
    if not text_ok:
        return "fail", (f"Answer text doesn't match the check value {formula} = {computed:.4g}. "
                        "Review this answer."), computed
    return "pass", f"Formula check passed ({formula} = {computed:.4g}).", computed


# "computed" answers are kept (the number is the app's), but marked for a look at the formula.
_VERIFIED = {"pass": True, "computed": None, "fail": False, "error": None, "nonnumeric": None}
_KEEP = {"pass", "computed", "nonnumeric"}  # what strict mode keeps


def _fill(text: str, value: float | None, number: Callable[[float], str]) -> str:
    return text.replace(PLACEHOLDER, "?" if value is None else number(value))


async def _request(settings: dict, *, subject: str, topic: str, difficulty: int, count: int,
                   extra: str, plan: str = "") -> list[dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(subject=subject)},
        {"role": "user", "content": USER_PROMPT.format(
            count=count, level=LEVELS.get(difficulty, LEVELS[2]), subject=subject, topic=topic, plan=plan,
            extra=f"Additional instructions: {extra}" if extra.strip() else "")},
    ]
    try:
        raw = await _chat(settings, messages, PROBLEM_SCHEMA, limit=TOKENS_PER_PROBLEM * count + 300)
    except AIError as e:
        # Older Ollama versions only understand format="json".
        if e.status is None or ("format" not in str(e).lower() and "schema" not in str(e).lower()):
            raise
        raw = await _chat(settings, messages, "json", limit=TOKENS_PER_PROBLEM * count + 300)
    try:
        return [i for i in _parse(raw) if isinstance(i, dict) and i.get("question")]
    except (json.JSONDecodeError, AIError) as e:
        raise AIError(f"Model returned invalid JSON: {e}") from e


def _story(question: str) -> str:
    return re.sub(r"\d+(?:\.\d+)?", "#", norm_question(question))


def _setup(story: str) -> str:
    """Everything before the final question: the situation the problem describes."""
    parts = re.split(r"(?<=[.?!])\s+", story)
    return " ".join(parts[:-1]) if len(parts) > 1 else story


def _repeats(question: str, others: list[str]) -> bool:
    """A near-copy of another question: the same story with only its numbers changed, or the same
    situation with a different question about it."""
    ratio = lambda a, b: difflib.SequenceMatcher(None, a, b).ratio()  # noqa: E731
    q = _story(question)
    for o in map(_story, others):  # a different object in the same template ("a baseball is hit...") is fine
        if ratio(q, o) > 0.95 or (len(_setup(q)) > 40 and ratio(_setup(q), _setup(o)) > 0.98):
            return True
    return False


async def generate_ai(settings: dict, *, subject: str, topic: str, difficulty: int, count: int,
                      extra: str = "", constants: dict[str, float] | None = None,
                      number: Callable[[float], str] | None = None) -> list[Problem]:
    """Ask the model for problems, ``BATCH`` at a time, each with its own settings to use and the
    problems so far to steer clear of. ``number`` formats the values the app fills in for
    [[ANSWER]] (default: 3 significant figures). In strict mode, problems whose formula can't run
    (or, without [[ANSWER]], whose answer fails the check) are discarded and re-requested, up to two
    extra rounds; if the model still comes up short, the best flagged ones fill the gap for review."""
    if not settings.get("ollama_url") or not settings.get("ollama_model"):
        raise AIError("Ollama is not configured — set the URL and model on the Setup page.")
    strict = settings.get("ai_strict", True)
    number = number or (lambda v: sig(v, 3))
    kept: list[Problem] = []
    rejected: list[Problem] = []
    dupes: list[Problem] = []  # never used: a near-copy of a problem already in the section
    bad_json: AIError | None = None
    for attempt in range(3):  # extra rounds replace duplicates and (in strict mode) failed checks
        remaining = count - len(kept)  # this round asks once for the shortfall, in batches
        if remaining <= 0:
            break
        while remaining > 0:
            n = min(remaining, BATCH)
            remaining -= n
            plan = _plan(topic, [p.question for p in kept + rejected + dupes])
            try:
                items = await _request(settings, subject=subject, topic=topic, difficulty=difficulty, count=n,
                                       extra=extra, plan=plan)
            except AIError as e:
                if not str(e).startswith("Model returned invalid JSON"):
                    raise  # Ollama unreachable or refusing: retrying won't help
                bad_json = e  # one garbled batch: later rounds refill the gap
                continue
            for item in items[:n]:
                status, note, value = _verify(item, constants)
                p = Problem(question=_fix_latex(str(item["question"])),
                            answer=_fix_latex(_fill(str(item.get("answer", "")), value, number)),
                            solution=_fix_latex(_fill(str(item.get("solution", "")), value, number)),
                            source="ai", verified=_VERIFIED[status], check_note=note)
                if _repeats(p.question, [q.question for q in kept + rejected]):
                    dupes.append(p)
                else:
                    (kept if not strict or status in _KEEP else rejected).append(p)
    for p in dupes:  # last resort: a near-copy beats a missing problem
        p.check_note += " Very similar to another problem in this section; regenerate it for more variety."
    out = (kept + rejected + dupes)[:count]
    if not out:
        raise bad_json or AIError("Model returned no usable problems.")
    return out
