"""Procedural physics problem generators (SI units).

Each variant draws from a small table of real-world scenarios so the numbers make
physical sense for the object named, uses ``ctx.g`` (9.8 or 10 m/s^2), formats
answers with ``ctx.fmt`` (sig figs, or exact in whole-number mode) and records its
givens and answers in ``facts`` for the test suite.
"""

from __future__ import annotations

import math

from . import drawings as draw
from .core import Ctx, Problem, U, num, sig, step, topic, variant

G_UNIV = 6.674e-11
K_E = 8.99e9


def P(question: str, answer: str, solution: str, given: dict, ans: dict, what: str = "", figure: str = "",
      **facts) -> Problem:
    """``what`` names the moving object, so tests can check its speed is realistic. Extra ``facts``
    (e.g. a graph's points) are kept for the tests."""
    return Problem(question, answer, solution, figure=figure, facts={"given": given, "ans": ans, "what": what, **facts})


def pick(ctx: Ctx, table):
    return ctx.rng.choice(table)


def _fall(ctx: Ctx, lo: float, hi: float, st: float) -> tuple[float, float]:
    """A drop height in [lo, hi] and its fall time. In whole-number mode with g = 10 the time is
    a multiple of 0.2 s, so h = 5t^2 comes out with at most one decimal (0.8, 5, 7.2, 20 ...)."""
    if ctx.nice and ctx.g == 10:
        ts = [k / 5 for k in range(1, 40) if lo <= 5 * (k / 5) ** 2 <= hi]
        if ts:
            t = ctx.rng.choice(ts)
            return round(5 * t * t, 6), t
    h = step(ctx.rng, lo, hi, st)
    return h, math.sqrt(2 * h / ctx.g)


def _angle(ctx: Ctx, choices: list[int]) -> tuple[int, float, float, str]:
    """An angle with its sine and cosine. Whole-number mode uses the textbook 3-4-5 convention
    (sin 37° = 0.6, cos 37° = 0.8) and says so in the problem."""
    if ctx.nice:
        th = ctx.rng.choice([37, 53])
        s_, c_ = (0.6, 0.8) if th == 37 else (0.8, 0.6)
        return th, s_, c_, f" Use $\\sin {th}^\\circ = {s_}$ and $\\cos {th}^\\circ = {c_}$."
    th = ctx.rng.choice(choices)
    return th, math.sin(math.radians(th)), math.cos(math.radians(th)), ""


def r3(v: float) -> float:
    """Round to 3 significant figures (for derived values shown as givens)."""
    return float(f"{v:.3g}")


# Objects with realistic mass (kg) and speed (m/s) ranges: name, m_lo, m_hi, m_step, v_lo, v_hi, v_step
OBJECTS = [
    ("baseball", 0.145, 0.145, 1, 20, 45, 1),
    ("tennis ball", 0.058, 0.058, 1, 15, 50, 1),
    ("soccer ball", 0.43, 0.43, 1, 5, 30, 1),
    ("bowling ball", 5, 7.5, 0.5, 2, 9, 0.5),
    ("hockey puck", 0.17, 0.17, 1, 5, 40, 1),
    ("cyclist and bike", 60, 100, 5, 3, 12, 0.5),
    ("car", 900, 2000, 50, 5, 35, 1),
    ("shopping cart", 15, 40, 1, 0.5, 3, 0.5),
    ("sprinter", 55, 90, 1, 5, 10, 0.5),
]


def _object(ctx: Ctx):
    name, mlo, mhi, mst, vlo, vhi, vst = pick(ctx, OBJECTS)
    return name, step(ctx.rng, mlo, mhi, mst), step(ctx.rng, vlo, vhi, vst)


# ======================================================== Kinematics

topic("kinematics", "physics", "Kinematics", "1D kinematics",
      "Constant-acceleration motion, free fall and braking distances.", courses=['conceptual', 'ap1'], figures=True)

# name, v0 max, accel range (lo, hi, step), top speed
VEHICLES = [("car", 20, (1, 4, 0.5), 40), ("motorcycle", 20, (2, 6, 0.5), 50),
            ("train", 15, (0.2, 1.2, 0.1), 35), ("cyclist", 6, (0.5, 2, 0.5), 15)]


@variant("kinematics", 1, "Final velocity")
def _kin_final_v(ctx: Ctx) -> Problem:
    name, v0max, (alo, ahi, ast), vmax = pick(ctx, VEHICLES)
    while True:
        v0, a, t = step(ctx.rng, 0, v0max, 1), step(ctx.rng, alo, ahi, ast), step(ctx.rng, 2, 20, 1)
        v = v0 + a * t
        if v <= vmax:
            break
    start = "starts from rest and" if v0 == 0 else f"moving at ${num(v0)}{U('m/s')}$"
    return P(f"A {name} {start} accelerates uniformly at ${num(a)}{U('m/s^2')}$ for ${num(t)}{U('s')}$. "
             "What is its final speed?",
             f"$v = {ctx.fmt(v)}{U('m/s')}$", rf"$v = v_0 + at = {num(v0)} + ({num(a)})({num(t)})$",
             {"v0": v0, "a": a, "t": t}, {"v": v}, what=name)


def _segments(ctx: Ctx, n: int, lo: int, hi: int) -> list[int]:
    """Segment end times: n segments of 2-5 s each."""
    t, out = 0, [0]
    for _ in range(n):
        t += ctx.rng.randint(2, 5)
        out.append(t)
    return out


@variant("kinematics", 1, "Position-time graphs")
def _kin_xt_graph(ctx: Ctx) -> Problem:
    while True:
        ts = _segments(ctx, 3, 2, 5)
        vs = [ctx.rng.randint(-4, 4) for _ in range(3)]
        xs = [ctx.rng.randint(-2, 6)]
        for i, v in enumerate(vs):
            xs.append(xs[-1] + v * (ts[i + 1] - ts[i]))
        if vs[0] and vs[2] and len(set(vs)) == 3 and max(map(abs, xs)) <= 24:
            break
    pts = list(zip(ts, xs))
    step_y = 2 if max(map(abs, xs)) <= 12 else 4
    return P(f"The graph shows the position of a cart. Find its velocity (a) from $t = 0$ to $t = {ts[1]}{U('s')}$ "
             f"and (b) from $t = {ts[2]}$ to $t = {ts[3]}{U('s')}$.",
             f"(a) ${vs[0]}{U('m/s')}$ (b) ${vs[2]}{U('m/s')}$", "Velocity is the slope of a position-time graph.",
             {}, {"vA": vs[0], "vB": vs[2]}, figure=draw.motion_graph(pts, "x (m)", ystep=step_y),
             graph=pts, figure_required=True)


def _vt_points(ctx: Ctx, allow_negative: bool) -> list[tuple[int, int]]:
    while True:
        ts = _segments(ctx, 3, 2, 5)
        vs = [0 if not allow_negative else ctx.rng.choice([0, 2, 4])]
        for _ in range(3):
            vs.append(ctx.rng.randrange(-10 if allow_negative else 0, 21, 2))
        accels = [(vs[i + 1] - vs[i]) / (ts[i + 1] - ts[i]) for i in range(3)]
        reverses = min(vs) < 0 < max(vs)  # moves forward and backward, so distance ≠ |displacement|
        if accels[0] and float(accels[0]).is_integer() and (reverses if allow_negative else True) \
                and max(map(abs, vs)) > 0:
            return list(zip(ts, vs))


