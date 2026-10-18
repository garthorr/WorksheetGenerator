"""Multiple choice for AP Physics 1: four choices, (A)-(D), one correct.

Wrong choices come from the mistakes students make on each problem type (a missing square
root, sin for cos, forgetting a factor of ½ or the starting velocity). The specs in
``mc_specs.py`` list those mistakes per problem type; generic factor-of-2-style values only
fill in when a type runs short. Numeric choices are listed smallest to largest, as on the
AP exam, and the correct letter is spread evenly over A-D. Problems with several parts
((a), (b), ...) ask for one quantity.

Derivations (symbolic answers) get wrong expressions made by the same kinds of mistakes:
a dropped square root, sin and cos swapped, a fraction upside down, a lost factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import sympy as sp
from sympy.printing.latex import LatexPrinter

from .core import Ctx, Problem, U, is_nice, num, sig

LETTERS = "ABCD"


@dataclass
class Part:
    """One quantity a problem can ask for in multiple-choice form."""
    unit: str  # LaTeX unit of the choices ("" for none, "^\\circ" for degrees)
    wrong: list = field(default_factory=list)  # values from common mistakes, most typical first
    ask: tuple[str, str] | None = None  # (old, new): rewrite the question to ask for just this quantity
    signed: bool = False  # the quantity has a direction sign (velocity), so negative choices make sense


# variant name -> spec(given, answers, g, facts) -> {answer key: Part}
SPECS: dict[str, Callable[[dict, dict, float, dict], dict[str, Part]]] = {}


def spec(*names: str):
    def deco(fn):
        for n in names:
            SPECS[n] = fn
        return fn
    return deco


# ------------------------------------------------------------------ question rewriting

def _outside_math(q: str):
    """Indexes of characters outside $...$."""
    inside = False
    for i, ch in enumerate(q):
        if ch == "$" and (i == 0 or q[i - 1] != "\\"):
            inside = not inside
            continue
        if not inside:
            yield i


def _parts(q: str):
    """Locate an "(a) ... (b) ..." ask: (sentence start, end index of its punctuation, lead-in, clauses)."""
    outside = list(_outside_math(q))
    marks = sorted({i for i in outside for c in "abcd" if q.startswith(f"({c}) ", i)})
    if not marks or not q.startswith("(a) ", marks[0]):
        return None
    start = 0
    for i in outside:
        if i < marks[0] - 1 and q[i] in ".?" and q[i + 1] == " ":
            start = i + 2
    end = next((i for i in outside if i > marks[-1] and q[i] in ".?" and (i + 1 == len(q) or q[i + 1] == " ")), None)
    if end is None:
        return None
    clauses = []
    for j, m in enumerate(marks):
        c = q[m + 4: marks[j + 1] if j + 1 < len(marks) else end].strip()
        while True:
            for tail in (", and", " and", ","):
                if c.endswith(tail):
                    c = c[: -len(tail)].rstrip()
                    break
            else:
                break
        clauses.append(c)
    return start, end, q[start:marks[0]], clauses


def _single_ask(q: str, index: int) -> str | None:
    found = _parts(q)
    if not found:
        return None
    start, end, lead, clauses = found
    if index >= len(clauses):
        return None
    sentence = lead + clauses[index]
    sentence = sentence[0].upper() + sentence[1:]
    return q[:start] + sentence + q[end] + q[end + 1:]


def part_count(q: str) -> int:
    found = _parts(q)
    return len(found[3]) if found else 0


def givens_shown(q: str, given: dict) -> bool:
    return all(num(abs(v)) in q or sig(abs(v), 3) in q
               for k, v in given.items() if isinstance(v, (int, float)) and v != 0 and k != "n")


# ------------------------------------------------------------------ numeric choices

# Fillers when a problem type runs short of mistakes: a factor of 2 (the commonest slip), then
# factors that don't line up with the answer in an obvious 1 : 2 : 3 : 4 pattern.
FILL_BELOW = [0.5, 0.7, 0.35, 0.25, 0.6, 0.15, 0.1]
FILL_ABOVE = [2, 1.4, 2.8, 4, 1.7, 6, 10]
MISTAKE_RANGE = (0.02, 50)  # a mistake can be this far off; fillers stay within 4x


def _choose(ctx: Ctx, correct: float, part: Part) -> tuple[list[float], int]:
    """Three wrong values and the correct one, sorted, with the correct one at a random position."""
    fmt = ctx.fmt
    shown = {fmt(correct)}
    picked: list[float] = []

    def usable(v, lo=0.25, hi=4.0) -> bool:
        if v is None or isinstance(v, complex) or not math.isfinite(v):
            return False
        if correct != 0:
            if v == 0 or (not part.signed and (v < 0) != (correct < 0)):
                return False
            ratio = abs(v / correct)
            if not lo <= ratio <= hi or abs(v - correct) < 0.04 * abs(correct):
                return False
        if any(abs(v - w) < 0.04 * max(abs(v), abs(w)) for w in picked):
            return False
        if ctx.nice and is_nice(correct) and not is_nice(v):
            return False
        return fmt(v) not in shown

    def take(pool, n, side, wide=False):
        got = 0
        for v in pool:
            if got == n:
                break
            if (v < correct) == (side == "below") and usable(v, *(MISTAKE_RANGE if wide else (0.25, 4.0))):
                picked.append(v)
                shown.add(fmt(v))
                got += 1
        return got

    mistakes = [float(v) for v in part.wrong if v is not None]
    if part.signed and correct:
        mistakes.append(-correct)
    mistakes = list(dict.fromkeys(m for m in mistakes if usable(m, *MISTAKE_RANGE)))
    if correct:
        below = [correct * f for f in FILL_BELOW] if correct > 0 else [correct * f for f in FILL_ABOVE]
        above = [correct * f for f in FILL_ABOVE] if correct > 0 else [correct * f for f in FILL_BELOW]
    else:  # zero: step away by the size of the mistakes
        size = max([abs(v) for v in mistakes if v] or [1.0])
        below, above = [-size * f for f in (1, 2, 0.5, 3)], [size * f for f in (1, 2, 0.5, 3)]
    # Where the correct answer lands: k choices below it and 3 - k above. Often a position the
    # problem's own mistakes can fill, but never always the same one, so the letters even out.
    n_below = sum(m < correct for m in mistakes)
    fits = [k for k in range(4) if k <= n_below and 3 - k <= len(mistakes) - n_below]
    k = ctx.rng.choice(fits) if len(fits) > 1 and ctx.rng.random() < 0.6 else ctx.rng.randrange(4)
    if ctx.nice:  # whole-number mode: fillers rounded to two significant figures stay simple
        below += [float(f"{v:.2g}") for v in below]
        above += [float(f"{v:.2g}") for v in above]
    for side, n in (("below", k), ("above", 3 - k)):
        got = take(mistakes, n, side, wide=True)
        take(below if side == "below" else above, n - got, side)
    for pool in (mistakes, below, above):  # one side ran short: fill from anywhere
        for v in pool:
            if len(picked) == 3:
                break
            if usable(v, *(MISTAKE_RANGE if pool is mistakes else (0.25, 4.0))):
                picked.append(v)
                shown.add(fmt(v))
    if len(picked) < 3:
        raise ValueError(f"not enough distinct choices for {correct}")
    values = sorted([correct, *picked])
    return values, values.index(correct)


def _numeric(p: Problem, ctx: Ctx) -> None:
    f = p.facts
    G, A = f["given"], f["ans"]
    parts = SPECS[f["variant"]](G, A, ctx.g, f)
    keys = list(A)
    options = []
    for key, part in parts.items():
        if part.ask:
            old, new = part.ask
            q = p.question.replace(old, new) if old in p.question else None
        elif len(A) > 1:
            q = _single_ask(p.question, keys.index(key))
        else:
            q = p.question
        if q and givens_shown(q, G):
            options.append((key, part, q))
    if not options:
        raise ValueError(f"{f['variant']}: no part can be asked on its own")
    key, part, q = ctx.rng.choice(options)
    values, k = _choose(ctx, A[key], part)
    unit = U(part.unit) if part.unit and not part.unit.startswith("^") else part.unit
    p.question = q
    p.choices = [f"{ctx.fmt(v)}{unit}" for v in values]
    p.correct = k
    p.answer = f"({LETTERS[k]}) ${p.choices[k]}$"
    f["mc"] = {"key": key, "values": values}


# ------------------------------------------------------------------ symbolic choices

# Symbols a student could mix up with each other (two masses, two lengths).
LOOKALIKES = [{"m", "M", "m_1", "m_2"}, {"h", "h_1", "h_2", "r", "d", "x", "R"}, {"v", "v_0", "v_1", "v_2"}]


def _expr_mistakes(e: sp.Expr) -> list[sp.Expr]:
    """Wrong answers a student could derive, most telling first. Only one plain factor-of-2 slip,
    so the answer isn't given away as the middle of x/2, x, 2x."""
    out = []
    root = e.replace(lambda x: x.is_Pow and x.exp == sp.Rational(1, 2), lambda x: x.base)
    if root != e:
        out.append(root)  # forgot the square root
        flipped = e.replace(lambda x: x.is_Pow and x.exp == sp.Rational(1, 2) and sp.fraction(x.base)[1] != 1,
                            lambda x: sp.sqrt(1 / x.base))
        if flipped != e:
            out.append(flipped)  # the fraction under the root upside down
    swap = {fn: (sp.cos if isinstance(fn, sp.sin) else sp.sin)(fn.args[0]) for fn in e.atoms(sp.sin, sp.cos)}
    if swap:
        out.append(e.xreplace(swap))  # sin and cos swapped
    num_, den = sp.fraction(sp.together(e))
    for target in (e, num_):  # sign slip in a sum
        if isinstance(target, sp.Add):
            a, *rest = target.args
            flipped = target.func(a, *[-r for r in rest])
            out.append(flipped if target is e else flipped / den)
            break
    names = {str(s_): s_ for s_ in e.free_symbols}
    for group in LOOKALIKES:  # two masses (or lengths) mixed up
        pair = sorted(n for n in names if n in group)
        if len(pair) >= 2:
            a, b = names[pair[0]], names[pair[1]]
            out.append(e.xreplace({a: b, b: a}))
    square = e.replace(lambda x: x.is_Pow and x.exp == 2, lambda x: x.base)
    if square != e:
        out.append(square)  # forgot to square
    if den != 1:
        out.append(den / num_)  # upside down
    bare = e.replace(lambda x: x.is_Mul, lambda x: x.func(*[a for a in x.args if not (
        a.is_Number or (a.is_Pow and a.base.is_Number))]))
    if bare != e:
        out.append(bare)  # a numeric factor (the 2 in 2gh, the ½ in ½mv²) left out
    coeff = sp.Mul(*[a for a in sp.Mul.make_args(e) if a.is_Number]) if isinstance(e, sp.Mul) else 1
    out.append(e / 2 if coeff != 1 and sp.Rational(coeff).p % 2 == 0 else 2 * e)
    for s_ in sorted(e.free_symbols, key=str):  # a factor left out
        if not (e / s_).has(s_) and (e / s_).free_symbols:
            out.append(e / s_)
    return out + [e / 2, 2 * e, e**2]  # last resorts


