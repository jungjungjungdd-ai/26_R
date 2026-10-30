import streamlit as st
import pandas as pd
from api import get_tools

tools = get_tools()

st.title("🛡️ 섀도 AI 현황")
st.caption("회사 승인 없이 사용 중인 AI 도구와 위험도")

c1, c2, c3, c4 = st.columns(4)
c1.metric("발견된 AI 도구", len(tools))
c2.metric("🔴 위험", sum(t["level"] == "위험" for t in tools))
c3.metric("🟡 주의", sum(t["level"] == "주의" for t in tools))
c4.metric("🟢 낮음", sum(t["level"] == "낮음" for t in tools))

st.subheader("위험도 순위")
df = pd.DataFrame(tools)[["name", "owner", "score", "level"]]
df.columns = ["AI 도구", "소유자", "위험도", "등급"]
st.dataframe(df.sort_values("위험도", ascending=False), hide_index=True)
