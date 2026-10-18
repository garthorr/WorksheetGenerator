"""Wrong choices for each AP Physics 1 problem type, built from the mistakes students make.

Each spec gets the problem's givens ``G``, its answers ``A``, ``g`` and its other facts, and
returns the quantities it can ask for: ``{answer key: Part(unit, [wrong values], ...)}``.
Wrong values are listed most typical mistake first; mc.py drops any that would be
confusing (too close to the answer, a duplicate, the wrong sign) and fills in if needed.
"""

from __future__ import annotations

import math

from .mc import Part, spec

PI = math.pi
NS, KGMS = "N\\cdot s", "kg\\cdot m/s"


def trig(G):
    """sin and cos of the problem's angle: the stated textbook values (3-4-5) when it gives them."""
    r = math.radians(G["theta"])
    return G.get("sin", math.sin(r)), G.get("cos", math.cos(r))


def slope_parts(pts, i):
    (t0, x0), (t1, x1) = pts[i], pts[i + 1]
    return t0, x0, t1, x1


# ------------------------------------------------------------------ kinematics

@spec("_kin_final_v")
def _(G, A, g, f):
    v0, a, t = G["v0"], G["a"], G["t"]
    return {"v": Part("m/s", [a * t if v0 else None, v0 + a * t / 2, v0 + a * t * t, a * t * t / 2, v0 + a / t])}


@spec("_kin_find_a")
def _(G, A, g, f):
    v0, v, t = G["v0"], G["v"], G["t"]
    return {"a": Part("m/s^2", [v / t if v0 else None, (v + v0) / t, (v - v0) * t, 2 * (v - v0) / t, t / (v - v0)])}


@spec("_kin_find_t")
def _(G, A, g, f):
    v0, v, a = G["v0"], G["v"], G["a"]
    return {"t": Part("s", [v / a if v0 else None, (v + v0) / a, (v - v0) * a, 2 * (v - v0) / a, a / (v - v0)])}


@spec("_kin_xt_graph")
def _(G, A, g, f):
    pts = f["graph"]
    out = {}
    for key, i in (("vA", 0), ("vB", 2)):
        t0, x0, t1, x1 = slope_parts(pts, i)
        out[key] = Part("m/s", [x1 - x0, x1, x1 / t1 if t1 else None, (t1 - t0) / (x1 - x0) if x1 != x0 else None],
                        signed=True)
    return out


@spec("_kin_vt_graph")
def _(G, A, g, f):
    pts = f["graph"]
    (t0, v0), (t1, v1) = pts[0], pts[1]
    rects = sum(vb * (tb - ta) for (ta, _), (tb, vb) in zip(pts, pts[1:]))  # rectangles, not trapezoids
    return {"a": Part("m/s^2", [v1, (t1 - t0) / (v1 - v0) if v1 != v0 else None, v1 / 2]),
            "d": Part("m", [rects, pts[-1][1] * pts[-1][0], A["d"] / 2, 2 * A["d"]], signed=True)}


@spec("_kin_vt_graph_signed")
def _(G, A, g, f):
    return {"d": Part("m", [A["dist"], -A["d"], -A["dist"]], signed=True),
            "dist": Part("m", [abs(A["d"]), A["dist"] / 2, A["dist"] * 2])}


@spec("_kin_free_fall")
def _(G, A, g, f):
    h = G["h"]
    return {"t": Part("s", [math.sqrt(h / g), 2 * h / g, h / g, math.sqrt(2 * h * g)]),
            "v": Part("m/s", [2 * g * h, math.sqrt(g * h), g * h, math.sqrt(2 * h / g)])}


@spec("_kin_displacement")
def _(G, A, g, f):
    v0, a, t = G["v0"], G["a"], G["t"]
    return {"d": Part("m", [v0 * t + a * t * t, a * t * t / 2 if v0 else None, (v0 + a * t) * t, v0 * t + a * t / 2])}


@spec("_kin_braking")
def _(G, A, g, f):
    v0, a = G["v0"], G["a"]
    return {"d": Part("m", [v0 * v0 / a, v0 / (2 * a), v0 * v0 / (4 * a), v0 * v0 * a / 2]),
            "t": Part("s", [2 * v0 / a, v0 / (2 * a), a / v0, v0 * v0 / a])}


