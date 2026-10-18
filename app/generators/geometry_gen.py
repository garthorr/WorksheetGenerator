"""Geometry: angle relationships, special right triangles, similarity, coordinate geometry,
circles, volume and surface area, transformations, and the laws of sines and cosines.

Every problem records ``facts["kind"]`` plus the values the tests need to check it
independently (tests/test_quality.py → check_geometry).
"""

from __future__ import annotations

import math
from fractions import Fraction

import sympy as sp

from . import drawings as draw
from .core import Ctx, Problem, U, nz, steps, topic, variant
from .math_gen import num_frac, paren, pi_tex, radical_steps

L = sp.latex
X, Y = sp.symbols("x y")


def deg(v) -> str:
    return f"{num_frac(Fraction(v))}^\\circ"


def expr_label(a: int, b: int) -> str:
    """Plain-text angle expression for a figure label, e.g. (3x + 10)°."""
    lead = "" if a == 1 else str(a)
    if b == 0:
        return f"{lead}x°"
    return f"({lead}x {'+' if b > 0 else '−'} {abs(b)})°"


def expr_tex(a: int, b: int) -> str:
    return L(a * X + b)


def solve_steps(lhs, rhs) -> list[str]:
    """Steps that solve a linear equation in x, starting from it simplified (lhs, rhs are sympy expressions)."""
    lhs, rhs = sp.expand(lhs), sp.expand(rhs)
    e = lhs - rhs
    p, q = e.coeff(X), e.subs(X, 0)
    out = [f"${L(lhs)} = {L(rhs)}$"]
    if rhs.has(X) or lhs.subs(X, 0) != 0:
        out.append(f"${L(p * X)} = {L(-q)}$")
    if p != 1:
        out.append(f"$x = {L(-q / p)}$")
    return out


def plain(e) -> str:
    """A radical as plain text for a figure label: 5*sqrt(2) -> 5√2, 7*sqrt(2)/2 -> 7√2/2."""
    e = sp.nsimplify(e)
    if e.is_Integer:
        return str(e)
    coef, rad = e.as_coeff_Mul()
    p, q = sp.Rational(coef).p, sp.Rational(coef).q
    text = f"{'' if p == 1 else p}√{rad ** 2}"
    return f"{text}/{q}" if q != 1 else text


def value_tex(ctx: Ctx, e, unit: str = "") -> str:
    """An exact length in the chosen answer form; whole numbers are shown as they are."""
    e = sp.nsimplify(e)
    if e.is_Integer:
        return f"{e}{U(unit) if unit else ''}"
    return ctx.exact_or_decimal(L(e), float(e), unit)


# ======================================================================== Angle relationships

topic("angles", "math", "Angles & triangles", "Angle relationships",
      "Complements, supplements, parallel lines cut by a transversal, triangle and polygon angles.",
      courses=["geo"], figures=True)


@variant("angles", 1, "Complements & supplements")
def _comp_supp(ctx: Ctx) -> Problem:
    kind, total = ctx.rng.choice([("complement", 90), ("supplement", 180)])
    a = ctx.rng.randint(5, total - 5)
    return Problem(f"Find the {kind} of a ${a}^\\circ$ angle.", f"${total - a}^\\circ$",
                   steps(f"{kind.capitalize()}ary angles add to ${total}^\\circ$.", f"${total} - {a} = {total - a}^\\circ$"),
                   facts={"kind": "angle_pair", "a": a, "total": total, "x": total - a})


# Angle positions at the two intersections, numbered clockwise from upper-left (see drawings.parallel_lines):
# even positions measure theta, odd ones 180 - theta.
_NAMED_PAIRS = {(1, 5): "corresponding", (2, 6): "corresponding", (3, 7): "corresponding", (4, 8): "corresponding",
                (3, 5): "alternate interior", (4, 6): "alternate interior",
                (4, 5): "same-side interior", (3, 6): "same-side interior",
                (1, 7): "alternate exterior", (2, 8): "alternate exterior",
                (1, 3): "vertical", (2, 4): "vertical", (5, 7): "vertical", (6, 8): "vertical",
                (1, 2): "a linear pair of", (2, 3): "a linear pair of", (5, 6): "a linear pair of",
                (6, 7): "a linear pair of"}


def _transversal_angle(theta: int, pos: int) -> int:
    return theta if pos % 2 == 0 else 180 - theta


def _pair(ctx: Ctx):
    (p, q), name = ctx.rng.choice(list(_NAMED_PAIRS.items()))
    return ((p, q) if ctx.rng.random() < 0.5 else (q, p)), name


def _pair_reason(name: str, equal: bool) -> str:
    if name.startswith("a linear pair"):
        return "The angles form a linear pair, so they are supplementary."
    return f"The angles are {name} angles, so they are {'equal' if equal else 'supplementary'}."


@variant("angles", 1, "Parallel lines & transversals")
def _transversal(ctx: Ctx) -> Problem:
    theta = ctx.rng.choice([*range(35, 81, 5), *range(100, 146, 5)])
    (kp, up), name = _pair(ctx)
    known, x = _transversal_angle(theta, kp), _transversal_angle(theta, up)
    equal = known == x
    return Problem("Lines $\\ell$ and $m$ are parallel. Find $x$.", f"$x = {x}^\\circ$",
                   steps(_pair_reason(name, equal),
                         f"$x = {known}^\\circ$" if equal else f"$x = 180 - {known} = {x}^\\circ$"),
                   facts={"kind": "transversal", "theta": theta, "known": (kp, known), "unknown": (up, x),
                          "figure_required": True},
                   figure=draw.parallel_lines(theta, {kp: f"{known}°", up: "x"}))


@variant("angles", 2, "Parallel lines with algebra")
def _transversal_alg(ctx: Ctx) -> Problem:
    while True:
        theta = ctx.rng.choice([*range(40, 81, 5), *range(100, 141, 5)])
        (p1, p2), name = _pair(ctx)
        ang1, ang2 = _transversal_angle(theta, p1), _transversal_angle(theta, p2)
        x0, a, c = ctx.rng.randint(5, 25), ctx.rng.randint(2, 6), ctx.rng.randint(2, 6)
        b, d = ang1 - a * x0, ang2 - c * x0
        if (ang1 != ang2 or a != c) and b and d and abs(b) < 100 and abs(d) < 100:
            break
    equal = ang1 == ang2
    e1, e2 = a * X + b, c * X + d
    work = (solve_steps(e1, e2) if equal else
            [f"$({L(e1)}) + ({L(e2)}) = 180$", *solve_steps(e1 + e2, sp.Integer(180))])
    return Problem("Lines $\\ell$ and $m$ are parallel. Find $x$ and the measure of each labeled angle.",
                   f"$x = {x0}$; the angles measure ${ang1}^\\circ$ and ${ang2}^\\circ$",
                   steps(_pair_reason(name, equal), *work,
                         f"${expr_tex(a, b)} = {ang1}^\\circ$ and ${expr_tex(c, d)} = {ang2}^\\circ$"),
                   facts={"kind": "transversal_alg", "theta": theta, "pos": (p1, p2), "e1": (a, b), "e2": (c, d),
                          "x": x0, "angles": (ang1, ang2), "figure_required": True},
                   figure=draw.parallel_lines(theta, {p1: expr_label(a, b), p2: expr_label(c, d)}))


