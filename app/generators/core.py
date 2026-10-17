"""Registry and helpers shared by the procedural problem generators.

A *topic* is what the user picks in the GUI (e.g. "Quadratic equations"). It belongs to
one or more *courses* and is made of named *skills* (e.g. "Factor ax² + bx + c"). Each
skill is available at one or more difficulty levels (1 = easy, 2 = medium, 3 = hard)
through *variants*: functions ``(ctx) -> Problem`` that build a problem from random
values and compute the answer themselves, so built-in answers are correct by construction.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field, fields
from fractions import Fraction
from typing import Callable

# Courses in catalog order: id -> (name, subject)
COURSES = {
    "alg1": ("Algebra 1", "math"),
    "geo": ("Geometry", "math"),
    "alg2": ("Algebra 2", "math"),
    "precalc": ("Precalculus", "math"),
    "calc": ("Beyond Precalculus", "math"),
    "conceptual": ("Conceptual Physics", "physics"),
    "ap1": ("AP Physics 1", "physics"),
}

# Teaching order of each course's units (topic categories) for the catalog.
COURSE_UNITS = {
    "alg1": ["Foundations", "Equations", "Lines & coordinate geometry", "Systems of equations", "Exponents",
             "Quadratics", "Statistics"],
    "geo": ["Lines & coordinate geometry", "Right triangles", "Area & perimeter"],
    "alg2": ["Systems of equations", "Quadratics", "Exponents", "Exponentials & logarithms"],
    "precalc": ["Exponentials & logarithms", "Right triangles", "Limits"],
    "calc": ["Limits", "Calculus"],
    "conceptual": ["Kinematics", "Forces & dynamics", "Momentum", "Work, energy & power",
                   "Circular motion & gravitation", "Fluids", "Heat", "Waves & sound", "Electricity",
                   "Light & optics"],
    # College Board AP Physics 1 unit order (circular motion and gravitation are part of Unit 2)
    "ap1": ["Kinematics", "Forces & dynamics", "Circular motion & gravitation", "Work, energy & power",
            "Momentum", "Fluids"],
}

PLACE_NAMES = {0: "whole number", 1: "tenth", 2: "hundredth", 3: "thousandth"}


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
    skill: str = ""
    # Machine-readable data for tests and the whole-number filter, never sent to the client.
    # Physics variants store {"given": {name: value}, "ans": {name: value}}.
    facts: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "facts"}


@dataclass
class Ctx:
    rng: random.Random
    difficulty: int = 2
    sig: int = 3  # physics: significant figures for decimal answers
    g: float = 9.8  # physics: m/s^2; many courses use 10
    nice: bool = False  # physics: prefer whole-number givens and answers (conceptual physics)
    form: str = "both"  # math: "exact" (π, radicals), "decimal", or "both"
    places: int = 1  # math: round decimal answers to this many decimal places

    # ---- physics
    def fmt(self, v: float) -> str:
        """Format an answer: exactly when whole-number mode produced a simple value, else to sig figs."""
        if self.nice and is_nice(v) and (v == 0 or 1e-4 <= abs(v) < 1e6):
            return num(float(f"{v:.6g}") + 0.0)  # trims float noise; + 0.0 turns -0.0 into 0.0
        return sig(v, self.sig)

    def g_note(self) -> str:
        """Sentence telling students which g to use, when it isn't the standard 9.8."""
        return "" if self.g == 9.8 else f" Use $g = {num(self.g)}\\,\\mathrm{{m/s^2}}$."

    # ---- math
    def rnd(self, v: float) -> str:
        """A decimal answer rounded to the chosen place (math classes round to a place, not sig figs)."""
        s = f"{v:.{self.places}f}"
        return s[1:] if re.fullmatch(r"-0\.?0*", s) else s

    def round_note(self) -> str:
        return f" Round to the nearest {PLACE_NAMES[self.places]}."

    def form_note(self, exact_phrase: str) -> str:
        """Instruction for an answer that has an exact form, e.g. exact_phrase = "in terms of $\\pi$"."""
        place = PLACE_NAMES[self.places]
        if self.form == "exact":
            return f" Give the exact answer {exact_phrase}."
        if self.form == "decimal":
            return f" Round to the nearest {place}."
        return f" Give the exact answer {exact_phrase} and a decimal rounded to the nearest {place}."

    def exact_or_decimal(self, exact_tex: str, value: float, unit: str = "") -> str:
        """Answer text in the chosen form (without $ delimiters)."""
        u = U(unit) if unit else ""
        if self.form == "exact":
            return f"{exact_tex}{u}"
        if self.form == "decimal":
            return f"\\approx {self.rnd(value)}{u}"
        return f"{exact_tex} \\approx {self.rnd(value)}{u}"


@dataclass
class Variant:
    fn: Callable[[Ctx], Problem]
    skill: str  # skill id


