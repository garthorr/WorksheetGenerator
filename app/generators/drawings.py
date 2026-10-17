"""Figures for worksheet problems, built with the drawing kit in figures.py.

Every function takes the problem's real values (so shapes are drawn to scale) and the
labels to show; the caller decides which values are given and which unknown, so a
figure never reveals an answer. Each returns an SVG string.
"""

from __future__ import annotations

import math

from .figures import GRAY, INK, WATER, Fig, Graph

# ======================================================================== geometry


def right_triangle(a: float, b: float, *, label_a: str = "", label_b: str = "", label_c: str = "",
                   angle_at: str = "", angle_label: str = "") -> str:
    """Right triangle with legs a (horizontal) and b (vertical), right angle at the bottom left.
    ``angle_at`` = "base" marks the acute angle at the bottom right (between leg a and the hypotenuse)."""
    C, B, A = (0.0, 0.0), (float(a), 0.0), (0.0, float(b))
    f = Fig(size=210, max_height=150)
    f.poly([C, B, A])
    f.right_angle(C, B, A)
    centre = (a / 3, b / 3)
    if label_a:
        f.seg_label(C, B, label_a, away=centre, italic=label_a in ("x", "?"))
    if label_b:
        f.seg_label(C, A, label_b, away=centre, italic=label_b in ("x", "?"))
    if label_c:
        f.seg_label(A, B, label_c, away=centre, italic=label_c in ("x", "?"))
    if angle_at == "base":
        f.angle(B, C, A, angle_label, italic=angle_label == "θ")
    return f.svg()


def rectangle(w: float, h: float, label_w: str, label_h: str) -> str:
    f = Fig(size=190, max_height=120)
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
    f.poly(pts)
    f.seg_label(pts[0], pts[1], label_w, away=(w / 2, h / 2))
    f.seg_label(pts[1], pts[2], label_h, away=(w / 2, h / 2))
    for v, a, b in ((pts[0], pts[1], pts[3]),):
        f.right_angle(v, a, b, size_px=7)
    return f.svg()


def triangle_base_height(base: float, height: float, label_b: str, label_h: str) -> str:
    apex_x = base * 0.35
    A, B, P = (0, 0), (base, 0), (apex_x, height)
    f = Fig(size=190, max_height=120)
    f.poly([A, B, P])
    f.line(P, (apex_x, 0), dash=True)
    f.right_angle((apex_x, 0), B, P, size_px=7)
    f.seg_label(A, B, label_b, away=(base / 2, height))
    f.text((apex_x, height / 2), label_h, dx=6, anchor="start")
    return f.svg()


def trapezoid(a: float, b: float, h: float, label_a: str, label_b: str, label_h: str) -> str:
    off = (b - a) / 2
    P = [(0, 0), (b, 0), (off + a, h), (off, h)]
    f = Fig(size=200, max_height=110)
    f.poly(P)
    f.seg_label(P[0], P[1], label_b, away=(b / 2, h))
    f.seg_label(P[3], P[2], label_a, away=(b / 2, 0))
    f.line((off, h), (off, 0), dash=True)
    f.right_angle((off, 0), P[1], (off, h), size_px=7)
    f.text((off, h / 2), label_h, dx=5, anchor="start")
    return f.svg()


def circle(r: float, label: str, *, diameter: bool = False) -> str:
    f = Fig(size=130, max_height=130)
    f.circle((0, 0), r)
    f.dot((0, 0))
    if diameter:
        f.line((-r, 0), (r, 0))
        f.text((0, 0), label, dy=-7)
    else:
        f.line((0, 0), (r, 0))
        f.text((r / 2, 0), label, dy=-7)
    return f.svg()


def window(w: float, h: float, label_w: str, label_h: str) -> str:
    """Rectangle w × h topped by a semicircle across its width."""
    f = Fig(size=150, max_height=170)
    f.poly([(w, h), (w, 0), (0, 0), (0, h)], closed=False)
    f.line((0, h), (w, h), dash=True)
    f.arc((w / 2, h), w / 2, 0, 180)
    f.seg_label((0, 0), (w, 0), label_w, away=(w / 2, h))
    f.seg_label((w, 0), (w, h), label_h, away=(0, h / 2))
    return f.svg()


