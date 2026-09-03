"""Phiên tải ảnh QR của Auto Fill và adapter tương thích Handfree cũ.

Extension xác thực bằng Bearer JWT; điện thoại dùng capability HMAC chỉ có quyền trên
đúng một session. Capability nằm trong URL fragment rồi được gửi bằng ``X-Upload-Token``
để không xuất hiện trong access log. Giao diện Auto Fill đặt tại ``/m/autofill/{sid}``.
"""
import base64
import io

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.deps import require_auth
from app.upload_session import store
from app.upload_session.access import (
    create_upload_capability,
    ensure_upload_session_experience,
    require_upload_session_access,
    upload_session_experience,
)
from app.upload_session.mobile_page import render_mobile_page
from app.upload_session.streaming import (
    FileLimitExceeded,
    SessionLimitExceeded,
    copy_upload_to_staging,
)
from app.upload_session.ws import broadcast

router = APIRouter(tags=["upload-session"])


def _require_handfree_enabled() -> None:
    if not settings.handfree_enabled:
        raise HTTPException(status_code=404, detail="Kênh Handfree chưa được bật.")


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


def mobile_session_url(sid: str) -> str:
    token = create_upload_capability(sid)
    return f"{mobile_base()}/m/autofill/{sid}#token={token}"


@router.post("/api/v1/upload-sessions")
async def create_session(user: dict = Depends(require_auth)):
    """Cán bộ (có token) tạo phiên → trả QR để điện thoại quét."""
    sess = store.new_session(user["id"])
    await store.save(sess)
    url = mobile_session_url(sess["_id"])
    return {"session_id": sess["_id"], "mobile_url": url,
            "qr_png_base64": _qr_png_base64(url), "received": 0}


@router.get("/api/v1/upload-sessions/{sid}")
async def get_session(
    sid: str,
    response: Response,
    sess: dict = Depends(require_upload_session_access),
):
    """Poll/khôi phục danh sách ảnh của phiên sau khi kiểm tra JWT/capability."""
    response.headers["Cache-Control"] = "no-store, max-age=0"
    if upload_session_experience(sess) == "handfree":
        _require_handfree_enabled()
        return {
            "session_id": sid,
            "procedure_key": sess["procedure_key"],
            "required_docs": sess["required_docs"],
            "files": [
                {k: f.get(k) for k in ("fid", "doc_key", "side", "name", "note")}
                for f in sess.get("files", [])
            ],
            "progress": store.progress(sess),
        }
    ensure_upload_session_experience(sess, "autofill")
    return {"session_id": sid,
            "files": [{k: f.get(k) for k in ("fid", "name", "type", "size")} for f in sess["files"]],
            "received": len(sess["files"])}


@router.get("/api/v1/upload-sessions/{sid}/files/{fid}")
async def get_file(sid: str, fid: str):
    """Tải bytes 1 ảnh về (extension kéo vào danh sách file popup).

    ⚠ TẠM THỜI BỎ AUTH (require_upload_session_access) — extension đang phát hành chỉ kéo bytes
    qua Port background nên chưa gắn Bearer → 401 → "gửi được mà không nhận". Trong lúc chờ bản
    FE mới lên chợ (đã gắn token trong endpoints.js.fetchUploadFileDataUrl), endpoint này coi
    ``sid`` (64-bit) + ``fid`` ngẫu nhiên như capability-qua-URL (không đoán được).
    TODO(bảo mật): KHÔI PHỤC ``Depends(require_upload_session_access)`` sau khi FE mới đã phát hành.
    """
    sess = await store.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Phiên không tồn tại hoặc đã hết hạn.")
    if upload_session_experience(sess) == "handfree":
        _require_handfree_enabled()
    meta = next((f for f in sess.get("files", []) if f["fid"] == fid), None)
    raw = store.read_file_bytes(sid, fid) if meta else None
    if raw is None:
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return Response(content=raw, media_type=meta.get("type") or "image/jpeg")


