"""Hàm dùng chung cho flow hội thoại (docs/05): tạo phiên + dựng lại action show_qr."""
from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import store
from app.channels.handfree.documents.router import (
    _GENERIC_DOCS,
    _qr_png_base64,
    mobile_session_url,
)


def docs_for_conversation(conv: dict) -> list[dict]:
    """Checklist đúng BƯỚC hội thoại đang đứng, không phải checklist chung của thủ tục."""
    from app.channels.handfree.chat import guided_steps as guided

    proc = get_procedure(conv.get("procedure_key") or "") or {}
    by_target = guided.docs_for_target(conv, proc, str(conv.get("docs_target") or ""))
    if by_target is not None:
        return by_target
    return proc.get("requiredDocs") or _GENERIC_DOCS


def _owner_hint(conv: dict) -> dict:
    owner = conv.get("owner_context") or {}
    return {
        "fullName": str(owner.get("fullName") or "").strip(),
        "identityNumber": str(owner.get("identityNumber") or "").strip(),
    }


async def create_for_conversation(conv: dict) -> dict:
    sess = store.new_session(
        conv["_id"],
        conv.get("procedure_key") or "",
        docs_for_conversation(conv),
        owner_user_id=str((conv.get("auth_user") or {}).get("id") or ""),
    )
    # Mốc "căn cước của ĐÚNG người này" cho khâu phân loại: endpoint nhận tệp chỉ thấy phiên,
    # không thấy hội thoại, nên phải gắn vào chính phiên.
    sess["owner_hint"] = _owner_hint(conv)
    await store.save(sess)
    conv["upload_session_id"] = sess["_id"]
    return show_qr_action(sess["_id"])


async def sync_for_conversation(conv: dict, sess: dict | None = None) -> None:
    """Phiên dùng lại xuyên bước → cập nhật checklist và mốc chủ hồ sơ cho đúng bước hiện tại."""
    from app.channels.handfree.chat import guided_steps as guided

    proc = get_procedure(conv.get("procedure_key") or "") or {}
    wanted = guided.docs_for_target(conv, proc, str(conv.get("docs_target") or ""))
    if wanted is None:
        return  # thủ tục không có checklist theo bước → không đụng tới phiên
    sid = str(conv.get("upload_session_id") or "")
    if not sid:
        return
    sess = sess or await store.get(sid)
    if not sess:
        return
    current = [str(d.get("key") or "") for d in sess.get("required_docs") or []]
    if [str(d.get("key") or "") for d in wanted] != current:
        await store.set_required_docs(sid, wanted)
    hint = _owner_hint(conv)
    if hint != (sess.get("owner_hint") or {}) and (hint["fullName"] or hint["identityNumber"]):
        await store.set_owner_hint(sid, hint)


def show_qr_action(sid: str) -> dict:
    url = mobile_session_url(sid)
    return {"type": "show_qr", "session_id": sid, "mobile_url": url,
            "qr_png_base64": _qr_png_base64(url)}


async def progress_of(sid: str) -> dict | None:
    sess = await store.get(sid)
    return store.progress(sess) if sess else None


async def complete_session(sid: str) -> None:
    """Chốt phiên từ flow (nhánh scan "đã đưa đủ") — KHÔNG broadcast để tránh FE bắn
    docs_complete lần hai (flow đã tự chuyển state ngay trong lượt này)."""
    # $set nguyên tử — không ghi đè cả doc nên không nuốt file mà /files đang thêm cùng lúc.
    await store.set_complete(sid, True)