@variant("angles", 2, "Angle pairs with algebra")
def _pair_alg(ctx: Ctx) -> Problem:
    kind, total = ctx.rng.choice([("complementary", 90), ("supplementary", 180), ("vertical", 0)])
    while True:
        x0, a, c = ctx.rng.randint(3, 25), ctx.rng.randint(1, 6), ctx.rng.randint(1, 6)
        ang1 = ctx.rng.randint(15, (total or 160) - 15)
        ang2 = total - ang1 if total else ang1
        b, d = ang1 - a * x0, ang2 - c * x0
        if (total or a != c) and b and d:
            break
    e1, e2 = a * X + b, c * X + d
    work = ([f"$({L(e1)}) + ({L(e2)}) = {total}$", *solve_steps(e1 + e2, sp.Integer(total))] if total else
            solve_steps(e1, e2))
    return Problem(f"$\\angle A$ and $\\angle B$ are {kind} angles with $m\\angle A = ({expr_tex(a, b)})^\\circ$ and "
                   f"$m\\angle B = ({expr_tex(c, d)})^\\circ$. Find $x$ and both angle measures.",
                   f"$x = {x0}$; $m\\angle A = {ang1}^\\circ$, $m\\angle B = {ang2}^\\circ$",
                   steps(f"{kind.capitalize()} angles add to ${total}^\\circ$:" if total else "Vertical angles are equal:",
                         *work, f"$m\\angle A = {ang1}^\\circ$, $m\\angle B = {ang2}^\\circ$"),
                   facts={"kind": "pair_alg", "total": total, "e1": (a, b), "e2": (c, d), "x": x0,
                          "angles": (ang1, ang2)})


@variant("angles", 1, "Triangle angle sum")
def _triangle_sum(ctx: Ctx) -> Problem:
    while True:  # no angle under 30°, so every label fits inside its corner
        A, B = ctx.rng.randint(30, 85), ctx.rng.randint(30, 85)
        C = 180 - A - B
        if 30 <= C <= 110:
            break
    return Problem(f"In $\\triangle ABC$, $m\\angle A = {A}^\\circ$ and $m\\angle B = {B}^\\circ$. Find $m\\angle C$.",
                   f"$m\\angle C = {C}^\\circ$",
                   steps("The angles of a triangle add to $180^\\circ$.", f"$m\\angle C = 180 - {A} - {B} = {C}^\\circ$"),
                   facts={"kind": "triangle_sum", "angles": (A, B, C), "want": [C]},
                   figure=draw.triangle(A, B, angle_labels={"A": f"{A}°", "B": f"{B}°", "C": "x"}, vertex_names="ABC"))


@variant("angles", 2, "Triangle angle sum")
def _triangle_sum_alg(ctx: Ctx) -> Problem:
    while True:
        x0 = ctx.rng.randint(8, 40)
        a1, b1, a2, b2 = ctx.rng.randint(1, 3), ctx.rng.randint(-10, 30), ctx.rng.randint(2, 4), ctx.rng.randint(-10, 30)
        A, B = a1 * x0 + b1, a2 * x0 + b2
        C = 180 - A - B
        if 40 <= A <= 100 and 40 <= B <= 100 and 40 <= C <= 100 and b1 and b2:
            break
    e1, e2 = a1 * X + b1, a2 * X + b2
    return Problem(f"In $\\triangle ABC$, $m\\angle A = ({expr_tex(a1, b1)})^\\circ$, $m\\angle B = ({expr_tex(a2, b2)})^\\circ$ "
                   f"and $m\\angle C = {C}^\\circ$. Find $x$ and the measures of $\\angle A$ and $\\angle B$.",
                   f"$x = {x0}$; $m\\angle A = {A}^\\circ$, $m\\angle B = {B}^\\circ$",
                   steps("The angles add to $180^\\circ$:", f"$({L(e1)}) + ({L(e2)}) + {C} = 180$",
                         *solve_steps(e1 + e2 + C, sp.Integer(180)),
                         f"$m\\angle A = {A}^\\circ$, $m\\angle B = {B}^\\circ$"),
                   facts={"kind": "triangle_sum", "angles": (A, B, C), "x": x0, "e1": (a1, b1), "e2": (a2, b2),
                          "want": [x0, A, B]},
                   figure=draw.triangle(A, B, angle_labels={"A": expr_label(a1, b1), "B": expr_label(a2, b2),
                                                            "C": f"{C}°"}, vertex_names="ABC"))


@variant("angles", 3, "Exterior angle theorem")
def _exterior(ctx: Ctx) -> Problem:
    while True:
        x0 = ctx.rng.randint(5, 30)
        a, b, c, d = ctx.rng.randint(1, 4), ctx.rng.randint(-10, 30), ctx.rng.randint(2, 6), ctx.rng.randint(-20, 20)
        A, ext = a * x0 + b, c * x0 + d
        C = ext - A
        if 30 <= A <= 90 and 30 <= C <= 90 and 40 <= 180 - ext <= 110 and b and d and a != c:
            break
    e_ext, e_A = c * X + d, a * X + b
    return Problem(f"In $\\triangle ABC$, side $\\overline{{AB}}$ is extended past $B$. The exterior angle at $B$ measures "
                   f"$({expr_tex(c, d)})^\\circ$, $m\\angle A = ({expr_tex(a, b)})^\\circ$ and $m\\angle C = {C}^\\circ$. "
                   "Find $x$ and the measure of the exterior angle.",
                   f"$x = {x0}$; the exterior angle measures ${ext}^\\circ$",
                   steps("An exterior angle equals the sum of the two remote interior angles:",
                         f"${L(e_ext)} = ({L(e_A)}) + {C}$", *solve_steps(e_ext, e_A + C),
                         f"Exterior angle: ${L(e_ext)} = {ext}^\\circ$"),
                   facts={"kind": "exterior", "A": A, "C": C, "ext": ext, "x": x0, "e_A": (a, b), "e_ext": (c, d)},
                   figure=draw.triangle(A, 180 - ext, angle_labels={"A": expr_label(a, b), "C": f"{C}°"},
                                        exterior_at_B=expr_label(c, d), vertex_names="ABC"))


_POLYGONS = {5: "pentagon", 6: "hexagon", 8: "octagon", 9: "nonagon", 10: "decagon", 12: "dodecagon"}


@variant("angles", 3, "Polygon angles")
def _polygon(ctx: Ctx) -> Problem:
    n = ctx.rng.choice([5, 6, 8, 9, 10, 12, 15, 18, 20, 24, 30, 36])
    total, each, ext = (n - 2) * 180, Fraction((n - 2) * 180, n), Fraction(360, n)
    name = _POLYGONS.get(n, f"{n}-sided polygon")
    if ctx.rng.random() < 0.5:
        return Problem(f"Find (a) the sum of the interior angles and (b) the measure of each interior angle of a "
                       f"regular {name}.",
                       f"(a) ${total}^\\circ$ (b) ${deg(each)}$",
                       steps(f"(a) Sum $= (n - 2) \\cdot 180^\\circ = ({n} - 2)(180^\\circ) = {total}^\\circ$",
                             f"(b) Each angle $= \\frac{{{total}^\\circ}}{{{n}}} = {deg(each)}$"),
                       facts={"kind": "polygon", "n": n, "sum": total, "each": each, "want": [total, each]},
                       figure=draw.regular_polygon(n) if n <= 12 else "")
    return Problem(f"Each interior angle of a regular polygon measures ${deg(each)}$. How many sides does it have?",
                   f"${n}$ sides",
                   steps(f"Each exterior angle is $180^\\circ - {deg(each)} = {deg(ext)}$.",
                         f"The exterior angles add to $360^\\circ$, so $n = \\frac{{360}}{{{num_frac(ext)}}} = {n}$"),
                   facts={"kind": "polygon", "n": n, "sum": total, "each": each, "want": [n]})


