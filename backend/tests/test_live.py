"""실시간 시연 API (LIVE-01~04) 테스트"""
import pytest

from app import config
from conftest import SAMPLE
from test_api import upload


@pytest.fixture(autouse=True)
def script(monkeypatch):
    monkeypatch.setattr(config, "LIVE_SCRIPT_PATH", SAMPLE / "live_script.json")


def analyzed(client):
    run_id = upload(client)
    assert client.post(f"/api/runs/{run_id}/analyze").status_code == 200
    return run_id


def scores(client, run_id):
    items = client.get(f"/api/runs/{run_id}/findings").json()
    return {(f["tool"]["id"], f["asset"]["id"]): f["score"] for f in items}


def step(client, run_id):
    r = client.post(f"/api/runs/{run_id}/live/step")
    assert r.status_code == 200, r.text
    return r.json()


def test_step_before_analyze(client):
    run_id = upload(client)
    r = client.post(f"/api/runs/{run_id}/live/step")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "NOT_ANALYZED"


def test_status_at_start(client):
    run_id = analyzed(client)
    s = client.get(f"/api/runs/{run_id}/live/status").json()
    assert (s["step"], s["total"], s["finished"]) == (0, 4, False)


def test_each_step_changes_result(client):
    run_id = analyzed(client)
    base = scores(client, run_id)
    expected = [
        (("T_ZAPIER", "A03"), 70, ["new_payload_hit", "score_up"]),
        (("T_IMAGE_AI", "A05"), 45, ["new_finding"]),
        (("T_MCP_PG", "A02"), 90, ["new_payload_hit", "new_payload_hit", "score_up"]),
        (("T_N8N", "A02"), 100, ["new_finding"]),
    ]
    for i, (key, score, types) in enumerate(expected, start=1):
        r = step(client, run_id)
        assert r["step"] == i and r["changed"] is True
        assert sorted(e["type"] for e in r["events"]) == sorted(types)
        assert scores(client, run_id)[key] == score
    assert scores(client, run_id) != base


def test_step_after_finish(client):
    run_id = analyzed(client)
    for _ in range(4):
        step(client, run_id)
    r = step(client, run_id)
    assert r["finished"] is True and r["changed"] is False and r["events"] == []
    assert r["step"] == 4


def test_reset_gives_same_result(client):
    run_id = analyzed(client)
    base = scores(client, run_id)
    first = [[(e["type"], e["message"]) for e in step(client, run_id)["events"]] for _ in range(4)]

    r = client.post(f"/api/runs/{run_id}/live/reset")
    assert r.status_code == 200 and r.json()["step"] == 0
    assert scores(client, run_id) == base
    assert client.get(f"/api/runs/{run_id}/events").json() == []

    second = [[(e["type"], e["message"]) for e in step(client, run_id)["events"]] for _ in range(4)]
    assert first == second


def test_events_filters(client):
    run_id = analyzed(client)
    for _ in range(4):
        step(client, run_id)
    items = client.get(f"/api/runs/{run_id}/events").json()
    assert len(items) == 7

    cursor = next(e for e in items if e["step"] == 2)
    after = client.get(f"/api/runs/{run_id}/events", params={"after_id": cursor["event_id"]}).json()
    assert after and all(e["event_id"] > cursor["event_id"] for e in after)

    since = client.get(f"/api/runs/{run_id}/events", params={"since": cursor["created_at"]}).json()
    assert since and all(e["step"] >= 3 for e in since)

    future = client.get(f"/api/runs/{run_id}/events", params={"since": "2999-01-01 00:00:00"}).json()
    assert future == []


def test_bad_since(client):
    run_id = analyzed(client)
    assert client.get(f"/api/runs/{run_id}/events", params={"since": "어제"}).status_code == 422


def test_revoked_status_survives_step(client):
    run_id = analyzed(client)
    items = client.get(f"/api/runs/{run_id}/findings").json()
    target = next(f for f in items if f["tool"]["id"] == "T_N8N" and f["asset"]["id"] == "A01")
    r = client.post(f"/api/findings/{target['finding_id']}/revoke")
    assert r.status_code == 200, r.text
    step(client, run_id)
    items = client.get(f"/api/runs/{run_id}/findings").json()
    now = next(f for f in items if f["tool"]["id"] == "T_N8N" and f["asset"]["id"] == "A01")
    assert now["status"] == "revoked"
