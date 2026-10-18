"""AP Physics 1 rotation and oscillations (and the conceptual-physics parts of them): torque and
static equilibrium, rotational kinematics and dynamics, rotational energy and angular momentum,
springs and pendulums.

Same conventions as physics_gen: realistic values, ``ctx.g``, answers via ``ctx.fmt``, givens and
answers in ``facts`` for the tests, and AP-style worked solutions.
"""

from __future__ import annotations

import math

from . import drawings as draw
from .core import Ctx, Problem, U, is_nice, num, sig, step, steps, topic, variant
from .physics_gen import P, _angle, _trig_tex, known, pick, r3

NM, RADS, RADS2, KGM2 = "N\\cdot m", "rad/s", "rad/s^2", "kg\\cdot m^2"

# Moments of inertia as I = beta * M R^2: name, beta, formula
SHAPES = {"disk": ("uniform solid disk", 0.5, "\\tfrac{1}{2}MR^2"),
          "cylinder": ("solid cylinder", 0.5, "\\tfrac{1}{2}MR^2"),
          "hoop": ("thin hoop", 1.0, "MR^2"),
          "sphere": ("solid sphere", 0.4, "\\tfrac{2}{5}MR^2"),
          "shell": ("hollow sphere", 2 / 3, "\\tfrac{2}{3}MR^2")}


def nice_draw(ctx: Ctx, make, tries: int = 80):
    """Call ``make()`` until every number it returns is simple (in whole-number mode); else just once."""
    vals = make()
    for _ in range(tries if ctx.nice else 0):
        if all(is_nice(v) for v in vals):
            break
        vals = make()
    return vals


# ======================================================================== Torque

topic("torque", "physics", "Torque & rotational dynamics", "Torque & equilibrium",
      "Torque, balancing a seesaw, and static equilibrium of beams.", courses=["conceptual", "ap1"],
      figures=True)

# who, where the force acts, lever-arm range (m), force range (N)
WRENCHES = [("A mechanic pulls on a wrench", "the bolt", (0.15, 0.45, 0.05), (20, 200, 5)),
            ("A student pushes on a door", "the hinges", (0.7, 0.9, 0.05), (5, 40, 1)),
            ("A cyclist pushes down on a pedal", "the crank axle", (0.17, 0.17, 1), (100, 600, 10)),
            ("A plumber turns a pipe wrench", "the pipe", (0.25, 0.6, 0.05), (50, 300, 10))]


@variant("torque", 1, "Torque")
def _torque_perp(ctx: Ctx) -> Problem:
    who, pivot, rr, fr = pick(ctx, WRENCHES)
    r, F = nice_draw(ctx, lambda: (step(ctx.rng, *rr), step(ctx.rng, fr[0], fr[1], fr[2] * (4 if ctx.nice else 1))))
    tau = r * F
    return P(f"{who} ${num(r)}{U('m')}$ from {pivot}, applying a ${num(F)}{U('N')}$ force perpendicular to the "
             "lever arm. What torque does the force produce?",
             f"$\\tau = {ctx.fmt(tau)}{U(NM)}$",
             steps(known(("r", r, "m"), ("F", F, "N")), "The force is perpendicular to the lever arm: $\\tau = rF$",
                   f"$\\tau = ({num(r)})({num(F)}) = {ctx.fmt(tau)}{U(NM)}$"),
             {"r": r, "F": F}, {"tau": tau})


@variant("torque", 2, "Torque")
def _torque_angle(ctx: Ctx) -> Problem:
    who, pivot, rr, fr = pick(ctx, WRENCHES[:1] + WRENCHES[3:])
    th, s_, _, note = _angle(ctx, [30, 40, 45, 50, 60, 70])
    r, F = step(ctx.rng, *rr), step(ctx.rng, fr[0], fr[1], fr[2] * (4 if ctx.nice else 1))
    tau = r * F * s_
    given = {"r": r, "F": F, "theta": th, **({"sin": s_} if note else {})}
    return P(f"{who} ${num(r)}{U('m')}$ from {pivot}, applying a ${num(F)}{U('N')}$ force at ${th}^\\circ$ to the "
             "handle. What torque does the force produce?" + note,
             f"$\\tau = {ctx.fmt(tau)}{U(NM)}$",
             steps(known(("r", r, "m"), ("F", F, "N"), ("\\theta", f"{th}^\\circ", "")),
                   "Only the force component perpendicular to the lever arm makes torque: $\\tau = rF\\sin\\theta$",
                   f"$\\tau = ({num(r)})({num(F)}){_trig_tex('sin', th, s_, note)} = {ctx.fmt(tau)}{U(NM)}$"),
             given, {"tau": tau})