class _Printer(LatexPrinter):
    """LaTeX for answer choices: positive terms first (sin θ − μ cos θ, not −μ cos θ + sin θ)."""

    def _as_ordered_terms(self, expr, order=None):
        return sorted(super()._as_ordered_terms(expr, order), key=lambda t: t.could_extract_minus_sign())


def _merge_roots(e: sp.Expr) -> sp.Expr:
    """√2·√(gh) -> √(2gh) and √x/2 -> √(x/4): sympy splits numbers out of roots; textbooks don't."""
    if e.is_Atom:
        return e
    args = [_merge_roots(a) for a in e.args]
    if isinstance(e, sp.Mul):
        half = sp.Rational(1, 2)
        roots = [a for a in args if a.is_Pow and a.exp in (half, -half)]
        halves = [a for a in args if a.is_Rational and a.p == 1 and a.q > 1]
        if len(roots) > 1 or (roots and halves):
            inner = sp.Mul(*[r.base ** (2 * r.exp) for r in roots], *[h**2 for h in halves])
            n, d = sp.fraction(inner)
            out = [a for a in args if a not in roots and a not in halves]
            out.append(sp.Pow(d, -half, evaluate=False) if n == 1 else sp.Pow(inner, half, evaluate=False))
            return sp.Mul(*out, evaluate=False) if len(out) > 1 else out[0]
    try:
        return e.func(*args, evaluate=False)  # don't let sympy split the merged roots again
    except TypeError:
        return e.func(*args)


