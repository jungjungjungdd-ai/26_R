"""데이터 분석: 샘플 원클릭 분석이 메인, 직접 업로드는 접어 둔다."""
from pathlib import Path

import pandas as pd
import streamlit as st

from api import ApiError, USE_MOCK, analyze, upload_run

# 테이블 키 → (설명, 확장자)
FILES = {
    "employees": ("직원", "csv"),
    "assets": ("회사 자산", "csv"),
    "ai_tools": ("AI 도구 카탈로그", "json"),
    "network_logs": ("네트워크 로그", "csv"),
    "oauth_grants": ("OAuth 권한", "csv"),
    "asset_activities": ("자산 활동", "csv"),
    "processes": ("프로세스 실행 기록", "csv"),
}
SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample"


def filename_of(key: str) -> str:
    return f"{key}.{FILES[key][1]}"


@st.cache_data
def sample_counts() -> dict[str, int]:
    """샘플 파일의 행 수 (버튼 아래 설명용). 파일이 없으면 빈 dict."""
    counts = {}
    for key in FILES:
        path = SAMPLE_DIR / filename_of(key)
        if not path.exists():
            return {}
        counts[key] = len(pd.read_json(path)) if path.suffix == ".json" else len(pd.read_csv(path))
    return counts


def classify(files: list) -> tuple[dict, list[str], list[str]]:
    """업로드한 파일을 이름으로 테이블에 나눈다. → (테이블별 파일, 알 수 없는 파일, 중복된 테이블)"""
    matched, unknown, duplicated = {}, [], []
    # 긴 이름부터 비교 (assets 가 asset_activities 를 가로채지 않게)
    keys = sorted(FILES, key=len, reverse=True)
    for f in files:
        stem, ext = Path(f.name).stem.lower(), Path(f.name).suffix.lower().lstrip(".")
        key = next((k for k in keys if k in stem and FILES[k][1] == ext), None)
        if key is None:
            unknown.append(f.name)
        elif key in matched:
            duplicated.append(key)
        else:
            matched[key] = f
    return matched, unknown, duplicated


def run_upload_and_analyze(files_payload: dict) -> None:
    try:
        with st.status("분석을 준비하는 중입니다...", expanded=True) as progress:
            st.write("1/2 파일을 업로드하고 형식을 검증하고 있습니다.")
            upload_result = upload_run(files_payload)
            run_id = upload_result["run_id"]
            st.session_state.run_id = run_id
            st.session_state.upload_rows = upload_result.get("rows", {})
            for key in ("mitigations", "open_logs", "selected_finding_id"):
                st.session_state.pop(key, None)

            st.write("2/2 AI 도구 사용과 회사 자산 접근 경로를 분석하고 있습니다.")
            analysis_result = analyze(run_id)
            st.session_state.findings_count = analysis_result.get("findings", 0)
            progress.update(label="분석이 완료되었습니다.", state="complete", expanded=False)
    except ApiError as exc:
        st.error(exc.message)
    except Exception as exc:  # noqa: BLE001 - 화면에 그대로 보여 준다
        st.error(str(exc))


st.title("📤 데이터 분석")
st.caption("직원·자산·AI 도구·네트워크 로그를 엮어 위험한 AI 자동화 경로를 찾습니다.")

if USE_MOCK:
    st.info("⚪ mock 모드입니다. 파일은 서버로 보내지 않고 예시 결과로 동작합니다.")

# ---- 1. 원클릭 분석 (메인) ----
counts = sample_counts()
sample_ready = USE_MOCK or bool(counts)
if st.button("▶ 샘플 데이터로 바로 분석", type="primary", use_container_width=True,
             disabled=not sample_ready):
    if USE_MOCK:
        payload = {key: b"" for key in FILES}
    else:
        payload = {key: (SAMPLE_DIR / filename_of(key)).read_bytes() for key in FILES}
    run_upload_and_analyze(payload)

if counts:
    st.caption(f"직원 {counts['employees']}명 · AI 도구 {counts['ai_tools']}개 · "
               f"네트워크 로그 {counts['network_logs']}건 등 샘플 데이터로 시연 사례를 분석합니다.")
elif not sample_ready:
    st.caption("data/sample 폴더에 샘플 파일이 없어 직접 업로드만 할 수 있습니다.")

# ---- 2. 직접 업로드 (고급, 접힘) ----
with st.expander("직접 업로드 (고급)", expanded=False):
    st.caption("파일 7개를 한 번에 끌어다 놓으세요. 파일 이름으로 자동 분류합니다. "
               "(예: employees.csv, ai_tools.json)")
    uploaded = st.file_uploader("로그 파일", type=["csv", "json"], accept_multiple_files=True,
                                label_visibility="collapsed", key="upload-files")
    matched, unknown, duplicated = classify(uploaded or [])

    cols = st.columns(4)
    for i, (key, (label, _ext)) in enumerate(FILES.items()):
        mark = "✅" if key in matched else "❌"
        cols[i % 4].markdown(f"{mark} {label}  \n`{filename_of(key)}`")
    if unknown:
        st.warning("알 수 없는 파일 (이름을 확인하세요): " + ", ".join(unknown))
    if duplicated:
        st.warning("같은 종류 파일이 두 개 이상입니다. 첫 번째 파일만 씁니다: "
                   + ", ".join(sorted(set(duplicated))))

    ready = len(matched) == len(FILES)
    if st.button("업로드 및 분석", use_container_width=True, disabled=not ready):
        run_upload_and_analyze(matched)
    if uploaded and not ready:
        st.caption(f"{len(matched)}/{len(FILES)}개 준비됨")

# ---- 3. 결과와 다음 행동 ----
if st.session_state.get("run_id") and st.session_state.get("upload_rows"):
    st.divider()
    st.success(f"분석 완료 · run_id `{st.session_state.run_id}` · "
               f"접근 경로 {st.session_state.get('findings_count', 0)}개 발견")
    n1, n2, n3 = st.columns(3)
    n1.page_link("views/overview.py", label="개요 보러 가기", icon="📊")
    n2.page_link("views/tools.py", label="AI 도구 목록", icon="🤖")
    n3.page_link("views/live.py", label="실시간 모니터링", icon="📡")

    with st.expander("테이블별 적재 행 수"):
        rows = st.session_state.upload_rows
        st.dataframe(pd.DataFrame([{"테이블": k, "설명": FILES.get(k, (k,))[0], "행 수": v}
                                   for k, v in rows.items()]),
                     hide_index=True, use_container_width=True)
