import random

import pytest

import asyncio
import json
import re

import httpx

from app import ai
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
    ok, *_ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*m*v**2", "answer_value": 9,
                     "answer": "$KE = 9.0\\,\\mathrm{J}$"})
    text_bad, *_ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*m*v**2", "answer_value": 9,
                           "answer": "12 J"})
    attr, *_ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*given.m*given['v']**2",
                       "answer_value": 9, "answer": "9 J"})
    assert (text_bad, attr) == ("fail", "pass")
    bad, *_ = _verify({"given": {"m": 2, "v": 3}, "answer_formula": "0.5*m*v**2", "answer_value": 18})
    err, *_ = _verify({"given": {"m": 2}, "answer_formula": "0.5*m*v**2", "answer_value": 9})
    none, *_ = _verify({"given": {}, "answer_formula": "", "answer_value": None})
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


def test_ai_text_with_latex_outside_math_is_tidied():
    # real model output: LaTeX in prose, a double-escaped line break, a bare formula answer
    sol = _fix_latex(r"Gravity along the incline is mg\sin(45°), so a = 10 \times 0.707 = 7.1 m/s².\n2) Done")
    assert sol == "Gravity along the incline is mg sin(45°), so a = 10 × 0.707 = 7.1 m/s².\n2) Done"
    assert _fix_latex(r"a = g\sin(45°) = 7.1 m/s^2") == r"$a = g\sin(45^\circ) = 7.1 m/s^2$"
    assert _fix_latex(r"KE = \frac{1}{2}mv^{2} is the energy of the moving cart") == \
        "KE = (1/2)mv² is the energy of the moving cart"
    # proper math and LaTeX commands that start with n are left alone
    assert _fix_latex(r"$\nu = 440$ Hz") == r"$\nu = 440$ Hz"
    assert _fix_latex("400 K") == "400 K"


def test_verify_uses_section_constants():
    item = {"given": {"m": 2}, "answer_formula": "m*g", "answer_value": 20, "answer": "20 N"}
    assert _verify(item)[0] == "error"
    assert _verify(item, {"g": 10})[0] == "pass"


def test_ai_generation_end_to_end(monkeypatch):
    """The whole AI path, prompts included, against a stand-in for Ollama (a brace in the
    prompt once broke str.format and every AI request with it)."""
    sent = {}

    async def fake_chat(settings, messages, fmt, limit=None):
        sent["messages"] = messages
        return json.dumps({"problems": [{
            "question": "A $2\\,\\mathrm{kg}$ cart accelerates at $3\\,\\mathrm{m/s^2}$. Find the net force.",
            "answer": "$F = 6\\,\\mathrm{N}$", "solution": "$F = ma = (2)(3) = 6\\,\\mathrm{N}$",
            "given": {"m": 2, "a": 3}, "answer_formula": "m * a", "answer_value": 6}]})

    monkeypatch.setattr(ai, "_chat", fake_chat)
    settings = {"ollama_url": "http://ollama:11434", "ollama_model": "test", "ai_strict": True}
    probs = asyncio.run(ai.generate_ai(settings, subject="physics", topic="Newton's laws", difficulty=2,
                                       count=1, extra="Use g = 9.8 m/s^2."))
    assert len(probs) == 1 and probs[0].verified is True and "\\mathrm{N}" in probs[0].answer
    system = sent["messages"][0]["content"]
    assert "physics teacher" in system and "\\mathrm{m/s^2}" in system and '{"problems"' in system


def test_numbers_in_survives_huge_exponents():
    """Model-written exponents once overflowed (10^{400}) or hung the server (10^{99999999999})."""
    assert _numbers_in(r"$3 \times 10^{400}\,\mathrm{J}$") == []
    assert 2 in _numbers_in(r"$2 \times 10^{99999999999}$")
    item = {"given": {}, "answer_formula": "3*10**40", "answer_value": 3e40, "answer": r"$3 \times 10^{400}$"}
    assert _verify(item)[0] == "fail"