@variant("torque", 1, "Balancing a seesaw")
def _seesaw(ctx: Ctx) -> Problem:
    def make():
        m1, m2 = step(ctx.rng, 20, 60, 5 if ctx.nice else 1), step(ctx.rng, 20, 60, 5 if ctx.nice else 1)
        d1 = step(ctx.rng, 0.8, 2.4, 0.2 if ctx.nice else 0.1)
        return m1, m2, d1, m1 * d1 / m2
    while True:
        m1, m2, d1, d2 = nice_draw(ctx, make)
        if m1 != m2 and 0.6 <= d2 <= 2.5:
            break
    return P(f"A ${num(m1)}{U('kg')}$ child sits ${num(d1)}{U('m')}$ from the pivot of a seesaw. How far from the pivot "
             f"must a ${num(m2)}{U('kg')}$ child sit on the other side to balance it?",
             f"$d_2 = {ctx.fmt(d2)}{U('m')}$",
             steps(known(("m_1", m1, "kg"), ("d_1", d1, "m"), ("m_2", m2, "kg")),
                   "Balanced: the torques about the pivot are equal, $m_1 g d_1 = m_2 g d_2$ ($g$ cancels)",
                   f"$d_2 = \\frac{{m_1 d_1}}{{m_2}} = \\frac{{({num(m1)})({num(d1)})}}{{{num(m2)}}} = {ctx.fmt(d2)}{U('m')}$"),
             {"m1": m1, "d1": d1, "m2": m2}, {"d2": d2},
             figure=draw.beam(6, [3], [(3 - d1, f"{num(m1)} kg", ""), (3 + d2, f"{num(m2)} kg", "")],
                              dims=[(3 - d1, 3, f"{num(d1)} m"), (3, 3 + d2, "x")]))


# What rests on the supports: plank description, mass range, length range, load description, load mass range
PLANKS = [("A <M> uniform plank <L> long rests on two sawhorses, one at each end. A <m> painter stands <x> from the "
           "left end.", (10, 40, 2), (3, 6, 0.5), (50, 90, 2)),
          ("A <M> uniform shelf board <L> long is held up by a bracket at each end. A <m> box of books sits <x> "
           "from the left end.", (2, 8, 0.5), (1, 2, 0.1), (5, 25, 1)),
          ("A <M> uniform footbridge <L> long is supported at each end. A <m> jogger stops <x> from the left "
           "end.", (300, 900, 50), (8, 20, 1), (50, 90, 2))]


@variant("torque", 3, "Static equilibrium")
def _beam_supports(ctx: Ctx) -> Problem:
    text, mr, lr, wr = pick(ctx, PLANKS)

    def make():
        M, L, m = step(ctx.rng, *mr), step(ctx.rng, *lr), step(ctx.rng, *wr)
        x = step(ctx.rng, L * 0.1, L * 0.45, lr[2] / 2) if ctx.rng.random() < 0.5 else \
            step(ctx.rng, L * 0.55, L * 0.9, lr[2] / 2)
        FR = ctx.g * (M * L / 2 + m * x) / L
        return M, L, m, x, FR, (M + m) * ctx.g - FR
    M, L, m, x, FR, FL = nice_draw(ctx, make)
    q = (text.replace("<M>", f"${num(M)}{U('kg')}$").replace("<L>", f"${num(L)}{U('m')}$")
         .replace("<m>", f"${num(m)}{U('kg')}$").replace("<x>", f"${num(x)}{U('m')}$"))
    g = num(ctx.g)
    return P(q + " Find the upward force from each support." + ctx.g_note(),
             f"Left: ${ctx.fmt(FL)}{U('N')}$; right: ${ctx.fmt(FR)}{U('N')}$",
             steps(known(("M", M, "kg"), ("L", L, "m"), ("m", m, "kg"), ("x", x, "m")),
                   "Take torques about the left end (so $F_L$ makes none). The beam's weight acts at its center:",
                   "$F_R L = Mg\\frac{L}{2} + mgx$",
                   f"$F_R = \\frac{{({num(M)})({g})({num(L / 2)}) + ({num(m)})({g})({num(x)})}}{{{num(L)}}} = "
                   f"{ctx.fmt(FR)}{U('N')}$",
                   f"Forces balance: $F_L = (M + m)g - F_R = ({num(M + m)})({g}) - {ctx.fmt(FR)} = {ctx.fmt(FL)}{U('N')}$"),
             {"M": M, "L": L, "m": m, "x": x}, {"FL": FL, "FR": FR},
             figure=draw.beam(L, [0, L], [(x, f"{num(m)} kg", "")], dims=[(0, x, f"{num(x)} m"), (0, L, f"{num(L)} m")]))


# ======================================================================== Rotational kinematics & dynamics

topic("rotation", "physics", "Torque & rotational dynamics", "Rotational kinematics & dynamics",
      "Angular velocity and acceleration, and Newton's second law for rotation, τ = Iα.", courses=["ap1"],
      figures=True)

