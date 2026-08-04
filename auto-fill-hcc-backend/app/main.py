import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.attachments.router import router as attachments_router
from app.auth.router import router as auth_router
from app.config import settings
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.db.indexes import ensure_indexes
from app.db.mongo import close, connect
from app.procedures.router import router as procedures_router
from app.process.router import router as process_router
from app.review.router import router as review_router
from app.traces.router import router as traces_router
from app.upload_session.router import router as upload_session_router
from app.upload_session.ws import router as upload_ws_router
from app.users.router import router as users_router


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
    allow_headers=["Content-Type", "Authorization"],
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
app.include_router(procedures_router)
app.include_router(process_router)
app.include_router(review_router)
app.include_router(attachments_router)
app.include_router(traces_router)
app.include_router(users_router)
app.include_router(upload_session_router)
app.include_router(upload_ws_router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}
