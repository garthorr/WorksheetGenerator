"""Procedural math problem generators. Answers are computed, never guessed, and every
problem comes with worked steps written the way the course shows its work."""

from __future__ import annotations

import math
import statistics
from fractions import Fraction

import sympy as sp

from . import drawings as draw
from .core import Ctx, Problem, U, frac, num, nz, sig, steps, topic, variant

x, y = sp.symbols("x y")
L = sp.latex


def pi_tex(const, coef) -> str:
    r"""const + coef*pi written the way textbooks do, e.g. 1290 + \frac{225}{2}\pi."""
    c = sp.Rational(coef)
    pi = f"{'' if c == 1 else L(c)}\\pi"
    return f"{const} + {pi}" if const else pi


def split_square(n: int) -> tuple[int, int]:
    """n = k^2 * m with m square-free: returns (k, m)."""
    k = math.isqrt(n)
    while n % (k * k):
        k -= 1
    return k, n // (k * k)


def pm_tex(a: int, b: int, disc: int) -> tuple[str, tuple[int, int, int, int]]:
    """Roots of ax^2 + bx + c with discriminant ``disc`` as one reduced "(B ± K√M)/D" expression."""
    k, m = split_square(disc)
    B, K, D = -b, k, 2 * a
    g = math.gcd(math.gcd(B, K), D)
    B, K, D = B // g, K // g, D // g
    rad = f"{'' if K == 1 else K}\\sqrt{{{m}}}"
    if D == 1:
        tex = f"{B} \\pm {rad}" if B else f"\\pm {rad}"
    else:
        tex = f"\\frac{{{B} \\pm {rad}}}{{{D}}}" if B else f"\\pm \\frac{{{rad}}}{{{D}}}"
    return tex, (B, K, m, D)


def radical_steps(n: int) -> str:
    """'√72 = 6√2' when the radical simplifies, else ''."""
    k, m = split_square(n)
    return f"Simplify: $\\sqrt{{{n}}} = \\sqrt{{{k * k}}}\\sqrt{{{m}}} = {k}\\sqrt{{{m}}}$" if k > 1 and m > 1 else ""


def paren(v) -> str:
    """Wrap negative numbers in parentheses for substitution steps."""
    s = frac(Fraction(v)) if not isinstance(v, str) else v
    return f"({s})" if s.startswith("-") else s


# ======================================================== Arithmetic

topic("add_sub", "math", "Foundations", "Addition & subtraction",
      "Whole-number addition and subtraction; negatives at higher levels.", courses=['alg1'])


def _add_sub(ctx: Ctx, lo: int, hi: int) -> Problem:
    a, b = ctx.rng.randint(lo, hi), ctx.rng.randint(lo, hi)
    if ctx.rng.random() < 0.5:
        if lo >= 0 and b > a:
            a, b = b, a
        return Problem(f"$${a} - {b}$$".replace("- -", "+ "),
                       f"${a - b}$")
    q = f"{a} + {b}".replace("+ -", "- ")
    return Problem(f"$${q}$$", f"${a + b}$")


variant("add_sub", 1, "Add & subtract")(lambda c: _add_sub(c, 1, 20))
variant("add_sub", 2, "Add & subtract")(lambda c: _add_sub(c, 10, 999))
variant("add_sub", 3, "Add & subtract")(lambda c: _add_sub(c, -999, 9999))

topic("mul_div", "math", "Foundations", "Multiplication & division",
      "Times tables up to multi-digit products; exact division.", courses=['alg1'])


def _mul_div(ctx: Ctx, a_rng: tuple[int, int], b_rng: tuple[int, int]) -> Problem:
    a, b = ctx.rng.randint(*a_rng), ctx.rng.randint(*b_rng)
    if ctx.rng.random() < 0.5:
        return Problem(rf"$${a} \times {b}$$", f"${a * b}$")
    return Problem(rf"$${a * b} \div {b}$$", f"${a}$", f"Check: ${a} \\times {b} = {a * b}$")


variant("mul_div", 1, "Multiply & divide")(lambda c: _mul_div(c, (1, 10), (1, 10)))
variant("mul_div", 2, "Multiply & divide")(lambda c: _mul_div(c, (11, 99), (2, 9)))
variant("mul_div", 3, "Multiply & divide")(lambda c: _mul_div(c, (100, 999), (11, 99)))

topic("order_ops", "math", "Foundations", "Order of operations",
    "Evaluate expressions with parentheses, exponents, × and ÷.", courses=['alg1'])

F = frac  # short name for the step text below

# (LaTeX template, value, steps): steps follow PEMDAS one operation at a time
_OPS_TEMPLATES = {
    1: [
        (r"{a} + {b} \times {c}", lambda a, b, c, d, e: a + b * c,
         lambda a, b, c, d, e: [f"Multiply first: ${b} \\times {c} = {F(b * c)}$", f"Then add: ${a} + {F(b * c)} = {F(a + b * c)}$"]),
        (r"({a} + {b}) \times {c}", lambda a, b, c, d, e: (a + b) * c,
         lambda a, b, c, d, e: [f"Parentheses first: ${a} + {b} = {F(a + b)}$",
                                f"Then multiply: ${F(a + b)} \\times {c} = {F((a + b) * c)}$"]),
        (r"{a} \times {b} - {c}", lambda a, b, c, d, e: a * b - c,
         lambda a, b, c, d, e: [f"Multiply first: ${a} \\times {b} = {F(a * b)}$",
                                f"Then subtract: ${F(a * b)} - {c} = {F(a * b - c)}$"]),
    ],
    2: [
        (r"({a} + {b}) \times {c} - {d}", lambda a, b, c, d, e: (a + b) * c - d,
         lambda a, b, c, d, e: [f"Parentheses: ${a} + {b} = {F(a + b)}$", f"Multiply: ${F(a + b)} \\times {c} = {F((a + b) * c)}$",
                                f"Subtract: ${F((a + b) * c)} - {d} = {F((a + b) * c - d)}$"]),
        (r"{a} \times {b} - {c} \times {d}", lambda a, b, c, d, e: a * b - c * d,
         lambda a, b, c, d, e: [f"Multiply: ${a} \\times {b} = {F(a * b)}$ and ${c} \\times {d} = {F(c * d)}$",
                                f"Subtract: ${F(a * b)} - {F(c * d)} = {F(a * b - c * d)}$"]),
        (r"{a} + {b}^2 \times {c}", lambda a, b, c, d, e: a + b**2 * c,
         lambda a, b, c, d, e: [f"Exponent: ${b}^2 = {F(b * b)}$", f"Multiply: ${F(b * b)} \\times {c} = {F(b * b * c)}$",
                                f"Add: ${a} + {F(b * b * c)} = {F(a + b * b * c)}$"]),
        (r"{a} \div {b} + {c} \times {d}", lambda a, b, c, d, e: a / b + c * d,
         lambda a, b, c, d, e: [f"Divide and multiply left to right: ${a} \\div {b} = {F(a / b)}$, ${c} \\times {d} = {F(c * d)}$",
                                f"Add: ${F(a / b)} + {F(c * d)} = {F(a / b + c * d)}$"]),
    ],
    3: [
        (r"{a} - {b} \times ({c} + {d})^2 \div {e}", lambda a, b, c, d, e: a - b * (c + d) ** 2 / e,
         lambda a, b, c, d, e: [f"Parentheses: ${c} + {d} = {F(c + d)}$", f"Exponent: ${F(c + d)}^2 = {F((c + d) ** 2)}$",
                                f"Multiply and divide left to right: ${b} \\times {F((c + d) ** 2)} \\div {e} = "
                                f"{F(b * (c + d) ** 2 / e)}$",
                                f"Subtract: ${a} - {F(b * (c + d) ** 2 / e)} = {F(a - b * (c + d) ** 2 / e)}$"]),
        (r"\left[{a} + ({b} - {c})^2\right] \div {d} - {e}", lambda a, b, c, d, e: (a + (b - c) ** 2) / d - e,
         lambda a, b, c, d, e: [f"Inner parentheses: ${b} - {c} = {F(b - c)}$, squared: ${F((b - c) ** 2)}$",
                                f"Brackets: ${a} + {F((b - c) ** 2)} = {F(a + (b - c) ** 2)}$",
                                f"Divide: ${F(a + (b - c) ** 2)} \\div {d} = {F((a + (b - c) ** 2) / d)}$",
                                f"Subtract: ${F((a + (b - c) ** 2) / d)} - {e} = {F((a + (b - c) ** 2) / d - e)}$"]),
        (r"{a}^2 - {b} \times ({c} - {d} \div {e})", lambda a, b, c, d, e: a**2 - b * (c - d / e),
         lambda a, b, c, d, e: [f"Inside the parentheses, divide first: ${d} \\div {e} = {F(d / e)}$, "
                                f"then ${c} - {F(d / e)} = {F(c - d / e)}$",
                                f"Exponent: ${a}^2 = {F(a * a)}$", f"Multiply: ${b} \\times {paren(c - d / e)} = {F(b * (c - d / e))}$",
                                f"Subtract: ${F(a * a)} - {paren(b * (c - d / e))} = {F(a * a - b * (c - d / e))}$"]),
    ],
}


def _order_ops(ctx: Ctx) -> Problem:
    tmpl, fn, how = ctx.rng.choice(_OPS_TEMPLATES[ctx.difficulty])
    for _ in range(500):
        vals = {k: Fraction(ctx.rng.randint(1, 12)) for k in "abcde"}
        try:
            v = fn(**vals)
        except ZeroDivisionError:
            continue
        if v.denominator == 1:
            q = tmpl.format(**{k: int(n) for k, n in vals.items()})
            return Problem(f"$${q}$$", f"${v.numerator}$", steps(*how(**vals)))
    raise RuntimeError("could not build an integer order-of-operations problem")


for _lv in (1, 2, 3):
    variant("order_ops", _lv, "Evaluate expressions")(_order_ops)

topic("fractions", "math", "Foundations", "Fractions",
      "Add, subtract, multiply and divide fractions; answers fully simplified.", courses=['alg1'])


def _rand_frac(ctx: Ctx, maxd: int) -> Fraction:
    d = ctx.rng.randint(2, maxd)
    return Fraction(ctx.rng.randint(1, d * 2 - 1), d)


def _unsimplified(n: int, d: int) -> str:
    return f"\\frac{{{n}}}{{{d}}}"


def _simplify_step(n: int, d: int) -> str:
    g = math.gcd(n, d)
    return f"Simplify: ${_unsimplified(n, d)} = {frac(Fraction(n, d))}$" if g > 1 or d == 1 else ""