def stadium(length: float, width: float, label_l: str, label_w: str) -> str:
    """Rectangle with a semicircle on each short end (a running track / field)."""
    r = width / 2
    f = Fig(size=230, max_height=110)
    f.line((0, 0), (length, 0)).line((0, width), (length, width))
    f.arc((length, r), r, -90, 90)
    f.arc((0, r), r, 90, 270)
    f.line((0, 0), (0, width), dash=True).line((length, 0), (length, width), dash=True)
    f.seg_label((0, width), (length, width), label_l, away=(length / 2, 0))
    f.text((length, r), label_w, dx=-5, anchor="end")
    return f.svg()


def box(l: float, w: float, h: float, label_l: str, label_w: str, label_h: str, *, diagonal: bool = False) -> str:
    """Rectangular box in oblique projection (depth drawn at 30°, half scale); hidden edges dashed."""
    dx, dy = w * 0.5 * math.cos(math.radians(30)), w * 0.5 * math.sin(math.radians(30))
    p = {  # front face corners, then back face corners
        "f00": (0, 0), "f10": (l, 0), "f11": (l, h), "f01": (0, h),
        "b00": (dx, dy), "b10": (l + dx, dy), "b11": (l + dx, h + dy), "b01": (dx, h + dy),
    }
    f = Fig(size=210, max_height=150)
    f.poly([p["f00"], p["f10"], p["f11"], p["f01"]])
    f.poly([p["f01"], p["b01"], p["b11"], p["f11"]], closed=False)
    f.line(p["f10"], p["b10"]).line(p["b10"], p["b11"])
    for a, b in (("f00", "b00"), ("b00", "b10"), ("b00", "b01")):
        f.line(p[a], p[b], dash=True, color=GRAY, width=1.1)
    if diagonal:  # the unknown, marked x
        f.line(p["f00"], p["b11"], dash=True, width=1.6)
        mid = ((p["f00"][0] + p["b11"][0]) / 2, (p["f00"][1] + p["b11"][1]) / 2)
        f.text(mid, "x", dx=-4, dy=-6, italic=True)
    centre = ((l + dx) / 2, (h + dy) / 2)
    f.seg_label(p["f00"], p["f10"], label_l, away=centre)
    f.seg_label(p["f10"], p["b10"], label_w, away=centre)
    f.seg_label(p["f00"], p["f01"], label_h, away=centre)
    return f.svg()


def coordinate_line(p: tuple[int, int], q: tuple[int, int], *, span: int = 8) -> str:
    """Coordinate plane with the line through lattice points p and q, both marked."""
    g = Graph(-span, span, -span, span, width=210, height=210, label_every=2, plane=True)
    g.line_through(p, q).point(p).point(q)
    return g.svg()


# ---- previews of figures for upcoming Geometry topics (parallel lines, circles, solids)

def parallel_lines(theta: float, labels: dict[int, str]) -> str:
    """Two horizontal parallel lines cut by a transversal rising to the right at ``theta`` degrees.
    Angle positions 1–4 at the top intersection and 5–8 at the bottom, numbered clockwise
    from upper-left: positions 2, 4, 6 and 8 measure theta; 1, 3, 5 and 7 measure 180 − theta."""
    t = math.radians(theta)
    d = (math.cos(t), math.sin(t))
    top, bot = (1.0 / math.tan(t), 1.0), (0.0, 0.0)
    f = Fig(size=220, max_height=150)
    for y in (0.0, 1.0):
        f.line((-1.6, y), (2.4, y))
    f.line((bot[0] - d[0] * 0.8, bot[1] - d[1] * 0.8), (top[0] + d[0] * 0.8, top[1] + d[1] * 0.8))
    f.text((2.4, 1.0), "ℓ", dx=8, dy=4, anchor="start", italic=True).text((2.4, 0.0), "m", dx=8, dy=4, anchor="start", italic=True)
    for k, label in labels.items():
        v = top if k <= 4 else bot
        quadrant = (k - 1) % 4  # 0 upper-left, 1 upper-right, 2 lower-right, 3 lower-left
        ray_line = {0: (-1, 0), 1: (1, 0), 2: (1, 0), 3: (-1, 0)}[quadrant]
        ray_tr = {0: d, 1: d, 2: (-d[0], -d[1]), 3: (-d[0], -d[1])}[quadrant]
        f.angle(v, (v[0] + ray_line[0], v[1]), (v[0] + ray_tr[0] * 0.5, v[1] + ray_tr[1] * 0.5), label,
                r_px=16, italic=not label[:1].isdigit())
    return f.svg()


