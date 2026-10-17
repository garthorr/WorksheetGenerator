"""Registry and helpers shared by the procedural problem generators.

A *topic* is what the user picks in the GUI (e.g. "Linear equations").
Each topic has one or more *variants* per difficulty level (1 = easy,
2 = medium, 3 = hard). A variant is a function ``(ctx) -> Problem`` that
builds a problem from random values and computes the answer itself, so
answers from procedural generators are always correct by construction.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field, fields
from fractions import Fraction
from typing import Callable


@dataclass
class Problem:
    question: str  # text with inline LaTeX in $...$
    answer: str
    solution: str = ""
    topic: str = ""
    source: str = "procedural"
    # True = answer computed/verified, False = AI answer failed the check,
    # None = AI answer that could not be checked automatically.
    verified: bool | None = True
    check_note: str = ""
    # Machine-readable data for tests and the whole-number filter, never sent to the client.
    # Physics variants store {"given": {name: value}, "ans": {name: value}}.
    facts: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "facts"}


@dataclass
class Ctx:
    rng: random.Random
    difficulty: int = 2
    sig: int = 3  # significant figures for decimal answers
    g: float = 9.8  # m/s^2; many courses use 10
    nice: bool = False  # prefer whole-number givens and answers (conceptual physics)

    def fmt(self, v: float) -> str:
        """Format an answer: exactly when whole-number mode produced a simple value, else to sig figs."""
        if self.nice and is_nice(v) and (v == 0 or 1e-4 <= abs(v) < 1e6):
            return num(float(f"{v:.6g}") + 0.0)  # trims float noise; + 0.0 turns -0.0 into 0.0
        return sig(v, self.sig)

    def g_note(self) -> str:
        """Sentence telling students which g to use, when it isn't the standard 9.8."""
        return "" if self.g == 9.8 else f" Use $g = {num(self.g)}\\,\\mathrm{{m/s^2}}$."


@dataclass
class Topic:
    id: str
    subject: str  # "math" | "physics"
    category: str
    name: str
    description: str
    variants: dict[int, list[Callable[[Ctx], Problem]]] = field(default_factory=dict)

    def meta(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "levels": sorted(self.variants),
        }


TOPICS: dict[str, Topic] = {}


def topic(id: str, subject: str, category: str, name: str, description: str) -> None:
    TOPICS[id] = Topic(id, subject, category, name, description)


def variant(topic_id: str, level: int):
    def deco(fn: Callable[[Ctx], Problem]):
        TOPICS[topic_id].variants.setdefault(level, []).append(fn)
        return fn

    return deco


def _level(t: Topic, difficulty: int) -> int:
    # Use the requested level, falling back to the closest available one.
    return min(t.variants, key=lambda lv: (abs(lv - difficulty), -lv))


def _run(fn: Callable[[Ctx], Problem], topic_id: str, ctx: Ctx) -> Problem:
    p = fn(ctx)
    p.topic = topic_id
    p.facts.setdefault("variant", fn.__name__)
    p.facts.setdefault("g", ctx.g)
    return p


def norm_question(q: str) -> str:
    return re.sub(r"\s+", " ", q).strip().lower()


def is_nice_problem(p: Problem) -> bool:
    """Physics problem whose givens and answers are all simple numbers."""
    given, ans = p.facts.get("given"), p.facts.get("ans")
    if not isinstance(given, dict) or not isinstance(ans, dict):
        return True
    return all(is_nice(v) for v in [*given.values(), *ans.values()] if isinstance(v, (int, float)))


MAX_TRIES = 40


