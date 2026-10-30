"""분석 파이프라인: loader 이후 단계를 순서대로 실행하고 결과를 저장 (담당: 테크 리드)

detector → payload_scanner → correlator → scorer → (recommender) → DB 저장
각 담당자는 자기 단계 함수만 완성하면 되고, 이 파일은 고치지 않아도 됩니다.
"""
import sqlite3

from ..db import RAW_TABLES, read_raw
from . import correlator, detector, payload_scanner, recommender, scorer


def path_key(path: dict) -> tuple[str, str, str]:
    """경로를 식별하는 키 (직원 + 도구 + 자산)."""
    return (path.get("employee_id") or "", path["tool_id"], path["asset_id"])


def assign_finding_ids(conn: sqlite3.Connection, run_id: str, paths: list[dict]) -> dict[tuple[str, str, str], str]:
    """같은 (직원, 도구, 자산) 경로에는 항상 같은 finding_id 를 준다.

    번호는 한 번 정해지면 `finding_ids` 표에 남아 재분석해도 바뀌지 않는다.
    처음 보는 경로는 지금까지 쓴 번호 다음 번호를 받는다.
    """
    rows = conn.execute("SELECT employee_id, tool_id, asset_id, seq FROM finding_ids WHERE run_id = ?",
                        (run_id,)).fetchall()
    seqs = {(r["employee_id"], r["tool_id"], r["asset_id"]): r["seq"] for r in rows}
    next_seq = max(seqs.values(), default=0) + 1

    ids = {}
    for key in sorted({path_key(path) for path in paths}):
        seq = seqs.get(key)
        if seq is None:
            seq = next_seq
            next_seq += 1
            conn.execute(
                "INSERT INTO finding_ids (run_id, employee_id, tool_id, asset_id, seq) VALUES (?, ?, ?, ?, ?)",
                (run_id, *key, seq),
            )
        ids[key] = f"{run_id}-F{seq:03d}"
    return ids


def run_analysis(conn: sqlite3.Connection, run_id: str) -> int:
    tables = {name: read_raw(conn, run_id, name) for name in RAW_TABLES}

    usage = detector.detect_tools(tables["network_logs"], tables["processes"], tables["ai_tools"])
    hits = payload_scanner.scan_logs(tables["network_logs"])
    paths = correlator.build_paths(usage, hits, tables)
    finding_ids = assign_finding_ids(conn, run_id, paths)

    # 이전 분석 결과 지우기 (같은 run 을 다시 분석할 때)
    old = [r[0] for r in conn.execute("SELECT finding_id FROM findings WHERE run_id = ?", (run_id,))]
    for table in ("finding_reasons", "recommendations"):
        conn.executemany(f"DELETE FROM {table} WHERE finding_id = ?", [(f,) for f in old])
    conn.execute("DELETE FROM findings WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM payload_hits WHERE run_id = ?", (run_id,))

    for path in paths:
        finding_id = finding_ids[path_key(path)]
        result = scorer.score(path)
        conn.execute(
            "INSERT INTO findings (finding_id, run_id, employee_id, tool_id, asset_id, scopes, score, level) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (finding_id, run_id, path["employee_id"], path["tool_id"], path["asset_id"],
             ",".join(path["scopes"]), result["score"], result["level"]),
        )
        for r in result["reasons"]:
            conn.execute(
                "INSERT INTO finding_reasons (finding_id, rule_code, points, description, source_table, source_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (finding_id, r["rule_code"], r["points"], r["description"],
                 r["source"]["table"], r["source"]["row_id"]),
            )
        for _, h in hits[hits["log_id"].isin(path["payload_log_ids"])].iterrows():
            conn.execute(
                "INSERT INTO payload_hits (run_id, finding_id, log_id, type, start_pos, end_pos) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, finding_id, h["log_id"], h["type"], int(h["start"]), int(h["end"])),
            )
        for rec in recommender.recommend(path, result["score"]):
            conn.execute(
                "INSERT INTO recommendations (rec_id, finding_id, action, description, expected_score) "
                "VALUES (?, ?, ?, ?, ?)",
                (rec["rec_id"], finding_id, rec["action"], rec["description"], rec["expected_score"]),
            )

    conn.execute("UPDATE runs SET status = 'done' WHERE run_id = ?", (run_id,))
    conn.commit()
    return len(paths)
