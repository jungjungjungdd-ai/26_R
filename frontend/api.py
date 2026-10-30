"""프론트 화면과 FastAPI 사이의 API 클라이언트."""
import copy
import os
from collections.abc import Mapping
from typing import Any

import requests

USE_MOCK = os.getenv("USE_MOCK", "true").lower() in {"1", "true", "yes"}
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api").rstrip("/")
MOCK_RUN_ID = "R20261031-01"

REQUIRED_FILES = (
    "employees",
    "assets",
    "ai_tools",
    "network_logs",
    "oauth_grants",
    "asset_activities",
    "processes",
)

MOCK_ROWS: dict[str, int] = {
    "employees": 5,
    "assets": 5,
    "ai_tools": 5,
    "network_logs": 6,
    "oauth_grants": 4,
    "asset_activities": 4,
    "processes": 2,
}

_INITIAL_MOCK_FINDINGS: list[dict[str, Any]] = [
    {
        "finding_id": f"{MOCK_RUN_ID}-F001",
        "employee": {"id": "E001", "name": "김영업", "status": "퇴사"},
        "tool": {"id": "T_N8N", "name": "n8n", "approved": False},
        "asset": {"id": "A01", "name": "CRM 고객 정보", "sensitivity": "개인정보"},
        "scopes": ["read", "send"],
        "score": 95,
        "level": "위험",
        "status": "open",
    },
    {
        "finding_id": f"{MOCK_RUN_ID}-F002",
        "employee": {"id": "E002", "name": "이개발", "status": "재직"},
        "tool": {"id": "T_MCP_PG", "name": "MCP 서버 (postgres)", "approved": False},
        "asset": {"id": "A02", "name": "고객 DB", "sensitivity": "개인정보"},
        "scopes": ["read", "write"],
        "score": 70,
        "level": "위험",
        "status": "open",
    },
    {
        "finding_id": f"{MOCK_RUN_ID}-F003",
        "employee": {"id": "E003", "name": "박마케팅", "status": "재직"},
        "tool": {"id": "T_ZAPIER", "name": "Zapier AI", "approved": False},
        "asset": {"id": "A03", "name": "사내 메일", "sensitivity": "기밀"},
        "scopes": ["read", "send"],
        "score": 50,
        "level": "주의",
        "status": "open",
    },
    {
        "finding_id": f"{MOCK_RUN_ID}-F004",
        "employee": {"id": "E005", "name": "정회계", "status": "재직"},
        "tool": {"id": "T_CHATGPT_ENT", "name": "ChatGPT Enterprise", "approved": True},
        "asset": {"id": "A05", "name": "사내 문서", "sensitivity": "기밀"},
        "scopes": ["read"],
        "score": 30,
        "level": "낮음",
        "status": "open",
    },
    {
        "finding_id": f"{MOCK_RUN_ID}-F005",
        "employee": {"id": "E004", "name": "최디자인", "status": "재직"},
        "tool": {"id": "T_IMAGE_AI", "name": "이미지 생성 AI", "approved": False},
        "asset": {"id": "A04", "name": "홍보 폴더", "sensitivity": "일반"},
        "scopes": ["read"],
        "score": 25,
        "level": "낮음",
        "status": "open",
    },
]

MOCK_FINDINGS: list[dict[str, Any]] = copy.deepcopy(_INITIAL_MOCK_FINDINGS)


