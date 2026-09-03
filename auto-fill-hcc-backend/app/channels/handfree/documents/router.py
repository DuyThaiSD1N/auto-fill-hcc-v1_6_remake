"""API phiên giấy tờ và giao diện mobile dành riêng cho channel Handfree.

API mới dùng namespace ``/api/v1/assistant/document-sessions``; giao diện điện thoại ở
``/m/handfree/{sid}``. File và quota vẫn dùng chung store với Auto Fill, còn phân loại
theo checklist thủ tục chỉ chạy trong router Handfree này.
"""
import base64
import io
import socket

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError
from app.channels.handfree.chat.access import get_owned_conversation
from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classify, store
from app.upload_session.access import (
    create_upload_capability,
    ensure_upload_session_experience,
    require_upload_session_access,
    upload_session_experience,
)
from app.channels.handfree.documents.mobile_page import render_mobile_page
from app.upload_session.streaming import (
    FileLimitExceeded,
    SessionLimitExceeded,
    copy_upload_to_staging,
)
from app.upload_session.ws import broadcast

router = APIRouter(
    prefix="/api/v1/assistant/document-sessions",
    tags=["assistant-document-session"],
)
mobile_router = APIRouter(tags=["assistant-document-mobile"])

# Fallback checklist khi thủ tục chưa khai requiredDocs trong registry.
_GENERIC_DOCS = [{"key": "giay_to", "name": "Giấy tờ theo hướng dẫn", "icon": "📄", "sides": 3}]
def _lan_ip() -> str:
    """IP LAN của máy chạy BE — dev không cần domain: điện thoại cùng wifi quét là vào."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "localhost"


def mobile_base() -> str:
    if settings.mobile_base_url:
        return settings.mobile_base_url.rstrip("/")
    return f"http://{_lan_ip()}:{settings.port}"


def _qr_png_base64(url: str) -> str:
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def mobile_session_url(sid: str) -> str:
    # Fragment không được browser gửi trong HTTP request/referrer, tránh capability lọt vào
    # Nginx access log. JavaScript mobile lấy token rồi gửi qua X-Upload-Token.
    token = create_upload_capability(sid)
    return f"{mobile_base()}/m/handfree/{sid}#token={token}"


class CreateSessionRequest(BaseModel):
    conversation_id: str
    procedure_key: str


@router.post("")
async def create_session(req: CreateSessionRequest, user: dict = Depends(require_auth)):
    conv = await get_owned_conversation(req.conversation_id, user)
    proc = get_procedure(req.procedure_key)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Không có thủ tục '{req.procedure_key}'.")
    conversation_procedure = str(conv.get("procedure_key") or "").strip()
    if conversation_procedure and conversation_procedure != req.procedure_key:
        raise AppError(
            "CONVERSATION_PROCEDURE_MISMATCH",
            "Thủ tục của phiên giấy tờ không khớp cuộc trò chuyện",
            409,
        )
    docs = proc.get("requiredDocs") or _GENERIC_DOCS
    sess = store.new_session(
        req.conversation_id, req.procedure_key, docs, owner_user_id=str(user.get("id") or "")
    )
    await store.save(sess)
    url = mobile_session_url(sess["_id"])
    return {
        "session_id": sess["_id"],
        "mobile_url": url,
        "qr_png_base64": _qr_png_base64(url),
        "required_docs": docs,
        "progress": store.progress(sess),
    }


@router.get("/{sid}")
async def get_session(
    sid: str,
    response: Response,
    sess: dict = Depends(require_upload_session_access),
):
    ensure_upload_session_experience(sess, "handfree")
    # Safari/WebView có thể cache GET cùng URL rồi trả progress cũ sau khi POST upload đã xong.
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return {
        "session_id": sid,
        "procedure_key": sess["procedure_key"],
        "required_docs": sess["required_docs"],
        "files": [{k: f.get(k) for k in ("fid", "doc_key", "side", "name", "note")} for f in sess["files"]],
        "progress": store.progress(sess),
    }


@router.get("/{sid}/files/{fid}")
async def get_file(
    sid: str,
    fid: str,
    sess: dict = Depends(require_upload_session_access),
):
    ensure_upload_session_experience(sess, "handfree")
    meta = next((f for f in sess.get("files", []) if f["fid"] == fid), None)
    raw = store.read_file_bytes(sid, fid) if meta else None
    if raw is None:
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return Response(content=raw, media_type=meta.get("type") or "image/jpeg")


@router.post("/{sid}/files")
async def upload_files(
    sid: str,
    files: list[UploadFile] = File(...),
    doc_key: str = Form(default=""),
    sess: dict = Depends(require_upload_session_access),
):
    ensure_upload_session_experience(sess, "handfree")
    if sess.get("complete"):
        raise HTTPException(status_code=409, detail="Phiên đã hoàn tất.")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    max_total_bytes = settings.max_total_payload_mb * 1024 * 1024
    existing_bytes = store.total_file_bytes(sess)
    incoming_bytes = 0
    payloads: list[dict] = []
    staged: list[dict] = []
    committed_file_ids: list[str] = []
    metadata_persisted = False
    try:
        for uf in files:
            filename = uf.filename or "anh.jpg"
            staged_path = store.new_staged_file_path(sid)
            remaining_total = max_total_bytes - existing_bytes - incoming_bytes
            if remaining_total < 0:
                raise HTTPException(
                    status_code=413,
                    detail=(f"Tổng dung lượng giấy tờ trong phiên vượt "
                            f"{settings.max_total_payload_mb}MB."),
                )
            try:
                size = await run_in_threadpool(
                    copy_upload_to_staging,
                    uf.file,
                    staged_path,
                    max_bytes,
                    remaining_total,
                )
            except FileLimitExceeded as exc:
                raise HTTPException(
                    status_code=413,
                    detail=f"Tệp {filename} vượt {settings.max_file_size_mb}MB.",
                ) from exc
            except SessionLimitExceeded as exc:
                raise HTTPException(
                    status_code=413,
                    detail=(f"Tổng dung lượng giấy tờ trong phiên vượt "
                            f"{settings.max_total_payload_mb}MB."),
                ) from exc
            incoming_bytes += size
            item = {"path": staged_path, "size": size}
            staged.append(item)
            payloads.append({
                "name": filename,
                "type": uf.content_type or "image/jpeg",
                # Chỉ là đường dẫn nội bộ do server tạo, không nhận từ request của người dùng.
                "path": str(staged_path),
            })

        results = await classify.classify_files(
            payloads,
            sess["required_docs"],
            sess["files"],
            hint_doc_key=doc_key or None,
            procedure_key=sess.get("procedure_key") or "",
        )
        accepted, metas = [], []
        for payload, staged_item, res in zip(payloads, staged, results):
            fid = store.new_file_id(payload["name"])
            store.commit_staged_file(sid, staged_item["path"], fid)
            committed_file_ids.append(fid)
            meta = {"fid": fid, "doc_key": res["doc_key"], "side": res["side"],
                    "name": payload["name"], "type": payload["type"],
                    "size": staged_item["size"], "note": res["note"]}
            metas.append(meta)
            accepted.append({**{k: meta[k] for k in ("fid", "doc_key", "side", "note")}})

        # Quota được kiểm tra LẠI ngay trong thao tác $push nguyên tử. Hai request đồng thời có
        # thể cùng vượt qua kiểm tra snapshot, nhưng chỉ request còn nằm trong 100MB được ghi.
        updated = await store.append_files_with_limit(sid, metas, max_total_bytes)
        if not updated:
            current = await store.get(sid)
            if current and current.get("complete"):
                raise HTTPException(status_code=409, detail="Phiên đã hoàn tất.")
            raise HTTPException(
                status_code=413,
                detail=f"Tổng dung lượng giấy tờ trong phiên vượt {settings.max_total_payload_mb}MB.",
            )
        metadata_persisted = True
        sess = updated
    finally:
        # File tạm chưa commit luôn phải biến mất. File đã commit chỉ được giữ khi metadata Mongo
        # đã ghi thành công; nếu không GET/điền sau này không thể tham chiếu và nó thành file rác.
        for staged_item in staged:
            store.delete_staged_file(staged_item["path"])
        if not metadata_persisted:
            for fid in committed_file_ids:
                store.delete_file_bytes(sid, fid)
    prog = store.progress(sess)
    # Tự chốt CHỈ khi đủ bắt buộc VÀ thủ tục không có slot tuỳ chọn — tự chốt sớm
    # sẽ khoá phiên trong lúc người dân còn đang thêm tờ khai/cam đoan.
    if (store.is_enough(sess)
            and not store.has_optional_slots(sess)
            and not sess.get("manual_complete_only")
            and not sess.get("complete")):
        sess = await store.set_complete(sid, True) or sess
        prog = store.progress(sess)
    await broadcast(sid, {"type": "progress", **prog})
    if sess.get("complete"):
        await broadcast(sid, {"type": "complete", **prog})
    return {"accepted": accepted, "progress": prog}


@router.delete("/{sid}/files/{fid}")
async def delete_file(
    sid: str,
    fid: str,
    sess: dict = Depends(require_upload_session_access),
):
    ensure_upload_session_experience(sess, "handfree")
    store.delete_file_bytes(sid, fid)
    # $pull nguyên tử + mở lại phiên (không ghi đè cả doc → không nuốt file đang upload).
    sess = await store.pull_file(sid, fid) or sess
    await broadcast(sid, {"type": "progress", **store.progress(sess)})
    return {"ok": True}


@router.post("/{sid}/complete")
async def force_complete(
    sid: str,
    sess: dict = Depends(require_upload_session_access),
):
    """Nút 'Dừng & gửi tất cả' — người dân chốt dù checklist chưa đủ (thiếu thì bot hỏi tiếp)."""
    ensure_upload_session_experience(sess, "handfree")
    # GUARD chống race: nút này hay chạy ĐUA với /files còn đang upload (mạng/máy chậm). Nếu
    # chốt lúc phiên CHƯA có file nào → broadcast complete → BE xử lý phiên rỗng → "0 file, thử
    # lại lần 2 mới được". Chưa có ảnh thì KHÔNG chốt, KHÔNG broadcast — báo mobile chờ upload xong.
    if not sess.get("files"):
        return {"ok": False, "detail": "Chưa nhận được tệp nào — công dân chờ gửi xong rồi bấm lại nhé.",
                "progress": store.progress(sess)}
    sess = await store.set_complete(sid, True) or sess
    prog = store.progress(sess)
    await broadcast(sid, {"type": "complete", **prog})
    return {"ok": True, "progress": prog}


@mobile_router.get("/m/handfree/{sid}")
async def mobile_page(sid: str):
    sess = await store.get(sid)
    if not sess or upload_session_experience(sess) != "handfree":
        return Response(content="<h3>Phiên đã hết hạn. Công dân quét lại mã QR mới trên máy tính nhé.</h3>",
                        media_type="text/html; charset=utf-8", status_code=404,
                        headers={"Cache-Control": "no-store, max-age=0"})
    return Response(content=render_mobile_page(sid), media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "no-store, max-age=0"})
