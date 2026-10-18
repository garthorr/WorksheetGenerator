"""Problem generation through an Ollama instance.

The model writes the problem, the answer *and* a machine-checkable formula
(given values + an arithmetic expression). We evaluate that formula ourselves
and compare it with the model's stated numeric answer, so every AI problem is
tagged verified / mismatch / unverifiable in the GUI instead of being trusted
blindly.
"""

from __future__ import annotations

import json
import math
import re

import httpx

from .generators import Problem
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
- "answer": the final answer with units, concise.
- "solution": 1-3 short worked steps.
- "given": the numeric inputs of the problem as {{"name": number}} (simple identifiers like v0, m, theta_deg).
- "answer_formula": a plain arithmetic expression using only the names in "given" that computes the
  main numeric answer. Allowed: + - * / ** sqrt sin cos tan asin acos atan exp ln log10 abs pi radians degrees.
  Trig functions take RADIANS, so use sin(radians(theta_deg)). Use g = 9.8 written as a number.
- "answer_value": the main numeric answer as a number (SI units as stated in "answer").
- If the answer is not numeric (an expression, proof, explanation), set "given" to {{}},
  "answer_formula" to "" and "answer_value" to null.
- Every problem must be self-contained, unambiguous and have exactly one correct answer.
- Make problems varied; do not repeat the same scenario."""

USER_PROMPT = """Write {count} {level} {subject} problem(s) on: {topic}.
{extra}"""


class AIError(RuntimeError):
    pass


async def list_models(base_url: str, timeout: float = 10) -> list[str]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{base_url.rstrip('/')}/api/tags")
        r.raise_for_status()
        return sorted(m["name"] for m in r.json().get("models", []))


async def _chat(settings: dict, messages: list[dict], fmt) -> str:
    payload = {
        "model": settings["ollama_model"],
        "messages": messages,
        "stream": False,
        "format": fmt,
        "options": {"temperature": float(settings.get("ollama_temperature", 0.7))},
    }
    url = f"{settings['ollama_url'].rstrip('/')}/api/chat"
    async with httpx.AsyncClient(timeout=float(settings.get("ollama_timeout", 180))) as client:
        r = await client.post(url, json=payload)
        if r.status_code >= 400:
            raise AIError(f"Ollama returned {r.status_code}: {r.text[:300]}")
        return r.json()["message"]["content"]


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
    t = re.sub(r"(%s)\s*(?:\\times|\\cdot|×|x)\s*10\^\{?(-?\d+)\}?" % _NUM,
               lambda m: repr(float(m[1]) * 10 ** int(m[2])), t)
    return [float(n) for n in re.findall(_NUM, t)]


def _text_matches(text: str, value: float) -> bool:
    for n in _numbers_in(text):
        for cand in (n, n / 100, n * 100):  # "75%" vs 0.75
            if math.isclose(cand, value, rel_tol=0.02, abs_tol=1e-9):
                return True
    return False


def _verify(item: dict, constants: dict[str, float] | None = None) -> tuple[str, str]:
    """Return (status, note); status is pass | fail | error | nonnumeric.

    Passing needs three things to agree: the model's formula evaluated by us, the model's
    stated numeric value, and a number in the answer text the student actually sees."""
    formula = (item.get("answer_formula") or "").strip()
    stated = item.get("answer_value")
    if not formula or stated is None:
        return "nonnumeric", "Non-numeric answer — not auto-checked."
    formula = re.sub(r"""given(?:\.(\w+)|\[['"](\w+)['"]\])""", lambda m: m[1] or m[2], formula)
    try:
        # Standard constants (e.g. the section's g) fill in names the model used but didn't list.
        computed = safe_eval(formula, {**(constants or {}), **(item.get("given") or {})})
        stated = float(stated)
    except Exception as e:  # noqa: BLE001
        return "error", f"Could not evaluate check formula ({e}); the problem may be missing a given value."
    if not math.isclose(computed, stated, rel_tol=0.02, abs_tol=1e-9):
        return "fail", f"Mismatch: stated {stated:.4g}, but {formula} = {computed:.4g}. Review this answer."
    if not _text_matches(str(item.get("answer", "")), computed):
        return "fail", f"Answer text doesn't match the check value {formula} = {computed:.4g}. Review this answer."
    return "pass", f"Formula check passed ({formula} = {computed:.4g})."


_VERIFIED = {"pass": True, "fail": False, "error": None, "nonnumeric": None}


async def _request(settings: dict, *, subject: str, topic: str, difficulty: int, count: int,
                   extra: str) -> list[dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(subject=subject)},
        {"role": "user", "content": USER_PROMPT.format(
            count=count, level=LEVELS.get(difficulty, LEVELS[2]), subject=subject, topic=topic,
            extra=f"Additional instructions: {extra}" if extra.strip() else "")},
    ]
    try:
        raw = await _chat(settings, messages, PROBLEM_SCHEMA)
    except AIError as e:
        # Older Ollama versions only understand format="json".
        if "format" not in str(e).lower() and "schema" not in str(e).lower():
            raise
        raw = await _chat(settings, messages, "json")
    except httpx.HTTPError as e:
        raise AIError(f"Could not reach Ollama at {settings['ollama_url']}: {e}") from e
    try:
        return [i for i in _parse(raw) if isinstance(i, dict) and i.get("question")]
    except (json.JSONDecodeError, AIError) as e:
        raise AIError(f"Model returned invalid JSON: {e}") from e


async def generate_ai(settings: dict, *, subject: str, topic: str, difficulty: int, count: int,
                      extra: str = "", constants: dict[str, float] | None = None) -> list[Problem]:
    """Ask the model for problems. In strict mode, problems whose answers fail (or can't run)
    the formula check are discarded and re-requested, up to two extra rounds; if the model
    still comes up short, the best flagged problems fill the gap so the user can review them."""
    if not settings.get("ollama_url") or not settings.get("ollama_model"):
        raise AIError("Ollama is not configured — set the URL and model on the Setup page.")
    strict = settings.get("ai_strict", True)
    kept: list[Problem] = []
    rejected: list[Problem] = []
    for attempt in range(3 if strict else 1):
        need = count - len(kept)
        if need <= 0:
            break
        avoid = ""
        if kept or rejected:
            avoid = " Write new problems, different from: " + " | ".join(p.question[:80] for p in kept + rejected)
        items = await _request(settings, subject=subject, topic=topic, difficulty=difficulty, count=need,
                               extra=extra + avoid)
        for item in items[:need]:
            status, note = _verify(item, constants)
            p = Problem(question=_fix_latex(str(item["question"])),
                        answer=_fix_latex(str(item.get("answer", ""))),
                        solution=_fix_latex(str(item.get("solution", ""))),
                        source="ai", verified=_VERIFIED[status], check_note=note)
            (kept if not strict or status in ("pass", "nonnumeric") else rejected).append(p)
    out = kept + rejected[: count - len(kept)]
    if not out:
        raise AIError("Model returned no usable problems.")
    return out
