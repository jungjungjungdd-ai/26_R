import streamlit as st

from api import ApiError, get_tools, revoke_tool

ICON = {"위험": "🔴", "주의": "🟡", "낮음": "🟢"}

if "revoked" not in st.session_state:
    st.session_state.revoked = set()

st.title("🤖 AI 도구 목록")
st.caption("도구별 승인 여부와 위험 점수를 확인하고, 미승인 도구의 권한을 회수할 수 있습니다.")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("먼저 업로드하세요. ‘데이터 분석’ 화면에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

try:
    tools = get_tools(run_id)
except ApiError as exc:
    st.error(exc.message)
    st.stop()
except Exception as exc:
    st.error(str(exc))
    st.stop()

for t in sorted(tools, key=lambda x: x["score"], reverse=True):
    title = f"{ICON[t['level']]} {t['name']} — {t['owner']} ({t['score']}점)"
    with st.expander(title):
        st.write("**접근 자산:**", ", ".join(t["assets"]))
        st.write("**승인 여부:**", "✅ 회사 공식 승인 도구" if t["approved"] else "🚨 미승인 Shadow AI")
        st.write("**점수 근거**")
        for reason in t["reasons"]:
            st.write(f"- {reason}")

        if t["id"] in st.session_state.revoked:
            st.success("🔒 권한 회수 완료")
        elif not t["approved"] and st.button("권한 회수", key=f"revoke-{t['id']}"):
            try:
                revoke_tool(t["id"])
                st.session_state.revoked.add(t["id"])
                st.rerun()
            except ApiError as exc:
                st.error(exc.message)
        elif t["approved"]:
            st.info("회사에서 승인한 도구이므로 회수 대상이 아닙니다.")
