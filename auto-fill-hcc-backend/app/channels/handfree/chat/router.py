"""API "1 cửa" của trợ lý (docs/03 §2) — extension chỉ nói chuyện với BE qua đây.

POST /api/v1/assistant/chat            — MỌI tương tác (gõ/nói/chip/sự kiện hệ thống)
GET  /api/v1/assistant/conversations/{id} — khôi phục phiên (đổi trang/F5)

Yêu cầu JWT (mọi role): máy quầy/kiosk đăng nhập tài khoản do admin cấp; acc có
tỉnh/xã → conversation mới auto-chọn nơi làm thủ tục. Rate-limit theo IP giữ nguyên.
"""
import logging
import re
import time
from collections import defaultdict
from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.channels.handfree.chat import access, flow, intents, store
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
    # Tín hiệu bước đang mở tại đúng thời điểm công dân gõ/bấm. Không thể chỉ dựa vào
    # page_status nền vì watcher có thể vừa reload hoặc chưa kịp báo sau khi SPA đổi bước.
    page_context: dict[str, object] = Field(default_factory=dict)
    # Cùng shape options.formContext của Auto-fill; extension đọc từ chính form đang mở.
    form_context: dict[str, object] = Field(default_factory=dict)
    # Cấu trúc các dòng thành phần hồ sơ trên trang hiện tại.
    attachment_context: dict[str, object] = Field(default_factory=dict)
    # Tùy chọn người dùng cho planner; tách giấy tờ trong file KHÔNG phải splitMode
    # (splitMode của chứng thực là tách thành nhiều hồ sơ/tab).
    attachment_preferences: dict[str, object] = Field(default_factory=dict)
    # Extension tự khai khả năng để backend không trả contract mới cho bản cũ.
    capabilities: dict[str, object] = Field(default_factory=dict)


def _clean_attachment_context(raw: dict[str, object]) -> dict[str, object]:
    """Chỉ giữ dữ liệu DOM ngắn mà planner cần; không lưu nguyên payload tùy ý từ client."""
    components = raw.get("components") if isinstance(raw, dict) else None
    if not isinstance(components, list):
        return {}
    cleaned: list[dict[str, object]] = []
    for position, component in enumerate(components[:100], start=1):
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index") or position)
        except (TypeError, ValueError):
            index = position
        if index <= 0:
            index = position
        name = re.sub(r"\s+", " ", str(component.get("componentName") or "")).strip()
        # Một số bảng render nhãn của dòng rồi lặp lại input modal dưới dạng
        # "Tên Hồ Sơ: <cùng nhãn>" trong chính cell. Giữ phần nhãn trước marker để
        # planner không nhận một componentName dài gấp đôi; nếu marker đứng đầu thì
        # lấy giá trị sau marker (dòng thành phần do người dùng tự thêm).
        marker = re.search(r"\bTên Hồ Sơ\s*:\s*", name, flags=re.IGNORECASE)
        if marker:
            before = name[:marker.start()].strip()
            after = name[marker.end():].strip()
            name = before or after
        name = name[:1000]
        if not name:
            continue
        cleaned.append({
            "index": index,
            "componentName": name,
            "required": bool(component.get("required")),
            "hasFile": bool(component.get("hasFile")),
        })
    if not cleaned:
        return {}
    result: dict[str, object] = {"components": cleaned}
    # Chỉ giữ bằng chứng dương tính. Client cũ không gửi hai cờ này vẫn giữ nguyên shape
    # attachmentContext trước đây và không được dùng làm fallback khi stepper mất.
    if raw.get("hasAttachmentTableHeader") is True:
        result["hasAttachmentTableHeader"] = True
    if raw.get("hasFileControl") is True:
        result["hasFileControl"] = True
    return result


def _bounded_int(value: object, default: int = 0) -> int:
    try:
        return max(0, min(10, int(value or default)))
    except (TypeError, ValueError):
        return default


def _clean_attachment_preferences(raw: dict[str, object]) -> dict[str, object]:
    """Chỉ nhận boolean tường minh; chuỗi "true" không được phép tự bật tách tài liệu."""
    if not isinstance(raw, dict) or not isinstance(raw.get("splitDocuments"), bool):
        return {}
    return {"splitDocuments": raw["splitDocuments"]}