def _areas(pts):
    """Signed area (displacement) and total area (distance) under a piecewise-linear v-t graph."""
    disp = dist = 0.0
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if v0 * v1 < 0:  # crosses zero inside the segment: split it
            tc = t0 + (t1 - t0) * v0 / (v0 - v1)
            parts = [(t0, v0, tc, 0), (tc, 0, t1, v1)]
        else:
            parts = [(t0, v0, t1, v1)]
        for a, va, b, vb in parts:
            area = (va + vb) / 2 * (b - a)
            disp += area
            dist += abs(area)
    return disp, dist


@variant("kinematics", 2, "Velocity-time graphs")
def _kin_vt_graph(ctx: Ctx) -> Problem:
    pts = _vt_points(ctx, allow_negative=False)
    (t0, v0), (t1, v1) = pts[0], pts[1]
    a = (v1 - v0) / (t1 - t0)
    disp, _ = _areas(pts)
    return P(f"The graph shows the velocity of a cart. Find (a) its acceleration from $t = 0$ to "
             f"$t = {t1}{U('s')}$ and (b) its displacement from $t = 0$ to $t = {pts[-1][0]}{U('s')}$.",
             f"(a) ${ctx.fmt(a)}{U('m/s^2')}$ (b) ${ctx.fmt(disp)}{U('m')}$",
             "Acceleration is the slope; displacement is the area under the velocity-time graph.",
             {}, {"a": a, "d": disp}, figure=draw.motion_graph(pts, "v (m/s)", ystep=2),
             graph=pts, figure_required=True)


@variant("kinematics", 3, "Velocity-time graphs")
def _kin_vt_graph_signed(ctx: Ctx) -> Problem:
    pts = _vt_points(ctx, allow_negative=True)
    disp, dist = _areas(pts)
    end = pts[-1][0]
    return P(f"The graph shows the velocity of a cart moving along a straight track. From $t = 0$ to "
             f"$t = {end}{U('s')}$, find (a) its displacement and (b) the total distance it travels.",
             f"(a) ${ctx.fmt(disp)}{U('m')}$ (b) ${ctx.fmt(dist)}{U('m')}$",
             "Area above the axis counts as positive displacement and area below as negative; "
             "distance adds the sizes of all areas.",
             {}, {"d": disp, "dist": dist}, figure=draw.motion_graph(pts, "v (m/s)", ystep=2),
             graph=pts, figure_required=True)


DROPS = [("balcony", 4, 20), ("rooftop", 10, 60), ("bridge", 10, 80), ("cliff", 20, 120)]
DROPPED = ["stone", "wrench", "water balloon", "tennis ball", "set of keys", "pine cone"]


@variant("kinematics", 2, "Free fall")
def _kin_free_fall(ctx: Ctx) -> Problem:
    place, lo, hi = pick(ctx, DROPS)
    h, t = _fall(ctx, lo, hi, 1)
    return P(f"A {pick(ctx, DROPPED)} is dropped from rest off a ${num(h)}{U('m')}$ high {place}. Ignoring air "
             "resistance, (a) how long does it take to reach the ground and (b) how fast is it moving on impact?"
             + ctx.g_note(),
             f"(a) $t = {ctx.fmt(t)}{U('s')}$ (b) $v = {ctx.fmt(ctx.g * t)}{U('m/s')}$",
             r"$t = \sqrt{2h/g}$, $v = gt$", {"h": h}, {"t": t, "v": ctx.g * t})


# name, v0 max, accel range (lo, hi, step), top speed
MOVERS = [("cyclist", 8, (0.5, 2, 0.5), 15), ("skateboarder", 5, (0.5, 1.5, 0.5), 8),
          ("runner", 4, (0.5, 1.5, 0.5), 9), ("car", 20, (1, 3, 0.5), 35)]


@variant("kinematics", 2, "Displacement")
def _kin_displacement(ctx: Ctx) -> Problem:
    name, v0max, (alo, ahi, ast), vmax = pick(ctx, MOVERS)
    while True:
        v0, a, t = step(ctx.rng, 0, v0max, 1), step(ctx.rng, alo, ahi, ast), step(ctx.rng, 2, 12, 1)
        if v0 + a * t <= vmax:
            break
    d = v0 * t + 0.5 * a * t * t
    start = "starts from rest" if v0 == 0 else f"is moving at ${num(v0)}{U('m/s')}$"
    return P(f"A {name} {start} and accelerates at ${num(a)}{U('m/s^2')}$ for ${num(t)}{U('s')}$. "
             f"How far does the {name} travel in that time?",
             f"$\\Delta x = {ctx.fmt(d)}{U('m')}$", r"$\Delta x = v_0 t + \tfrac{1}{2}at^2$",
             {"v0": v0, "a": a, "t": t}, {"d": d}, what=name)


@variant("kinematics", 3, "Stopping distance")
def _kin_braking(ctx: Ctx) -> Problem:
    v0, a = step(ctx.rng, 12, 35, 1), step(ctx.rng, 4, 8, 0.5)
    road = "a dry road" if a >= 6 else "a wet road"
    return P(f"A driver traveling at ${num(v0)}{U('m/s')}$ brakes on {road} with a constant deceleration of "
             f"${num(a)}{U('m/s^2')}$. Find (a) the stopping distance and (b) the stopping time.",
             f"(a) ${ctx.fmt(v0 * v0 / (2 * a))}{U('m')}$ (b) ${ctx.fmt(v0 / a)}{U('s')}$",
             r"$v^2 = v_0^2 + 2a\Delta x \Rightarrow \Delta x = v_0^2 / 2a$; $t = v_0/a$",
             {"v0": v0, "a": a}, {"d": v0 * v0 / (2 * a), "t": v0 / a})


@variant("kinematics", 3, "Vertical throw")
def _kin_throw_up(ctx: Ctx) -> Problem:
    v0 = step(ctx.rng, 5, 30, 1)
    thing = pick(ctx, ["ball", "rock", "beanbag", "set of keys"])
    return P(f"A {thing} is thrown straight up at ${num(v0)}{U('m/s')}$. Find (a) the maximum height above the "
             "release point and (b) the total time until it returns to the release point." + ctx.g_note(),
             f"(a) ${ctx.fmt(v0 * v0 / (2 * ctx.g))}{U('m')}$ (b) ${ctx.fmt(2 * v0 / ctx.g)}{U('s')}$",
             r"$h = v_0^2/2g$, $t = 2v_0/g$", {"v0": v0}, {"h": v0 * v0 / (2 * ctx.g), "t": 2 * v0 / ctx.g})


# ======================================================== Projectiles

topic("projectile", "physics", "Kinematics", "Projectile motion",
      "Horizontal launches and angled launches over level ground.", courses=['conceptual', 'ap1'], figures=True)

# description, height range (lo, hi, step), speed range (lo, hi, step)
LAUNCHES = [
    ("A marble rolls off the edge of a ${h}$ high table", "the marble", "table", (0.7, 1.2, 0.05), (0.5, 3, 0.1)),
    ("A soccer ball is kicked horizontally off a ${h}$ high cliff", "the ball", "cliff", (10, 60, 1), (5, 20, 1)),
    ("A stone is thrown horizontally from a ${h}$ high bridge", "the stone", "bridge", (8, 40, 1), (4, 15, 1)),
    ("A diver runs horizontally off a ${h}$ high platform", "the diver", "platform", (3, 10, 0.5), (1.5, 4, 0.5)),
]


def _horizontal(ctx: Ctx):
    text, who, where, hr, vr = pick(ctx, LAUNCHES)
    (h, t), v = _fall(ctx, *hr), step(ctx.rng, *vr)
    lead = text.replace("${h}$", f"${num(h)}{U('m')}$") + f" at ${num(v)}{U('m/s')}$"
    return lead, who, where, h, v, t


