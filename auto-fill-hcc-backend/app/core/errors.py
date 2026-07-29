from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Lỗi nghiệp vụ trả về client theo format chuẩn {error, message, code}."""

    def __init__(self, error: str, message: str, code: int = 400):
        self.error = error
        self.message = message
        self.code = code
        super().__init__(message)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.code,
        content={"error": exc.error, "message": exc.message, "code": exc.code},
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": str(exc), "code": 500},
    )
