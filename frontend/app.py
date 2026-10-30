import streamlit as st

st.set_page_config(page_title="Shadow AI Radar", page_icon="🛡️", layout="wide")

pages = [
    st.Page("views/upload.py", title="데이터 분석", icon="📤"),
    st.Page("views/overview.py", title="개요", icon="📊", default=True),
    st.Page("views/tools.py", title="AI 도구 목록", icon="🤖"),
    st.Page("views/asset_map.py", title="자산 지도", icon="🗺️"),
]
st.navigation(pages).run()
