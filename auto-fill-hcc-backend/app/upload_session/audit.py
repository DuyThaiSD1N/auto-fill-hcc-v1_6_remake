"""Nhật ký MỘT phiên tải ảnh qua QR: mở phiên — điện thoại gửi — máy tính lấy.

Vì sao cần: ca "điện thoại báo đã gửi 3 tệp mà máy tính không thấy gì" KHÔNG chẩn đoán được,
vì giữa hai mốc đó hệ thống không ghi lại gì. Có collection này thì tra một phiên là biết ngay
đứt ở khâu nào: gửi lên không được, hay lên rồi mà máy tính không kéo về.

Vì sao KHÔNG ghi vào `upload_sessions`: collection đó có TTL (Auto Fill 30 phút, Handfree 24h)
— đúng lúc cần điều tra thì bản ghi đã bị xoá. Ở đây KHÔNG đặt TTL.

Vì sao KHÔNG dùng `audit_logs`: bảng đó theo từng request /process (procedure, độ trễ OCR/LLM),
không có khái niệm phiên.

Mốc "máy tính đã lấy" lấy từ chính request GET /files/{fid} — không cần extension báo thêm, nên
bản extension đang phát hành cũng được ghi nhận đầy đủ.

Mọi hàm best-effort: ghi nhật ký hỏng KHÔNG được làm hỏng việc gửi/nhận của công dân.
"""
from datetime import datetime, timezone

from app.db.mongo import get_db

# Trần số sự kiện giữ lại mỗi phiên. Một phiên bình thường có dưới 20 sự kiện; đặt trần để
# phiên bị bấm loạn không làm phình document.
_MAX_EVENTS = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _push(
    sid: str,
    event: dict,
    *,
    inc: dict | None = None,
    init: dict | None = None,
    fields: dict | None = None,
) -> None:
    """Một sự kiện = MỘT lệnh ghi. Tách làm hai lệnh thì lệnh sau phải upsert=False, và nếu
    document chưa kịp tạo (log_opened hỏng, phiên từ bản BE cũ) thì received/delivered mất trắng.
    """
    if not sid:
        return
    update: dict = {
        "$setOnInsert": {"created_at": _now(), **(init or {})},
        "$set": {"updated_at": _now(), **(fields or {})},
        "$push": {"events": {"$each": [{"at": _now(), **event}], "$slice": -_MAX_EVENTS}},
    }
    if inc:
        update["$inc"] = inc
    try:
        await get_db().upload_session_logs.update_one({"_id": sid}, update, upsert=True)
    except Exception:  # noqa: BLE001 — nhật ký không được chặn luồng
        return


async def log_opened(sid: str, *, user_id: str, username: str | None, experience: str) -> None:
    """Cán bộ bấm tạo mã QR."""
    await _push(
        sid,
        {"kind": "open"},
        init={"user_id": user_id, "username": username, "experience": experience,
              "received": 0, "delivered": 0, "bytes_in": 0},
    )


async def log_uploaded(sid: str, *, names: list[str], nbytes: int, received: int) -> None:
    """Điện thoại gửi xong một lô."""
    await _push(
        sid,
        {"kind": "upload", "count": len(names), "names": names[:20], "bytes": int(nbytes)},
        inc={"bytes_in": int(nbytes)},
        fields={"received": int(received)},
    )


async def log_delivered(sid: str, *, name: str, nbytes: int, delivered: int, received: int) -> None:
    """Máy tính kéo được một tệp về (quan sát từ GET /files/{fid})."""
    await _push(
        sid,
        {"kind": "deliver", "name": name, "bytes": int(nbytes)},
        fields={"delivered": int(delivered), "received": int(received)},
    )


async def log_missing(sid: str, *, fid: str) -> None:
    """Máy tính đòi một tệp không còn trong phiên — dấu hiệu phiên hết hạn hoặc sai server."""
    await _push(sid, {"kind": "missing", "fid": fid})
