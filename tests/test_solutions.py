"""Worked solutions: present, consistent with the answer, and built from the givens."""

import random

import pytest

from app.ai import _numbers_in
from app.generators import TOPICS, generate_set
from app.generators.core import num, sig

LEVELS = [(t, lv) for t in TOPICS for lv in sorted(TOPICS[t].variants)]
NO_STEPS = {"add_sub", "mul_div"}  # whole-number arithmetic: the answer is the work


def problems(topic, level):
    out = []
    for form, nice in (("both", False), ("decimal", True), ("exact", False)):
        out += generate_set(topic, level, 8, random.Random(f"s{topic}{level}{form}"), form=form, nice=nice, g=10 if nice else 9.8)
    return out


@pytest.mark.parametrize("topic,level", LEVELS, ids=[f"{t}-L{lv}" for t, lv in LEVELS])
def test_solutions_reach_the_answer(topic, level):
    for p in problems(topic, level):
        if topic in NO_STEPS:
            continue
        assert p.solution.strip(), f"no worked solution: {p.question}"
        sol_nums = _numbers_in(p.solution)
        for n in _numbers_in(p.answer):
            assert any(abs(n - m) <= 1e-9 * max(1, abs(n)) for m in sol_nums), \
                f"answer value {n} never appears in the steps:\n  {p.answer}\n  {p.solution}"


@pytest.mark.parametrize("topic,level", [(t, lv) for t, lv in LEVELS if TOPICS[t].subject == "physics"],
                         ids=[f"{t}-L{lv}" for t, lv in LEVELS if TOPICS[t].subject == "physics"])
def test_physics_steps_use_the_givens(topic, level):
    for p in problems(topic, level):
        for k, val in p.facts["given"].items():
            if val == 0 or k == "n":
                continue
            assert num(abs(val)) in p.solution or sig(abs(val), 3) in p.solution, \
                f"given {k} = {val} isn't used in the steps: {p.solution}"
        assert len(p.solution.splitlines()) >= 2, p.solution
