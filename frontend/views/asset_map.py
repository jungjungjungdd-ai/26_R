import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from api import MOCK_RUN_ID, USE_MOCK, get_graph

COLOR = {"위험": "#EF4444", "주의": "#F59E0B", "낮음": "#22C55E"}
TYPE_COLOR = {"employee": "#3B82F6", "tool": "#8B5CF6", "asset": "#64748B"}

st.title("🗺️ 자산 지도")
st.caption("어떤 직원이 어떤 AI 도구를 통해 회사 자산에 접근했는지 연결 관계로 확인합니다.")

run_id = st.session_state.get("run_id") or (MOCK_RUN_ID if USE_MOCK else None)
if not run_id:
    st.info("먼저 ‘데이터 분석’에서 분석을 실행해 주세요.")
    st.stop()

try:
    graph = get_graph(run_id)
except Exception as exc:
    st.error(f"자산 지도를 불러오지 못했습니다: {exc}")
    st.stop()

nodes = [Node(id=node["id"], label=node["label"],
              size=30 if node["type"] == "asset" else 25,
              color=TYPE_COLOR.get(node["type"], "#64748B"),
              shape="box" if node["type"] == "asset" else "dot")
         for node in graph["nodes"]]
edges = [Edge(source=edge["source"], target=edge["target"],
              color=COLOR.get(edge.get("level"), "#94A3B8"))
         for edge in graph["edges"]]

if nodes:
    agraph(nodes=nodes, edges=edges,
           config=Config(width=1000, height=550, directed=True, physics=True))
    st.markdown("#### 범례")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown("🔵 **직원**")
    c2.markdown("🟣 **AI 도구**")
    c3.markdown("⬜ **회사 자산**")
    c4.markdown("🔴 **위험 경로**")
    c5.markdown("🟡 **주의 경로**")
else:
    st.info("표시할 접근 경로가 없습니다.")