def _launch_figure(h, v, where) -> str:
    return draw.horizontal_launch(h, where, f"{num(h)} m", f"{num(v)} m/s")


@variant("projectile", 1, "Horizontal launch: range")
def _proj_horiz_range(ctx: Ctx) -> Problem:
    lead, who, where, h, v, t = _horizontal(ctx)
    return P(f"{lead}. How far from the base of the {where} does {who} land?" + ctx.g_note(),
             f"$x = {ctx.fmt(v * t)}{U('m')}$", rf"$t = \sqrt{{2h/g}} = {ctx.fmt(t)}\,\mathrm{{s}}$, $x = v t$",
             {"h": h, "v": v}, {"x": v * t}, figure=_launch_figure(h, v, where))


@variant("projectile", 2, "Horizontal launch: time, range & speed")
def _proj_horiz_full(ctx: Ctx) -> Problem:
    lead, who, where, h, v, t = _horizontal(ctx)
    vy = ctx.g * t
    return P(f"{lead}. Find (a) the time in the air, (b) how far from the base it lands, and (c) its speed "
             "just before it lands." + ctx.g_note(),
             f"(a) ${ctx.fmt(t)}{U('s')}$ (b) ${ctx.fmt(v * t)}{U('m')}$ (c) ${ctx.fmt(math.hypot(v, vy))}{U('m/s')}$",
             r"$t = \sqrt{2h/g}$, $x = vt$, $v_y = gt$, speed $= \sqrt{v^2 + v_y^2}$",
             {"h": h, "v": v}, {"t": t, "x": v * t, "speed": math.hypot(v, vy)}, figure=_launch_figure(h, v, where))


@variant("projectile", 3, "Angled launch")
def _proj_angle(ctx: Ctx) -> Problem:
    th, sin_, cos_, trig_note = _angle(ctx, [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70])
    v = step(ctx.rng, 10, 50, 10) if ctx.nice else step(ctx.rng, 10, 35, 1)
    vx, vy = v * cos_, v * sin_
    thing = pick(ctx, ["A golf ball is", "A soccer ball is", "A projectile is", "A water balloon is"])
    T = 2 * vy / ctx.g
    return P(f"{thing} launched at ${num(v)}{U('m/s')}$, ${th}^\\circ$ above the horizontal, over level ground. "
             "Find (a) the time of flight, (b) the maximum height, (c) the horizontal range." + ctx.g_note() + trig_note,
             f"(a) ${ctx.fmt(T)}{U('s')}$ (b) ${ctx.fmt(vy * vy / (2 * ctx.g))}{U('m')}$ "
             f"(c) ${ctx.fmt(vx * T)}{U('m')}$",
             rf"$v_x = {ctx.fmt(vx)}$, $v_y = {ctx.fmt(vy)}$; $T = 2v_y/g$, $H = v_y^2/2g$, $R = v_x T$",
             {"v": v, "theta": th, **({"sin": sin_, "cos": cos_} if trig_note else {})},
             {"T": T, "H": vy * vy / (2 * ctx.g), "R": vx * T},
             figure=draw.angled_launch(th, f"{num(v)} m/s", f"{th}°"))


# ======================================================== Forces

topic("newton", "physics", "Forces & dynamics", "Newton's laws & forces",
      "F = ma, friction, inclined planes and Atwood machines.", courses=['conceptual', 'ap1'], figures=True)

# noun, mass range (lo, hi, step), acceleration range (lo, hi, step)
PUSHED = [("cart", (2, 40, 1), (0.5, 5, 0.5)), ("car", (900, 2000, 50), (1, 4, 0.5)),
          ("sled", (10, 60, 1), (0.5, 3, 0.5)), ("box", (5, 50, 1), (0.5, 4, 0.5)),
          ("skater", (40, 90, 1), (0.5, 3, 0.5)), ("hockey puck", (0.17, 0.17, 1), (5, 30, 1))]


@variant("newton", 1, "F = ma")
def _newton_force(ctx: Ctx) -> Problem:
    name, mr, ar = pick(ctx, PUSHED)
    m, a = step(ctx.rng, *mr), step(ctx.rng, *ar)
    return P(f"What net force is needed to accelerate a ${num(m)}{U('kg')}$ {name} at ${num(a)}{U('m/s^2')}$?",
             f"$F = {ctx.fmt(m * a)}{U('N')}$", "$F = ma$", {"m": m, "a": a}, {"F": m * a}, what=name)


@variant("newton", 1, "F = ma")
def _newton_accel(ctx: Ctx) -> Problem:
    name, mr, ar = pick(ctx, PUSHED)
    m = step(ctx.rng, *mr)
    F = r3(m * step(ctx.rng, *ar))
    return P(f"A net force of ${num(F)}{U('N')}$ acts on a ${num(m)}{U('kg')}$ {name}. Find its acceleration.",
             f"$a = {ctx.fmt(F / m)}{U('m/s^2')}$", "$a = F/m$", {"F": F, "m": m}, {"a": F / m}, what=name)


def _fbd_forces(ctx: Ctx, two_d: bool):
    """Forces whose net can't be misread off the diagram (the net never equals a drawn force)."""
    while True:
        forces = _fbd_draw(ctx, two_d)
        net = math.hypot(forces["right"] - forces["left"], forces["up"] - forces["down"])
        if all(abs(net - F) > 1e-9 for F in forces.values()):
            return forces


def _fbd_draw(ctx: Ctx, two_d: bool):
    """Forces (N) on a box: right/left always differ; up/down differ only for a 2-D problem.
    In whole-number mode a 2-D net force comes from a 3-4-5-style triple, so its size is whole."""
    if two_d and ctx.nice:
        a, b, _ = ctx.rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17)])
        k = ctx.rng.choice([1, 2, 5]) if a > 3 else ctx.rng.choice([5, 10, 15, 20])
        fx, fy = (a * k, b * k) if ctx.rng.random() < 0.5 else (b * k, a * k)
        left, down = ctx.rng.randrange(0, 60, 5), ctx.rng.randrange(20, 80, 5)
        return {"right": left + fx, "left": left, "up": down + fy, "down": down}
    while True:
        r, l_ = ctx.rng.randrange(10, 125, 5), ctx.rng.randrange(0, 85, 5)
        up = ctx.rng.randrange(20, 125, 5)
        down = ctx.rng.randrange(20, 125, 5) if two_d else up
        if r != l_ and (not two_d or up != down):
            return {"right": r, "left": l_, "up": up, "down": down}


def _fbd_figure(forces: dict) -> str:
    biggest = max(forces.values())
    return draw.free_body([(d, 1.2 * F / biggest, f"{F} N") for d, F in forces.items() if F])


@variant("newton", 1, "Free-body diagrams")
def _newton_fbd(ctx: Ctx) -> Problem:
    forces = _fbd_forces(ctx, two_d=False)
    m = ctx.rng.choice([2, 4, 5, 8, 10, 12, 15, 20, 25])
    net = forces["right"] - forces["left"]
    side = "to the right" if net > 0 else "to the left"
    return P(f"The free-body diagram shows every force acting on a ${m}{U('kg')}$ box. Find (a) the net force "
             "and (b) the box's acceleration.",
             f"(a) ${abs(net)}{U('N')}$ {side} (b) ${ctx.fmt(abs(net) / m)}{U('m/s^2')}$ {side}",
             "The vertical forces balance; the net force is the difference of the horizontal forces, and $a = F/m$.",
             {"m": m}, {"F": abs(net), "a": abs(net) / m}, figure=_fbd_figure(forces), forces=forces,
             figure_required=True)


