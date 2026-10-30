import requests

USE_MOCK = True  # 백엔드가 준비되면 False로 바꾸기
BASE_URL = "http://localhost:8000"

# 백엔드는 반드시 이 형식 그대로 돌려줘야 함
MOCK_TOOLS = [
    {"id": "t1", "name": "n8n 워크플로 (CRM 동기화)", "owner": "김영업 (퇴사)",
     "approved": False, "assets": ["CRM 고객 정보"], "score": 100, "level": "위험",
     "reasons": ["비승인 도구 +25", "개인정보 자산 접근 +30", "외부 전송 권한 +15",
                 "대량 전송 발생 +15", "소유자 퇴사 +20"]},
    {"id": "t2", "name": "MCP 서버 (postgres)", "owner": "이개발",
     "approved": False, "assets": ["고객 DB"], "score": 70, "level": "위험",
     "reasons": ["비승인 도구 +25", "개인정보 자산 접근 +30", "대량 전송 발생 +15"]},
    {"id": "t3", "name": "Zapier AI", "owner": "박마케팅",
     "approved": False, "assets": ["사내 메일"], "score": 55, "level": "주의",
     "reasons": ["비승인 도구 +25", "기밀 자산 접근 +15", "외부 전송 권한 +15"]},
    {"id": "t4", "name": "이미지 생성 AI (개인 계정)", "owner": "최디자인",
     "approved": False, "assets": ["홍보 폴더"], "score": 25, "level": "낮음",
     "reasons": ["비승인 도구 +25"]},
    {"id": "t5", "name": "ChatGPT Enterprise", "owner": "전사",
     "approved": True, "assets": ["사내 문서"], "score": 0, "level": "낮음",
     "reasons": ["회사 승인 도구"]},
]


def get_tools() -> list[dict]:
    if USE_MOCK:
        return MOCK_TOOLS
    r = requests.get(f"{BASE_URL}/tools", timeout=5)
    r.raise_for_status()
    return r.json()


def revoke_tool(tool_id: str) -> dict:
    if USE_MOCK:
        return {"ok": True}
    r = requests.post(f"{BASE_URL}/tools/{tool_id}/revoke", timeout=5)
    r.raise_for_status()
    return r.json()