def _clean_client_capabilities(raw: dict[str, object]) -> dict[str, object]:
    """Whitelist contract FE-BE; khóa lạ từ client không được lưu vào conversation."""
    return {
        "attachmentEngineVersion": _bounded_int(raw.get("attachmentEngineVersion")),
        "supportsSourceSegments": raw.get("supportsSourceSegments") is True,
        "supportsAttachmentContext": raw.get("supportsAttachmentContext") is True,
        "supportsPageBoundDocsComplete": raw.get("supportsPageBoundDocsComplete") is True,
        "supportsAttachActionLease": raw.get("supportsAttachActionLease") is True,
    }


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = ""
    source: str = "text"          # text | voice | chip | system
    # Nhãn hiển thị của chip/card () — history lưu nhãn này
    # thay vì lệnh máy "__action:..." để khôi phục phiên không lộ lệnh máy ra khung chat.
    display_message: str | None = None
    client_context: ClientContext | None = None
    # Ngôn ngữ máy quầy đang chọn (chrome.storage). CHỈ áp cho conversation MỚI để câu chào
    # đầu tiên đã đúng tiếng Mông; phiên đang có thì conv.lang (đổi qua set_lang) là nguồn sự thật.
    preferred_lang: str | None = None


def _default_location() -> dict:
    # Mặc định nơi pilot: Bắc Ninh — Song Liễu. Đổi nơi triển khai = đổi env sau (docs/03a §1).
    return {"province": "Tỉnh Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Song Liễu"}


def _serialize(conv: dict, reply: flow.Reply) -> dict:
    return {
        "conversation_id": conv["_id"],
        "state": conv.get("state", "greet"),
        "lang": conv.get("lang", "vi"),
        "display_md": reply.display_md,
        "tts_text": reply.tts_text,
        "tts_lang": reply.tts_lang,
        "chips": reply.chips,
        "cards": reply.cards,
        "actions": reply.actions,
        "awaiting_events": reply.awaiting_events or conv.get("awaiting_events", []),
        "progress": flow.build_progress(conv),
        "procedure_key": conv.get("procedure_key"),
        "location": conv.get("location", {}),
        "execution_subject": conv.get("execution_subject", "self"),
    }


def _last_reply_for_restore(conv: dict) -> dict | None:
    """Refresh mutable picker state without changing the stored chat transcript."""
    last_reply = conv.get("last_reply")
    if not isinstance(last_reply, dict):
        return None
    restored = deepcopy(last_reply)
    restored["cards"] = [
        flow._location_card(conv) if card.get("kind") == "location_picker" else card  # noqa: SLF001
        for card in restored.get("cards", [])
        if isinstance(card, dict)
    ]
    # Nhãn nút chốt giấy tờ phụ thuộc trang hiện tại. last_reply có thể được tạo ở
    # bước trước, nên khi sidebar tải lại phải dựng nhãn từ docs_target mới nhất.
    for chip in restored.get("chips", []):
        if isinstance(chip, dict) and chip.get("send") == "__action:docs_done":
            chip["label"] = flow._docs_done_label_for_conv(conv)  # noqa: SLF001
    return restored