def circle_angles(central: float, *, inscribed: bool = True, labels: dict[str, str] | None = None) -> str:
    """Circle with a central angle over arc AB and (optionally) an inscribed angle on the same arc."""
    labels = labels or {}
    a0, a1 = -central / 2 - 90, central / 2 - 90
    A = (math.cos(math.radians(a0)), math.sin(math.radians(a0)))
    B = (math.cos(math.radians(a1)), math.sin(math.radians(a1)))
    O, P = (0.0, 0.0), (0.0, 1.0)
    f = Fig(size=160, max_height=160)
    f.circle(O, 1).dot(O)
    f.line(O, A).line(O, B)
    f.text(A, "A", dx=-6, dy=10, anchor="end").text(B, "B", dx=6, dy=10, anchor="start")
    f.text(O, "O", dx=-8, dy=4, anchor="end")
    f.angle(O, A, B, labels.get("central", ""), r_px=18, italic=False)
    if inscribed:
        f.line(P, A).line(P, B).dot(P)
        f.text(P, "P", dy=-8)
        f.angle(P, A, B, labels.get("inscribed", ""), r_px=26, italic=False)
    if "arc" in labels:
        mid = (math.cos(math.radians(-90)), math.sin(math.radians(-90)))
        f.text(mid, labels["arc"], dy=16)
    return f.svg()


def cylinder(r: float, h: float, label_r: str, label_h: str) -> str:
    f = Fig(size=140, max_height=160)
    ry = r * 0.3
    _ellipse(f, (0, h), r, ry)
    _ellipse(f, (0, 0), r, ry, hidden_back=True)
    f.line((-r, 0), (-r, h)).line((r, 0), (r, h))
    f.line((0, h), (r, h), dash=True).dot((0, h))
    f.text((r / 2, h + ry), label_r, dy=-5)
    f.text((r, h / 2), label_h, dx=6, anchor="start")
    return f.svg()


def cone(r: float, h: float, label_r: str, label_h: str) -> str:
    f = Fig(size=140, max_height=160)
    _ellipse(f, (0, 0), r, r * 0.3, hidden_back=True)
    f.line((-r, 0), (0, h)).line((r, 0), (0, h))
    f.line((0, 0), (0, h), dash=True).line((0, 0), (r, 0), dash=True).dot((0, 0))
    f.right_angle((0, 0), (r, 0), (0, h), size_px=7)
    f.text((r / 2, -r * 0.3), label_r, dy=14)
    f.text((0, h / 2), label_h, dx=5, anchor="start")
    return f.svg()


def sphere(r: float, label_r: str) -> str:
    f = Fig(size=130, max_height=130)
    f.circle((0, 0), r)
    _ellipse(f, (0, 0), r, r * 0.3, hidden_back=True)
    f.line((0, 0), (r, 0), dash=True).dot((0, 0))
    f.text((r / 2, 0), label_r, dy=-6)
    return f.svg()


def _ellipse(f: Fig, c, rx: float, ry: float, *, hidden_back: bool = False) -> None:
    front = [(c[0] + rx * math.cos(math.radians(a)), c[1] + ry * math.sin(math.radians(a))) for a in range(180, 361, 10)]
    back = [(c[0] + rx * math.cos(math.radians(a)), c[1] + ry * math.sin(math.radians(a))) for a in range(0, 181, 10)]
    f.poly(front, closed=False)
    f.poly(back, closed=False, dash=hidden_back, color=GRAY if hidden_back else INK, width=1.1 if hidden_back else 1.5)


