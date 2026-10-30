"""자산 지도: 직원 → AI 도구 → 회사 자산 경로를 왼쪽에서 오른쪽 3열로 보여 준다."""
import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from api import ApiError, get_findings

LEVEL_COLOR = {"위험": "#EF4444", "주의": "#F59E0B", "낮음": "#22C55E"}
LEVEL_RANK = {"위험": 3, "주의": 2, "낮음": 1}
LEVEL_WIDTH = {"위험": 5, "주의": 3, "낮음": 2}
DONE_COLOR = "#475569"  # 회수·조치 완료된 경로
TEXT = "#F3F4F6"
BG = "#0B1220"
SENSITIVITY_BORDER = {"개인정보": "#EF4444", "기밀": "#F59E0B", "일반": "#94A3B8"}
COLUMN = {"employee": 0, "tool": 1, "asset": 2}
STATUS_TEXT = {"open": "조치 필요", "revoked": "회수됨", "mitigated": "완화됨"}


def node_style(background: str, border: str) -> dict:
    return {"background": background, "border": border,
            "highlight": {"background": background, "border": "#FFFFFF"},
            "hover": {"background": background, "border": "#FFFFFF"}}


def make_node(node_id: str, kind: str, label: str, tooltip: str, background: str, border: str) -> Node:
    return Node(id=node_id, label=label, title=tooltip, shape="box", level=COLUMN[kind],
                color=node_style(background, border), borderWidth=2, borderWidthSelected=3,
                margin=14, widthConstraint={"minimum": 170, "maximum": 210},
                font={"color": TEXT, "size": 20, "face": "Pretendard, Malgun Gothic, sans-serif"})


def worst(items: list[dict]) -> dict:
    """여러 경로가 같은 선을 쓰면 가장 위험한 경로 기준으로 그린다."""
    open_items = [f for f in items if f["status"] == "open"]
    pool = open_items or items
    top = max(pool, key=lambda f: (LEVEL_RANK.get(f["level"], 0), f["score"]))
    return {"level": top["level"], "score": top["score"], "done": not open_items}


def make_edge(source: str, target: str, info: dict, show_score: bool) -> Edge:
    color = DONE_COLOR if info["done"] else LEVEL_COLOR.get(info["level"], "#94A3B8")
    extra = {}
    if show_score:
        extra["label"] = f"{info['score']}점" + (" ✔" if info["done"] else "")
        extra["font"] = {"color": TEXT, "size": 18, "strokeWidth": 0, "background": BG, "align": "middle"}
    return Edge(source=source, target=target, color=color,
                width=1.5 if info["done"] else LEVEL_WIDTH.get(info["level"], 2),
                dashes=info["done"],
                smooth={"type": "cubicBezier", "forceDirection": "horizontal", "roundness": 0.45},
                **extra)