@router.post("/chat")
async def assistant_chat(req: ChatRequest, request: Request, user: dict = Depends(require_auth)):
    ip = request.client.host if request.client else "?"
    if not _rate_ok(ip):
        raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu, công dân chờ chút rồi thử lại nhé.")

    conv = await store.get(req.conversation_id or "")
    if conv is None:
        # Acc gắn tỉnh/xã → phiên mới auto-chọn nơi làm thủ tục (vẫn đổi được trên card).
        conv = store.new_conversation(location=location_for(user.get("tinh"), user.get("xa")) or _default_location())
        if str(req.preferred_lang or "").strip().lower() == "hmong":
            conv["lang"] = "hmong"
    else:
        access.ensure_conversation_owner(conv, user)
    # Đồng bộ lại theo tài khoản hiện tại ở mọi lượt. Nhờ vậy trace Handfree dùng cùng
    # tên tài khoản với Auto Fill kể cả khi admin vừa đổi tên hiển thị của tài khoản.
    conv["auth_user"] = {
        "id": user["id"],
        "username": user["username"],
        "name": user.get("name") or "",
    }

    # Giữ mỏ neo người yêu cầu trong conversation để lượt "Đã đưa đủ" chạy nền vẫn nhận được
    # đúng formContext như API /process của Auto-fill. Chỉ lưu các khóa ngắn mà pipeline sử dụng.
    raw_form_context = (req.client_context.form_context if req.client_context else {}) or {}
    if raw_form_context:
        conv["form_context"] = {
            "applicantFullname": str(raw_form_context.get("applicantFullname") or "")[:200],
            "applicantIdentityNumber": str(raw_form_context.get("applicantIdentityNumber") or "")[:30],
        }

    if req.client_context:
        capabilities = req.client_context.capabilities or {}
        if capabilities:
            conv["client_capabilities"] = _clean_client_capabilities(capabilities)
        attachment_context = _clean_attachment_context(req.client_context.attachment_context or {})
        # Không lấy object rỗng ở bước kê khai đè context vừa thu trên trang Thành phần hồ sơ.
        if attachment_context:
            conv["attachment_context"] = attachment_context
            conv["attachment_context_url"] = str(req.client_context.url or "")[:2000]
        attachment_preferences = _clean_attachment_preferences(
            req.client_context.attachment_preferences or {}
        )
        # Dict chứa False vẫn truthy: lựa chọn tắt phải được lưu rõ để ghi đè lần bật trước.
        if attachment_preferences:
            conv["attachment_preferences"] = attachment_preferences

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
        reply = flow.first_greet(conv)  # lối vào chào chuẩn — đi qua bọc ngôn ngữ (tiếng Mông)
    else:
        intent = await intents.resolve(message, conv.get("state", "greet"))
        reply = await flow.handle_turn(
            conv,
            intent,
            client_page_context=(req.client_context.page_context if req.client_context else None),
        )

    payload = _serialize(conv, reply)
    # Reply RỖNG (bot im lặng chờ trang) → không lưu history, không đè last_reply —
    # khôi phục phiên phải render lại được câu có nội dung gần nhất.
    if reply.display_md or reply.cards or reply.chips:
        store.push_history(conv, "bot", reply.display_md, "bot")
        conv["last_reply"] = {
            k: payload[k] for k in ("display_md", "tts_text", "tts_lang", "chips", "cards", "state")
        }
    await store.save(conv)

    if settings.llm_debug:
        logger.info("[assistant] %s src=%s state=%s msg=%r", conv["_id"], req.source, conv["state"], message[:120])
    return payload


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, user: dict = Depends(require_auth)):
    """Người dân bấm 'Cuộc trò chuyện mới' / 'Xóa dữ liệu' — xoá NGAY, không chờ TTL."""
    from app.db.mongo import get_db

    await access.get_owned_conversation(conv_id, user)
    await get_db().conversations.delete_one({
        "_id": conv_id,
        "auth_user.id": str(user.get("id") or ""),
    })
    return {"ok": True}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, user: dict = Depends(require_auth)):
    conv = await access.get_owned_conversation(conv_id, user)
    return {
        "conversation_id": conv["_id"],
        "state": conv.get("state", "greet"),
        "lang": conv.get("lang", "vi"),
        "procedure_key": conv.get("procedure_key"),
        "location": conv.get("location", {}),
        "execution_subject": conv.get("execution_subject", "self"),
        "progress": flow.build_progress(conv),
        "awaiting_events": conv.get("awaiting_events", []),
        # Sidebar có thể bị dựng lại sau full navigation. Trả id phiên để nó nối lại WS;
        # attach_plan đã lưu trong conversation sẽ được page_status lấy lại nếu lỡ mất event.
        "upload_session_id": conv.get("upload_session_id"),
        "last_reply": _last_reply_for_restore(conv),
        # Đuôi hội thoại để render lại khung chat (bỏ system event + mọi lệnh máy còn sót).
        "history": [
            {"role": h["role"], "text": h["text"]}
            for h in conv.get("history", [])[-30:]
            if h.get("source") != "system" and not str(h.get("text", "")).startswith("__")
        ],
    }