# ======================================================================== physics


def horizontal_launch(h: float, what: str, label_h: str, label_v: str) -> str:
    """A platform/table/cliff of height h with an object leaving its edge horizontally."""
    f = Fig(size=220, max_height=150)
    top_w = max(h * 0.6, 1.0)
    f.poly([(-top_w, 0), (0, 0), (0, h), (-top_w, h)], fill="#eee")
    f.line((-top_w, 0), (h * 1.6, 0)).hatch((-top_w, 0), (h * 1.6, 0))
    f.dot((0, h), r_px=4)
    pts = [(h * 1.2 * t, h * (1 - t * t)) for t in (i / 12 for i in range(13))]
    f.poly(pts, closed=False, dash=True, color=GRAY, width=1.2)
    f.arrow((0, h), (h * 0.45, h))
    f.text((h * 0.45, h), label_v, dx=4, dy=-8, anchor="start")
    f.line((-top_w - h * 0.08, 0), (-top_w - h * 0.08, h), width=1)
    f.text((-top_w - h * 0.08, h / 2), label_h, dx=-6, anchor="end")
    f.text((h * 1.2, 0), "?", dy=16, italic=True)
    f.text((-top_w / 2, h), what, dy=-6, size=11, color=GRAY)
    return f.svg()


def angled_launch(theta: float, label_v: str, label_theta: str) -> str:
    t = math.radians(theta)
    R, H = math.sin(2 * t), math.sin(t) ** 2 / 2
    f = Fig(size=220, max_height=110)
    f.line((-0.05, 0), (R * 1.08, 0)).hatch((-0.05, 0), (R * 1.08, 0))
    pts = [(R * u, 4 * H * u * (1 - u)) for u in (i / 20 for i in range(21))]
    f.poly(pts, closed=False, dash=True, color=GRAY, width=1.2)
    L = 0.32 * max(R, 0.6)
    f.arrow((0, 0), (L * math.cos(t), L * math.sin(t)))
    f.text((L * math.cos(t), L * math.sin(t)), label_v, dx=6, dy=-2, anchor="start")
    f.angle((0, 0), (1, 0), (math.cos(t), math.sin(t)), label_theta, r_px=24, italic=False)
    return f.svg()


def _block(f: Fig, x: float, y: float, w: float, h: float, label: str = "", angle_deg: float = 0) -> tuple[float, float]:
    """A box with its bottom-centre at (x, y), optionally tilted; returns its centre."""
    a = math.radians(angle_deg)
    ux, uy, vx, vy = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    corners = [(x + ux * s * w / 2 + vx * t * h, y + uy * s * w / 2 + vy * t * h) for s, t in ((-1, 0), (1, 0), (1, 1), (-1, 1))]
    f.poly(corners, fill="#f2f2f2")
    cx, cy = x + vx * h / 2, y + vy * h / 2
    if label:
        f.text((cx, cy), label, dy=4, size=12)
    return cx, cy


def pushed_crate(label_f: str, label_mu: str, label_m: str = "") -> str:
    f = Fig(size=210, max_height=90)
    f.line((-1.4, 0), (2.4, 0)).hatch((-1.4, 0), (2.4, 0))
    cx, cy = _block(f, 0.5, 0, 1.0, 0.8, label_m)
    f.arrow((-1.2, cy), (0, cy))
    f.text((-1.2, cy), label_f, dy=-8, anchor="start")
    f.text((1.8, 0), label_mu, dy=-6, size=12)
    return f.svg()


def incline(theta: float, label_theta: str, label_mu: str = "") -> str:
    t = math.radians(theta)
    L = 3.0
    top = (L * math.cos(t), L * math.sin(t))
    f = Fig(size=210, max_height=130)
    f.poly([(0, 0), (top[0], 0), top], fill="#f7f7f7")
    f.hatch((0, 0), (top[0], 0))
    f.angle((0, 0), (1, 0), top, label_theta, r_px=26, italic=False)
    s = 0.62 * L
    _block(f, s * math.cos(t), s * math.sin(t), 0.55, 0.38, "", theta)
    if label_mu:
        f.text((top[0] * 0.3, top[1] * 0.3), label_mu, dx=8, dy=-14, anchor="end", size=12)
    return f.svg()


