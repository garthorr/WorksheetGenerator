"""Quality checks for the built-in generators.

Correctness checks are *independent* of the generator code where possible: math answers
are substituted back into the displayed equation (or the question text is re-parsed and
evaluated), and physics answers are checked against a different physical relation than
the one the generator used (conservation laws, Kirchhoff's rules, alternate kinematics
equations). Every problem type must be covered, so new ones can't skip the checks.
"""

from __future__ import annotations

import math
import random
import re
import statistics
from fractions import Fraction
from functools import cache

import pytest
import sympy as sp

from app.ai import _numbers_in
from app.generators import TOPICS, generate_set
from app.generators.core import COURSE_UNITS, COURSES, is_nice_problem, norm_question, num, sig, variants_for
from app.safe_eval import safe_eval

x, y = sp.symbols("x y")
LEVELS = [(t, lv) for t in TOPICS for lv in sorted(TOPICS[t].variants)]
MATH = [(t, lv) for t, lv in LEVELS if TOPICS[t].subject == "math"]
PHYSICS = [(t, lv) for t, lv in LEVELS if TOPICS[t].subject == "physics"]
ids = [f"{t}-L{lv}" for t, lv in LEVELS]


@cache
def sample(topic: str, level: int, g: float = 9.8, nice: bool = False, form: str = "both", places: int = 1,
           sections: int = 8, size: int = 10):
    """Problems from several independent 10-problem sections."""
    out = []
    for s in range(sections):
        out.append(generate_set(topic, level, size, random.Random(f"q{topic}{level}{g}{nice}{form}{places}{s}"),
                                g=g, nice=nice, form=form, places=places))
    return out


def problems(topic, level, **kw):
    return [p for sec in sample(topic, level, **kw) for p in sec]


def close(a, b, rel=1e-6):
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=1e-9)


def shown(value: float, text: str, rel=0.006) -> bool:
    """Is ``value`` displayed in ``text`` (allowing for rounding to 3 sig figs)?"""
    return any(math.isclose(n, value, rel_tol=rel, abs_tol=1e-9) for n in _numbers_in(text))


def shown_r(value: float, text: str, places: int) -> bool:
    """Is ``value`` displayed in ``text``, rounded to ``places`` decimal places?"""
    tol = 0.5 * 10**-places + 1e-9
    return any(abs(n - value) <= tol for n in _numbers_in(text))


PI_TERM = re.compile(r"(?:(\d+) \+ )?(?:\\frac\{(\d+)\}\{(\d+)\}|(\d+))?\\pi")


def pi_values(text: str) -> list[float]:
    r"""Values of exact answers like 121\pi or 806 + \frac{169}{2}\pi in ``text``."""
    out = []
    for m in PI_TERM.finditer(text):
        coef = Fraction(int(m[2]), int(m[3])) if m[2] else Fraction(int(m[4] or 1))
        out.append(int(m[1] or 0) + float(coef) * math.pi)
    return out


def outside_math(text: str) -> str:
    return re.sub(r"\$\$.+?\$\$|\$[^$]+\$", "", text, flags=re.S)


# =================================================================== variety

@pytest.mark.parametrize("topic,level", LEVELS, ids=ids)
def test_large_section_has_no_repeats(topic, level):
    for seed in range(2):
        qs = [norm_question(p.question) for p in generate_set(topic, level, 30, random.Random(seed))]
        assert len(set(qs)) == 30, f"only {len(set(qs))} distinct problems in a 30-problem section"


def test_physics_options_are_harmless_for_math():
    for topic, level in MATH:
        assert generate_set(topic, level, 3, random.Random(1), g=10, nice=True)


def test_no_repeats_across_sections_of_a_worksheet():
    seen: set[str] = set()
    qs = []
    for i in range(4):
        qs += [p.question for p in generate_set("pythagorean", 1, 15, random.Random(i), seen=seen)]
    assert len(set(qs)) == len(qs) == 60