st.title("🗺️ 자산 지도")
st.caption("직원 → AI 도구 → 회사 자산 순서로, 누가 어떤 AI로 무엇에 접근하는지 보여 줍니다. "
           "선이 굵고 빨갈수록 위험합니다.")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("먼저 업로드하세요. ‘데이터 분석’ 화면에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

try:
    findings = get_findings(run_id)
except ApiError as exc:
    st.error(exc.message)
    st.stop()
except Exception as exc:  # noqa: BLE001
    st.error(str(exc))
    st.stop()

if not findings:
    st.info("표시할 접근 경로가 없습니다.")
    st.stop()

# ---- 필터 ----
def name_of(part: dict) -> str:
    return part.get("name") or part.get("id") or "알 수 없음"


focus_options = ["전체 보기"]
focus_options += sorted({f"👤 {name_of(f['employee'])}" for f in findings if f["employee"].get("id")})
focus_options += sorted({f"🤖 {name_of(f['tool'])}" for f in findings})
focus_options += sorted({f"🗄️ {name_of(f['asset'])}" for f in findings})

c1, c2, c3 = st.columns([2, 2, 1.3])
levels = c1.multiselect("등급", ["위험", "주의", "낮음"], default=["위험", "주의", "낮음"])
focus = c2.selectbox("특정 대상만 보기", focus_options)
hide_done = c3.toggle("조치 완료 숨기기", value=False)
show_score = c3.toggle("점수 표시", value=True)

shown = [f for f in findings if f["level"] in levels and not (hide_done and f["status"] != "open")]
if focus != "전체 보기":
    icon, name = focus.split(" ", 1)
    part = {"👤": "employee", "🤖": "tool", "🗄️": "asset"}[icon]
    shown = [f for f in shown if name_of(f[part]) == name]

open_shown = [f for f in shown if f["status"] == "open"]
m1, m2, m3, m4 = st.columns(4)
m1.metric("표시 중인 경로", len(shown))
m2.metric("🔴 위험", sum(f["level"] == "위험" for f in open_shown))
m3.metric("🟡 주의", sum(f["level"] == "주의" for f in open_shown))
m4.metric("✔ 조치 완료", len(shown) - len(open_shown))

if not shown:
    st.info("조건에 맞는 경로가 없습니다. 필터를 바꿔 보세요.")
    st.stop()

# ---- 노드와 선 만들기 ----
nodes: dict[str, Node] = {}
emp_tool: dict[tuple[str, str], list[dict]] = {}
tool_asset: dict[tuple[str, str], list[dict]] = {}

for f in sorted(shown, key=lambda x: x["score"], reverse=True):  # 위험한 경로가 위로
    emp, tool, asset = f["employee"], f["tool"], f["asset"]
    tool_id, asset_id = f"tool:{tool['id']}", f"asset:{asset['id']}"

    if emp.get("id"):
        emp_id = f"emp:{emp['id']}"
        retired = emp.get("status") == "퇴사"
        nodes.setdefault(emp_id, make_node(
            emp_id, "employee",
            f"👤 {name_of(emp)}" + ("\n⚠ 퇴사자" if retired else ""),
            f"직원 {name_of(emp)} ({emp.get('status', '')})",
            "#1E3A8A", "#EF4444" if retired else "#60A5FA"))
        emp_tool.setdefault((emp_id, tool_id), []).append(f)

    approved = tool.get("approved")
    nodes.setdefault(tool_id, make_node(
        tool_id, "tool",
        f"🤖 {name_of(tool)}\n" + ("✅ 승인" if approved else "🚫 미승인"),
        f"AI 도구 {name_of(tool)} ({'회사 승인' if approved else '미승인'})",
        "#3B1D6E", "#22C55E" if approved else "#A78BFA"))

    sensitivity = asset.get("sensitivity", "일반")
    nodes.setdefault(asset_id, make_node(
        asset_id, "asset",
        f"🗄️ {name_of(asset)}\n{sensitivity}",
        f"회사 자산 {name_of(asset)} (민감도: {sensitivity})",
        "#1F2937", SENSITIVITY_BORDER.get(sensitivity, "#94A3B8")))
    tool_asset.setdefault((tool_id, asset_id), []).append(f)

edges = [make_edge(s, t, worst(items), False) for (s, t), items in emp_tool.items()]
edges += [make_edge(s, t, worst(items), show_score) for (s, t), items in tool_asset.items()]

# ---- 위치 직접 계산 (선이 덜 꼬이게) ----
# 직원: 위험한 경로 순서대로 위에서부터
# 도구: 연결된 직원들의 평균 높이 / 자산: 연결된 도구들의 평균 높이
COL_GAP, ROW_GAP = 320, 110


def order_by_parents(children: list[str], links: dict, parent_row: dict) -> list[str]:
    def center(child: str) -> float:
        rows = [parent_row[p] for (p, c) in links if c == child and p in parent_row]
        return sum(rows) / len(rows) if rows else float("inf")
    return sorted(children, key=lambda c: (center(c), children.index(c)))


columns = {kind: [nid for nid, n in nodes.items() if n.level == col] for kind, col in COLUMN.items()}
emp_row = {nid: i for i, nid in enumerate(columns["employee"])}
tool_order = order_by_parents(columns["tool"], emp_tool, emp_row)
tool_row = {nid: i for i, nid in enumerate(tool_order)}
asset_order = order_by_parents(columns["asset"], tool_asset, tool_row)

ordered = {"employee": columns["employee"], "tool": tool_order, "asset": asset_order}
per_column = max(len(ids) for ids in ordered.values())
for kind, ids in ordered.items():
    offset = (per_column - len(ids)) * ROW_GAP / 2  # 개수가 적은 열은 가운데로
    for i, nid in enumerate(ids):
        nodes[nid].x = COLUMN[kind] * COL_GAP
        nodes[nid].y = offset + i * ROW_GAP

config = Config(height=max(360, per_column * ROW_GAP + 90), width=1000, directed=True,
                physics=False, hierarchical=False,
                interaction={"hover": True, "tooltipDelay": 150, "zoomView": True, "dragView": True},
                edges={"arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}})
config.width = "100%"

selected = agraph(nodes=list(nodes.values()), edges=edges, config=config)

st.markdown(
    "<div style='display:flex;flex-wrap:wrap;gap:18px;font-size:0.9rem;color:#CBD5E1'>"
    "<span><span style='color:#EF4444'>━━</span> 위험</span>"
    "<span><span style='color:#F59E0B'>━━</span> 주의</span>"
    "<span><span style='color:#22C55E'>━━</span> 낮음</span>"
    "<span><span style='color:#475569'>┅┅</span> 조치 완료</span>"
    "<span>자산 테두리: <span style='color:#EF4444'>개인정보</span> · "
    "<span style='color:#F59E0B'>기밀</span> · <span style='color:#94A3B8'>일반</span></span>"
    "<span>빨간 테두리 직원 = 퇴사자</span>"
    "</div>",
    unsafe_allow_html=True,
)

# ---- 경로 표 (노드를 누르면 그 노드가 들어간 경로만) ----
table = shown
if selected and selected in nodes:  # 필터를 바꾸면 이전에 누른 노드가 없을 수 있다
    kind, raw_id = selected.split(":", 1)
    part = {"emp": "employee", "tool": "tool", "asset": "asset"}[kind]
    table = [f for f in shown if f[part].get("id") == raw_id]
    st.subheader(f"선택한 노드의 경로 · {nodes[selected].label.splitlines()[0]}")
else:
    st.subheader("경로 목록")
    st.caption("지도에서 노드를 누르면 그 노드가 들어간 경로만 보여 줍니다.")

st.dataframe(
    pd.DataFrame([{
        "직원": f"{name_of(f['employee'])} ({f['employee'].get('status', '')})" if f["employee"].get("id") else "-",
        "AI 도구": name_of(f["tool"]) + ("" if f["tool"].get("approved") else " 🚫"),
        "회사 자산": f"{name_of(f['asset'])} ({f['asset'].get('sensitivity', '')})",
        "점수": f["score"],
        "등급": f["level"],
        "상태": STATUS_TEXT.get(f["status"], f["status"]),
    } for f in sorted(table, key=lambda x: x["score"], reverse=True)]),
    hide_index=True, use_container_width=True,
    column_config={"점수": st.column_config.ProgressColumn("점수", min_value=0, max_value=100, format="%d")},
)