# object, radius range (m), rpm range
SPINNERS = [("A ceiling fan blade", "its tip", (0.5, 0.7, 0.05), (60, 240, 10)),
            ("A washing machine drum", "its rim", (0.23, 0.28, 0.01), (400, 1200, 50)),
            ("A merry-go-round", "its edge", (2, 4, 0.5), (4, 12, 1)),
            ("A bicycle wheel", "its rim", (0.33, 0.35, 0.01), (60, 300, 10)),
            ("A record on a turntable", "its outer edge", (0.15, 0.15, 1), [45, 78])]


@variant("rotation", 1, "Angular velocity")
def _ang_velocity(ctx: Ctx) -> Problem:
    obj, where, rr, nr = pick(ctx, SPINNERS)
    r, rpm = step(ctx.rng, *rr), ctx.rng.choice(nr) if isinstance(nr, list) else step(ctx.rng, *nr)
    w = rpm * 2 * math.pi / 60
    v = w * r
    return P(f"{obj} turns at ${num(rpm)}{U('rev/min')}$. Find (a) its angular velocity in rad/s and (b) the speed of "
             f"{where}, ${num(r)}{U('m')}$ from the axis.",
             f"(a) $\\omega = {ctx.fmt(w)}{U(RADS)}$ (b) $v = {ctx.fmt(v)}{U('m/s')}$",
             steps(known(("f", rpm, "rev/min"), ("r", r, "m")),
                   f"(a) $\\omega = {num(rpm)}\\,\\frac{{\\text{{rev}}}}{{\\text{{min}}}} \\times \\frac{{2\\pi\\text{{ rad}}}}"
                   f"{{1\\text{{ rev}}}} \\times \\frac{{1\\text{{ min}}}}{{60\\text{{ s}}}} = {ctx.fmt(w)}{U(RADS)}$",
                   f"(b) $v = \\omega r = ({ctx.fmt(w)})({num(r)}) = {ctx.fmt(v)}{U('m/s')}$"),
             {"rpm": rpm, "r": r}, {"omega": w, "v": v})


# object, top angular speed (rad/s) range, time range (s)
SPIN_UPS = [("A potter's wheel", (4, 12, 1), (2, 8, 1)), ("A car's wheel", (20, 80, 5), (4, 12, 1)),
            ("An electric drill bit", (100, 300, 10), (0.5, 2, 0.5)), ("A spinning top", (20, 60, 5), (1, 4, 0.5)),
            ("A wind turbine rotor", (1, 3, 0.5), (10, 40, 5))]


@variant("rotation", 2, "Angular acceleration")
def _ang_accel(ctx: Ctx) -> Problem:
    obj, wr, tr = pick(ctx, SPIN_UPS)

    def make():
        w, t = step(ctx.rng, *wr), step(ctx.rng, *tr)
        w0 = 0.0 if ctx.rng.random() < 0.5 else step(ctx.rng, wr[0] * 0.2, w * 0.6, wr[2])
        return w0, w, t, (w - w0) / t, (w0 + w) / 2 * t
    w0, w, t, alpha, theta = nice_draw(ctx, make)
    start = "from rest" if w0 == 0 else f"from ${num(w0)}{U(RADS)}$"
    return P(f"{obj} speeds up uniformly {start} to ${num(w)}{U(RADS)}$ in ${num(t)}{U('s')}$. Find (a) its angular "
             "acceleration and (b) the angle it turns through in that time, in radians.",
             f"(a) $\\alpha = {ctx.fmt(alpha)}{U(RADS2)}$ (b) $\\Delta\\theta = {ctx.fmt(theta)}{U('rad')}$",
             steps(known(("\\omega_0", w0, RADS), ("\\omega", w, RADS), ("t", t, "s")),
                   f"(a) $\\alpha = \\frac{{\\omega - \\omega_0}}{{t}} = \\frac{{{num(w)} - {num(w0)}}}{{{num(t)}}} = "
                   f"{ctx.fmt(alpha)}{U(RADS2)}$",
                   f"(b) $\\Delta\\theta = \\frac{{\\omega_0 + \\omega}}{{2}}t = \\frac{{{num(w0)} + {num(w)}}}{{2}}({num(t)}) = "
                   f"{ctx.fmt(theta)}{U('rad')}$"),
             {"w0": w0, "w": w, "t": t}, {"alpha": alpha, "theta": theta})


# object, mass range (kg), radius range (m), force range (N)
WHEELS = [("grinding wheel", (1, 5, 0.5), (0.1, 0.2, 0.05), (5, 40, 1)),
          ("flywheel", (10, 60, 5), (0.2, 0.5, 0.05), (20, 200, 10)),
          ("playground merry-go-round", (100, 400, 20), (1.5, 2.5, 0.5), (50, 250, 10)),
          ("potter's wheel", (5, 20, 1), (0.15, 0.3, 0.05), (5, 50, 1))]


