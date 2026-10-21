"""API behaviour: courses, skills, answer forms and option defaults; login and request guards."""

import json

import pytest
from fastapi.testclient import TestClient

from app import main, storage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "SHEETS", tmp_path / "worksheets")
    monkeypatch.setattr(storage, "SETTINGS_FILE", tmp_path / "settings.json")
    return TestClient(main.app)


@pytest.fixture()
def locked(client, monkeypatch):
    """The app with a password set."""
    monkeypatch.setattr(main, "APP_PASSWORD", "pw")
    monkeypatch.setattr(main, "SESSION_KEY", b"test-key")
    monkeypatch.setattr(main, "FAIL_DELAY", 0)
    monkeypatch.setattr(main, "_login_fails", {})
    return client


def gen(client, **section):
    r = client.post("/api/generate", json={"seed": 7, "sections": [section]})
    assert r.status_code == 200, r.text
    return r.json()["sections"][0]


def test_courses_and_topics(client):
    courses = client.get("/api/courses").json()
    assert [c["name"] for c in courses][:4] == ["Algebra 1", "Geometry", "Algebra 2", "Precalculus"]
    topics = {t["id"]: t for t in client.get("/api/topics").json()}
    assert "geo" in topics["pythagorean"]["courses"]
    assert {s["id"] for s in topics["quadratics"]["skills"]} >= {"factor_x_bx_c", "quadratic_formula"}


def test_skills_filter_and_validation(client):
    sec = gen(client, topic="quadratics", count=4, difficulty=1, skills=["quadratic_formula"])
    assert {p["skill"] for p in sec["problems"]} == {"quadratic_formula"}
    bad = gen(client, topic="quadratics", count=1, skills=["nope"])
    assert "unknown skill" in bad["error"]


def test_answer_form_section_and_defaults(client):
    exact = gen(client, topic="area", count=3, skills=["circle_area"], answer_form="exact")
    assert all("\\pi" in p["answer"] and "approx" not in p["answer"] for p in exact["problems"])
    # Setup page default applies when the section doesn't choose
    client.put("/api/settings", json={"math_answer_form": "decimal", "math_places": 2})
    dec = gen(client, topic="area", count=3, skills=["circle_area"])
    assert all("\\pi" not in p["answer"] and "hundredth" in p["question"] for p in dec["problems"])


def test_invalid_options_rejected(client):
    for bad in ({"places": 7}, {"answer_form": "fraction"}, {"g": 9.81}):
        r = client.post("/api/generate", json={"sections": [{"topic": "area", **bad}]})
        assert r.status_code == 422, bad


def test_login_required_and_host_header_cannot_bypass_it(locked):
    assert locked.get("/api/settings").status_code == 401
    # request.url is rebuilt from the Host header: "x/login?" once made the login check see /login
    # while the router served /api/settings (CVE-2026-48710).
    r = locked.get("/api/settings", headers={"host": "x/login?"})
    assert r.status_code in (400, 401) and "ollama_url" not in r.text
    for path in ("/", "/static/app.js", "/static/login.html"):
        assert locked.get(path, follow_redirects=False).status_code == 307, path
    assert locked.get("/login").status_code == 200 and locked.get("/healthz").status_code == 200


def test_login_flow_and_rate_limit(locked, monkeypatch):
    r = locked.post("/login", data={"password": "nope"}, follow_redirects=False)
    assert r.headers["location"] == "/login?error=1"
    r = locked.post("/login", data={"password": "pw"}, follow_redirects=False)
    assert r.headers["location"] == "/" and main.COOKIE in r.cookies
    assert locked.get("/api/settings").status_code == 200
    # Too many failures lock the client out for a while, right password or not.
    monkeypatch.setattr(main, "LOGIN_MAX_FAILS", 2)
    locked.cookies.clear()
    for _ in range(2):
        locked.post("/login", data={"password": "nope"})
    r = locked.post("/login", data={"password": "pw"}, follow_redirects=False)
    assert r.headers["location"] == "/login?error=wait"


def test_cross_site_requests_refused(client):
    sheet = {"title": "t", "sections": []}
    assert client.post("/api/worksheets", json=sheet, headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert client.get("/api/worksheets", headers={"sec-fetch-site": "same-site"}).status_code == 403
    assert client.post("/api/worksheets", json=sheet, headers={"sec-fetch-site": "same-origin"}).status_code == 200
    assert client.get("/", headers={"sec-fetch-site": "cross-site"}).status_code == 200  # following a link


def test_unknown_host_refused(client, monkeypatch):
    monkeypatch.setattr(main, "ALLOWED_HOSTS", {"box.tailnet.ts.net", "127.0.0.1"})
    assert client.get("/healthz", headers={"host": "rebound.example"}).status_code == 400
    assert client.get("/healthz", headers={"host": "box.tailnet.ts.net:8080"}).status_code == 200


def test_large_bodies_refused(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_BODY", 100)
    assert client.post("/api/worksheets", json={"title": "x" * 200, "sections": []}).status_code == 413


def test_worksheet_validation_and_library(client):
    assert client.post("/api/worksheets", json={"sections": [1]}).status_code == 422
    assert client.post("/api/worksheets", content=json.dumps({"sections": []}),
                       headers={"content-type": "text/plain"}).status_code == 422
    saved = client.post("/api/worksheets", json={
        "title": "Mine", "custom": True,
        "sections": [{"config": {"topic": "area"}, "problems": [{"question": "q"}], "extra": 1}]}).json()
    assert saved["custom"] is True and saved["sections"][0]["extra"] == 1  # unknown fields are kept
    # A damaged file in the library is left out instead of breaking the whole list.
    (storage.SHEETS / f"{'0' * 32}.json").write_text('{"id": "x", "sections": [1]}')
    (storage.SHEETS / f"{'1' * 32}.json").write_text("not json")
    listing = client.get("/api/worksheets").json()
    assert [w["title"] for w in listing] == ["Mine"] and listing[0]["problems"] == 1


def test_one_failing_section_does_not_sink_the_rest(client, monkeypatch):
    real = main.generate_set

    def flaky(topic, *args, **kwargs):
        if topic == "quadratics":
            raise ZeroDivisionError("boom")
        return real(topic, *args, **kwargs)

    monkeypatch.setattr(main, "generate_set", flaky)
    r = client.post("/api/generate", json={"seed": 1, "sections": [{"topic": "quadratics"},
                                                                   {"topic": "area", "count": 2}]})
    bad, good = r.json()["sections"]
    assert "went wrong" in bad["error"] and len(good["problems"]) == 2


def test_conceptual_sections_ask_ai_for_written_response():
    opts = main._options(main.Section(topic="kinematics"), storage.DEFAULT_SETTINGS)
    written = main.Section(topic="concept_motion", subject="physics", source="ai")
    assert "written-response" in main._ai_instructions(written, opts) and "g =" not in main._ai_instructions(written, opts)
    assert main._written(main.Section(topic="custom", custom_topic="tides", subject="physics", course="conceptual"))
    assert not main._written(main.Section(topic="kinematics", subject="physics", course="physics"))
    physics = main.Section(topic="kinematics", subject="physics")
    assert main._number_format(physics, {**opts, "sig": 3})(7.9721) == "7.97"