def atwood(label_1: str, label_2: str, m1: float, m2: float) -> str:
    f = Fig(size=150, max_height=170)
    f.line((-0.8, 3.2), (0.8, 3.2)).hatch((-0.8, 3.2), (0.8, 3.2), below=False)
    f.line((0, 3.2), (0, 2.6))
    f.circle((0, 2.4), 0.4).dot((0, 2.4))
    big = max(m1, m2)
    for x, m, label in ((-0.4, m1, label_1), (0.4, m2, label_2)):
        side = 0.45 + 0.35 * m / big  # heavier mass drawn bigger, and hanging lower
        bottom = 0.8 if m == big else 1.4
        f.line((x, 2.4), (x, bottom + side))
        _block(f, x, bottom, side, side, label)
    return f.svg()


def rope_pull(theta: float, label_f: str, label_theta: str) -> str:
    t = math.radians(theta)
    f = Fig(size=210, max_height=110)
    f.line((-1.2, 0), (2.6, 0)).hatch((-1.2, 0), (2.6, 0))
    cx, cy = _block(f, 0, 0, 1.0, 0.7)
    start = (0.5, cy)
    end = (start[0] + 1.6 * math.cos(t), start[1] + 1.6 * math.sin(t))
    f.arrow(start, end)
    if theta:  # a horizontal pull needs no angle mark
        f.line(start, (start[0] + 0.9, start[1]), dash=True, color=GRAY, width=1)
        f.angle(start, (start[0] + 1, start[1]), end, label_theta, r_px=26, italic=False)
    f.text(end, label_f, dx=5, anchor="start")
    return f.svg()


def collision(label_m1: str, label_v1: str, label_m2: str, label_v2: str, v2_dir: int) -> str:
    """Two carts on a track; v2_dir is +1 (right), -1 (left) or 0 (at rest)."""
    f = Fig(size=230, max_height=90)
    f.line((-0.3, 0), (5.3, 0)).hatch((-0.3, 0), (5.3, 0))
    for x0, label in ((0.4, label_m1), (3.4, label_m2)):
        _block(f, x0 + 0.6, 0.12, 1.2, 0.6, label)
        f.circle((x0 + 0.25, 0.1), 0.1).circle((x0 + 0.95, 0.1), 0.1)
    f.arrow((0.6, 1.05), (1.8, 1.05))
    f.text((1.2, 1.05), label_v1, dy=-8)
    if v2_dir:
        a, b = ((3.6, 1.05), (4.8, 1.05)) if v2_dir > 0 else ((4.8, 1.05), (3.6, 1.05))
        f.arrow(a, b)
        f.text((4.2, 1.05), label_v2, dy=-8)
    else:
        f.text((4.0, 1.05), label_v2, dy=-4, size=12, color=GRAY)
    return f.svg()


def coaster(label_h: str) -> str:
    f = Fig(size=220, max_height=120)
    # a smooth drop from height 2 at x = 0 to the ground at x = 2, then level track
    pts = [(x / 10, math.cos(math.pi * x / 20) + 1 if x <= 20 else 0.0) for x in range(31)]
    f.poly(pts, closed=False, width=2)
    f.line((0, 0), (3.0, 0), color=GRAY, width=1).hatch((0, 0), (3.0, 0))
    _block(f, 0.12, 2.0, 0.24, 0.16)
    f.line((-0.25, 0), (-0.25, 2.0), width=1)
    f.text((-0.25, 1.0), label_h, dx=-6, anchor="end")
    return f.svg()