@variant("rotation", 2, "Torque and angular acceleration")
def _torque_alpha(ctx: Ctx) -> Problem:
    obj, mr, rr, fr = pick(ctx, WHEELS)

    def make():
        M, R, F, t = step(ctx.rng, *mr), step(ctx.rng, *rr), step(ctx.rng, *fr), step(ctx.rng, 2, 8, 1)
        alpha = F * R / (0.5 * M * R * R)
        return M, R, F, t, alpha, alpha * t
    M, R, F, t, alpha, w = nice_draw(ctx, make)
    I = 0.5 * M * R * R
    return P(f"A ${num(M)}{U('kg')}$ {obj} of radius ${num(R)}{U('m')}$ (a uniform solid disk, $I = \\tfrac{{1}}{{2}}MR^2$) "
             f"starts from rest. A constant ${num(F)}{U('N')}$ force is applied tangent to its rim. Find (a) its "
             f"angular acceleration and (b) its angular velocity after ${num(t)}{U('s')}$.",
             f"(a) $\\alpha = {ctx.fmt(alpha)}{U(RADS2)}$ (b) $\\omega = {ctx.fmt(w)}{U(RADS)}$",
             steps(known(("M", M, "kg"), ("R", R, "m"), ("F", F, "N"), ("t", t, "s")),
                   f"$I = \\tfrac{{1}}{{2}}MR^2 = \\tfrac{{1}}{{2}}({num(M)})({num(R)})^2 = {ctx.fmt(I)}{U(KGM2)}$",
                   f"$\\tau = FR = ({num(F)})({num(R)}) = {ctx.fmt(F * R)}{U(NM)}$",
                   f"(a) $\\alpha = \\frac{{\\tau}}{{I}} = \\frac{{{ctx.fmt(F * R)}}}{{{ctx.fmt(I)}}} = {ctx.fmt(alpha)}{U(RADS2)}$",
                   f"(b) $\\omega = \\omega_0 + \\alpha t = 0 + ({ctx.fmt(alpha)})({num(t)}) = {ctx.fmt(w)}{U(RADS)}$"),
             {"M": M, "R": R, "F": F, "t": t}, {"alpha": alpha, "w": w})


@variant("rotation", 3, "Pulleys with mass")
def _pulley_mass(ctx: Ctx) -> Problem:
    what = pick(ctx, ["bucket", "block", "lantern"])

    def make():
        m, M = step(ctx.rng, 1, 12, 1 if ctx.nice else 0.5), step(ctx.rng, 2, 20, 2 if ctx.nice else 0.5)
        R = ctx.rng.choice([0.1, 0.2, 0.25, 0.5] if ctx.nice else [0.08, 0.1, 0.12, 0.15, 0.2, 0.25, 0.3])
        a = m * ctx.g / (m + M / 2)
        return m, M, R, a, m * (ctx.g - a), a / R
    m, M, R, a, T, alpha = nice_draw(ctx, make)
    g = num(ctx.g)
    return P(f"A ${num(m)}{U('kg')}$ {what} hangs from a light rope wrapped around a pulley: a ${num(M)}{U('kg')}$ uniform "
             f"solid disk of radius ${num(R)}{U('m')}$ ($I = \\tfrac{{1}}{{2}}MR^2$) that turns without friction. The "
             f"{what} is released from rest. Find (a) its acceleration, (b) the tension in the rope and (c) the "
             "pulley's angular acceleration." + ctx.g_note(),
             f"(a) $a = {ctx.fmt(a)}{U('m/s^2')}$ (b) $T = {ctx.fmt(T)}{U('N')}$ (c) $\\alpha = {ctx.fmt(alpha)}{U(RADS2)}$",
             steps(known(("m", m, "kg"), ("M", M, "kg"), ("R", R, "m"), ("g", ctx.g, "m/s^2")),
                   f"{what.capitalize()}: $mg - T = ma$",
                   "Pulley: $TR = I\\alpha = \\tfrac{1}{2}MR^2 \\cdot \\frac{a}{R}$, so $T = \\tfrac{1}{2}Ma$",
                   f"Add the equations: $mg = (m + \\tfrac{{1}}{{2}}M)a$, so "
                   f"(a) $a = \\frac{{({num(m)})({g})}}{{{num(m)} + \\tfrac{{1}}{{2}}({num(M)})}} = {ctx.fmt(a)}{U('m/s^2')}$",
                   f"(b) $T = \\tfrac{{1}}{{2}}Ma = \\tfrac{{1}}{{2}}({num(M)})({ctx.fmt(a)}) = {ctx.fmt(T)}{U('N')}$",
                   f"(c) $\\alpha = \\frac{{a}}{{R}} = \\frac{{{ctx.fmt(a)}}}{{{num(R)}}} = {ctx.fmt(alpha)}{U(RADS2)}$"),
             {"m": m, "M": M, "R": R}, {"a": a, "T": T, "alpha": alpha},
             figure=draw.pulley_mass(f"{num(M)} kg", f"{num(m)} kg"))


# ======================================================================== Rotational energy & angular momentum

topic("rot_energy", "physics", "Rotational energy & momentum", "Rotational energy & angular momentum",
      "Rotational kinetic energy, conservation of angular momentum, and rolling.", courses=["ap1"])

