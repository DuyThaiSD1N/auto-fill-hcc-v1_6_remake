"""App con của nhóm API thống kê đối tác, gắn ở /partner-api/v1 (xem app/main.py).

Tách app riêng để có trang docs/OpenAPI RIÊNG chỉ gồm các API này (gửi cho đối tác), không lộ
danh sách API nội bộ. App con không thừa hưởng exception handler của app chính nên đăng ký lại.
"""
from fastapi import FastAPI

from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.partner_api.router import router

PREFIX = "/partner-api/v1"

partner_app = FastAPI(
    title="API thống kê Trợ lý nhân dân",
    version="1.0.0",
    description=(
        "Số liệu hồ sơ của Trợ lý nhân dân (Auto Fill + Handfree), cùng cách đếm với web thống kê.\n\n"
        "Xác thực: gửi header `X-API-Key: <key>` với mọi request. Ngày theo lịch Việt Nam, dạng `YYYY-MM-DD`."
    ),
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
)
partner_app.add_exception_handler(AppError, app_error_handler)
partner_app.add_exception_handler(Exception, unhandled_error_handler)
partner_app.include_router(router)
