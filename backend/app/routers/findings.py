"""Finding 도메인: FND-01 ~ FND-05 (담당: 위험도)"""
from fastapi import APIRouter

from ..db import connect
from ..errors import ApiError
from .common import finding_to_dict, get_finding_row

router = APIRouter(prefix="/findings", tags=["Finding"])


@router.get("/{finding_id}")
def get_finding(finding_id: str):
    """FND-01 경로 상세와 점수 근거"""
    with connect() as conn:
        row = get_finding_row(conn, finding_id)
        item = finding_to_dict(conn, row)
        reasons = conn.execute("SELECT * FROM finding_reasons WHERE finding_id = ? ORDER BY reason_id",
                               (finding_id,)).fetchall()
    item["reasons"] = [{"rule_code": r["rule_code"], "points": r["points"], "description": r["description"],
                        "source": {"table": r["source_table"], "row_id": r["source_id"]}} for r in reasons]
    return item


@router.get("/{finding_id}/payload-hits")
def payload_hits(finding_id: str):
    """FND-02 전송 내용 원문과 하이라이트 위치. 로그가 여러 개면 로그별로 묶어 리스트로 반환."""
    with connect() as conn:
        row = get_finding_row(conn, finding_id)
        hits = conn.execute("SELECT * FROM payload_hits WHERE finding_id = ? ORDER BY log_id, start_pos",
                            (finding_id,)).fetchall()
        result = {}
        for h in hits:
            if h["log_id"] not in result:
                log = conn.execute("SELECT payload_sample FROM network_logs WHERE run_id = ? AND log_id = ?",
                                   (row["run_id"], h["log_id"])).fetchone()
                result[h["log_id"]] = {"log_id": h["log_id"], "text": log["payload_sample"] if log else "",
                                       "hits": []}
            result[h["log_id"]]["hits"].append({"type": h["type"], "start": h["start_pos"], "end": h["end_pos"]})
    return list(result.values())


@router.post("/{finding_id}/revoke")
def revoke(finding_id: str):
    """FND-03 권한 회수 (상태만 변경)"""
    with connect() as conn:
        get_finding_row(conn, finding_id)
        conn.execute("UPDATE findings SET status = 'revoked' WHERE finding_id = ?", (finding_id,))
    return {"finding_id": finding_id, "status": "revoked"}


@router.get("/{finding_id}/recommendations")
def recommendations(finding_id: str):
    """FND-04 조치 추천 (선택)"""
    with connect() as conn:
        get_finding_row(conn, finding_id)
        rows = conn.execute("SELECT * FROM recommendations WHERE finding_id = ?", (finding_id,)).fetchall()
    return [{"rec_id": r["rec_id"], "action": r["action"], "description": r["description"],
             "expected_score": r["expected_score"]} for r in rows]


@router.post("/{finding_id}/recommendations/{rec_id}/apply")
def apply_recommendation(finding_id: str, rec_id: str):
    """FND-05 추천 조치 적용 (선택, 상태와 점수만 변경)"""
    with connect() as conn:
        row = get_finding_row(conn, finding_id)
        rec = conn.execute("SELECT * FROM recommendations WHERE finding_id = ? AND rec_id = ?",
                           (finding_id, rec_id)).fetchone()
        if rec is None:
            raise ApiError(404, "NOT_FOUND", "추천 조치가 없습니다", {"rec_id": rec_id})
        conn.execute("UPDATE findings SET status = 'mitigated', score = ? WHERE finding_id = ?",
                     (rec["expected_score"], finding_id))
        conn.execute("UPDATE recommendations SET applied = 1 WHERE finding_id = ? AND rec_id = ?",
                     (finding_id, rec_id))
    return {"finding_id": finding_id, "rec_id": rec_id, "status": "mitigated",
            "score_before": row["score"], "score_after": rec["expected_score"]}
