"""Figures: valid SVG, consistent with the question, and never giving away the answer."""

import random
import re
import xml.etree.ElementTree as ET
from functools import cache

import pytest

from app.ai import _numbers_in
from app.generators import TOPICS, generate_set

SVG = "{http://www.w3.org/2000/svg}"

# Problem types that should always come with a figure.
EXPECTED = {
    "_pyth_hyp", "_pyth_leg", "_pyth_radical", "_pyth_box", "_area_rect", "_perim_rect", "_area_tri",
    "_area_circle", "_circumference", "_area_trap", "_area_window", "_area_track", "_slope_graph",
    "_slope_graph_eq", "_trig_angle", "_proj_horiz_range", "_proj_horiz_full", "_proj_angle", "_newton_fbd",
    "_newton_fbd_2d", "_newton_friction", "_newton_incline", "_newton_atwood", "_energy_work_angle",
    "_energy_coaster", "_mom_inelastic", "_mom_elastic", "_circ_series", "_circ_parallel", "_circ_combo",
    "_snell", "_lens", "_buoyancy", "_kin_xt_graph", "_kin_vt_graph", "_kin_vt_graph_signed",
}


@cache
def all_problems():
    out = []
    for topic, t in TOPICS.items():
        for level in t.variants:
            for nice in (False, True):
                out += generate_set(topic, level, 12, random.Random(f"fig{topic}{level}{nice}"),
                                    g=10 if nice else 9.8, nice=nice)
    return out


def with_figures():
    return [p for p in all_problems() if p.figure]


def labels(svg: str) -> list[str]:
    """Text labels in a figure, excluding graph tick marks."""
    root = ET.fromstring(svg)
    return [t.text or "" for t in root.iter(f"{SVG}text") if t.get("class") != "tick"]


def test_figures_are_valid_svg():
    assert len(with_figures()) > 300
    for p in with_figures():
        root = ET.fromstring(p.figure)
        assert root.tag == f"{SVG}svg"
        x, y, w, h = map(float, root.get("viewBox").split())
        assert 40 < w < 400 and 30 < h < 400, (p.facts["variant"], w, h)
        assert "<script" not in p.figure and "href" not in p.figure


def test_expected_problem_types_have_figures():
    seen = {p.facts["variant"] for p in with_figures()}
    missing = EXPECTED - seen
    assert not missing, f"no figure for {missing}"
    # trig sides are lambdas; check them by skill instead
    assert any(p.skill.startswith("find_a_side") for p in with_figures())


def test_figure_numbers_come_from_the_question():
    """A figure only repeats what the question says — except problems that are read off the figure."""
    for p in with_figures():
        if p.facts.get("figure_required"):
            continue
        q_nums = _numbers_in(p.question.replace("{,}", ""))
        for text in labels(p.figure):
            for n in _numbers_in(text.replace("₁", "").replace("₂", "").replace("₃", "")):
                assert any(abs(n - m) < 1e-9 for m in q_nums), f"{n} in figure but not in question: {p.question}"


def test_figures_never_show_the_answer():
    def among(v, nums):
        return any(abs(v - n) < 1e-6 * max(1, abs(v)) for n in nums)

    for p in with_figures():
        q_nums = _numbers_in(p.question)
        fig_nums = [n for text in labels(p.figure) for n in _numbers_in(text)]
        ans = p.facts.get("ans")
        for v in (ans.values() if isinstance(ans, dict) else []):
            if isinstance(v, (int, float)) and abs(v) > 1e-9 and not among(v, q_nums):  # a given may equal the answer
                assert not among(v, fig_nums), f"figure reveals answer {v}: {p.question}"
        if p.topic in ("pythagorean", "trig_right"):  # the side or angle asked for is marked x or θ
            assert {"x", "θ"} & set(labels(p.figure)), f"figure doesn't mark the unknown: {p.question}"


def test_turning_figures_off_keeps_only_required_ones():
    for topic in ("pythagorean", "slope", "newton", "kinematics", "circuits"):
        for level in TOPICS[topic].variants:
            for p in generate_set(topic, level, 10, random.Random(level), figures=False):
                assert bool(p.figure) == bool(p.facts.get("figure_required")), p.question


def test_topic_figure_flags_match():
    has = {p.topic for p in with_figures()}
    for t in TOPICS.values():
        assert t.figures == (t.id in has), f"{t.id}: figures flag is {t.figures}"


def test_gallery_figures_parse():
    from scripts.gallery import FIGURES
    for name, svg in FIGURES.items():
        ET.fromstring(svg)
