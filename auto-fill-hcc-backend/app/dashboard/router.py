"""API bảng thống kê PHƯỜNG (self-service cho cán bộ phường).

Khác trang quản trị (/traces, /reports — require_admin, xem PII/OCR mọi phường), API này
chỉ trả SỐ LIỆU TỔNG HỢP và LUÔN khóa phạm vi vào chính tài khoản đăng nhập: dashboard đếm
đúng trace có user_id = user trong token. Không nhận xã/userId từ client nên không thể mở
rộng sang phường khác. Tái dùng repo.stats_by_user_ids (cùng cách đếm "hồ sơ riêng biệt"
như trang quản trị) + daily_counts_by_user_ids cho biểu đồ theo ngày.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_ward
from app.traces import repo
from app.traces.date_range import parse_stats_range

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# Mốc "từ đầu" khi người dùng chọn "Tất cả" (không truyền ngày).
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@router.get("/summary")
async def summary(
    user: dict = Depends(require_ward),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
):
    start, end = parse_stats_range(dateFrom, dateTo)
    date_from = start or _EPOCH
    date_to = end or (datetime.now(timezone.utc) + timedelta(days=1))

    # Phạm vi = CHÍNH tài khoản đang đăng nhập (mỗi phường một tài khoản).
    ids = [str(user["id"])]
    stats = await repo.stats_by_user_ids(user_ids=ids, date_from=date_from, date_to=date_to)
    by_day = await repo.daily_counts_by_user_ids(user_ids=ids, date_from=date_from, date_to=date_to)

    procedures = stats.get("procedures") or []
    top = procedures[0] if procedures else None
    return {
        "ward": {
            "name": user.get("name") or user.get("username"),
            "xa": user.get("xa"),
            "tinh": user.get("tinh"),
        },
        "range": {"from": dateFrom, "to": dateTo},
        "kpis": {
            "dossiers": stats.get("totalDossiers", 0),
            "requests": stats.get("totalRequests", 0),
            "procedureTypes": len(procedures),
            "topProcedure": {"label": top["label"], "count": top["count"]} if top else None,
        },
        "byProcedure": procedures,
        "byDay": by_day,
    }
