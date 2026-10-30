import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from api import ApiError, get_graph

COLOR = {"위험": "#EF4444", "주의": "#F59E0B", "낮음": "#22C55E"}
TYPE_COLOR = {"employee": "#3B82F6", "tool": "#8B5CF6", "asset": "#64748B"}

st.title("🗺️ 자산 지도")
st.caption("어떤 직원이 어떤 AI 도구를 통해 회사 자산에 접근했는지 연결 관계로 확인합니다.")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("먼저 업로드하세요. ‘데이터 분석’ 화면에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

try:
    graph = get_graph(run_id)
except ApiError as exc:
    st.error(exc.message)
    st.stop()
except Exception as exc:
    st.error(str(exc))
    st.stop()

nodes = [
    Node(
        id=node["id"],
        label=node["label"],
        size=30 if node["type"] == "asset" else 25,
        color=TYPE_COLOR.get(node["type"], "#64748B"),
        shape="box" if node["type"] == "asset" else "dot",
    )
    for node in graph.get("nodes", [])
]
edges = [
    Edge(
        source=edge["source"],
        target=edge["target"],
        color=COLOR.get(edge.get("level"), "#94A3B8"),
    )
    for edge in graph.get("edges", [])
]

if nodes:
    agraph(
        nodes=nodes,
        edges=edges,
        config=Config(width=1000, height=550, directed=True, physics=True),
    )
    st.markdown("#### 범례")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.markdown("🔵 **직원 (employee)**")
    c2.markdown("🟣 **AI 도구 (tool)**")
    c3.markdown("⬜ **회사 자산 (asset)**")
    c4.markdown("🔴 **위험 경로**")
    c5.markdown("🟡 **주의 경로**")
    c6.markdown("🟢 **낮음 경로**")
else:
    st.info("표시할 접근 경로가 없습니다.")
