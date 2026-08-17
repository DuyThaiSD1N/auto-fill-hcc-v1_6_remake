"""API phiên tải giấy tờ + trang mobile (docs/05 §1, §3).

Extension:  POST /api/v1/upload-sessions · GET .../{sid} · GET .../{sid}/files/{fid}
Mobile:     GET /m/{sid} (trang chụp ảnh) · POST .../{sid}/files · DELETE .../files/{fid}
            · POST .../{sid}/complete ("Dừng & gửi tất cả")
Realtime:   ws.py broadcast — router này chỉ bắn event sau mỗi thay đổi.
"""
import base64
import io
import socket

import qrcode
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.procedures.registry import get_procedure
from app.upload_session import classify, store
from app.upload_session.mobile_page import render_mobile_page
from app.upload_session.ws import broadcast

router = APIRouter(tags=["upload-session"])

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


class CreateSessionRequest(BaseModel):
    conversation_id: str
    procedure_key: str


@router.post("/api/v1/upload-sessions")
async def create_session(req: CreateSessionRequest):
    proc = get_procedure(req.procedure_key)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Không có thủ tục '{req.procedure_key}'.")
    docs = proc.get("requiredDocs") or _GENERIC_DOCS
    sess = store.new_session(req.conversation_id, req.procedure_key, docs)
    await store.save(sess)
    url = f"{mobile_base()}/m/{sess['_id']}"
    return {
        "session_id": sess["_id"],
        "mobile_url": url,
        "qr_png_base64": _qr_png_base64(url),
        "required_docs": docs,
        "progress": store.progress(sess),
    }


@router.get("/api/v1/upload-sessions/{sid}")
async def get_session(sid: str):
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại hoặc đã hết hạn.")
    return {
        "session_id": sid,
        "procedure_key": sess["procedure_key"],
        "required_docs": sess["required_docs"],
        "files": [{k: f.get(k) for k in ("fid", "doc_key", "side", "name", "note")} for f in sess["files"]],
        "progress": store.progress(sess),
    }


@router.get("/api/v1/upload-sessions/{sid}/files/{fid}")
async def get_file(sid: str, fid: str):
    sess = await store.get(sid)
    meta = next((f for f in (sess or {}).get("files", []) if f["fid"] == fid), None)
    raw = store.read_file_bytes(sid, fid) if meta else None
    if raw is None:
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return Response(content=raw, media_type=meta.get("type") or "image/jpeg")


@router.post("/api/v1/upload-sessions/{sid}/files")
async def upload_files(sid: str, files: list[UploadFile] = File(...), doc_key: str = Form(default="")):
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại hoặc đã hết hạn.")
    if sess.get("complete"):
        raise HTTPException(status_code=409, detail="Phiên đã hoàn tất.")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    payloads, raws = [], []
    for uf in files:
        raw = await uf.read()
        if len(raw) > max_bytes:
            raise HTTPException(status_code=413, detail=f"Ảnh {uf.filename} vượt {settings.max_file_size_mb}MB.")
        raws.append(raw)
        payloads.append({
            "name": uf.filename or "anh.jpg",
            "type": uf.content_type or "image/jpeg",
            "dataUrl": f"data:{uf.content_type or 'image/jpeg'};base64,{base64.b64encode(raw).decode()}",
        })

    results = await classify.classify_files(
        payloads,
        sess["required_docs"],
        sess["files"],
        hint_doc_key=doc_key or None,
        procedure_key=sess.get("procedure_key") or "",
    )
    accepted, metas = [], []
    for payload, raw, res in zip(payloads, raws, results):  # map theo THỨ TỰ mảng
        fid = store.new_file_id(payload["name"])
        store.save_file_bytes(sid, fid, raw)
        meta = {"fid": fid, "doc_key": res["doc_key"], "side": res["side"],
                "name": payload["name"], "type": payload["type"], "size": len(raw),
                "note": res["note"]}
        metas.append(meta)
        accepted.append({**{k: meta[k] for k in ("fid", "doc_key", "side", "note")}})

    # $push nguyên tử — KHÔNG đọc-sửa-ghi cả doc (chống đua với /complete và POST ảnh khác
    # làm mất files). Dùng doc SAU cập nhật để tính progress/tự-chốt cho khớp thực tế.
    sess = await store.append_files(sid, metas) or sess
    prog = store.progress(sess)
    # Tự chốt CHỈ khi đủ bắt buộc VÀ thủ tục không có slot tuỳ chọn — tự chốt sớm
    # sẽ khoá phiên trong lúc người dân còn đang thêm tờ khai/cam đoan.
    if store.is_enough(sess) and not store.has_optional_slots(sess) and not sess.get("complete"):
        sess = await store.set_complete(sid, True) or sess
        prog = store.progress(sess)
    await broadcast(sid, {"type": "progress", **prog})
    if sess.get("complete"):
        await broadcast(sid, {"type": "complete", **prog})
    return {"accepted": accepted, "progress": prog}


@router.delete("/api/v1/upload-sessions/{sid}/files/{fid}")
async def delete_file(sid: str, fid: str):
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại.")
    store.delete_file_bytes(sid, fid)
    # $pull nguyên tử + mở lại phiên (không ghi đè cả doc → không nuốt file đang upload).
    sess = await store.pull_file(sid, fid) or sess
    await broadcast(sid, {"type": "progress", **store.progress(sess)})
    return {"ok": True}


@router.post("/api/v1/upload-sessions/{sid}/complete")
async def force_complete(sid: str):
    """Nút 'Dừng & gửi tất cả' — người dân chốt dù checklist chưa đủ (thiếu thì bot hỏi tiếp)."""
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại.")
    # GUARD chống race: nút này hay chạy ĐUA với /files còn đang upload (mạng/máy chậm). Nếu
    # chốt lúc phiên CHƯA có file nào → broadcast complete → BE xử lý phiên rỗng → "0 file, thử
    # lại lần 2 mới được". Chưa có ảnh thì KHÔNG chốt, KHÔNG broadcast — báo mobile chờ upload xong.
    if not sess.get("files"):
        return {"ok": False, "detail": "Chưa nhận được tệp nào — bà con chờ gửi xong rồi bấm lại nhé.",
                "progress": store.progress(sess)}
    sess = await store.set_complete(sid, True) or sess
    prog = store.progress(sess)
    await broadcast(sid, {"type": "complete", **prog})
    return {"ok": True, "progress": prog}


@router.get("/m/{sid}")
async def mobile_page(sid: str):
    sess = await store.get(sid)
    if not sess:
        return Response(content="<h3>Phiên đã hết hạn. Bà con quét lại mã QR mới trên máy tính nhé.</h3>",
                        media_type="text/html; charset=utf-8", status_code=404)
    return Response(content=render_mobile_page(sid), media_type="text/html; charset=utf-8")
