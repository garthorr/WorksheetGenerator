"""Multiple choice (AP Physics 1 only): one right answer, distinct and believable wrong ones."""

import math
import random
from collections import Counter
from functools import cache

import pytest
import sympy as sp
from fastapi.testclient import TestClient

from app import main, storage
from app.ai import _numbers_in
from app.generators import TOPICS, generate_set
from app.generators.core import supports_mc
from app.generators.mc import SPECS, givens_shown, part_count
from tests.test_quality import LAWS

MC_TOPICS = [t for t in TOPICS if supports_mc(t)]
MC_LEVELS = [(t, lv) for t in MC_TOPICS for lv in sorted(TOPICS[t].variants)]


@cache
def mc_problems(topic, level):
    out = []
    for nice, g in ((False, 9.8), (True, 10)):
        for s in range(6):
            out += generate_set(topic, level, 8, random.Random(f"mc{topic}{level}{nice}{s}"), mc=True, nice=nice, g=g)
    return out


def all_mc():
    return [p for t, lv in MC_LEVELS for p in mc_problems(t, lv)]


def test_multiple_choice_is_ap_physics_1_only():
    assert set(MC_TOPICS) == {t for t in TOPICS if "ap1" in TOPICS[t].courses}
    assert all(TOPICS[t].subject == "physics" for t in MC_TOPICS)
    for topic in ("quadratics", "pythagorean", "circles", "thermal", "circuits", "waves"):
        with pytest.raises(ValueError):
            generate_set(topic, 1, 2, random.Random(1), mc=True)


def test_every_ap1_problem_type_has_a_spec():
    for t in MC_TOPICS:
        for vs in TOPICS[t].variants.values():
            for v in vs:
                assert t == "derivations" or v.fn.__name__ in SPECS, f"{v.fn.__name__} has no multiple-choice spec"


@pytest.mark.parametrize("topic,level", MC_LEVELS, ids=[f"{t}-L{lv}" for t, lv in MC_LEVELS])
def test_one_correct_choice(topic, level):
    for p in mc_problems(topic, level):
        f = p.facts
        assert len(p.choices) == 4 and len(set(p.choices)) == 4, p.choices
        letter = "ABCD"[p.correct]
        assert p.answer.startswith(f"({letter}) ") and p.choices[p.correct] in p.answer, p.answer
        assert "(a)" not in p.question and "(b)" not in p.question, p.question  # one quantity asked
        assert p.solution.strip()
        if f.get("symbolic"):
            exprs = f["mc"]["exprs"]
            assert sp.simplify(exprs[p.correct] - f["answer"]) == 0
            for i, e in enumerate(exprs):
                assert e.free_symbols, e
                for j in range(i):
                    assert sp.simplify(e - exprs[j]) != 0, (e, exprs[j])
            continue
        G, A, key, values = f["given"], f["ans"], f["mc"]["key"], f["mc"]["values"]
        drawn = {k: f[k] for k in ("graph", "forces", "inertia") if k in f}
        assert LAWS[f["variant"]]({**G, **drawn}, A, f["g"])  # the keyed answer is the checked one
        assert values == sorted(values) and values[p.correct] == A[key]
        correct = A[key]
        for i, (v, text) in enumerate(zip(values, p.choices)):
            assert any(math.isclose(n, v, rel_tol=0.006, abs_tol=1e-9) for n in _numbers_in(text)), (v, text)
            if i != p.correct:
                assert abs(v - correct) >= 0.04 * abs(correct) - 1e-12, (values, correct)
        assert givens_shown(p.question, G), p.question


def test_letters_are_spread_evenly():
    counts = Counter(p.correct for p in all_mc())
    total = sum(counts.values())
    assert all(0.15 <= counts[k] / total <= 0.35 for k in range(4)), counts


def test_wrong_choices_mostly_come_from_real_mistakes():
    real = total = 0
    for p in all_mc():
        f = p.facts
        if f.get("symbolic"):
            continue
        key = f["mc"]["key"]
        part = SPECS[f["variant"]](f["given"], f["ans"], f["g"], f)[key]
        mistakes = [m for m in part.wrong if m is not None] + ([-f["ans"][key]] if part.signed else [])
        for i, v in enumerate(f["mc"]["values"]):
            if i != p.correct:
                total += 1
                real += any(math.isclose(v, m, rel_tol=1e-9) for m in mistakes)
    assert real / total >= 0.6, f"only {real / total:.0%} of wrong choices come from modeled mistakes"


def test_multi_part_answers_match_their_parts():
    """Asking one part relies on the answers being listed in (a), (b), (c) order."""
    for t in MC_TOPICS:
        for level in TOPICS[t].variants:
            for p in generate_set(t, level, 10, random.Random(level)):
                n = part_count(p.question)
                if n:
                    assert n == len(p.facts["ans"]), (p.facts["variant"], p.question)


def test_whole_number_mode_keeps_choices_simple():
    """When the answer is a simple number, the wrong choices are simple too (no 12 next to 8.49)."""
    from app.generators.core import is_nice
    simple = ok = 0
    for t, lv in MC_LEVELS:
        for p in generate_set(t, lv, 8, random.Random(f"w{t}{lv}"), mc=True, nice=True, g=10):
            values = p.facts["mc"].get("values")
            if values and is_nice(values[p.correct]):
                simple += 1
                ok += all(is_nice(v) for v in values)
    assert ok / simple >= 0.9, f"{ok}/{simple}"


# ------------------------------------------------------------------ API

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "SHEETS", tmp_path / "worksheets")
    monkeypatch.setattr(storage, "SETTINGS_FILE", tmp_path / "settings.json")
    return TestClient(main.app)


def gen(client, **section):
    r = client.post("/api/generate", json={"seed": 3, "sections": [section]})
    assert r.status_code == 200, r.text
    return r.json()["sections"][0]


def test_api_multiple_choice(client):
    topics = {t["id"]: t for t in client.get("/api/topics").json()}
    assert topics["rotation"]["mc"] and topics["kinematics"]["mc"] and not topics["quadratics"]["mc"]
    sec = gen(client, subject="physics", topic="kinematics", count=4, format="mc", course="ap1")
    assert not sec["error"] and all(len(p["choices"]) == 4 and p["correct"] in range(4) for p in sec["problems"])
    free = gen(client, subject="physics", topic="kinematics", count=2)
    assert all(not p["choices"] and p["correct"] is None for p in free["problems"])
    for bad in ({"topic": "quadratics"}, {"topic": "kinematics", "subject": "physics", "course": "conceptual"},
                {"topic": "kinematics", "subject": "physics", "source": "ai"}):
        assert "only for" in gen(client, count=1, format="mc", **bad)["error"], bad
    one = client.post("/api/problem", json={"subject": "physics", "topic": "torque", "format": "mc", "course": "ap1"})
    assert one.status_code == 200 and len(one.json()["choices"]) == 4