# ======================================================================== Special right triangles

topic("special_right", "math", "Right triangles", "Special right triangles",
      "45-45-90 and 30-60-90 triangles, in simplest radical form.", courses=["geo", "precalc"], exact_forms=True,
      rounding=True, figures=True)

R2, R3 = sp.sqrt(2), sp.sqrt(3)
_GIVEN = {"short": "a shorter leg", "long": "a longer leg", "hyp": "a hypotenuse", "leg": "legs"}
_FIND = {"short": "the shorter leg", "long": "the longer leg", "hyp": "the hypotenuse", "leg": "the length of each leg"}
_ANS = {"short": "Shorter leg", "long": "Longer leg", "hyp": "Hypotenuse", "leg": "Each leg"}


def _special(ctx: Ctx, kind: int, short, given: str, wants: list[str], work: list[str]) -> Problem:
    short = sp.nsimplify(short)
    if kind == 45:
        sides = {"leg": short, "hyp": sp.nsimplify(short * R2)}
    else:
        sides = {"short": short, "long": sp.nsimplify(short * R3), "hyp": 2 * short}
    unit = ctx.rng.choice(["cm", "in", "ft", "m"])
    marks = {given: f"{plain(sides[given])} {unit}", **{w: v for w, v in zip(wants, ("x", "y"))}}
    if kind == 45:
        fig = draw.right_triangle(float(short), float(short), label_a=marks.get("leg", ""),
                                  label_c=marks.get("hyp", ""), angle_at="base", angle_label="45°")
    else:  # long leg horizontal, short leg vertical: the base angle is 30°
        fig = draw.right_triangle(float(sides["long"]), float(short), label_a=marks.get("long", ""),
                                  label_b=marks.get("short", ""), label_c=marks.get("hyp", ""),
                                  angle_at="base", angle_label="30°")
    exact = any(not sides[w].is_Integer for w in wants)
    letters = " and ".join(f"{_FIND[w]} (${v}$)" for w, v in zip(wants, "xy")) if len(wants) > 1 else _FIND[wants[0]]
    decimals = [f"{_ANS[w]} $\\approx {ctx.rnd(float(sides[w]))}{U(unit)}$"
                for w in wants if not sides[w].is_Integer and ctx.form != "exact"]
    return Problem(f"A {'45-45-90' if kind == 45 else '30-60-90'} triangle has {_GIVEN[given]} "
                   f"${L(sides[given])}$ {unit} long. Find {letters}."
                   + (ctx.form_note("in simplest radical form") if exact else ""),
                   "; ".join(f"{_ANS[w]}: ${value_tex(ctx, sides[w], unit)}$" for w in wants),
                   steps(*work, *decimals),
                   facts={"kind": "special", "type": kind, "sides": sides, "wants": wants},
                   figure=fig)


@variant("special_right", 1, "45-45-90 triangles")
def _s45(ctx: Ctx) -> Problem:
    a = sp.Integer(ctx.rng.randint(2, 16))
    if ctx.rng.random() < 0.5:
        return _special(ctx, 45, a, "leg", ["hyp"],
                        ["In a 45-45-90 triangle, hypotenuse $= \\text{leg} \\cdot \\sqrt{2}$",
                         f"Hypotenuse $= {a}\\sqrt{{2}}$"])
    return _special(ctx, 45, a, "hyp", ["leg"],
                    ["Leg $= \\frac{\\text{hypotenuse}}{\\sqrt{2}}$",
                     f"Leg $= \\frac{{{L(a * R2)}}}{{\\sqrt{{2}}}} = {a}$"])


@variant("special_right", 2, "30-60-90 triangles")
def _s30(ctx: Ctx) -> Problem:
    s = sp.Integer(ctx.rng.randint(2, 15))
    if ctx.rng.random() < 0.5:
        return _special(ctx, 30, s, "short", ["long", "hyp"],
                        [f"Longer leg $= \\text{{shorter leg}} \\cdot \\sqrt{{3}} = {L(s * R3)}$",
                         f"Hypotenuse $= 2 \\cdot \\text{{shorter leg}} = 2({s}) = {2 * s}$"])
    return _special(ctx, 30, s, "hyp", ["short", "long"],
                    [f"Shorter leg $= \\frac{{\\text{{hypotenuse}}}}{{2}} = \\frac{{{2 * s}}}{{2}} = {s}$",
                     f"Longer leg $= \\text{{shorter leg}} \\cdot \\sqrt{{3}} = {L(s * R3)}$"])


