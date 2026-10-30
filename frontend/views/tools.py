from html import escape

import pandas as pd
import requests
import streamlit as st

from api import (
    ApiError,
    apply_recommendation,
    export_run,
    get_finding,
    get_findings,
    get_log,
    get_payload_hits,
    get_recommendations,
    revoke,
)

ICON = {"위험": "🔴", "주의": "🟡", "낮음": "🟢"}
STATUS = {"open": "🚨 조치 필요", "revoked": "🔒 회수됨", "mitigated": "🛠️ 완화됨"}
LEVELS = ["전체", "위험", "주의", "낮음"]
APPROVED = {"전체": None, "미승인": False, "승인": True}
STATUSES = {"전체": None, "조치 필요": "open", "회수됨": "revoked", "완화됨": "mitigated"}


def error_text(exc: Exception) -> str:
    """백엔드 공통 에러 형식 {"error": {"message": ...}} 에서 메시지를 꺼낸다."""
    if isinstance(exc, ApiError):
        return exc.message
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            return exc.response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
    return str(exc)


def path_label(f: dict) -> str:
    emp = f["employee"]
    owner = f"{emp['name']}({emp['status']})" if emp.get("status") == "퇴사" else emp["name"]
    return f"{owner} → {f['tool']['name']} → {f['asset']['name']}"


def highlight(text: str, hits: list[dict]) -> str:
    """text[start:end] 구간을 빨간색으로. 뒤쪽 hit부터 잘라 붙여 위치가 밀리지 않게 한다."""
    parts, end = [], len(text)
    for h in sorted(hits, key=lambda h: h["start"], reverse=True):
        s, e = h["start"], min(h["end"], end)
        if s >= e:
            continue
        parts.append(escape(text[e:end]))
        parts.append(
            f'<mark style="background:#FFE5E5;color:#D70015;font-weight:700;padding:2px 6px;border:1px solid #FF3B30;'
            f'border-radius:6px" title="{escape(h["type"])}">{escape(text[s:e])}</mark>'
        )
        end = s
    parts.append(escape(text[:end]))
    return "".join(reversed(parts))


