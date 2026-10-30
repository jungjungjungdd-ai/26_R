"""프론트 화면과 FastAPI 사이의 API 클라이언트."""
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

MOCK_FINDINGS: list[dict[str, Any]] = [
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


def check_backend_health() -> bool:
    """백엔드 상태 확인 불리언 헬퍼. mock 모드에서는 실제 서버를 호출하지 않는다."""
    if USE_MOCK:
        return False
    try:
        return health().get("status") == "ok"
    except ApiError:
        return False


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
        for finding in MOCK_FINDINGS:
            finding["status"] = "open"
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


# 하위 호환용 별칭
analyze_run = analyze


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


# F2 작업 전까지 기존 도구 목록 화면을 유지하기 위한 임시 호환 함수.
def get_tools(run_id: str | None = None) -> list[dict[str, Any]]:
    target_run_id = run_id or MOCK_RUN_ID
    return [
        {
            "id": f["finding_id"],
            "name": f["tool"]["name"],
            "owner": f["employee"]["name"],
            "approved": f["tool"]["approved"],
            "assets": [f["asset"]["name"]],
            "score": f["score"],
            "level": f["level"],
            "status": f["status"],
            "reasons": ["상세 근거는 F2 화면에서 연결 예정"],
        }
        for f in get_findings(target_run_id)
    ]


def revoke_tool(finding_id: str) -> dict[str, Any]:
    if USE_MOCK:
        for finding in MOCK_FINDINGS:
            if finding["finding_id"] == finding_id:
                finding["status"] = "revoked"
                return {"finding_id": finding_id, "status": "revoked"}
        raise ApiError(
            status_code=404,
            code="NOT_FOUND",
            message="경로가 없습니다",
            detail={"finding_id": finding_id},
        )
    return _request("POST", f"/findings/{finding_id}/revoke")
