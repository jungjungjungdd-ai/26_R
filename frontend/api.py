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


# ---- F2: 경로 상세 (FND-01~05, LOG-01, RUN-06) ----

def _fid(n: int) -> str:
    return f"{MOCK_RUN_ID}-F{n:03d}"


def _reason(code: str, points: int, desc: str, table: str, row_id: str) -> dict:
    return {"rule_code": code, "points": points, "description": desc,
            "source": {"table": table, "row_id": row_id}}


def _payload(log_id: str, text: str, *matches: tuple[str, str]) -> dict:
    hits = [{"type": kind, "start": text.index(sub), "end": text.index(sub) + len(sub)}
            for kind, sub in matches]
    return {"log_id": log_id, "text": text, "hits": hits}


MOCK_REASONS = {
    _fid(1): [_reason("R01", 20, "비승인 도구", "ai_tools", "T_N8N"),
              _reason("R02", 30, "개인정보 자산 접근", "assets", "A01"),
              _reason("R03", 15, "외부 전송 권한", "oauth_grants", "G001"),
              _reason("R04", 15, "대량 전송 발생", "network_logs", "N0213"),
              _reason("R05", 15, "소유자 퇴사", "employees", "E001")],
    _fid(2): [_reason("R01", 20, "비승인 도구", "ai_tools", "T_MCP_PG"),
              _reason("R02", 30, "개인정보 자산 접근", "assets", "A02"),
              _reason("R06", 20, "쓰기 권한 보유", "oauth_grants", "G002")],
    _fid(3): [_reason("R01", 20, "비승인 도구", "ai_tools", "T_ZAPIER"),
              _reason("R07", 15, "기밀 자산 접근", "assets", "A03"),
              _reason("R03", 15, "외부 전송 권한", "oauth_grants", "G003")],
    _fid(4): [_reason("R01", 20, "비승인 도구", "ai_tools", "T_IMAGE_AI"),
              _reason("R08", 5, "업무 외 시간 실행", "processes", "P010")],
    _fid(5): [_reason("R07", 15, "기밀 자산 접근", "assets", "A05"),
              _reason("R04", 15, "대량 전송 발생", "network_logs", "N0301")],
}

MOCK_PAYLOAD_HITS = {
    _fid(1): [_payload("N0213", "홍길동,010-1234-5678,서울시 강남구",
                       ("전화번호", "010-1234-5678")),
              _payload("N0214", "고객 김철수 kim@example.com 주민번호 900101-1234567",
                       ("이메일", "kim@example.com"), ("주민등록번호", "900101-1234567"))],
    _fid(2): [_payload("N0250", "SELECT * FROM customers -- 이영희 010-9876-5432",
                       ("전화번호", "010-9876-5432"))],
    _fid(3): [_payload("N0280", "To: park@partner.co.kr 견적서 첨부",
                       ("이메일", "park@partner.co.kr"))],
}

MOCK_RECOMMENDATIONS = {
    _fid(1): [{"rec_id": "REC01", "action": "외부 전송 권한 제거",
               "description": "n8n 연동에서 send 권한을 제거합니다.", "expected_score": 65}],
    _fid(2): [{"rec_id": "REC01", "action": "읽기 전용으로 축소",
               "description": "MCP 서버의 DB 계정을 read-only로 바꿉니다.", "expected_score": 50}],
    _fid(3): [{"rec_id": "REC01", "action": "권한 축소",
               "description": "메일 send 권한을 제거하고 read만 남깁니다.", "expected_score": 20}],
}