st.title("🤖 탐지 경로")
st.caption("직원 → AI 도구 → 회사 자산 경로별 위험 점수와 근거를 확인하고 조치합니다.")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("먼저 업로드하세요. ‘데이터 분석’ 화면에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

# ---- 필터 + 내보내기 ----
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
level = c1.selectbox("등급", LEVELS)
approved = c2.selectbox("승인 여부", list(APPROVED))
status = c3.selectbox("상태", list(STATUSES))
try:
    c4.download_button(
        "📥 결과 내보내기 (CSV)",
        export_run(run_id),
        file_name=f"{run_id}.csv",
        mime="text/csv",
        use_container_width=True,
    )
except Exception as exc:
    st.error(f"CSV 내보내기 불가: {error_text(exc)}")

try:
    findings = get_findings(
        run_id,
        level=None if level == "전체" else level,
        approved=APPROVED[approved],
        status=STATUSES[status],
    )
except Exception as exc:
    st.error(f"탐지 결과를 불러오지 못했습니다: {error_text(exc)}")
    st.stop()

if not findings:
    st.info("조건에 맞는 경로가 없습니다.")
    st.stop()

findings = sorted(findings, key=lambda f: f["score"], reverse=True)
table = pd.DataFrame(
    [
        {
            "등급": f"{ICON.get(f['level'], '')} {f['level']}",
            "경로": path_label(f),
            "점수": f["score"],
            "승인": "✅" if f["tool"]["approved"] else "❌",
            "상태": STATUS.get(f["status"], f["status"]),
        }
        for f in findings
    ]
)
picked = st.dataframe(
    table,
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
    key="finding-table",
)

ids = [f["finding_id"] for f in findings]
if picked.selection.rows:
    st.session_state["selected_finding_id"] = ids[picked.selection.rows[0]]
fid = st.session_state.get("selected_finding_id")
if fid not in ids:
    fid = st.session_state["selected_finding_id"] = ids[0]

# ---- 상세 ----
st.divider()
try:
    f = get_finding(fid)
except Exception as exc:
    st.error(f"상세 정보를 불러오지 못했습니다: {error_text(exc)}")
    st.stop()

st.subheader(f"{ICON.get(f['level'], '')} {path_label(f)}")
m1, m2, m3, m4 = st.columns(4)
mitigation = st.session_state.get("mitigations", {}).get(fid)
if f["status"] == "mitigated" and mitigation:
    m1.metric(
        "위험 점수",
        mitigation["score_after"],
        delta=mitigation["score_after"] - mitigation["score_before"],
        delta_color="inverse",
    )
else:
    m1.metric("위험 점수", f["score"])
m2.metric("등급", f["level"])
m3.metric("상태", STATUS.get(f["status"], f["status"]))
m4.metric("권한", ", ".join(f.get("scopes", [])) or "-")
st.caption(
    f"도구 {'✅ 회사 승인' if f['tool']['approved'] else '🚨 미승인 Shadow AI'} · "
    f"자산 민감도 {f['asset'].get('sensitivity', '-')} · ID {fid}"
)

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("#### 점수 근거")
    open_logs = st.session_state.setdefault("open_logs", set())
    reasons = f.get("reasons", [])
    if not reasons:
        st.caption("점수 근거가 없습니다.")
    for i, r in enumerate(reasons):
        src = r.get("source") or {}
        key = (fid, src.get("table"), src.get("row_id"))
        a, b = st.columns([4, 1])
        a.markdown(f"`{r['rule_code']}` {r['description']} **+{r['points']}**")
        if src.get("table") and b.button(
            "닫기" if key in open_logs else "원본 보기",
            key=f"log-{fid}-{i}",
            use_container_width=True,
        ):
            open_logs.symmetric_difference_update({key})
            st.rerun()
        if key in open_logs:
            try:
                row = get_log(src["table"], src["row_id"], run_id=run_id)["row"]
                st.caption(f"{src['table']} / {src['row_id']}")
                st.dataframe(
                    pd.DataFrame({"필드": list(row), "값": [str(v) for v in row.values()]}),
                    hide_index=True,
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"원본 로그를 불러오지 못했습니다: {error_text(exc)}")

    st.markdown("#### 민감정보 검출 내역")
    try:
        payloads = get_payload_hits(fid)
    except Exception as exc:
        payloads = []
        st.error(f"검출 내역을 불러오지 못했습니다: {error_text(exc)}")
    if not payloads:
        st.caption("전송 내용에서 검출된 민감정보가 없습니다.")
    for p in payloads:
        types = ", ".join(sorted({h["type"] for h in p["hits"]}))
        st.caption(f"로그 {p['log_id']} · {types}")
        st.markdown(
            f'<div style="font-family:monospace;background:#FFFFFF;color:#1D1D1F;border:1px solid rgba(0,0,0,0.08);box-shadow:0 2px 10px rgba(0,0,0,0.03);padding:12px 16px;'
            f'border-radius:6px">{highlight(p["text"], p["hits"])}</div>',
            unsafe_allow_html=True,
        )

with right:
    st.markdown("#### 조치")
    if f["status"] == "revoked":
        st.success("🔒 회수됨 — 이 경로의 권한이 회수되었습니다.")
    elif f["tool"]["approved"]:
        st.info("회사에서 승인한 도구이므로 회수 대상이 아닙니다.")
    elif st.button("권한 회수", type="primary", key=f"revoke-{fid}", use_container_width=True):
        try:
            revoke(fid)
            st.toast("권한을 회수했습니다.", icon="🔒")
            st.rerun()
        except Exception as exc:
            st.error(f"권한 회수 실패: {error_text(exc)}")

    if f["status"] == "mitigated":
        if mitigation:
            st.success(f"🛠️ 완화됨 — 점수 {mitigation['score_before']} → {mitigation['score_after']}")
        else:
            st.success("🛠️ 완화됨 — 추천 조치가 적용되었습니다.")

    st.markdown("#### 조치 추천")
    try:
        recs = get_recommendations(fid)
    except Exception as exc:
        recs = []
        st.error(f"추천을 불러오지 못했습니다: {error_text(exc)}")
    if not recs:
        st.caption("추천 조치가 없습니다.")
    for rec in recs:
        with st.container(border=True):
            arrow = f"{f['score']} → " if f["status"] == "open" else ""
            st.markdown(f"**{rec['action']}** · 예상 점수 {arrow}{rec['expected_score']}")
            st.caption(rec["description"])
            if f["status"] == "open" and st.button("적용", key=f"apply-{fid}-{rec['rec_id']}"):
                try:
                    result = apply_recommendation(fid, rec["rec_id"])
                    st.session_state.setdefault("mitigations", {})[fid] = result
                    st.toast(
                        f"조치 적용: {result['score_before']} → {result['score_after']}점",
                        icon="🛠️",
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"조치 적용 실패: {error_text(exc)}")