class ApiError(Exception):
    """백엔드 에러 응답({"error": {"code", "message", "detail"}}) 예외."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail or {}


def _request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = requests.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(
            status_code=503,
            code="CONNECTION_ERROR",
            message=f"백엔드 서버에 연결할 수 없습니다: {exc}",
        ) from exc

    if not response.ok:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict) and error.get("message"):
            raise ApiError(
                status_code=response.status_code,
                code=str(error.get("code", "API_ERROR")),
                message=str(error["message"]),
                detail=error.get("detail") if isinstance(error.get("detail"), dict) else {},
            )
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if response.status_code == 422 and isinstance(detail, list) and detail:
            first = detail[0] if isinstance(detail[0], dict) else {}
            loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
            msg = first.get("msg", "요청 형식이 올바르지 않습니다")
            raise ApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message=f"요청 형식 오류 ({loc}): {msg}" if loc else f"요청 형식 오류: {msg}",
                detail={"errors": detail},
            )
        raise ApiError(
            status_code=response.status_code,
            code="HTTP_ERROR",
            message=f"요청 처리 중 오류가 발생했습니다 (HTTP {response.status_code})",
        )

    return response.json()


def health() -> dict[str, Any]:
    """SYS-01 백엔드 상태 확인 (GET /health)."""
    if USE_MOCK:
        return {"status": "ok"}
    return _request("GET", "/health")


def _as_request_file(name: str, uploaded: Any) -> tuple[str, bytes, str]:
    default_ext = "json" if name == "ai_tools" else "csv"
    filename = getattr(uploaded, "name", f"{name}.{default_ext}")
    content_type = getattr(uploaded, "type", "application/octet-stream")
    if hasattr(uploaded, "getvalue"):
        content = uploaded.getvalue()
    elif hasattr(uploaded, "read"):
        if hasattr(uploaded, "seek"):
            uploaded.seek(0)
        content = uploaded.read()
    elif isinstance(uploaded, (bytes, bytearray)):
        content = bytes(uploaded)
    else:
        raise ApiError(400, "INVALID_FILE", f"{filename}을(를) 읽을 수 없습니다", {"file": filename})
    return filename, content, content_type


def upload_run(files: Mapping[str, Any]) -> dict[str, Any]:
    """RUN-01 로그 파일 7개 업로드 (POST /runs)."""
    missing = [key for key in REQUIRED_FILES if key not in files or files[key] is None]
    if missing:
        raise ApiError(
            status_code=400,
            code="INVALID_FILE",
            message=f"필수 파일이 빠졌습니다: {', '.join(missing)}",
            detail={"missing": missing},
        )
    if USE_MOCK:
        MOCK_FINDINGS[:] = copy.deepcopy(_INITIAL_MOCK_FINDINGS)
        _MOCK_LIVE["step"] = 0  # 새 업로드 = 새 run 이므로 실시간 진행도 처음부터
        _MOCK_LIVE["events"].clear()
        return {
            "run_id": MOCK_RUN_ID,
            "status": "uploaded",
            "rows": dict(MOCK_ROWS),
        }
    request_files = {name: _as_request_file(name, files[name]) for name in REQUIRED_FILES}
    return _request("POST", "/runs", files=request_files)


def analyze(run_id: str) -> dict[str, Any]:
    """RUN-02 탐지, 상관분석, 위험도 산정 실행 (POST /runs/{run_id}/analyze)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        return {
            "run_id": run_id,
            "status": "done",
            "findings": len(MOCK_FINDINGS),
            "duration_ms": 42,
        }
    return _request("POST", f"/runs/{run_id}/analyze")


def get_summary(run_id: str) -> dict[str, Any]:
    """RUN-03 개요 화면용 요약 숫자 (GET /runs/{run_id}/summary)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        open_items = [f for f in MOCK_FINDINGS if f["status"] == "open"]
        levels = {
            level: sum(f["level"] == level for f in open_items)
            for level in ("위험", "주의", "낮음")
        }
        return {
            "tools_detected": len({f["tool"]["id"] for f in MOCK_FINDINGS}),
            "unapproved": len(
                {f["tool"]["id"] for f in MOCK_FINDINGS if not f["tool"]["approved"]}
            ),
            "levels": levels,
            "revoked": sum(f["status"] != "open" for f in MOCK_FINDINGS),
        }
    return _request("GET", f"/runs/{run_id}/summary")


def get_findings(
    run_id: str,
    level: str | None = None,
    approved: bool | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """RUN-04 경로 목록 조회 (GET /runs/{run_id}/findings)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        items = sorted(MOCK_FINDINGS, key=lambda x: x["score"], reverse=True)
        if level:
            items = [item for item in items if item["level"] == level]
        if approved is not None:
            items = [item for item in items if item["tool"]["approved"] == approved]
        if status:
            items = [item for item in items if item["status"] == status]
        return items
    params = {
        key: value
        for key, value in {"level": level, "approved": approved, "status": status}.items()
        if value is not None
    }
    return _request("GET", f"/runs/{run_id}/findings", params=params)


