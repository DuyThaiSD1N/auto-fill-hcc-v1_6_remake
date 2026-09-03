"""Gộp số liệu Auto Fill + Handfree từ hai nguồn trong cùng MongoDB.

Hai nguồn vẫn khớp theo đơn vị và thủ tục giống báo cáo Excel. Truy vấn Handfree là
best-effort để một lỗi aggregation phụ không làm vỡ phần Auto Fill của dashboard.
"""
import logging
from datetime import datetime, timedelta

from app.procedures.registry import PROCEDURES
from app.reports.handfree_client import fetch_handfree_daily_stats, fetch_handfree_stats
from app.reports.integration import canonical_procedure_id
from app.reports.schemas import ExcelExportRequest
from app.traces.date_range import VIETNAM_TZ

logger = logging.getLogger(__name__)
_REGISTRY = {p["key"]: p for p in PROCEDURES}
# Giới hạn khoảng biểu đồ để response không quá dày; truy vấn Handfree hiện là một aggregation.
_HF_DAILY_MAX_DAYS = 92


def _af_canon(item: dict) -> tuple[str, str]:
    key = item.get("key") or "—"
    entry = _REGISTRY.get(key)
    return canonical_procedure_id(key, entry), (entry or {}).get("label") or item.get("label") or key


def _hf_canon(item: dict) -> tuple[str, str]:
    key = str(item.get("procedureKey") or "").strip() or "—"
    entry = _REGISTRY.get(key)
    cid = str(item.get("canonicalProcedureId") or "").strip() or canonical_procedure_id(key, entry)
    return cid, (entry or {}).get("label") or item.get("label") or key


def merge_procedures(af_procs: list[dict] | None, hf_procs: list[dict] | None) -> list[dict]:
    """Gộp danh sách thủ tục AF + HF theo canonical id → [{key, label, count}] (count = tổng 2 hệ)."""
    rows: dict[str, dict] = {}
    for item in af_procs or []:
        count = int(item.get("count") or 0)
        if count <= 0:
            continue
        cid, label = _af_canon(item)
        rows.setdefault(cid, {"key": cid, "label": label, "count": 0})["count"] += count
    for item in hf_procs or []:
        count = int(item.get("count") or 0)
        if count <= 0:
            continue
        cid, label = _hf_canon(item)
        rows.setdefault(cid, {"key": cid, "label": label, "count": 0})["count"] += count
    ordered = sorted(rows.values(), key=lambda row: (-row["count"], row["label"]))
    return ordered


def _hf_body(date_from: datetime, date_to: datetime) -> ExcelExportRequest:
    # fetch_handfree_* chỉ đọc dateFrom/dateTo; các field còn lại chỉ để qua validator.
    # Khoảng vào là [date_from, date_to) theo UTC nhưng ĐÃ ứng với ngày lịch VIỆT NAM. Lớp báo cáo
    # nhận dateFrom/dateTo là ngày lịch (bao gồm cả hai đầu) → phải quy về giờ VN và lùi mốc cuối
    # 1 micro giây, nếu không "Hôm nay" (nửa mở sang 00:00 ngày kế) sẽ bị đếm thành 2 ngày.
    d_from = date_from.astimezone(VIETNAM_TZ).strftime("%Y-%m-%d")
    d_to = (date_to - timedelta(microseconds=1)).astimezone(VIETNAM_TZ).strftime("%Y-%m-%d")
    return ExcelExportRequest(
        dateFrom=d_from,
        dateTo=d_to,
        selectionMode="province",
        province="dashboard",
    )


async def fetch_handfree(
    units: list[dict],
    date_from: datetime,
    date_to: datetime,
    *,
    want_daily: bool,
) -> tuple[dict[str, dict], dict[str, int], bool]:
    """Lấy số liệu Handfree cho tập đơn vị. Trả (units_by_key, daily_by_date, ok)."""
    accounts = [
        {"_id": u.get("unitId"), "tinh": u.get("tinh"), "xa": u.get("xa")}
        for u in units
        if u.get("unitId") and u.get("xa")
    ]
    if not accounts:
        # Không có đơn vị nào ghép được (không có xã) — không phải lỗi, chỉ là không có phần Handfree.
        return {}, {}, True

    body = _hf_body(date_from, date_to)
    units_by_key: dict[str, dict] = {}
    daily_by_date: dict[str, int] = {}
    ok = True
    try:
        stats = await fetch_handfree_stats(accounts, body)
        for unit in stats.get("units") or []:
            key = str(unit.get("unitKey") or "").strip()
            if key:
                units_by_key[key] = unit
    except Exception as exc:  # noqa: BLE001 - Handfree lỗi/không cấu hình KHÔNG được làm vỡ dashboard
        ok = False
        logger.warning("Handfree stats không khả dụng cho dashboard: %s", exc)

    if want_daily and ok and (date_to - date_from).days <= _HF_DAILY_MAX_DAYS:
        try:
            daily = await fetch_handfree_daily_stats(accounts, body)
            for unit in daily.get("units") or []:
                for row in unit.get("dailyCounts") or []:
                    day = str(row.get("date") or "")
                    if day:
                        daily_by_date[day] = daily_by_date.get(day, 0) + int(row.get("count") or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Handfree daily không khả dụng cho dashboard: %s", exc)

    return units_by_key, daily_by_date, ok


async def fetch_handfree_daily(units: list[dict], date_from: datetime, date_to: datetime) -> dict[str, int]:
    """Chỉ lấy Handfree theo ngày cho một tập đơn vị (dùng khi đã lọc 1 đơn vị cụ thể)."""
    accounts = [
        {"_id": u.get("unitId"), "tinh": u.get("tinh"), "xa": u.get("xa")}
        for u in units
        if u.get("unitId") and u.get("xa")
    ]
    if not accounts or (date_to - date_from).days > _HF_DAILY_MAX_DAYS:
        return {}
    daily_by_date: dict[str, int] = {}
    try:
        daily = await fetch_handfree_daily_stats(accounts, _hf_body(date_from, date_to))
        for unit in daily.get("units") or []:
            for row in unit.get("dailyCounts") or []:
                day = str(row.get("date") or "")
                if day:
                    daily_by_date[day] = daily_by_date.get(day, 0) + int(row.get("count") or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Handfree daily không khả dụng cho dashboard: %s", exc)
    return daily_by_date


def merge_daily(af_daily: list[dict], hf_daily_by_date: dict[str, int]) -> list[dict]:
    """Gộp lượt/hồ sơ theo ngày của hai hệ, theo mốc ngày (YYYY-MM-DD)."""
    by_date: dict[str, int] = {}
    for row in af_daily or []:
        day = str(row.get("date") or "")
        if day:
            by_date[day] = by_date.get(day, 0) + int(row.get("count") or 0)
    for day, count in hf_daily_by_date.items():
        by_date[day] = by_date.get(day, 0) + int(count or 0)
    return [{"date": day, "count": by_date[day]} for day in sorted(by_date)]