# object, shape, mass range, radius range, angular speed range (rad/s)
ROTORS = [("flywheel", "disk", (5, 50, 5), (0.1, 0.5, 0.05), (20, 300, 10)),
          ("merry-go-round", "disk", (100, 400, 20), (1.5, 3, 0.5), (0.5, 3, 0.5)),
          ("bicycle wheel", "hoop", (1, 2, 0.1), (0.33, 0.35, 0.01), (5, 40, 1)),
          ("potter's wheel", "disk", (5, 20, 1), (0.15, 0.3, 0.05), (3, 15, 1)),
          ("bowling ball", "sphere", (5, 7, 0.5), (0.11, 0.11, 1), (10, 60, 5))]


@variant("rot_energy", 1, "Rotational kinetic energy")
def _rot_ke(ctx: Ctx) -> Problem:
    obj, shape, mr, rr, wr = pick(ctx, ROTORS)
    name, beta, formula = SHAPES[shape]

    def make():
        M, R, w = step(ctx.rng, *mr), step(ctx.rng, *rr), step(ctx.rng, *wr)
        return M, R, w, beta * M * R * R, 0.5 * beta * M * R * R * w * w
    M, R, w, I, KE = nice_draw(ctx, make)
    return P(f"A ${num(M)}{U('kg')}$ {obj} of radius ${num(R)}{U('m')}$ spins at ${num(w)}{U(RADS)}$. Treating it as a "
             f"{name} ($I = {formula}$), find (a) its moment of inertia and (b) its rotational kinetic energy.",
             f"(a) $I = {ctx.fmt(I)}{U(KGM2)}$ (b) $K = {ctx.fmt(KE)}{U('J')}$",
             steps(known(("M", M, "kg"), ("R", R, "m"), ("\\omega", w, RADS)),
                   f"(a) $I = {formula} = {formula.replace('MR^2', f'({num(M)})({num(R)})^2')} = {ctx.fmt(I)}{U(KGM2)}$",
                   f"(b) $K = \\tfrac{{1}}{{2}}I\\omega^2 = \\tfrac{{1}}{{2}}({ctx.fmt(I)})({num(w)})^2 = {ctx.fmt(KE)}{U('J')}$"),
             {"M": M, "R": R, "w": w}, {"I_rot": I, "KE": KE}, inertia=beta)


@variant("rot_energy", 2, "Conservation of angular momentum")
def _skater(ctx: Ctx) -> Problem:
    who = pick(ctx, ["A figure skater", "A diver", "A student on a spinning stool holding dumbbells"])

    def make():
        I1, I2 = step(ctx.rng, 2.5, 6, 0.5), step(ctx.rng, 0.8, 2.4, 0.2 if ctx.nice else 0.1)
        w1 = step(ctx.rng, 1, 6, 1 if ctx.nice else 0.5)
        return I1, I2, w1, I1 * w1 / I2
    I1, I2, w1, w2 = nice_draw(ctx, make)
    return P(f"{who} spins at ${num(w1)}{U(RADS)}$ with a moment of inertia of ${num(I1)}{U(KGM2)}$. Pulling in their "
             f"arms reduces their moment of inertia to ${num(I2)}{U(KGM2)}$. Find their new angular velocity.",
             f"$\\omega_2 = {ctx.fmt(w2)}{U(RADS)}$",
             steps(known(("I_1", I1, KGM2), ("\\omega_1", w1, RADS), ("I_2", I2, KGM2)),
                   "No external torque, so angular momentum is conserved: $I_1\\omega_1 = I_2\\omega_2$",
                   f"$\\omega_2 = \\frac{{I_1\\omega_1}}{{I_2}} = \\frac{{({num(I1)})({num(w1)})}}{{{num(I2)}}} = "
                   f"{ctx.fmt(w2)}{U(RADS)}$"),
             {"I1": I1, "w1": w1, "I2": I2}, {"w2": w2})


@variant("rot_energy", 2, "Conservation of angular momentum")
def _platform(ctx: Ctx) -> Problem:
    def make():
        M, R = step(ctx.rng, 100, 300, 20), step(ctx.rng, 1.5, 2.5, 0.5)
        m, w0 = step(ctx.rng, 20, 60, 5 if ctx.nice else 1), step(ctx.rng, 1, 4, 0.5)
        Id, Ic = 0.5 * M * R * R, m * R * R
        return M, R, m, w0, Id, Ic, Id * w0 / (Id + Ic)
    M, R, m, w0, Id, Ic, w = nice_draw(ctx, make)
    return P(f"A ${num(M)}{U('kg')}$ merry-go-round of radius ${num(R)}{U('m')}$ (a uniform solid disk, "
             f"$I = \\tfrac{{1}}{{2}}MR^2$) spins freely at ${num(w0)}{U(RADS)}$. A ${num(m)}{U('kg')}$ child steps "
             "straight onto its edge from the ground. Find the new angular velocity.",
             f"$\\omega = {ctx.fmt(w)}{U(RADS)}$",
             steps(known(("M", M, "kg"), ("R", R, "m"), ("\\omega_0", w0, RADS), ("m", m, "kg")),
                   f"Merry-go-round: $I_d = \\tfrac{{1}}{{2}}MR^2 = \\tfrac{{1}}{{2}}({num(M)})({num(R)})^2 = {ctx.fmt(Id)}{U(KGM2)}$",
                   f"Child at the edge: $I_c = mR^2 = ({num(m)})({num(R)})^2 = {ctx.fmt(Ic)}{U(KGM2)}$",
                   "Angular momentum is conserved: $I_d\\omega_0 = (I_d + I_c)\\omega$",
                   f"$\\omega = \\frac{{({ctx.fmt(Id)})({num(w0)})}}{{{ctx.fmt(Id)} + {ctx.fmt(Ic)}}} = {ctx.fmt(w)}{U(RADS)}$"),
             {"M": M, "R": R, "w0": w0, "m": m}, {"w": w})