@variant("newton", 2, "Free-body diagrams")
def _newton_fbd_2d(ctx: Ctx) -> Problem:
    forces = _fbd_forces(ctx, two_d=True)
    fx, fy = forces["right"] - forces["left"], forces["up"] - forces["down"]
    net = math.hypot(fx, fy)
    angle = math.degrees(math.atan2(abs(fy), abs(fx)))
    where = f"{'above' if fy > 0 else 'below'} the {'+' if fx > 0 else '−'}x direction" if fx else ""
    return P("The free-body diagram shows every force acting on a box. Find the magnitude of the net force "
             "and the angle it makes with the horizontal.",
             f"$F_{{net}} = {ctx.fmt(net)}{U('N')}$ at ${ctx.fmt(angle)}^\\circ$ {where}".rstrip(),
             f"$F_x = {fx}\\,\\mathrm{{N}}$, $F_y = {fy}\\,\\mathrm{{N}}$, $F = \\sqrt{{F_x^2 + F_y^2}}$",
             {}, {"F": net, "angle": angle}, figure=_fbd_figure(forces), forces=forces, figure_required=True)


@variant("newton", 2, "Friction")
def _newton_friction(ctx: Ctx) -> Problem:
    m, mu = step(ctx.rng, 10, 60, 1), step(ctx.rng, 0.1, 0.5, 0.05)
    fr = mu * m * ctx.g
    F = step(ctx.rng, math.ceil(fr * 1.2 / 10) * 10, math.ceil(fr * 2.5 / 10) * 10, 10)
    a = (F - fr) / m
    return P(f"A ${num(m)}{U('kg')}$ crate is pushed across a floor with a horizontal force of ${num(F)}{U('N')}$. "
             f"The coefficient of kinetic friction is ${num(mu)}$. Find the crate's acceleration." + ctx.g_note(),
             f"$a = {ctx.fmt(a)}{U('m/s^2')}$",
             rf"$f_k = \mu m g = {ctx.fmt(fr)}\,\mathrm{{N}}$; $a = (F - f_k)/m$",
             {"m": m, "F": F, "mu": mu}, {"a": a},
             figure=draw.pushed_crate(f"{num(F)} N", f"μₖ = {num(mu)}", f"{num(m)} kg"))


@variant("newton", 3, "Inclines")
def _newton_incline(ctx: Ctx) -> Problem:
    th, sin_, cos_, trig_note = _angle(ctx, [25, 30, 35, 40, 45])
    mu = step(ctx.rng, 0.1, 0.4, 0.05)
    a = ctx.g * (sin_ - mu * cos_)
    return P(f"A block slides down a ${th}^\\circ$ incline. The coefficient of kinetic friction is ${num(mu)}$. "
             "Find its acceleration." + ctx.g_note() + trig_note,
             f"$a = {ctx.fmt(a)}{U('m/s^2')}$", r"$a = g(\sin\theta - \mu_k \cos\theta)$",
             {"theta": th, "mu": mu, **({"sin": sin_, "cos": cos_} if trig_note else {})}, {"a": a},
             figure=draw.incline(th, f"{th}°", f"μₖ = {num(mu)}"))


@variant("newton", 3, "Atwood machine")
def _newton_atwood(ctx: Ctx) -> Problem:
    m1, m2 = step(ctx.rng, 1, 10, 0.5), step(ctx.rng, 1, 10, 0.5)
    while m1 == m2:
        m2 = step(ctx.rng, 1, 10, 0.5)
    a = abs(m1 - m2) * ctx.g / (m1 + m2)
    T = 2 * m1 * m2 * ctx.g / (m1 + m2)
    return P(f"Masses of ${num(m1)}{U('kg')}$ and ${num(m2)}{U('kg')}$ hang from a light string over a "
             "frictionless pulley (Atwood machine). Find (a) the acceleration and (b) the string tension." + ctx.g_note(),
             f"(a) ${ctx.fmt(a)}{U('m/s^2')}$ (b) ${ctx.fmt(T)}{U('N')}$",
             r"$a = \frac{|m_1 - m_2|g}{m_1 + m_2}$, $T = \frac{2m_1 m_2 g}{m_1 + m_2}$",
             {"m1": m1, "m2": m2}, {"a": a, "T": T},
             figure=draw.atwood(f"{num(m1)} kg", f"{num(m2)} kg", m1, m2))


# ======================================================== Energy

topic("energy", "physics", "Work, energy & power", "Work, energy & power",
      "Kinetic/potential energy, work done by forces, energy conservation, power.", courses=['conceptual', 'ap1'], figures=True)


@variant("energy", 1, "Kinetic energy")
def _energy_ke(ctx: Ctx) -> Problem:
    name, m, v = _object(ctx)
    return P(f"Find the kinetic energy of a ${num(m)}{U('kg')}$ {name} moving at ${num(v)}{U('m/s')}$.",
             f"$KE = {ctx.fmt(0.5 * m * v * v)}{U('J')}$", r"$KE = \tfrac{1}{2}mv^2$",
             {"m": m, "v": v}, {"KE": 0.5 * m * v * v}, what=name)


# noun, mass range, height range, verb phrase
LIFTS = [("textbook", (0.5, 3, 0.5), (0.5, 2, 0.1), "is lifted onto a shelf"),
         ("box", (5, 30, 1), (0.5, 2, 0.1), "is lifted onto a truck bed"),
         ("hiker", (45, 95, 1), (100, 900, 10), "climbs a hill"),
         ("elevator car", (500, 1500, 50), (3, 60, 1), "rises"),
         ("bucket of water", (5, 15, 0.5), (2, 20, 1), "is hauled up a well")]


@variant("energy", 1, "Potential energy")
def _energy_pe(ctx: Ctx) -> Problem:
    name, mr, hr, verb = pick(ctx, LIFTS)
    m, h = step(ctx.rng, *mr), step(ctx.rng, *hr)
    return P(f"A ${num(m)}{U('kg')}$ {name} {verb} through a height of ${num(h)}{U('m')}$. How much gravitational "
             "potential energy does it gain?" + ctx.g_note(),
             f"$\\Delta PE = {ctx.fmt(m * ctx.g * h)}{U('J')}$", r"$\Delta PE = mgh$",
             {"m": m, "h": h}, {"PE": m * ctx.g * h})


@variant("energy", 2, "Work")
def _energy_work_angle(ctx: Ctx) -> Problem:
    F, d, th = step(ctx.rng, 20, 200, 5), step(ctx.rng, 2, 50, 1), ctx.rng.choice([0, 15, 20, 25, 30, 35, 40, 45, 60])
    W = F * d * math.cos(math.radians(th))
    what = pick(ctx, ["a sled", "a wagon", "a suitcase", "a crate"])
    return P(f"A rope pulls {what} ${num(d)}{U('m')}$ across level ground with a force of ${num(F)}{U('N')}$ "
             f"at ${th}^\\circ$ above the horizontal. How much work does the rope do?",
             f"$W = {ctx.fmt(W)}{U('J')}$", r"$W = Fd\cos\theta$", {"F": F, "d": d, "theta": th}, {"W": W},
             figure=draw.rope_pull(th, f"{num(F)} N", f"{th}°"))


@variant("energy", 2, "Energy conservation")
def _energy_coaster(ctx: Ctx) -> Problem:
    if ctx.nice and ctx.g == 10:
        v = step(ctx.rng, 10, 36, 2)
        h = v * v / 20  # one decimal at most
    else:
        h = step(ctx.rng, 5, 70, 1)
        v = math.sqrt(2 * ctx.g * h)
    what = pick(ctx, ["A roller-coaster car starts from rest", "A skateboarder starts from rest",
                      "A sled starts from rest"])
    return P(f"{what} at the top of a ${num(h)}{U('m')}$ high slope. Ignoring friction, how fast is it moving "
             "at the bottom?" + ctx.g_note(),
             f"$v = {ctx.fmt(v)}{U('m/s')}$", r"$mgh = \tfrac{1}{2}mv^2 \Rightarrow v = \sqrt{2gh}$", {"h": h}, {"v": v},
             figure=draw.coaster(f"{num(h)} m"))


