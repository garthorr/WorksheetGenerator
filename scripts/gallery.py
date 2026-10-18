"""Render every figure type to one HTML page for visual review.

    python -m scripts.gallery out.html

Figures are embedded exactly as the GUI shows them (<img src="data:image/svg+xml,...">).
"""

import sys
from urllib.parse import quote

from app.generators import drawings as d

FIGURES = {
    "Right triangle (Pythagorean)": d.right_triangle(9, 12, label_a="9 ft", label_b="x", label_c="15 ft"),
    "Right triangle (trig)": d.right_triangle(12, 7, label_a="12 cm", label_b="x", angle_at="base", angle_label="30°"),
    "Right triangle (find θ)": d.right_triangle(8, 5, label_a="8 m", label_b="5 m", angle_at="base", angle_label="θ"),
    "Rectangle": d.rectangle(12, 7, "12 cm", "7 cm"),
    "Triangle (base & height)": d.triangle_base_height(14, 9, "14 in", "9 in"),
    "Trapezoid": d.trapezoid(8, 18, 7, "8 cm", "18 cm", "7 cm"),
    "Circle (radius)": d.circle(5, "5 m"),
    "Circle (diameter)": d.circle(5, "10 cm", diameter=True),
    "Window": d.window(36, 48, "36 in", "48 in"),
    "Stadium": d.stadium(100, 60, "100 m", "60 m"),
    "Box with diagonal": d.box(12, 8, 6, "12 in", "8 in", "6 in", diagonal=True),
    "Coordinate plane": d.coordinate_line((-3, -2), (4, 5)),
    "Parallel lines": d.parallel_lines(62, {2: "62°", 6: "x"}),
    "Parallel lines (algebra)": d.parallel_lines(115, {3: "(3x + 20)°", 5: "(5x − 4)°"}),
    "Triangle angles": d.triangle(48, 71, angle_labels={"A": "48°", "B": "71°", "C": "x"}, vertex_names="ABC"),
    "Exterior angle": d.triangle(55, 70, angle_labels={"A": "(x + 18)°", "C": "30°"}, exterior_at_B="(4x − 6)°",
                                 vertex_names="ABC"),
    "Regular polygon": d.regular_polygon(8),
    "45-45-90": d.right_triangle(7, 7, label_a="7 cm", label_c="x", angle_at="base", angle_label="45°"),
    "30-60-90": d.right_triangle(10.39, 6, label_b="6 in", label_a="x", label_c="y", angle_at="base", angle_label="30°"),
    "Similar triangles": d.similar_triangles(8, 6, 60, 1.5, {"c": "8", "b": "6"}, {"c": "12", "b": "x"}),
    "Side splitter": d.side_splitter({"CD": "4", "DA": "6", "CE": "5", "EB": "x"}),
    "Classify (coordinate plane)": d.plane_polygon([(-5, -1), (-2, 0), (-6, 2)]),
    "Circle angles": d.circle_angles(100, labels={"central": "100°", "inscribed": "x"}),
    "Circle (arc)": d.circle_angles(140, labels={"arc": "x", "inscribed": "70°"}),
    "Sector": d.sector(135, "8 cm", "135°"),
    "Sector (reflex)": d.sector(270, "5 cm", "270°"),
    "Intersecting chords": d.chords({"AE": "6", "EB": "3", "CE": "9", "ED": "x"}),
    "Box": d.box(7, 3, 9, "7 in", "3 in", "9 in"),
    "Cylinder": d.cylinder(3, 7, "3 cm", "7 cm"),
    "Cone": d.cone(4, 9, "4 in", "9 in"),
    "Sphere": d.sphere(6, "6 m"),
    "Law of sines": d.triangle(46, 37, angle_labels={"A": "46°", "B": "37°"}, side_labels={"a": "20", "b": "x"},
                               vertex_names="ABC"),
    "Law of cosines (angle)": d.triangle(36.3, 92.4, angle_labels={"C": "θ"}, side_labels={"a": "18", "b": "19", "c": "16"},
                                         vertex_names="ABC"),
    "Obtuse triangle": d.triangle(20, 135, angle_labels={"B": "135°"}, side_labels={"a": "7", "c": "12", "b": "x"},
                                  vertex_names="ABC"),
    "Horizontal launch": d.horizontal_launch(20, "cliff", "20 m", "16 m/s"),
    "Angled launch": d.angled_launch(37, "20 m/s", "37°"),
    "Pushed crate": d.pushed_crate("150 N", "μk = 0.25", "40 kg"),
    "Incline": d.incline(30, "30°", "μk = 0.2"),
    "Atwood machine": d.atwood("3 kg", "5 kg", 3, 5),
    "Rope pull": d.rope_pull(30, "80 N", "30°"),
    "Collision": d.collision("1200 kg", "15 m/s", "900 kg", "5 m/s", -1),
    "Collision (target at rest)": d.collision("2 kg", "4 m/s", "3 kg", "at rest", 0),
    "Coaster": d.coaster("45 m"),
    "Free-body diagram": d.free_body([("right", 1.2, "60 N"), ("left", 0.6, "25 N"), ("up", 1.0, "98 N"), ("down", 1.0, "98 N")]),
    "Series circuit": d.series_circuit(["12 Ω", "20 Ω", "8 Ω"], "9 V"),
    "Parallel circuit": d.parallel_circuit(["10 Ω", "15 Ω", "30 Ω"], "12 V"),
    "Combination circuit": d.combo_circuit("R₁ = 4 Ω", "R₂ = 6 Ω", "R₃ = 12 Ω", "24 V"),
    "Lens": d.lens_diagram(10, 25, "f = 10 cm", "25 cm"),
    "Refraction": d.refraction(40, "40°", "air", "water"),
    "Submerged block": d.submerged_block("ρ = 2700 kg/m³"),
    "Seesaw": d.beam(6, [3], [(1.6, "40 kg", ""), (4.6, "35 kg", "")], dims=[(1.6, 3, "1.4 m"), (3, 4.6, "x")]),
    "Beam on two supports": d.beam(4, [0, 4], [(3, "60 kg", "")], dims=[(0, 3, "3 m"), (0, 4, "4 m")]),
    "Pulley with mass": d.pulley_mass("8 kg", "3 kg"),
    "Mass on a spring": d.spring_block("k = 200 N/m", "0.5 kg"),
    "Pendulum": d.pendulum("1.2 m"),
    "Velocity-time graph": d.motion_graph([(0, 0), (4, 12), (8, 12), (10, 0)], "v (m/s)", ystep=2, xstep=1),
    "Position-time graph": d.motion_graph([(0, 0), (3, 9), (5, 9), (8, -3)], "x (m)", ystep=3),
}


def main(out: str, zoom: float = 1) -> None:
    cards = "".join(
        f'<figure><img src="data:image/svg+xml;charset=utf-8,{quote(svg)}" alt="{name}"><figcaption>{name}</figcaption></figure>'
        for name, svg in FIGURES.items())
    img_css = "img{max-width:100%}" if zoom == 1 else "img{width:100%}"  # zoom: wider columns, figures fill them
    css = ("body{font-family:system-ui;margin:16px;background:#f3f4f7}"
           f"main{{display:grid;grid-template-columns:repeat(auto-fill,minmax({260 * zoom:.0f}px,1fr));gap:14px}}"
           "figure{background:#fff;margin:0;padding:12px;border:1px solid #ddd;border-radius:8px;text-align:center}"
           + img_css + "figcaption{font-size:12px;color:#555;margin-top:6px}")
    html = (f"<!doctype html><meta charset=utf-8><title>Figure gallery</title><style>{css}</style>"
            f"<h1>Figure gallery</h1><main>{cards}</main>")
    with open(out, "w") as fh:
        fh.write(html)
    print(f"wrote {len(FIGURES)} figures to {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gallery.html", zoom=float(sys.argv[2]) if len(sys.argv) > 2 else 1)