@router.post("/api/v1/upload-sessions/{sid}/files")
async def upload_files(
    sid: str,
    files: list[UploadFile] = File(...),
    doc_key: str = Form(default=""),
    sess: dict = Depends(require_upload_session_access),
):
    """Điện thoại gửi một lô ảnh; Auto Fill lưu phẳng rồi phát sự kiện WS."""
    if upload_session_experience(sess) == "handfree":
        _require_handfree_enabled()
        # Compatibility window cho extension Handfree hiện hữu. Client mới dùng namespace
        # /api/v1/assistant/document-sessions, nhưng cùng gọi đúng một implementation.
        from app.channels.handfree.documents.router import upload_files as upload_handfree_files

        return await upload_handfree_files(sid, files, doc_key, sess)
    ensure_upload_session_experience(sess, "autofill")
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    max_total_bytes = settings.max_total_payload_mb * 1024 * 1024
    existing_bytes = store.total_file_bytes(sess)
    incoming_bytes = 0
    staged: list[dict] = []
    committed: list[str] = []
    metadata_persisted = False
    accepted: list[dict] = []
    try:
        for uf in files:
            filename = uf.filename or "anh.jpg"
            staged_path = store.new_staged_file_path(sid)
            remaining_total = max_total_bytes - existing_bytes - incoming_bytes
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
                    detail=f"Ảnh {filename} vượt {settings.max_file_size_mb}MB.",
                ) from exc
            except SessionLimitExceeded as exc:
                raise HTTPException(
                    status_code=413,
                    detail=(f"Tổng dung lượng giấy tờ trong phiên vượt "
                            f"{settings.max_total_payload_mb}MB."),
                ) from exc
            incoming_bytes += size
            staged.append({
                "path": staged_path,
                "name": filename,
                "type": uf.content_type or "image/jpeg",
                "size": size,
            })

        for item in staged:
            fid = store.new_file_id(item["name"])
            store.commit_staged_file(sid, item["path"], fid)
            committed.append(fid)
            accepted.append({
                "fid": fid,
                "name": item["name"],
                "type": item["type"],
                "size": item["size"],
            })

        updated = await store.append_files_with_limit(sid, accepted, max_total_bytes)
        if not updated:
            raise HTTPException(
                status_code=413,
                detail=f"Tổng dung lượng giấy tờ trong phiên vượt {settings.max_total_payload_mb}MB.",
            )
        metadata_persisted = True
    finally:
        for item in staged:
            store.delete_staged_file(item["path"])
        if not metadata_persisted:
            for fid in committed:
                store.delete_file_bytes(sid, fid)

    received = len(updated.get("files", []))
    await broadcast(sid, {"type": "files_added", "files": accepted, "received": received})
    return {"accepted": accepted, "received": received}


@router.delete("/api/v1/upload-sessions/{sid}/files/{fid}")
async def legacy_delete_file(
    sid: str,
    fid: str,
    sess: dict = Depends(require_upload_session_access),
):
    """Adapter tạm thời cho sidebar Handfree chưa chuyển sang namespace mới."""
    _require_handfree_enabled()
    ensure_upload_session_experience(sess, "handfree")
    from app.channels.handfree.documents.router import delete_file as delete_handfree_file

    return await delete_handfree_file(sid, fid, sess)


@router.post("/api/v1/upload-sessions/{sid}/complete")
async def legacy_force_complete(
    sid: str,
    sess: dict = Depends(require_upload_session_access),
):
    """Adapter chốt phiên cho sidebar Handfree cũ; Auto Fill không dùng endpoint này."""
    _require_handfree_enabled()
    ensure_upload_session_experience(sess, "handfree")
    from app.channels.handfree.documents.router import force_complete as complete_handfree_session

    return await complete_handfree_session(sid, sess)


@router.get("/m/autofill/{sid}")
async def mobile_page(sid: str):
    sess = await store.get(sid)
    if not sess or upload_session_experience(sess) != "autofill":
        return Response(content="<h3>Phiên đã hết hạn. Bà con quét lại mã QR mới trên máy tính nhé.</h3>",
                        media_type="text/html; charset=utf-8", status_code=404)
    return Response(content=render_mobile_page(sid), media_type="text/html; charset=utf-8")


@router.get("/m/{sid}")
async def legacy_mobile_dispatch(sid: str):
    """QR cũ vẫn vào đúng giao diện trong compatibility window."""
    sess = await store.get(sid)
    if not sess:
        return Response(
            content="<h3>Phiên đã hết hạn. Công dân quét lại mã QR mới nhé.</h3>",
            media_type="text/html; charset=utf-8",
            status_code=404,
        )
    experience = upload_session_experience(sess)
    if experience == "handfree" and not settings.handfree_enabled:
        return Response(
            content="<h3>Kênh Handfree chưa được bật.</h3>",
            media_type="text/html; charset=utf-8",
            status_code=404,
        )
    token = create_upload_capability(sid)
    return RedirectResponse(url=f"/m/{experience}/{sid}#token={token}", status_code=307)
