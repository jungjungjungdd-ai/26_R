import os
from pathlib import Path

# DB 파일 위치. 기본값은 저장소의 data/app.db
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parents[2] / "data" / "app.db"))
