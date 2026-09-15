"""Phiên tải giấy tờ qua QR (docs/05 §1) — metadata Mongo `upload_sessions` (TTL), file trên disk.

File nằm `{storage_dir}/upload_sessions/{sid}/{fid}` — pipeline Bước 6 đọc thẳng từ đây,
người dân KHÔNG phải gửi lại.
"""
import base64
import secrets
from datetime import datetime, timedelta, timezone
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


def new_session(
    conversation_id: str,
    procedure_key: str = "",
    required_docs: list[dict] | None = None,
    *,
    owner_user_id: str = "",
    experience: str | None = None,
) -> dict:
    """Tạo session cho cả Auto Fill và Handfree mà vẫn giữ contract gọi cũ.

    Auto Fill trước đây gọi ``new_session(user_id)``; Handfree truyền thêm procedure và
    checklist. Dùng ``experience`` lưu trong document để route/mobile không đoán theo URL.
    """
    is_handfree = experience == "handfree" or required_docs is not None or bool(procedure_key)
    now = _now()
    if not is_handfree:
        return {
            "_id": f"HS-{secrets.token_hex(8).upper()}",
            "experience": "autofill",
            "user_id": conversation_id,
            "owner_user_id": str(owner_user_id or conversation_id),
            "files": [],
            "created_at": now,
            "updated_at": now,
            "expires_at": now + timedelta(minutes=settings.upload_session_ttl_minutes),
        }

    # Gắn tên tiếng Mông theo SLOT KEY cho checklist (VÔ ĐIỀU KIỆN — sidebar tự quyết hiển thị
    # theo chế độ đang bật, nên toggle tiếng Mông giữa chừng phiên vẫn có sẵn dữ liệu).
    from app.channels.handfree.chat.script_mong import DOC_SLOT_HMONG

    docs = []
    for d in required_docs or []:
        item = dict(d)
        name_hmong = DOC_SLOT_HMONG.get(str(d.get("key") or ""))
        if name_hmong:
            item["nameHmong"] = name_hmong
        docs.append(item)
    return {
        # 64-bit thay cho mã 24-bit cũ: vẫn đủ ngắn để hiện trên UI nhưng tránh va chạm
        # phiên khi hệ thống có nhiều lượt upload. Quyền truy cập vẫn do capability/JWT quyết.
        "_id": f"HS-{secrets.token_hex(8).upper()}",
        "experience": "handfree",
        "conversation_id": conversation_id,
        "owner_user_id": str(owner_user_id or ""),
        "procedure_key": procedure_key,
        # required_docs: [{key, name, icon, sides, nameHmong?}] — sinh từ registry.requiredDocs
        "required_docs": docs,
        # files: [{fid, doc_key|null, side: "front"|"back"|null, name, type, size, note}]
        "files": [],
        "complete": False,
        # Lượt đầu được phép tự chốt khi đủ giấy bắt buộc. Lượt bổ sung bật cờ này để
        # danh sách cũ (vốn đã đủ) không làm phiên chốt ngay sau file mới đầu tiên.
        "manual_complete_only": False,
        "created_at": now,
        "updated_at": now,
        "expires_at": now + timedelta(hours=settings.upload_session_ttl_hours),
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


async def mark_delivered(sid: str, fids: list[str]) -> dict | None:
    """Đánh dấu các file MÁY TÍNH ĐÃ LẤY ĐƯỢC (extension gọi sau khi kéo bytes xong).

    Điện thoại chỉ biết "server nhận HTTP 200" — chưa chắc máy tính đã có. Không có mốc này thì
    trang mobile báo "đã gửi" trong khi cán bộ vẫn chưa thấy gì, đúng tình huống đã gặp ở
    Chứng thực bản sao. $addToSet để gọi lại nhiều lần không cộng trùng.
    """
    if not sid or not fids:
        return await get(sid) if sid else None
    return await get_db().upload_sessions.find_one_and_update(
        {"_id": sid},
        {"$addToSet": {"delivered_fids": {"$each": list(fids)}}, "$set": {"updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )


def delivered_count(sess: dict) -> int:
    """Số file đã tới máy tính. Chỉ đếm fid CÒN trong phiên (file bị xoá không tính)."""
    alive = {str(f.get("fid")) for f in (sess.get("files") or [])}
    return len(alive & {str(x) for x in (sess.get("delivered_fids") or [])})


def total_file_bytes(sess: dict) -> int:
    """Tổng byte đã được chốt vào phiên; metadata cũ thiếu size được tính là 0."""
    return sum(max(0, int(item.get("size") or 0)) for item in sess.get("files", []))


async def append_files_with_limit(
    sid: str,
    metas: list[dict],
    max_total_bytes: int,
) -> dict | None:
    """Thêm metadata nguyên tử khi tổng file sau cập nhật không vượt quota.

    Điều kiện ``$expr`` được Mongo kiểm tra cùng thao tác ``$push`` nên hai request upload
    đồng thời không thể cùng vượt qua dựa trên một snapshot tổng dung lượng đã cũ.
    """
    if not sid or not metas:
        return await get(sid)
    incoming = sum(max(0, int(item.get("size") or 0)) for item in metas)
    existing_total = {
        "$sum": {
            "$map": {
                "input": {"$ifNull": ["$files", []]},
                "as": "file",
                "in": {"$ifNull": ["$$file.size", 0]},
            }
        }
    }
    return await get_db().upload_sessions.find_one_and_update(
        {
            "_id": sid,
            "complete": {"$ne": True},
            "$expr": {"$lte": [{"$add": [existing_total, incoming]}, max_total_bytes]},
        },
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


async def reopen_for_supplement(sid: str) -> dict | None:
    """Mở lại phiên đã chốt để thêm/xóa tệp; chỉ chốt lại khi người dùng bấm hoàn tất."""
    if not sid:
        return None
    return await get_db().upload_sessions.find_one_and_update(
        {"_id": sid},
        {"$set": {
            "complete": False,
            "manual_complete_only": True,
            "updated_at": _now(),
        }},
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


def new_staged_file_path(sid: str) -> Path:
    """Đường dẫn file tạm chưa xuất hiện trong metadata phiên."""
    return _dir(sid) / f".upload-{secrets.token_hex(8)}.tmp"


def commit_staged_file(sid: str, staged_path: Path, fid: str) -> None:
    """Đổi tên nguyên tử trong cùng thư mục sau khi OCR/phân loại hoàn tất."""
    staged_path.replace(_dir(sid) / fid)


def delete_staged_file(staged_path: Path) -> None:
    if staged_path.exists():
        staged_path.unlink()


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
    updated_at = sess.get("updated_at")
    # `revision` giúp mobile loại phản hồi GET cũ về muộn sau một lần upload/delete mới.
    # Dùng microsecond epoch (vẫn nằm trong Number.MAX_SAFE_INTEGER của JavaScript) để cả
    # thao tác thêm và xoá file đều được phép thay đổi số lượng theo đúng thứ tự server.
    revision = int(updated_at.timestamp() * 1_000_000) if isinstance(updated_at, datetime) else 0
    return {"docs": docs, "received": received, "total": total, "unknown": unknown,
            "files_count": len(sess["files"]), "revision": revision,
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