@variant("special_right", 3, "Rationalizing denominators")
def _s_rational(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.5:
        h = ctx.rng.choice([n for n in range(3, 25) if n % 2])  # odd, so the leg isn't a whole number of √2
        leg = sp.nsimplify(h / R2)
        return _special(ctx, 45, leg, "hyp", ["leg"],
                        [f"Leg $= \\frac{{{h}}}{{\\sqrt{{2}}}}$",
                         f"Rationalize: $\\frac{{{h}}}{{\\sqrt{{2}}}} \\cdot \\frac{{\\sqrt{{2}}}}{{\\sqrt{{2}}}} = {L(leg)}$"])
    lg = ctx.rng.choice([n for n in range(2, 25) if n % 3])
    short = sp.nsimplify(lg / R3)
    return _special(ctx, 30, short, "long", ["short", "hyp"],
                    [f"Shorter leg $= \\frac{{{lg}}}{{\\sqrt{{3}}}} \\cdot \\frac{{\\sqrt{{3}}}}{{\\sqrt{{3}}}} = {L(short)}$",
                     f"Hypotenuse $= 2 \\cdot \\text{{shorter leg}} = 2 \\cdot {L(short)} = {L(2 * short)}$"])


# ======================================================================== Similar triangles

topic("similarity", "math", "Similarity", "Similar triangles",
      "Missing sides of similar triangles, indirect measurement, the side-splitter theorem, area and volume ratios.",
      courses=["geo"], figures=True)


@variant("similarity", 1, "Missing sides")
def _similar_sides(ctx: Ctx) -> Problem:
    k = Fraction(ctx.rng.choice([3, 5]), 2) if ctx.rng.random() < 0.5 else Fraction(ctx.rng.randint(2, 4))
    while True:
        c, b = ctx.rng.randrange(4, 17, 2), ctx.rng.randint(3, 16)
        if (k * b).denominator == 1 and b != c and 0.6 <= b / c <= 1.7:
            break
    DE, DF = k * c, k * b
    return Problem(f"$\\triangle ABC \\sim \\triangle DEF$ with $AB = {c}$, $AC = {b}$ and $DE = {num_frac(DE)}$. Find $DF$.",
                   f"$DF = {num_frac(DF)}$",
                   steps(f"Scale factor: $\\frac{{DE}}{{AB}} = \\frac{{{num_frac(DE)}}}{{{c}}} = {num_frac(k)}$",
                         f"$DF = {num_frac(k)} \\cdot AC = {num_frac(k)}({b}) = {num_frac(DF)}$"),
                   facts={"kind": "similar", "pairs": [(c, DE), (b, DF)], "want": [DF]},
                   figure=draw.similar_triangles(c, b, ctx.rng.randint(45, 80), min(float(k), 1.7),
                                                 {"c": str(c), "b": str(b)}, {"c": num_frac(DE), "b": "x"}))


_SHADOWS = [("A {h} m tall student", "a tree", "How tall is the tree?"),
            ("A {h} m tall student", "a flagpole", "How tall is the flagpole?"),
            ("A {h} m tall fence post", "a building", "How tall is the building?")]


def _r(v: float) -> float:
    return round(v, 6)


@variant("similarity", 2, "Indirect measurement")
def _shadows(ctx: Ctx) -> Problem:
    who, thing, ask = ctx.rng.choice(_SHADOWS)
    h1, s1 = ctx.rng.choice([1.5, 1.6, 1.7, 1.8]), ctx.rng.choice([1.2, 2, 2.4, 3])
    k = ctx.rng.choice([4, 5, 6, 7.5, 8, 10, 12])
    s2, h2 = _r(s1 * k), _r(h1 * k)
    f = lambda v: f"{v:g}"  # noqa: E731
    return Problem(f"{who.replace('{h}', f(h1))} casts a ${f(s1)}$ m shadow. At the same time, {thing} casts a "
                   f"${f(s2)}$ m shadow. {ask}",
                   f"${f(h2)}$ m",
                   steps("The sun's rays make similar triangles, so heights are proportional to shadows:",
                         f"$\\frac{{h}}{{{f(s2)}}} = \\frac{{{f(h1)}}}{{{f(s1)}}}$",
                         f"$h = \\frac{{{f(h1)} \\cdot {f(s2)}}}{{{f(s1)}}} = {f(h2)}$ m"),
                   facts={"kind": "similar", "pairs": [(h1, h2), (s1, s2)], "want": [h2]})


@variant("similarity", 2, "Side-splitter theorem")
def _splitter(ctx: Ctx) -> Problem:
    while True:
        CD, DA, CE = ctx.rng.randint(2, 15), ctx.rng.randint(2, 15), ctx.rng.randint(2, 15)
        EB = Fraction(DA * CE, CD)
        if EB.denominator == 1 and len({CD, DA, CE}) == 3:
            break
    return Problem(f"In $\\triangle ABC$, $\\overline{{DE}} \\parallel \\overline{{AB}}$ with $D$ on $\\overline{{CA}}$ and $E$ on "
                   f"$\\overline{{CB}}$. If $CD = {CD}$, $DA = {DA}$ and $CE = {CE}$, find $EB$.",
                   f"$EB = {EB}$",
                   steps("A line parallel to one side splits the other two sides proportionally:",
                         f"$\\frac{{CD}}{{DA}} = \\frac{{CE}}{{EB}}$, so $\\frac{{{CD}}}{{{DA}}} = \\frac{{{CE}}}{{x}}$",
                         f"$x = \\frac{{{DA} \\cdot {CE}}}{{{CD}}} = {EB}$"),
                   facts={"kind": "splitter", "CD": CD, "DA": DA, "CE": CE, "EB": int(EB), "want": [int(EB)]},
                   figure=draw.side_splitter({"CD": str(CD), "DA": str(DA), "CE": str(CE), "EB": "x"}))


@variant("similarity", 3, "Area and volume ratios")
def _scale_ratios(ctx: Ctx) -> Problem:
    a, b = ctx.rng.sample(range(2, 8), 2)
    k = Fraction(b, a)
    first = "smaller" if b > a else "larger"
    if ctx.rng.random() < 0.5:
        v1 = ctx.rng.randint(2, 12) * a * a
        what, unit, p = "area", "cm^2", 2
        q = (f"Two similar polygons have corresponding sides of ${a}$ cm and ${b}$ cm. The {first} polygon has an "
             f"area of ${v1}{U('cm^2')}$. Find the area of the other polygon.")
    else:
        v1 = ctx.rng.randint(2, 10) * a**3
        what, unit, p = "volume", "cm^3", 3
        q = (f"Two similar solids have corresponding edges of ${a}$ cm and ${b}$ cm. The {first} solid has a volume "
             f"of ${v1}{U('cm^3')}$. Find the volume of the other solid.")
    v2 = v1 * k**p
    return Problem(q, f"${num_frac(v2)}{U(unit)}$",
                   steps(f"Scale factor: $k = \\frac{{{b}}}{{{a}}}$",
                         f"{what.capitalize()}s scale by $k^{p}$: ${v1} \\cdot \\left(\\frac{{{b}}}{{{a}}}\\right)^{p} = "
                         f"{num_frac(v2)}{U(unit)}$"),
                   facts={"kind": "scale_ratio", "a": a, "b": b, "power": p, "v1": v1, "v2": v2, "want": [v2]})


# ======================================================================== Distance & midpoint

topic("coordinate_geo", "math", "Lines & coordinate geometry", "Distance & midpoint",
      "Midpoints, distances and missing endpoints on the coordinate plane; classifying triangles by their vertices.",
      courses=["geo"], exact_forms=True, rounding=True, figures=True)


def _pt(p) -> str:
    return f"({num_frac(Fraction(p[0]))}, {num_frac(Fraction(p[1]))})"


def _two_pts(ctx: Ctx, span: int):
    while True:
        A = (ctx.rng.randint(-span, span), ctx.rng.randint(-span, span))
        B = (ctx.rng.randint(-span, span), ctx.rng.randint(-span, span))
        if A[0] != B[0] and A[1] != B[1]:
            return A, B


@variant("coordinate_geo", 1, "Midpoint")
def _midpoint(ctx: Ctx) -> Problem:
    A, B = _two_pts(ctx, 10)
    M = (Fraction(A[0] + B[0], 2), Fraction(A[1] + B[1], 2))
    return Problem(f"Find the midpoint of the segment with endpoints $A{_pt(A)}$ and $B{_pt(B)}$.", f"$M{_pt(M)}$",
                   steps("$M = \\left(\\frac{x_1 + x_2}{2}, \\frac{y_1 + y_2}{2}\\right)$",
                         f"$M = \\left(\\frac{{{A[0]} + {paren(B[0])}}}{{2}}, \\frac{{{A[1]} + {paren(B[1])}}}{{2}}\\right) "
                         f"= {_pt(M)}$"),
                   facts={"kind": "midpoint", "A": A, "B": B, "M": M, "want": "M"})


@variant("coordinate_geo", 2, "Missing endpoint")
def _endpoint(ctx: Ctx) -> Problem:
    A, B = _two_pts(ctx, 9)
    M = (Fraction(A[0] + B[0], 2), Fraction(A[1] + B[1], 2))
    return Problem(f"$M{_pt(M)}$ is the midpoint of $\\overline{{AB}}$, and $A$ is at ${_pt(A)}$. Find the coordinates of $B$.",
                   f"$B{_pt(B)}$",
                   steps("The midpoint is halfway, so $B = (2x_M - x_A,\\ 2y_M - y_A)$",
                         f"$B = (2({num_frac(M[0])}) - {paren(A[0])},\\ 2({num_frac(M[1])}) - {paren(A[1])}) = {_pt(B)}$"),
                   facts={"kind": "midpoint", "A": A, "B": B, "M": M, "want": "B"})


@variant("coordinate_geo", 2, "Distance")
def _distance(ctx: Ctx) -> Problem:
    A, B = _two_pts(ctx, 9)
    dx, dy = B[0] - A[0], B[1] - A[1]
    n = dx * dx + dy * dy
    d = sp.sqrt(n)
    return Problem(f"Find the distance between $A{_pt(A)}$ and $B{_pt(B)}$."
                   + ("" if d.is_Integer else ctx.form_note("in simplest radical form")),
                   f"${value_tex(ctx, d)}$",
                   steps("$d = \\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$",
                         f"$d = \\sqrt{{({B[0]} - {paren(A[0])})^2 + ({B[1]} - {paren(A[1])})^2}} = "
                         f"\\sqrt{{({dx})^2 + ({dy})^2}} = \\sqrt{{{n}}}$",
                         f"$d = {d}$" if d.is_Integer else radical_steps(n),
                         "" if d.is_Integer or ctx.form == "exact" else f"$d \\approx {ctx.rnd(float(d))}$"),
                   facts={"kind": "distance", "A": A, "B": B, "d": d})


@variant("coordinate_geo", 3, "Classify triangles")
def _classify(ctx: Ctx) -> Problem:
    target = ctx.rng.choice(["right", "isosceles", "isosceles right", "scalene"])
    while True:
        A = (ctx.rng.randint(-6, 3), ctx.rng.randint(-6, 3))
        u = (ctx.rng.randint(-5, 5), ctx.rng.randint(-5, 5))
        m = ctx.rng.choice([2, 3])
        w = {"right": (-u[1] * m, u[0] * m), "isosceles right": (-u[1], u[0]), "isosceles": (u[1], u[0]),
             "scalene": (ctx.rng.randint(-5, 5), ctx.rng.randint(-5, 5))}[target]
        B, C = (A[0] + u[0], A[1] + u[1]), (A[0] + w[0], A[1] + w[1])
        if u[0] * w[1] - u[1] * w[0] and all(abs(v) <= 7 for p in (B, C) for v in p):
            break
    sq = {"AB": (B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2, "BC": (C[0] - B[0]) ** 2 + (C[1] - B[1]) ** 2,
          "AC": (C[0] - A[0]) ** 2 + (C[1] - A[1]) ** 2}
    s0, s1, s2 = sorted(sq.values())
    right, iso = s0 + s1 == s2, len(set(sq.values())) < 3
    rel = "=" if right else "\\ne"
    return Problem(f"Triangle $ABC$ has vertices $A{_pt(A)}$, $B{_pt(B)}$ and $C{_pt(C)}$. Classify the triangle by its "
                   "sides, and decide whether it is a right triangle.",
                   f"{'Isosceles' if iso else 'Scalene'}; {'a right triangle' if right else 'not a right triangle'}",
                   steps("Squared side lengths: " + ", ".join(f"${k}^2 = {v}$" for k, v in sq.items()),
                         "Two sides are equal, so it is isosceles." if iso else "No two sides are equal, so it is scalene.",
                         f"${s0} + {s1} {rel} {s2}$, so it is {'' if right else 'not '}a right triangle."),
                   facts={"kind": "classify", "pts": (A, B, C), "iso": iso, "right": right},
                   figure=draw.plane_polygon([A, B, C]))


# ======================================================================== Circles

topic("circles", "math", "Circles", "Circles",
      "Inscribed angles, arc length and sector area, intersecting chords, and equations of circles.",
      courses=["geo"], exact_forms=True, rounding=True, figures=True)


@variant("circles", 1, "Inscribed angles")
def _inscribed(ctx: Ctx) -> Problem:
    central = ctx.rng.randrange(40, 162, 2)
    half = central // 2
    if ctx.rng.random() < 0.5:
        return Problem(f"In circle $O$, central angle $\\angle AOB$ measures ${central}^\\circ$. Find the measure of "
                       "inscribed angle $\\angle APB$.", f"$m\\angle APB = {half}^\\circ$",
                       steps("An inscribed angle is half the central angle that intercepts the same arc.",
                             f"$m\\angle APB = \\frac{{{central}^\\circ}}{{2}} = {half}^\\circ$"),
                       facts={"kind": "inscribed", "central": central, "inscribed": half, "want": [half]},
                       figure=draw.circle_angles(central, labels={"central": f"{central}°", "inscribed": "x"}))
    return Problem(f"In circle $O$, inscribed angle $\\angle APB$ measures ${half}^\\circ$. Find the measure "
                   "of arc $AB$.", f"$m\\overset{{\\frown}}{{AB}} = {central}^\\circ$",
                   steps("An inscribed angle is half the arc it intercepts, so the arc is twice the angle.",
                         f"$m\\overset{{\\frown}}{{AB}} = 2({half}^\\circ) = {central}^\\circ$"),
                   facts={"kind": "inscribed", "central": central, "inscribed": half, "want": [central]},
                   figure=draw.circle_angles(central, labels={"arc": "x", "inscribed": f"{half}°"}))


_SECTOR_ANGLES = [30, 36, 40, 45, 60, 72, 80, 90, 120, 135, 150, 216, 240, 270, 300]


@variant("circles", 2, "Arc length & sector area")
def _sector(ctx: Ctx) -> Problem:
    r, th = ctx.rng.randint(2, 20), ctx.rng.choice(_SECTOR_ANGLES)
    if ctx.rng.random() < 0.5:
        coef = Fraction(2 * r * th, 360)
        val = float(coef) * math.pi
        return Problem(f"Find the length of an arc with central angle ${th}^\\circ$ in a circle of radius ${r}$ cm."
                       + ctx.form_note("in terms of $\\pi$"),
                       f"${ctx.exact_or_decimal(pi_tex(0, coef), val, 'cm')}$",
                       steps("Arc length $= \\frac{\\theta}{360^\\circ} \\cdot 2\\pi r$",
                             f"$= \\frac{{{th}}}{{360}} \\cdot 2\\pi({r}) = {pi_tex(0, coef)}{U('cm')}$",
                             "" if ctx.form == "exact" else f"$\\approx {ctx.rnd(val)}{U('cm')}$"),
                       facts={"kind": "sector", "r": r, "theta": th, "what": "arc", "value": val},
                       figure=draw.sector(th, f"{r} cm", f"{th}°"))
    coef = Fraction(r * r * th, 360)
    val = float(coef) * math.pi
    return Problem(f"Find the area of a sector with central angle ${th}^\\circ$ in a circle of radius ${r}$ cm."
                   + ctx.form_note("in terms of $\\pi$"),
                   f"${ctx.exact_or_decimal(pi_tex(0, coef), val, 'cm^2')}$",
                   steps("Sector area $= \\frac{\\theta}{360^\\circ} \\cdot \\pi r^2$",
                         f"$= \\frac{{{th}}}{{360}} \\cdot \\pi({r})^2 = {pi_tex(0, coef)}{U('cm^2')}$",
                         "" if ctx.form == "exact" else f"$\\approx {ctx.rnd(val)}{U('cm^2')}$"),
                   facts={"kind": "sector", "r": r, "theta": th, "what": "area", "value": val},
                   figure=draw.sector(th, f"{r} cm", f"{th}°"))


@variant("circles", 3, "Intersecting chords")
def _chords(ctx: Ctx) -> Problem:
    while True:
        AE, EB, CE = ctx.rng.randint(2, 12), ctx.rng.randint(2, 12), ctx.rng.randint(2, 12)
        ED = Fraction(AE * EB, CE)
        if ED.denominator == 1 and CE not in (AE, EB):
            break
    return Problem(f"Chords $\\overline{{AB}}$ and $\\overline{{CD}}$ intersect at $E$. If $AE = {AE}$, $EB = {EB}$ and "
                   f"$CE = {CE}$, find $ED$.", f"$ED = {ED}$",
                   steps("The products of the chord segments are equal: $AE \\cdot EB = CE \\cdot ED$",
                         f"${AE} \\cdot {EB} = {CE}x$", f"$x = \\frac{{{AE * EB}}}{{{CE}}} = {ED}$"),
                   facts={"kind": "chords", "AE": AE, "EB": EB, "CE": CE, "ED": int(ED), "want": [int(ED)]},
                   figure=draw.chords({"AE": str(AE), "EB": str(EB), "CE": str(CE), "ED": "x"}))


@variant("circles", 3, "Equations of circles")
def _circle_eq(ctx: Ctx) -> Problem:
    h, k, r = nz(ctx.rng, -8, 8), nz(ctx.rng, -8, 8), ctx.rng.randint(2, 9)
    std = sp.Eq((X - h) ** 2 + (Y - k) ** 2, r * r)
    if ctx.rng.random() < 0.5:
        return Problem(f"Write the equation of the circle with center $({h}, {k})$ and radius ${r}$.",
                       f"${L(std)}$",
                       steps("Standard form: $(x - h)^2 + (y - k)^2 = r^2$",
                             f"$(x - {paren(h)})^2 + (y - {paren(k)})^2 = {r}^2$", f"${L(std)}$"),
                       facts={"kind": "circle_eq", "h": h, "k": k, "r": r})
    general = sp.expand((X - h) ** 2 + (Y - k) ** 2 - r * r)
    c = general.subs({X: 0, Y: 0})
    gx, gy = sp.expand((X - h) ** 2 - h * h), sp.expand((Y - k) ** 2 - k * k)
    return Problem(f"Find the center and radius of the circle $${L(general)} = 0$$",
                   f"Center $({h}, {k})$, radius ${r}$",
                   steps(f"Group the terms and move the constant: $({L(gx)}) + ({L(gy)}) = {-c}$",
                         f"Complete each square by adding ${h * h}$ and ${k * k}$ to both sides:",
                         f"$(x - {paren(h)})^2 + (y - {paren(k)})^2 = {-c} + {h * h} + {k * k} = {r * r}$",
                         f"Center $({h}, {k})$, radius $\\sqrt{{{r * r}}} = {r}$"),
                   facts={"kind": "circle_eq", "h": h, "k": k, "r": r, "general": general})


# ======================================================================== Volume & surface area

topic("solids", "math", "Volume & surface area", "Volume & surface area",
      "Prisms, cylinders, cones, pyramids and spheres.", courses=["geo"], exact_forms=True, rounding=True,
      figures=True)


def _pi_answer(ctx: Ctx, coef: Fraction, unit: str) -> tuple[str, float]:
    val = float(coef) * math.pi
    return ctx.exact_or_decimal(pi_tex(0, coef), val, unit), val


def _about(ctx: Ctx, name: str, val: float, unit: str) -> str:
    return "" if ctx.form == "exact" else f"${name} \\approx {ctx.rnd(val)}{U(unit)}$"


@variant("solids", 1, "Prisms & cylinders")
def _prism(ctx: Ctx) -> Problem:
    l, w, h = ctx.rng.randint(3, 15), ctx.rng.randint(2, 12), ctx.rng.randint(2, 12)
    what = ctx.rng.choice(["a rectangular box", "a fish tank", "a storage bin"])
    return Problem(f"Find the volume of {what} that measures ${l}$ in by ${w}$ in by ${h}$ in.",
                   f"${l * w * h}{U('in^3')}$", steps("$V = lwh$", f"$V = ({l})({w})({h}) = {l * w * h}{U('in^3')}$"),
                   facts={"kind": "solid", "shape": "prism", "what": "V", "dims": {"l": l, "w": w, "h": h},
                          "value": l * w * h},
                   figure=draw.box(l, w, h, f"{l} in", f"{w} in", f"{h} in"))


@variant("solids", 1, "Prisms & cylinders")
def _cylinder(ctx: Ctx) -> Problem:
    r, h = ctx.rng.randint(2, 10), ctx.rng.randint(2, 20)
    ans, val = _pi_answer(ctx, Fraction(r * r * h), "cm^3")
    what = ctx.rng.choice(["a cylinder", "a can", "a cylindrical water tank"])
    return Problem(f"Find the volume of {what} with radius ${r}$ cm and height ${h}$ cm." + ctx.form_note("in terms of $\\pi$"),
                   f"${ans}$", steps("$V = \\pi r^2 h$", f"$V = \\pi({r})^2({h}) = {r * r * h}\\pi{U('cm^3')}$",
                                     _about(ctx, "V", val, "cm^3")),
                   facts={"kind": "solid", "shape": "cylinder", "what": "V", "dims": {"r": r, "h": h}, "value": val},
                   figure=draw.cylinder(r, h, f"{r} cm", f"{h} cm"))


@variant("solids", 2, "Cones, pyramids & spheres")
def _cone(ctx: Ctx) -> Problem:
    r, h = ctx.rng.randint(2, 10), ctx.rng.randint(3, 18)
    coef = Fraction(r * r * h, 3)
    ans, val = _pi_answer(ctx, coef, "cm^3")
    return Problem(f"Find the volume of a cone with radius ${r}$ cm and height ${h}$ cm." + ctx.form_note("in terms of $\\pi$"),
                   f"${ans}$", steps("$V = \\tfrac{1}{3}\\pi r^2 h$",
                                     f"$V = \\tfrac{{1}}{{3}}\\pi({r})^2({h}) = {pi_tex(0, coef)}{U('cm^3')}$",
                                     _about(ctx, "V", val, "cm^3")),
                   facts={"kind": "solid", "shape": "cone", "what": "V", "dims": {"r": r, "h": h}, "value": val},
                   figure=draw.cone(r, h, f"{r} cm", f"{h} cm"))


@variant("solids", 2, "Cones, pyramids & spheres")
def _sphere(ctx: Ctx) -> Problem:
    r = ctx.rng.randint(2, 12)
    coef = Fraction(4 * r**3, 3)
    ans, val = _pi_answer(ctx, coef, "m^3")
    return Problem(f"Find the volume of a sphere with radius ${r}$ m." + ctx.form_note("in terms of $\\pi$"),
                   f"${ans}$", steps("$V = \\tfrac{4}{3}\\pi r^3$", f"$V = \\tfrac{{4}}{{3}}\\pi({r})^3 = {pi_tex(0, coef)}{U('m^3')}$",
                                     _about(ctx, "V", val, "m^3")),
                   facts={"kind": "solid", "shape": "sphere", "what": "V", "dims": {"r": r}, "value": val},
                   figure=draw.sphere(r, f"{r} m"))


@variant("solids", 2, "Cones, pyramids & spheres")
def _pyramid(ctx: Ctx) -> Problem:
    s, h = ctx.rng.randint(2, 15), 3 * ctx.rng.randint(1, 7)
    V = s * s * h // 3
    return Problem(f"A pyramid has a square base ${s}$ ft on each side and a height of ${h}$ ft. Find its volume.",
                   f"${V}{U('ft^3')}$",
                   steps("$V = \\tfrac{1}{3}Bh$, where $B$ is the area of the base", f"$B = {s}^2 = {s * s}$",
                         f"$V = \\tfrac{{1}}{{3}}({s * s})({h}) = {V}{U('ft^3')}$"),
                   facts={"kind": "solid", "shape": "pyramid", "what": "V", "dims": {"s": s, "h": h}, "value": V})


_CONE_TRIPLES = [(3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17), (9, 12, 15), (7, 24, 25), (4, 3, 5), (12, 5, 13)]


@variant("solids", 3, "Surface area")
def _surface(ctx: Ctx) -> Problem:
    shape = ctx.rng.choice(["cylinder", "cone", "sphere", "prism"])
    if shape == "cylinder":
        r, h = ctx.rng.randint(2, 10), ctx.rng.randint(2, 15)
        coef = Fraction(2 * r * r + 2 * r * h)
        ans, val = _pi_answer(ctx, coef, "cm^2")
        return Problem(f"Find the total surface area of a cylinder with radius ${r}$ cm and height ${h}$ cm."
                       + ctx.form_note("in terms of $\\pi$"), f"${ans}$",
                       steps("Two circles plus the curved side: $SA = 2\\pi r^2 + 2\\pi rh$",
                             f"$SA = 2\\pi({r})^2 + 2\\pi({r})({h}) = {2 * r * r}\\pi + {2 * r * h}\\pi = {pi_tex(0, coef)}{U('cm^2')}$",
                             _about(ctx, "SA", val, "cm^2")),
                       facts={"kind": "solid", "shape": "cylinder", "what": "SA", "dims": {"r": r, "h": h}, "value": val},
                       figure=draw.cylinder(r, h, f"{r} cm", f"{h} cm"))
    if shape == "cone":
        r, h, sl = ctx.rng.choice(_CONE_TRIPLES)
        k = ctx.rng.randint(1, 2)
        r, h, sl = r * k, h * k, sl * k
        coef = Fraction(r * r + r * sl)
        ans, val = _pi_answer(ctx, coef, "cm^2")
        return Problem(f"A cone has radius ${r}$ cm and height ${h}$ cm. Find its total surface area."
                       + ctx.form_note("in terms of $\\pi$"), f"${ans}$",
                       steps(f"Slant height: $\\ell = \\sqrt{{r^2 + h^2}} = \\sqrt{{{r}^2 + {h}^2}} = {sl}$",
                             "Base plus curved surface: $SA = \\pi r^2 + \\pi r\\ell$",
                             f"$SA = \\pi({r})^2 + \\pi({r})({sl}) = {pi_tex(0, coef)}{U('cm^2')}$",
                             _about(ctx, "SA", val, "cm^2")),
                       facts={"kind": "solid", "shape": "cone", "what": "SA", "dims": {"r": r, "h": h}, "value": val},
                       figure=draw.cone(r, h, f"{r} cm", f"{h} cm"))
    if shape == "sphere":
        r = ctx.rng.randint(2, 15)
        ans, val = _pi_answer(ctx, Fraction(4 * r * r), "m^2")
        return Problem(f"Find the surface area of a sphere with radius ${r}$ m." + ctx.form_note("in terms of $\\pi$"),
                       f"${ans}$", steps("$SA = 4\\pi r^2$", f"$SA = 4\\pi({r})^2 = {4 * r * r}\\pi{U('m^2')}$",
                                         _about(ctx, "SA", val, "m^2")),
                       facts={"kind": "solid", "shape": "sphere", "what": "SA", "dims": {"r": r}, "value": val},
                       figure=draw.sphere(r, f"{r} m"))
    l, w, h = ctx.rng.randint(3, 15), ctx.rng.randint(2, 12), ctx.rng.randint(2, 12)
    SA = 2 * (l * w + l * h + w * h)
    return Problem(f"Find the surface area of a rectangular box ${l}$ in by ${w}$ in by ${h}$ in.", f"${SA}{U('in^2')}$",
                   steps("Six faces in three matching pairs: $SA = 2(lw + lh + wh)$",
                         f"$SA = 2({l * w} + {l * h} + {w * h}) = {SA}{U('in^2')}$"),
                   facts={"kind": "solid", "shape": "prism", "what": "SA", "dims": {"l": l, "w": w, "h": h}, "value": SA},
                   figure=draw.box(l, w, h, f"{l} in", f"{w} in", f"{h} in"))


# ======================================================================== Transformations

topic("transformations", "math", "Transformations", "Transformations",
      "Translations, reflections, rotations and dilations on the coordinate plane.", courses=["geo"], figures=True)

# name -> (description, coordinate rule, function)
_RULES = {
    "reflect_x": ("reflected over the $x$-axis", "(x, y) \\to (x, -y)", lambda p: (p[0], -p[1])),
    "reflect_y": ("reflected over the $y$-axis", "(x, y) \\to (-x, y)", lambda p: (-p[0], p[1])),
    "reflect_yx": ("reflected over the line $y = x$", "(x, y) \\to (y, x)", lambda p: (p[1], p[0])),
    "reflect_ynx": ("reflected over the line $y = -x$", "(x, y) \\to (-y, -x)", lambda p: (-p[1], -p[0])),
    "rot90": ("rotated $90^\\circ$ counterclockwise about the origin", "(x, y) \\to (-y, x)", lambda p: (-p[1], p[0])),
    "rot180": ("rotated $180^\\circ$ about the origin", "(x, y) \\to (-x, -y)", lambda p: (-p[0], -p[1])),
    "rot270": ("rotated $90^\\circ$ clockwise about the origin", "(x, y) \\to (y, -x)", lambda p: (p[1], -p[0])),
}


def _triangle_pts(ctx: Ctx, span: int = 6):
    """Three lattice points making a triangle that's easy to see: not a sliver, no tiny side."""
    while True:
        pts = [(ctx.rng.randint(-span, span), ctx.rng.randint(-span, span)) for _ in range(3)]
        (x1, y1), (x2, y2), (x3, y3) = pts
        area2 = abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
        sides = [math.dist(pts[i], pts[i - 1]) for i in range(3)]
        if area2 >= span * 2 and min(sides) >= 2 and area2 / max(sides) ** 2 >= 0.25:
            return pts


def _vertices(pts, prime: str = "") -> str:
    return ",\\ ".join(f"{n}{prime}{_pt(p)}" for n, p in zip("ABC", pts))


def _transform_problem(desc: str, pts, img, ops, work: list[str]) -> Problem:
    return Problem(f"Triangle $ABC$ has vertices ${_vertices(pts)}$. Find the vertices of its image after it is {desc}.",
                   f"${_vertices(img, chr(39))}$", steps(*work),
                   facts={"kind": "transform", "pre": pts, "img": img, "ops": ops},
                   figure=draw.plane_polygon(pts))


def _mapping(pts, img) -> list[str]:
    return [f"${n}{_pt(p)} \\to {n}'{_pt(q)}$" for n, p, q in zip("ABC", pts, img)]


@variant("transformations", 1, "Translations")
def _translate(ctx: Ctx) -> Problem:
    pts = _triangle_pts(ctx)
    a, b = nz(ctx.rng, -6, 6), nz(ctx.rng, -6, 6)
    img = [(x + a, y + b) for x, y in pts]
    desc = (f"translated ${abs(a)}$ unit{'s' if abs(a) != 1 else ''} {'right' if a > 0 else 'left'} and "
            f"${abs(b)}$ unit{'s' if abs(b) != 1 else ''} {'up' if b > 0 else 'down'}")
    return _transform_problem(desc, pts, img, [("translate", a, b)],
                              [f"Rule: $(x, y) \\to ({L(X + a)}, {L(Y + b)})$", *_mapping(pts, img)])


@variant("transformations", 1, "Reflections")
def _reflect(ctx: Ctx) -> Problem:
    pts = _triangle_pts(ctx)
    name = ctx.rng.choice(["reflect_x", "reflect_y", "reflect_yx", "reflect_ynx"])
    desc, rule, fn = _RULES[name]
    img = [fn(p) for p in pts]
    return _transform_problem(desc, pts, img, [(name,)], [f"Rule: ${rule}$", *_mapping(pts, img)])


@variant("transformations", 2, "Rotations")
def _rotate(ctx: Ctx) -> Problem:
    pts = _triangle_pts(ctx)
    name = ctx.rng.choice(["rot90", "rot180", "rot270"])
    desc, rule, fn = _RULES[name]
    img = [fn(p) for p in pts]
    return _transform_problem(desc, pts, img, [(name,)], [f"Rule: ${rule}$", *_mapping(pts, img)])


@variant("transformations", 3, "Dilations")
def _dilate(ctx: Ctx) -> Problem:
    k = ctx.rng.choice([Fraction(2), Fraction(3), Fraction(1, 2), Fraction(3, 2)])
    pts = _triangle_pts(ctx, 4 if k >= 2 else 6)
    img = [(k * x, k * y) for x, y in pts]
    kt = num_frac(k)
    return _transform_problem(f"dilated by a scale factor of ${kt}$ centered at the origin", pts, img, [("dilate", k)],
                              [f"Multiply each coordinate by ${kt}$: $(x, y) \\to ({kt}x, {kt}y)$", *_mapping(pts, img)])


@variant("transformations", 3, "Compositions")
def _compose(ctx: Ctx) -> Problem:
    pts = _triangle_pts(ctx, 5)
    first = ctx.rng.choice(["reflect_x", "reflect_y", "rot90", "rot180"])
    a, b = nz(ctx.rng, -5, 5), nz(ctx.rng, -5, 5)
    desc1, rule1, fn = _RULES[first]
    mid = [fn(p) for p in pts]
    img = [(x + a, y + b) for x, y in mid]
    return _transform_problem(f"{desc1} and then translated by $\\langle {a}, {b} \\rangle$", pts, img,
                              [(first,), ("translate", a, b)],
                              [f"First, ${rule1}$: " + ", ".join(f"${n}{_pt(q)} \\to {_pt(m)}$"
                                                                 for n, q, m in zip("ABC", pts, mid)),
                               f"Then add $\\langle {a}, {b} \\rangle$: ${_vertices(img, chr(39))}$"])


# ======================================================================== Law of sines & cosines

topic("triangle_trig", "math", "Triangle trigonometry", "Law of sines & cosines",
      "Find sides, angles and areas of triangles that aren't right triangles.", courses=["geo", "precalc"],
      rounding=True, figures=True)


def _solve_sss(a: float, b: float, c: float) -> dict:
    A = math.degrees(math.acos((b * b + c * c - a * a) / (2 * b * c)))
    B = math.degrees(math.acos((a * a + c * c - b * b) / (2 * a * c)))
    return {"A": A, "B": B, "C": 180 - A - B, "a": a, "b": b, "c": c}


def _tri_fig(t: dict, angle_labels: dict, side_labels: dict) -> str:
    return draw.triangle(t["A"], t["B"], angle_labels=angle_labels, side_labels=side_labels, vertex_names="ABC")


@variant("triangle_trig", 2, "Law of sines")
def _law_sines(ctx: Ctx) -> Problem:
    A, B, a = ctx.rng.randint(30, 80), ctx.rng.randint(30, 80), ctx.rng.randint(5, 30)  # C is 20° to 120°
    k = a / math.sin(math.radians(A))
    b, c = k * math.sin(math.radians(B)), k * math.sin(math.radians(180 - A - B))
    t = {"A": A, "B": B, "C": 180 - A - B, "a": a, "b": b, "c": c}
    return Problem(f"In $\\triangle ABC$, $m\\angle A = {A}^\\circ$, $m\\angle B = {B}^\\circ$ and $a = {a}$. Find $b$."
                   + ctx.round_note(), f"$b \\approx {ctx.rnd(b)}$",
                   steps("$\\frac{a}{\\sin A} = \\frac{b}{\\sin B}$",
                         f"$b = \\frac{{{a}\\sin {B}^\\circ}}{{\\sin {A}^\\circ}} \\approx {ctx.rnd(b)}$"),
                   facts={"kind": "oblique", "tri": t, "want": ("b", b)},
                   figure=_tri_fig(t, {"A": f"{A}°", "B": f"{B}°"}, {"a": str(a), "b": "x"}))


def _well_shaped(t: dict) -> bool:
    return min(t["A"], t["B"], t["C"]) >= 18


@variant("triangle_trig", 2, "Area with sine")
def _area_sine(ctx: Ctx) -> Problem:
    while True:
        a, b, C = ctx.rng.randint(4, 25), ctx.rng.randint(4, 25), ctx.rng.randint(25, 140)
        t = _solve_sss(a, b, math.sqrt(a * a + b * b - 2 * a * b * math.cos(math.radians(C))))
        if _well_shaped(t):
            break
    area = 0.5 * a * b * math.sin(math.radians(C))
    return Problem(f"In $\\triangle ABC$, $a = {a}$ cm, $b = {b}$ cm and $m\\angle C = {C}^\\circ$. Find the area of the "
                   "triangle." + ctx.round_note(), f"$\\approx {ctx.rnd(area)}{U('cm^2')}$",
                   steps("$\\text{Area} = \\tfrac{1}{2}ab\\sin C$",
                         f"$= \\tfrac{{1}}{{2}}({a})({b})\\sin {C}^\\circ \\approx {ctx.rnd(area)}{U('cm^2')}$"),
                   facts={"kind": "oblique", "tri": t, "want": ("area", area)},
                   figure=_tri_fig(t, {"C": f"{C}°"}, {"a": f"{a} cm", "b": f"{b} cm"}))


@variant("triangle_trig", 3, "Law of cosines")
def _cosines_side(ctx: Ctx) -> Problem:
    while True:
        b, c, A = ctx.rng.randint(4, 25), ctx.rng.randint(4, 25), ctx.rng.randint(20, 140)
        a2 = b * b + c * c - 2 * b * c * math.cos(math.radians(A))
        t = _solve_sss(math.sqrt(a2), b, c)
        if _well_shaped(t):
            break
    return Problem(f"In $\\triangle ABC$, $b = {b}$, $c = {c}$ and $m\\angle A = {A}^\\circ$. Find $a$." + ctx.round_note(),
                   f"$a \\approx {ctx.rnd(t['a'])}$",
                   steps("$a^2 = b^2 + c^2 - 2bc\\cos A$",
                         f"$a^2 = {b}^2 + {c}^2 - 2({b})({c})\\cos {A}^\\circ \\approx {a2:.3f}$",
                         f"$a \\approx {ctx.rnd(t['a'])}$"),
                   facts={"kind": "oblique", "tri": t, "want": ("a", t["a"])},
                   figure=_tri_fig(t, {"A": f"{A}°"}, {"a": "x", "b": str(b), "c": str(c)}))


@variant("triangle_trig", 3, "Law of cosines")
def _cosines_angle(ctx: Ctx) -> Problem:
    while True:
        a, b, c = ctx.rng.randint(4, 20), ctx.rng.randint(4, 20), ctx.rng.randint(4, 20)
        if a + b > c and a + c > b and b + c > a and len({a, b, c}) == 3 and _well_shaped(_solve_sss(a, b, c)):
            break
    t = _solve_sss(a, b, c)
    num_, den = a * a + b * b - c * c, 2 * a * b
    ratio = f"{'-' if num_ < 0 else ''}\\frac{{{abs(num_)}}}{{{den}}}"
    return Problem(f"A triangle has sides $a = {a}$, $b = {b}$ and $c = {c}$. Find $m\\angle C$." + ctx.round_note(),
                   f"$m\\angle C \\approx {ctx.rnd(t['C'])}^\\circ$",
                   steps("$\\cos C = \\frac{a^2 + b^2 - c^2}{2ab}$",
                         f"$\\cos C = \\frac{{{a}^2 + {b}^2 - {c}^2}}{{2({a})({b})}} = {ratio}$",
                         f"$C = \\cos^{{-1}}\\left({ratio}\\right) \\approx {ctx.rnd(t['C'])}^\\circ$"),
                   facts={"kind": "oblique", "tri": t, "want": ("C", t["C"])},
                   figure=_tri_fig(t, {"C": "θ"}, {"a": str(a), "b": str(b), "c": str(c)}))
