from pathlib import Path

import pandas as pd
import streamlit as st

from api import ApiError, USE_MOCK, analyze, upload_run

FILES = {
    "employees": ("직원 (employees.csv)", ["csv"]),
    "assets": ("회사 자산 (assets.csv)", ["csv"]),
    "ai_tools": ("AI 도구 카탈로그 (ai_tools.json)", ["json"]),
    "network_logs": ("네트워크 로그 (network_logs.csv)", ["csv"]),
    "oauth_grants": ("OAuth 권한 (oauth_grants.csv)", ["csv"]),
    "asset_activities": ("자산 활동 (asset_activities.csv)", ["csv"]),
    "processes": ("프로세스 실행 기록 (processes.csv)", ["csv"]),
}

SAMPLE_FILENAMES = {
    "employees": "employees.csv",
    "assets": "assets.csv",
    "ai_tools": "ai_tools.json",
    "network_logs": "network_logs.csv",
    "oauth_grants": "oauth_grants.csv",
    "asset_activities": "asset_activities.csv",
    "processes": "processes.csv",
}

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample"


def _render_rows_table(rows: dict[str, int]) -> None:
    st.subheader("테이블별 적재 행 수 (rows)")
    table_data = [
        {
            "테이블": key,
            "설명": FILES[key][0] if key in FILES else key,
            "행 수": count,
        }
        for key, count in rows.items()
    ]
    st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)


def _execute_upload_and_analyze(files_payload: dict) -> None:
    try:
        with st.status("분석을 준비하는 중입니다...", expanded=True) as progress:
            st.write("1/2 파일을 업로드하고 형식을 검증하고 있습니다.")
            upload_result = upload_run(files_payload)
            run_id = upload_result["run_id"]
            rows = upload_result.get("rows", {})
            st.session_state.run_id = run_id
            st.session_state.upload_rows = rows
            st.session_state.pop("mitigations", None)
            st.session_state.pop("open_logs", None)
            st.session_state.pop("selected_finding_id", None)

            st.write("2/2 AI 도구 사용과 회사 자산 접근 경로를 분석하고 있습니다.")
            analysis_result = analyze(run_id)
            st.session_state.findings_count = analysis_result.get("findings", 0)
            progress.update(label="분석이 완료되었습니다.", state="complete", expanded=False)

        st.success(
            f"분석 완료 (run_id: {run_id}) — {analysis_result['findings']}개의 접근 경로를 찾았습니다."
        )
    except ApiError as exc:
        st.error(exc.message)
    except Exception as exc:
        st.error(str(exc))


st.title("📤 데이터 업로드 및 분석")
st.caption("직원·자산·AI 도구·네트워크 로그 등 필수 파일 7개를 검증한 뒤 위험 경로를 분석합니다.")

if USE_MOCK:
    st.info("현재는 mock 모드입니다. 파일 내용은 서버로 전송되지 않으며 명세서 예시 응답으로 동작합니다.")

uploaded = {}
left, right = st.columns(2)
for index, (key, (label, extensions)) in enumerate(FILES.items()):
    with (left if index % 2 == 0 else right):
        uploaded[key] = st.file_uploader(label, type=extensions, key=f"upload-{key}")

all_ready = all(uploaded.values())
sample_available = USE_MOCK or all((SAMPLE_DIR / fn).exists() for fn in SAMPLE_FILENAMES.values())

btn_col1, btn_col2 = st.columns(2) if sample_available else (st.container(), None)
with btn_col1:
    if st.button(
        "업로드하고 분석 실행",
        type="primary",
        disabled=not all_ready,
        use_container_width=True,
    ):
        _execute_upload_and_analyze(uploaded)

if btn_col2 is not None:
    with btn_col2:
        if st.button("샘플 데이터로 업로드 및 분석", use_container_width=True):
            if USE_MOCK:
                sample_files = {key: b"" for key in FILES}
            else:
                sample_files = {
                    key: (SAMPLE_DIR / fn).read_bytes()
                    for key, fn in SAMPLE_FILENAMES.items()
                }
            _execute_upload_and_analyze(sample_files)

if not all_ready:
    st.caption(f"{sum(file is not None for file in uploaded.values())}/7개 파일 선택됨")
else:
    st.success("필수 파일 7개가 모두 준비되었습니다. 분석을 실행할 수 있습니다.")

if st.session_state.get("run_id") and st.session_state.get("upload_rows"):
    st.divider()
    st.write("**현재 실행 ID (`run_id`):**", f"`{st.session_state.run_id}`")
    _render_rows_table(st.session_state.upload_rows)