def get_graph(run_id: str) -> dict[str, Any]:
    """RUN-05 자산 지도용 노드와 선 (GET /runs/{run_id}/graph)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        for finding in get_findings(run_id):
            employee, tool, asset = finding["employee"], finding["tool"], finding["asset"]
            if employee.get("id"):
                nodes[employee["id"]] = {
                    "id": employee["id"],
                    "label": employee["name"],
                    "type": "employee",
                }
                edges.append(
                    {
                        "source": employee["id"],
                        "target": tool["id"],
                        "finding_id": finding["finding_id"],
                        "level": finding["level"],
                    }
                )
            nodes[tool["id"]] = {
                "id": tool["id"],
                "label": tool["name"],
                "type": "tool",
                "approved": tool["approved"],
            }
            nodes[asset["id"]] = {
                "id": asset["id"],
                "label": asset["name"],
                "type": "asset",
                "sensitivity": asset["sensitivity"],
            }
            edges.append(
                {
                    "source": tool["id"],
                    "target": asset["id"],
                    "finding_id": finding["finding_id"],
                    "level": finding["level"],
                }
            )
        return {"nodes": list(nodes.values()), "edges": edges}
    return _request("GET", f"/runs/{run_id}/graph")


# ---- F2: 경로 상세 (FND-01~05, LOG-01, RUN-06) ----


def _fid(n: int) -> str:
    return f"{MOCK_RUN_ID}-F{n:03d}"


def _reason(code: str, points: int, desc: str, table: str, row_id: str) -> dict[str, Any]:
    return {
        "rule_code": code,
        "points": points,
        "description": desc,
        "source": {"table": table, "row_id": row_id},
    }


def _payload(log_id: str, text: str, *matches: tuple[str, str]) -> dict[str, Any]:
    hits = [
        {"type": kind, "start": text.index(sub), "end": text.index(sub) + len(sub)}
        for kind, sub in matches
    ]
    return {"log_id": log_id, "text": text, "hits": hits}


MOCK_REASONS = {
    _fid(1): [
        _reason("R01", 20, "비승인 도구", "ai_tools", "T_N8N"),
        _reason("R02", 30, "개인정보 자산 접근", "assets", "A01"),
        _reason("R03", 15, "외부 전송 권한", "oauth_grants", "G001"),
        _reason("R04", 15, "대량 전송 발생", "network_logs", "N0213"),
        _reason("R05", 15, "소유자 퇴사", "employees", "E001"),
    ],
    _fid(2): [
        _reason("R01", 20, "비승인 도구", "ai_tools", "T_MCP_PG"),
        _reason("R02", 30, "개인정보 자산 접근", "assets", "A02"),
        _reason("R06", 20, "쓰기 권한 보유", "oauth_grants", "G002"),
    ],
    _fid(3): [
        _reason("R01", 20, "비승인 도구", "ai_tools", "T_ZAPIER"),
        _reason("R07", 15, "기밀 자산 접근", "assets", "A03"),
        _reason("R03", 15, "외부 전송 권한", "oauth_grants", "G003"),
    ],
    _fid(4): [
        _reason("R07", 15, "기밀 자산 접근", "assets", "A05"),
        _reason("R04", 15, "대량 전송 발생", "network_logs", "N0301"),
    ],
    _fid(5): [
        _reason("R01", 20, "비승인 도구", "ai_tools", "T_IMAGE_AI"),
        _reason("R08", 5, "업무 외 시간 실행", "processes", "P010"),
    ],
}

MOCK_PAYLOAD_HITS = {
    _fid(1): [
        _payload(
            "N0213",
            "홍길동,010-1234-5678,서울시 강남구",
            ("전화번호", "010-1234-5678"),
        ),
        _payload(
            "N0214",
            "고객 김철수 kim@example.com 주민번호 900101-1234567",
            ("이메일", "kim@example.com"),
            ("주민등록번호", "900101-1234567"),
        ),
    ],
    _fid(2): [
        _payload(
            "N0250",
            "SELECT * FROM customers -- 이영희 010-9876-5432",
            ("전화번호", "010-9876-5432"),
        )
    ],
    _fid(3): [
        _payload(
            "N0280",
            "To: park@partner.co.kr 견적서 첨부",
            ("이메일", "park@partner.co.kr"),
        )
    ],
}

MOCK_RECOMMENDATIONS = {
    _fid(1): [
        {
            "rec_id": "REC01",
            "action": "외부 전송 권한 제거",
            "description": "n8n 연동에서 send 권한을 제거합니다.",
            "expected_score": 65,
        }
    ],
    _fid(2): [
        {
            "rec_id": "REC01",
            "action": "읽기 전용으로 축소",
            "description": "MCP 서버의 DB 계정을 read-only로 바꿉니다.",
            "expected_score": 50,
        }
    ],
    _fid(3): [
        {
            "rec_id": "REC01",
            "action": "권한 축소",
            "description": "메일 send 권한을 제거하고 read만 남깁니다.",
            "expected_score": 20,
        }
    ],
}

MOCK_LOGS = {
    ("ai_tools", "T_N8N"): {
        "tool_id": "T_N8N",
        "name": "n8n",
        "category": "workflow",
        "approved": False,
        "domains": "hooks.n8n.io",
    },
    ("ai_tools", "T_MCP_PG"): {
        "tool_id": "T_MCP_PG",
        "name": "MCP (PostgreSQL)",
        "category": "mcp",
        "approved": False,
    },
    ("ai_tools", "T_ZAPIER"): {
        "tool_id": "T_ZAPIER",
        "name": "Zapier AI",
        "category": "workflow",
        "approved": False,
    },
    ("ai_tools", "T_IMAGE_AI"): {
        "tool_id": "T_IMAGE_AI",
        "name": "이미지 생성 AI",
        "category": "genai",
        "approved": False,
    },
    ("assets", "A01"): {"asset_id": "A01", "name": "CRM 고객 정보", "sensitivity": "개인정보"},
    ("assets", "A02"): {"asset_id": "A02", "name": "고객 DB", "sensitivity": "개인정보"},
    ("assets", "A03"): {"asset_id": "A03", "name": "사내 메일", "sensitivity": "기밀"},
    ("assets", "A05"): {"asset_id": "A05", "name": "사내 문서", "sensitivity": "기밀"},
    ("oauth_grants", "G001"): {
        "grant_id": "G001",
        "employee_id": "E001",
        "tool_id": "T_N8N",
        "asset_id": "A01",
        "scopes": "read,send",
        "granted_at": "2026-09-01 10:00:00",
    },
    ("oauth_grants", "G002"): {
        "grant_id": "G002",
        "employee_id": "E002",
        "tool_id": "T_MCP_PG",
        "asset_id": "A02",
        "scopes": "read,write",
        "granted_at": "2026-10-02 14:20:00",
    },
    ("oauth_grants", "G003"): {
        "grant_id": "G003",
        "employee_id": "E003",
        "tool_id": "T_ZAPIER",
        "asset_id": "A03",
        "scopes": "read,send",
        "granted_at": "2026-10-10 09:12:00",
    },
    ("network_logs", "N0213"): {
        "log_id": "N0213",
        "timestamp": "2026-10-30 23:05:00",
        "employee_id": "E001",
        "domain": "hooks.n8n.io",
        "bytes_out": 850000,
    },
    ("network_logs", "N0301"): {
        "log_id": "N0301",
        "timestamp": "2026-10-29 18:40:00",
        "employee_id": "E005",
        "domain": "api.openai.com",
        "bytes_out": 420000,
    },
    ("employees", "E001"): {
        "employee_id": "E001",
        "name": "김영업",
        "dept": "영업",
        "status": "퇴사",
        "left_at": "2026-10-15",
    },
    ("processes", "P010"): {
        "proc_id": "P010",
        "employee_id": "E004",
        "process_name": "imagegen.exe",
        "started_at": "2026-10-28 23:40:00",
    },
}


def _mock_finding(finding_id: str) -> dict[str, Any]:
    for finding in MOCK_FINDINGS:
        if finding["finding_id"] == finding_id:
            return finding
    raise ApiError(404, "NOT_FOUND", "경로가 없습니다", {"finding_id": finding_id})


def get_finding(finding_id: str) -> dict[str, Any]:
    """FND-01 경로 상세 + 점수 근거(reasons)."""
    if USE_MOCK:
        return {**_mock_finding(finding_id), "reasons": MOCK_REASONS.get(finding_id, [])}
    return _request("GET", f"/findings/{finding_id}")


def get_payload_hits(finding_id: str) -> list[dict[str, Any]]:
    """FND-02 로그별 민감정보 검출 위치. 명세 예시와 달리 리스트로 온다."""
    if USE_MOCK:
        _mock_finding(finding_id)
        return MOCK_PAYLOAD_HITS.get(finding_id, [])
    return _request("GET", f"/findings/{finding_id}/payload-hits")


def revoke(finding_id: str) -> dict[str, Any]:
    """FND-03 권한 회수."""
    if USE_MOCK:
        _mock_finding(finding_id)["status"] = "revoked"
        return {"finding_id": finding_id, "status": "revoked"}
    return _request("POST", f"/findings/{finding_id}/revoke")


def get_recommendations(finding_id: str) -> list[dict[str, Any]]:
    """FND-04 조치 추천."""
    if USE_MOCK:
        _mock_finding(finding_id)
        return MOCK_RECOMMENDATIONS.get(finding_id, [])
    return _request("GET", f"/findings/{finding_id}/recommendations")


def apply_recommendation(finding_id: str, rec_id: str) -> dict[str, Any]:
    """FND-05 추천 조치 적용."""
    if USE_MOCK:
        finding = _mock_finding(finding_id)
        recs = MOCK_RECOMMENDATIONS.get(finding_id, [])
        rec = next((r for r in recs if r["rec_id"] == rec_id), None)
        if rec is None:
            raise ApiError(404, "NOT_FOUND", "추천 조치가 없습니다", {"rec_id": rec_id})
        before = finding["score"]
        finding.update(status="mitigated", score=rec["expected_score"])
        return {
            "finding_id": finding_id,
            "rec_id": rec_id,
            "status": "mitigated",
            "score_before": before,
            "score_after": rec["expected_score"],
        }
    return _request("POST", f"/findings/{finding_id}/recommendations/{rec_id}/apply")


def get_log(table: str, row_id: str, run_id: str | None = None) -> dict[str, Any]:
    """LOG-01 근거 원본 로그 한 줄."""
    if USE_MOCK:
        return {"table": table, "row": MOCK_LOGS.get((table, row_id), {})}
    params = {"run_id": run_id} if run_id else None
    return _request("GET", f"/logs/{table}/{row_id}", params=params)


def export_run(run_id: str) -> bytes:
    """RUN-06 분석 결과 CSV (utf-8-sig)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        header = "finding_id,employee_name,tool_name,asset_name,score,level,status"
        rows = [
            ",".join(
                [
                    f["finding_id"],
                    f["employee"]["name"],
                    f["tool"]["name"],
                    f["asset"]["name"],
                    str(f["score"]),
                    f["level"],
                    f["status"],
                ]
            )
            for f in MOCK_FINDINGS
        ]
        return "\n".join([header, *rows]).encode("utf-8-sig")
    try:
        response = requests.get(f"{BASE_URL}/runs/{run_id}/export", timeout=15)
    except requests.RequestException as exc:
        raise ApiError(503, "CONNECTION_ERROR", f"백엔드 서버에 연결할 수 없습니다: {exc}") from exc
    if not response.ok:
        try:
            err = response.json().get("error", {})
            raise ApiError(
                response.status_code,
                str(err.get("code", "API_ERROR")),
                str(err.get("message", "CSV 내보내기 실패")),
            )
        except ValueError:
            raise ApiError(response.status_code, "HTTP_ERROR", f"CSV 내보내기 실패 (HTTP {response.status_code})")
    return response.content