@dataclass
class Skill:
    id: str
    label: str
    levels: list[int] = field(default_factory=list)


@dataclass
class Topic:
    id: str
    subject: str  # "math" | "physics"
    category: str  # unit within the course, e.g. "Right triangles"
    name: str
    description: str
    courses: list[str]
    # Answer options the GUI should offer: exact/decimal choice, and a rounding place.
    exact_forms: bool = False
    rounding: bool = False
    variants: dict[int, list[Variant]] = field(default_factory=dict)
    skills: dict[str, Skill] = field(default_factory=dict)

    def meta(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "courses": self.courses,
            "exact_forms": self.exact_forms,
            "rounding": self.rounding,
            "levels": sorted(self.variants),
            "skills": [{"id": s.id, "label": s.label, "levels": sorted(s.levels)} for s in self.skills.values()],
        }


TOPICS: dict[str, Topic] = {}


def topic(id: str, subject: str, category: str, name: str, description: str, *, courses: list[str],
          exact_forms: bool = False, rounding: bool = False) -> None:
    assert courses and all(c in COURSES and COURSES[c][1] == subject for c in courses), (id, courses)
    TOPICS[id] = Topic(id, subject, category, name, description, courses, exact_forms, rounding)


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def variant(topic_id: str, level: int, skill: str):
    """Register a variant for ``skill`` (a teacher-facing label) at ``level``. Registering the
    same label at several levels makes one skill whose difficulty follows the section's."""
    def deco(fn: Callable[[Ctx], Problem]):
        t = TOPICS[topic_id]
        sid = slug(skill)
        s = t.skills.setdefault(sid, Skill(sid, skill))
        if level not in s.levels:
            s.levels.append(level)
        t.variants.setdefault(level, []).append(Variant(fn, sid))
        return fn

    return deco


def _nearest(levels, difficulty: int) -> int:
    # The requested level, falling back to the closest available one (harder on ties).
    return min(levels, key=lambda lv: (abs(lv - difficulty), -lv))


def variants_for(topic_id: str, difficulty: int, skills: list[str] | None = None) -> list[Variant]:
    """Variants a section draws from: every skill at the difficulty, or just the chosen
    skills, each at the level nearest the difficulty."""
    t = TOPICS[topic_id]
    if not skills:
        return t.variants[_nearest(t.variants, difficulty)]
    unknown = [s for s in skills if s not in t.skills]
    if unknown:
        raise KeyError(f"unknown skill(s) for {t.name}: {', '.join(unknown)}")
    out = []
    for sid in dict.fromkeys(skills):  # keep order, drop duplicates
        level = _nearest(t.skills[sid].levels, difficulty)
        out += [v for v in t.variants[level] if v.skill == sid]
    return out


def _run(v: Variant, topic_id: str, ctx: Ctx) -> Problem:
    p = v.fn(ctx)
    p.topic, p.skill = topic_id, v.skill
    p.facts.setdefault("variant", v.fn.__name__)
    p.facts.setdefault("g", ctx.g)
    p.facts.setdefault("form", ctx.form)
    p.facts.setdefault("places", ctx.places)
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
                 g: float = 9.8, nice: bool = False, form: str = "both", places: int = 1,
                 skills: list[str] | None = None, seen: set[str] | None = None) -> list[Problem]:
    """Generate ``count`` problems for one section.

    - Draws from every skill at the difficulty, or only the chosen ``skills``.
    - Rotates through the problem types so a section covers all of them.
    - Never repeats a question already in ``seen`` (shared across a worksheet; updated in place).
    - Avoids repeating an answer within the section, and in whole-number mode prefers problems
      whose givens and answers are simple, as long as the variant can produce them.
    """
    t = TOPICS[topic_id]
    nice = nice and t.subject == "physics"  # whole-number mode is a physics option
    pool = variants_for(topic_id, difficulty, skills)
    order = rng.sample(pool, len(pool))
    seen = set() if seen is None else seen
    answers: set[str] = set()
    out = []
    for i in range(count):
        v = order[i % len(order)]
        best, best_score = None, -1
        for _ in range(MAX_TRIES):
            ctx = Ctx(rng=rng, difficulty=difficulty, sig=sig, g=g, nice=nice, form=form, places=places)
            p = _run(v, topic_id, ctx)
            p.facts["slot"] = pool.index(v)  # which problem type, for rotation checks
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


def generate(topic_id: str, difficulty: int, rng: random.Random, avoid: set[str] | None = None,
             **options) -> Problem:
    """One problem (e.g. to replace a single problem in a worksheet), avoiding ``avoid``."""
    seen = {norm_question(q) for q in avoid} if avoid else set()
    return generate_set(topic_id, difficulty, 1, rng, seen=seen, **options)[0]


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