@pytest.mark.parametrize("topic,level", LEVELS, ids=ids)
def test_sections_rotate_through_every_problem_type(topic, level):
    n_types = len(TOPICS[topic].variants[level])
    for sec in sample(topic, level):
        assert {p.facts["slot"] for p in sec} == set(range(n_types))


@pytest.mark.parametrize("topic,level", LEVELS, ids=ids)
def test_answers_rarely_repeat_within_a_section(topic, level):
    secs = sample(topic, level)
    if len({p.answer for sec in secs for p in sec}) < 30:
        pytest.skip("few possible answers (e.g. small integers), so some repetition is natural")
    dup = sum(len({p.answer for p in sec}) < len(sec) for sec in secs)
    assert dup <= 1, f"{dup}/{len(secs)} sections repeat an answer"


# =================================================================== wording

@pytest.mark.parametrize("topic,level", LEVELS, ids=ids)
def test_wording(topic, level):
    for p in problems(topic, level):
        q = p.question
        assert q[0].isupper() or q.startswith("$"), q
        assert q.rstrip().endswith(("?", ".", "$$", ")")), q
        assert "  " not in q and "+ -" not in q and "- -" not in q, q
        assert not re.search(r"(?<![\d.])1 ?x\b", q), q  # coefficient 1 should be implicit
        for bad in ("side hypotenuse", "table-top", "None", "nan"):
            assert bad not in q and bad not in p.answer, (bad, q)
        for text in (q, p.answer, p.solution):
            assert "\\" not in outside_math(text), f"LaTeX outside $...$ would show as raw text: {text}"


# =================================================================== math correctness

def _parse_number(tok: str) -> Fraction:
    m = re.fullmatch(r"(-?\d+)\\tfrac\{(\d+)\}\{(\d+)\}", tok)  # mixed number
    if m:
        whole = int(m[1])
        return whole + (1 if whole >= 0 else -1) * Fraction(int(m[2]), int(m[3]))
    m = re.fullmatch(r"(-?)\\frac\{(\d+)\}\{(\d+)\}", tok)
    if m:
        return (-1 if m[1] else 1) * Fraction(int(m[2]), int(m[3]))
    return Fraction(tok)


def _answer_value(ans: str) -> Fraction:
    body = ans.strip("$").split(" = ")[0].strip()
    return _parse_number(body)


