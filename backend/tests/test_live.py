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


# ---------------------------------------------------------------- 이슈 #35: 회수된 경로는 로그를 만들지 않는다
@pytest.fixture
def n8n_script(tmp_path, monkeypatch):
    """1단계에 n8n 전송 로그(E001)와 Zapier 전송 로그(E003)가 함께 들어 있는 대본"""
    import json
    script = {"steps": [{"title": "n8n·Zapier 전송", "rows": {"network_logs": [
        {"log_id": "N0009", "timestamp": "2026-10-31 09:00:00", "employee_id": "E001",
         "domain": "hooks.n8n.io", "bytes_out": 500000, "payload_sample": "김하나,010-1111-2222"},
        {"log_id": "N0010", "timestamp": "2026-10-31 09:01:00", "employee_id": "E003",
         "domain": "hooks.zapier.com", "bytes_out": 380000, "payload_sample": "최둘,010-3333-4444"},
    ]}}]}
    path = tmp_path / "script.json"
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(config, "LIVE_SCRIPT_PATH", path)


def revoke_n8n(client, run_id):
    items = client.get(f"/api/runs/{run_id}/findings").json()
    target = next(f for f in items if f["tool"]["id"] == "T_N8N" and f["asset"]["id"] == "A01")
    assert client.post(f"/api/findings/{target['finding_id']}/revoke").status_code == 200


def log_exists(client, run_id, log_id, table="network_logs"):
    return client.get(f"/api/logs/{table}/{log_id}", params={"run_id": run_id}).status_code == 200


def test_revoked_path_log_is_skipped(client, n8n_script):
    run_id = analyzed(client)
    revoke_n8n(client, run_id)
    r = step(client, run_id)

    assert r["rows_added"] == 1 and r["rows_blocked"] == 1
    assert not log_exists(client, run_id, "N0009")      # 회수된 n8n 로그는 없음
    assert log_exists(client, run_id, "N0010")          # 다른 도구 로그는 들어감
    blocked = [e for e in r["events"] if e["type"] == "blocked"]
    assert len(blocked) == 1
    assert "회수로 차단됨" in blocked[0]["message"] and "N0009" in blocked[0]["message"]
    assert blocked[0]["detail"]["tool_id"] == "T_N8N"

    items = client.get(f"/api/runs/{run_id}/events").json()
    assert [e["type"] for e in items].count("blocked") == 1


def test_not_revoked_path_still_gets_log(client, n8n_script):
    run_id = analyzed(client)
    r = step(client, run_id)
    assert r["rows_added"] == 2 and r["rows_blocked"] == 0
    assert log_exists(client, run_id, "N0009")
    assert all(e["type"] != "blocked" for e in r["events"])


def test_reset_allows_log_again(client, n8n_script):
    run_id = analyzed(client)
    revoke_n8n(client, run_id)
    step(client, run_id)
    client.post(f"/api/runs/{run_id}/live/reset")   # reset 하면 회수도 처음으로 돌아간다
    r = step(client, run_id)
    assert r["rows_blocked"] == 0 and log_exists(client, run_id, "N0009")


def test_revoked_oauth_grant_is_skipped(client):
    """기본 대본 4단계: 퇴사자 n8n 권한 부여(G0006)도 n8n 회수 뒤에는 들어가지 않는다"""
    run_id = analyzed(client)
    revoke_n8n(client, run_id)
    for _ in range(3):
        step(client, run_id)
    r = step(client, run_id)
    assert r["rows_blocked"] == 1
    assert [e["type"] for e in r["events"]] == ["blocked"]
    assert not log_exists(client, run_id, "G0006", "oauth_grants")
