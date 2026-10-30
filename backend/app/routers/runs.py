"""Run 도메인: RUN-01 ~ RUN-06 (담당: 테크 리드)"""
import io
import json
import time
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response

from ..db import connect, save_raw
from ..engine import loader, pipeline
from ..errors import ApiError
from .common import finding_to_dict, get_run

router = APIRouter(prefix="/runs", tags=["Run"])

LEVEL_ORDER = {"위험": 0, "주의": 1, "낮음": 2}


def new_run_id(conn) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = conn.execute("SELECT COUNT(*) FROM runs WHERE run_id LIKE ?", (f"R{today}-%",)).fetchone()[0]
    return f"R{today}-{count + 1:02d}"


@router.post("", status_code=201)
async def upload_run(
    employees: UploadFile = File(...),
    assets: UploadFile = File(...),
    ai_tools: UploadFile = File(...),
    network_logs: UploadFile = File(...),
    oauth_grants: UploadFile = File(...),
    asset_activities: UploadFile = File(...),
    processes: UploadFile = File(...),
):
    """RUN-01 로그 파일 7개 업로드, 검증 후 DB 적재"""
    files = {"employees": employees, "assets": assets, "ai_tools": ai_tools, "network_logs": network_logs,
             "oauth_grants": oauth_grants, "asset_activities": asset_activities, "processes": processes}
    frames = {}
    for name, f in files.items():
        df = loader.read_file(name, f.filename, await f.read())
        frames[name] = loader.validate(name, f.filename, df)

    with connect() as conn:
        run_id = new_run_id(conn)
        rows = {name: len(df) for name, df in frames.items()}
        conn.execute("INSERT INTO runs VALUES (?, ?, ?, ?)",
                     (run_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "uploaded",
                      json.dumps(rows, ensure_ascii=False)))
        for name, df in frames.items():
            save_raw(conn, run_id, name, df)
    return {"run_id": run_id, "status": "uploaded", "rows": rows}


@router.post("/{run_id}/analyze")
def analyze_run(run_id: str):
    """RUN-02 탐지, 상관분석, 위험도 산정 실행"""
    with connect() as conn:
        get_run(conn, run_id, need_done=False)
        started = time.perf_counter()
        count = pipeline.run_analysis(conn, run_id)
    return {"run_id": run_id, "status": "done", "findings": count,
            "duration_ms": int((time.perf_counter() - started) * 1000)}


@router.get("/{run_id}/summary")
def run_summary(run_id: str):
    """RUN-03 개요 화면용 요약 숫자"""
    with connect() as conn:
        get_run(conn, run_id)
        rows = conn.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,)).fetchall()
        open_rows = [r for r in rows if r["status"] == "open"]
        tools = {r["tool_id"] for r in rows}
        unapproved = {
            r["tool_id"] for r in rows
            if not conn.execute("SELECT approved FROM ai_tools WHERE run_id = ? AND tool_id = ?",
                                (run_id, r["tool_id"])).fetchone()["approved"]
        }
    levels = {"위험": 0, "주의": 0, "낮음": 0}
    for r in open_rows:
        levels[r["level"]] += 1
    return {"tools_detected": len(tools), "unapproved": len(unapproved), "levels": levels,
            "revoked": sum(r["status"] != "open" for r in rows)}


@router.get("/{run_id}/findings")
def list_findings(run_id: str, level: str | None = None, approved: bool | None = None,
                  status: str | None = None):
    """RUN-04 경로 목록 (점수 높은 순)"""
    with connect() as conn:
        get_run(conn, run_id)
        rows = conn.execute("SELECT * FROM findings WHERE run_id = ? ORDER BY score DESC",
                            (run_id,)).fetchall()
        items = [finding_to_dict(conn, r) for r in rows]
    if level:
        items = [i for i in items if i["level"] == level]
    if approved is not None:
        items = [i for i in items if i["tool"]["approved"] == approved]
    if status:
        items = [i for i in items if i["status"] == status]
    return items


@router.get("/{run_id}/graph")
def run_graph(run_id: str):
    """RUN-05 자산 지도용 노드와 선"""
    items = list_findings(run_id)
    nodes, edges = {}, []
    for i in items:
        if i["employee"]["id"]:
            nodes[i["employee"]["id"]] = {"id": i["employee"]["id"], "label": i["employee"]["name"],
                                          "type": "employee"}
            edges.append({"source": i["employee"]["id"], "target": i["tool"]["id"],
                          "finding_id": i["finding_id"], "level": i["level"]})
        nodes[i["tool"]["id"]] = {"id": i["tool"]["id"], "label": i["tool"]["name"], "type": "tool",
                                  "approved": i["tool"]["approved"]}
        nodes[i["asset"]["id"]] = {"id": i["asset"]["id"], "label": i["asset"]["name"], "type": "asset",
                                   "sensitivity": i["asset"]["sensitivity"]}
        edges.append({"source": i["tool"]["id"], "target": i["asset"]["id"],
                      "finding_id": i["finding_id"], "level": i["level"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@router.get("/{run_id}/export")
def export_run(run_id: str):
    """RUN-06 분석 결과 CSV (선택)"""
    items = list_findings(run_id)
    df = pd.DataFrame([{
        "finding_id": i["finding_id"], "employee_name": i["employee"]["name"], "tool_name": i["tool"]["name"],
        "asset_name": i["asset"]["name"], "score": i["score"], "level": i["level"], "status": i["status"],
    } for i in items])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return Response(buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{run_id}.csv"'})
