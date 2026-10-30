import pandas as pd
import streamlit as st

from api import MOCK_RUN_ID, USE_MOCK, check_backend_health, get_findings, get_summary

st.title("🛡️ 섀도 AI 현황")
st.caption("사내 AI 도구 사용 현황과 직원 → AI 도구 → 회사 자산 접근 경로를 한눈에 확인합니다.")

if USE_MOCK:
    st.info("⚪ Mock 데이터로 화면을 미리 보는 중입니다. Docker Compose 실행 시 실제 백엔드에 연결됩니다.")
elif check_backend_health():
    st.success("🟢 백엔드 API가 정상적으로 연결되었습니다.")
else:
    st.error("🔴 백엔드 API에 연결할 수 없습니다. 서버 실행 상태와 BACKEND_URL을 확인해 주세요.")

run_id = st.session_state.get("run_id") or (MOCK_RUN_ID if USE_MOCK else None)
if not run_id:
    st.info("먼저 ‘데이터 분석’에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

try:
    summary = get_summary(run_id)
    findings = get_findings(run_id)
except Exception as exc:
    st.error(f"분석 결과를 불러오지 못했습니다: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("발견된 AI 도구", summary["tools_detected"])
c2.metric("미승인 도구", summary["unapproved"])
c3.metric("🔴 위험", summary["levels"]["위험"])
c4.metric("조치 완료", summary["revoked"])

st.subheader("위험도 순위")
rows = [{"AI 도구": f["tool"]["name"], "소유자": f["employee"]["name"],
         "승인 여부": "✅ 공식 승인" if f["tool"]["approved"] else "🚨 미승인",
         "접근 자산": f["asset"]["name"], "위험도": f["score"], "등급": f["level"]}
        for f in findings]
if rows:
    st.dataframe(pd.DataFrame(rows).sort_values("위험도", ascending=False),
                 hide_index=True, use_container_width=True)
else:
    st.info("탐지된 접근 경로가 없습니다.")
