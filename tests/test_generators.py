import random

import pytest

import asyncio
import json

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

    async def fake_chat(settings, messages, fmt):
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
