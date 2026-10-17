"""A small SVG drawing kit for worksheet figures.

Figures are drawn from a problem's own numbers: they label the givens and mark the
unknown with x, θ or ? — never the answer. Shapes are built in "world" units (y up),
then scaled to fit; labels, angle marks and arrowheads are sized in screen pixels so
they look the same in every figure. The viewBox is computed from everything drawn
(including estimated label sizes), so nothing is clipped.

The SVG is shown with <img src="data:image/svg+xml,..."> in the GUI, so it can never
run script even if a saved worksheet were tampered with.
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

INK = "#111"
GRAY = "#666"
LIGHT = "#d9d9d9"
WATER = "#dcebf7"
FONT = "Georgia, 'Times New Roman', serif"
STROKE = 1.5
FONT_SIZE = 13
DISPLAY_SCALE = 1.15  # figures are drawn at this multiple of their natural size, to sit well next to 12 pt text

Pt = tuple[float, float]


def _sub(a: Pt, b: Pt) -> Pt:
    return a[0] - b[0], a[1] - b[1]


def _unit(v: Pt) -> Pt:
    n = math.hypot(*v) or 1.0
    return v[0] / n, v[1] / n


def _text_box(x: float, y: float, s: str, size: float, anchor: str) -> tuple[float, float, float, float]:
    w = 0.58 * size * len(s)
    x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
    return x0, y - size * 0.8, x0 + w, y + size * 0.25


def label_value(value: float | str, unit: str = "") -> str:
    """Plain-text label like '12 cm' or '0.5 m/s'."""
    if isinstance(value, str):
        return value
    v = float(value)
    s = str(int(v)) if v.is_integer() else f"{v:g}"
    return f"{s} {unit}".strip()


class Fig:
    """Collects shapes in world coordinates and renders them to SVG."""

    def __init__(self, size: float = 220, max_height: float = 170, min_scale: float | None = None):
        self.size, self.max_height, self.min_scale = size, max_height, min_scale
        self.items: list[tuple] = []

    # ---------------------------------------------------------------- shapes (world units)
    def line(self, p: Pt, q: Pt, *, dash: bool = False, width: float = STROKE, color: str = INK) -> Fig:
        self.items.append(("line", p, q, dash, width, color))
        return self

    def poly(self, pts: list[Pt], *, closed: bool = True, fill: str = "none", dash: bool = False,
             width: float = STROKE, color: str = INK) -> Fig:
        self.items.append(("poly", list(pts), closed, fill, dash, width, color))
        return self

    def circle(self, c: Pt, r: float, *, fill: str = "none", dash: bool = False, width: float = STROKE) -> Fig:
        self.items.append(("circle", c, r, fill, dash, width))
        return self

    def arc(self, c: Pt, r: float, a0: float, a1: float, *, dash: bool = False, width: float = STROKE) -> Fig:
        """Arc counterclockwise from angle a0 to a1 (degrees)."""
        if a1 < a0:
            a1 += 360
        n = max(8, int((a1 - a0) / 6))
        pts = [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
        return self.poly(pts, closed=False, dash=dash, width=width)

    def dot(self, p: Pt, r_px: float = 2.6, color: str = INK) -> Fig:
        self.items.append(("dot", p, r_px, color))
        return self

    def arrow(self, p: Pt, q: Pt, *, width: float = 1.8, color: str = INK, head: float = 9) -> Fig:
        """A vector from p to q with an arrowhead at q (force, velocity, ray)."""
        self.items.append(("arrow", p, q, width, color, head))
        return self

    # ---------------------------------------------------------------- annotations (pixel offsets)
    def text(self, p: Pt, s: str, *, dx: float = 0, dy: float = 0, anchor: str = "middle", italic: bool = False,
             size: float = FONT_SIZE, color: str = INK) -> Fig:
        self.items.append(("text", p, s, dx, dy, anchor, italic, size, color))
        return self

    def seg_label(self, p: Pt, q: Pt, s: str, *, away: Pt | None = None, gap: float = 9,
                  italic: bool = False) -> Fig:
        """Label beside segment pq, on the side away from point ``away`` (e.g. the shape's centre)."""
        self.items.append(("seglabel", p, q, s, away, gap, italic))
        return self

    def right_angle(self, v: Pt, a: Pt, b: Pt, size_px: float = 9) -> Fig:
        self.items.append(("rightangle", v, a, b, size_px))
        return self

    def angle(self, v: Pt, a: Pt, b: Pt, label: str = "", *, r_px: float = 20, italic: bool = True,
              arcs: int = 1) -> Fig:
        """Arc marking the angle between rays v→a and v→b, with a label at its bisector."""
        self.items.append(("angle", v, a, b, label, r_px, italic, arcs))
        return self

    def ticks(self, p: Pt, q: Pt, n: int = 1) -> Fig:
        """Congruence tick marks across the middle of segment pq."""
        self.items.append(("ticks", p, q, n))
        return self

    def hatch(self, p: Pt, q: Pt, *, below: bool = True) -> Fig:
        """Ground hatching along pq (a surface)."""
        self.items.append(("hatch", p, q, below))
        return self

    # ---------------------------------------------------------------- render
    def _world_points(self):
        for it in self.items:
            k = it[0]
            if k in ("line", "arrow"):
                yield it[1]
                yield it[2]
            elif k == "poly":
                yield from it[1]
            elif k == "circle":
                (cx, cy), r = it[1], it[2]
                yield cx - r, cy - r
                yield cx + r, cy + r
            elif k in ("dot", "text"):
                yield it[1]

    def svg(self) -> str:
        pts = list(self._world_points())
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        dx, dy = (maxx - minx) or 1.0, (maxy - miny) or 1.0
        s = min(self.size / dx, self.max_height / dy)
        if self.min_scale:
            s = max(s, self.min_scale)

        def T(p: Pt) -> Pt:
            return (p[0] - minx) * s, (maxy - p[1]) * s

        out: list[str] = []
        box = [math.inf, math.inf, -math.inf, -math.inf]

        def grow(x0, y0, x1=None, y1=None):
            x1 = x0 if x1 is None else x1
            y1 = y0 if y1 is None else y1
            box[0], box[1] = min(box[0], x0, x1), min(box[1], y0, y1)
            box[2], box[3] = max(box[2], x0, x1), max(box[3], y0, y1)

        def stroke_attrs(dash, width, color=INK):
            d = ' stroke-dasharray="5 4"' if dash else ""
            return f'stroke="{color}" stroke-width="{width}"{d} stroke-linecap="round" stroke-linejoin="round"'

        def put_text(x, y, s_, anchor, italic, size, color=INK):
            style = ' font-style="italic"' if italic else ""
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}"{style} '
                       f'fill="{color}" stroke="#fff" stroke-width="3" paint-order="stroke">{escape(s_)}</text>')
            grow(*_text_box(x, y, s_, size, anchor))

        def label_at(x, y, nx, ny, s_, italic, size=FONT_SIZE):
            """Place text so it sits on the side of (x, y) that the unit vector (nx, ny) points to."""
            anchor = "start" if nx > 0.35 else "end" if nx < -0.35 else "middle"
            base = y + (size * 0.8 if ny > 0.35 else -3 if ny < -0.35 else size * 0.35)
            put_text(x, base, s_, anchor, italic, size)

        for it in self.items:
            k = it[0]
            if k == "line":
                (x1, y1), (x2, y2) = T(it[1]), T(it[2])
                out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {stroke_attrs(*it[3:6])}/>')
                grow(x1, y1, x2, y2)
            elif k == "poly":
                sp_ = [T(p) for p in it[1]]
                tag = "polygon" if it[2] else "polyline"
                coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in sp_)
                out.append(f'<{tag} points="{coords}" fill="{it[3]}" {stroke_attrs(it[4], it[5], it[6])}/>')
                for x, y in sp_:
                    grow(x, y)
            elif k == "circle":
                (cx, cy), r = T(it[1]), it[2] * s
                out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{it[3]}" {stroke_attrs(it[4], it[5])}/>')
                grow(cx - r, cy - r, cx + r, cy + r)
            elif k == "dot":
                (cx, cy), r, color = T(it[1]), it[2], it[3]
                out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}"/>')
                grow(cx - r, cy - r, cx + r, cy + r)
            elif k == "arrow":
                (x1, y1), (x2, y2), width, color, head = T(it[1]), T(it[2]), it[3], it[4], it[5]
                ux, uy = _unit((x2 - x1, y2 - y1))
                bx, by = x2 - ux * head, y2 - uy * head
                out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {stroke_attrs(False, width, color)}/>')
                hx, hy = -uy * head * 0.38, ux * head * 0.38
                out.append(f'<polygon points="{x2:.1f},{y2:.1f} {bx + hx:.1f},{by + hy:.1f} {bx - hx:.1f},{by - hy:.1f}" '
                           f'fill="{color}"/>')
                grow(x1, y1, x2, y2)
                grow(bx + hx, by + hy, bx - hx, by - hy)
            elif k == "text":
                (x, y), s_, ddx, ddy, anchor, italic, size, color = T(it[1]), *it[2:]
                put_text(x + ddx, y + ddy, s_, anchor, italic, size, color)
            elif k == "seglabel":
                p, q, s_, away, gap, italic = it[1:]
                (x1, y1), (x2, y2) = T(p), T(q)
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                ux, uy = _unit((x2 - x1, y2 - y1))
                nx, ny = -uy, ux
                if away is not None:
                    ax, ay = T(away)
                    if (mx - ax) * nx + (my - ay) * ny < 0:
                        nx, ny = -nx, -ny
                label_at(mx + nx * gap, my + ny * gap, nx, ny, s_, italic)
            elif k == "rightangle":
                v, a, b, size = T(it[1]), T(it[2]), T(it[3]), it[4]
                ua, ub = _unit(_sub(a, v)), _unit(_sub(b, v))
                p1 = (v[0] + ua[0] * size, v[1] + ua[1] * size)
                p2 = (p1[0] + ub[0] * size, p1[1] + ub[1] * size)
                p3 = (v[0] + ub[0] * size, v[1] + ub[1] * size)
                out.append(f'<polyline points="{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}" '
                           f'fill="none" {stroke_attrs(False, 1.1)}/>')
            elif k == "angle":
                v, a, b, label, r, italic, arcs = T(it[1]), T(it[2]), T(it[3]), *it[4:]
                ta = math.atan2(a[1] - v[1], a[0] - v[0])
                tb = math.atan2(b[1] - v[1], b[0] - v[0])
                d = (tb - ta + math.pi) % (2 * math.pi) - math.pi  # signed smaller angle
                for j in range(arcs):
                    rr = r + 4 * j
                    pts_ = [(v[0] + rr * math.cos(ta + d * i / 16), v[1] + rr * math.sin(ta + d * i / 16)) for i in range(17)]
                    out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts_)}" fill="none" '
                               f'{stroke_attrs(False, 1.1)}/>')
                    for x, y in pts_:
                        grow(x, y)
                if label:
                    mid = ta + d / 2
                    nx, ny = math.cos(mid), math.sin(mid)
                    if abs(d) < math.radians(40):  # too narrow to fit text inside: put it just outside the vertex
                        label_at(v[0] - nx * 7, v[1] - ny * 7, -nx, -ny, label, italic)
                    else:
                        lr = r + 4 * (arcs - 1) + 6
                        label_at(v[0] + nx * lr, v[1] + ny * lr, nx, ny, label, italic)
            elif k == "ticks":
                (x1, y1), (x2, y2), n = T(it[1]), T(it[2]), it[3]
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                ux, uy = _unit((x2 - x1, y2 - y1))
                for j in range(n):
                    off = (j - (n - 1) / 2) * 4
                    cx, cy = mx + ux * off, my + uy * off
                    out.append(f'<line x1="{cx - uy * 5:.1f}" y1="{cy + ux * 5:.1f}" x2="{cx + uy * 5:.1f}" '
                               f'y2="{cy - ux * 5:.1f}" {stroke_attrs(False, 1.2)}/>')
            elif k == "hatch":
                (x1, y1), (x2, y2), below = T(it[1]), T(it[2]), it[3]
                ux, uy = _unit((x2 - x1, y2 - y1))
                nx, ny = (-uy, ux) if below else (uy, -ux)
                if ny < 0:
                    nx, ny = -nx, -ny
                length = math.hypot(x2 - x1, y2 - y1)
                for j in range(int(length // 8) + 1):
                    px, py = x1 + ux * j * 8, y1 + uy * j * 8
                    qx, qy = px + nx * 6 - ux * 5, py + ny * 6 - uy * 5
                    out.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{qx:.1f}" y2="{qy:.1f}" {stroke_attrs(False, 0.9, GRAY)}/>')
                    grow(qx, qy)

        m = 4
        x0, y0, x1, y1 = box[0] - m, box[1] - m, box[2] + m, box[3] + m
        w, h = x1 - x0, y1 - y0
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" '
                f'width="{w * DISPLAY_SCALE:.0f}" height="{h * DISPLAY_SCALE:.0f}" font-family="{FONT}">'
                + "".join(out) + "</svg>")


class Graph:
    """A coordinate grid: motion graphs (first quadrant, labelled axes) or a coordinate plane."""

    def __init__(self, xmin: float, xmax: float, ymin: float, ymax: float, *, xstep: float = 1, ystep: float = 1,
                 width: float = 240, height: float = 180, xlabel: str = "", ylabel: str = "",
                 label_every: int = 1, plane: bool = False):
        self.r = (xmin, xmax, ymin, ymax)
        self.step = (xstep, ystep)
        self.W, self.H = width, height
        self.xlabel, self.ylabel, self.label_every, self.plane = xlabel, ylabel, label_every, plane
        self.items: list[tuple] = []

    def px(self, p: Pt) -> Pt:
        xmin, xmax, ymin, ymax = self.r
        return (p[0] - xmin) / (xmax - xmin) * self.W, (ymax - p[1]) / (ymax - ymin) * self.H

    def polyline(self, pts: list[Pt], *, width: float = 2.2) -> Graph:
        self.items.append(("poly", pts, width))
        return self

    def line_through(self, p: Pt, q: Pt) -> Graph:
        """The full line through p and q, clipped to the window."""
        xmin, xmax, ymin, ymax = self.r
        (x1, y1), (x2, y2) = p, q
        if x1 == x2:
            return self.polyline([(x1, ymin), (x1, ymax)], width=1.8)
        m = (y2 - y1) / (x2 - x1)
        cand = [(xmin, y1 + m * (xmin - x1)), (xmax, y1 + m * (xmax - x1))]
        if m:
            cand += [(x1 + (ymin - y1) / m, ymin), (x1 + (ymax - y1) / m, ymax)]
        inside = sorted({(round(x, 9), round(y, 9)) for x, y in cand
                         if xmin - 1e-9 <= x <= xmax + 1e-9 and ymin - 1e-9 <= y <= ymax + 1e-9})
        return self.polyline([inside[0], inside[-1]], width=1.8)

    def point(self, p: Pt, label: str = "") -> Graph:
        self.items.append(("point", p, label))
        return self

    def svg(self) -> str:
        xmin, xmax, ymin, ymax = self.r
        xs, ys = self.step
        out = []
        tick = lambda v: str(int(v)) if float(v).is_integer() else f"{v:g}"  # noqa: E731

        def grid_values(lo, hi, st):
            k0 = math.ceil(lo / st - 1e-9)
            return [round(k * st, 9) for k in range(k0, int(math.floor(hi / st + 1e-9)) + 1)]

        for i, x in enumerate(grid_values(xmin, xmax, xs)):
            X, _ = self.px((x, 0))
            out.append(f'<line x1="{X:.1f}" y1="0" x2="{X:.1f}" y2="{self.H:.1f}" stroke="{LIGHT}" stroke-width="0.8"/>')
        for y in grid_values(ymin, ymax, ys):
            _, Y = self.px((0, y))
            out.append(f'<line x1="0" y1="{Y:.1f}" x2="{self.W:.1f}" y2="{Y:.1f}" stroke="{LIGHT}" stroke-width="0.8"/>')
        # axes: through the origin for a coordinate plane, along the edges for a motion graph
        ax_x = self.px((0, 0))[0] if self.plane else 0
        ax_y = self.px((0, 0))[1] if self.plane or ymin < 0 <= ymax else self.H
        out.append(f'<line x1="0" y1="{ax_y:.1f}" x2="{self.W:.1f}" y2="{ax_y:.1f}" stroke="{INK}" stroke-width="1.3"/>')
        out.append(f'<line x1="{ax_x:.1f}" y1="0" x2="{ax_x:.1f}" y2="{self.H:.1f}" stroke="{INK}" stroke-width="1.3"/>')
        fs = 11
        for i, x in enumerate(grid_values(xmin, xmax, xs)):
            if i % self.label_every or (self.plane and x == 0):
                continue
            X, _ = self.px((x, 0))
            out.append(f'<text class="tick" x="{X:.1f}" y="{ax_y + fs + 3:.1f}" text-anchor="middle" font-size="{fs}" fill="{INK}" '
                       f'stroke="#fff" stroke-width="3" paint-order="stroke">{tick(x)}</text>')
        for i, y in enumerate(grid_values(ymin, ymax, ys)):
            if i % self.label_every or (self.plane and y == 0):
                continue
            _, Y = self.px((0, y))
            out.append(f'<text class="tick" x="{ax_x - 4:.1f}" y="{Y + 4:.1f}" text-anchor="end" font-size="{fs}" fill="{INK}" '
                       f'stroke="#fff" stroke-width="3" paint-order="stroke">{tick(y)}</text>')
        if self.xlabel:  # at the end of the horizontal axis, clear of the plotted line
            out.append(f'<text x="{self.W + 6:.1f}" y="{ax_y + 4:.1f}" text-anchor="start" font-size="12" '
                       f'font-style="italic" fill="{INK}" stroke="#fff" stroke-width="3" paint-order="stroke">'
                       f'{escape(self.xlabel)}</text>')
        if self.ylabel:
            out.append(f'<text x="{ax_x + 4:.1f}" y="-6" text-anchor="start" font-size="12" font-style="italic" '
                       f'fill="{INK}">{escape(self.ylabel)}</text>')
        for it in self.items:
            if it[0] == "poly":
                coords = " ".join(f"{X:.1f},{Y:.1f}" for X, Y in (self.px(p) for p in it[1]))
                out.append(f'<polyline points="{coords}" fill="none" stroke="{INK}" stroke-width="{it[2]}" '
                           'stroke-linejoin="round" stroke-linecap="round"/>')
            elif it[0] == "point":
                X, Y = self.px(it[1])
                out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="3.2" fill="{INK}"/>')
                if it[2]:
                    out.append(f'<text x="{X + 6:.1f}" y="{Y - 6:.1f}" font-size="12" fill="{INK}" stroke="#fff" '
                               f'stroke-width="3" paint-order="stroke">{escape(it[2])}</text>')
        left, top = 34, 22
        right, bottom = (12 + 7 * len(self.xlabel)) if self.xlabel else 10, 22
        w, h = self.W + left + right, self.H + top + bottom
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-left} {-top} {w:.0f} {h:.0f}" '
                f'width="{w * DISPLAY_SCALE:.0f}" height="{h * DISPLAY_SCALE:.0f}" font-family="{FONT}">'
                + "".join(out) + "</svg>")