@variant("energy", 3, "Power")
def _energy_power(ctx: Ctx) -> Problem:
    m, h, t = step(ctx.rng, 40, 95, 1), step(ctx.rng, 3, 20, 0.5), step(ctx.rng, 4, 30, 1)
    return P(f"A ${num(m)}{U('kg')}$ student runs up stairs with a vertical rise of ${num(h)}{U('m')}$ in "
             f"${num(t)}{U('s')}$. What average power do they develop against gravity?" + ctx.g_note(),
             f"$P = {ctx.fmt(m * ctx.g * h / t)}{U('W')}$", r"$P = mgh/t$", {"m": m, "h": h, "t": t},
             {"P": m * ctx.g * h / t})


@variant("energy", 3, "Energy lost to friction")
def _energy_friction_loss(ctx: Ctx) -> Problem:
    m, h = step(ctx.rng, 20, 80, 1), step(ctx.rng, 2, 8, 0.5)
    v = step(ctx.rng, 2, math.sqrt(2 * ctx.g * h) * 0.9, 0.5)
    W_fr = m * ctx.g * h - 0.5 * m * v * v
    return P(f"A ${num(m)}{U('kg')}$ child slides from rest down a playground slide ${num(h)}{U('m')}$ high and "
             f"reaches the bottom at ${num(v)}{U('m/s')}$. How much energy was transformed by friction?" + ctx.g_note(),
             f"${ctx.fmt(W_fr)}{U('J')}$", r"$E_{\text{friction}} = mgh - \tfrac{1}{2}mv^2$",
             {"m": m, "h": h, "v": v}, {"E": W_fr})


# ======================================================== Momentum

topic("momentum", "physics", "Momentum", "Momentum & collisions",
      "Momentum, impulse, inelastic and elastic 1D collisions.", courses=['conceptual', 'ap1'], figures=True)


@variant("momentum", 1, "Momentum")
def _mom_p(ctx: Ctx) -> Problem:
    name, m, v = _object(ctx)
    return P(f"Find the momentum of a ${num(m)}{U('kg')}$ {name} moving at ${num(v)}{U('m/s')}$.",
             f"$p = {ctx.fmt(m * v)}{U('kg\\cdot m/s')}$", "$p = mv$", {"m": m, "v": v}, {"p": m * v}, what=name)


# description, force range (N), contact time range (s)
HITS = [("A soccer player kicks a ball with an average force of {F}", (100, 900, 10), (0.005, 0.03, 0.001)),
        ("A bat hits a baseball with an average force of {F}", (1000, 8000, 100), (0.0005, 0.002, 0.0001)),
        ("A car's brakes exert an average force of {F}", (2000, 9000, 100), (1, 5, 0.5)),
        ("A tennis racket hits a ball with an average force of {F}", (200, 800, 10), (0.003, 0.008, 0.001))]


@variant("momentum", 1, "Impulse")
def _mom_impulse(ctx: Ctx) -> Problem:
    text, fr, tr = pick(ctx, HITS)
    F, t = step(ctx.rng, *fr), step(ctx.rng, *tr)
    return P(text.replace("{F}", f"${num(F)}{U('N')}$") + f" for ${num(t)}{U('s')}$. What impulse is delivered?",
             f"$J = {ctx.fmt(F * t)}{U('N\\cdot s')}$", r"$J = F\Delta t$", {"F": F, "t": t}, {"J": F * t})


@variant("momentum", 2, "Inelastic collisions")
def _mom_inelastic(ctx: Ctx) -> Problem:
    m1, m2 = step(ctx.rng, 800, 2500, 100), step(ctx.rng, 800, 2500, 100)
    v1, v2 = step(ctx.rng, 5, 25, 1), step(ctx.rng, -10, 10, 1)
    vf = (m1 * v1 + m2 * v2) / (m1 + m2)
    other = ("at rest" if v2 == 0 else f"moving at ${num(abs(v2))}{U('m/s')}$ in the "
             + ("same direction" if v2 > 0 else "opposite direction"))
    return P(f"A ${num(m1)}{U('kg')}$ car moving at ${num(v1)}{U('m/s')}$ collides head-on with and sticks to a "
             f"${num(m2)}{U('kg')}$ car {other}. Find their common velocity just after the collision "
             "(positive = the first car's original direction).",
             f"$v_f = {ctx.fmt(vf)}{U('m/s')}$", r"$v_f = \frac{m_1 v_1 + m_2 v_2}{m_1 + m_2}$",
             {"m1": m1, "m2": m2, "v1": v1, "v2": v2}, {"vf": vf},
             figure=draw.collision(f"{num(m1)} kg", f"{num(v1)} m/s", f"{num(m2)} kg",
                                   f"{num(abs(v2))} m/s" if v2 else "at rest", (v2 > 0) - (v2 < 0)))


@variant("momentum", 3, "Elastic collisions")
def _mom_elastic(ctx: Ctx) -> Problem:
    m1, m2 = step(ctx.rng, 0.1, 5, 0.1), step(ctx.rng, 0.1, 5, 0.1)
    while abs(m1 - m2) < 0.05:
        m2 = step(ctx.rng, 0.1, 5, 0.1)
    v1 = step(ctx.rng, 1, 10, 0.5)
    v1f = (m1 - m2) / (m1 + m2) * v1
    v2f = 2 * m1 / (m1 + m2) * v1
    return P(f"A ${num(m1)}{U('kg')}$ cart moving at ${num(v1)}{U('m/s')}$ hits a stationary ${num(m2)}{U('kg')}$ "
             "cart in a perfectly elastic head-on collision on a frictionless track. Find both final velocities.",
             f"$v_1' = {ctx.fmt(v1f)}{U('m/s')}$, $v_2' = {ctx.fmt(v2f)}{U('m/s')}$",
             r"$v_1' = \frac{m_1 - m_2}{m_1 + m_2}v_1$, $v_2' = \frac{2m_1}{m_1 + m_2}v_1$",
             {"m1": m1, "m2": m2, "v1": v1}, {"v1f": v1f, "v2f": v2f},
             figure=draw.collision(f"{num(m1)} kg", f"{num(v1)} m/s", f"{num(m2)} kg", "at rest", 0))


# ======================================================== Circular motion & gravitation

topic("circular", "physics", "Circular motion & gravitation", "Circular motion & gravitation",
      "Centripetal acceleration and force, universal gravitation, orbits.", courses=['conceptual', 'ap1'])

# description, radius range, speed range, largest realistic centripetal acceleration (m/s^2)
TURNS = [("A car rounds a curve of radius {r}", (30, 200, 5), (8, 30, 1), 8, "car"),
         ("A ball on a string moves in a circle of radius {r}", (0.3, 1.5, 0.1), (1, 8, 0.5), 150, "ball"),
         ("A child rides a merry-go-round {r} from the center", (1, 4, 0.5), (1, 5, 0.5), 6, "child"),
         ("A runner rounds a curved track of radius {r}", (30, 40, 1), (5, 9, 0.5), 4, "runner")]


