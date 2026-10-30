"""scorer 담당: pytest tests/test_scorer.py 가 모두 통과하면 완료"""
import pytest

from app.engine import scorer

N8N = {
    "employee_id": "E001", "tool_id": "T_N8N", "asset_id": "A01", "approved": False,
    "scopes": ["read", "send"], "sensitivity": "개인정보", "employee_status": "퇴사",
    "bytes_out": 1270000, "network_log_ids": ["N0001", "N0006"], "payload_hit_count": 4,
    "payload_log_ids": ["N0001", "N0006"], "grant_id": "G0001", "proc_id": None, "activity_count": 500,
}
MCP = {
    "employee_id": "E002", "tool_id": "T_MCP_PG", "asset_id": "A02", "approved": False,
    "scopes": ["read", "write"], "sensitivity": "개인정보", "employee_status": "재직",
    "bytes_out": 2100000, "network_log_ids": ["N0002"], "payload_hit_count": 0,
    "payload_log_ids": [], "grant_id": None, "proc_id": "P0001", "activity_count": 1020,
}
APPROVED = {**MCP, "tool_id": "T_CHATGPT_ENT", "approved": True, "scopes": ["read"],
            "sensitivity": "기밀", "bytes_out": 0, "network_log_ids": []}


def test_level_boundaries():
    assert scorer.level_of(70) == "위험"
    assert scorer.level_of(69) == "주의"
    assert scorer.level_of(40) == "주의"
    assert scorer.level_of(39) == "낮음"


@pytest.mark.todo
def test_n8n_score():
    r = scorer.score(N8N)
    assert (r["score"], r["level"]) == (95, "위험")
    assert [x["rule_code"] for x in r["reasons"]] == ["R01", "R02", "R05", "R06", "R07", "R08"]


@pytest.mark.todo
def test_n8n_sources():
    src = {x["rule_code"]: x["source"] for x in scorer.score(N8N)["reasons"]}
    assert src["R02"] == {"table": "oauth_grants", "row_id": "G0001"}
    assert src["R06"] == {"table": "oauth_grants", "row_id": "G0001"}
    assert src["R07"] == {"table": "network_logs", "row_id": "N0001"}
    assert src["R08"] == {"table": "employees", "row_id": "E001"}


@pytest.mark.todo
def test_mcp_score():
    r = scorer.score(MCP)
    assert (r["score"], r["level"]) == (70, "위험")
    src = {x["rule_code"]: x["source"] for x in r["reasons"]}
    assert src["R03"] == {"table": "processes", "row_id": "P0001"}
    assert src["R06"] == {"table": "network_logs", "row_id": "N0002"}


@pytest.mark.todo
def test_approved_tool_has_no_r01():
    r = scorer.score(APPROVED)
    assert "R01" not in [x["rule_code"] for x in r["reasons"]]
    assert (r["score"], r["level"]) == (15, "낮음")
