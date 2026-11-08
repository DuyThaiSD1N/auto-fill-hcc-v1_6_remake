"""Điều phối khôi phục hồ sơ đang làm dở — flow / router chỉ gọi các hàm ở đây.

Vòng đời:
  1. Mỗi lượt chat (`checkpoint`): hồ sơ đã có giấy tờ mà chưa nộp → sao dữ liệu từng bước vào bản ghi, gia hạn 30 phút.
  2. Phiên bị đóng (`on_close`): hết giờ chờ / cổng văng về trang chủ thì giữ; cán bộ chủ động làm mới thì xoá.
  3. Lượt sau chọn lại đúng thủ tục (`before_turn`): gợi ý khôi phục hoặc làm mới hoàn toàn.
  4. Khôi phục (`after_turn`): tới bước nhận giấy tờ thì nạp lại phiên giấy tờ cũ (không xin đồng ý lại); tới bước
     nào flow bật tác vụ OCR/LLM thì nạp dữ liệu đã lưu của bước đó thay cho chạy lại.
"""
import logging
import re
from datetime import timedelta, timezone

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.chat.resume import registry, replay, store
from app.upload_session import store as up_store

logger = logging.getLogger(__name__)

ACCEPT_SEND = "__action:resume_accept"
DECLINE_SEND = "__action:resume_decline"
# Phiên bị đóng ngoài ý cán bộ (hết giờ chờ, cổng đẩy về trang chủ) → giữ để khôi phục. Lý do khác (trò chuyện mới,
# làm thủ tục khác, đã xong) là cán bộ chủ động bỏ hồ sơ → xoá ngay.
_KEEP_ON_CLOSE = frozenset({"idle", "dvc-home"})
# Flow tới bước xin đồng ý / chọn cách gửi giấy tờ = lúc nạp lại phiên giấy tờ cũ.
_DOCS_STATES = frozenset({"consent", "ask_doc_method"})
_VN = timezone(timedelta(hours=7))


def _flow():
    from app.channels.handfree.chat import flow  # flow import module này → nạp muộn tránh vòng import

    return flow


def _user_id(conv: dict) -> str:
    return str((conv.get("auth_user") or {}).get("id") or "")


def _join(first, *rest):
    """Ghép nhiều câu trả lời thành một lượt (chỉ chạy ngoài chế độ Mông — registry đã chặn)."""
    out = _flow().Reply(first.display_md, first.tts_text)
    out.chips, out.cards, out.actions = list(first.chips), list(first.cards), list(first.actions)
    out.awaiting_events = list(first.awaiting_events)
    for r in rest:
        out.display_md = "\n\n".join(t for t in (out.display_md, r.display_md) if t)
        out.tts_text = " ".join(t for t in (out.tts_text, r.tts_text) if t)
        out.chips = r.chips or out.chips
        out.cards = [*out.cards, *r.cards]
        out.actions = [*out.actions, *r.actions]
        out.awaiting_events = r.awaiting_events or out.awaiting_events
    return out


def _say(tpl: dict, **kw):
    flow = _flow()
    return flow.Reply(*flow._fmt(tpl, **kw))


async def _session_fids(sid: str) -> list[str]:
    sess = await up_store.get(sid) if sid else None
    return [str(f.get("fid")) for f in (sess or {}).get("files") or [] if f.get("fid")]


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


# ── 1. Lưu ──

async def checkpoint(conv: dict) -> None:
    try:
        await _checkpoint(conv)
    except Exception:  # noqa: BLE001 — lưu khôi phục hỏng không được làm hỏng lượt chat
        logger.exception("[resume] lưu mốc hồ sơ %s lỗi", conv.get("_id"))


async def _checkpoint(conv: dict) -> None:
    adapter = registry.adapter_for(conv)
    if adapter is None:
        return
    if conv.get("submit_clicked_at") or conv.get("submitted_completed"):
        await store.delete(conv["_id"])
        return
    resume = conv.get("resume") or {}
    live_sid = str(conv.get("upload_session_id") or "")
    sid = live_sid or str((resume.get("session") or {}).get("upload_session_id") or "")
    fids = await _session_fids(sid)
    if not fids:
        return  # chưa đưa giấy tờ nào → không có gì để khôi phục
    prev = await store.get(conv["_id"]) or {}
    saved = prev.get("steps") or resume.get("steps") or {}
    consent = conv.get("consent") if (conv.get("consent") or {}).get("accepted") else prev.get("consent")
    await store.save(conv["_id"], {
        "user_id": _user_id(conv),
        "procedure_key": conv["procedure_key"],
        "family": adapter.family,
        "principal": conv.get("portal_principal") or prev.get("principal") or resume.get("principal") or {},
        "upload_session_id": sid,
        "doc_method": conv.get("doc_method") or prev.get("doc_method"),
        "consent": consent,
        # Chưa tới bước nạp lại giấy tờ thì hội thoại chưa có dữ liệu của phiên trước → giữ nguyên bản đã lưu.
        "steps": adapter.capture(conv, saved, fids) if live_sid else saved,
        "started_at": conv.get("logged_in_at") or conv.get("dossier_started_at"),
    })


