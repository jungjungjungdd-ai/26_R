"""프론트 화면과 FastAPI 사이의 API 클라이언트."""
import os
from collections.abc import Mapping
from typing import Any

import requests

USE_MOCK = os.getenv("USE_MOCK", "true").lower() in {"1", "true", "yes"}
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api").rstrip("/")
MOCK_RUN_ID = "R20261031-01"

MOCK_FINDINGS = [
    {"finding_id": f"{MOCK_RUN_ID}-F001",
     "employee": {"id": "E001", "name": "김영업", "status": "퇴사"},
     "tool": {"id": "T_N8N", "name": "n8n", "approved": False},
     "asset": {"id": "A01", "name": "CRM 고객 정보", "sensitivity": "개인정보"},
     "scopes": ["read", "send"], "score": 95, "level": "위험", "status": "open"},
    {"finding_id": f"{MOCK_RUN_ID}-F002",
     "employee": {"id": "E002", "name": "이개발", "status": "재직"},
     "tool": {"id": "T_MCP_PG", "name": "MCP (PostgreSQL)", "approved": False},
     "asset": {"id": "A02", "name": "고객 DB", "sensitivity": "개인정보"},
     "scopes": ["read", "write"], "score": 70, "level": "위험", "status": "open"},
    {"finding_id": f"{MOCK_RUN_ID}-F003",
     "employee": {"id": "E003", "name": "박마케팅", "status": "재직"},
     "tool": {"id": "T_ZAPIER", "name": "Zapier AI", "approved": False},
     "asset": {"id": "A03", "name": "사내 메일", "sensitivity": "기밀"},
     "scopes": ["read", "send"], "score": 50, "level": "주의", "status": "open"},
    {"finding_id": f"{MOCK_RUN_ID}-F004",
     "employee": {"id": "E004", "name": "최디자인", "status": "재직"},
     "tool": {"id": "T_IMAGE_AI", "name": "이미지 생성 AI", "approved": False},
     "asset": {"id": "A04", "name": "홍보 폴더", "sensitivity": "일반"},
     "scopes": ["read"], "score": 25, "level": "낮음", "status": "open"},
    {"finding_id": f"{MOCK_RUN_ID}-F005",
     "employee": {"id": "E005", "name": "정회계", "status": "재직"},
     "tool": {"id": "T_CHATGPT_ENT", "name": "ChatGPT Enterprise", "approved": True},
     "asset": {"id": "A05", "name": "사내 문서", "sensitivity": "기밀"},
     "scopes": ["read"], "score": 30, "level": "낮음", "status": "open"},
]


def _request(method: str, path: str, **kwargs: Any) -> Any:
    response = requests.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def check_backend_health() -> bool:
    """백엔드 상태 확인. mock 모드에서는 실제 서버를 호출하지 않는다."""
    if USE_MOCK:
        return False
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except requests.RequestException:
        return False


def _as_request_file(uploaded: Any) -> tuple[str, bytes, str]:
    filename = getattr(uploaded, "name", "upload.csv")
    content_type = getattr(uploaded, "type", "application/octet-stream")
    content = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
    return filename, content, content_type


def upload_run(files: Mapping[str, Any]) -> dict:
    if USE_MOCK:
        return {"run_id": MOCK_RUN_ID, "status": "uploaded",
                "rows": {name: 1 for name in files}}
    request_files = {name: _as_request_file(file) for name, file in files.items()}
    return _request("POST", "/runs", files=request_files)


def analyze_run(run_id: str) -> dict:
    if USE_MOCK:
        return {"run_id": run_id, "status": "done", "findings": len(MOCK_FINDINGS),
                "duration_ms": 42}
    return _request("POST", f"/runs/{run_id}/analyze")


def get_summary(run_id: str) -> dict:
    if USE_MOCK:
        levels = {level: sum(f["level"] == level for f in MOCK_FINDINGS)
                  for level in ("위험", "주의", "낮음")}
        return {"tools_detected": len({f["tool"]["id"] for f in MOCK_FINDINGS}),
                "unapproved": len({f["tool"]["id"] for f in MOCK_FINDINGS
                                   if not f["tool"]["approved"]}),
                "levels": levels, "revoked": 0}
    return _request("GET", f"/runs/{run_id}/summary")


def get_findings(run_id: str, level: str | None = None,
                 approved: bool | None = None, status: str | None = None) -> list[dict]:
    if USE_MOCK:
        items = list(MOCK_FINDINGS)
        if level:
            items = [item for item in items if item["level"] == level]
        if approved is not None:
            items = [item for item in items if item["tool"]["approved"] == approved]
        if status:
            items = [item for item in items if item["status"] == status]
        return items
    params = {key: value for key, value in {
        "level": level, "approved": approved, "status": status}.items() if value is not None}
    return _request("GET", f"/runs/{run_id}/findings", params=params)


def get_graph(run_id: str) -> dict:
    if USE_MOCK:
        nodes: dict[str, dict] = {}
        edges = []
        for finding in MOCK_FINDINGS:
            employee, tool, asset = finding["employee"], finding["tool"], finding["asset"]
            nodes[employee["id"]] = {"id": employee["id"], "label": employee["name"],
                                     "type": "employee"}
            nodes[tool["id"]] = {"id": tool["id"], "label": tool["name"], "type": "tool",
                                 "approved": tool["approved"]}
            nodes[asset["id"]] = {"id": asset["id"], "label": asset["name"], "type": "asset",
                                  "sensitivity": asset["sensitivity"]}
            edge = {"finding_id": finding["finding_id"], "level": finding["level"]}
            edges.extend([{"source": employee["id"], "target": tool["id"], **edge},
                          {"source": tool["id"], "target": asset["id"], **edge}])
        return {"nodes": list(nodes.values()), "edges": edges}
    return _request("GET", f"/runs/{run_id}/graph")


# F2 작업 전까지 기존 도구 목록 화면을 유지하기 위한 임시 호환 함수.
def get_tools() -> list[dict]:
    return [{"id": f["finding_id"], "name": f["tool"]["name"],
             "owner": f["employee"]["name"], "approved": f["tool"]["approved"],
             "assets": [f["asset"]["name"]], "score": f["score"], "level": f["level"],
             "reasons": ["상세 근거는 F2 화면에서 연결 예정"]}
            for f in get_findings(MOCK_RUN_ID)]


def revoke_tool(finding_id: str) -> dict:
    if USE_MOCK:
        return {"finding_id": finding_id, "status": "revoked"}
    return _request("POST", f"/findings/{finding_id}/revoke")
