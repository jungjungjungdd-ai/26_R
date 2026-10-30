"""correlator 담당: pytest tests/test_correlator.py 가 모두 통과하면 완료

detector, payload_scanner 가 먼저 완성되어야 의미 있게 돌아갑니다.
"""
import pytest

from app.engine import correlator, detector, payload_scanner

pytestmark = pytest.mark.todo


@pytest.fixture
def paths(tables):
    usage = detector.detect_tools(tables["network_logs"], tables["processes"], tables["ai_tools"])
    hits = payload_scanner.scan_logs(tables["network_logs"])
    result = correlator.build_paths(usage, hits, tables)
    return {(p["employee_id"], p["tool_id"], p["asset_id"]): p for p in result}


def test_five_paths(paths):
    assert set(paths) == {
        ("E001", "T_N8N", "A01"),
        ("E002", "T_MCP_PG", "A02"),
        ("E003", "T_ZAPIER", "A03"),
        ("E004", "T_IMAGE_AI", "A04"),
        ("E005", "T_CHATGPT_ENT", "A05"),
    }


def test_all_keys(paths):
    for p in paths.values():
        assert set(correlator.PATH_KEYS) <= set(p)


def test_n8n_path(paths):
    p = paths[("E001", "T_N8N", "A01")]
    assert p["approved"] is False
    assert p["scopes"] == ["read", "send"]
    assert p["sensitivity"] == "개인정보"
    assert p["employee_status"] == "퇴사"
    assert p["bytes_out"] == 1270000
    assert sorted(p["network_log_ids"]) == ["N0001", "N0006"]
    assert p["payload_hit_count"] == 4
    assert sorted(p["payload_log_ids"]) == ["N0001", "N0006"]
    assert p["grant_id"] == "G0001"
    assert p["activity_count"] == 500


def test_mcp_path_from_process(paths):
    p = paths[("E002", "T_MCP_PG", "A02")]
    assert p["scopes"] == ["read", "write"]   # asset_activities 의 action 에서 옴
    assert p["proc_id"] == "P0001"
    assert p["grant_id"] is None
    assert p["bytes_out"] == 2100000


def test_image_ai_without_network(paths):
    p = paths[("E004", "T_IMAGE_AI", "A04")]
    assert p["bytes_out"] == 0
    assert p["network_log_ids"] == []