@spec("_kin_throw_up")
def _(G, A, g, f):
    v0 = G["v0"]
    return {"h": Part("m", [v0 * v0 / g, v0 / (2 * g), v0 / g, v0 * v0 / (4 * g)]),
            "t": Part("s", [v0 / g, 4 * v0 / g, v0 * v0 / g, v0 / (2 * g)])}


# ------------------------------------------------------------------ projectiles

def _fall_mistakes(h, g):
    return [math.sqrt(h / g), 2 * h / g, math.sqrt(2 * h * g) / g * 2, h / g]


@spec("_proj_horiz_range")
def _(G, A, g, f):
    h, v = G["h"], G["v"]
    return {"x": Part("m", [v * t for t in _fall_mistakes(h, g)] + [2 * A["x"]])}


@spec("_proj_horiz_full")
def _(G, A, g, f):
    h, v, t = G["h"], G["v"], A["t"]
    return {"t": Part("s", _fall_mistakes(h, g)),
            "x": Part("m", [v * w for w in _fall_mistakes(h, g)]),
            "speed": Part("m/s", [v + g * t, g * t, v, math.sqrt(v * v + g * t)])}


@spec("_proj_angle")
def _(G, A, g, f):
    v = G["v"]
    s, c = trig(G)
    return {"T": Part("s", [v * s / g, 2 * v * c / g, 2 * v / g, v * c / g]),
            "H": Part("m", [(v * s) ** 2 / g, (v * c) ** 2 / (2 * g), v * v / (2 * g), v * s / (2 * g)]),
            "R": Part("m", [A["R"] / 2, v * A["T"], v * s * A["T"], v * v / g])}


# ------------------------------------------------------------------ forces

@spec("_newton_force")
def _(G, A, g, f):
    m, a = G["m"], G["a"]
    return {"F": Part("N", [m / a, m * g, m * (a + g), a / m])}


@spec("_newton_accel")
def _(G, A, g, f):
    F, m = G["F"], G["m"]
    return {"a": Part("m/s^2", [F * m, m / F, F / (m * g), F / m - g])}


@spec("_newton_fbd")
def _(G, A, g, f):
    F, m = f["forces"], G["m"]
    old = "Find (a) the net force and (b) the box's acceleration."
    total = F["right"] + F["left"]
    return {"F": Part("N", [total, max(F["right"], F["left"]), A["F"] * 2, F["up"] + A["F"]],
                      ask=(old, "Find the magnitude of the net force on the box.")),
            "a": Part("m/s^2", [total / m, A["F"] * m, m / A["F"], max(F["right"], F["left"]) / m],
                      ask=(old, "Find the magnitude of the box's acceleration."))}


@spec("_newton_fbd_2d")
def _(G, A, g, f):
    F = f["forces"]
    fx, fy = abs(F["right"] - F["left"]), abs(F["up"] - F["down"])
    return {"F": Part("N", [fx + fy, max(fx, fy), math.hypot(F["right"], F["up"]), abs(fx - fy)],
                      ask=("Find the magnitude of the net force and the angle it makes with the horizontal.",
                           "Find the magnitude of the net force."))}


@spec("_newton_friction")
def _(G, A, g, f):
    m, F, mu = G["m"], G["F"], G["mu"]
    return {"a": Part("m/s^2", [F / m, (F + mu * m * g) / m, (F - mu * m) / m, (F - mu * m * g) / (m * g)])}


@spec("_newton_incline")
def _(G, A, g, f):
    s, c = trig(G)
    mu = G["mu"]
    return {"a": Part("m/s^2", [g * (c - mu * s), g * (s + mu * c), g * s, g * (s - mu)])}


@spec("_newton_atwood")
def _(G, A, g, f):
    heavy, light = max(G["m1"], G["m2"]), min(G["m1"], G["m2"])
    return {"a": Part("m/s^2", [(heavy - light) * g / heavy, heavy * g / (heavy + light), (heavy - light) * g,
                                (heavy - light) * g / light]),
            "T": Part("N", [heavy * g, light * g, (heavy + light) * g / 2, light * (g - A["a"])])}


# ------------------------------------------------------------------ energy

@spec("_energy_ke")
def _(G, A, g, f):
    m, v = G["m"], G["v"]
    return {"KE": Part("J", [m * v * v, m * v / 2, m * v, (m * v) ** 2 / 2])}


@spec("_energy_ke_speed")
def _(G, A, g, f):
    KE, m = G["KE"], G["m"]
    return {"v": Part("m/s", [2 * KE / m, math.sqrt(KE / m), KE / m, math.sqrt(2 * KE * m)])}