# Textbook order for factors: m g h, G M m, μ m g, k x, F cos θ.
PRINT_ORDER = ["mu", "G", "M", "m", "m_1", "m_2", "k", "F", "g", "a", "v_0", "v", "v_1", "v_2", "v_f", "t", "h",
               "h_1", "h_2", "d", "x", "r", "R"]


def _factor_key(a: sp.Expr):
    base = a.base if a.is_Pow and a.base.is_Symbol else a
    if a.is_Number or a is sp.pi:
        return (0, 1 if a is sp.pi else 0)
    if base.is_Symbol:
        name = str(base)
        return (1, PRINT_ORDER.index(name) if name in PRINT_ORDER else len(PRINT_ORDER))
    if isinstance(a, (sp.sin, sp.cos, sp.tan)):
        return (3, 0)
    return (2 if a.is_Pow else 4, 0)


def _textbook_order(e: sp.Expr) -> sp.Expr:
    if e.is_Atom:
        return e
    args = [_textbook_order(a) for a in e.args]
    if isinstance(e, sp.Mul):
        return sp.Mul(*sorted(args, key=_factor_key), evaluate=False)
    try:
        return e.func(*args, evaluate=False)
    except TypeError:
        return e.func(*args)


def tex(e: sp.Expr) -> str:
    e = _textbook_order(_merge_roots(sp.factor_terms(e)))
    return _Printer({"fold_func_brackets": True, "order": "none"}).doprint(e)


def _symbolic(p: Problem, ctx: Ctx) -> None:
    f = p.facts
    answer = f["answer"]
    picked: list[sp.Expr] = []
    for w in _expr_mistakes(answer):
        if len(picked) == 3:
            break
        w = sp.simplify(w)
        if w.free_symbols and all(sp.simplify(w - x) != 0 for x in [answer, *picked]):
            picked.append(w)
    if len(picked) < 3:
        raise ValueError(f"not enough distinct wrong expressions for {answer}")
    exprs = [answer, *picked]
    order = ctx.rng.sample(range(4), 4)
    choices = [tex(exprs[i]) for i in order]
    k = order.index(0)
    p.choices, p.correct = choices, k
    p.answer = f"({LETTERS[k]}) ${sp.latex(f['unknown'])} = {choices[k]}$"
    f["mc"] = {"key": str(f["unknown"]), "exprs": [exprs[i] for i in order]}


def to_multiple_choice(p: Problem, ctx: Ctx) -> None:
    """Turn a freshly generated problem into a multiple-choice one, in place."""
    if p.facts.get("symbolic"):
        _symbolic(p, ctx)
    else:
        _numeric(p, ctx)


from . import mc_specs  # noqa: E402,F401  (registers SPECS)
