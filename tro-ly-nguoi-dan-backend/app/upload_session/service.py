"""Hàm dùng chung cho flow hội thoại (docs/05): tạo phiên + dựng lại action show_qr."""
from app.procedures.registry import get_procedure
from app.upload_session import store
from app.upload_session.router import _GENERIC_DOCS, _qr_png_base64, mobile_base


async def create_for_conversation(conv: dict) -> dict:
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    docs = proc.get("requiredDocs") or _GENERIC_DOCS
    sess = store.new_session(conv["_id"], conv.get("procedure_key") or "", docs)
    await store.save(sess)
    conv["upload_session_id"] = sess["_id"]
    return show_qr_action(sess["_id"])


def show_qr_action(sid: str) -> dict:
    url = f"{mobile_base()}/m/{sid}"
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