@spec("_energy_pe")
def _(G, A, g, f):
    m, h = G["m"], G["h"]
    return {"PE": Part("J", [m * h, m * g * h / 2, m * h / g, m * g])}


@spec("_energy_pe_height")
def _(G, A, g, f):
    PE, m = G["PE"], G["m"]
    return {"h": Part("m", [PE / m, PE * g / m, PE / (2 * m * g), m * g / PE])}


@spec("_energy_work_angle")
def _(G, A, g, f):
    F, d, th = G["F"], G["d"], G["theta"]
    r = math.radians(th)
    return {"W": Part("J", [F * d * math.sin(r) if th else None, F * d if th else None, F / d, F * d * math.cos(r) / 2])}


@spec("_energy_coaster")
def _(G, A, g, f):
    h = G["h"]
    return {"v": Part("m/s", [2 * g * h, math.sqrt(g * h), g * h, math.sqrt(2 * h / g)])}


@spec("_energy_power")
def _(G, A, g, f):
    m, h, t = G["m"], G["h"], G["t"]
    return {"P": Part("W", [m * g * h, m * h / t, m * g * h * t, m * g * h / (2 * t)])}


@spec("_energy_friction_loss")
def _(G, A, g, f):
    m, h, v = G["m"], G["h"], G["v"]
    return {"E": Part("J", [m * g * h, m * v * v / 2, m * g * h + m * v * v / 2, m * g * h - m * v * v])}


# ------------------------------------------------------------------ momentum

@spec("_mom_p")
def _(G, A, g, f):
    m, v = G["m"], G["v"]
    return {"p": Part(KGMS, [m * v * v / 2, m / v, v / m, m * v * v])}


@spec("_mom_p_speed")
def _(G, A, g, f):
    p, m = G["p"], G["m"]
    return {"v": Part("m/s", [p * m, m / p, math.sqrt(2 * p / m), p / (2 * m)])}


@spec("_mom_impulse")
def _(G, A, g, f):
    F, t = G["F"], G["t"]
    return {"J": Part(NS, [F / t, F * t / 2, t / F, F * t * t])}


@spec("_mom_inelastic")
def _(G, A, g, f):
    m1, m2, v1, v2 = G["m1"], G["m2"], G["v1"], G["v2"]
    return {"vf": Part("m/s", [(m1 * v1 - m2 * v2) / (m1 + m2) if v2 else None,
                               m1 * v1 / (m1 + m2) if v2 else None, (v1 + v2) / 2, (m1 * v1 + m2 * v2) / m1,
                               m1 * v1 / m2], signed=True)}


@spec("_mom_elastic")
def _(G, A, g, f):
    m1, m2, v1 = G["m1"], G["m2"], G["v1"]
    old = "Find both final velocities."
    return {"v1f": Part("m/s", [-A["v1f"], m1 * v1 / (m1 + m2), 0, v1 * (m1 - m2) / m1, v1],
                        ask=(old, "Find the velocity of the first cart just after the collision."), signed=True),
            "v2f": Part("m/s", [v1, m1 * v1 / (m1 + m2), m1 * v1 / m2, v1 * (m1 - m2) / (m1 + m2)],
                        ask=(old, "Find the velocity of the second cart just after the collision."), signed=True)}


# ------------------------------------------------------------------ circular motion & gravitation

@spec("_circ_accel")
def _(G, A, g, f):
    r, v = G["r"], G["v"]
    return {"ac": Part("m/s^2", [v / r, v * v * r, v * r, r / v])}


@spec("_circ_speed")
def _(G, A, g, f):
    ac, r = G["ac"], G["r"]
    return {"v": Part("m/s", [ac * r, math.sqrt(ac / r), ac / r, math.sqrt(2 * ac * r)])}


@spec("_circ_string")
def _(G, A, g, f):
    m, r, T = G["m"], G["r"], G["T"]
    v = A["v"]
    return {"v": Part("m/s", [PI * r / T, r / T, 2 * PI * T / r, 2 * PI * r * T]),
            "F": Part("N", [m * v / r, m * v * v, m * v * v * r, m * (r / T) ** 2 / r])}


@spec("_circ_orbit")
def _(G, A, g, f):
    GM, R, h = 6.674e-11 * G["M"], G["R"], G["h_km"] * 1e3
    r = R + h
    v_R, v_h = math.sqrt(GM / R), math.sqrt(GM / h)
    return {"v": Part("m/s", [v_R, math.sqrt(GM / (R + G["h_km"])), v_h, math.sqrt(2 * GM / r)]),
            "T": Part("s", [2 * PI * R / v_R, r / A["v"], 2 * PI * h / v_h, A["T"] / 2])}


