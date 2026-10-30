import streamlit as st

st.set_page_config(page_title="Shadow AI Radar", page_icon="🛡️", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* Apple iOS / macOS Clean Typography & Background */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "SF Pro Display", "Malgun Gothic", sans-serif !important;
        color: #1D1D1F;
    }
    .stApp {
        background-color: #F5F5F7;
    }
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1320px !important;
    }

    /* Sidebar — macOS Translucent Vibrancy Style */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.88) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0, 0, 0, 0.07) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {
        padding-top: 1rem;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        border-radius: 12px !important;
        margin: 4px 10px !important;
        padding: 10px 14px !important;
        font-weight: 600 !important;
        transition: all 0.18s ease !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #007AFF !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.25);
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span {
        color: #FFFFFF !important;
    }

    /* Page Titles & Captions */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        color: #1D1D1F !important;
        font-size: 2.05rem !important;
        margin-bottom: 0.15rem !important;
    }
    h2, h3, h4 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #1D1D1F !important;
    }
    [data-testid="stCaptionContainer"] {
        color: #6E6E73 !important;
        font-size: 0.94rem !important;
    }

    /* Apple Card Style for Metric Boxes */
    [data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.06) !important;
        border-radius: 18px !important;
        padding: 18px 20px !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.035) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06) !important;
    }
    [data-testid="stMetricLabel"] {
        font-weight: 600 !important;
        color: #6E6E73 !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        color: #1D1D1F !important;
        font-size: 1.85rem !important;
        letter-spacing: -0.03em !important;
    }

    /* Bordered Containers & Expanders — iOS Grouped Table Card Feel */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stExpander"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.07) !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
    }

    /* Buttons — iOS Pill / Rounded Action Buttons */
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.1rem !important;
        border: 1px solid rgba(0, 0, 0, 0.08) !important;
        background-color: #FFFFFF !important;
        color: #1D1D1F !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.16s ease !important;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: #007AFF !important;
        color: #007AFF !important;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.12) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #0A84FF 0%, #007AFF 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(0, 122, 255, 0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(180deg, #007AFF 0%, #0062CC 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 18px rgba(0, 122, 255, 0.4) !important;
    }

    /* DataFrames & Tables */
    [data-testid="stDataFrame"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.06) !important;
        border-radius: 16px !important;
        padding: 6px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
    }

    /* Alerts / Banners (st.info, st.success, st.warning, st.error) */
    [data-testid="stAlert"] {
        border-radius: 14px !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.025) !important;
    }

    /* Selectbox & Inputs */
    [data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
    }

    /* Page Links */
    [data-testid="stPageLink-NavLink"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.07) !important;
        border-radius: 14px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03) !important;
    }
    [data-testid="stPageLink-NavLink"]:hover {
        border-color: #007AFF !important;
        background: #F0F7FF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("views/upload.py", title="데이터 분석", icon="📤"),
    st.Page("views/overview.py", title="개요", icon="📊", default=True),
    st.Page("views/tools.py", title="AI 도구 목록", icon="🤖"),
    st.Page("views/asset_map.py", title="자산 지도", icon="🗺️"),
    st.Page("views/live.py", title="실시간 모니터링", icon="📡"),
]
st.navigation(pages).run()