def free_body(forces: list[tuple[str, float, str]]) -> str:
    """A box with force arrows. forces: (direction 'left'|'right'|'up'|'down', relative length, label)."""
    f = Fig(size=200, max_height=170)
    f.poly([(-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)], fill="#f2f2f2")
    vec = {"right": (1, 0), "left": (-1, 0), "up": (0, 1), "down": (0, -1)}
    for direction, length, label in forces:
        ux, uy = vec[direction]
        start = (ux * 0.4, uy * 0.4)
        end = (start[0] + ux * (0.5 + length), start[1] + uy * (0.5 + length))
        f.arrow(start, end)
        dx, dy = {"right": (6, 4), "left": (-6, 4), "up": (8, 6), "down": (8, -2)}[direction]
        f.text(end, label, dx=dx, dy=dy, anchor="start" if direction in ("right", "up", "down") else "end")
    return f.svg()


def _zigzag(f: Fig, p, q, label: str = "", label_side: int = 1) -> None:
    """Resistor symbol between p and q (horizontal or vertical wire)."""
    (x1, y1), (x2, y2) = p, q
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    nx, ny = -uy, ux
    z = 0.9  # zigzag length
    a = ((x1 + x2) / 2 - ux * z / 2, (y1 + y2) / 2 - uy * z / 2)
    b = ((x1 + x2) / 2 + ux * z / 2, (y1 + y2) / 2 + uy * z / 2)
    f.line(p, a).line(b, q)
    pts = [a] + [(a[0] + ux * z * (i + 0.5) / 6 + nx * 0.18 * (1 if i % 2 == 0 else -1),
                  a[1] + uy * z * (i + 0.5) / 6 + ny * 0.18 * (1 if i % 2 == 0 else -1)) for i in range(6)] + [b]
    f.poly(pts, closed=False)
    if label:
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if abs(ux) > 0.5:
            f.text(mid, label, dy=-14 * label_side if label_side > 0 else 22, size=12)
        else:
            f.text(mid, label, dx=15 * label_side, dy=4, anchor="start" if label_side > 0 else "end", size=12)


def _battery(f: Fig, p, q, label: str) -> None:
    """Cell symbol on a vertical wire from p (bottom) to q (top): long plate = positive, on top."""
    (x, y1), (_, y2) = p, q
    mid = (y1 + y2) / 2
    f.line((x, y1), (x, mid - 0.08)).line((x, mid + 0.08), (x, y2))
    f.line((x - 0.32, mid + 0.08), (x + 0.32, mid + 0.08), width=1.8)
    f.line((x - 0.17, mid - 0.08), (x + 0.17, mid - 0.08), width=3)
    f.text((x - 0.32, mid), label, dx=-6, dy=4, anchor="end", size=12)


def series_circuit(resistor_labels: list[str], battery_label: str) -> str:
    f = Fig(size=230, max_height=130)
    w, h = 4.0, 2.4
    _battery(f, (0, 0), (0, h), battery_label)
    n = len(resistor_labels)
    if n == 2:
        _zigzag(f, (0, h), (w, h), resistor_labels[0])
        _zigzag(f, (w, h), (w, 0), resistor_labels[1], label_side=1)
    else:
        _zigzag(f, (0, h), (w, h), resistor_labels[0])
        _zigzag(f, (w, h), (w, 0), resistor_labels[1], label_side=1)
        _zigzag(f, (w, 0), (0, 0), resistor_labels[2], label_side=-1)
    if n == 2:
        f.line((w, 0), (0, 0))
    return f.svg()


def parallel_circuit(resistor_labels: list[str], battery_label: str) -> str:
    f = Fig(size=230, max_height=130)
    h, gap = 2.4, 1.6
    n = len(resistor_labels)
    right = gap * n
    _battery(f, (0, 0), (0, h), battery_label)
    f.line((0, h), (right, h)).line((0, 0), (right, 0))
    for i, label in enumerate(resistor_labels):
        x = gap * (i + 1)
        _zigzag(f, (x, h), (x, 0), label, label_side=1)
        f.dot((x, h), r_px=2).dot((x, 0), r_px=2)
    return f.svg()