# ------------------------------------------------------------------ fluids

@spec("_density")
def _(G, A, g, f):
    m, V = G["m"], G["V"]
    return {"rho": Part("g/cm^3", [V / m, m / V / 10, m / (2 * V), m / V * 2])}


@spec("_density_mass")
def _(G, A, g, f):
    rho, V = G["rho"], G["V"]
    return {"m": Part("g", [V / rho, rho * V / 10, rho * V / 2, rho * V * 2])}


@spec("_pressure_depth")
def _(G, A, g, f):
    rho, h = G["rho"], G["h"]
    return {"P": Part("Pa", [rho * g * h, 101300 + rho * h, 101300 + rho * g * h * 2, 101300 + rho * g * h / 2])}


@spec("_buoyancy")
def _(G, A, g, f):
    V, rho = G["V"], G["rho"]
    W = rho * V * g
    return {"Fb": Part("N", [W, 1000 * V, W - A["Fb"], 1000 * V * g * 2]),
            "Wapp": Part("N", [W, W + A["Fb"], A["Fb"], rho * V - 1000 * V])}


# ------------------------------------------------------------------ torque & rotation

@spec("_torque_perp")
def _(G, A, g, f):
    r, F = G["r"], G["F"]
    return {"tau": Part("N\\cdot m", [F / r, r * F / 2, r / F, r * r * F])}


@spec("_torque_angle")
def _(G, A, g, f):
    r, F = G["r"], G["F"]
    s, c = trig(G)
    return {"tau": Part("N\\cdot m", [r * F * c, r * F, F / r * s, r * F * s / 2])}


@spec("_seesaw")
def _(G, A, g, f):
    m1, d1, m2 = G["m1"], G["d1"], G["m2"]
    return {"d2": Part("m", [m2 * d1 / m1, d1, m1 * d1 / (m1 + m2), 2 * d1 - m1 * d1 / m2])}


@spec("_beam_supports")
def _(G, A, g, f):
    M, L, m, x = G["M"], G["L"], G["m"], G["x"]
    even, only_load = (M + m) * g / 2, m * g * x / L
    old = "Find the upward force from each support."
    return {"FL": Part("N", [A["FR"], even, (M + m) * g, m * g * (L - x) / L],
                       ask=(old, "What upward force does the support at the left end exert?")),
            "FR": Part("N", [A["FL"], even, only_load, (M + m) * g],
                       ask=(old, "What upward force does the support at the right end exert?"))}


@spec("_ang_velocity")
def _(G, A, g, f):
    rpm, r = G["rpm"], G["r"]
    return {"omega": Part("rad/s", [rpm / 60, 2 * PI * rpm, rpm * PI / 60]),
            "v": Part("m/s", [rpm * r / 60, 2 * A["v"], PI * rpm * r / 60, A["omega"] / r, 2 * PI * rpm * r])}


@spec("_ang_accel")
def _(G, A, g, f):
    w0, w, t = G["w0"], G["w"], G["t"]
    return {"alpha": Part("rad/s^2", [w / t if w0 else None, (w + w0) / t, (w - w0) * t, 2 * (w - w0) / t]),
            "theta": Part("rad", [w * t, (w - w0) * t / 2 if w0 else w * t * 2, A["alpha"] * t * t / 2 if w0 else None,
                                  w0 * t if w0 else None, A["theta"] * 2])}


@spec("_torque_alpha")
def _(G, A, g, f):
    M, R, F, t = G["M"], G["R"], G["F"], G["t"]
    return {"alpha": Part("rad/s^2", [F / (M * R), F * R / (M / 2), F / M, 4 * F / (M * R)]),
            "w": Part("rad/s", [F / (M * R) * t, A["alpha"] * t / 2, A["alpha"] * t * t, F / M * t])}


@spec("_pulley_mass")
def _(G, A, g, f):
    m, M, R = G["m"], G["M"], G["R"]
    a_point = m * g / (m + M)  # pulley treated as a point mass
    return {"a": Part("m/s^2", [g, a_point, m * g / M, m * g / (m + 2 * M)]),
            "T": Part("N", [m * g, m * (g + A["a"]), M * g / 2, m * (g - a_point)]),
            "alpha": Part("rad/s^2", [A["a"] * R, g / R, a_point / R, A["a"] / (2 * R)])}


