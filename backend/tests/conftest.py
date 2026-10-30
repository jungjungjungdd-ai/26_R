import os
import tempfile
from pathlib import Path

import pytest

# 테스트는 실제 data/app.db 를 건드리지 않도록 임시 DB 사용
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")

from app.engine import loader  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"
FILES = {
    "employees": "employees.csv", "assets": "assets.csv", "ai_tools": "ai_tools.json",
    "network_logs": "network_logs.csv", "oauth_grants": "oauth_grants.csv",
    "asset_activities": "asset_activities.csv", "processes": "processes.csv",
}


@pytest.fixture
def tables():
    """data/sample 의 파일 7개를 DataFrame 으로 읽은 것"""
    out = {}
    for name, filename in FILES.items():
        df = loader.read_file(name, filename, (SAMPLE / filename).read_bytes())
        out[name] = loader.validate(name, filename, df)
    return out


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