def generate_set(topic_id: str, difficulty: int, count: int, rng: random.Random, *, sig: int = 3,
                 g: float = 9.8, nice: bool = False, seen: set[str] | None = None) -> list[Problem]:
    """Generate ``count`` problems for one section.

    - Rotates through the topic's problem types so a section covers all of them.
    - Never repeats a question already in ``seen`` (shared across a worksheet; updated in place).
    - Avoids repeating an answer within the section, and in whole-number mode prefers problems
      whose givens and answers are simple, as long as the variant can produce them.
    """
    t = TOPICS[topic_id]
    nice = nice and t.subject == "physics"  # whole-number mode is a physics option
    fns = t.variants[_level(t, difficulty)]
    order = rng.sample(fns, len(fns))
    seen = set() if seen is None else seen
    answers: set[str] = set()
    out = []
    for i in range(count):
        fn = order[i % len(order)]
        best, best_score = None, -1
        for _ in range(MAX_TRIES):
            p = _run(fn, topic_id, Ctx(rng=rng, difficulty=difficulty, sig=sig, g=g, nice=nice))
            p.facts["slot"] = fns.index(fn)  # which problem type, for rotation checks
            if norm_question(p.question) in seen:
                if best is None:
                    best = p  # pool exhausted: a repeat beats an empty slot
                continue
            score = 1 + (p.answer not in answers) + (not nice or is_nice_problem(p))
            if score > best_score:
                best, best_score = p, score
            if score == 3:
                break
        seen.add(norm_question(best.question))
        answers.add(best.answer)
        out.append(best)
    return out


def generate(topic_id: str, difficulty: int, rng: random.Random, sig: int = 3, *, g: float = 9.8,
             nice: bool = False, avoid: set[str] | None = None) -> Problem:
    """One problem (e.g. to replace a single problem in a worksheet), avoiding ``avoid``."""
    seen = {norm_question(q) for q in avoid} if avoid else set()
    return generate_set(topic_id, difficulty, 1, rng, sig=sig, g=g, nice=nice, seen=seen)[0]


# ---------------------------------------------------------------- formatting

def sig(x: float, n: int = 3) -> str:
    """Format ``x`` to ``n`` significant figures as LaTeX."""
    if x == 0:
        return "0"
    x = float(f"{x:.{n - 1}e}")  # round to n sig figs first so 9.996 -> 10.0, not 10.00
    exp = math.floor(math.log10(abs(x)))
    if -3 <= exp < 5:
        decimals = n - 1 - exp
        x = round(x, decimals)  # negative decimals round large values to n sig figs
        s = f"{x:.{max(decimals, 0)}f}"
        return "-" + s[1:] if s.startswith("-") else s
    mant = round(x / 10**exp, n - 1)
    if abs(mant) >= 10:
        mant /= 10
        exp += 1
    return f"{mant:.{n - 1}f} \\times 10^{{{exp}}}"


def is_nice(v: float) -> bool:
    """Easy to work with by hand: a whole number, one decimal place, or two significant
    figures (12, 2.5, 0.013, 3400) — unlike 2.86 or 0.00228."""
    if abs(v * 10 - round(v * 10)) < 1e-6 * max(1.0, abs(v)):
        return True
    return math.isclose(v, float(f"{v:.2g}"), rel_tol=1e-9)


def num(x: float) -> str:
    """Format a given value compactly (no trailing zeros)."""
    if float(x).is_integer():
        return str(int(x))
    return f"{x:g}"


def U(unit: str) -> str:
    """LaTeX unit with a thin space, e.g. U('m/s^2')."""
    return rf"\,\mathrm{{{unit}}}"


def frac(f: Fraction, mixed: bool = False) -> str:
    f = Fraction(f)
    if f.denominator == 1:
        return str(f.numerator)
    sign = "-" if f < 0 else ""
    n, d = abs(f.numerator), f.denominator
    if mixed and n > d:
        return rf"{sign}{n // d}\tfrac{{{n % d}}}{{{d}}}"
    return rf"{sign}\frac{{{n}}}{{{d}}}"


def nz(rng: random.Random, lo: int, hi: int) -> int:
    """Random nonzero integer in [lo, hi]."""
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v


def step(rng: random.Random, lo: float, hi: float, st: float) -> float:
    """Random multiple of ``st`` in [lo, hi]; a fixed value when lo == hi (e.g. a baseball's mass)."""
    if lo == hi:
        return lo
    k = rng.randint(math.ceil(lo / st - 1e-9), math.floor(hi / st + 1e-9))
    return round(k * st, 10)