# ------------------------------------------------------------------ rotational energy & angular momentum

@spec("_rot_ke")
def _(G, A, g, f):
    M, R, w, beta = G["M"], G["R"], G["w"], f["inertia"]
    I = A["I_rot"]
    return {"I_rot": Part("kg\\cdot m^2", [M * R * R if beta != 1 else M * R * R / 2, beta * M * R, M * R * R * 2]),
            "KE": Part("J", [I * w / 2, I * w * w, M * (w * R) ** 2 / 2 if beta != 1 else M * (w * R) ** 2 / 4,
                             M * R * R * w * w / 2 if beta != 1 else None])}


@spec("_skater")
def _(G, A, g, f):
    I1, w1, I2 = G["I1"], G["w1"], G["I2"]
    return {"w2": Part("rad/s", [I2 * w1 / I1, w1 * math.sqrt(I1 / I2), w1 * (I1 / I2) ** 2, w1 * (I1 - I2)])}


@spec("_platform")
def _(G, A, g, f):
    M, R, w0, m = G["M"], G["R"], G["w0"], G["m"]
    Id = M * R * R / 2
    return {"w": Part("rad/s", [M * w0 / (M + m), M * R * R * w0 / (M * R * R + m * R * R), Id * w0 / (Id + m * R * R / 2),
                                Id * w0 / (m * R * R)])}


@spec("_rolling")
def _(G, A, g, f):
    h, beta = G["h"], f["inertia"]
    others = [b for b in (0.4, 0.5, 1.0, 2 / 3) if abs(b - beta) > 1e-9]
    return {"v": Part("m/s", [math.sqrt(2 * g * h), *[math.sqrt(2 * g * h / (1 + b)) for b in others[:1]],
                              math.sqrt(g * h), 2 * g * h / (1 + beta)])}


@spec("_rolling_ke")
def _(G, A, g, f):
    m, v, beta = G["m"], G["v"], f["inertia"]
    Kt, Kr = A["Kt"], A["Kr"]
    return {"Kt": Part("J", [m * v * v, Kt + Kr, Kr, m * v / 2]),
            "Kr": Part("J", [Kt, beta * m * v * v, 2 * Kr if beta != 1 else Kr / 2, Kt + Kr]),
            "K": Part("J", [Kt, Kt + 2 * Kr, Kr, m * v * v])}


# ------------------------------------------------------------------ oscillations

@spec("_osc_period")
def _(G, A, g, f):
    N, t = G["N"], G["t"]
    return {"T": Part("s", [N / t, t / (2 * PI * N), 2 * PI * t / N, t * N / 100]),
            "f": Part("Hz", [t / N, 2 * PI * N / t, N / (2 * PI * t), N / t / 2])}


@spec("_hooke")
def _(G, A, g, f):
    m, x = G["m"], G["x_cm"]
    return {"k": Part("N/m", [m * g / x, m / (x / 100), m * g * (x / 100), A["k"] / 2])}


@spec("_pendulum")
def _(G, A, g, f):
    if "L" in G:
        L = G["L"]
        return {"T": Part("s", [2 * PI * math.sqrt(g / L), math.sqrt(L / g), 2 * PI * L / g, PI * math.sqrt(L / g)])}
    T = G["T"]
    return {"L": Part("m", [g * T / (2 * PI), g * T * T / (2 * PI), T * T / (4 * PI * PI), g * T * T / (4 * PI)])}


@spec("_spring_period")
def _(G, A, g, f):
    m, k = G["m"], G["k"]
    return {"T": Part("s", [2 * PI * math.sqrt(k / m), math.sqrt(m / k), 2 * PI * m / k, PI * math.sqrt(m / k)]),
            "f": Part("Hz", [math.sqrt(k / m), 2 * PI * math.sqrt(m / k), math.sqrt(m / k) / (2 * PI),
                             1 / A["f"]])}


@spec("_shm_energy")
def _(G, A, g, f):
    m, k, A_cm = G["m"], G["k"], G["A_cm"]
    a = A_cm / 100
    return {"E": Part("J", [k * a * a, k * a / 2, m * a * a / 2, k * a * a / 4]),
            "v": Part("m/s", [a * k / m, a * math.sqrt(m / k), 2 * A["E"] / m, a * math.sqrt(2 * k / m)])}
