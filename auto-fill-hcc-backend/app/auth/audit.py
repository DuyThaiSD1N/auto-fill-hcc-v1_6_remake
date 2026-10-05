"""Nhật ký đăng nhập / làm mới token — để biết ai bị đá ra màn đăng nhập và VÌ SAO.

Trước đây prod không có log nào về auth: cán bộ kêu "tự đăng xuất" thì không phân biệt được
refresh token bị thu hồi, tranh chấp xoay vòng, gọi nhầm sang server khác hay do extension tự xoá.
Ghi không chặn luồng đăng nhập (lỗi ghi thì bỏ qua). Giữ 30 ngày (TTL theo `at`).
"""
from datetime import datetime, timezone

TTL_SECONDS = 30 * 24 * 3600


async def log_auth(db, event: str, *, user_id: str | None = None, username: str | None = None,
                   reason: str | None = None, device_info: str | None = None,
                   ip: str | None = None) -> None:
    doc = {"at": datetime.now(timezone.utc), "event": event}
    for key, value in (("user_id", user_id), ("username", username), ("reason", reason),
                       ("device_info", device_info), ("ip", ip)):
        if value:
            doc[key] = value
    try:
        await db.auth_events.insert_one(doc)
    except Exception:  # noqa: BLE001 — nhật ký không được làm hỏng đăng nhập
        return
