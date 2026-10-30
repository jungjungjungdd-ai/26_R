"""detector 담당: pytest tests/test_detector.py 가 모두 통과하면 완료"""
import pytest

from app.engine import detector

pytestmark = pytest.mark.todo


def test_build_lookup(tables):
    domain_map, process_map = detector.build_lookup(tables["ai_tools"])
    assert domain_map["hooks.n8n.io"] == "T_N8N"
    assert domain_map["chatgpt.com"] == "T_CHATGPT_ENT"
    assert process_map == {"mcp-server-postgres": "T_MCP_PG"}


def test_detect_tools(tables):
    usage = detector.detect_tools(tables["network_logs"], tables["processes"], tables["ai_tools"])
    assert list(usage.columns) == detector.USAGE_COLUMNS
    found = set(zip(usage["source_table"], usage["source_id"], usage["tool_id"]))
    assert found == {
        ("network_logs", "N0001", "T_N8N"),
        ("network_logs", "N0002", "T_MCP_PG"),
        ("network_logs", "N0003", "T_ZAPIER"),
        ("network_logs", "N0004", "T_CHATGPT_ENT"),
        ("network_logs", "N0006", "T_N8N"),
        ("processes", "P0001", "T_MCP_PG"),
    }  # google.com 과 photoshop.exe 는 AI 가 아니므로 없어야 함
