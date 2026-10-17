"""API behaviour: courses, skills, answer forms and option defaults."""

import pytest
from fastapi.testclient import TestClient

from app import main, storage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "SHEETS", tmp_path / "worksheets")
    monkeypatch.setattr(storage, "SETTINGS_FILE", tmp_path / "settings.json")
    return TestClient(main.app)


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