def test_ollama_failures_become_ai_errors(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(ai, "_thinks", {})
    settings = {"ollama_url": "http://ollama:11434", "ollama_model": "m"}
    formats = []

    def unreachable(request):
        raise httpx.ConnectError("refused")

    def odd_reply(request):
        return httpx.Response(200, json={"nope": 1})

    def old_ollama(request):  # rejects the JSON-schema format; the plain-JSON retry can't connect
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion"]})
        formats.append(json.loads(request.content)["format"])
        if len(formats) == 1:
            return httpx.Response(400, text="invalid format")
        raise httpx.ConnectError("refused")

    for handler, message in ((unreachable, "Could not reach"), (odd_reply, "unexpected response"),
                             (old_ollama, "Could not reach")):
        monkeypatch.setattr(ai.httpx, "AsyncClient",
                            lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
        with pytest.raises(ai.AIError, match=message):
            asyncio.run(ai._request(settings, subject="math", topic="t", difficulty=2, count=1, extra=""))
    assert formats[1] == "json"


def test_think_flag_only_for_thinking_models(monkeypatch):
    """Thinking models get think=false unless the Setup page allows thinking; others never get the flag."""
    real_client = httpx.AsyncClient
    monkeypatch.setattr(ai, "_thinks", {})
    sent, shown = [], []

    def ollama(request):
        if request.url.path == "/api/show":
            model = json.loads(request.content)["model"]
            shown.append(model)
            return httpx.Response(200, json={"capabilities": ["completion"] + ["thinking"] * (model == "qwen3")})
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "{}"}})

    monkeypatch.setattr(ai.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(ollama), **kw))
    for model, think in (("qwen3", False), ("qwen3", True), ("mistral", False)):
        settings = {"ollama_url": "http://ollama:11434", "ollama_model": model, "ai_think": think}
        asyncio.run(ai._chat(settings, [], "json"))
    assert [p.get("think", "absent") for p in sent] == [False, True, "absent"]
    assert shown == ["qwen3", "mistral"]  # capabilities are asked once per model


def test_app_fills_in_the_number():
    """The model writes [[ANSWER]] and a formula; the app computes the number (models slip on arithmetic)."""
    item = {"given": {"v0": 25, "theta_deg": 30}, "answer_formula": "(v0*sin(radians(theta_deg)))**2/(2*g)",
            "answer_value": 7.76, "answer": "$h = [[ANSWER]]\\,\\mathrm{m}$",
            "solution": "$h = \\frac{(25\\sin 30^\\circ)^2}{2(9.8)} = [[ANSWER]]\\,\\mathrm{m}$"}
    status, note, value = _verify(item, {"g": 9.8})
    assert status == "computed" and abs(value - 7.972) < 0.001 and "7.76" in note  # the model's slip, reported
    assert _verify({**item, "answer_value": 7.97}, {"g": 9.8})[0] == "pass"
    assert _verify({**item, "answer_formula": ""})[:3:2] == ("error", 7.76)  # only the model's estimate to show


STORIES = ["A loaded cart rolls down a ramp in the school gym", "A hockey puck slides across the rink after a slap shot",
           "Two dogs pull a sled over packed snow", "An elevator car rises toward the tenth floor",
           "A rowing team drives its boat along a calm river", "A delivery drone climbs away from the warehouse roof",
           "A toy rocket leaves its launch pad", "A bowling ball rolls toward the pins",
           "A shopper shoves a trolley through the parking lot", "A snowmobile tows a skier across a frozen lake",
           "A freight locomotive hauls coal cars out of the yard", "A model glider is pulled into the air by a winch"]