@variant("fractions", 1, "Same denominators")
def _frac_same_den(ctx: Ctx) -> Problem:
    d = ctx.rng.randint(3, 12)
    a, b = ctx.rng.randint(1, d - 1), ctx.rng.randint(1, d - 1)
    if ctx.rng.random() < 0.5:
        return Problem(rf"$$\frac{{{a}}}{{{d}}} + \frac{{{b}}}{{{d}}}$$", f"${frac(Fraction(a + b, d))}$",
                       steps(f"Same denominator, so add the numerators: ${_unsimplified(a + b, d)}$",
                             _simplify_step(a + b, d)))
    a, b = max(a, b), min(a, b)
    return Problem(rf"$$\frac{{{a}}}{{{d}}} - \frac{{{b}}}{{{d}}}$$", f"${frac(Fraction(a - b, d))}$",
                   steps(f"Same denominator, so subtract the numerators: ${_unsimplified(a - b, d)}$",
                         _simplify_step(a - b, d) if a != b else ""))


def _frac_ops(ctx: Ctx, mixed: bool) -> Problem:
    maxd = 12 if not mixed else 9
    f1, f2 = _rand_frac(ctx, maxd), _rand_frac(ctx, maxd)
    if mixed:
        f1 += ctx.rng.randint(1, 4)
        f2 += ctx.rng.randint(1, 3)
    op = ctx.rng.choice(["+", "-", r"\times", r"\div"])
    res = {"+": f1 + f2, "-": f1 - f2, r"\times": f1 * f2, r"\div": f1 / f2}[op]
    ans = f"${frac(res)}$"
    if mixed and abs(res.numerator) > res.denominator > 1:
        ans = f"${frac(res)} = {frac(res, mixed=True)}$"
    work = [f"Write as improper fractions: ${frac(f1)} {op} {frac(f2)}$"] if mixed else []
    n1, d1, n2, d2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator
    if op in ("+", "-"):
        lcd = math.lcm(d1, d2)
        a, b = n1 * lcd // d1, n2 * lcd // d2
        raw = a + b if op == "+" else a - b
        work += [f"Common denominator ${lcd}$: ${_unsimplified(a, lcd)} {op} {_unsimplified(b, lcd)} = {_unsimplified(raw, lcd)}$"
                 if raw >= 0 else f"Common denominator ${lcd}$: ${_unsimplified(a, lcd)} - {_unsimplified(b, lcd)} = "
                 f"-{_unsimplified(-raw, lcd)}$"]
        top, bottom = raw, lcd
    else:
        if op == r"\div":
            work.append(f"Multiply by the reciprocal: ${frac(f1)} \\times {_unsimplified(d2, n2)}$")
            n2, d2 = d2, n2
        top, bottom = n1 * n2, d1 * d2
        work.append(f"Multiply across: $\\frac{{{n1} \\times {n2}}}{{{d1} \\times {d2}}} = {_unsimplified(top, bottom)}$")
    work.append(_simplify_step(abs(top), bottom) and f"Simplify: ${frac(res)}$")
    if mixed and abs(res.numerator) > res.denominator > 1:
        work.append(f"As a mixed number: ${frac(res, mixed=True)}$")
    return Problem(f"$${frac(f1, mixed)} {op} {frac(f2, mixed)}$$", ans, steps(*work))


variant("fractions", 2, "Any denominators")(lambda c: _frac_ops(c, False))
variant("fractions", 3, "Mixed numbers")(lambda c: _frac_ops(c, True))

topic("percent", "math", "Foundations", "Percentages",
      "Percent of a number, percent change and reverse percentages.", courses=['alg1'])


def num_frac(f: Fraction) -> str:
    """Show a Fraction as an integer or terminating decimal when possible."""
    f = Fraction(f)
    if f.denominator == 1:
        return str(f.numerator)
    d = f.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    return f"{float(f):g}" if d == 1 else frac(f)


@variant("percent", 1, "Percent of a number")
def _pct_of(ctx: Ctx) -> Problem:
    p = ctx.rng.choice([5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90])
    n = ctx.rng.randint(1, 30) * 20
    v = Fraction(p * n, 100)
    return Problem(f"What is ${p}\\%$ of ${n}$?", f"${num_frac(v)}$",
                   steps(f"Write the percent as a decimal: ${p}\\% = {p / 100:g}$",
                         f"Multiply: ${p / 100:g} \\times {n} = {num_frac(v)}$"),
                   facts={"p": p, "n": n, "v": v})


_PCT_CONTEXTS = [
    "${part}$ is what percent of ${whole}$?",
    "A student answered ${part}$ of ${whole}$ test questions correctly. What percent is that?",
    "A team won ${part}$ of its ${whole}$ games. What percent of its games did it win?",
    "${part}$ of the ${whole}$ students in a school band play brass instruments. What percent is that?",
]


@variant("percent", 2, "Find the percent")
def _pct_what(ctx: Ctx) -> Problem:
    while True:
        whole = ctx.rng.choice([20, 25, 40, 50, 60, 80, 120, 150, 160, 200, 240, 250, 300, 400, 500])
        p = ctx.rng.choice([*range(5, 100, 5), 110, 120, 150])
        part = Fraction(p * whole, 100)
        if part.denominator == 1 and (p <= 100 or ctx.rng.random() < 0.15):
            break
    text = ctx.rng.choice(_PCT_CONTEXTS if p <= 100 else _PCT_CONTEXTS[:1])
    return Problem(text.replace("${part}$", f"${part}$").replace("${whole}$", f"${whole}$"), f"${p}\\%$",
                   steps(f"Part over whole: $\\frac{{{part}}}{{{whole}}} = {p / 100:g}$",
                         f"Convert to a percent: ${p / 100:g} \\times 100\\% = {p}\\%$"),
                   facts={"part": part, "whole": whole, "p": p})


_ITEMS = ["jacket", "pair of headphones", "bike", "video game", "backpack", "pair of sneakers"]


@variant("percent", 3, "Original price after a discount")
def _pct_discount(ctx: Ctx) -> Problem:
    p = ctx.rng.choice([10, 15, 20, 25, 30, 35, 40, 50])
    orig = ctx.rng.randint(4, 60) * 5
    sale = Fraction(orig * (100 - p), 100)
    return Problem(f"After a ${p}\\%$ discount, a {ctx.rng.choice(_ITEMS)} costs ${num_frac(sale)}$ dollars. "
                   "What was the original price?",
                   f"${orig}$ dollars",
                   steps(f"The sale price is ${100 - p}\\%$ of the original: ${num_frac(sale)} = {(100 - p) / 100:g}x$",
                         f"Divide: $x = \\frac{{{num_frac(sale)}}}{{{(100 - p) / 100:g}}} = {orig}$"),
                   facts={"p": p, "sale": sale, "orig": orig})


@variant("percent", 3, "Percent change")
def _pct_change(ctx: Ctx) -> Problem:
    old = ctx.rng.randint(5, 50) * 4
    new = old + ctx.rng.choice([-1, 1]) * old * ctx.rng.choice([5, 10, 20, 25, 40, 50, 75]) // 100
    ch = Fraction(new - old, old) * 100
    word = "increase" if new > old else "decrease"
    return Problem(f"A value changes from ${old}$ to ${new}$. What is the percent change?",
                   f"${num_frac(abs(ch))}\\%$ {word}",
                   steps(f"Change: ${new} - {old} = {new - old}$",
                         f"Divide by the original: $\\frac{{{new - old}}}{{{old}}} \\times 100\\% = {num_frac(ch)}\\%$",
                         f"Negative means a decrease; positive means an increase: a ${num_frac(abs(ch))}\\%$ {word}."),
                   facts={"old": old, "new": new, "pct": ch})


# ======================================================== Algebra

topic("linear_eq", "math", "Equations", "Linear equations",
      "Solve one-step, two-step, and variables-on-both-sides equations.", courses=['alg1'])


def _undo_add(a: int, rhs: int, result: int, var: str = "x") -> str:
    """Step text for removing a constant from the left side."""
    if a > 0:
        return f"Subtract ${a}$ from both sides: ${var} = {rhs} - {a} = {result}$"
    return f"Add ${-a}$ to both sides: ${var} = {rhs} + {-a} = {result}$"


@variant("linear_eq", 1, "One-step (add or subtract)")
def _lin_add(ctx: Ctx) -> Problem:
    sol, a = nz(ctx.rng, -12, 15), nz(ctx.rng, -15, 15)
    eq = sp.Eq(x + a, sol + a)
    return Problem(f"Solve for $x$: $${L(eq)}$$", f"$x = {sol}$",
                   steps(_undo_add(a, sol + a, sol), f"Check: ${sol} + {paren(a)} = {sol + a}$"),
                   facts={"eq": eq, "x": sol})


@variant("linear_eq", 1, "One-step (multiply or divide)")
def _lin_mul(ctx: Ctx) -> Problem:
    sol, a = nz(ctx.rng, -12, 15), ctx.rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 12, -2, -3, -4, -5])
    eq = sp.Eq(a * x, a * sol)
    return Problem(f"Solve for $x$: $${L(eq)}$$", f"$x = {sol}$",
                   steps(f"Divide both sides by ${a}$: $x = \\frac{{{a * sol}}}{{{a}}} = {sol}$",
                         f"Check: ${paren(a)}({sol}) = {a * sol}$"),
                   facts={"eq": eq, "x": sol})


@variant("linear_eq", 2, "Two-step equations")
def _lin2(ctx: Ctx) -> Problem:
    sol = nz(ctx.rng, -10, 10)
    a, b = ctx.rng.choice([2, 3, 4, 5, 6, 7, 8, 9, -2, -3, -4, -5, -6]), nz(ctx.rng, -20, 20)
    eq = sp.Eq(a * x + b, a * sol + b)
    c = a * sol + b
    return Problem(f"Solve for $x$: $${L(eq)}$$", f"$x = {sol}$",
                   steps(_undo_add(b, c, a * sol, f"{a}x").replace(f"{a}x = ", f"{L(a * x)} = "),
                         f"Divide both sides by ${a}$: $x = \\frac{{{a * sol}}}{{{a}}} = {sol}$"),
                   facts={"eq": eq, "x": sol})