# coefficient of (1/2)Mv^2 in K_rot when rolling, and 1 + that coefficient
_ROLL = {"sphere": ("\\tfrac{2}{5}\\cdot", "\\tfrac{7}{5}"), "cylinder": ("\\tfrac{1}{2}\\cdot", "\\tfrac{3}{2}"),
         "hoop": ("", "2"), "shell": ("\\tfrac{2}{3}\\cdot", "\\tfrac{5}{3}")}


@variant("rot_energy", 3, "Rolling")
def _rolling(ctx: Ctx) -> Problem:
    shape = pick(ctx, ["sphere", "cylinder", "hoop", "shell"])
    name, beta, formula = SHAPES[shape]
    if ctx.nice and ctx.g == 10:
        while True:
            v = step(ctx.rng, 1, 8, 1)
            h = round(v * v * (1 + beta) / (2 * ctx.g), 9)
            if is_nice(h) and 0.2 <= h <= 4:
                break
    else:
        h = step(ctx.rng, 0.3, 4, 0.1)
        v = math.sqrt(2 * ctx.g * h / (1 + beta))
    k, one_plus = _ROLL[shape]
    return P(f"A {name} ($I = {formula}$) starts from rest and rolls without slipping down a ramp "
             f"${num(h)}{U('m')}$ high. How fast is it moving at the bottom?" + ctx.g_note(),
             f"$v = {ctx.fmt(v)}{U('m/s')}$",
             steps(known(("h", h, "m"), ("g", ctx.g, "m/s^2")),
                   f"Rolling without slipping, $\\omega = \\frac{{v}}{{R}}$, so $K_{{rot}} = \\tfrac{{1}}{{2}}I\\omega^2 = "
                   f"{k}\\tfrac{{1}}{{2}}Mv^2$",
                   f"Energy is conserved: $Mgh = \\tfrac{{1}}{{2}}Mv^2 + {k}\\tfrac{{1}}{{2}}Mv^2 = "
                   f"{one_plus}\\cdot\\tfrac{{1}}{{2}}Mv^2$",
                   f"$v = \\sqrt{{\\frac{{2gh}}{{{one_plus}}}}} = \\sqrt{{\\frac{{2({num(ctx.g)})({num(h)})}}{{{one_plus}}}}} = "
                   f"{ctx.fmt(v)}{U('m/s')}$"),
             {"h": h}, {"v": v}, inertia=beta)


@variant("rot_energy", 3, "Rolling")
def _rolling_ke(ctx: Ctx) -> Problem:
    balls = [("bowling ball", 6, 0.11, (2, 9, 0.5)), ("solid rubber ball", 0.5, 0.05, (1, 8, 1)),
             *([] if ctx.nice else [("basketball", 0.62, 0.12, (2, 10, 0.5))])]
    obj, m, r, vr = pick(ctx, balls)
    name, beta, formula = SHAPES["shell" if obj == "basketball" else "sphere"]
    I = beta * m * r * r

    def make():
        v = step(ctx.rng, *vr)
        return v, 0.5 * m * v * v, 0.5 * I * (v / r) ** 2
    v, Kt, Kr = nice_draw(ctx, make)
    w = v / r
    return P(f"A ${num(m)}{U('kg')}$ {obj} of radius ${num(r)}{U('m')}$ (a {name}, $I = {formula}$) rolls without "
             f"slipping at ${num(v)}{U('m/s')}$. Find (a) its translational kinetic energy, (b) its rotational kinetic "
             "energy and (c) its total kinetic energy.",
             f"(a) ${ctx.fmt(Kt)}{U('J')}$ (b) ${ctx.fmt(Kr)}{U('J')}$ (c) ${ctx.fmt(Kt + Kr)}{U('J')}$",
             steps(known(("m", m, "kg"), ("R", r, "m"), ("v", v, "m/s")),
                   f"(a) $K_{{trans}} = \\tfrac{{1}}{{2}}mv^2 = \\tfrac{{1}}{{2}}({num(m)})({num(v)})^2 = {ctx.fmt(Kt)}{U('J')}$",
                   f"Rolling without slipping: $\\omega = \\frac{{v}}{{R}} = \\frac{{{num(v)}}}{{{num(r)}}} = {sig(w, 3)}{U(RADS)}$, "
                   f"and $I = {formula.replace('MR^2', f'({num(m)})({num(r)})^2')} = {sig(I, 3)}{U(KGM2)}$",
                   f"(b) $K_{{rot}} = \\tfrac{{1}}{{2}}I\\omega^2 = \\tfrac{{1}}{{2}}({sig(I, 3)})({sig(w, 3)})^2 = {ctx.fmt(Kr)}{U('J')}$",
                   f"(c) $K = {ctx.fmt(Kt)} + {ctx.fmt(Kr)} = {ctx.fmt(Kt + Kr)}{U('J')}$"),
             {"m": m, "r": r, "v": v}, {"Kt": Kt, "Kr": Kr, "K": Kt + Kr}, inertia=beta, what=obj)