MOCK_LOGS = {
    ("ai_tools", "T_N8N"): {"tool_id": "T_N8N", "name": "n8n", "category": "workflow",
                           "approved": False, "domains": "hooks.n8n.io"},
    ("ai_tools", "T_MCP_PG"): {"tool_id": "T_MCP_PG", "name": "MCP (PostgreSQL)",
                              "category": "mcp", "approved": False},
    ("ai_tools", "T_ZAPIER"): {"tool_id": "T_ZAPIER", "name": "Zapier AI",
                              "category": "workflow", "approved": False},
    ("ai_tools", "T_IMAGE_AI"): {"tool_id": "T_IMAGE_AI", "name": "이미지 생성 AI",
                                "category": "genai", "approved": False},
    ("assets", "A01"): {"asset_id": "A01", "name": "CRM 고객 정보", "sensitivity": "개인정보"},
    ("assets", "A02"): {"asset_id": "A02", "name": "고객 DB", "sensitivity": "개인정보"},
    ("assets", "A03"): {"asset_id": "A03", "name": "사내 메일", "sensitivity": "기밀"},
    ("assets", "A05"): {"asset_id": "A05", "name": "사내 문서", "sensitivity": "기밀"},
    ("oauth_grants", "G001"): {"grant_id": "G001", "employee_id": "E001", "tool_id": "T_N8N",
                               "asset_id": "A01", "scopes": "read,send",
                               "granted_at": "2026-09-01 10:00:00"},
    ("oauth_grants", "G002"): {"grant_id": "G002", "employee_id": "E002",
                               "tool_id": "T_MCP_PG", "asset_id": "A02",
                               "scopes": "read,write", "granted_at": "2026-10-02 14:20:00"},
    ("oauth_grants", "G003"): {"grant_id": "G003", "employee_id": "E003",
                               "tool_id": "T_ZAPIER", "asset_id": "A03",
                               "scopes": "read,send", "granted_at": "2026-10-10 09:12:00"},
    ("network_logs", "N0213"): {"log_id": "N0213", "timestamp": "2026-10-30 23:05:00",
                                "employee_id": "E001", "domain": "hooks.n8n.io",
                                "bytes_out": 850000},
    ("network_logs", "N0301"): {"log_id": "N0301", "timestamp": "2026-10-29 18:40:00",
                                "employee_id": "E005", "domain": "api.openai.com",
                                "bytes_out": 420000},
    ("employees", "E001"): {"employee_id": "E001", "name": "김영업", "dept": "영업",
                            "status": "퇴사", "left_at": "2026-10-15"},
    ("processes", "P010"): {"proc_id": "P010", "employee_id": "E004",
                            "process_name": "imagegen.exe",
                            "started_at": "2026-10-28 23:40:00"},
}


def _mock_finding(finding_id: str) -> dict:
    return next(f for f in MOCK_FINDINGS if f["finding_id"] == finding_id)


def get_finding(finding_id: str) -> dict:
    """FND-01 경로 상세 + 점수 근거(reasons)."""
    if USE_MOCK:
        return {**_mock_finding(finding_id), "reasons": MOCK_REASONS.get(finding_id, [])}
    return _request("GET", f"/findings/{finding_id}")


def get_payload_hits(finding_id: str) -> list[dict]:
    """FND-02 로그별 민감정보 검출 위치. 명세 예시와 달리 리스트로 온다."""
    if USE_MOCK:
        return MOCK_PAYLOAD_HITS.get(finding_id, [])
    return _request("GET", f"/findings/{finding_id}/payload-hits")


def revoke(finding_id: str) -> dict:
    """FND-03 권한 회수."""
    if USE_MOCK:
        _mock_finding(finding_id)["status"] = "revoked"
        return {"finding_id": finding_id, "status": "revoked"}
    return _request("POST", f"/findings/{finding_id}/revoke")


def get_recommendations(finding_id: str) -> list[dict]:
    """FND-04 조치 추천."""
    if USE_MOCK:
        return MOCK_RECOMMENDATIONS.get(finding_id, [])
    return _request("GET", f"/findings/{finding_id}/recommendations")


def apply_recommendation(finding_id: str, rec_id: str) -> dict:
    """FND-05 추천 조치 적용."""
    if USE_MOCK:
        finding = _mock_finding(finding_id)
        rec = next(r for r in MOCK_RECOMMENDATIONS[finding_id] if r["rec_id"] == rec_id)
        before = finding["score"]
        finding.update(status="mitigated", score=rec["expected_score"])
        return {"finding_id": finding_id, "rec_id": rec_id, "status": "mitigated",
                "score_before": before, "score_after": rec["expected_score"]}
    return _request("POST", f"/findings/{finding_id}/recommendations/{rec_id}/apply")


def get_log(table: str, row_id: str, run_id: str | None = None) -> dict:
    """LOG-01 근거 원본 로그 한 줄."""
    if USE_MOCK:
        return {"table": table, "row": MOCK_LOGS.get((table, row_id), {})}
    params = {"run_id": run_id} if run_id else None
    return _request("GET", f"/logs/{table}/{row_id}", params=params)


def export_run(run_id: str) -> bytes:
    """RUN-06 분석 결과 CSV (utf-8-sig)."""
    if USE_MOCK:
        header = "finding_id,employee_name,tool_name,asset_name,score,level,status"
        rows = [",".join([f["finding_id"], f["employee"]["name"], f["tool"]["name"],
                          f["asset"]["name"], str(f["score"]), f["level"], f["status"]])
                for f in MOCK_FINDINGS]
        return "\n".join([header, *rows]).encode("utf-8-sig")
    response = requests.get(f"{BASE_URL}/runs/{run_id}/export", timeout=15)
    response.raise_for_status()
    return response.content
