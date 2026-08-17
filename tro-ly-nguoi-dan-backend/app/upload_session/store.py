"""Phiên tải giấy tờ qua QR (docs/05 §1) — metadata Mongo `upload_sessions` (TTL), file trên disk.

File nằm `{storage_dir}/upload_sessions/{sid}/{fid}` — pipeline Bước 6 đọc thẳng từ đây,
người dân KHÔNG phải gửi lại.
"""
import base64
import secrets
from datetime import datetime, timezone
from pathlib import Path

from pymongo import ReturnDocument

from app.config import settings
from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dir(sid: str) -> Path:
    p = Path(settings.storage_dir) / "upload_sessions" / sid
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_session(conversation_id: str, procedure_key: str, required_docs: list[dict]) -> dict:
    return {
        "_id": f"HS-{secrets.token_hex(3).upper()}",   # ngắn để hiện trên UI ("phiên HS-3F9A2C")
        "conversation_id": conversation_id,
        "procedure_key": procedure_key,
        # required_docs: [{key, name, icon, sides}] — sinh từ registry.requiredDocs
        "required_docs": required_docs,
        # files: [{fid, doc_key|null, side: "front"|"back"|null, name, type, size, note}]
        "files": [],
        "complete": False,
        "created_at": _now(),
        "updated_at": _now(),
    }


async def get(sid: str) -> dict | None:
    if not sid:
        return None
    return await get_db().upload_sessions.find_one({"_id": sid})


async def save(sess: dict) -> None:
    sess["updated_at"] = _now()
    await get_db().upload_sessions.replace_one({"_id": sess["_id"]}, sess, upsert=True)


# ── Cập nhật NGUYÊN TỬ (không đọc-sửa-ghi cả doc) ──
# Nhiều POST ảnh "chụp lần lượt" + nút "Dừng & gửi tất cả" (/complete) chạy song song. Nếu mỗi
# đường get→sửa→replace_one cả doc thì cái ghi sau ĐÈ cái trước → mất `files` → "Phiên không còn
# file nào". $push/$set/$pull chỉ đụng đúng field nên các thao tác này cộng dồn, không giẫm nhau.

async def append_files(sid: str, metas: list[dict]) -> dict | None:
    """Thêm file vào phiên bằng $push (nguyên tử). Trả doc SAU khi cập nhật."""
    if not sid:
        return None
    if not metas:
        return await get(sid)
    return await get_db().upload_sessions.find_one_and_update(
        {"_id": sid},
        {"$push": {"files": {"$each": metas}}, "$set": {"updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )


async def set_complete(sid: str, value: bool) -> dict | None:
    """Đặt cờ complete bằng $set (nguyên tử) — KHÔNG đụng mảng `files`, nên không ghi đè ảnh
    mà một /files khác đang thêm cùng lúc."""
    if not sid:
        return None
    return await get_db().upload_sessions.find_one_and_update(
        {"_id": sid},
        {"$set": {"complete": value, "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )


async def pull_file(sid: str, fid: str) -> dict | None:
    """Gỡ 1 file khỏi phiên bằng $pull (nguyên tử) + mở lại phiên (complete=False) để chụp lại."""
    if not sid:
        return None
    return await get_db().upload_sessions.find_one_and_update(
        {"_id": sid},
        {"$pull": {"files": {"fid": fid}}, "$set": {"complete": False, "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )


def save_file_bytes(sid: str, fid: str, data: bytes) -> None:
    (_dir(sid) / fid).write_bytes(data)


def read_file_bytes(sid: str, fid: str) -> bytes | None:
    p = _dir(sid) / fid
    return p.read_bytes() if p.exists() else None


def delete_file_bytes(sid: str, fid: str) -> None:
    p = _dir(sid) / fid
    if p.exists():
        p.unlink()


async def delete_session(sid: str) -> None:
    """Xoá THẬT phiên + file trên disk (nút 'Xóa dữ liệu' — docs/08)."""
    import shutil

    if not sid:
        return
    await get_db().upload_sessions.delete_one({"_id": sid})
    p = Path(settings.storage_dir) / "upload_sessions" / sid
    if p.exists():
        shutil.rmtree(p)


def new_file_id(name: str) -> str:
    ext = (name.rsplit(".", 1)[-1] if "." in name else "jpg").lower()[:5]
    return f"f{secrets.token_hex(4)}.{ext}"


def file_to_data_url(sid: str, f: dict) -> str | None:
    """Dựng lại {name,type,dataUrl} cho pipeline process/attach (hợp đồng cũ)."""
    raw = read_file_bytes(sid, f["fid"])
    if raw is None:
        return None
    return f"data:{f.get('type') or 'image/jpeg'};base64,{base64.b64encode(raw).decode()}"


def progress(sess: dict) -> dict:
    """Tóm tắt tiến trình cho card doc_progress + WS event (docs/05 §1).

    Slot `optional` KHÔNG tính vào total/received "bắt buộc" — chỉ hiển thị.
    """
    docs = []
    for d in sess["required_docs"]:
        received_count = sum(1 for f in sess["files"] if f.get("doc_key") == d["key"])
        repeatable = bool(d.get("repeatable") or sess.get("procedure_key") == "chung-thuc-ban-sao")
        docs.append({**d, "repeatable": repeatable,
                     "received": min(received_count, d["sides"]),
                     "receivedCount": received_count})
    required = [d for d in docs if not d.get("optional")]
    total = sum(d["sides"] for d in required)
    received = sum(d["received"] for d in required)
    unknown = sum(1 for f in sess["files"] if not f.get("doc_key"))
    # files_count = TỔNG mọi tệp đã nhận (bắt buộc + tuỳ chọn + chưa nhận ra loại). Dùng để HIỂN
    # THỊ "Đã nhận X tệp" — tránh cảnh gửi tệp vào slot 'nếu có' mà báo 0. received/total (chỉ
    # BẮT BUỘC) giữ nguyên cho is_enough + thanh tiến trình.
    return {"docs": docs, "received": received, "total": total, "unknown": unknown,
            "files_count": len(sess["files"]),
            "complete": bool(sess.get("complete"))}


def is_enough(sess: dict) -> bool:
    """Đủ giấy tờ BẮT BUỘC. Lưu ý: có slot optional thì router KHÔNG tự chốt phiên
    (người dân có thể còn muốn thêm tờ khai/cam đoan) — chờ bấm 'Dừng & gửi tất cả'."""
    p = progress(sess)
    return p["total"] > 0 and p["received"] >= p["total"]


def has_optional_slots(sess: dict) -> bool:
    """Có ô còn cho phép nhận thêm thì không tự chốt phiên sau khi vừa đủ tối thiểu."""
    return sess.get("procedure_key") == "chung-thuc-ban-sao" or any(
        d.get("optional") or d.get("repeatable") for d in sess.get("required_docs", [])
    )
