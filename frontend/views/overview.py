import pandas as pd
import streamlit as st

from api import ApiError, USE_MOCK, get_findings, get_summary, health

st.title("🛡️ 섀도 AI 현황")
st.caption("사내 AI 도구 사용 현황과 직원 → AI 도구 → 회사 자산 접근 경로를 한눈에 확인합니다.")

if USE_MOCK:
    st.info("⚪ Mock 데이터로 화면을 미리 보는 중입니다. Docker Compose 실행 시 실제 백엔드에 연결됩니다.")
else:
    try:
        if health().get("status") == "ok":
            st.success("🟢 백엔드 API가 정상적으로 연결되었습니다.")
        else:
            st.error("🔴 백엔드 API 응답이 비정상입니다.")
    except ApiError as exc:
        st.error(exc.message)

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("먼저 업로드하세요. ‘데이터 분석’ 화면에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

try:
    summary = get_summary(run_id)
    findings = get_findings(run_id)
except ApiError as exc:
    st.error(exc.message)
    st.stop()
except Exception as exc:
    st.error(str(exc))
    st.stop()

levels = summary.get("levels", {})
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("발견된 AI 도구", summary.get("tools_detected", 0))
c2.metric("미승인 도구", summary.get("unapproved", 0))
c3.metric("🔴 위험", levels.get("위험", 0))
c4.metric("🟡 주의", levels.get("주의", 0))
c5.metric("🟢 낮음", levels.get("낮음", 0))
c6.metric("조치 완료", summary.get("revoked", 0))

st.subheader("위험도 순위")
rows = [
    {
        "경로 ID": f["finding_id"],
        "직원": f"{f['employee']['name']} ({f['employee']['status']})",
        "AI 도구": f["tool"]["name"],
        "승인 여부": "✅ 공식 승인" if f["tool"]["approved"] else "🚨 미승인",
        "접근 자산": f"{f['asset']['name']} ({f['asset']['sensitivity']})",
        "권한/행동": ", ".join(f.get("scopes", [])),
        "위험도": f["score"],
        "등급": f["level"],
        "상태": f["status"],
    }
    for f in findings
]
if rows:
    st.dataframe(
        pd.DataFrame(rows).sort_values("위험도", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("탐지된 접근 경로가 없습니다.")
