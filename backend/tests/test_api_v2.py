import time

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.jobs import JobStore


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "jobs", JobStore(workers=1))
    return TestClient(main.app)


def wait_for(client, job_id, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/v2/search/{job_id}").json()
        if job["status"] in {"done", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_health_and_products(client):
    assert client.get("/health").json() == {"status": "ok"}
    ids = [p["id"] for p in client.get("/api/v2/products").json()]
    assert ids == ["raw_sheep_wool", "duck_down", "cashmere"]


@pytest.mark.parametrize("body", [
    {"product": "silk"},
    {},
    {"product": "cashmere", "max_candidates": 0},
    {"product": "cashmere", "mode": "seed"},
    {"product": "cashmere", "seed_urls": ["not a url"]},
    {"product": "cashmere", "country": "x" * 101},
])
def test_invalid_requests_are_rejected(client, body):
    assert client.post("/api/v2/search", json=body).status_code == 422


def test_job_flow_returns_result(client, monkeypatch):
    seen = {}

    def fake_pipeline(req, progress):
        seen["req"] = req
        progress(stage="verifying", done=1, total=2, message="Checked a.test")
        return {"leads": [], "summary": {"examined": 0}}

    monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
    response = client.post("/api/v2/search", json={"product": "duck_down", "country": "  Japan  "})
    assert response.status_code == 202
    job = wait_for(client, response.json()["job_id"])
    assert job["status"] == "done" and job["result"]["summary"]["examined"] == 0
    assert job["stages"][-1] == "done"
    assert seen["req"].country == "Japan" and seen["req"].mode == "live"


def test_failed_job_reports_its_error(client, monkeypatch):
    def failing(req, progress):
        raise RuntimeError("The web search failed for every query.")

    monkeypatch.setattr(main, "run_pipeline", failing)
    job_id = client.post("/api/v2/search", json={"product": "cashmere"}).json()["job_id"]
    job = wait_for(client, job_id)
    assert job["status"] == "failed" and "failed for every query" in job["error"]


def test_unexpected_errors_are_not_leaked_but_reported(client, monkeypatch):
    def broken(req, progress):
        raise KeyError("internal detail")

    monkeypatch.setattr(main, "run_pipeline", broken)
    job = wait_for(client, client.post("/api/v2/search", json={"product": "cashmere"}).json()["job_id"])
    assert job["status"] == "failed" and "internal detail" not in job["error"]


def test_unknown_job_is_404(client):
    assert client.get("/api/v2/search/nope").status_code == 404


def test_knowledge_endpoint_exposes_rules_and_relations(client):
    kb = client.get("/api/v2/knowledge/duck_down").json()
    rule_ids = {r["id"] for r in kb["rules"]}
    assert {"DD-P1", "DD-N1", "G7"} <= rule_ids
    dd_p1 = next(r for r in kb["rules"] if r["id"] == "DD-P1")
    assert dd_p1["if"] and dd_p1["then"] == {"relevance": "strong", "usage": "supported"}
    assert any(r["predicate"] == "distinguished_from" for r in kb["relations"])
    assert client.get("/api/v2/knowledge/silk").status_code == 422


def test_legacy_endpoint_still_validates(client):
    assert client.post("/api/search", json={}).status_code == 422


def test_snapshots_are_listed(client, tmp_path, monkeypatch):
    import json

    import app.pipeline.runner as runner

    (tmp_path / "cashmere__italy.json").write_text(json.dumps(
        {"product": "cashmere", "country": "Italy", "recorded_at": "2026-11-22T08:00:00+00:00",
         "companies": [{}, {}]}), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(runner, "SNAPSHOT_DIR", tmp_path)
    assert client.get("/api/v2/snapshots").json() == [{
        "product": "cashmere", "product_name": "Cashmere", "country": "Italy",
        "recorded_at": "2026-11-22T08:00:00+00:00", "companies": 2}]