def test_ai_batches_list_earlier_problems_and_fill_answers(monkeypatch):
    calls, made = [], iter(range(100))

    async def fake_chat(settings, messages, fmt, limit=None):
        n = int(re.search(r"Write (\d+) ", messages[1]["content"])[1])
        calls.append((n, messages[1]["content"]))
        return json.dumps({"problems": [{
            "question": f"{STORIES[k % 12]}; its mass is ${k + 2}\\,\\mathrm{{kg}}$. Find the net force on it.",
            "answer": "$F = [[ANSWER]]\\,\\mathrm{N}$", "solution": "$F = ma = [[ANSWER]]\\,\\mathrm{N}$",
            "given": {"m": k + 2, "a": 3}, "answer_formula": "m * a", "answer_value": 999}
            for k in (next(made) for _ in range(n))]})

    monkeypatch.setattr(ai, "_chat", fake_chat)
    settings = {"ollama_url": "http://ollama:11434", "ollama_model": "m", "ai_strict": True}
    probs = asyncio.run(ai.generate_ai(settings, subject="physics", topic="Newton's laws", difficulty=2, count=12,
                                       number=lambda v: f"{v:.1f}"))
    assert [n for n, _ in calls] == [5, 5, 2]
    # The estimate (999) disagrees, so each is kept with the app's number and flagged to check the formula.
    assert len(probs) == 12 and all(p.verified is None for p in probs)
    assert probs[0].answer == "$F = 6.0\\,\\mathrm{N}$" and "[[ANSWER]]" not in probs[0].solution
    assert "must practice the topic above (Newton's laws)" in calls[0][1] and "already exist" not in calls[0][1]
    assert "already exist" in calls[1][1] and "A loaded cart rolls" in calls[1][1]  # later batches see earlier ones


def test_ai_near_duplicates_are_replaced(monkeypatch):
    replies = iter([["A cliff diver runs off a 20 m ledge at 3.0 m/s. How far out does she land?",
                     "A cliff diver runs off a 20 m ledge at 4.0 m/s. How far out does she land?"],
                    ["A golfer chips a ball off a 5.0 m terrace at 8.0 m/s. How long is it in the air?"]])

    async def fake_chat(settings, messages, fmt, limit=None):
        return json.dumps({"problems": [{"question": q, "answer": "an explanation", "solution": "", "given": {},
                                         "answer_formula": "", "answer_value": None} for q in next(replies)]})

    monkeypatch.setattr(ai, "_chat", fake_chat)
    settings = {"ollama_url": "http://ollama:11434", "ollama_model": "m", "ai_strict": False}
    probs = asyncio.run(ai.generate_ai(settings, subject="physics", topic="projectiles", difficulty=2, count=2))
    assert [p.question[:12] for p in probs] == ["A cliff dive", "A golfer chi"]


def test_a_garbled_batch_is_refilled_and_replies_are_capped(monkeypatch):
    replies = iter(['{"problems": [{"question": "A cliff diver runs off a ledge', json.dumps({"problems": [
        {"question": f"{s}. Explain what happens.", "answer": "an explanation", "solution": "", "given": {},
         "answer_formula": "", "answer_value": None} for s in STORIES[:2]]})])
    limits = []

    async def fake_chat(settings, messages, fmt, limit=None):
        limits.append(limit)
        return next(replies)

    monkeypatch.setattr(ai, "_chat", fake_chat)
    settings = {"ollama_url": "http://ollama:11434", "ollama_model": "m", "ai_strict": True}
    probs = asyncio.run(ai.generate_ai(settings, subject="physics", topic="t", difficulty=2, count=2))
    assert len(probs) == 2 and limits == [2 * ai.TOKENS_PER_PROBLEM + 300] * 2


def test_near_copies_fill_in_only_as_a_last_resort(monkeypatch):
    async def fake_chat(settings, messages, fmt, limit=None):
        n = int(re.search(r"Write (\d+) ", messages[1]["content"])[1])
        return json.dumps({"problems": [{"question": f"A cliff diver runs off a 20 m ledge at {k + 3}.0 m/s. How far "
                                                     f"out does she land?", "answer": "x", "solution": "", "given": {},
                                         "answer_formula": "", "answer_value": None} for k in range(n)]})

    monkeypatch.setattr(ai, "_chat", fake_chat)
    settings = {"ollama_url": "http://ollama:11434", "ollama_model": "m", "ai_strict": True}
    probs = asyncio.run(ai.generate_ai(settings, subject="physics", topic="projectiles", difficulty=2, count=3))
    assert len(probs) == 3 and all("Very similar" in p.check_note for p in probs[1:])
