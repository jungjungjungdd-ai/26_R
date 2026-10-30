"""실시간 모니터링: 시연 대본을 단계별로 재생하며, 재분석으로 생긴 변화(events)를 피드로 보여 준다.

백엔드 명세: LIVE_API_SPEC.md (LIVE-01 step, LIVE-02 status, LIVE-03 reset, LIVE-04 events)
"""
from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from api import ApiError, USE_MOCK, get_events, get_summary, live_reset, live_status, live_step

INTERVAL_OPTIONS = {"3초": 3, "5초": 5, "10초": 10}
EVENT_ICON = {"new_finding": "🆕", "score_up": "📈", "new_payload_hit": "🔍"}


def add_to_feed(step: int, title: str | None, rows_added: int | None, events: list[dict]) -> None:
    """한 단계의 결과를 피드 맨 위에 쌓는다."""
    st.session_state.live_feed.insert(0, {
        "step": step,
        "title": title,
        "time": datetime.now().strftime("%H:%M:%S"),
        "rows_added": rows_added,
        "events": events,
    })


def rebuild_feed(step: int) -> None:
    """새로고침 등으로 피드가 비었으면 LIVE-04 events 로 다시 채운다 (단계 제목은 복원 불가)."""
    try:
        events = get_events(run_id)
    except ApiError:
        return
    for s in range(1, step + 1):
        add_to_feed(s, None, None, [e for e in events if e.get("step") == s])
    if st.session_state.live_feed:
        st.session_state.live_feed[0]["time"] = "복원"


def do_step() -> None:
    try:
        result = live_step(run_id)
    except ApiError as exc:
        st.session_state.live_running = False
        st.session_state.live_error = exc.message
        return
    if result.get("title"):  # 이미 끝난 뒤 누르면 title 이 None
        add_to_feed(result["step"], result["title"], result.get("rows_added"), result.get("events", []))
        for e in result.get("events", []):
            if e.get("type") in ("new_finding", "score_up"):
                st.toast(f"{EVENT_ICON[e['type']]} {e['message']}")
    if result.get("finished"):
        st.session_state.live_running = False


st.title("📡 실시간 모니터링")
st.caption("새로 들어오는 로그를 바로 재분석해 위험한 AI 자동화 경로의 변화를 실시간으로 보여 줍니다.")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("먼저 업로드하세요. ‘데이터 분석’ 화면에서 파일을 업로드하고 분석을 실행해 주세요.")
    st.stop()

if USE_MOCK:
    st.info("⚪ Mock 시나리오로 재생 중입니다. 처음으로를 누르면 회수·조치 상태도 함께 초기화됩니다.")

st.session_state.setdefault("live_running", False)
st.session_state.setdefault("live_feed", [])
st.session_state.setdefault("live_tick", 0)
if st.session_state.get("live_run_id") != run_id:  # 다른 run 을 새로 올렸으면 피드 초기화
    st.session_state.live_run_id = run_id
    st.session_state.live_feed = []
    st.session_state.live_running = False

# ---- 조작 버튼 ----
c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.2])
if c1.button("▶ 시작", use_container_width=True, disabled=st.session_state.live_running):
    st.session_state.live_running = True
if c2.button("⏸ 일시정지", use_container_width=True, disabled=not st.session_state.live_running):
    st.session_state.live_running = False
if c3.button("⏭ 다음 단계", use_container_width=True):
    do_step()
if c4.button("⏮ 처음으로", use_container_width=True):
    try:
        live_reset(run_id)
        st.session_state.live_feed = []
        st.session_state.live_running = False
    except ApiError as exc:
        st.session_state.live_error = exc.message
interval = INTERVAL_OPTIONS[c5.selectbox("자동 간격", list(INTERVAL_OPTIONS), index=1,
                                         label_visibility="collapsed")]

# ---- 자동 진행: 타이머가 새로 울렸을 때만 한 단계 진행 ----
if st.session_state.live_running:
    tick = st_autorefresh(interval=interval * 1000, key="live-refresh")
    if tick and tick != st.session_state.live_tick:
        st.session_state.live_tick = tick
        do_step()

if st.session_state.get("live_error"):
    st.error(st.session_state.pop("live_error"))

# ---- 진행 상태 ----
try:
    status = live_status(run_id)
except ApiError as exc:
    st.error(exc.message)
    st.stop()

step, total = status.get("step", 0), status.get("total", 0)
if step and not st.session_state.live_feed:
    rebuild_feed(step)

if st.session_state.live_running:
    state_text = "🟢 실시간 수집 중"
elif status.get("finished"):
    state_text = "✅ 시나리오 완료"
else:
    state_text = "⏸ 대기"
st.progress(step / total if total else 0.0, text=f"{state_text} · {step} / {total} 단계")

n1, n2 = st.columns(2)
n1.markdown(f"**방금 일어난 일:** {status.get('last_title') or '아직 시작 전입니다.'}")
n2.markdown(f"**다음 단계:** {status.get('next_title') or '없음 (마지막 단계)'}")

try:
    summary = get_summary(run_id)
    levels = summary.get("levels", {})
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("발견된 AI 도구", summary.get("tools_detected", 0))
    m2.metric("🔴 위험", levels.get("위험", 0))
    m3.metric("🟡 주의", levels.get("주의", 0))
    m4.metric("조치 완료", summary.get("revoked", 0))
except ApiError:
    pass  # 요약을 못 받아도 피드는 보여 준다

# ---- 변화 피드 (최신 단계가 위) ----
st.subheader("탐지 피드")
feed = st.session_state.live_feed
if not feed:
    st.caption("아직 들어온 로그가 없습니다. ▶ 시작 또는 ⏭ 다음 단계를 눌러 보세요.")
for entry in feed:
    is_new = entry["step"] == step
    with st.container(border=True):
        label = f"{entry['step']}단계 · {entry['title']}" if entry["title"] else f"{entry['step']}단계"
        head = f"**{label}** · {entry['time']}"
        if entry["rows_added"] is not None:
            head += f" · 로그 {entry['rows_added']}건 수신"
        if is_new:
            head += " · `NEW`"
        st.markdown(head)
        if not entry["events"]:
            st.caption("위험 변화 없음")
        for e in entry["events"]:
            st.markdown(f"{EVENT_ICON.get(e.get('type'), '•')} {e.get('message', '')}")