@variant("linear_eq", 3, "Variables on both sides")
def _lin3(ctx: Ctx) -> Problem:
    sol = nz(ctx.rng, -10, 10)
    a, b = ctx.rng.randint(2, 6), nz(ctx.rng, -8, 8)
    c = nz(ctx.rng, -9, 9)
    while c == a:
        c = nz(ctx.rng, -9, 9)
    d = a * (sol + b) - c * sol
    lhs = sp.Mul(a, x + b, evaluate=False)
    eq = sp.Eq(lhs, c * x + d, evaluate=False)
    return Problem(f"Solve for $x$: $${L(eq)}$$", f"$x = {sol}$",
                   steps(f"Distribute: ${L(sp.expand(a * (x + b)))} = {L(c * x + d)}$",
                         f"Collect $x$ on the left and numbers on the right: ${L((a - c) * x)} = {d - a * b}$",
                         f"Divide by ${a - c}$: $x = {sol}$"),
                   facts={"eq": eq, "x": sol})


topic("systems", "math", "Systems of equations", "Systems of equations",
      "Two linear equations in two unknowns with integer solutions.", courses=['alg1', 'alg2'])


def _system(ctx: Ctx, coef: int, sol_rng: int) -> Problem:
    sx, sy = ctx.rng.randint(-sol_rng, sol_rng), ctx.rng.randint(-sol_rng, sol_rng)
    while True:
        a1, b1, a2, b2 = (nz(ctx.rng, -coef, coef) for _ in range(4))
        if a1 * b2 - a2 * b1 != 0:
            break
    c1, c2 = a1 * sx + b1 * sy, a2 * sx + b2 * sy
    e1, e2 = sp.Eq(a1 * x + b1 * y, c1), sp.Eq(a2 * x + b2 * y, c2)
    # Elimination: scale both equations so the x-coefficients match, then subtract.
    lcm = math.lcm(abs(a1), abs(a2))
    k1, k2 = lcm // a1, lcm // a2
    work = []
    if abs(k1) != 1 or abs(k2) != 1 or k1 != k2:
        work.append(f"Eliminate $x$: multiply the first equation by ${k1}$ and the second by ${k2}$:")
        work.append(f"${L(sp.Eq(k1 * a1 * x + k1 * b1 * y, k1 * c1))}$ and ${L(sp.Eq(k2 * a2 * x + k2 * b2 * y, k2 * c2))}$")
    else:
        work.append("Eliminate $x$ by subtracting the equations:")
    yb, rhs = k1 * b1 - k2 * b2, k1 * c1 - k2 * c2
    work.append(f"Subtract: ${L(yb * y)} = {rhs}$, so $y = {sy}$")
    work.append(f"Substitute into the first equation: ${L(a1 * x)} + {paren(b1)}({sy}) = {c1}$, so $x = {sx}$")
    return Problem(rf"Solve the system: $$\begin{{cases}} {L(e1)} \\ {L(e2)} \end{{cases}}$$",
                   f"$x = {sx},\\ y = {sy}$", steps(*work), facts={"eqs": [e1, e2], "x": sx, "y": sy})


variant("systems", 1, "Solve a system")(lambda c: _system(c, 3, 6))
variant("systems", 2, "Solve a system")(lambda c: _system(c, 6, 9))
variant("systems", 3, "Solve a system")(lambda c: _system(c, 12, 12))

topic("quadratics", "math", "Quadratics", "Quadratic equations",
      "Solve by factoring, or with the quadratic formula at the hard level.", courses=['alg1', 'alg2'],
      exact_forms=True, rounding=True)


@variant("quadratics", 1, "Factor x² + bx + c")
def _quad1(ctx: Ctx) -> Problem:
    r1, r2 = ctx.rng.sample(range(-9, 10), 2)  # distinct roots
    poly = sp.expand((x - r1) * (x - r2))
    roots = sorted({r1, r2})
    b, c = -(r1 + r2), r1 * r2
    return Problem(f"Solve by factoring: $${L(poly)} = 0$$",
                   "$" + ",\\ ".join(f"x = {r}" for r in roots) + "$",
                   steps(f"Find two numbers that multiply to ${c}$ and add to ${b}$: ${-r1}$ and ${-r2}$",
                         f"Factor: ${L(sp.factor(poly))} = 0$",
                         f"Set each factor to zero: $x = {roots[0]}$ or $x = {roots[1]}$"),
                   facts={"poly": poly, "roots": roots})


@variant("quadratics", 2, "Factor ax² + bx + c")
def _quad2(ctx: Ctx) -> Problem:
    # (px - q)(x - r) with gcd(p, q) = 1, keeping coefficients small enough to factor by hand
    while True:
        p, q, r = ctx.rng.randint(2, 5), nz(ctx.rng, -9, 9), ctx.rng.randint(-7, 7)
        if math.gcd(p, q) == 1 and abs(p * r + q) <= 25 and abs(q * r) <= 50:
            break
    poly = sp.expand((p * x - q) * (x - r))
    roots = sorted({sp.Rational(q, p), sp.Integer(r)})
    a, b, c = p, -(p * r + q), q * r
    return Problem(f"Solve by factoring: $${L(poly)} = 0$$",
                   "$" + ",\\ ".join(f"x = {L(rt)}" for rt in roots) + "$",
                   steps(f"$ac = ({a})({c}) = {a * c}$; two numbers with product ${a * c}$ and sum ${b}$: "
                         f"${-p * r}$ and ${-q}$",
                         f"Split the middle term and factor by grouping: ${L(sp.factor(poly))} = 0$",
                         f"Set each factor to zero: ${L(p * x - q)} = 0 \\Rightarrow x = {L(sp.Rational(q, p))}$; "
                         f"${L(x - r)} = 0 \\Rightarrow x = {r}$"),
                   facts={"poly": poly, "roots": roots})


@variant("quadratics", 3, "Quadratic formula")
def _quad3(ctx: Ctx) -> Problem:
    while True:
        a, b, c = ctx.rng.randint(1, 5), nz(ctx.rng, -10, 10), nz(ctx.rng, -12, 12)
        disc = b * b - 4 * a * c
        if disc > 0 and math.isqrt(disc) ** 2 != disc:
            break
    poly = a * x**2 + b * x + c
    roots = sorted(sp.solve(sp.Eq(poly, 0), x), key=float)
    exact, pm = pm_tex(a, b, disc)
    approx = ",\\ ".join(ctx.rnd(float(rt)) for rt in roots)
    answer = {"exact": f"$x = {exact}$", "decimal": f"$x \\approx {approx}$",
              "both": f"$x = {exact}$ $(x \\approx {approx})$"}[ctx.form]
    return Problem(f"Solve using the quadratic formula: $${L(poly)} = 0$$" + ctx.form_note("in simplest radical form"),
                   answer,
                   steps(f"$a = {a},\\ b = {b},\\ c = {c}$",
                         f"Discriminant: $b^2 - 4ac = ({b})^2 - 4({a})({c}) = {disc}$",
                         f"$x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}} = \\frac{{{-b} \\pm \\sqrt{{{disc}}}}}{{{2 * a}}}$",
                         radical_steps(disc), f"$x = {exact}$",
                         "" if ctx.form == "exact" else f"$x \\approx {approx}$"),
                   facts={"poly": poly, "roots": roots, "pm": pm})


topic("exponents", "math", "Exponents", "Exponent rules",
      "Simplify expressions using product, quotient and power rules.", courses=['alg1', 'alg2'])


def _mono(c: int, var: str, e: int) -> str:
    """LaTeX monomial like 3x^{5}, omitting a coefficient of 1."""
    return f"{'' if c == 1 else c}{var}^{{{e}}}"


@variant("exponents", 1, "Product rule")
def _exp_product(ctx: Ctx) -> Problem:
    c1, c2, a, b = ctx.rng.randint(1, 9), ctx.rng.randint(1, 9), ctx.rng.randint(2, 9), ctx.rng.randint(2, 9)
    q = (c1 * x**a) * (c2 * x**b)
    return Problem(f"Simplify: $$({_mono(c1, 'x', a)})({_mono(c2, 'x', b)})$$", f"${L(c1 * c2 * x ** (a + b))}$",
                   steps(f"Multiply the coefficients: ${c1} \\cdot {c2} = {c1 * c2}$",
                         f"Add the exponents: $x^{{{a}}} \\cdot x^{{{b}}} = x^{{{a}+{b}}} = x^{{{a + b}}}$"),
                   facts={"q_expr": q, "ans_expr": c1 * c2 * x ** (a + b)})


@variant("exponents", 1, "Quotient rule")
def _exp_quotient(ctx: Ctx) -> Problem:
    c2, k, b, d = ctx.rng.randint(1, 6), ctx.rng.randint(1, 8), ctx.rng.randint(1, 6), ctx.rng.randint(1, 7)
    c1, a = c2 * k, b + d
    q = (c1 * x**a) / (c2 * x**b)
    return Problem(f"Simplify: $$\\frac{{{_mono(c1, 'x', a)}}}{{{_mono(c2, 'x', b)}}}$$", f"${L(k * x ** d)}$",
                   steps(f"Divide the coefficients: ${c1} \\div {c2} = {k}$",
                         f"Subtract the exponents: $\\frac{{x^{{{a}}}}}{{x^{{{b}}}}} = x^{{{a}-{b}}} = x^{{{d}}}$"),
                   facts={"q_expr": q, "ans_expr": k * x**d})


@variant("exponents", 2, "Power rule")
def _exp2(ctx: Ctx) -> Problem:
    while True:
        a, b, c = ctx.rng.randint(2, 6), ctx.rng.randint(2, 4), ctx.rng.randint(1, 12)
        if a * b != c:  # an x^0 answer would be a trick question
            break
    k = ctx.rng.randint(2, 5)
    ans = k**b * x ** (a * b - c)
    return Problem(f"Simplify, writing with positive exponents: $$\\frac{{({k}x^{{{a}}})^{{{b}}}}}{{x^{{{c}}}}}$$",
                   f"${L(ans)}$",
                   steps(f"Power of a product: $({k}x^{{{a}}})^{{{b}}} = {k}^{{{b}}}x^{{{a} \\cdot {b}}} = {k ** b}x^{{{a * b}}}$",
                         f"Quotient rule: $x^{{{a * b} - {c}}} = x^{{{a * b - c}}}$",
                         f"Result: ${L(ans)}$" if a * b - c > 0 else
                         f"Move the negative exponent to the denominator: ${L(ans)}$"),
                   facts={"q_expr": (k * x**a) ** b / x**c, "ans_expr": ans})


