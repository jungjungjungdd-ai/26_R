from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """API명세서의 에러 형식으로 응답하기 위한 예외.

    raise ApiError(404, "NOT_FOUND", "finding이 없습니다", {"finding_id": "F001"})
    """

    def __init__(self, status: int, code: str, message: str, detail: dict | None = None):
        self.status, self.code, self.message, self.detail = status, code, message, detail or {}


async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
    )


async def internal_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": str(exc), "detail": {}}},
    )