@variant("circular", 1, "Centripetal acceleration")
def _circ_accel(ctx: Ctx) -> Problem:
    text, rr, vr, amax, name = pick(ctx, TURNS)
    while True:
        r, v = step(ctx.rng, *rr), step(ctx.rng, *vr)
        if v * v / r <= amax:
            break
    return P(text.replace("{r}", f"${num(r)}{U('m')}$") + f" at a constant ${num(v)}{U('m/s')}$. "
             "Find its centripetal acceleration.",
             f"$a_c = {ctx.fmt(v * v / r)}{U('m/s^2')}$", r"$a_c = v^2/r$", {"r": r, "v": v}, {"ac": v * v / r},
             what=name)


@variant("circular", 2, "Centripetal force")
def _circ_string(ctx: Ctx) -> Problem:
    m, r, T = step(ctx.rng, 0.2, 2, 0.1), step(ctx.rng, 0.3, 1.5, 0.1), step(ctx.rng, 0.5, 3, 0.1)
    v = 2 * math.pi * r / T
    return P(f"A ${num(m)}{U('kg')}$ ball on a string moves in a horizontal circle of radius ${num(r)}{U('m')}$, "
             f"completing one revolution every ${num(T)}{U('s')}$. Find (a) its speed and (b) the centripetal force.",
             f"(a) ${ctx.fmt(v)}{U('m/s')}$ (b) ${ctx.fmt(m * v * v / r)}{U('N')}$",
             r"$v = 2\pi r / T$, $F_c = mv^2/r$", {"m": m, "r": r, "T": T}, {"v": v, "F": m * v * v / r})


BODIES = [("Earth", 5.97e24, 6.37e6), ("Mars", 6.42e23, 3.39e6), ("the Moon", 7.35e22, 1.74e6),
          ("Jupiter", 1.90e27, 6.99e7), ("Venus", 4.87e24, 6.05e6), ("Mercury", 3.30e23, 2.44e6)]


@variant("circular", 3, "Orbits")
def _circ_orbit(ctx: Ctx) -> Problem:
    name, M, R = pick(ctx, BODIES)
    h = step(ctx.rng, 200, 2000, 50) * 1e3
    r = R + h
    v = math.sqrt(G_UNIV * M / r)
    return P(f"A satellite orbits {name} (mass ${sig(M, 3)}{U('kg')}$, radius ${sig(R, 3)}{U('m')}$) at an "
             f"altitude of ${num(h / 1000)}{U('km')}$. Find (a) its orbital speed and (b) its period.",
             f"(a) ${ctx.fmt(v)}{U('m/s')}$ (b) ${ctx.fmt(2 * math.pi * r / v)}{U('s')}$",
             r"$v = \sqrt{GM/r}$ with $r = R + h$; $T = 2\pi r/v$",
             {"M": M, "R": R, "h_km": h / 1000}, {"v": v, "T": 2 * math.pi * r / v})


# ======================================================== Circuits

topic("circuits", "physics", "Electricity", "DC circuits",
      "Ohm's law, power, and series/parallel resistor networks.", courses=['conceptual'], figures=True)

E12 = [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82]
RESISTORS = [r * k for k in (1, 10, 100) for r in E12]  # standard values, 10 Ω – 8.2 kΩ
BATTERIES = [1.5, 3, 4.5, 6, 9, 12, 24]
NICE_RESISTORS = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 40, 60]
NICE_BATTERIES = [3, 6, 9, 12, 24]
OHM = U("\\Omega")


def _resistors(ctx: Ctx, k: int) -> list[int]:
    return ctx.rng.sample(NICE_RESISTORS if ctx.nice else RESISTORS[:24], k)


def _battery(ctx: Ctx, smallest: float = 1.5) -> float:
    return ctx.rng.choice([v for v in (NICE_BATTERIES if ctx.nice else BATTERIES) if v >= smallest])


@variant("circuits", 1, "Ohm's law")
def _ohm_current(ctx: Ctx) -> Problem:
    V, R = _battery(ctx), _resistors(ctx, 1)[0]
    return P(f"A ${num(V)}{U('V')}$ battery is connected across a ${R}{OHM}$ resistor. Find the current.",
             f"$I = {ctx.fmt(V / R)}{U('A')}$", "$I = V/R$", {"V": V, "R": R}, {"I": V / R})


@variant("circuits", 1, "Ohm's law")
def _ohm_voltage(ctx: Ctx) -> Problem:
    R, I = _resistors(ctx, 1)[0], step(ctx.rng, 0.02, 0.5, 0.01)
    return P(f"A current of ${num(I)}{U('A')}$ flows through a ${R}{OHM}$ resistor. Find the voltage across it.",
             f"$V = {ctx.fmt(I * R)}{U('V')}$", "$V = IR$", {"I": I, "R": R}, {"V": I * R})


@variant("circuits", 1, "Ohm's law")
def _ohm_resistance(ctx: Ctx) -> Problem:
    V, I = _battery(ctx, 3), step(ctx.rng, 0.05, 2, 0.05)
    return P(f"A device draws ${num(I)}{U('A')}$ from a ${num(V)}{U('V')}$ battery. What is its resistance?",
             f"$R = {ctx.fmt(V / I)}{OHM}$", "$R = V/I$", {"V": V, "I": I}, {"R": V / I})


def _resistor_list(Rs):
    return ", ".join(f"${r}{OHM}$" for r in Rs[:-1]) + f" and ${Rs[-1]}{OHM}$"


@variant("circuits", 2, "Series circuits")
def _circ_series(ctx: Ctx) -> Problem:
    Rs = _resistors(ctx, ctx.rng.randint(2, 3))
    V = _battery(ctx, 4.5)
    Req = sum(Rs)
    return P(f"Resistors of {_resistor_list(Rs)} are connected in series to a ${num(V)}{U('V')}$ battery. Find "
             "(a) the equivalent resistance, (b) the current, and (c) the voltage across the first resistor.",
             f"(a) ${ctx.fmt(Req)}{OHM}$ (b) ${ctx.fmt(V / Req)}{U('A')}$ (c) ${ctx.fmt(V / Req * Rs[0])}{U('V')}$",
             r"Series: $R_{eq} = \sum R_i$; $I = V/R_{eq}$; $V_1 = IR_1$",
             {"V": V, **{f"R{i + 1}": r for i, r in enumerate(Rs)}},
             {"Req": Req, "I": V / Req, "V1": V / Req * Rs[0]},
             figure=draw.series_circuit([f"{r} Ω" for r in Rs], f"{num(V)} V"))


@variant("circuits", 2, "Parallel circuits")
def _circ_parallel(ctx: Ctx) -> Problem:
    Rs = _resistors(ctx, ctx.rng.randint(2, 3))
    V = _battery(ctx, 4.5)
    Req = 1 / sum(1 / r for r in Rs)
    return P(f"Resistors of {_resistor_list(Rs)} are connected in parallel to a ${num(V)}{U('V')}$ battery. Find "
             "(a) the equivalent resistance, (b) the total current, and (c) the total power delivered.",
             f"(a) ${ctx.fmt(Req)}{OHM}$ (b) ${ctx.fmt(V / Req)}{U('A')}$ (c) ${ctx.fmt(V * V / Req)}{U('W')}$",
             r"Parallel: $1/R_{eq} = \sum 1/R_i$; $I = V/R_{eq}$; $P = V^2/R_{eq}$",
             {"V": V, **{f"R{i + 1}": r for i, r in enumerate(Rs)}},
             {"Req": Req, "I": V / Req, "P": V * V / Req},
             figure=draw.parallel_circuit([f"{r} Ω" for r in Rs], f"{num(V)} V"))