@variant("exponents", 3, "Negative exponents")
def _exp3(ctx: Ctx) -> Problem:
    while True:
        a, b, c = ctx.rng.randint(1, 5), ctx.rng.randint(1, 5), ctx.rng.randint(2, 3)
        d, e = ctx.rng.randint(1, 9), ctx.rng.randint(1, 9)
        if a * c != d:
            break
    ans = x ** (a * c - d) * y ** (-b * c - e)
    return Problem(f"Simplify, writing with positive exponents: "
                   f"$$\\frac{{(x^{{{a}}} y^{{-{b}}})^{{{c}}}}}{{x^{{{d}}} y^{{{e}}}}}$$",
                   f"${L(ans)}$",
                   steps(f"Power of a product: $(x^{{{a}}}y^{{-{b}}})^{{{c}}} = x^{{{a * c}}}y^{{{-b * c}}}$",
                         f"Quotient rule: $x^{{{a * c} - {d}}}y^{{{-b * c} - {e}}} = x^{{{a * c - d}}}y^{{{-b * c - e}}}$",
                         f"Move negative exponents to the denominator: ${L(ans)}$"),
                   facts={"q_expr": (x**a * y ** (-b)) ** c / (x**d * y**e), "ans_expr": ans})


topic("logs", "math", "Exponentials & logarithms", "Logarithms",
      "Evaluate logs and solve exponential/logarithmic equations.", courses=['alg2', 'precalc'], rounding=True)


def _log_arg(r: int, n: int) -> str:
    return str(r**n) if n >= 0 else f"\\frac{{1}}{{{r ** -n}}}"


@variant("logs", 1, "Evaluate logarithms")
def _log_eval(ctx: Ctx) -> Problem:
    while True:
        b, n = ctx.rng.randint(2, 10), ctx.rng.choice([-3, -2, -1, 1, 2, 3, 4, 5, 6])
        if 1 / 1000 <= b**n <= 100_000:
            break
    base = "" if b == 10 else f"_{{{b}}}"
    return Problem(f"Evaluate: $$\\log{base}\\left({_log_arg(b, n)}\\right)$$", f"${n}$",
                   steps(f"Ask: ${b}$ to what power gives ${_log_arg(b, n)}$?",
                         f"${b}^{{{n}}} = {_log_arg(b, n)}$, so the logarithm is ${n}$"),
                   facts={"base": b, "arg": sp.Rational(b) ** n, "x": n})


@variant("logs", 1, "Natural logs")
def _log_ln(ctx: Ctx) -> Problem:
    n = ctx.rng.choice([-3, -2, -1, 2, 3, 4, 5, 6, 7])
    if ctx.rng.random() < 0.5:
        return Problem(f"Evaluate: $$\\ln\\left(e^{{{n}}}\\right)$$", f"${n}$",
                       steps("$\\ln$ and $e^x$ undo each other: $\\ln(e^k) = k$", f"$\\ln(e^{{{n}}}) = {n}$"),
                       facts={"base": sp.E, "arg": sp.E**n, "x": n})
    return Problem(f"Evaluate: $$e^{{\\ln {abs(n)}}}$$", f"${abs(n)}$",
                   steps("$e^x$ and $\\ln$ undo each other: $e^{\\ln k} = k$", f"$e^{{\\ln {abs(n)}}} = {abs(n)}$"))


@variant("logs", 2, "Logs with fractional values")
def _log_frac(ctx: Ctx) -> Problem:
    # log_{r^m}(r^n) = n/m, e.g. log_8(4) = 2/3
    while True:
        r, m = ctx.rng.choice([2, 3, 5]), ctx.rng.randint(2, 3)
        n = nz(ctx.rng, -4, 6)
        if n % m and r**m <= 125 and r ** abs(n) <= 15625:
            break
    v = sp.Rational(n, m)
    return Problem(f"Evaluate: $$\\log_{{{r ** m}}}\\left({_log_arg(r, n)}\\right)$$", f"${L(v)}$",
                   steps(f"Let the value be $x$: $({r ** m})^x = {_log_arg(r, n)}$",
                         f"Write both as powers of ${r}$: $({r}^{{{m}}})^x = {r}^{{{n}}}$",
                         f"So ${m}x = {n}$ and $x = {L(v)}$"),
                   facts={"base": r**m, "arg": sp.Rational(r) ** n, "x": v})


@variant("logs", 2, "Solve exponential equations")
def _log_solve(ctx: Ctx) -> Problem:
    b = ctx.rng.choice([2, 3, 5, 6, 7, 10, 1.5, 1.05, 1.08])
    c = ctx.rng.randint(5, 500)
    xv = math.log(c) / math.log(b)
    return Problem(f"Solve for $x$: $${num(b)}^{{x}} = {c}$$" + ctx.round_note(),
                   f"$x \\approx {ctx.rnd(xv)}$",
                   steps(f"Take the natural log of both sides: $x\\ln {num(b)} = \\ln {c}$",
                         f"$x = \\frac{{\\ln {c}}}{{\\ln {num(b)}}} \\approx {ctx.rnd(xv)}$"),
                   facts={"base": b, "arg": c, "x": xv})


@variant("logs", 3, "Log properties")
def _log_sum(ctx: Ctx) -> Problem:
    while True:
        b, n = ctx.rng.choice([2, 3, 4, 5, 6, 10]), ctx.rng.randint(1, 4)
        divs = [m for m in range(2, b**n) if (b**n) % m == 0]
        if divs and b**n <= 10_000:
            break
    m = ctx.rng.choice(divs)
    base = "" if b == 10 else f"_{{{b}}}"
    if ctx.rng.random() < 0.5:
        return Problem(f"Solve for $x$: $$\\log{base}(x) + \\log{base}({m}) = {n}$$", f"$x = {L(sp.Rational(b ** n, m))}$",
                       steps(f"Product rule: $\\log{base}({m}x) = {n}$",
                             f"Exponential form: ${m}x = {b}^{{{n}}} = {b ** n}$",
                             f"$x = \\frac{{{b ** n}}}{{{m}}} = {L(sp.Rational(b ** n, m))}$"),
                       facts={"lhs": sp.log(x, b) + sp.log(m, b), "rhs": n, "x": sp.Rational(b**n, m)})
    return Problem(f"Solve for $x$: $$\\log{base}(x) - \\log{base}({m}) = {n}$$", f"$x = {m * b ** n}$",
                   steps(f"Quotient rule: $\\log{base}\\left(\\frac{{x}}{{{m}}}\\right) = {n}$",
                         f"Exponential form: $\\frac{{x}}{{{m}}} = {b}^{{{n}}} = {b ** n}$",
                         f"$x = {m} \\cdot {b ** n} = {m * b ** n}$"),
                   facts={"lhs": sp.log(x, b) - sp.log(m, b), "rhs": n, "x": m * b**n})


@variant("logs", 3, "Solve log equations")
def _log_shift(ctx: Ctx) -> Problem:
    b, n, k = ctx.rng.choice([2, 3, 4, 5, 10]), ctx.rng.randint(1, 4), nz(ctx.rng, -20, 20)
    base = "" if b == 10 else f"_{{{b}}}"
    inner = L(x + k)
    return Problem(f"Solve for $x$: $$\\log{base}({inner}) = {n}$$", f"$x = {b ** n - k}$",
                   steps(f"Exponential form: ${inner} = {b}^{{{n}}} = {b ** n}$",
                         _undo_add(k, b**n, b**n - k)),
                   facts={"lhs": sp.log(x + k, b), "rhs": n, "x": b**n - k})


# ======================================================== Geometry

topic("pythagorean", "math", "Right triangles", "Pythagorean theorem",
      "Missing sides of right triangles, the converse, and 3-D diagonals.", courses=['geo'], exact_forms=True,
      rounding=True, figures=True)

_TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37),
            (11, 60, 61), (28, 45, 53), (33, 56, 65)]

# Each context: (unit, largest sensible length, text asking for the hypotenuse,
#                text asking for leg b given hypotenuse c and leg a, realistic shape test on (a, b),
#                whether leg a is vertical in the story — for drawing the figure).
# Leg a plays the same role in both texts (e.g. the ladder's foot distance).
_ANY = lambda a, b: True  # noqa: E731
_PYTH_CONTEXTS = [
    ("cm", 100, "A right triangle has legs ${a}$ and ${b}$. Find the length of the hypotenuse.",
     "A right triangle has a hypotenuse of ${c}$ and one leg of ${a}$. Find the other leg.", _ANY, False),
    ("ft", 40, "A ladder leans against a wall. Its foot is ${a}$ from the wall and its top is ${b}$ up the wall. "
           "How long is the ladder?",
     "A ${c}$ ladder leans against a wall with its foot ${a}$ from the wall. How high up the wall does it reach?",
     lambda a, b: a <= 0.6 * b, False),  # ladders lean steeply
    ("in", 100, "A rectangular TV screen is ${b}$ wide and ${a}$ tall. How long is its diagonal?",
     "A TV screen has a ${c}$ diagonal and is ${a}$ tall. How wide is it?",
     lambda a, b: 1.3 <= b / a <= 1.9, True),  # real screen proportions
    ("m", 100, "A rectangular field measures ${a}$ by ${b}$. How long is a straight path between opposite corners?",
     "A straight path between opposite corners of a rectangular field is ${c}$ long. One side of the field "
     "is ${a}$. How long is the other side?", _ANY, False),
    ("m", 100, "A kite is flying ${b}$ above a point on the ground that is ${a}$ from the person holding the "
          "string. If the string is straight, how long is it?",
     "A kite on a ${c}$ straight string is directly above a point ${a}$ from the person holding it. "
     "How high is the kite?", lambda a, b: 0.3 <= b / a <= 4, False),
    ("mi", 100, "A plane flies ${a}$ north and then ${b}$ east. How far is it from its starting point?",
     "A boat ends up ${c}$ from port after sailing ${a}$ north and then due east. How far east did it sail?", _ANY, True),
]


def _fill(text: str, unit: str, **vals) -> str:
    for k, v in vals.items():
        text = text.replace(f"${{{k}}}$", f"${v}{U(unit)}$")
    return text


def _pyth_figure(a, b, c, unit: str, a_vertical: bool, unknown: str) -> str:
    """Right triangle for a Pythagorean problem: legs a and b, hypotenuse c, with the unknown side marked x."""
    labels = {k: ("x" if k == unknown else f"{num(float(v))} {unit}") for k, v in (("a", a), ("b", b), ("c", c))}
    if a_vertical:  # draw leg a upright, as in the story
        return draw.right_triangle(float(b), float(a), label_a=labels["b"], label_b=labels["a"], label_c=labels["c"])
    return draw.right_triangle(float(a), float(b), label_a=labels["a"], label_b=labels["b"], label_c=labels["c"])


