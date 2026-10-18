"""Algebra 1 equation word problems: define a variable, write the equation, solve.

Each problem records its equations and solution in ``facts["word"]`` so the tests can
substitute the solution back in.
"""

from __future__ import annotations

import sympy as sp

from .core import Ctx, Problem, steps, topic, variant

L = sp.latex
n, w, a, s, t, x, d, q = sp.symbols("n w a s t x d q")

topic("word_problems", "math", "Equations", "Equation word problems",
      "Consecutive integers, perimeter, tickets and coins, distance-rate-time and mixtures.", courses=["alg1"])

WORDS = {2: "two", 3: "three", 4: "four"}


def W(eqs, sol) -> dict:
    return {"word": {"eqs": eqs, "sol": sol}}


@variant("word_problems", 1, "Consecutive integers")
def _consecutive(ctx: Ctx) -> Problem:
    kind = ctx.rng.choice(["", "even ", "odd "])
    count = ctx.rng.choice([2, 3, 3, 4])
    gap = 1 if not kind else 2
    start = ctx.rng.randint(-15, 60)
    if kind == "even " and start % 2:
        start += 1
    if kind == "odd " and start % 2 == 0:
        start += 1
    vals = [start + gap * i for i in range(count)]
    total = sum(vals)
    offsets = [gap * i for i in range(count)]
    expr = sum(n + o for o in offsets)
    eq = sp.Eq(expr, total)
    terms = " + ".join(f"({L(n + o)})" if o else "n" for o in offsets)
    return Problem(f"The sum of {WORDS[count]} consecutive {kind}integers is ${total}$. Find the integers.",
                   "$" + ",\\ ".join(map(str, vals)) + "$",
                   steps(f"Let the smallest be $n$; the next are " + ", ".join(f"${L(n + o)}$" for o in offsets[1:]),
                         f"${terms} = {total}$", f"${L(expr)} = {total}$",
                         f"${count}n = {total - sum(offsets)}$, so $n = {start}$",
                         "The integers are " + ", ".join(f"${v}$" for v in vals)),
                   facts=W([eq], {n: start}))


# How the length compares with the width: (wording with {c}, multiplier k, sign of the constant, c range)
_LENGTH_RULES = [("${c}$ cm longer than", 1, 1, (2, 15)), ("twice", 2, 0, (0, 0)),
                 ("${c}$ cm more than twice", 2, 1, (1, 9)), ("${c}$ cm less than three times", 3, -1, (1, 6))]


@variant("word_problems", 1, "Perimeter problems")
def _perimeter(ctx: Ctx) -> Problem:
    text, k, sign, (lo, hi) = ctx.rng.choice(_LENGTH_RULES)
    c = ctx.rng.randint(lo, hi)
    width = ctx.rng.randint(3, 30)
    length = k * width + sign * c
    P = 2 * (length + width)
    lw = k * w + sign * c
    eq = sp.Eq(2 * lw + 2 * w, P)
    return Problem(f"A rectangle's length is {text.replace('{c}', str(c))} its width. Its perimeter is ${P}$ cm. "
                   "Find its length and width.",
                   f"width ${width}$ cm, length ${length}$ cm",
                   steps(f"Let the width be $w$; the length is ${L(lw)}$",
                         f"$2({L(lw)}) + 2w = {P}$", f"${L(sp.expand(2 * lw + 2 * w))} = {P}$",
                         f"${2 * k + 2}w = {P - 2 * sign * c}$, so $w = {width}$",
                         f"Length: ${L(lw.subs(w, width))} = {length}$ cm"),
                   facts=W([eq], {w: width}))


@variant("word_problems", 2, "Tickets and coins")
def _tickets(ctx: Ctx) -> Problem:
    pa = ctx.rng.randint(8, 18)
    ps = ctx.rng.randint(3, pa - 2)
    adults, students = ctx.rng.randint(20, 200), ctx.rng.randint(20, 300)
    N, R = adults + students, pa * adults + ps * students
    eqs = [sp.Eq(a + s, N), sp.Eq(pa * a + ps * s, R)]
    event = ctx.rng.choice(["school play", "basketball game", "band concert", "science fair"])
    return Problem(f"A {event} sold ${N}$ tickets. Adult tickets cost ${pa}$ dollars and student tickets cost "
                   f"${ps}$ dollars. Ticket sales totaled ${R}$ dollars. How many of each type were sold?",
                   f"${adults}$ adult and ${students}$ student tickets",
                   steps("Let $a$ = adult tickets and $s$ = student tickets.",
                         f"$a + s = {N}$ and ${pa}a + {ps}s = {R}$",
                         f"Substitute $s = {N} - a$: ${pa}a + {ps}({N} - a) = {R}$",
                         f"${pa - ps}a + {ps * N} = {R}$, so ${pa - ps}a = {R - ps * N}$ and $a = {adults}$",
                         f"$s = {N} - {adults} = {students}$"),
                   facts=W(eqs, {a: adults, s: students}))


