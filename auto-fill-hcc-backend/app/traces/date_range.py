"""Chuẩn hóa khoảng ngày báo cáo/thống kê theo múi giờ Việt Nam."""
import re
from datetime import date, datetime, time, timedelta, timezone

from app.core.errors import AppError


VIETNAM_TZ = timezone(timedelta(hours=7))
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_stats_bound(value: str | None, *, end: bool) -> datetime | None:
    if not value:
        return None
    if _DATE_ONLY_RE.fullmatch(value):
        try:
            day = date.fromisoformat(value)
        except ValueError as exc:
            raise AppError("BAD_DATE", f"Ngày không hợp lệ: {value}", 400) from exc
        if end:
            day += timedelta(days=1)
        return datetime.combine(day, time.min, tzinfo=VIETNAM_TZ).astimezone(timezone.utc)

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError("BAD_DATE", f"Thời gian không hợp lệ: {value}", 400) from exc
    # FE cũ có thể gửi datetime không timezone; màn báo cáo theo ngày làm việc Việt Nam.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=VIETNAM_TZ)
    return parsed.astimezone(timezone.utc)


def parse_stats_range(
    date_from: str | None,
    date_to: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Trả khoảng nửa mở [đầu ngày đầu, đầu ngày kế tiếp sau ngày cuối)."""
    start = parse_stats_bound(date_from, end=False)
    end = parse_stats_bound(date_to, end=True)
    if start and end and start >= end:
        raise AppError("BAD_DATE_RANGE", "Từ ngày phải nhỏ hơn hoặc bằng đến ngày.", 400)
    return start, end