def _scaled_triple(ctx: Ctx, cmax: int = 100, fits=_ANY):
    """A scaled Pythagorean triple (a, b, c) with c <= cmax whose legs pass ``fits``."""
    options = [(a * k, b * k, c * k) for a0, b0, c0 in _TRIPLES for k in range(1, cmax // c0 + 1)
               for a, b, c in ((a0, b0, c0), (b0, a0, c0)) if fits(a * k, b * k)]
    return ctx.rng.choice(options)


@variant("pythagorean", 1, "Find the hypotenuse")
def _pyth_hyp(ctx: Ctx) -> Problem:
    unit, cmax, hyp_text, _, fits, a_vert = ctx.rng.choice(_PYTH_CONTEXTS)
    a, b, c = _scaled_triple(ctx, cmax, fits)
    return Problem(_fill(hyp_text, unit, a=a, b=b), f"${c}{U(unit)}$",
                   steps("$a^2 + b^2 = c^2$", f"${a}^2 + {b}^2 = c^2$", f"${a * a} + {b * b} = {c * c} = c^2$",
                         f"$c = \\sqrt{{{c * c}}} = {c}{U(unit)}$"),
                   facts={"a": a, "b": b, "c": c}, figure=_pyth_figure(a, b, c, unit, a_vert, "c"))


@variant("pythagorean", 2, "Find a leg")
def _pyth_leg(ctx: Ctx) -> Problem:
    unit, cmax, _, leg_text, fits, a_vert = ctx.rng.choice(_PYTH_CONTEXTS)
    a, b, c = _scaled_triple(ctx, cmax, fits)
    return Problem(_fill(leg_text, unit, a=a, c=c), f"${b}{U(unit)}$",
                   steps("$a^2 + b^2 = c^2 \\Rightarrow b^2 = c^2 - a^2$", f"$b^2 = {c}^2 - {a}^2 = {c * c} - {a * a} = {b * b}$",
                         f"$b = \\sqrt{{{b * b}}} = {b}{U(unit)}$"),
                   facts={"a": a, "b": b, "c": c}, figure=_pyth_figure(a, b, c, unit, a_vert, "b"))


@variant("pythagorean", 2, "Is it a right triangle?")
def _pyth_converse(ctx: Ctx) -> Problem:
    a, b, c = _scaled_triple(ctx, 60)
    a, b = sorted((a, b))
    if ctx.rng.random() < 0.5:
        # near miss: looks plausible, isn't right — but must still be a triangle (3, 4, 7 isn't)
        c += ctx.rng.choice([d for d in (-2, -1, 1, 2) if a + b > c + d > b - a])
    sides = sorted((a, b, c))
    s2 = sides[0] ** 2 + sides[1] ** 2
    right = s2 == sides[2] ** 2
    kind = "right" if right else ("acute" if s2 > sides[2] ** 2 else "obtuse")
    rel = "=" if right else (">" if kind == "acute" else "<")
    shown = ctx.rng.sample(sides, 3)
    return Problem(f"A triangle has sides ${shown[0]}$, ${shown[1]}$ and ${shown[2]}$. Is it a right triangle? "
                   "If not, is it acute or obtuse?",
                   f"{'Yes, it is a right triangle' if right else f'No, it is {kind}'}: "
                   f"${sides[0]}^2 + {sides[1]}^2 = {s2}$ ${rel} {sides[2]}^2 = {sides[2] ** 2}$",
                   steps("Compare the squares of the two shorter sides with the square of the longest side.",
                         f"${sides[0]}^2 + {sides[1]}^2 = {sides[0] ** 2} + {sides[1] ** 2} = {s2}$",
                         f"${sides[2]}^2 = {sides[2] ** 2}$",
                         f"${s2} {rel} {sides[2] ** 2}$, so the triangle is {kind} "
                         "(equal: right; greater: acute; less: obtuse)."),
                   facts={"sides": sides, "kind": kind})


@variant("pythagorean", 3, "Simplest radical form")
def _pyth_radical(ctx: Ctx) -> Problem:
    unit, _, hyp_text, leg_text, fits, a_vert = ctx.rng.choice(_PYTH_CONTEXTS)
    is_square = lambda n: math.isqrt(n) ** 2 == n  # noqa: E731
    if ctx.rng.random() < 0.5:
        while True:
            a, b = ctx.rng.sample(range(2, 21), 2)
            if not is_square(a * a + b * b) and fits(a, b):
                break
        n = a * a + b * b
        exact, q = sp.sqrt(n), _fill(hyp_text, unit, a=a, b=b)
        facts = {"a": a, "b": b, "c": exact}
        fig = _pyth_figure(a, b, float(exact), unit, a_vert, "c")
        work = [f"$c^2 = {a}^2 + {b}^2 = {n}$", f"$c = \\sqrt{{{n}}}$"]
    else:
        while True:
            a, c = ctx.rng.randint(2, 20), ctx.rng.randint(5, 26)
            if c > a and not is_square(c * c - a * a) and fits(a, math.sqrt(c * c - a * a)):
                break
        n = c * c - a * a
        exact, q = sp.sqrt(n), _fill(leg_text, unit, a=a, c=c)
        facts = {"a": a, "b": exact, "c": c}
        fig = _pyth_figure(a, float(exact), c, unit, a_vert, "b")
        work = [f"$b^2 = {c}^2 - {a}^2 = {n}$", f"$b = \\sqrt{{{n}}}$"]
    return Problem(q + ctx.form_note("in simplest radical form"),
                   f"${ctx.exact_or_decimal(L(exact), float(exact), unit)}$",
                   steps(*work, radical_steps(n), "" if ctx.form == "exact" else f"$\\approx {ctx.rnd(float(exact))}{U(unit)}$"),
                   facts=facts, figure=fig)


@variant("pythagorean", 3, "3-D diagonals")
def _pyth_box(ctx: Ctx) -> Problem:
    l, w, h = ctx.rng.randint(2, 20), ctx.rng.randint(2, 15), ctx.rng.randint(2, 15)
    n = l * l + w * w + h * h
    d = sp.sqrt(n)
    what = ctx.rng.choice(["box", "shipping crate", "room"])
    unit = "ft" if what == "room" else "in"
    ans = f"{L(d)}{U(unit)}" if d.is_Integer else ctx.exact_or_decimal(L(d), float(d), unit)
    return Problem(f"A rectangular {what} measures ${l}$ by ${w}$ by ${h}{U(unit)}$. How long is the diagonal "
                   "from a bottom corner to the opposite top corner?"
                   + ("" if d.is_Integer else ctx.form_note("in simplest radical form")),
                   f"${ans}$",
                   steps("The space diagonal: $d = \\sqrt{l^2 + w^2 + h^2}$",
                         f"$d = \\sqrt{{{l}^2 + {w}^2 + {h}^2}} = \\sqrt{{{n}}}$", radical_steps(n),
                         "" if d.is_Integer or ctx.form == "exact" else f"$d \\approx {ctx.rnd(float(d))}{U(unit)}$"),
                   facts={"dims": (l, w, h), "d": d},
                   figure=draw.box(l, w, h, f"{l} {unit}", f"{w} {unit}", f"{h} {unit}", diagonal=True))


topic("area", "math", "Area & perimeter", "Area & perimeter",
      "Rectangles, triangles, circles, trapezoids and composite shapes.", courses=['geo'], exact_forms=True,
      rounding=True, figures=True)

# (unit, wording): {w} and {h} become measurements with the unit
_RECT_AREA = [("cm", "Find the area of a rectangle ${w}$ by ${h}$."),
              ("ft", "A rectangular garden is ${w}$ by ${h}$. How much ground does it cover?"),
              ("ft", "How much carpet is needed to cover a rectangular floor ${w}$ by ${h}$?"),
              ("in", "What is the area of a rectangular poster ${w}$ by ${h}$?")]
_RECT_PERIM = [("m", "Find the perimeter of a rectangle ${w}$ by ${h}$."),
               ("ft", "How much fencing is needed to enclose a rectangular yard ${w}$ by ${h}$?"),
               ("in", "A rectangular picture is ${w}$ by ${h}$. How much framing goes around its edge?"),
               ("m", "How far is one lap around a rectangular field ${w}$ by ${h}$?")]
_TRI_AREA = [("in", "Find the area of a triangle with base ${b}$ and height ${h}$."),
             ("ft", "A triangular sail has a base of ${b}$ and a height of ${h}$. What is its area?"),
             ("m", "A triangular garden bed has a base of ${b}$ and a height of ${h}$. What area does it cover?")]
_CIRCLE_AREA = [("m", "Find the area of a circle with radius ${r}$."),
                ("ft", "A circular rug has a radius of ${r}$. What area does it cover?"),
                ("m", "A circular pond has a radius of ${r}$. What is its surface area?")]
_CIRCLE_AREA_D = [("m", "Find the area of a circle with diameter ${d}$."),
                  ("in", "A pizza has a diameter of ${d}$. What is its area?")]
_CIRCUMFERENCE = [("cm", "Find the circumference of a circle with radius ${r}$.", "r"),
                  ("cm", "Find the circumference of a circle with diameter ${d}$.", "d"),
                  ("in", "A bicycle wheel has a diameter of ${d}$. How far does it roll in one full turn?", "d"),
                  ("ft", "A circular garden has a radius of ${r}$. How much edging goes around it?", "r")]


@variant("area", 1, "Rectangles")
def _area_rect(ctx: Ctx) -> Problem:
    w, h = ctx.rng.sample(range(2, 31), 2)
    unit, text = ctx.rng.choice(_RECT_AREA)
    return Problem(_fill(text, unit, w=w, h=h), f"${w * h}{U(unit + '^2')}$",
                   steps("$A = lw$", f"$A = ({w})({h}) = {w * h}{U(unit + '^2')}$"),
                   facts={"ans": w * h}, figure=draw.rectangle(w, h, f"{w} {unit}", f"{h} {unit}"))


@variant("area", 1, "Rectangles")
def _perim_rect(ctx: Ctx) -> Problem:
    w, h = ctx.rng.sample(range(2, 31), 2)
    unit, text = ctx.rng.choice(_RECT_PERIM)
    return Problem(_fill(text, unit, w=w, h=h), f"${2 * (w + h)}{U(unit)}$",
                   steps("$P = 2l + 2w$", f"$P = 2({w}) + 2({h}) = {2 * (w + h)}{U(unit)}$"),
                   facts={"ans": 2 * (w + h)}, figure=draw.rectangle(w, h, f"{w} {unit}", f"{h} {unit}"))


@variant("area", 1, "Triangles")
def _area_tri(ctx: Ctx) -> Problem:
    b, h = ctx.rng.randint(2, 30), ctx.rng.randint(2, 30)
    unit, text = ctx.rng.choice(_TRI_AREA)
    return Problem(_fill(text, unit, b=b, h=h), f"${num(b * h / 2)}{U(unit + '^2')}$",
                   steps("$A = \\tfrac{1}{2}bh$", f"$A = \\tfrac{{1}}{{2}}({b})({h}) = {num(b * h / 2)}{U(unit + '^2')}$"),
                   facts={"ans": b * h / 2}, figure=draw.triangle_base_height(b, h, f"{b} {unit}", f"{h} {unit}"))


@variant("area", 2, "Circle area")
def _area_circle(ctx: Ctx) -> Problem:
    r = ctx.rng.randint(2, 25)
    by_radius = ctx.rng.random() < 0.5
    unit, text = ctx.rng.choice(_CIRCLE_AREA if by_radius else _CIRCLE_AREA_D)
    area = ctx.exact_or_decimal(f"{r * r}\\pi", math.pi * r * r, unit + "^2")
    return Problem(_fill(text, unit, r=r, d=2 * r) + ctx.form_note("in terms of $\\pi$"), f"${area}$",
                   steps("" if by_radius else f"The radius is half the diameter: $r = {r}{U(unit)}$",
                         "$A = \\pi r^2$", f"$A = \\pi({r})^2 = {r * r}\\pi$",
                         "" if ctx.form == "exact" else f"$A \\approx {ctx.rnd(math.pi * r * r)}{U(unit + '^2')}$"),
                   facts={"ans": math.pi * r * r},
                   figure=draw.circle(r, f"{r} {unit}") if by_radius else draw.circle(r, f"{2 * r} {unit}", diameter=True))


@variant("area", 2, "Circumference")
def _circumference(ctx: Ctx) -> Problem:
    r = ctx.rng.randint(2, 25)
    unit, text, given = ctx.rng.choice(_CIRCUMFERENCE)
    return Problem(_fill(text, unit, r=r, d=2 * r) + ctx.form_note("in terms of $\\pi$"),
                   f"${ctx.exact_or_decimal(f'{2 * r}\\pi', 2 * math.pi * r, unit)}$",
                   steps("$C = 2\\pi r$" if given == "r" else "$C = \\pi d$",
                         f"$C = 2\\pi({r}) = {2 * r}\\pi$" if given == "r" else f"$C = \\pi({2 * r}) = {2 * r}\\pi$",
                         "" if ctx.form == "exact" else f"$C \\approx {ctx.rnd(2 * math.pi * r)}{U(unit)}$"),
                   facts={"ans": 2 * math.pi * r},
                   figure=draw.circle(r, f"{r} {unit}") if given == "r" else draw.circle(r, f"{2 * r} {unit}", diameter=True))


@variant("area", 2, "Trapezoids")
def _area_trap(ctx: Ctx) -> Problem:
    a, b, h = ctx.rng.randint(3, 15), ctx.rng.randint(16, 30), ctx.rng.randint(2, 15)
    return Problem(f"A trapezoid has parallel sides ${a}$ cm and ${b}$ cm and height ${h}$ cm. Find its area.",
                   f"${num((a + b) * h / 2)}{U('cm^2')}$",
                   steps("$A = \\frac{b_1 + b_2}{2}h$",
                         f"$A = \\frac{{{a} + {b}}}{{2}}({h}) = ({num((a + b) / 2)})({h}) = {num((a + b) * h / 2)}{U('cm^2')}$"),
                   facts={"ans": (a + b) * h / 2}, figure=draw.trapezoid(a, b, h, f"{a} cm", f"{b} cm", f"{h} cm"))


@variant("area", 3, "Composite figures")
def _area_window(ctx: Ctx) -> Problem:
    w = ctx.rng.randint(12, 40) * 2
    h = ctx.rng.randint(math.ceil(w * 0.6), w * 2)  # window-like proportions
    r = w // 2
    area_t, per_t = pi_tex(w * h, sp.Rational(w * w, 8)), pi_tex(2 * h + w, sp.Rational(w, 2))
    area, per = w * h + math.pi * w * w / 8, 2 * h + w + math.pi * w / 2
    return Problem(f"A window is a rectangle ${w}$ in wide and ${h}$ in tall, topped by a semicircle across its "
                   "full width. Find (a) the area of glass and (b) the length of trim around the outside."
                   + ctx.form_note("in terms of $\\pi$"),
                   f"(a) ${ctx.exact_or_decimal(area_t, area, 'in^2')}$ "
                   f"(b) ${ctx.exact_or_decimal(per_t, per, 'in')}$",
                   steps(f"The semicircle has radius $r = \\frac{{{w}}}{{2}} = {r}$",
                         f"(a) Rectangle + half circle: $({w})({h}) + \\tfrac{{1}}{{2}}\\pi({r})^2 = {area_t}$"
                         + ("" if ctx.form == "exact" else f" $\\approx {ctx.rnd(area)}{U('in^2')}$"),
                         f"(b) Two sides, the bottom and the arc: $2({h}) + {w} + \\tfrac{{1}}{{2}}(2\\pi \\cdot {r}) = {per_t}$"
                         + ("" if ctx.form == "exact" else f" $\\approx {ctx.rnd(per)}{U('in')}$")),
                   facts={"ans": (area, per)}, figure=draw.window(w, h, f"{w} in", f"{h} in"))


@variant("area", 3, "Composite figures")
def _area_track(ctx: Ctx) -> Problem:
    L_, d = ctx.rng.randint(40, 120), ctx.rng.randint(30, 70)
    r = sp.Rational(d, 2)
    area_t, per_t = pi_tex(L_ * d, sp.Rational(d * d, 4)), pi_tex(2 * L_, d)
    area, per = L_ * d + math.pi * d * d / 4, 2 * L_ + math.pi * d
    return Problem(f"A field is a rectangle ${L_}$ m long and ${d}$ m wide with a semicircle on each short end. "
                   "Find (a) its area and (b) the distance around it." + ctx.form_note("in terms of $\\pi$"),
                   f"(a) ${ctx.exact_or_decimal(area_t, area, 'm^2')}$ "
                   f"(b) ${ctx.exact_or_decimal(per_t, per, 'm')}$",
                   steps(f"The two semicircles make one circle of radius $r = \\frac{{{d}}}{{2}} = {L(r)}$",
                         f"(a) Rectangle + circle: $({L_})({d}) + \\pi({L(r)})^2 = {area_t}$"
                         + ("" if ctx.form == "exact" else f" $\\approx {ctx.rnd(area)}{U('m^2')}$"),
                         f"(b) Two straight sides + the circle's circumference: $2({L_}) + \\pi({d}) = {per_t}$"
                         + ("" if ctx.form == "exact" else f" $\\approx {ctx.rnd(per)}{U('m')}$")),
                   facts={"ans": (area, per)}, figure=draw.stadium(L_, d, f"{L_} m", f"{d} m"))


topic("slope", "math", "Lines & coordinate geometry", "Slope & lines",
      "Slope between points, equation of a line, perpendicular lines.", courses=['alg1', 'geo'], figures=True)


def _line_tex(m: Fraction, b: Fraction) -> str:
    return L(sp.Eq(y, sp.Rational(m.numerator, m.denominator) * x + sp.Rational(b.numerator, b.denominator)))


def _two_points(ctx: Ctx):
    while True:
        x1, y1, x2, y2 = (ctx.rng.randint(-9, 9) for _ in range(4))
        if x1 != x2 and y1 != y2:  # no vertical lines, no zero slopes
            return x1, y1, x2, y2


def _slope_step(x1, y1, x2, y2) -> str:
    m = Fraction(y2 - y1, x2 - x1)
    return (f"$m = \\frac{{y_2 - y_1}}{{x_2 - x_1}} = \\frac{{{y2} - {paren(y1)}}}{{{x2} - {paren(x1)}}} = "
            f"\\frac{{{y2 - y1}}}{{{x2 - x1}}} = {frac(m)}$")


@variant("slope", 1, "Slope from two points")
def _slope1(ctx: Ctx) -> Problem:
    x1, y1, x2, y2 = _two_points(ctx)
    m = Fraction(y2 - y1, x2 - x1)
    return Problem(f"Find the slope of the line through $({x1}, {y1})$ and $({x2}, {y2})$.",
                   f"$m = {frac(m)}$", steps(_slope_step(x1, y1, x2, y2)),
                   facts={"points": [(x1, y1), (x2, y2)], "m": m})


def _lattice_line(ctx: Ctx, span: int = 7):
    """Two lattice points on a non-horizontal, non-vertical line, both inside the grid."""
    while True:
        p = (ctx.rng.randint(-span + 1, span - 1), ctx.rng.randint(-span + 1, span - 1))
        q = (ctx.rng.randint(-span + 1, span - 1), ctx.rng.randint(-span + 1, span - 1))
        if p[0] != q[0] and p[1] != q[1] and abs(q[0] - p[0]) >= 2:
            return tuple(sorted((p, q)))


@variant("slope", 1, "Slope from a graph")
def _slope_graph(ctx: Ctx) -> Problem:
    (x1, y1), (x2, y2) = _lattice_line(ctx)
    m = Fraction(y2 - y1, x2 - x1)
    return Problem("Find the slope of the line shown. The marked points are on the grid.",
                   f"$m = {frac(m)}$",
                   steps(f"Read the marked points: $({x1}, {y1})$ and $({x2}, {y2})$",
                         f"Rise ${y2 - y1}$, run ${x2 - x1}$", _slope_step(x1, y1, x2, y2)),
                   facts={"points": [(x1, y1), (x2, y2)], "m": m, "figure_required": True},
                   figure=draw.coordinate_line((x1, y1), (x2, y2)))


@variant("slope", 2, "Equation of a line from a graph")
def _slope_graph_eq(ctx: Ctx) -> Problem:
    while True:
        b = ctx.rng.randint(-5, 5)
        run, rise = ctx.rng.randint(1, 4), nz(ctx.rng, -5, 5)
        k = ctx.rng.randint(1, 2)
        q = (run * k, b + rise * k)
        if abs(q[1]) <= 7 and run * k <= 7 and math.gcd(rise, run) == 1:
            break
    m = Fraction(rise, run)
    return Problem("Write the equation of the line shown in slope-intercept form.",
                   f"${_line_tex(m, Fraction(b))}$",
                   steps(f"The line crosses the $y$-axis at $(0, {b})$, so $b = {b}$",
                         f"From $(0, {b})$ to $({q[0]}, {q[1]})$: rise ${q[1] - b}$, run ${q[0]}$, so $m = {frac(m)}$",
                         f"$y = mx + b$: ${_line_tex(m, Fraction(b))}$"),
                   facts={"points": [(0, b), q], "m": m, "b": Fraction(b), "figure_required": True},
                   figure=draw.coordinate_line((0, b), q))


@variant("slope", 2, "Equation of a line")
def _slope2(ctx: Ctx) -> Problem:
    x1, y1, x2, y2 = _two_points(ctx)
    m = Fraction(y2 - y1, x2 - x1)
    b = y1 - m * x1
    return Problem(f"Find the equation, in slope-intercept form, of the line through "
                   f"$({x1}, {y1})$ and $({x2}, {y2})$.",
                   f"${_line_tex(m, b)}$",
                   steps(_slope_step(x1, y1, x2, y2),
                         f"Use $({x1}, {y1})$ in $y = mx + b$: ${y1} = {paren(m)}({x1}) + b$, so $b = {frac(b)}$",
                         f"${_line_tex(m, b)}$"),
                   facts={"points": [(x1, y1), (x2, y2)], "m": m, "b": b})


@variant("slope", 3, "Perpendicular lines")
def _slope3(ctx: Ctx) -> Problem:
    m = Fraction(nz(ctx.rng, -6, 6), ctx.rng.randint(1, 4))
    b0 = ctx.rng.randint(-8, 8)
    px, py = ctx.rng.randint(-6, 6), ctx.rng.randint(-6, 6)
    mp = -1 / m
    b = py - mp * px
    return Problem(f"Find the equation of the line perpendicular to ${_line_tex(m, Fraction(b0))}$ "
                   f"passing through $({px}, {py})$.",
                   f"${_line_tex(mp, b)}$",
                   steps(f"The given slope is ${frac(m)}$; a perpendicular slope is its negative reciprocal: ${frac(mp)}$",
                         f"Use $({px}, {py})$: ${py} = {paren(mp)}({px}) + b$, so $b = {frac(b)}$",
                         f"${_line_tex(mp, b)}$"),
                   facts={"m0": m, "points": [(px, py)], "m": mp, "b": b})


topic("trig_right", "math", "Right triangles", "Right-triangle trigonometry",
      "SOH-CAH-TOA: missing sides and angles.", courses=['geo', 'precalc'], rounding=True, figures=True)

_SIDE_RATIO = {"hypotenuse": lambda t: 1, "opposite": math.sin, "adjacent": math.cos}
# which ratio links two sides: (top, bottom) of the fraction
_RATIO = {frozenset({"opposite", "hypotenuse"}): ("\\sin", "opposite", "hypotenuse"),
          frozenset({"adjacent", "hypotenuse"}): ("\\cos", "adjacent", "hypotenuse"),
          frozenset({"opposite", "adjacent"}): ("\\tan", "opposite", "adjacent")}


def _side_phrase(side: str) -> str:
    return "the hypotenuse" if side == "hypotenuse" else f"the side {side} to the angle"


def _trig_side(ctx: Ctx, known: str, want: str) -> Problem:
    th, v = ctx.rng.randint(15, 75), ctx.rng.randint(3, 40)
    t = math.radians(th)
    ans = v / _SIDE_RATIO[known](t) * _SIDE_RATIO[want](t)
    fn, top, bottom = _RATIO[frozenset({known, want})]
    hyp = v / _SIDE_RATIO[known](t)
    sides = {"adjacent": hyp * math.cos(t), "opposite": hyp * math.sin(t), "hypotenuse": hyp}
    label = {known: f"{v} cm", want: "x"}
    fig = draw.right_triangle(sides["adjacent"], sides["opposite"], label_a=label.get("adjacent", ""),
                              label_b=label.get("opposite", ""), label_c=label.get("hypotenuse", ""),
                              angle_at="base", angle_label=f"{th}°")
    frac_tex = f"\\frac{{x}}{{{v}}}" if want == top else f"\\frac{{{v}}}{{x}}"
    solve = (f"$x = {v}{fn} {th}^\\circ$" if want == top else f"$x = \\frac{{{v}}}{{{fn} {th}^\\circ}}$")
    return Problem(f"In a right triangle, one acute angle measures ${th}^\\circ$ and {_side_phrase(known)} is "
                   f"${v}$ cm long. Find the length of {_side_phrase(want)}." + ctx.round_note(),
                   f"${ctx.rnd(ans)}{U('cm')}$",
                   steps(f"The {top} and {bottom} sides are linked by ${fn}$: ${fn}\\theta = \\frac{{\\text{{{top[:3]}}}}}"
                         f"{{\\text{{{bottom[:3]}}}}}$",
                         f"${fn} {th}^\\circ = {frac_tex}$", f"{solve} $\\approx {ctx.rnd(ans)}{U('cm')}$"),
                   facts={"theta": th, "known": (known, v), "want": (want, ans)}, figure=fig)


# Level 1: the unknown is found by multiplying; level 2: by dividing.
variant("trig_right", 1, "Find a side (unknown in numerator)")(lambda c: _trig_side(c, "hypotenuse", "opposite"))
variant("trig_right", 1, "Find a side (unknown in numerator)")(lambda c: _trig_side(c, "hypotenuse", "adjacent"))
variant("trig_right", 1, "Find a side (unknown in numerator)")(lambda c: _trig_side(c, "adjacent", "opposite"))
variant("trig_right", 2, "Find a side (unknown in denominator)")(lambda c: _trig_side(c, "opposite", "hypotenuse"))
variant("trig_right", 2, "Find a side (unknown in denominator)")(lambda c: _trig_side(c, "adjacent", "hypotenuse"))
variant("trig_right", 2, "Find a side (unknown in denominator)")(lambda c: _trig_side(c, "opposite", "adjacent"))


@variant("trig_right", 3, "Find an angle")
def _trig_angle(ctx: Ctx) -> Problem:
    a, b = ctx.rng.sample(range(3, 31), 2)
    if ctx.rng.random() < 0.5:
        th = math.degrees(math.atan2(a, b))
        return Problem(f"A right triangle has legs ${a}$ m (opposite angle $\\theta$) and ${b}$ m (adjacent to "
                       "$\\theta$). Find $\\theta$ in degrees." + ctx.round_note(),
                       f"$\\theta \\approx {ctx.rnd(th)}^\\circ$",
                       steps("Opposite and adjacent are linked by tangent: $\\tan\\theta = \\frac{\\text{opp}}{\\text{adj}}$",
                             f"$\\tan\\theta = \\frac{{{a}}}{{{b}}}$",
                             f"$\\theta = \\tan^{{-1}}\\left(\\frac{{{a}}}{{{b}}}\\right) \\approx {ctx.rnd(th)}^\\circ$"),
                       facts={"opp": a, "adj": b, "theta": th},
                       figure=draw.right_triangle(b, a, label_a=f"{b} m", label_b=f"{a} m", angle_at="base",
                                                  angle_label="θ"))
    a, c = min(a, b), max(a, b)
    th = math.degrees(math.asin(a / c))
    return Problem(f"A ${c}$ ft ramp rises ${a}$ ft. What angle does the ramp make with the ground?"
                   + ctx.round_note(), f"$\\theta \\approx {ctx.rnd(th)}^\\circ$",
                   steps("The rise is opposite the angle and the ramp is the hypotenuse: "
                         "$\\sin\\theta = \\frac{\\text{opp}}{\\text{hyp}}$",
                         f"$\\sin\\theta = \\frac{{{a}}}{{{c}}}$",
                         f"$\\theta = \\sin^{{-1}}\\left(\\frac{{{a}}}{{{c}}}\\right) \\approx {ctx.rnd(th)}^\\circ$"),
                   facts={"opp": a, "hyp": c, "theta": th},
                   figure=draw.right_triangle(math.sqrt(c * c - a * a), a, label_b=f"{a} ft", label_c=f"{c} ft",
                                              angle_at="base", angle_label="θ"))


# ======================================================== Calculus

topic("derivatives", "math", "Calculus", "Derivatives",
      "Power rule, then product/chain rules, then quotient & composite functions.", courses=['calc'])


def _poly(ctx: Ctx, deg: int):
    return sum(nz(ctx.rng, -9, 9) * x**k for k in range(deg, -1, -1) if ctx.rng.random() < 0.8 or k == deg)


@variant("derivatives", 1, "Power rule")
def _deriv1(ctx: Ctx) -> Problem:
    f = _poly(ctx, ctx.rng.randint(2, 4))
    return Problem(f"Find $\\dfrac{{d}}{{dx}}$ of $$f(x) = {L(f)}$$", f"$f'(x) = {L(sp.diff(f, x))}$",
                   steps("Power rule term by term: $\\frac{d}{dx}(ax^n) = nax^{n-1}$; constants differentiate to 0",
                         f"$f'(x) = {L(sp.diff(f, x))}$"),
                   facts={"f": f, "df": sp.diff(f, x)})


def _elem(ctx: Ctx):
    k = ctx.rng.randint(1, 5)
    return ctx.rng.choice([sp.sin(k * x), sp.cos(k * x), sp.exp(k * x), sp.log(x), x ** ctx.rng.randint(2, 5)])


@variant("derivatives", 2, "Product & chain rules")
def _deriv2(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.5:
        u, v = ctx.rng.randint(1, 5) * x ** ctx.rng.randint(1, 3), _elem(ctx)
        f = u * v
        rule = (f"Product rule with $u = {L(u)}$, $v = {L(v)}$: $f' = u'v + uv' = "
                f"({L(sp.diff(u, x))})({L(v)}) + ({L(u)})({L(sp.diff(v, x))})$")
    else:
        inner, n = _poly(ctx, 2), ctx.rng.randint(2, 5)
        f = inner**n
        rule = (f"Chain rule: $f' = {n}({L(inner)})^{{{n - 1}}} \\cdot ({L(sp.diff(inner, x))})$")
    df = sp.factor(sp.diff(f, x))
    return Problem(f"Differentiate: $$f(x) = {L(f)}$$", f"$f'(x) = {L(df)}$",
                   steps(rule, f"Simplify: $f'(x) = {L(df)}$"), facts={"f": f, "df": df})


@variant("derivatives", 3, "Quotient & composite functions")
def _deriv3(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.5:
        top, bottom = _poly(ctx, 1), x**2 + ctx.rng.randint(1, 9)
        f = top / bottom
        rule = (f"Quotient rule: $f' = \\frac{{({L(sp.diff(top, x))})({L(bottom)}) - ({L(top)})({L(sp.diff(bottom, x))})}}"
                f"{{({L(bottom)})^2}}$")
    else:
        outer = ctx.rng.choice([sp.sin, sp.cos, sp.exp, sp.sqrt])
        inner = _poly(ctx, 2)
        f = outer(inner)
        rule = f"Chain rule with inner function $u = {L(inner)}$, $u' = {L(sp.diff(inner, x))}$"
    df = sp.simplify(sp.diff(f, x))
    return Problem(f"Differentiate: $$f(x) = {L(f)}$$", f"$f'(x) = {L(df)}$",
                   steps(rule, f"Simplify: $f'(x) = {L(df)}$"), facts={"f": f, "df": df})


topic("integrals", "math", "Calculus", "Integrals",
      "Indefinite polynomial integrals, u-substitution and definite integrals.", courses=['calc'])


@variant("integrals", 1, "Polynomials")
def _int1(ctx: Ctx) -> Problem:
    f = _poly(ctx, ctx.rng.randint(1, 3))
    F = sp.integrate(f, x)
    return Problem(f"Evaluate: $$\\int \\left({L(f)}\\right)\\,dx$$", f"${L(F)} + C$",
                   steps("Reverse power rule term by term: $\\int ax^n\\,dx = \\frac{a}{n+1}x^{n+1}$",
                         f"${L(F)} + C$"),
                   facts={"f": f, "F": F})


@variant("integrals", 2, "u-substitution")
def _int2(ctx: Ctx) -> Problem:
    a, b = ctx.rng.randint(1, 4), nz(ctx.rng, -5, 5)
    g = a * x**2 + b if ctx.rng.random() < 0.5 else a * x + b
    kind = ctx.rng.choice(["sin", "cos", "exp", "pow"])
    u = sp.Symbol("u")
    if kind == "pow":
        n = ctx.rng.randint(2, 5)
        f, F, Fu = g**n * sp.diff(g, x), g ** (n + 1) / (n + 1), u ** (n + 1) / (n + 1)
        inner = u**n
    else:
        outer, anti = {"sin": (sp.sin, lambda w: -sp.cos(w)), "cos": (sp.cos, sp.sin),
                       "exp": (sp.exp, sp.exp)}[kind]
        f, F, Fu, inner = outer(g) * sp.diff(g, x), anti(g), anti(u), outer(u)
    return Problem(f"Evaluate using substitution: $$\\int {L(f)}\\,dx$$", f"${L(F)} + C$",
                   steps(f"Let $u = {L(g)}$, so $du = {L(sp.diff(g, x))}\\,dx$",
                         f"$\\int {L(inner)}\\,du = {L(Fu)} + C$", f"Substitute back: ${L(F)} + C$"),
                   facts={"f": f, "F": F})


@variant("integrals", 3, "Definite integrals")
def _int3(ctx: Ctx) -> Problem:
    f = _poly(ctx, ctx.rng.randint(2, 3))
    lo = ctx.rng.randint(-3, 2)
    hi = lo + ctx.rng.randint(1, 4)
    F = sp.integrate(f, x)
    val = sp.integrate(f, (x, lo, hi))
    return Problem(f"Evaluate: $$\\int_{{{lo}}}^{{{hi}}} \\left({L(f)}\\right)\\,dx$$", f"${L(val)}$",
                   steps(f"Antiderivative: $F(x) = {L(F)}$",
                         f"$F({hi}) - F({paren(lo)}) = {L(F.subs(x, hi))} - {paren(L(F.subs(x, lo)))} = {L(val)}$"),
                   facts={"f": f, "lo": lo, "hi": hi, "val": val})


topic("limits", "math", "Limits", "Limits",
      "Algebraic limits, removable discontinuities and limits at infinity.", courses=['precalc', 'calc'])


@variant("limits", 1, "Direct substitution")
def _lim1(ctx: Ctx) -> Problem:
    f = _poly(ctx, 2)
    a = ctx.rng.randint(-4, 4)
    return Problem(f"Evaluate: $$\\lim_{{x \\to {a}}} \\left({L(f)}\\right)$$", f"${L(f.subs(x, a))}$",
                   steps("A polynomial is continuous, so substitute directly:",
                         f"${L(f).replace('x', f'({a})')} = {L(f.subs(x, a))}$"),
                   facts={"expr": f, "a": a, "val": f.subs(x, a)})


@variant("limits", 2, "Factor and cancel")
def _lim2(ctx: Ctx) -> Problem:
    a, b = ctx.rng.randint(-6, 6), ctx.rng.randint(-6, 6)
    c = ctx.rng.randint(-6, 6)
    while c == a:
        c = ctx.rng.randint(-6, 6)
    num_, den = sp.expand((x - a) * (x - b)), sp.expand((x - a) * (x - c))
    val = sp.Rational(a - b, a - c)
    return Problem(f"Evaluate: $$\\lim_{{x \\to {a}}} \\frac{{{L(num_)}}}{{{L(den)}}}$$", f"${L(val)}$",
                   steps(f"Direct substitution gives $\\frac{{0}}{{0}}$, so factor: "
                         f"$\\frac{{({L(x - a)})({L(x - b)})}}{{({L(x - a)})({L(x - c)})}}$",
                         f"Cancel ${L(x - a)}$: ${L((x - b) / (x - c))}$",
                         f"Substitute $x = {a}$: $\\frac{{{a} - {paren(b)}}}{{{a} - {paren(c)}}} = {L(val)}$"),
                   facts={"expr": num_ / den, "a": a, "val": val})


@variant("limits", 3, "sin(x)/x limits")
def _lim_trig(ctx: Ctx) -> Problem:
    k = ctx.rng.randint(2, 9)
    m = ctx.rng.randint(1, 5)
    return Problem(f"Evaluate: $$\\lim_{{x \\to 0}} \\frac{{\\sin({k}x)}}{{{L(m * x)}}}$$",
                   f"${L(sp.Rational(k, m))}$",
                   steps(f"Rewrite: $\\frac{{\\sin({k}x)}}{{{L(m * x)}}} = \\frac{{{k}}}{{{m}}} \\cdot \\frac{{\\sin({k}x)}}{{{k}x}}$",
                         f"Since $\\lim_{{u \\to 0}} \\frac{{\\sin u}}{{u}} = 1$, the limit is ${L(sp.Rational(k, m))}$"),
                   facts={"expr": sp.sin(k * x) / (m * x), "a": 0, "val": sp.Rational(k, m)})


@variant("limits", 3, "Limits at infinity")
def _lim_infinity(ctx: Ctx) -> Problem:
    deg = ctx.rng.randint(2, 3)
    p, q = _poly(ctx, deg), _poly(ctx, deg)
    val = sp.limit(p / q, x, sp.oo)
    lp, lq = sp.Poly(p, x).LC(), sp.Poly(q, x).LC()
    return Problem(f"Evaluate: $$\\lim_{{x \\to \\infty}} \\frac{{{L(p)}}}{{{L(q)}}}$$", f"${L(val)}$",
                   steps("The degrees are equal, so the limit is the ratio of the leading coefficients:",
                         f"$\\frac{{{lp}}}{{{lq}}} = {L(val)}$"),
                   facts={"expr": p / q, "a": sp.oo, "val": val})


# ======================================================== Statistics

topic("stats", "math", "Statistics", "Mean, median, mode & spread",
      "Measures of center and spread for a data set.", courses=['alg1'], rounding=True)


def _dataset(ctx: Ctx, n: int, hi: int) -> list[int]:
    data = [ctx.rng.randint(1, hi) for _ in range(n - 1)]
    data.append(ctx.rng.choice(data))  # guarantee a repeated value
    ctx.rng.shuffle(data)
    return data


def _data_tex(data):
    return ",\\ ".join(map(str, data))


def _median_step(data) -> str:
    s, n = sorted(data), len(data)
    if n % 2:
        return f"Median: the middle (position ${n // 2 + 1}$) value is ${s[n // 2]}$"
    a, b = s[n // 2 - 1], s[n // 2]
    return f"Median: the two middle values are ${a}$ and ${b}$; $\\frac{{{a} + {b}}}{{2}} = {num((a + b) / 2)}$"


@variant("stats", 1, "Median, mode & range")
def _stats1(ctx: Ctx) -> Problem:
    while True:
        data = _dataset(ctx, ctx.rng.randint(5, 9), 20)
        modes = statistics.multimode(data)
        if len(modes) == 1:
            break
    return Problem(f"For the data $${_data_tex(data)}$$ find the median, mode and range.",
                   f"Median ${num(statistics.median(data))}$, mode ${', '.join(map(str, sorted(modes)))}$, "
                   f"range ${max(data) - min(data)}$",
                   steps(f"Sort: ${_data_tex(sorted(data))}$", _median_step(data),
                         f"Mode: ${modes[0]}$ appears most often (${data.count(modes[0])}$ times)",
                         f"Range: ${max(data)} - {min(data)} = {max(data) - min(data)}$"),
                   facts={"data": data})


@variant("stats", 2, "Mean & median")
def _stats2(ctx: Ctx) -> Problem:
    data = _dataset(ctx, ctx.rng.randint(6, 9), 50)
    mean = Fraction(sum(data), len(data))
    exact = mean * 10**ctx.places == int(mean * 10**ctx.places)  # terminates within the rounding place
    mean_txt = num_frac(mean) if exact else ctx.rnd(float(mean))
    return Problem(f"Find the mean and median of $${_data_tex(data)}$$" + ("" if exact else ctx.round_note()),
                   f"Mean ${'=' if exact else r'\approx'} {mean_txt}$, "
                   f"median $= {num(statistics.median(data))}$",
                   steps(f"Mean: $\\frac{{{sum(data)}}}{{{len(data)}}} {'=' if exact else r'\approx'} {mean_txt}$",
                         f"Sort: ${_data_tex(sorted(data))}$", _median_step(data)),
                   facts={"data": data})


@variant("stats", 3, "Standard deviation")
def _stats3(ctx: Ctx) -> Problem:
    data = _dataset(ctx, ctx.rng.randint(5, 8), 30)
    mean = statistics.fmean(data)
    sd = statistics.pstdev(data)
    ss = sum((v - mean) ** 2 for v in data)
    return Problem(f"Find the mean and the population standard deviation of $${_data_tex(data)}$$"
                   + ctx.round_note(), f"$\\mu \\approx {ctx.rnd(mean)}$, $\\sigma \\approx {ctx.rnd(sd)}$",
                   steps(f"Mean: $\\mu = \\frac{{{sum(data)}}}{{{len(data)}}} \\approx {ctx.rnd(mean)}$",
                         f"Sum of squared deviations: $\\sum (x_i - \\mu)^2 \\approx {ctx.rnd(ss)}$",
                         f"$\\sigma = \\sqrt{{\\frac{{\\sum (x_i - \\mu)^2}}{{n}}}} = \\sqrt{{\\frac{{{ctx.rnd(ss)}}}{{{len(data)}}}}} "
                         f"\\approx {ctx.rnd(sd)}$"),
                   facts={"data": data})
