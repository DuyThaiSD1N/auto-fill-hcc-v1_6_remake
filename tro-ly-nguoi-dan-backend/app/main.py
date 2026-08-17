from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.attachments.router import router as attachments_router
from app.auth.router import router as auth_router
from app.config import settings
from app.consents.router import router as consents_router
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.db.indexes import ensure_indexes
from app.db.mongo import close, connect
from app.procedures.router import router as procedures_router
from app.process.router import router as process_router
from app.review.router import router as review_router
from app.traces.router import router as traces_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    connect()
    await ensure_indexes()
    yield
    close()


app = FastAPI(title="Trợ lý người dân Backend", version="0.1.0", lifespan=lifespan)

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

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(auth_router)
app.include_router(procedures_router)
app.include_router(process_router)
app.include_router(review_router)
app.include_router(attachments_router)
app.include_router(traces_router)
app.include_router(users_router)
app.include_router(consents_router)

# ── Module toàn trình (bật dần theo docs/, xem docs/00-tong-quan-toan-trinh.md §3.1) ──
from app.chat.router import router as chat_router          # Bước 3 — docs/03  # noqa: E402
from app.locations.router import router as locations_router  # Bước 3 — docs/03  # noqa: E402

app.include_router(chat_router)
app.include_router(locations_router)

from app.voice.router import router as voice_router      # Bước 4 — docs/04  # noqa: E402
from app.voice.ws_asr import router as ws_asr_router     # noqa: E402
from app.voice.ws_tts import router as ws_tts_router     # noqa: E402

app.include_router(voice_router)
app.include_router(ws_asr_router)
app.include_router(ws_tts_router)

from app.upload_session.router import router as upload_session_router  # Bước 5 — docs/05  # noqa: E402
from app.upload_session.ws import router as upload_session_ws_router   # noqa: E402

app.include_router(upload_session_router)
app.include_router(upload_session_ws_router)
# from app.upload_session.router import router as upload_session_router  # Bước 5 — docs/05
# from app.profiles.router import router as profiles_router            # Bước 8 — docs/08
# from app.notify.router import router as notify_router                # Bước 8 — docs/08


@app.get("/healthz")
async def healthz():
    return {"ok": True}
