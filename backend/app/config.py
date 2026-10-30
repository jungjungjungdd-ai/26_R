import os
from pathlib import Path

# DB 파일 위치. 기본값은 저장소의 data/app.db
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parents[2] / "data" / "app.db"))

# 실시간 시연 대본 (LIVE-01~04). 기본값은 DB 파일 옆의 sample 폴더
# 로컬: data/sample/live_script.json, 도커: /app/data/sample/live_script.json
LIVE_SCRIPT_PATH = Path(os.getenv("LIVE_SCRIPT_PATH", DB_PATH.parent / "sample" / "live_script.json"))