# ---- LIVE: 실시간 시연 (LIVE-01~04, 백엔드 LIVE_API_SPEC.md 기준) ----
# live/status, live/reset → {"run_id", "step", "total", "finished", "last_title", "next_title"}
# live/step               → 위 내용 + {"title", "changed", "rows_added", "findings", "events": [...]}
# events 한 건            → {"event_id", "step", "created_at", "type", "finding_id", "message", "detail"}
#   type: new_finding(새 위험 경로) / score_up(점수 상승) / new_payload_hit(새 민감정보 검출)


def _mock_new_finding(n: int, employee: dict, tool: dict, asset: dict,
                      scopes: list[str], score: int, level: str) -> dict[str, Any]:
    return {"finding_id": f"{MOCK_RUN_ID}-F{n:03d}", "employee": employee, "tool": tool,
            "asset": asset, "scopes": scopes, "score": score, "level": level, "status": "open"}


# 백엔드 data/sample/live_script.json 과 같은 4단계
_MOCK_SCENARIO: list[dict[str, Any]] = [
    {
        "title": "Zapier로 고객 연락처 전송",
        "rows_added": 1,
        "score_up": {"finding_id": f"{MOCK_RUN_ID}-F003", "score": 70, "level": "위험"},
        "hits": [("N0007", "전화번호", 2)],
    },
    {
        "title": "이미지 생성 AI가 사내 문서 접근 권한 획득",
        "rows_added": 1,
        "new": _mock_new_finding(
            6, {"id": "E004", "name": "최디자인", "status": "재직"},
            {"id": "T_IMAGE_AI", "name": "이미지 생성 AI", "approved": False},
            {"id": "A05", "name": "사내 문서", "sensitivity": "기밀"},
            ["read", "write"], 45, "주의"),
    },
    {
        "title": "로컬 MCP로 주민번호·이메일 대량 전송",
        "rows_added": 1,
        "score_up": {"finding_id": f"{MOCK_RUN_ID}-F002", "score": 90, "level": "위험"},
        "hits": [("N0008", "주민등록번호", 1), ("N0008", "이메일", 1)],
    },
    {
        "title": "퇴사자 계정으로 n8n이 고객 DB 접근",
        "rows_added": 1,
        "new": _mock_new_finding(
            7, {"id": "E001", "name": "김영업", "status": "퇴사"},
            {"id": "T_N8N", "name": "n8n", "approved": False},
            {"id": "A02", "name": "고객 DB", "sensitivity": "개인정보"},
            ["read", "write"], 100, "위험"),
    },
]

