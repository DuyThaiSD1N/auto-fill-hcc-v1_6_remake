import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.attachments.router import router as attachments_router
from app.dossiers.router import router as dossiers_router
from app.auth.router import router as auth_router
from app.batch.router import router as batch_router
from app.config import settings
from app.consent.router import router as consent_router
from app.consents.router import router as consents_router
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.db.indexes import ensure_indexes
from app.db.mongo import close, connect
from app.locations.router import router as locations_router
from app.procedures.router import router as procedures_router
from app.process.router import router as process_router
from app.review.router import router as review_router
from app.reports.router import router as reports_router
from app.dashboard.router import router as dashboard_router
from app.traces.router import router as traces_router
from app.upload_session.router import router as upload_session_router
from app.upload_session.ws import router as upload_ws_router
from app.users.router import router as users_router
from app.v2.router import router as v2_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    connect()
    await ensure_indexes()
    yield
    close()


app = FastAPI(title="Auto Fill HCC Backend", version="1.0.0", lifespan=lifespan)

# CORS cho Chrome extension + FE web (màn trace).
cors_kwargs = dict(
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Upload-Token"],
    expose_headers=["Content-Disposition"],
)
# FE web luôn nằm trong allow_origins; extension dùng allow_origins (khi cấu hình id)
# hoặc allow_origin_regex (khi cho phép mọi extension ở dev). Hai tham số này cùng hiệu lực.
if settings.allow_all_extensions:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origin_list,
        allow_origin_regex=r"chrome-extension://.*",
        **cors_kwargs,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins + settings.frontend_origin_list,
        **cors_kwargs,
    )

_timing_log = logging.getLogger("app.timing")


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Đo thời gian XỬ LÝ THẬT trong app (nhận body + parse + handler + build response),
    KHÔNG gồm BackgroundTasks (chạy sau khi trả). So header X-Process-Time với TTFB trình duyệt:
    - X-Process-Time ~ TTFB  → server thật sự lâu (đào tiếp từng chặng).
    - X-Process-Time << TTFB → phần còn lại ở proxy/mạng/nhận body, không phải xử lý.
    """
    t0 = time.perf_counter()
    response = await call_next(request)
    dt_ms = int((time.perf_counter() - t0) * 1000)
    response.headers["X-Process-Time"] = str(dt_ms)
    if dt_ms > 1000:  # chỉ log request chậm (>1s) cho đỡ nhiễu
        _timing_log.warning("SLOW %s %s -> %dms (status=%s)",
                            request.method, request.url.path, dt_ms, response.status_code)
    return response


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(auth_router)
app.include_router(batch_router)
app.include_router(procedures_router)
app.include_router(process_router)
app.include_router(review_router)
app.include_router(attachments_router)
app.include_router(dossiers_router)  # mốc bấm nộp của Auto Fill (Handfree đi qua chat)
app.include_router(traces_router)
app.include_router(dashboard_router)  # bảng thống kê phường (require_ward, khóa theo user_id)
app.include_router(reports_router)
app.include_router(users_router)
app.include_router(locations_router)
app.include_router(upload_session_router)
app.include_router(upload_ws_router)
app.include_router(consent_router)
app.include_router(consents_router)
app.include_router(v2_router)

# Handfree là một channel bổ sung trên cùng core procedure/process/attach. Feature flag chỉ
# đóng/mở entrypoint hội thoại và mobile riêng; toàn bộ API Auto Fill phía trên không đổi.
if settings.handfree_enabled:
    from app.channels.handfree.chat.router import router as handfree_chat_router
    from app.channels.handfree.documents.router import (
        mobile_router as handfree_mobile_router,
        router as handfree_document_router,
    )
    from app.channels.handfree.voice.router import router as handfree_voice_router
    from app.channels.handfree.voice.ws_asr import router as handfree_asr_router
    from app.channels.handfree.voice.ws_tts import router as handfree_tts_router

    app.include_router(handfree_chat_router)
    app.include_router(handfree_document_router)
    app.include_router(handfree_mobile_router)
    app.include_router(handfree_voice_router)
    app.include_router(handfree_asr_router)
    app.include_router(handfree_tts_router)

# Asset tĩnh cho trang mobile QR:
#  - /static/scanner/*  : bundle ESM scanner (build từ repo scanic-stream-mask, xem BUILD.md)
#  - /static/vendor/*   : thư viện prebuilt (pdf-lib gộp ảnh scan thành 1 PDF)
# Mount ở thư mục CHA để phục vụ cả hai; model ML vẫn tự tải CDN phía điện thoại.
if settings.handfree_enabled:
    _handfree_static_dir = (
        Path(__file__).parent / "channels" / "handfree" / "documents" / "static"
    )
    if _handfree_static_dir.is_dir():
        app.mount(
            "/static/mobile/handfree",
            StaticFiles(directory=_handfree_static_dir),
            name="handfree-mobile-static",
        )

_static_dir = Path(__file__).parent / "upload_session" / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/healthz")
async def healthz():
    return {"ok": True}
