import streamlit as st
from api import get_tools, revoke_tool

ICON = {"위험": "🔴", "주의": "🟡", "낮음": "🟢"}

if "revoked" not in st.session_state:
    st.session_state.revoked = set()

st.title("🤖 AI 도구 목록")

for t in sorted(get_tools(), key=lambda x: x["score"], reverse=True):
    title = f"{ICON[t['level']]} {t['name']} — {t['owner']} ({t['score']}점)"
    with st.expander(title):
        st.write("**접근 자산:**", ", ".join(t["assets"]))
        st.write("**점수 근거**")
        for reason in t["reasons"]:
            st.write(f"- {reason}")

        if t["id"] in st.session_state.revoked:
            st.success("권한 회수됨")
        elif not t["approved"] and st.button("권한 회수", key=f"revoke-{t['id']}"):
            revoke_tool(t["id"])
            st.session_state.revoked.add(t["id"])
            st.rerun()
