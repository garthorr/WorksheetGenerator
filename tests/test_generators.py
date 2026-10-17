import random

import pytest

from app.ai import _fix_latex, _numbers_in, _parse, _verify
from app.generators import TOPICS, generate
from app.safe_eval import safe_eval


@pytest.mark.parametrize("topic_id", sorted(TOPICS))
@pytest.mark.parametrize("level", [1, 2, 3])
def test_every_topic_generates(topic_id, level):
    rng = random.Random(f"{topic_id}{level}")
    for _ in range(40):
        p = generate(topic_id, level, rng)
        assert p.question and p.answer
        assert p.question.count("$") % 2 == 0, p.question
        assert p.answer.count("$") % 2 == 0, p.answer
        assert "nan" not in p.answer.lower()


def test_seed_is_reproducible():
    a = [generate("quadratics", 2, random.Random(7)).question for _ in range(3)]
    b = [generate("quadratics", 2, random.Random(7)).question for _ in range(3)]
    assert a == b


def test_safe_eval():
    assert safe_eval("v0**2/(2*a)", {"v0": 20, "a": 4}) == 50
    assert abs(safe_eval("sin(radians(30))") - 0.5) < 1e-12
    for bad in ["__import__('os')", "().__class__", "open('x')", "9**9**9**9"]:
        with pytest.raises(Exception):
            safe_eval(bad)


def test_verify_and_parse():
    ok, _ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*m*v**2", "answer_value": 9,
                     "answer": "$KE = 9.0\\,\\mathrm{J}$"})
    text_bad, _ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*m*v**2", "answer_value": 9,
                           "answer": "12 J"})
    attr, _ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*given.m*given['v']**2",
                       "answer_value": 9, "answer": "9 J"})
    assert (text_bad, attr) == ("fail", "pass")
    bad, _ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*m*v**2", "answer_value": 18})
    err, _ = _verify({"given": {"m": 2}, "answer_formula": "0.5*m*v**2", "answer_value": 9})
    none, _ = _verify({"given": {}, "answer_formula": "", "answer_value": None})
    assert (ok, bad, err, none) == ("pass", "fail", "error", "nonnumeric")
    items = _parse('```json\n{"problems": [{"question": "$\\frac{1}{2}$"}]}\n```')
    assert _fix_latex(items[0]["question"]) == "$\\frac{1}{2}$"


def test_numbers_in():
    assert _numbers_in(r"$3.2 \times 10^{4}\,\mathrm{N}$")[0] == 32000
    assert _numbers_in(r"$x = \frac{3}{4}$") == [0.75]
    assert _numbers_in("1,500 J") == [1500]


def test_unbalanced_dollar_repaired():
    assert _fix_latex("$24.00 feet") == "24.00 feet"
    assert _fix_latex("$x = 3$ and $$y$$") == "$x = 3$ and $$y$$"
    assert _fix_latex(r"costs \$5") == r"costs \$5"
