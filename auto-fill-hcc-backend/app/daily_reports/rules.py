"""Quy tắc thuần của báo cáo hằng ngày (quyền, ngày báo cáo, kiểm số liệu, trường trả về) — không chạm DB."""
import re
from datetime import date, datetime, timedelta, timezone

from app.core.errors import AppError

# Ba vai trò, phân giải từ token qua phạm vi thống kê (app/dashboard/scope.py), cùng cách với báo lỗi:
#   reporter : HCC xã/phường, HCC tỉnh (tài khoản đơn vị) — viết báo cáo hôm nay, xem báo cáo của CHÍNH mình;
#   viewer   : tài khoản Tỉnh xem thống kê — xem báo cáo các đơn vị trong tỉnh;
#   manager  : admin — xem mọi báo cáo.
REPORTER, VIEWER, MANAGER = "reporter", "viewer", "manager"

MAX_COUNT = 999_999
MAX_TEXT = 2000
_VN_TZ = timezone(timedelta(hours=7))
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def access_of(user: dict, scope: dict) -> str:
    if (user.get("role") or "user") == "admin":
        return MANAGER
    if scope.get("scopeKind") == "unit":
        return REPORTER
    return VIEWER


def today_vn(now: datetime | None = None) -> str:
    """Ngày báo cáo theo lịch Việt Nam — hệ thống tự nhận, cán bộ không chọn ngày."""
    return (now or datetime.now(timezone.utc)).astimezone(_VN_TZ).date().isoformat()


def parse_day(value: str | None, field: str) -> str | None:
    """'YYYY-MM-DD' hợp lệ hoặc None; sai định dạng → 400 (lọc chuỗi so sánh trực tiếp với `date`)."""
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if not _DAY.match(raw):
            raise ValueError
        date.fromisoformat(raw)
    except ValueError:
        raise AppError("BAD_DATE", f"{field} phải có dạng YYYY-MM-DD.", 400)
    return raw


def clean_count(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_COUNT:
        raise AppError("DAILY_REPORT_BAD_COUNT", f"{label} phải là số nguyên từ 0 đến {MAX_COUNT:,}.".replace(",", "."), 400)
    return value


def clean_text(value: str | None) -> str:
    text = (value or "").strip()
    if len(text) > MAX_TEXT:
        raise AppError("DAILY_REPORT_TEXT_TOO_LONG", f"Mỗi ô ghi chú tối đa {MAX_TEXT} ký tự.", 400)
    return text


def iso(value):
    # Motor trả datetime không kèm múi giờ; giá trị lưu luôn là UTC.
    if not value:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def serialize(doc: dict, access: str, today: str) -> dict:
    return {
        "id": str(doc["_id"]),
        "date": doc.get("date"),
        "unitId": doc.get("unit_id"),
        "unitName": doc.get("unit_name"),
        "province": doc.get("province"),
        "reporterName": doc.get("reporter_name"),
        "assistantCount": int(doc.get("assistant_count") or 0),
        "actualCount": int(doc.get("actual_count") or 0),
        "advantages": doc.get("advantages") or "",
        "difficulties": doc.get("difficulties") or "",
        "createdAt": iso(doc.get("created_at")),
        "updatedAt": iso(doc.get("updated_at")) if doc.get("updated_at") != doc.get("created_at") else None,
        # Chỉ được sửa trong ngày báo cáo, bởi chính đơn vị gửi; qua ngày thì khoá.
        "editable": access == REPORTER and doc.get("date") == today,
    }
