import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from api import get_tools

COLOR = {"위험": "#EF4444", "주의": "#F59E0B", "낮음": "#22C55E"}

st.title("🗺️ 자산 지도")
st.caption("어떤 AI 도구가 어떤 회사 자산에 접근하는지")

tools = get_tools()
nodes, edges, assets = [], [], set()

for t in tools:
    nodes.append(Node(id=t["id"], label=t["name"], size=25, color=COLOR[t["level"]]))
    for a in t["assets"]:
        assets.add(a)
        edges.append(Edge(source=t["id"], target=f"asset:{a}"))

for a in assets:
    nodes.append(Node(id=f"asset:{a}", label=a, size=30, color="#64748B", shape="box"))

agraph(nodes=nodes, edges=edges, config=Config(width=1000, height=550, directed=True, physics=True))