@variant("circuits", 3, "Combination circuits")
def _circ_combo(ctx: Ctx) -> Problem:
    R1, R2, R3 = _resistors(ctx, 3)
    V = _battery(ctx, 6)
    Rp = R2 * R3 / (R2 + R3)
    Req = R1 + Rp
    I = V / Req
    return P(f"Resistor $R_1 = {R1}{OHM}$ is in series with a parallel pair $R_2 = {R2}{OHM}$ and "
             f"$R_3 = {R3}{OHM}$, all across a ${num(V)}{U('V')}$ battery. Find (a) the equivalent resistance, "
             "(b) the current through $R_1$, (c) the current through $R_2$.",
             f"(a) ${ctx.fmt(Req)}{OHM}$ (b) ${ctx.fmt(I)}{U('A')}$ (c) ${ctx.fmt(I * Rp / R2)}{U('A')}$",
             rf"$R_{{23}} = {ctx.fmt(Rp)}\,\Omega$; $V_{{23}} = I R_{{23}}$; $I_2 = V_{{23}}/R_2$",
             {"V": V, "R1": R1, "R2": R2, "R3": R3}, {"Req": Req, "I": I, "I2": I * Rp / R2},
             figure=draw.combo_circuit(f"R₁ = {R1} Ω", f"R₂ = {R2} Ω", f"R₃ = {R3} Ω", f"{num(V)} V"))


# ======================================================== Electrostatics

topic("electrostatics", "physics", "Electricity", "Electrostatics",
      "Coulomb's law and electric field of point charges.", courses=['conceptual'])


@variant("electrostatics", 1, "Coulomb's law")
@variant("electrostatics", 2, "Coulomb's law")
def _coulomb(ctx: Ctx) -> Problem:
    q1, q2 = step(ctx.rng, 1, 9, 0.5), step(ctx.rng, 1, 9, 0.5)
    r = step(ctx.rng, 0.05, 2, 0.05)
    F = K_E * q1 * q2 * 1e-12 / r**2
    return P(f"Two point charges of ${num(q1)}{U('\\mu C')}$ and ${num(q2)}{U('\\mu C')}$ are "
             f"${num(r)}{U('m')}$ apart. Find the magnitude of the force between them.",
             f"$F = {ctx.fmt(F)}{U('N')}$", r"$F = k\frac{q_1 q_2}{r^2}$, $k = 8.99\times10^9$",
             {"q1": q1, "q2": q2, "r": r}, {"F": F})


@variant("electrostatics", 3, "Electric field")
def _field(ctx: Ctx) -> Problem:
    q1, q2 = ctx.rng.sample(range(1, 10), 2)  # distinct, so the fields don't cancel exactly
    d = step(ctx.rng, 0.2, 1, 0.1)
    E = K_E * abs(q1 - q2) * 1e-6 / (d / 2) ** 2
    return P(f"Positive charges ${q1}{U('\\mu C')}$ and ${q2}{U('\\mu C')}$ are ${num(d)}{U('m')}$ apart. "
             "Find the magnitude of the electric field at the midpoint between them.",
             f"$E = {ctx.fmt(E)}{U('N/C')}$",
             r"$E = k\frac{|q_1 - q_2|}{(d/2)^2}$ (the two fields point in opposite directions)",
             {"q1": q1, "q2": q2, "d": d}, {"E": E})


# ======================================================== Waves

topic("waves", "physics", "Waves & sound", "Waves & sound",
      "Wave speed, period, echoes and standing waves on strings.", courses=['conceptual'])

# description, speed range (lo, hi, step), frequency range (lo, hi, step)
WAVES = [("a sound wave in air", (343, 343, 1), (100, 2000, 10)),
         ("a sound wave in water", (1480, 1480, 1), (100, 2000, 10)),
         ("a wave on a guitar string", (150, 400, 10), (80, 1000, 1)),
         ("an ocean wave", (2, 12, 0.5), (0.05, 0.3, 0.01)),
         ("a wave on a stretched rope", (1, 6, 0.5), (0.5, 4, 0.5))]


@variant("waves", 1, "Wave speed")
def _wave_speed(ctx: Ctx) -> Problem:
    name, vr, fr = pick(ctx, WAVES)
    v, f = step(ctx.rng, *vr), step(ctx.rng, *fr)
    lam = r3(v / f)
    return P(f"For {name}, the frequency is ${num(f)}{U('Hz')}$ and the wavelength is ${num(lam)}{U('m')}$. "
             "Find the wave speed and the period.",
             f"$v = {ctx.fmt(f * lam)}{U('m/s')}$, $T = {ctx.fmt(1 / f)}{U('s')}$",
             r"$v = f\lambda$, $T = 1/f$", {"f": f, "lam": lam}, {"v": f * lam, "T": 1 / f})


# description (time placeholder {t}), speed, divide by 2 for a round trip, time range, what's asked
ECHOES = [("You shout toward a cliff and hear the echo {t} later.", 343, True, (0.3, 4, 0.1),
           "How far away is the cliff?"),
          ("A ship's sonar pulse returns from the sea floor {t} after it is sent.", 1480, True, (0.1, 4, 0.05),
           "How deep is the water?"),
          ("You see a lightning flash and hear the thunder {t} later.", 343, False, (1, 15, 0.5),
           "How far away was the lightning strike?"),
          ("A bat's chirp echoes off a moth and returns {t} after it is emitted.", 343, True, (0.005, 0.1, 0.005),
           "How far away is the moth?")]


@variant("waves", 2, "Echoes")
def _wave_echo(ctx: Ctx) -> Problem:
    text, v, there_and_back, tr, ask = pick(ctx, ECHOES)
    t = step(ctx.rng, *tr)
    medium = "air" if v == 343 else "seawater"
    d = v * t / 2 if there_and_back else v * t
    return P(text.replace("{t}", f"${num(t)}{U('s')}$") + f" Sound travels at ${v}{U('m/s')}$ in {medium}. {ask}",
             f"$d = {ctx.fmt(d)}{U('m')}$",
             r"$d = vt/2$ (the sound travels there and back)" if there_and_back else r"$d = vt$ (light arrives almost instantly)",
             {"t": t, "v": v}, {"d": d})


@variant("waves", 3, "Standing waves")
def _string_harmonic(ctx: Ctx) -> Problem:
    L_, v, n = step(ctx.rng, 0.3, 1.5, 0.05), step(ctx.rng, 100, 500, 10), ctx.rng.randint(1, 4)
    ords = {1: "fundamental", 2: "second harmonic", 3: "third harmonic", 4: "fourth harmonic"}
    return P(f"A string ${num(L_)}{U('m')}$ long, fixed at both ends, carries waves at ${num(v)}{U('m/s')}$. "
             f"Find the frequency and wavelength of the {ords[n]}.",
             f"$f_{n} = {ctx.fmt(n * v / (2 * L_))}{U('Hz')}$, $\\lambda_{n} = {ctx.fmt(2 * L_ / n)}{U('m')}$",
             r"$\lambda_n = 2L/n$, $f_n = nv/2L$", {"L": L_, "v": v, "n": n},
             {"f": n * v / (2 * L_), "lam": 2 * L_ / n})


# ======================================================== Optics

topic("optics", "physics", "Light & optics", "Optics",
      "Snell's law, thin lenses and magnification.", courses=['conceptual'], figures=True)

MEDIA = [("air", 1.00), ("water", 1.33), ("ice", 1.31), ("ethanol", 1.36), ("glycerin", 1.47),
         ("acrylic", 1.49), ("crown glass", 1.52), ("flint glass", 1.66), ("cubic zirconia", 2.15),
         ("diamond", 2.42)]