_MOCK_LIVE: dict[str, Any] = {"step": 0, "events": []}


def _path_label(f: dict[str, Any]) -> str:
    return f"{f['employee']['name']} → {f['tool']['name']} → {f['asset']['name']}"


def _mock_live_status() -> dict[str, Any]:
    step, total = _MOCK_LIVE["step"], len(_MOCK_SCENARIO)
    return {
        "run_id": MOCK_RUN_ID,
        "step": step,
        "total": total,
        "finished": step >= total,
        "last_title": _MOCK_SCENARIO[step - 1]["title"] if step > 0 else None,
        "next_title": _MOCK_SCENARIO[step]["title"] if step < total else None,
    }


def _mock_add_event(step: int, kind: str, finding_id: str, message: str) -> dict[str, Any]:
    from datetime import datetime

    event = {
        "event_id": len(_MOCK_LIVE["events"]) + 1,
        "step": step,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "type": kind,
        "finding_id": finding_id,
        "message": message,
        "detail": {},
    }
    _MOCK_LIVE["events"].append(event)
    return event


def live_status(run_id: str) -> dict[str, Any]:
    """LIVE-02 진행 상태 (GET /runs/{run_id}/live/status)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        return _mock_live_status()
    return _request("GET", f"/runs/{run_id}/live/status")


def live_step(run_id: str) -> dict[str, Any]:
    """LIVE-01 대본의 다음 단계 로그를 넣고 재분석 (POST /runs/{run_id}/live/step)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        if _MOCK_LIVE["step"] >= len(_MOCK_SCENARIO):
            return {**_mock_live_status(), "title": None, "changed": False, "rows_added": 0,
                    "findings": len(MOCK_FINDINGS), "events": []}
        scene = _MOCK_SCENARIO[_MOCK_LIVE["step"]]
        _MOCK_LIVE["step"] += 1
        step = _MOCK_LIVE["step"]
        events = []
        if "new" in scene and not any(f["finding_id"] == scene["new"]["finding_id"] for f in MOCK_FINDINGS):
            item = copy.deepcopy(scene["new"])
            MOCK_FINDINGS.append(item)
            events.append(_mock_add_event(
                step, "new_finding", item["finding_id"],
                f"새 위험 경로: {_path_label(item)} ({item['score']}점, {item['level']})"))
        if "score_up" in scene:
            up = scene["score_up"]
            item = next((f for f in MOCK_FINDINGS if f["finding_id"] == up["finding_id"]), None)
            if item and up["score"] > item["score"]:
                before = item["score"]
                item.update(score=up["score"], level=up["level"])  # 회수·조치 상태는 그대로 유지
                events.append(_mock_add_event(
                    step, "score_up", item["finding_id"],
                    f"점수 상승: {_path_label(item)} {before}점 → {item['score']}점"))
        for log_id, kind, count in scene.get("hits", []):
            fid = scene.get("score_up", {}).get("finding_id", "")
            events.append(_mock_add_event(
                step, "new_payload_hit", fid, f"새 민감정보 검출: {kind} {count}건 (로그 {log_id})"))
        return {**_mock_live_status(), "title": scene["title"], "changed": bool(events),
                "rows_added": scene["rows_added"], "findings": len(MOCK_FINDINGS), "events": events}
    return _request("POST", f"/runs/{run_id}/live/step")


def live_reset(run_id: str) -> dict[str, Any]:
    """LIVE-03 처음 상태로 (POST /runs/{run_id}/live/reset). 회수·조치 상태도 초기화된다."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        _MOCK_LIVE["step"] = 0
        _MOCK_LIVE["events"].clear()
        MOCK_FINDINGS[:] = copy.deepcopy(_INITIAL_MOCK_FINDINGS)
        return _mock_live_status()
    return _request("POST", f"/runs/{run_id}/live/reset")


def get_events(run_id: str, after_id: int | None = None) -> list[dict[str, Any]]:
    """LIVE-04 변화 목록, 오래된 순 (GET /runs/{run_id}/events?after_id=)."""
    if not run_id:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if USE_MOCK:
        return [e for e in _MOCK_LIVE["events"] if after_id is None or e["event_id"] > after_id]
    params = {"after_id": after_id} if after_id is not None else None
    return _request("GET", f"/runs/{run_id}/events", params=params)