def check_math(p) -> str:
    """Independent correctness check. Returns the name of the check that ran."""
    f, q, a = p.facts, p.question, p.answer
    if p.topic in ("add_sub", "mul_div", "fractions"):
        tok = r"-?\d+\\tfrac\{\d+\}\{\d+\}|-?\\frac\{\d+\}\{\d+\}|-?\d+"
        m = re.fullmatch(rf"\$\$({tok}) (\+|-|\\times|\\div) ({tok})\$\$", q)
        assert m, q
        u, v = _parse_number(m[1]), _parse_number(m[3])
        expect = {"+": u + v, "-": u - v, r"\times": u * v, r"\div": u / v}[m[2]]
        assert _answer_value(a) == expect, (q, a)
        if p.topic == "fractions":  # fully simplified
            for n, d in re.findall(r"\\frac\{(\d+)\}\{(\d+)\}", a):
                assert math.gcd(int(n), int(d)) == 1, a
        return "arith"
    if p.topic == "order_ops":
        expr = q.strip("$").replace(r"\times", "*").replace(r"\div", "/").replace("^", "**")
        expr = expr.replace(r"\left[", "(").replace(r"\right]", ")")
        assert close(safe_eval(expr), int(a.strip("$"))), (q, a)
        return "order_ops"
    if "eq" in f:
        assert sp.latex(f["eq"]) in q and f["eq"].subs(x, f["x"]) is sp.true and f"x = {f['x']}" in a
        assert f["x"] != 0
        return "linear"
    if "eqs" in f:
        assert all(e.subs({x: f["x"], y: f["y"]}) is sp.true for e in f["eqs"])
        assert all(sp.latex(e) in q for e in f["eqs"]) and f"x = {f['x']}" in a and f"y = {f['y']}" in a
        return "system"
    form, places = f["form"], f["places"]
    if "poly" in f:
        assert sp.latex(f["poly"]) in q and len(set(f["roots"])) == 2
        assert all(sp.simplify(f["poly"].subs(x, r)) == 0 for r in f["roots"])
        if "pm" in f:  # quadratic formula: (B ± K√M)/D, reduced
            B, K, M, D = f["pm"]
            pm_roots = sorted([(B - K * math.sqrt(M)) / D, (B + K * math.sqrt(M)) / D])
            assert all(close(u, float(v)) for u, v in zip(pm_roots, f["roots"]))
            assert math.gcd(math.gcd(B, K), D) == 1
            if form != "decimal":
                assert f"\\sqrt{{{M}}}" in a and r"\pm" in a, a
            if form != "exact":
                assert all(shown_r(float(r), a, places) for r in f["roots"]), a
        else:
            assert all(sp.latex(r) in a for r in f["roots"]), a
        return "quadratic"
    if "q_expr" in f:
        assert sp.simplify(f["q_expr"] - f["ans_expr"]) == 0 and sp.latex(f["ans_expr"]) in a
        assert "^{-" not in a, a  # positive exponents only
        return "exponents"
    if "base" in f:
        b, arg, val = f["base"], f["arg"], f["x"]
        assert close(sp.N(sp.sympify(b) ** val), sp.N(arg), rel=1e-9)
        assert shown_r(float(val), a, places) or sp.latex(sp.nsimplify(val)) in a
        return "log"
    if "lhs" in f:
        assert close(sp.N(f["lhs"].subs(x, f["x"])), f["rhs"])
        assert f"x = {sp.latex(sp.nsimplify(f['x']))}" in a
        return "log equation"
    if "sides" in f:
        s0, s1, s2 = f["sides"]
        kind = "right" if s0**2 + s1**2 == s2**2 else ("acute" if s0**2 + s1**2 > s2**2 else "obtuse")
        assert kind == f["kind"] and s0 + s1 > s2 and (kind in a)
        return "converse"
    if "dims" in f:
        assert sp.simplify(f["d"] ** 2 - sum(d * d for d in f["dims"])) == 0
        if f["d"].is_Integer or form != "decimal":
            assert sp.latex(f["d"]) in a
        if not f["d"].is_Integer and form != "exact":
            assert shown_r(float(f["d"]), a, places)
        return "box diagonal"
    if "ladder" in q and {"a", "b"} <= f.keys():
        assert float(f["a"]) <= 0.6 * float(f["b"]), f"ladder too flat: {q}"
    if "TV" in q and {"a", "b"} <= f.keys():
        assert 1.3 <= float(f["b"]) / float(f["a"]) <= 1.9, f"odd TV shape: {q}"
    if {"a", "b", "c"} <= f.keys():
        assert sp.simplify(sp.sympify(f["a"]) ** 2 + sp.sympify(f["b"]) ** 2 - sp.sympify(f["c"]) ** 2) == 0
        unknown = [sp.sympify(v) for v in (f["a"], f["b"], f["c"]) if not shown(float(v), q, rel=1e-9)]
        assert len(unknown) == 1, q
        u = unknown[0]
        if u.is_Integer:
            assert shown(float(u), a, rel=1e-9), a
        else:
            assert (form == "decimal") != (sp.latex(u) in a), a  # exact form present unless decimal-only
            assert (form == "exact") != shown_r(float(u), a, places), a
        return "pythagorean"
    if "points" in f:
        m = f["m"]
        if "b" in f:
            assert all(Fraction(py) == m * px + f["b"] for px, py in f["points"])
        else:
            (x1, y1), (x2, y2) = f["points"]
            assert m == Fraction(y2 - y1, x2 - x1)
        if "m0" in f:
            assert m * f["m0"] == -1
        assert m != 0
        return "line"
    if "known" in f:
        ratio = {"opposite": math.sin, "adjacent": math.cos, "hypotenuse": lambda t: 1}
        t = math.radians(f["theta"])
        (ks, kv), (ws, wv) = f["known"], f["want"]
        assert close(wv / kv, ratio[ws](t) / ratio[ks](t))
        assert shown_r(wv, a, places)
        return "trig side"
    if "theta" in f:
        t = math.radians(f["theta"])
        assert close(math.tan(t), f["opp"] / f["adj"]) if "adj" in f else close(math.sin(t), f["opp"] / f["hyp"])
        assert shown_r(f["theta"], a, places)
        return "trig angle"
    if "df" in f:
        assert sp.simplify(sp.diff(f["f"], x) - f["df"]) == 0
        return "derivative"
    if "F" in f:
        assert sp.simplify(sp.diff(f["F"], x) - f["f"]) == 0
        return "antiderivative"
    if "lo" in f:  # Simpson's rule, independent of sympy's integrator
        g = sp.lambdify(x, f["f"])
        n, h = 200, (f["hi"] - f["lo"]) / 200
        s = g(f["lo"]) + g(f["hi"]) + sum((4 if i % 2 else 2) * g(f["lo"] + i * h) for i in range(1, n))
        assert close(s * h / 3, f["val"], rel=1e-6)
        return "definite integral"
    if "expr" in f:
        g = sp.lambdify(x, f["expr"])
        if f["a"] == sp.oo:
            assert close(g(1e7), f["val"], rel=1e-4)
        else:
            assert math.isclose((g(f["a"] - 1e-7) + g(f["a"] + 1e-7)) / 2, f["val"], rel_tol=1e-4, abs_tol=1e-5)
        return "limit"
    if "data" in f:
        d = sorted(f["data"])
        n = len(d)
        median = d[n // 2] if n % 2 else (d[n // 2 - 1] + d[n // 2]) / 2
        if "median" in a.lower():
            assert shown(median, a, rel=1e-9), a
        if "range" in a:
            assert shown(max(d) - min(d), a, rel=1e-9), a
        if "mode" in a:
            counts = {v: d.count(v) for v in d}
            top = max(counts.values())
            assert [v for v in counts if counts[v] == top] == [int(re.search(r"mode \$(\d+)\$", a)[1])]
        if "\\mu" in a or "Mean" in a:
            assert shown_r(sum(d) / n, a, places)
        if "sigma" in a:
            mu = sum(d) / n
            assert shown_r(math.sqrt(sum((v - mu) ** 2 for v in d) / n), a, places)
        return "stats"
    if p.topic == "percent":
        if "n" in f:
            assert f["v"] == Fraction(f["p"] * f["n"], 100)
        elif "whole" in f:
            assert Fraction(f["part"] * 100, f["whole"]) == f["p"]
        elif "sale" in f:
            assert Fraction(f["orig"] * (100 - f["p"]), 100) == f["sale"]
        else:
            assert f["pct"] == Fraction(f["new"] - f["old"], f["old"]) * 100 and f["pct"] != 0
        return "percent"
    if p.topic == "logs":  # e^(ln n)
        n = int(re.search(r"\\ln (\d+)", q)[1])
        assert a == f"${n}$"
        return "log identity"
    if "ans" in f:  # area/perimeter: exact (π) and decimal answers both match the computed value
        vals = f["ans"] if isinstance(f["ans"], tuple) else (f["ans"],)
        pis = pi_values(a)
        for v in vals:
            exact = any(close(v, pv) for pv in pis) or shown(v, a, rel=1e-9)
            decimal = shown_r(v, a, places)
            assert {"exact": exact, "decimal": decimal and not pis, "both": exact and decimal}[form], (form, a)
        return "displayed value"
    raise AssertionError(f"no correctness check for {p.topic}: {q}")


FORMS = [("both", 1), ("exact", 1), ("decimal", 2), ("decimal", 0)]


@pytest.mark.parametrize("topic,level", MATH, ids=[f"{t}-L{lv}" for t, lv in MATH])
def test_math_answers_are_correct(topic, level):
    t = TOPICS[topic]
    for form, places in (FORMS if t.exact_forms or t.rounding else FORMS[:1]):
        for p in problems(topic, level, form=form, places=places):
            check_math(p)


@pytest.mark.parametrize("topic", [t for t in TOPICS if TOPICS[t].exact_forms or TOPICS[t].rounding])
@pytest.mark.parametrize("form,places", FORMS)
def test_answer_forms(topic, form, places):
    place = {0: "whole number", 1: "tenth", 2: "hundredth", 3: "thousandth"}[places]
    for level in TOPICS[topic].variants:
        for p in problems(topic, level, form=form, places=places):
            decimals = re.findall(r"\\approx (-?\d+(?:\.(\d+))?)", p.answer)
            if decimals:  # every rounded value uses the requested place, and the question says so
                assert all(len(d) == places for _, d in decimals), p.answer
                assert f"nearest {place}" in p.question, p.question
            if form == "exact" and ("\\pi" in p.answer or "\\sqrt" in p.answer):
                assert not decimals and "Round" not in p.question and "exact" in p.question, p.question
            if form == "decimal":
                assert "\\pi" not in p.answer and "\\sqrt" not in p.answer, p.answer


# =================================================================== courses & skills

def test_every_topic_has_courses_and_skills():
    for t in TOPICS.values():
        assert t.courses and all(c in COURSES for c in t.courses)
        assert t.skills and all(s.levels for s in t.skills.values())
        for level, vs in t.variants.items():
            assert all(v.skill in t.skills and level in t.skills[v.skill].levels for v in vs)
    for course in COURSES:
        assert any(course in t.courses for t in TOPICS.values()), f"{course} has no topics"
        units = {t.category for t in TOPICS.values() if course in t.courses}
        assert units == set(COURSE_UNITS[course]), f"{course} unit order out of date: {units ^ set(COURSE_UNITS[course])}"


def test_chosen_skills_only():
    probs = generate_set("pythagorean", 2, 12, random.Random(3), skills=["find_a_leg"])
    assert {p.skill for p in probs} == {"find_a_leg"}
    # A skill that only exists at another level is used at its own level.
    probs = generate_set("quadratics", 1, 6, random.Random(3), skills=["quadratic_formula", "factor_x_bx_c"])
    assert {p.skill for p in probs} == {"quadratic_formula", "factor_x_bx_c"}
    assert all("pm" in p.facts for p in probs if p.skill == "quadratic_formula")
    with pytest.raises(KeyError):
        variants_for("quadratics", 2, ["no_such_skill"])


@pytest.mark.parametrize("topic", sorted(TOPICS))
def test_every_skill_generates_alone(topic):
    for sid in TOPICS[topic].skills:
        for level in (1, 3):
            probs = generate_set(topic, level, 4, random.Random(sid), skills=[sid])
            assert len(probs) == 4 and {p.skill for p in probs} == {sid}


# =================================================================== physics correctness

LAWS = {}
c = close


def _laws():
    # Each check uses a different relation than the generator did, where one exists.
    L = LAWS
    L["_kin_final_v"] = lambda G, A, g: c((A["v"] - G["v0"]) / G["t"], G["a"])
    L["_kin_free_fall"] = lambda G, A, g: c(0.5 * g * A["t"] ** 2, G["h"]) and c(A["v"] ** 2, 2 * g * G["h"])
    L["_kin_displacement"] = lambda G, A, g: c(A["d"], (2 * G["v0"] + G["a"] * G["t"]) / 2 * G["t"])
    L["_kin_braking"] = lambda G, A, g: c(A["d"], G["v0"] / 2 * A["t"])  # average speed x time
    L["_kin_throw_up"] = lambda G, A, g: c(A["h"], G["v0"] / 2 * A["t"] / 2)
    L["_proj_horiz_range"] = lambda G, A, g: c(0.5 * g * (A["x"] / G["v"]) ** 2, G["h"])
    L["_proj_horiz_full"] = lambda G, A, g: (c(A["speed"] ** 2, G["v"] ** 2 + 2 * g * G["h"])
                                             and c(A["x"], G["v"] * A["t"]))
    def trig(G):  # the 3-4-5 convention when the problem states it, else exact trig
        r = math.radians(G["theta"])
        return G.get("sin", math.sin(r)), G.get("cos", math.cos(r))

    L["_proj_angle"] = lambda G, A, g: (
        c(A["R"], 2 * G["v"] ** 2 * trig(G)[0] * trig(G)[1] / g)  # v^2 sin(2θ) / g
        and c(A["H"], (G["v"] * trig(G)[0]) ** 2 / (2 * g))
        and c(A["T"], 2 * math.sqrt(2 * A["H"] / g)))
    L["_newton_force"] = lambda G, A, g: c(A["F"] / G["m"], G["a"])
    L["_newton_accel"] = lambda G, A, g: c(A["a"] * G["m"], G["F"])
    L["_newton_friction"] = lambda G, A, g: c(G["F"] - G["mu"] * G["m"] * g, G["m"] * A["a"]) and A["a"] > 0
    L["_newton_incline"] = lambda G, A, g: c(A["a"], g * (trig(G)[0] - G["mu"] * trig(G)[1])) and A["a"] > 0

    def atwood(G, A, g):
        heavy, light = max(G["m1"], G["m2"]), min(G["m1"], G["m2"])
        return c(heavy * g - A["T"], heavy * A["a"]) and c(A["T"] - light * g, light * A["a"])
    L["_newton_atwood"] = atwood
    L["_energy_ke"] = lambda G, A, g: c(A["KE"], G["m"] * G["v"] ** 2 / 2)
    L["_energy_pe"] = lambda G, A, g: c(A["PE"], G["m"] * g * G["h"])
    L["_energy_work_angle"] = lambda G, A, g: c(A["W"], G["F"] * G["d"] * math.cos(math.radians(G["theta"])))
    L["_energy_coaster"] = lambda G, A, g: c(A["v"], g * math.sqrt(2 * G["h"] / g))  # = g * fall time
    L["_energy_power"] = lambda G, A, g: c(A["P"] * G["t"], G["m"] * g * G["h"])
    L["_energy_friction_loss"] = lambda G, A, g: (c(A["E"] + G["m"] * G["v"] ** 2 / 2, G["m"] * g * G["h"])
                                                  and A["E"] > 0)
    L["_mom_p"] = lambda G, A, g: c(A["p"], G["m"] * G["v"])
    L["_mom_impulse"] = lambda G, A, g: c(A["J"], G["F"] * G["t"])
    L["_mom_inelastic"] = lambda G, A, g: c(G["m1"] * G["v1"] + G["m2"] * G["v2"], (G["m1"] + G["m2"]) * A["vf"])

    def elastic(G, A, g):
        p0, p1 = G["m1"] * G["v1"], G["m1"] * A["v1f"] + G["m2"] * A["v2f"]
        k0, k1 = G["m1"] * G["v1"] ** 2, G["m1"] * A["v1f"] ** 2 + G["m2"] * A["v2f"] ** 2
        return c(p0, p1) and c(k0, k1)
    L["_mom_elastic"] = elastic
    L["_circ_accel"] = lambda G, A, g: c(A["ac"] * G["r"], G["v"] ** 2)
    L["_circ_string"] = lambda G, A, g: c(A["v"] * G["T"], 2 * math.pi * G["r"]) and c(A["F"] * G["r"], G["m"] * A["v"] ** 2)

    def orbit(G, A, g):
        r = G["R"] + G["h_km"] * 1e3
        return c(A["v"] ** 2 * r, 6.674e-11 * G["M"]) and c(A["v"] * A["T"], 2 * math.pi * r)
    L["_circ_orbit"] = orbit
    L["_ohm_current"] = lambda G, A, g: c(A["I"] * G["R"], G["V"])
    L["_ohm_voltage"] = lambda G, A, g: c(A["V"], G["I"] * G["R"])
    L["_ohm_resistance"] = lambda G, A, g: c(A["R"] * G["I"], G["V"])

    def series(G, A, g):
        Rs = [v for k, v in G.items() if k.startswith("R")]
        return c(sum(A["I"] * r for r in Rs), G["V"]) and c(A["V1"], A["I"] * G["R1"])  # Kirchhoff's loop rule
    L["_circ_series"] = series

    def parallel(G, A, g):
        Rs = [v for k, v in G.items() if k.startswith("R")]
        return c(sum(G["V"] / r for r in Rs), A["I"]) and c(A["P"], G["V"] * A["I"])  # junction rule
    L["_circ_parallel"] = parallel

    def combo(G, A, g):
        I3 = A["I"] - A["I2"]
        return c(G["V"], A["I"] * G["R1"] + A["I2"] * G["R2"]) and c(A["I2"] * G["R2"], I3 * G["R3"])
    L["_circ_combo"] = combo
    L["_coulomb"] = lambda G, A, g: c(A["F"] * G["r"] ** 2, 8.99e9 * G["q1"] * G["q2"] * 1e-12)
    L["_field"] = lambda G, A, g: (c(A["E"], abs(8.99e9 * G["q1"] * 1e-6 / (G["d"] / 2) ** 2
                                                  - 8.99e9 * G["q2"] * 1e-6 / (G["d"] / 2) ** 2)) and A["E"] > 0)
    L["_wave_speed"] = lambda G, A, g: c(A["v"], G["f"] * G["lam"]) and c(A["T"] * G["f"], 1)
    L["_wave_echo"] = lambda G, A, g: c(A["d"], G["v"] * G["t"]) or c(2 * A["d"], G["v"] * G["t"])
    L["_string_harmonic"] = lambda G, A, g: c(A["f"] * A["lam"], G["v"]) and c(A["lam"] * G["n"], 2 * G["L"])
    L["_snell"] = lambda G, A, g: c(G["n1"] * math.sin(math.radians(G["theta1"])),
                                    G["n2"] * math.sin(math.radians(A["theta2"])))
    L["_lens"] = lambda G, A, g: c(1 / G["f"], 1 / G["do"] + 1 / A["di"]) and c(A["m"], -A["di"] / G["do"])
    L["_heat_specific"] = lambda G, A, g: c(A["Q"], G["m"] * G["c"] * G["dT"])
    L["_heat_melt"] = lambda G, A, g: c(A["Q"], G["m"] * (2090 * -G["T0"] + 3.34e5))
    L["_gas"] = lambda G, A, g: c(A["P"] * G["V"] / 1000, G["n"] * 8.314 * G["T"]) and c(A["atm"] * 101325, A["P"])
    L["_density"] = lambda G, A, g: c(A["rho"] * G["V"], G["m"])
    L["_pressure_depth"] = lambda G, A, g: c(A["P"] - 101300, G["rho"] * g * G["h"])
    L["_buoyancy"] = lambda G, A, g: c(A["Fb"], 1000 * G["V"] * g) and c(A["Wapp"] + A["Fb"], G["rho"] * G["V"] * g)


_laws()

# Fastest each object can realistically go (m/s).
TOP_SPEED = {"baseball": 50, "tennis ball": 70, "soccer ball": 35, "bowling ball": 10, "hockey puck": 50,
             "cyclist and bike": 20, "car": 45, "shopping cart": 4, "sprinter": 12.5, "runner": 11,
             "skateboarder": 10, "cyclist": 20, "motorcycle": 60, "train": 40, "ball": 15, "child": 6}
TOP_ACCEL = {"car": 9, "runner": 5, "child": 7, "skater": 4, "sled": 5, "box": 6, "cart": 6}


def realistic(p) -> list[str]:
    G, A, what, v = p.facts["given"], p.facts["ans"], p.facts.get("what"), p.facts["variant"]
    issues = []
    speed = max([abs(s) for k, s in {**G, **A}.items() if k in ("v", "v0", "speed")] or [0])
    if what in TOP_SPEED and v != "_newton_force" and speed > TOP_SPEED[what]:
        issues.append(f"{what} at {speed:.3g} m/s")
    accel = A.get("ac", A.get("a", G.get("a")))
    if what in TOP_ACCEL and accel and accel > TOP_ACCEL[what]:
        issues.append(f"{what} accelerating at {accel:.3g} m/s^2")
    if v == "_wave_speed" and not 0.5 <= A["v"] <= 6000:
        issues.append(f"wave speed {A['v']:.3g}")
    if v == "_density" and not 0.1 <= A["rho"] <= 22.6:
        issues.append(f"density {A['rho']:.3g} g/cm^3")
    current = {**G, **A}.get("I")
    if current is not None and not 1e-4 <= current <= 20:
        issues.append(f"current {current:.3g} A")
    if v in ("_kin_free_fall", "_proj_horiz_full") and A["t"] > 6:
        issues.append(f"falls for {A['t']:.3g} s")
    if v == "_kin_braking" and G["a"] > 9:
        issues.append("braking harder than tires allow")
    return issues


@pytest.mark.parametrize("topic,level", PHYSICS, ids=[f"{t}-L{lv}" for t, lv in PHYSICS])
@pytest.mark.parametrize("g,nice", [(9.8, False), (10, True)], ids=["g9.8", "g10-whole"])
def test_physics(topic, level, g, nice):
    for p in problems(topic, level, g=g, nice=nice):
        G, A, var = p.facts["given"], p.facts["ans"], p.facts["variant"]
        assert var in LAWS, f"{var} has no physics check in tests/test_quality.py"
        assert LAWS[var](G, A, g), f"{var}: answers violate the check law {G} {A}"
        for k, val in G.items():
            if val == 0 or k == "n":  # stated in words: "from rest", "fourth harmonic"
                continue
            # negative values are stated as a size plus a direction in words
            assert num(abs(val)) in p.question or sig(abs(val), 3) in p.question, \
                f"given {k}={val} not shown: {p.question}"
        for k, val in A.items():
            assert shown(val, p.answer), f"answer {k}={val:.4g} not shown: {p.answer}"
            assert val != 0 or var == "_mom_inelastic", f"trivial answer {k} = 0"
        assert not realistic(p), f"{realistic(p)}: {p.question}"


@pytest.mark.parametrize("topic", sorted({t for t, _ in PHYSICS}))
def test_g_is_stated_exactly_when_it_matters(topic):
    for level in TOPICS[topic].variants:
        for v in TOPICS[topic].variants[level]:
            fn = v.fn
            for s in range(15):
                p98 = fn(_ctx(s, level, 9.8))
                p10 = fn(_ctx(s, level, 10))
                uses_g = p98.answer != p10.answer or p98.facts["given"] != p10.facts["given"]
                assert ("Use $g = 10" in p10.question) == uses_g, (fn.__name__, p10.question)
                assert "Use $g" not in p98.question


def _ctx(seed, level, g):
    from app.generators.core import Ctx
    return Ctx(rng=random.Random(seed), difficulty=level, g=g)


# AP-level problem types whose values can't all be simple (trig, square roots, physical constants).
NOT_WHOLE_NUMBER = {"_circ_orbit", "_coulomb", "_field", "_snell", "_lens", "_gas", "_circ_string",
                    "_string_harmonic", "_heat_melt", "_proj_horiz_full", "_circ_combo"}


def test_whole_number_mode():
    by_variant: dict[str, list[bool]] = {}
    for topic, level in PHYSICS:
        for p in problems(topic, level, g=10, nice=True):
            by_variant.setdefault(p.facts["variant"], []).append(is_nice_problem(p))
    weak = {v: f"{sum(r)}/{len(r)}" for v, r in by_variant.items()
            if v not in NOT_WHOLE_NUMBER and sum(r) / len(r) < 0.9}
    assert not weak, f"problem types that rarely give simple values in whole-number mode: {weak}"
