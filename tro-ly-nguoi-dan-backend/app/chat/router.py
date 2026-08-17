"""API "1 cửa" của trợ lý (docs/03 §2) — extension chỉ nói chuyện với BE qua đây.

POST /api/v1/assistant/chat            — MỌI tương tác (gõ/nói/chip/sự kiện hệ thống)
GET  /api/v1/assistant/conversations/{id} — khôi phục phiên (đổi trang/F5)

Yêu cầu JWT (mọi role): máy quầy/kiosk đăng nhập tài khoản do admin cấp; acc có
tỉnh/xã → conversation mới auto-chọn nơi làm thủ tục. Rate-limit theo IP giữ nguyên.
"""
import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.chat import flow, intents, store
from app.config import settings
from app.core.deps import require_auth
from app.locations.lookup import location_for

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

# Rate-limit theo IP (mirror pattern public-autofill của chatbot TS): 60 lượt/phút là quá đủ
# cho hội thoại người thật; chống script spam.
_RATE: dict[str, list[float]] = defaultdict(list)
_RATE_MAX, _RATE_WINDOW = 60, 60.0


def _rate_ok(ip: str) -> bool:
    now = time.monotonic()
    bucket = [t for t in _RATE[ip] if now - t < _RATE_WINDOW]
    bucket.append(now)
    _RATE[ip] = bucket
    return len(bucket) <= _RATE_MAX


class ClientContext(BaseModel):
    url: str = ""
    detected_procedure: str | None = None
    form_filled: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = ""
    source: str = "text"          # text | voice | chip | system
    # Nhãn hiển thị của chip/card () — history lưu nhãn này
    # thay vì lệnh máy "__action:..." để khôi phục phiên không lộ lệnh máy ra khung chat.
    display_message: str | None = None
    client_context: ClientContext | None = None


def _default_location() -> dict:
    # Mặc định nơi pilot: Bắc Ninh — Song Liễu. Đổi nơi triển khai = đổi env sau (docs/03a §1).
    return {"province": "Tỉnh Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Song Liễu"}


def _serialize(conv: dict, reply: flow.Reply) -> dict:
    return {
        "conversation_id": conv["_id"],
        "state": conv.get("state", "greet"),
        "display_md": reply.display_md,
        "tts_text": reply.tts_text,
        "chips": reply.chips,
        "cards": reply.cards,
        "actions": reply.actions,
        "awaiting_events": reply.awaiting_events or conv.get("awaiting_events", []),
        "progress": flow.build_progress(conv),
        "procedure_key": conv.get("procedure_key"),
        "location": conv.get("location", {}),
    }


@router.post("/chat")
async def assistant_chat(req: ChatRequest, request: Request, user: dict = Depends(require_auth)):
    ip = request.client.host if request.client else "?"
    if not _rate_ok(ip):
        raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu, bà con chờ chút rồi thử lại nhé.")

    conv = await store.get(req.conversation_id or "")
    if conv is None:
        # Acc gắn tỉnh/xã → phiên mới auto-chọn nơi làm thủ tục (vẫn đổi được trên card).
        conv = store.new_conversation(location=location_for(user.get("tinh"), user.get("xa")) or _default_location())
        conv["auth_user"] = {"id": user["id"], "username": user["username"], "name": user.get("name") or ""}

    message = (req.message or "").strip()
    # History chỉ lưu thứ NGƯỜI thấy: nhãn chip nếu có; lệnh máy trần (__action/__event)
    # không có nhãn thì KHÔNG lưu (khôi phục phiên không được lộ lệnh máy).
    display = (req.display_message or "").strip()
    if message and not message.startswith("__"):
        store.push_history(conv, "user", message, req.source)
    elif message and display:
        store.push_history(conv, "user", display, req.source)

    # Lượt đầu (message rỗng, phiên mới) → màn chào; còn lại đi qua intent → flow.
    if not message and not conv["history"]:
        reply = flow._handle_greet(conv, intents.Intent("unknown"))  # noqa: SLF001 — lối vào chào chuẩn
    else:
        intent = await intents.resolve(message, conv.get("state", "greet"))
        reply = await flow.handle_turn(conv, intent)

    payload = _serialize(conv, reply)
    # Reply RỖNG (bot im lặng chờ trang) → không lưu history, không đè last_reply —
    # khôi phục phiên phải render lại được câu có nội dung gần nhất.
    if reply.display_md or reply.cards or reply.chips:
        store.push_history(conv, "bot", reply.display_md, "bot")
        conv["last_reply"] = {k: payload[k] for k in ("display_md", "tts_text", "chips", "cards", "state")}
    await store.save(conv)

    if settings.llm_debug:
        logger.info("[assistant] %s src=%s state=%s msg=%r", conv["_id"], req.source, conv["state"], message[:120])
    return payload


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, _: dict = Depends(require_auth)):
    """Người dân bấm 'Cuộc trò chuyện mới' / 'Xóa dữ liệu' — xoá NGAY, không chờ TTL."""
    from app.db.mongo import get_db

    await get_db().conversations.delete_one({"_id": conv_id})
    return {"ok": True}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, _: dict = Depends(require_auth)):
    conv = await store.get(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại hoặc đã hết hạn.")
    return {
        "conversation_id": conv["_id"],
        "state": conv.get("state", "greet"),
        "procedure_key": conv.get("procedure_key"),
        "location": conv.get("location", {}),
        "progress": flow.build_progress(conv),
        "awaiting_events": conv.get("awaiting_events", []),
        "last_reply": conv.get("last_reply"),
        # Đuôi hội thoại để render lại khung chat (bỏ system event + mọi lệnh máy còn sót).
        "history": [
            {"role": h["role"], "text": h["text"]}
            for h in conv.get("history", [])[-30:]
            if h.get("source") != "system" and not str(h.get("text", "")).startswith("__")
        ],
    }