async def on_form_snapshot(user_id: str, request_id: str, kind: str, at: int, fields: list[dict]) -> bool:
    """Ảnh chụp tờ khai (sau điền / cán bộ sửa / rời bước) → bản cán bộ sửa được ưu tiên khi điền lại."""
    return await store.set_declaration_snapshot(user_id, request_id, {"kind": kind, "at": at, "fields": fields})


# ── 2. Đóng phiên ──

async def on_close(conv_id: str, reason: str) -> None:
    if reason in _KEEP_ON_CLOSE:
        await store.close(conv_id, reason)
    else:
        await store.delete(conv_id)


async def discard(conv: dict) -> None:
    """Đã bấm nộp → không còn là hồ sơ dở."""
    if registry.adapter_for(conv) is not None:
        await store.delete(conv["_id"])


# ── 3. Gợi ý khôi phục ──

def _choice(intent: Intent) -> str:
    if intent.kind == "action" and intent.value in ("resume_accept", "resume_decline"):
        return intent.value.removeprefix("resume_")
    return {"confirm": "accept", "deny": "decline"}.get(intent.kind, "")


def _confirms_procedure(intent: Intent) -> bool:
    return intent.kind == "confirm" or (intent.kind == "action" and intent.value == "goto_login")


def _offer_reply(conv: dict, record: dict, adapter):
    principal = record.get("principal") or {}
    stopped = record.get("closed_at") or record.get("last_activity_at")
    if stopped is not None and stopped.tzinfo is None:
        stopped = stopped.replace(tzinfo=timezone.utc)
    progress = [vi.RESUME_PROGRESS["docs"],
                *(vi.RESUME_PROGRESS[k] for k in adapter.progress(record.get("steps") or {}))]
    r = _say(vi.RESUME_OFFER, procedure=_flow()._proc_label(conv),
             citizen=principal.get("name") or vi.RESUME_CITIZEN_UNKNOWN,
             stopped_at=stopped.astimezone(_VN).strftime("%H:%M") if stopped else "?",
             progress=", ".join(progress), minutes=store.minutes_left(record))
    r.chips = [{"label": vi.RESUME_ACCEPT_LABEL, "send": ACCEPT_SEND, "solid": True},
               {"label": vi.RESUME_DECLINE_LABEL, "send": DECLINE_SEND}]
    return r


async def before_turn(conv: dict, intent: Intent):
    """Chạy đầu mỗi lượt. Trả Reply khi lượt này thuộc về gợi ý khôi phục; None → flow xử lý như thường."""
    replay.set_kinds(())
    adapter = registry.adapter_for(conv)
    if adapter is None:
        conv.pop("resume_offer", None)
        return None
    adapter.observe(conv, intent)
    resume = conv.get("resume")
    if resume:
        sid = str(conv.get("upload_session_id") or (resume.get("session") or {}).get("upload_session_id") or "")
        replay.set_kinds(adapter.replayable(resume, await _session_fids(sid)))
        return None
    offer = conv.get("resume_offer")
    if offer and (conv.get("state") != "confirm_procedure" or offer.get("procedure_key") != conv.get("procedure_key")):
        conv.pop("resume_offer", None)  # đã rời màn xác nhận thủ tục (đổi thủ tục…) → lời gợi ý hết hiệu lực
        offer = None
    if offer:
        choice = _choice(intent)
        if choice == "accept":
            return await _accept(conv, offer)
        if choice == "decline":
            await store.delete(offer["id"])
            conv.pop("resume_offer", None)
            return _flow()._start_guide_login(conv)
        return None
    if conv.get("state") == "confirm_procedure" and _confirms_procedure(intent):
        record = await store.latest(_user_id(conv), str(conv.get("procedure_key") or ""))
        if record and record["_id"] != conv["_id"]:
            conv["resume_offer"] = {"id": record["_id"], "procedure_key": conv["procedure_key"]}
            return _offer_reply(conv, record, adapter)
    return None