@variant("word_problems", 2, "Tickets and coins")
def _coins(ctx: Ctx) -> Problem:
    (n1, v1), (n2, v2) = ctx.rng.choice([(("nickels", 5), ("dimes", 10)), (("dimes", 10), ("quarters", 25)),
                                         (("nickels", 5), ("quarters", 25))])
    c1, c2 = ctx.rng.randint(5, 40), ctx.rng.randint(5, 40)
    N, cents = c1 + c2, v1 * c1 + v2 * c2
    eqs = [sp.Eq(d + q, N), sp.Eq(v1 * d + v2 * q, cents)]
    return Problem(f"A jar holds ${N}$ coins, all {n1} and {n2}, worth ${cents / 100:.2f}$ dollars in total. "
                   f"How many of each coin are there?",
                   f"${c1}$ {n1} and ${c2}$ {n2}",
                   steps(f"Let $d$ = {n1} and $q$ = {n2}. Work in cents: ${cents / 100:.2f}$ dollars $= {cents}$ cents.",
                         f"$d + q = {N}$ and ${v1}d + {v2}q = {cents}$",
                         f"Substitute $d = {N} - q$: ${v1}({N} - q) + {v2}q = {cents}$",
                         f"${v2 - v1}q = {cents - v1 * N}$, so $q = {c2}$", f"$d = {N} - {c2} = {c1}$"),
                   facts=W(eqs, {d: c1, q: c2}))


@variant("word_problems", 2, "Distance, rate and time")
def _opposite(ctx: Ctx) -> Problem:
    r1, r2 = ctx.rng.randrange(30, 75, 5), ctx.rng.randrange(40, 90, 5)
    hours = ctx.rng.choice([1, 1.5, 2, 2.5, 3, 3.5, 4, 5])
    D = (r1 + r2) * hours
    what = ctx.rng.choice([("Two trains leave the same station", "mph"), ("Two cars leave the same rest stop", "mph"),
                           ("Two cyclists leave the same park", "mph")])
    if what[0].startswith("Two cyclists"):
        r1, r2 = r1 // 5, r2 // 5
        D = (r1 + r2) * hours
    eq = sp.Eq((r1 + r2) * t, D)
    D_txt = f"{D:g}"
    return Problem(f"{what[0]} at the same time, traveling in opposite directions at ${r1}$ mph and ${r2}$ mph. "
                   f"After how many hours will they be ${D_txt}$ miles apart?",
                   f"${hours:g}$ hours",
                   steps("Let $t$ = hours. Distance = rate × time, and the distances add:",
                         f"${r1}t + {r2}t = {D_txt}$", f"${r1 + r2}t = {D_txt}$, so $t = {hours:g}$"),
                   facts=W([eq], {t: sp.nsimplify(hours)}))


@variant("word_problems", 3, "Mixtures")
def _mixture(ctx: Ctx) -> Problem:
    while True:
        p_low, p_high = ctx.rng.randrange(5, 40, 5), ctx.rng.randrange(45, 95, 5)
        base, add = ctx.rng.randint(2, 20), ctx.rng.randint(1, 20)
        total_pct = p_low * base + p_high * add
        if total_pct % (base + add) == 0:
            p_mix = total_pct // (base + add)
            if p_low < p_mix < p_high:
                break
    eq = sp.Eq(sp.Rational(p_high, 100) * x + sp.Rational(p_low, 100) * base, sp.Rational(p_mix, 100) * (x + base))
    what = ctx.rng.choice(["acid solution", "saltwater solution", "juice drink", "antifreeze mixture"])
    return Problem(f"How many liters of a ${p_high}\\%$ {what} must be added to ${base}$ liters of a ${p_low}\\%$ "
                   f"{what} to make a ${p_mix}\\%$ {what}?",
                   f"${add}$ liters",
                   steps(f"Let $x$ = liters of the ${p_high}\\%$ {what}.",
                         "The amount of the key ingredient is the same before and after mixing:",
                         f"${p_high / 100:g}x + {p_low / 100:g}({base}) = {p_mix / 100:g}(x + {base})$",
                         f"${p_high / 100:g}x - {p_mix / 100:g}x = {p_mix / 100:g}({base}) - {p_low / 100:g}({base})$",
                         f"${(p_high - p_mix) / 100:g}x = {(p_mix - p_low) * base / 100:g}$, so $x = {add}$"),
                   facts=W([eq], {x: add}))


@variant("word_problems", 3, "Catch-up problems")
def _catch_up(ctx: Ctx) -> Problem:
    while True:
        r1, r2 = ctx.rng.randrange(30, 60, 5), ctx.rng.randrange(45, 80, 5)
        head = ctx.rng.choice([0.5, 1, 1.5, 2])
        if r2 > r1 and (r1 * head) % (r2 - r1) == 0:
            hours = r1 * head / (r2 - r1)
            if 0.5 <= hours <= 8:
                break
    eq = sp.Eq(r2 * t, r1 * (t + sp.nsimplify(head)))
    return Problem(f"A truck leaves a warehouse traveling at ${r1}$ mph. ${head:g}$ hours later, a car leaves the "
                   f"same warehouse on the same road at ${r2}$ mph. How many hours after the car leaves does it "
                   "catch up to the truck?",
                   f"${hours:g}$ hours",
                   steps("Let $t$ = hours the car travels; the truck has traveled $t + " f"{head:g}$ hours.",
                         "When the car catches up, they have gone the same distance:",
                         f"${r2}t = {r1}(t + {head:g})$", f"${r2}t - {r1}t = {r1 * head:g}$",
                         f"${r2 - r1}t = {r1 * head:g}$, so $t = {hours:g}$"),
                   facts=W([eq], {t: sp.nsimplify(hours)}))
