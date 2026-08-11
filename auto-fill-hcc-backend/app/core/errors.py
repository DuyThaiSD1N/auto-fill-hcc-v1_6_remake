import logging
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Câu chung an toàn cho lỗi không lường trước — KHÔNG lộ chi tiết kỹ thuật ra UI.
_GENERIC_500 = "Hệ thống gặp lỗi khi xử lý. Vui lòng thử lại sau."


class AppError(Exception):
    """Lỗi nghiệp vụ trả về client theo format chuẩn {error, message, code}.

    `message` là câu tiếng Việt dành cho người dùng (extension hiển thị trực tiếp/ tra theo `error`).
    KHÔNG nhét traceback/OCR/LLM thô vào `message` — chi tiết kỹ thuật để log server.
    """

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


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Lỗi ngoài dự kiến: ghi ĐẦY ĐỦ ở server (kèm mã tra cứu), nhưng chỉ trả UI câu chung + mã.

    Trước đây trả `str(exc)` → lộ nguyên exception Python lên UI extension. Nay giấu chi tiết,
    gắn `requestId` để cán bộ đọc cho bộ phận kỹ thuật tra log.
    """
    request_id = uuid.uuid4().hex[:12]
    logger.exception("UNHANDLED [%s] %s %s", request_id, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": _GENERIC_500,
                 "code": 500, "requestId": request_id},
    )