# ======================================================================== Oscillations

topic("oscillations", "physics", "Oscillations", "Springs & pendulums",
      "Period and frequency, Hooke's law, pendulum and mass-spring periods, energy in simple harmonic motion.",
      courses=["conceptual", "ap1"], figures=True)

# what oscillates, count range, period range (s)
OSCILLATORS = [("A pendulum completes {N} full swings", (10, 30, 1), (0.8, 3, 0.1)),
               ("A mass on a spring bobs up and down {N} times", (10, 40, 1), (0.3, 2, 0.1)),
               ("A hummingbird's wings beat {N} times", (20, 60, 1), (0.015, 0.025, 0.001)),
               ("A guitar string vibrates {N} times", (100, 500, 10), (0.002, 0.01, 0.0005))]


@variant("oscillations", 1, "Period and frequency")
def _osc_period(ctx: Ctx) -> Problem:
    text, nr, tr = pick(ctx, OSCILLATORS)
    N, T = nice_draw(ctx, lambda: (step(ctx.rng, *nr), step(ctx.rng, *tr)))
    t = r3(N * T)
    T, f = t / N, N / t
    return P(f"{text.replace('{N}', f'${num(N)}$')} in ${num(t)}{U('s')}$. Find (a) the period and (b) the frequency.",
             f"(a) $T = {ctx.fmt(T)}{U('s')}$ (b) $f = {ctx.fmt(f)}{U('Hz')}$",
             steps(known(("N", N, ""), ("t", t, "s")),
                   f"(a) $T = \\frac{{t}}{{N}} = \\frac{{{num(t)}}}{{{num(N)}}} = {ctx.fmt(T)}{U('s')}$",
                   f"(b) $f = \\frac{{N}}{{t}} = \\frac{{{num(N)}}}{{{num(t)}}} = {ctx.fmt(f)}{U('Hz')}$ (or $f = \\frac{{1}}{{T}}$)"),
             {"N": N, "t": t}, {"T": T, "f": f})


@variant("oscillations", 1, "Hooke's law")
def _hooke(ctx: Ctx) -> Problem:
    def make():
        m, x = step(ctx.rng, 0.1, 2, 0.1 if ctx.nice else 0.05), step(ctx.rng, 2, 25, 1)
        return m, x, m * ctx.g / (x / 100)
    m, x, k = nice_draw(ctx, make, tries=200)
    return P(f"Hanging a ${num(m)}{U('kg')}$ mass from a spring stretches it ${num(x)}{U('cm')}$. Find the spring "
             "constant." + ctx.g_note(),
             f"$k = {ctx.fmt(k)}{U('N/m')}$",
             steps(known(("m", m, "kg"), ("x", x, "cm"), ("g", ctx.g, "m/s^2")),
                   f"In meters: $x = {num(x / 100)}{U('m')}$",
                   "At rest, the spring force balances the weight: $kx = mg$",
                   f"$k = \\frac{{mg}}{{x}} = \\frac{{({num(m)})({num(ctx.g)})}}{{{num(x / 100)}}} = {ctx.fmt(k)}{U('N/m')}$"),
             {"m": m, "x_cm": x}, {"k": k})


