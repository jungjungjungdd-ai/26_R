import streamlit as st

from api import USE_MOCK, analyze_run, upload_run

FILES = {
    "employees": ("직원", ["csv"]),
    "assets": ("회사 자산", ["csv"]),
    "ai_tools": ("AI 도구 카탈로그", ["json"]),
    "network_logs": ("네트워크 로그", ["csv"]),
    "oauth_grants": ("OAuth 권한", ["csv"]),
    "asset_activities": ("자산 활동", ["csv"]),
    "processes": ("프로세스 실행 기록", ["csv"]),
}

st.title("📤 데이터 업로드 및 분석")
st.caption("직원·자산·AI 도구·네트워크 로그 등 필수 파일 7개를 검증한 뒤 위험 경로를 분석합니다.")
if USE_MOCK:
    st.info("현재는 mock 모드입니다. 파일 내용은 서버로 전송되지 않습니다.")

uploaded = {}
left, right = st.columns(2)
for index, (key, (label, extensions)) in enumerate(FILES.items()):
    with (left if index % 2 == 0 else right):
        uploaded[key] = st.file_uploader(label, type=extensions, key=f"upload-{key}")

all_ready = all(uploaded.values())
if st.button("업로드하고 분석 실행", type="primary", disabled=not all_ready,
             use_container_width=True):
    try:
        with st.status("분석을 준비하는 중입니다...", expanded=True) as progress:
            st.write("1/2 파일을 업로드하고 형식을 검증하고 있습니다.")
            upload_result = upload_run(uploaded)
            run_id = upload_result["run_id"]
            st.write("2/2 AI 도구 사용과 회사 자산 접근 경로를 분석하고 있습니다.")
            analysis_result = analyze_run(run_id)
            progress.update(label="분석이 완료되었습니다.", state="complete", expanded=False)
        st.session_state.run_id = run_id
        st.success(f"분석 완료: {analysis_result['findings']}개의 접근 경로를 찾았습니다.")
        st.write("분석 ID", run_id)
    except Exception as exc:
        st.error(f"분석에 실패했습니다: {exc}")

if not all_ready:
    st.caption(f"{sum(file is not None for file in uploaded.values())}/7개 파일 선택됨")
else:
    st.success("필수 파일 7개가 모두 준비되었습니다. 분석을 실행할 수 있습니다.")