@variant("optics", 1, "Snell's law")
@variant("optics", 2, "Snell's law")
def _snell(ctx: Ctx) -> Problem:
    (m1, n1), (m2, n2) = sorted(ctx.rng.sample(MEDIA, 2), key=lambda m: m[1])  # slow -> fast: no TIR
    th1 = step(ctx.rng, 10, 70, 5)
    th2 = math.degrees(math.asin(n1 * math.sin(math.radians(th1)) / n2))
    return P(f"Light passes from {m1} ($n = {n1:.2f}$) into {m2} ($n = {n2:.2f}$) at an angle of incidence "
             f"of ${num(th1)}^\\circ$. Find the angle of refraction.",
             f"$\\theta_2 = {ctx.fmt(th2)}^\\circ$", r"$n_1 \sin\theta_1 = n_2 \sin\theta_2$",
             {"n1": n1, "n2": n2, "theta1": th1}, {"theta2": th2},
             figure=draw.refraction(th1, f"{num(th1)}°", m1, m2))


@variant("optics", 3, "Thin lenses")
def _lens(ctx: Ctx) -> Problem:
    f = step(ctx.rng, 5, 30, 1)
    do = step(ctx.rng, math.ceil(f * 1.2), f * 4, 1)
    di = 1 / (1 / f - 1 / do)
    m = -di / do
    return P(f"An object is ${num(do)}{U('cm')}$ from a converging lens of focal length ${num(f)}{U('cm')}$. "
             "Find the image distance, the magnification, and describe the image.",
             f"$d_i = {ctx.fmt(di)}{U('cm')}$, $m = {ctx.fmt(m)}$; real, inverted",
             r"$\frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}$, $m = -d_i/d_o$",
             {"f": f, "do": do}, {"di": di, "m": m},
             figure=draw.lens_diagram(f, do, f"f = {num(f)} cm", f"{num(do)} cm"))


# ======================================================== Thermal

topic("thermal", "physics", "Heat", "Heat & gases",
      "Specific heat, latent heat and the ideal gas law.", courses=['conceptual'])

SPECIFIC_HEAT = [("water", 4186), ("aluminum", 900), ("copper", 385), ("iron", 450), ("glass", 840)]


@variant("thermal", 1, "Specific heat")
def _heat_specific(ctx: Ctx) -> Problem:
    name, c = pick(ctx, SPECIFIC_HEAT)
    m, dT = step(ctx.rng, 0.1, 5, 0.1), step(ctx.rng, 5, 80, 1)
    return P(f"How much heat is needed to raise ${num(m)}{U('kg')}$ of {name} "
             f"($c = {c}{U('J/(kg\\cdot ^\\circ C)')}$) by ${num(dT)}^\\circ\\mathrm{{C}}$?",
             f"$Q = {ctx.fmt(m * c * dT)}{U('J')}$", r"$Q = mc\Delta T$", {"m": m, "c": c, "dT": dT},
             {"Q": m * c * dT})


@variant("thermal", 2, "Phase change")
def _heat_melt(ctx: Ctx) -> Problem:
    m, T0 = step(ctx.rng, 0.1, 2, 0.1), step(ctx.rng, -30, -5, 1)
    Q = m * 2090 * (-T0) + m * 3.34e5
    return P(f"How much heat is needed to turn ${num(m)}{U('kg')}$ of ice at ${num(T0)}^\\circ\\mathrm{{C}}$ into "
             f"water at $0^\\circ\\mathrm{{C}}$? ($c_{{ice}} = 2090{U('J/(kg\\cdot ^\\circ C)')}$, "
             f"$L_f = 3.34\\times10^5{U('J/kg')}$)",
             f"$Q = {ctx.fmt(Q)}{U('J')}$", r"$Q = mc_{ice}\Delta T + mL_f$", {"m": m, "T0": T0}, {"Q": Q})


@variant("thermal", 3, "Ideal gas law")
def _gas(ctx: Ctx) -> Problem:
    n, T, V = step(ctx.rng, 0.5, 5, 0.5), step(ctx.rng, 250, 450, 5), step(ctx.rng, 5, 50, 1)
    P_ = n * 8.314 * T / (V / 1000)
    return P(f"${num(n)}{U('mol')}$ of an ideal gas at ${num(T)}{U('K')}$ occupies ${num(V)}{U('L')}$. "
             "Find its pressure in pascals and in atmospheres.",
             f"$P = {ctx.fmt(P_)}{U('Pa')} = {ctx.fmt(P_ / 101325)}{U('atm')}$",
             r"$P = nRT/V$ with $V$ in $\mathrm{m^3}$, $R = 8.314$", {"n": n, "T": T, "V": V},
             {"P": P_, "atm": P_ / 101325})


# ======================================================== Fluids

topic("fluids", "physics", "Fluids", "Fluids & pressure",
      "Density, hydrostatic pressure and buoyancy.", courses=['conceptual', 'ap1'], figures=True)

# density in g/cm^3
MATERIALS = [("aluminum", 2.70), ("iron", 7.87), ("copper", 8.96), ("lead", 11.3), ("gold", 19.3),
             ("silver", 10.5), ("ice", 0.917), ("oak", 0.75), ("cork", 0.24), ("granite", 2.75), ("glass", 2.5)]


@variant("fluids", 1, "Density")
def _density(ctx: Ctx) -> Problem:
    name, rho = pick(ctx, MATERIALS)
    V = step(ctx.rng, 5, 500, 5)
    if ctx.nice:  # textbook-rounded density (iron 7.9, copper 9.0) and an exact mass
        rho = float(f"{rho:.2g}")
        m = round(rho * V, 6)
    else:
        m = r3(rho * V)
    return P(f"A sample of {name} has a mass of ${num(m)}{U('g')}$ and a volume of ${num(V)}{U('cm^3')}$. "
             "Find its density.",
             f"$\\rho = {ctx.fmt(m / V)}{U('g/cm^3')}$", r"$\rho = m/V$", {"m": m, "V": V}, {"rho": m / V})


WATERS = [("a freshwater lake", 1000), ("the ocean", 1025)]


@variant("fluids", 2, "Pressure at depth")
def _pressure_depth(ctx: Ctx) -> Problem:
    where, rho = pick(ctx, WATERS)
    h = step(ctx.rng, 1, 100, 0.5)
    P_ = 101300 + rho * ctx.g * h
    return P(f"Find the absolute pressure ${num(h)}{U('m')}$ below the surface of {where} "
             f"($\\rho = {rho}{U('kg/m^3')}$, $P_0 = 1.013\\times10^5{U('Pa')}$)." + ctx.g_note(),
             f"$P = {ctx.fmt(P_)}{U('Pa')}$", r"$P = P_0 + \rho g h$", {"h": h, "rho": rho}, {"P": P_})


@variant("fluids", 3, "Buoyancy")
def _buoyancy(ctx: Ctx) -> Problem:
    V, rho = step(ctx.rng, 0.001, 0.02, 0.001), step(ctx.rng, 2000, 8000, 100)
    W = rho * V * ctx.g
    Fb = 1000 * V * ctx.g
    return P(f"A ${num(V)}{U('m^3')}$ block of density ${num(rho)}{U('kg/m^3')}$ is fully submerged in water. "
             "Find (a) the buoyant force and (b) its apparent weight." + ctx.g_note(),
             f"(a) ${ctx.fmt(Fb)}{U('N')}$ (b) ${ctx.fmt(W - Fb)}{U('N')}$",
             r"$F_b = \rho_{water} V g$; apparent weight $= mg - F_b$", {"V": V, "rho": rho},
             {"Fb": Fb, "Wapp": W - Fb}, figure=draw.submerged_block(f"ρ = {num(rho)} kg/m³"))
