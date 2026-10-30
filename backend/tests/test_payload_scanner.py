"""payload_scanner 담당: pytest tests/test_payload_scanner.py 가 모두 통과하면 완료"""
import pytest

from app.engine import payload_scanner as ps

pytestmark = pytest.mark.todo


def types(text):
    return [h["type"] for h in ps.scan_text(text)]


def test_phone_position():
    assert ps.scan_text("홍길동,010-1234-5678,서울시") == [{"type": "전화번호", "start": 4, "end": 17}]


def test_phone_without_dash():
    assert types("연락처 01055556666") == ["전화번호"]


def test_resident_number():
    assert types("주민번호 900101-1234567 입니다") == ["주민등록번호"]


def test_email():
    assert types("메일은 kim.sales@company.co.kr 로") == ["이메일"]


def test_api_key():
    assert types("key=sk-abcdefghijklmnopqrstuvwx1234") == ["API 키"]
    assert types("AKIAIOSFODNN7EXAMPLE") == ["API 키"]


def test_clean_text():
    assert ps.scan_text("주간 회의 일정 공유드립니다") == []


def test_sorted_by_start():
    hits = ps.scan_text("kim@a.com 010-1111-2222")
    assert [h["type"] for h in hits] == ["이메일", "전화번호"]
