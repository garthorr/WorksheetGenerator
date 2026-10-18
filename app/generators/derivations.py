"""AP Physics 1 style symbolic derivations ("derive an expression for v in terms of g and h").

Each item lists the physics relations it rests on (``laws``) alongside the expected answer.
The tests solve those relations independently with sympy and compare, so a typo in an
answer can't slip through.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from .core import Ctx, Problem, steps, topic, variant


def L(e) -> str:
    return sp.latex(e, fold_func_brackets=True)


S = sp.Symbol
m, M, g, h, v, v0, a, t, d = S("m"), S("M"), S("g"), S("h"), S("v"), S("v_0"), S("a"), S("t"), S("d")
theta, mu, k, xc, r, G = S("theta"), S("mu"), S("k"), S("x"), S("r"), S("G")
m1, m2, F, T, N, P, K, W = S("m_1"), S("m_2"), S("F"), S("T"), S("N"), S("P"), S("K"), S("W")
h1, h2, vf, V, v1, v2, dK, ac = S("h_1"), S("h_2"), S("v_f"), S("V"), S("v_1"), S("v_2"), S(r"\Delta K"), S("a_c")
H, R_ = S("H"), S("R")

# Preferred order when listing "in terms of ..." symbols.
ORDER = [m, m1, m2, M, F, k, xc, v0, v, v1, a, t, d, h, h1, h2, r, theta, mu, G, g]


@dataclass
class Ask:
    text: str  # what to derive
    unknown: sp.Symbol
    answer: sp.Expr
    work: list[str]  # derivation steps (LaTeX inside $...$)
    solve_for: tuple = ()  # other unknowns the laws introduce (eliminated by the test)


@dataclass
class Item:
    level: int
    skill: str
    scenario: str  # may contain {obj}
    objs: list[str]
    laws: list[sp.Eq]
    asks: list[Ask]


ITEMS = [
    # ---------------------------------------------------------------- kinematics
    Item(2, "Kinematics derivations", "A {obj} starts from rest and speeds up with constant acceleration $a$.",
         ["car", "cart", "cyclist", "sprinter"], [sp.Eq(v, v0 + a * t), sp.Eq(d, v0 * t + a * t**2 / 2), sp.Eq(v0, 0)],
         [Ask("Derive an expression for its speed after a time $t$.", v, a * t,
              ["$v = v_0 + at$ with $v_0 = 0$", "$v = at$"], (d, v0)),
          Ask("Derive an expression for the distance it travels in a time $t$.", d, a * t**2 / 2,
              ["$d = v_0t + \\tfrac{1}{2}at^2$ with $v_0 = 0$", "$d = \\tfrac{1}{2}at^2$"], (v, v0)),
          Ask("Derive an expression for the time it takes to reach a speed $v$.", t, v / a,
              ["$v = v_0 + at$ with $v_0 = 0$", "$v = at \\Rightarrow t = \\frac{v}{a}$"], (d, v0))]),
    Item(3, "Kinematics derivations", "A {obj} starts from rest and speeds up with constant acceleration.",
         ["car", "cart", "cyclist"], [sp.Eq(v**2, v0**2 + 2 * a * d), sp.Eq(v0, 0)],
         [Ask("It reaches a speed $v$ after traveling a distance $d$. Derive an expression for its acceleration.",
              a, v**2 / (2 * d), ["$v^2 = v_0^2 + 2ad$ with $v_0 = 0$", "$v^2 = 2ad \\Rightarrow a = \\frac{v^2}{2d}$"],
              (v0,))]),
    Item(3, "Kinematics derivations", "A {obj} is dropped from rest from a height $h$ above the ground. "
         "Ignore air resistance.", ["stone", "ball", "wrench"],
         [sp.Eq(h, g * t**2 / 2), sp.Eq(v, g * t)],
         [Ask("Derive an expression for the time it takes to reach the ground.", t, sp.sqrt(2 * h / g),
              ["$h = \\tfrac{1}{2}gt^2$", "$t^2 = \\frac{2h}{g} \\Rightarrow t = \\sqrt{\\frac{2h}{g}}$"], (v,)),
          Ask("Derive an expression for its speed just before it hits the ground.", v, sp.sqrt(2 * g * h),
              ["$t = \\sqrt{\\frac{2h}{g}}$ (from $h = \\tfrac{1}{2}gt^2$)",
               "$v = gt = g\\sqrt{\\frac{2h}{g}} = \\sqrt{2gh}$"], (t,))]),
    Item(3, "Kinematics derivations", "A {obj} is thrown straight up with speed $v_0$. Ignore air resistance.",
         ["ball", "rock", "beanbag"], [sp.Eq(0, v0**2 - 2 * g * h), sp.Eq(0, v0 - g * t)],
         [Ask("Derive an expression for the maximum height it reaches.", h, v0**2 / (2 * g),
              ["At the top $v = 0$: $0 = v_0^2 - 2gh$", "$h = \\frac{v_0^2}{2g}$"], (t,)),
          Ask("Derive an expression for the time it takes to reach the top.", t, v0 / g,
              ["At the top $v = 0$: $0 = v_0 - gt$", "$t = \\frac{v_0}{g}$"], (h,))]),
    Item(3, "Kinematics derivations", "A {obj} is launched horizontally with speed $v$ from a height $h$ above level "
         "ground. Ignore air resistance.", ["ball", "marble", "package"],
         [sp.Eq(h, g * t**2 / 2), sp.Eq(d, v * t)],
         [Ask("Derive an expression for the time it is in the air.", t, sp.sqrt(2 * h / g),
              ["Vertically it starts from rest: $h = \\tfrac{1}{2}gt^2$", "$t = \\sqrt{\\frac{2h}{g}}$"], (d,)),
          Ask("Derive an expression for the horizontal distance it travels.", d, v * sp.sqrt(2 * h / g),
              ["$t = \\sqrt{\\frac{2h}{g}}$ (vertical motion)", "Horizontally the speed is constant: $d = vt$",
               "$d = v\\sqrt{\\frac{2h}{g}}$"], (t,))]),
    # ---------------------------------------------------------------- forces
    Item(2, "Force derivations", "A {obj} of mass $m$ slides down a frictionless incline at angle $\\theta$ above "
         "the horizontal.", ["block", "crate", "sled"],
         [sp.Eq(m * a, m * g * sp.sin(theta)), sp.Eq(N, m * g * sp.cos(theta))],
         [Ask("Derive an expression for its acceleration.", a, g * sp.sin(theta),
              ["Along the incline only $mg\\sin\\theta$ acts: $ma = mg\\sin\\theta$", "$a = g\\sin\\theta$"], (N,)),
          Ask("Derive an expression for the normal force on it.", N, m * g * sp.cos(theta),
              ["Perpendicular to the incline the forces balance: $N - mg\\cos\\theta = 0$", "$N = mg\\cos\\theta$"],
              (a,))]),
    Item(2, "Force derivations", "A {obj} of mass $m$ on a frictionless floor is pulled by a force $F$ directed at "
         "an angle $\\theta$ above the horizontal.", ["box", "sled", "wagon"],
         [sp.Eq(m * a, F * sp.cos(theta))],
         [Ask("Derive an expression for its acceleration.", a, F * sp.cos(theta) / m,
              ["Only the horizontal component accelerates it: $ma = F\\cos\\theta$", "$a = \\frac{F\\cos\\theta}{m}$"])]),
    Item(3, "Force derivations", "A {obj} of mass $m$ slides down an incline at angle $\\theta$; the coefficient of "
         "kinetic friction is $\\mu$.", ["block", "crate", "sled"],
         [sp.Eq(m * a, m * g * sp.sin(theta) - mu * N), sp.Eq(N, m * g * sp.cos(theta))],
         [Ask("Derive an expression for its acceleration.", a, g * (sp.sin(theta) - mu * sp.cos(theta)),
              ["$N = mg\\cos\\theta$, so friction is $\\mu mg\\cos\\theta$",
               "$ma = mg\\sin\\theta - \\mu mg\\cos\\theta$", "$a = g(\\sin\\theta - \\mu\\cos\\theta)$"], (N,))]),
    Item(3, "Force derivations", "Masses $m_1$ and $m_2$ (with $m_1 > m_2$) hang from a light string over a "
         "frictionless pulley.", ["Atwood machine"],
         [sp.Eq(m1 * a, m1 * g - T), sp.Eq(m2 * a, T - m2 * g)],
         [Ask("Derive an expression for the acceleration of the masses.", a, (m1 - m2) * g / (m1 + m2),
              ["Heavier mass: $m_1a = m_1g - T$; lighter mass: $m_2a = T - m_2g$",
               "Add them: $(m_1 + m_2)a = (m_1 - m_2)g$", "$a = \\frac{(m_1 - m_2)g}{m_1 + m_2}$"], (T,)),
          Ask("Derive an expression for the tension in the string.", T, 2 * m1 * m2 * g / (m1 + m2),
              ["$a = \\frac{(m_1 - m_2)g}{m_1 + m_2}$", "$T = m_2(g + a) = \\frac{2m_1m_2g}{m_1 + m_2}$"], (a,))]),
    Item(3, "Force derivations", "A block of mass $m_1$ on a frictionless table is connected by a light string over "
         "a pulley at the table's edge to a hanging {obj} of mass $m_2$.", ["block", "weight"],
         [sp.Eq(m1 * a, T), sp.Eq(m2 * a, m2 * g - T)],
         [Ask("Derive an expression for the acceleration of the system.", a, m2 * g / (m1 + m2),
              ["Table block: $m_1a = T$; hanging mass: $m_2a = m_2g - T$", "Add them: $(m_1 + m_2)a = m_2g$",
               "$a = \\frac{m_2g}{m_1 + m_2}$"], (T,))]),
    Item(3, "Force derivations", "A {obj} of mass $m$ is pushed across a floor by a horizontal force $F$; the "
         "coefficient of kinetic friction is $\\mu$.", ["crate", "box", "cart"],
         [sp.Eq(m * a, F - mu * N), sp.Eq(N, m * g)],
         [Ask("Derive an expression for its acceleration.", a, F / m - mu * g,
              ["$N = mg$, so friction is $\\mu mg$", "$ma = F - \\mu mg$", "$a = \\frac{F}{m} - \\mu g$"], (N,))]),
    # ---------------------------------------------------------------- energy
    Item(2, "Energy derivations", "A {obj} of mass $m$ slides from rest down a frictionless ramp of height $h$.",
         ["block", "skateboarder", "sled"], [sp.Eq(m * g * h, m * v**2 / 2)],
         [Ask("Derive an expression for its speed at the bottom.", v, sp.sqrt(2 * g * h),
              ["Energy is conserved: $mgh = \\tfrac{1}{2}mv^2$", "$v = \\sqrt{2gh}$"])]),
    Item(2, "Energy derivations", "A {obj} of mass $m$ is lifted at constant speed through a height $h$ in a time $t$.",
         ["box", "bucket", "crate"], [sp.Eq(W, m * g * h), sp.Eq(P * t, W)],
         [Ask("Derive an expression for the work done on it.", W, m * g * h,
              ["At constant speed the lifting force equals $mg$", "$W = Fd = mgh$"], (P,)),
          Ask("Derive an expression for the average power delivered.", P, m * g * h / t,
              ["$W = mgh$", "$P = \\frac{W}{t} = \\frac{mgh}{t}$"], (W,))]),
    Item(2, "Energy derivations", "A {obj} of mass $m$ has kinetic energy $K$.", ["cart", "ball", "runner"],
         [sp.Eq(K, m * v**2 / 2)],
         [Ask("Derive an expression for its speed.", v, sp.sqrt(2 * K / m),
              ["$K = \\tfrac{1}{2}mv^2$", "$v^2 = \\frac{2K}{m} \\Rightarrow v = \\sqrt{\\frac{2K}{m}}$"])]),
    Item(3, "Energy derivations", "A spring of spring constant $k$ is compressed a distance $x$ and launches a {obj} "
         "of mass $m$ along a frictionless surface.", ["block", "cart", "puck"],
         [sp.Eq(k * xc**2 / 2, m * v**2 / 2), sp.Eq(k * xc**2 / 2, m * g * h)],
         [Ask("Derive an expression for the launch speed.", v, xc * sp.sqrt(k / m),
              ["Spring energy becomes kinetic energy: $\\tfrac{1}{2}kx^2 = \\tfrac{1}{2}mv^2$", "$v = x\\sqrt{\\frac{k}{m}}$"],
              (h,)),
          Ask("The surface then curves up into a frictionless ramp. Derive an expression for the greatest height it "
              "reaches.", h, k * xc**2 / (2 * m * g),
              ["Spring energy becomes gravitational energy: $\\tfrac{1}{2}kx^2 = mgh$", "$h = \\frac{kx^2}{2mg}$"], (v,))]),
    Item(3, "Energy derivations", "A {obj} of mass $m$ moving at speed $v$ slides to a stop on a floor with "
         "coefficient of kinetic friction $\\mu$.", ["block", "hockey puck", "crate"],
         [sp.Eq(m * v**2 / 2, mu * m * g * d)],
         [Ask("Derive an expression for the stopping distance.", d, v**2 / (2 * mu * g),
              ["Friction's work removes the kinetic energy: $\\mu mg\\,d = \\tfrac{1}{2}mv^2$", "$d = \\frac{v^2}{2\\mu g}$"])]),
    Item(3, "Energy derivations", "A {obj} starts from rest at height $h_1$ on a frictionless track and rolls down "
         "to a point at height $h_2$.", ["roller-coaster car", "marble", "cart"],
         [sp.Eq(m * g * h1, m * g * h2 + m * v**2 / 2)],
         [Ask("Derive an expression for its speed at height $h_2$.", v, sp.sqrt(2 * g * (h1 - h2)),
              ["$mgh_1 = mgh_2 + \\tfrac{1}{2}mv^2$", "$v = \\sqrt{2g(h_1 - h_2)}$"])]),
    # ---------------------------------------------------------------- momentum
    Item(2, "Momentum derivations", "A {obj} of mass $m_1$ moving at speed $v$ collides with and sticks to a "
         "stationary {obj} of mass $m_2$.", ["cart", "railroad car", "puck"],
         [sp.Eq(m1 * v, (m1 + m2) * vf)],
         [Ask("Derive an expression for their speed just after the collision.", vf, m1 * v / (m1 + m2),
              ["Momentum is conserved: $m_1v = (m_1 + m_2)v_f$", "$v_f = \\frac{m_1v}{m_1 + m_2}$"])]),
    Item(2, "Momentum derivations", "A {obj} at rest breaks into two pieces of mass $m_1$ and $m_2$. The first moves "
         "off at speed $v_1$.", ["firework shell", "space capsule", "rock"],
         [sp.Eq(0, m1 * v1 - m2 * v2)],
         [Ask("Derive an expression for the speed of the second piece.", v2, m1 * v1 / m2,
              ["Total momentum stays zero: $0 = m_1v_1 - m_2v_2$", "$v_2 = \\frac{m_1v_1}{m_2}$"])]),
    Item(2, "Momentum derivations", "A {obj} of mass $m$ moving at speed $v$ is brought to rest in a time $t$.",
         ["ball", "car", "egg"], [sp.Eq(F * t, m * v)],
         [Ask("Derive an expression for the average force needed.", F, m * v / t,
              ["Impulse equals the change in momentum: $Ft = mv$", "$F = \\frac{mv}{t}$"])]),
    Item(3, "Momentum derivations", "A {obj} of mass $m_1$ moving at speed $v$ collides with and sticks to a "
         "stationary object of mass $m_2$.", ["cart", "puck", "ball of clay"],
         [sp.Eq(m1 * v, (m1 + m2) * vf), sp.Eq(dK, m1 * v**2 / 2 - (m1 + m2) * vf**2 / 2)],
         [Ask("Derive an expression for the kinetic energy lost in the collision.", dK, m1 * m2 * v**2 / (2 * (m1 + m2)),
              ["$v_f = \\frac{m_1v}{m_1 + m_2}$ (momentum)", "$\\Delta K = \\tfrac{1}{2}m_1v^2 - \\tfrac{1}{2}(m_1 + m_2)v_f^2$",
               "$\\Delta K = \\frac{m_1m_2v^2}{2(m_1 + m_2)}$"], (vf,))]),
    Item(3, "Momentum derivations", "A {obj} of mass $m$ moving at speed $v$ embeds in a block of mass $M$ hanging "
         "at rest from a string. The block and {obj} swing up to a height $h$.", ["bullet", "dart"],
         [sp.Eq(m * v, (m + M) * V), sp.Eq((m + M) * V**2 / 2, (m + M) * g * h)],
         [Ask("Derive an expression for the initial speed $v$ in terms of $m$, $M$, $g$ and $h$.", v,
              (m + M) * sp.sqrt(2 * g * h) / m,
              ["After the collision, energy: $\\tfrac{1}{2}(m + M)V^2 = (m + M)gh \\Rightarrow V = \\sqrt{2gh}$",
               "During the collision, momentum: $mv = (m + M)V$", "$v = \\frac{(m + M)\\sqrt{2gh}}{m}$"], (V,))]),
    Item(3, "Momentum derivations", "An {obj} of mass $M$ at rest splits into two pieces; one of mass $m$ moves off "
         "at speed $v$.", ["object", "explosive charge"],
         [sp.Eq(m * v, (M - m) * V), sp.Eq(K, m * v**2 / 2 + (M - m) * V**2 / 2)],
         [Ask("Derive an expression for the total kinetic energy released.", K, m * M * v**2 / (2 * (M - m)),
              ["Momentum: $mv = (M - m)V \\Rightarrow V = \\frac{mv}{M - m}$",
               "$K = \\tfrac{1}{2}mv^2 + \\tfrac{1}{2}(M - m)V^2 = \\frac{mMv^2}{2(M - m)}$"], (V,))]),
    # ---------------------------------------------------------------- circular motion & gravitation
    Item(2, "Circular motion derivations", "A {obj} of mass $m$ moves in a circle of radius $r$ at constant speed $v$.",
         ["car", "ball on a string", "satellite"],
         [sp.Eq(ac, v**2 / r), sp.Eq(v * T, 2 * sp.pi * r), sp.Eq(F, m * v**2 / r)],
         [Ask("Derive an expression for its centripetal acceleration.", ac, v**2 / r,
              ["For uniform circular motion the acceleration points to the center:", "$a_c = \\frac{v^2}{r}$"], (T, F)),
          Ask("Derive an expression for the time for one revolution.", T, 2 * sp.pi * r / v,
              ["One lap is $2\\pi r$ at speed $v$: $vT = 2\\pi r$", "$T = \\frac{2\\pi r}{v}$"], (ac, F)),
          Ask("Derive an expression for the net (centripetal) force on it.", F, m * v**2 / r,
              ["Newton's second law with $a_c = \\frac{v^2}{r}$:", "$F = ma_c = \\frac{mv^2}{r}$"], (ac, T))]),
    Item(3, "Circular motion derivations", "A {obj} rounds a flat curve of radius $r$. The coefficient of static "
         "friction between the tires and the road is $\\mu$.", ["car", "motorcycle", "bus"],
         [sp.Eq(m * v**2 / r, mu * m * g)],
         [Ask("Derive an expression for the greatest speed it can have without sliding.", v, sp.sqrt(mu * g * r),
              ["Friction supplies the centripetal force: $\\frac{mv^2}{r} = \\mu mg$", "$v = \\sqrt{\\mu gr}$"])]),
    Item(3, "Circular motion derivations", "A {obj} moves in a circular orbit of radius $r$ around a planet of mass $M$.",
         ["satellite", "moon", "space station"],
         [sp.Eq(G * M * m / r**2, m * v**2 / r), sp.Eq(v * T, 2 * sp.pi * r)],
         [Ask("Derive an expression for its orbital speed.", v, sp.sqrt(G * M / r),
              ["Gravity supplies the centripetal force: $\\frac{GMm}{r^2} = \\frac{mv^2}{r}$", "$v = \\sqrt{\\frac{GM}{r}}$"],
              (T,)),
          Ask("Derive an expression for its orbital period.", T, 2 * sp.pi * sp.sqrt(r**3 / (G * M)),
              ["$v = \\sqrt{\\frac{GM}{r}}$", "$T = \\frac{2\\pi r}{v} = 2\\pi\\sqrt{\\frac{r^3}{GM}}$"], (v,))]),
    Item(3, "Circular motion derivations", "A {obj} goes around a vertical loop of radius $r$.",
         ["roller-coaster car", "toy car", "marble"],
         [sp.Eq(m * g, m * v**2 / r)],
         [Ask("Derive an expression for the minimum speed it needs at the top of the loop to stay on the track.", v,
              sp.sqrt(g * r),
              ["At the minimum speed, gravity alone supplies the centripetal force: $mg = \\frac{mv^2}{r}$",
               "$v = \\sqrt{gr}$"])]),
]

topic("derivations", "physics", "Derivations", "Symbolic derivations",
      "AP-style problems: derive an expression in terms of given quantities.", courses=["ap1"])


def _in_terms_of(expr: sp.Expr) -> str:
    syms = sorted(expr.free_symbols, key=lambda s_: ORDER.index(s_) if s_ in ORDER else 99)
    names = [f"${L(s_)}$" for s_ in syms]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _final_form(ask: Ask) -> str:
    """The answer as the derivation's last step writes it (mg cos θ, not sympy's g m cos θ)."""
    last = ask.work[-1].strip().strip("$")
    return last.split("=")[-1].strip() if "=" in last else L(ask.answer)


def _make(level: int, skill: str):
    pool = [(item, ask) for item in ITEMS if item.level == level and item.skill == skill for ask in item.asks]

    def build(ctx: Ctx) -> Problem:
        item, ask = ctx.rng.choice(pool)
        obj = ctx.rng.choice(item.objs)
        text = ask.text if "in terms of" in ask.text else \
            ask.text.rstrip(".") + f" in terms of {_in_terms_of(ask.answer)}."
        return Problem(f"{item.scenario.replace('{obj}', obj)} {text}",
                       f"${L(ask.unknown)} = {_final_form(ask)}$", steps(*ask.work),
                       facts={"given": {}, "ans": {}, "what": "", "symbolic": True, "laws": item.laws,
                              "unknown": ask.unknown, "answer": ask.answer, "solve_for": ask.solve_for})
    build.__name__ = f"_derive_{skill.split()[0].lower()}_{level}"
    return build


for _skill in dict.fromkeys(i.skill for i in ITEMS):
    for _level in sorted({i.level for i in ITEMS if i.skill == _skill}):
        variant("derivations", _level, _skill)(_make(_level, _skill))
