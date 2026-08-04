"""Phiên tải ảnh qua QR (đơn giản, KHÔNG phân loại).

Extension (có token):  POST /api/v1/upload-sessions · GET .../{sid} · GET .../{sid}/files/{fid}
Điện thoại (MỞ, guard bằng sid bí mật): GET /m/{sid} (trang chụp ảnh) · POST .../{sid}/files
Realtime: ws.py broadcast files_added sau mỗi lô upload → popup kéo ảnh về danh sách file.

Vì sao mobile MỞ (không auth): điện thoại người dân không có token cán bộ. Bảo vệ bằng sid
ngẫu nhiên dài (capability token) + TTL phiên (Mongo tự dọn). Không có sid thì vô danh.
"""
import base64
import io

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from app.config import settings
from app.core.deps import require_auth
from app.upload_session import store
from app.upload_session.mobile_page import render_mobile_page
from app.upload_session.ws import broadcast

router = APIRouter(tags=["upload-session"])


def mobile_base() -> str:
    """URL công khai điện thoại quét — domain BE (auto-fill-hcc có domain thật nên không
    cần trò dò IP LAN)."""
    if settings.mobile_base_url:
        return settings.mobile_base_url.rstrip("/")
    return f"http://localhost:{settings.port}"


def _qr_png_base64(url: str) -> str:
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.post("/api/v1/upload-sessions")
async def create_session(user: dict = Depends(require_auth)):
    """Cán bộ (có token) tạo phiên → trả QR để điện thoại quét."""
    sess = store.new_session(user["id"])
    await store.save(sess)
    url = f"{mobile_base()}/m/{sess['_id']}"
    return {"session_id": sess["_id"], "mobile_url": url,
            "qr_png_base64": _qr_png_base64(url), "received": 0}


@router.get("/api/v1/upload-sessions/{sid}")
async def get_session(sid: str):
    """Poll/khôi phục danh sách ảnh của phiên (sid = capability token)."""
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại hoặc đã hết hạn.")
    return {"session_id": sid,
            "files": [{k: f.get(k) for k in ("fid", "name", "type", "size")} for f in sess["files"]],
            "received": len(sess["files"])}


@router.get("/api/v1/upload-sessions/{sid}/files/{fid}")
async def get_file(sid: str, fid: str):
    """Tải bytes 1 ảnh về (extension kéo vào danh sách file popup)."""
    sess = await store.get(sid)
    meta = next((f for f in (sess or {}).get("files", []) if f["fid"] == fid), None)
    raw = store.read_file_bytes(sid, fid) if meta else None
    if raw is None:
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return Response(content=raw, media_type=meta.get("type") or "image/jpeg")


@router.post("/api/v1/upload-sessions/{sid}/files")
async def upload_files(sid: str, files: list[UploadFile] = File(...)):
    """Điện thoại gửi 1 lô ảnh (MỞ, guard bằng sid). Không phân loại — lưu phẳng + bắn WS."""
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại hoặc đã hết hạn.")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    accepted = []
    for uf in files:
        raw = await uf.read()
        if len(raw) > max_bytes:
            raise HTTPException(status_code=413, detail=f"Ảnh {uf.filename} vượt {settings.max_file_size_mb}MB.")
        fid = store.new_file_id(uf.filename or "anh.jpg")
        store.save_file_bytes(sid, fid, raw)
        meta = {"fid": fid, "name": uf.filename or "anh.jpg",
                "type": uf.content_type or "image/jpeg", "size": len(raw)}
        sess["files"].append(meta)
        accepted.append(meta)

    await store.save(sess)
    await broadcast(sid, {"type": "files_added", "files": accepted, "received": len(sess["files"])})
    return {"accepted": accepted, "received": len(sess["files"])}


@router.get("/m/{sid}")
async def mobile_page(sid: str):
    sess = await store.get(sid)
    if not sess:
        return Response(content="<h3>Phiên đã hết hạn. Bà con quét lại mã QR mới trên máy tính nhé.</h3>",
                        media_type="text/html; charset=utf-8", status_code=404)
    return Response(content=render_mobile_page(sid), media_type="text/html; charset=utf-8")
