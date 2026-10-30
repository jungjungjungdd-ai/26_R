"""API 흐름 테스트: 지금 바로 통과해야 함"""
import pytest

from conftest import FILES, SAMPLE


def upload(client):
    files = {name: (fn, (SAMPLE / fn).read_bytes()) for name, fn in FILES.items()}
    r = client.post("/api/runs", files=files)
    assert r.status_code == 201, r.text
    return r.json()["run_id"]


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_and_analyze(client):
    run_id = upload(client)
    assert client.post(f"/api/runs/{run_id}/analyze").status_code == 200
    assert client.get(f"/api/runs/{run_id}/summary").status_code == 200
    assert client.get(f"/api/runs/{run_id}/findings").status_code == 200
    assert client.get(f"/api/runs/{run_id}/graph").status_code == 200


def test_missing_file_column(client):
    files = {name: (fn, (SAMPLE / fn).read_bytes()) for name, fn in FILES.items()}
    files["oauth_grants"] = ("oauth_grants.csv", b"grant_id,employee_id\nG1,E001\n")
    r = client.post("/api/runs", files=files)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE"


def test_not_analyzed(client):
    run_id = upload(client)
    assert client.get(f"/api/runs/{run_id}/summary").json()["error"]["code"] == "NOT_ANALYZED"


def test_log_lookup(client):
    upload(client)
    r = client.get("/api/logs/network_logs/N0001")
    assert r.json()["row"]["domain"] == "hooks.n8n.io"


@pytest.mark.todo
def test_full_demo_result(client):
    """엔진 4개가 모두 완성되면 통과: 시연용 숨긴 사례가 기대한 점수로 나오는지"""
    run_id = upload(client)
    client.post(f"/api/runs/{run_id}/analyze")
    summary = client.get(f"/api/runs/{run_id}/summary").json()
    assert summary["levels"] == {"위험": 2, "주의": 1, "낮음": 2}
    scores = {(f["tool"]["id"]): f["score"] for f in client.get(f"/api/runs/{run_id}/findings").json()}
    assert scores == {"T_N8N": 95, "T_MCP_PG": 70, "T_ZAPIER": 50, "T_IMAGE_AI": 25, "T_CHATGPT_ENT": 30}