@variant("oscillations", 2, "Pendulum period")
def _pendulum(ctx: Ctx) -> Problem:
    tpi = "2\\pi"
    if ctx.rng.random() < 0.5:
        L = step(ctx.rng, 0.2, 3, 0.1)
        T = 2 * math.pi * math.sqrt(L / ctx.g)
        return P(f"A simple pendulum is ${num(L)}{U('m')}$ long. Find its period for small swings." + ctx.g_note(),
                 f"$T = {ctx.fmt(T)}{U('s')}$",
                 steps(known(("L", L, "m"), ("g", ctx.g, "m/s^2")), f"$T = {tpi}\\sqrt{{\\frac{{L}}{{g}}}}$",
                       f"$T = {tpi}\\sqrt{{\\frac{{{num(L)}}}{{{num(ctx.g)}}}}} = {ctx.fmt(T)}{U('s')}$"),
                 {"L": L}, {"T": T}, figure=draw.pendulum(f"{num(L)} m"))
    what, T = pick(ctx, [("A grandfather clock's pendulum", 2.0), ("A playground swing", None),
                         ("A metronome's pendulum", None)])
    T = T or (step(ctx.rng, 2.5, 4, 0.1) if "swing" in what else step(ctx.rng, 0.4, 1, 0.1))
    L = ctx.g * (T / (2 * math.pi)) ** 2
    return P(f"{what} has a period of ${num(T)}{U('s')}$. Treating it as a simple pendulum, how long is it?"
             + ctx.g_note(),
             f"$L = {ctx.fmt(L)}{U('m')}$",
             steps(known(("T", T, "s"), ("g", ctx.g, "m/s^2")),
                   f"$T = {tpi}\\sqrt{{\\frac{{L}}{{g}}}} \\Rightarrow L = g\\left(\\frac{{T}}{{{tpi}}}\\right)^2$",
                   f"$L = ({num(ctx.g)})\\left(\\frac{{{num(T)}}}{{{tpi}}}\\right)^2 = {ctx.fmt(L)}{U('m')}$"),
             {"T": T}, {"L": L}, figure=draw.pendulum("L"))


@variant("oscillations", 2, "Mass-spring period")
def _spring_period(ctx: Ctx) -> Problem:
    m, k = step(ctx.rng, 0.2, 5, 0.1), step(ctx.rng, 10, 500, 10)
    T = 2 * math.pi * math.sqrt(m / k)
    return P(f"A ${num(m)}{U('kg')}$ block attached to a spring with $k = {num(k)}{U('N/m')}$ oscillates on a "
             "frictionless surface. Find (a) the period and (b) the frequency of the motion.",
             f"(a) $T = {ctx.fmt(T)}{U('s')}$ (b) $f = {ctx.fmt(1 / T)}{U('Hz')}$",
             steps(known(("m", m, "kg"), ("k", k, "N/m")),
                   f"(a) $T = 2\\pi\\sqrt{{\\frac{{m}}{{k}}}} = 2\\pi\\sqrt{{\\frac{{{num(m)}}}{{{num(k)}}}}} = {ctx.fmt(T)}{U('s')}$",
                   f"(b) $f = \\frac{{1}}{{T}} = \\frac{{1}}{{{ctx.fmt(T)}}} = {ctx.fmt(1 / T)}{U('Hz')}$"),
             {"m": m, "k": k}, {"T": T, "f": 1 / T},
             figure=draw.spring_block(f"k = {num(k)} N/m", f"{num(m)} kg"))


@variant("oscillations", 3, "Energy in simple harmonic motion")
def _shm_energy(ctx: Ctx) -> Problem:
    def make():
        if ctx.nice:  # k/m a perfect square, so v_max = A·sqrt(k/m) is simple
            m = ctx.rng.choice([0.5, 1, 2, 4])
            k = m * step(ctx.rng, 2, 20, 2 if m == 0.5 else 1) ** 2
        else:
            m, k = step(ctx.rng, 0.2, 4, 0.1), step(ctx.rng, 20, 600, 10)
        A = step(ctx.rng, 2, 20, 1)
        return m, k, A, 0.5 * k * (A / 100) ** 2, A / 100 * math.sqrt(k / m)
    m, k, A, E, v = nice_draw(ctx, make, tries=200)
    return P(f"A ${num(m)}{U('kg')}$ block on a spring ($k = {num(k)}{U('N/m')}$) oscillates on a frictionless surface "
             f"with an amplitude of ${num(A)}{U('cm')}$. Find (a) the total mechanical energy and (b) the block's "
             "maximum speed.",
             f"(a) $E = {ctx.fmt(E)}{U('J')}$ (b) $v_{{max}} = {ctx.fmt(v)}{U('m/s')}$",
             steps(known(("m", m, "kg"), ("k", k, "N/m"), ("A", A, "cm")), f"In meters: $A = {num(A / 100)}{U('m')}$",
                   f"(a) At the amplitude it is all spring energy: $E = \\tfrac{{1}}{{2}}kA^2 = \\tfrac{{1}}{{2}}({num(k)})"
                   f"({num(A / 100)})^2 = {ctx.fmt(E)}{U('J')}$",
                   f"(b) At equilibrium it is all kinetic: $\\tfrac{{1}}{{2}}mv_{{max}}^2 = E$, so "
                   f"$v_{{max}} = \\sqrt{{\\frac{{2E}}{{m}}}} = \\sqrt{{\\frac{{2({ctx.fmt(E)})}}{{{num(m)}}}}} = {ctx.fmt(v)}{U('m/s')}$"),
             {"m": m, "k": k, "A_cm": A}, {"E": E, "v": v},
             figure=draw.spring_block(f"k = {num(k)} N/m", f"{num(m)} kg"))