def combo_circuit(label_1: str, label_2: str, label_3: str, battery_label: str) -> str:
    """R1 in series with R2 ∥ R3."""
    f = Fig(size=230, max_height=130)
    h = 2.4
    _battery(f, (0, 0), (0, h), battery_label)
    _zigzag(f, (0, h), (2.6, h), label_1)
    f.line((2.6, h), (4.4, h)).line((0, 0), (4.4, 0))
    _zigzag(f, (2.6, h), (2.6, 0), label_2, label_side=-1)
    _zigzag(f, (4.4, h), (4.4, 0), label_3, label_side=1)
    f.dot((2.6, h), r_px=2).dot((2.6, 0), r_px=2)
    return f.svg()


def lens_diagram(f_len: float, d_obj: float, label_f: str, label_do: str) -> str:
    """Converging lens on the principal axis with both focal points and an object arrow, plus
    dimension lines for the object distance and focal length. The image is the student's to find."""
    F = 2.0
    D = d_obj / f_len * F
    fig = Fig(size=240, max_height=150)
    fig.line((-D - 0.6, 0), (F * 2.2, 0), color=GRAY, width=1)
    fig.arrow((0, 0), (0, 2.0), width=1.6, head=7).arrow((0, 0), (0, -2.0), width=1.6, head=7)
    for x in (-F, F):
        fig.dot((x, 0)).text((x, 0), "F", dy=15, size=12)
    fig.arrow((-D, 0), (-D, 1.3), width=2.2)
    fig.text((-D, 1.3), "object", dy=-6, size=11, color=GRAY)
    y = -2.5  # dimension lines below the axis: object distance on the left, focal length on the right
    for a, b, label in ((-D, 0, label_do), (0, F, label_f)):
        fig.line((a, y), (b, y), width=0.9)
        fig.line((a, y - 0.15), (a, y + 0.15), width=0.9).line((b, y - 0.15), (b, y + 0.15), width=0.9)
        fig.text(((a + b) / 2, y), label, dy=14, size=12)
    return fig.svg()


def refraction(theta: float, label_theta: str, top: str, bottom: str) -> str:
    t = math.radians(theta)
    f = Fig(size=190, max_height=150)
    f.poly([(-1.3, -1.1), (1.3, -1.1), (1.3, 0), (-1.3, 0)], fill=WATER, width=0.0001)
    f.line((-1.3, 0), (1.3, 0))
    f.line((0, 1.1), (0, -1.1), dash=True, color=GRAY, width=1)
    start = (-math.sin(t) * 1.05, math.cos(t) * 1.05)
    f.arrow(start, (0, 0))
    f.angle((0, 0), (0, 1), start, label_theta, r_px=26, italic=False)
    f.text((1.25, 0.15), top, dx=0, dy=-4, anchor="end", size=12, color=GRAY)
    f.text((1.25, -0.15), bottom, dy=12, anchor="end", size=12, color=GRAY)
    return f.svg()


def submerged_block(label: str) -> str:
    f = Fig(size=170, max_height=130)
    f.poly([(0, 0), (3, 0), (3, 2.0), (0, 2.0)], fill=WATER, width=0.0001)
    f.poly([(0, 2.5), (0, 0), (3, 0), (3, 2.5)], closed=False, width=1.8)
    f.line((0, 2.0), (3, 2.0), color="#4a7fb0", width=1)
    _block(f, 1.5, 0.6, 0.9, 0.7, "")
    f.text((1.5, 0.6), label, dy=15, size=12)
    return f.svg()


def motion_graph(points: list[tuple[float, float]], ylabel: str, *, ystep: float = 1, xstep: float = 1) -> str:
    """Piecewise-linear position-time or velocity-time graph through the given points."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ymin = min(0, math.floor(min(ys) / ystep) * ystep)
    ymax = math.ceil(max(ys) / ystep) * ystep + ystep
    every = 1 if (ymax - ymin) / ystep <= 10 else 2
    g = Graph(0, max(xs), ymin, ymax, xstep=xstep, ystep=ystep, width=240, height=170,
              xlabel="t (s)", ylabel=ylabel, label_every=every)
    g.polyline(points)
    return g.svg()