async def _accept(conv: dict, offer: dict):
    conv.pop("resume_offer", None)
    record = await store.get(offer["id"])
    if not record or record.get("user_id") != _user_id(conv):
        return _join(_say(vi.RESUME_EXPIRED), _flow()._start_guide_login(conv))
    record = await store.rekey(record, conv["_id"])
    conv["resume"] = {
        "from": record["resumed_from"],
        "steps": record.get("steps") or {},
        "snapshot": record.get("declaration_snapshot") or {},
        "principal": record.get("principal") or {},
        "session": {k: record.get(k) for k in ("upload_session_id", "doc_method", "consent")},
        "replayed": [],
        "docs_restored": False,
    }
    return _join(_say(vi.RESUME_ACCEPTED), _flow()._start_guide_login(conv))


# ── 4. Khôi phục từng bước ──

def _other_citizen(conv: dict, resume: dict) -> bool:
    """Chỉ khôi phục cho đúng công dân: cổng đã đăng nhập người có số định danh khác → không đưa dữ liệu sang."""
    before = _digits((resume.get("principal") or {}).get("cccd"))
    now = _digits((conv.get("portal_principal") or {}).get("cccd"))
    return bool(before and now and before != now)


async def _restore_docs(conv: dict, resume: dict, reply, page_context: dict | None):
    """Bước nhận giấy tờ: gắn lại phiên giấy tờ cũ rồi chốt luôn như vừa nhận đủ giấy tờ."""
    flow = _flow()
    if _other_citizen(conv, resume):
        conv.pop("resume", None)
        await store.delete(conv["_id"])
        return _join(_say(vi.RESUME_OTHER_CITIZEN), reply), None
    session = resume.get("session") or {}
    sid = str(session.get("upload_session_id") or "")
    fids = await _session_fids(sid)
    if not fids:
        conv.pop("resume", None)
        await store.delete(conv["_id"])
        return _join(_say(vi.RESUME_DOCS_GONE), reply), None
    await up_store.rebind_conversation(sid, conv["_id"])
    conv["upload_session_id"] = sid
    conv["doc_method"] = session.get("doc_method") or "scan"
    if (session.get("consent") or {}).get("accepted"):
        conv["consent"] = session["consent"]
    await flow.upload_service.sync_for_conversation(conv)
    resume["docs_restored"] = True
    restored = await flow._docs_complete(conv, page_context)
    restored.actions = [{"type": "resume_upload_session", "session_id": sid}, *restored.actions]
    return restored, _say(vi.RESUME_DOCS_RESTORED, files_count=len(fids))


async def after_turn(conv: dict, intent: Intent, reply, client_page_context: dict | None):
    """Chạy sau khi flow xử lý xong lượt: nạp lại giấy tờ / dữ liệu bước nếu lượt này vừa tới bước đó."""
    adapter = registry.adapter_for(conv)
    if adapter is None:
        return reply
    adapter.decorate(conv, reply)
    resume = conv.get("resume")
    if not resume:
        return reply
    notes = []
    # Chỉ bỏ qua bước xin đồng ý khi hồ sơ dở đã có bản đồng ý; chưa có thì để công dân đồng ý rồi mới nạp giấy tờ.
    consented = bool(((resume.get("session") or {}).get("consent") or {}).get("accepted"))
    if (not resume.get("docs_restored") and conv.get("state") in _DOCS_STATES
            and (consented or conv.get("state") != "consent")):
        page_context = (intent.payload if intent.kind == "event" and intent.value == "page_status"
                        else client_page_context)
        reply, note = await _restore_docs(conv, resume, reply, page_context)
        if note is None:
            return reply
        notes.append(note)
    ready = []
    while (step := adapter.due_step(conv)) is not None:
        adapter.apply(step, conv)
        notes.append(_say(vi.RESUME_STEP_REPLAYED[step.key]))
        ready.append(await _flow()._handle_turn_inner(conv, Intent("event", step.event)))
    if not ready:
        return _join(*notes, reply) if notes else reply
    # Câu "đang đọc giấy tờ…" của lượt gốc không còn đúng — thay bằng câu khôi phục, giữ nguyên lệnh / nút.
    base = _join(*notes)
    base.chips, base.cards, base.actions = reply.chips, reply.cards, reply.actions
    base.awaiting_events = reply.awaiting_events
    return _join(base, *ready)
