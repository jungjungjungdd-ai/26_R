"""System 도메인: SYS-01"""
from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/health")
def health():
    return {"status": "ok"}
