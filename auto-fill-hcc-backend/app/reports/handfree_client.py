"""Đọc thống kê Handfree ngay trong Mongo dùng chung.

Tên module được giữ để không làm vỡ các import của lớp xuất Excel. Đây không còn là
HTTP client: Auto Fill và Handfree là hai ``experience`` trên cùng một backend/DB.
"""
from typing import Literal

from app.core.errors import AppError
from app.procedures.registry import PROCEDURES
from app.reports.integration import canonical_procedure_id, province_name, unit_key
from app.reports.procedure_meta import cap_thu_tuc, ma_thu_tuc, pham_vi_ho_tro
from app.reports.schemas import ExcelExportRequest
from app.stats import cutover
from app.traces import repo as traces_repo
from app.traces.date_range import parse_stats_range


def _units(accounts: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Chuẩn hóa đơn vị và ánh xạ user_id trong DB chung sang khóa dòng Excel."""
    units: dict[str, dict] = {}
    user_to_unit: dict[str, str] = {}
    for account in accounts:
        province = province_name(account.get("tinh"))
        ward = str(account.get("xa") or "").strip()
        if not province or not ward:
            # Tài khoản cấp tỉnh/legacy vẫn được xuất ở phần Auto Fill. Không có đủ
            # tỉnh + xã thì không thể ghép an toàn vào một dòng Handfree cấp xã.
            continue
        key = unit_key(province, ward)
        units.setdefault(key, {"unitKey": key, "province": province, "ward": ward})
        user_to_unit[str(account["_id"])] = key
    return list(units.values()), user_to_unit


def _procedure_rows(stats: dict, user_to_unit: dict[str, str]) -> dict[str, list[dict]]:
    registry = {item["key"]: item for item in PROCEDURES}
    counts: dict[str, dict[str, dict]] = {
        key: {} for key in set(user_to_unit.values())
    }
    for ward in stats.get("wards") or []:
        key = user_to_unit.get(str(ward.get("userId") or ""))
        if not key:
            continue
        for procedure in ward.get("procedures") or []:
            procedure_key = str(procedure.get("key") or "").strip()
            if not procedure_key:
                continue
            entry = registry.get(procedure_key)
            canonical_id = canonical_procedure_id(procedure_key, entry)
            bucket = counts[key].setdefault(canonical_id, {
                "canonicalProcedureId": canonical_id,
                "procedureKey": procedure_key,
                "procedureCode": None,
                "label": (entry or {}).get("label") or procedure.get("label") or procedure_key,
                "level": cap_thu_tuc(procedure_key),
                "supportScope": pham_vi_ho_tro(entry, procedure_key),
                "count": 0,
            })
            code = ma_thu_tuc(entry)
            bucket["procedureCode"] = code if code != "—" else None
            bucket["count"] += int(procedure.get("count") or 0)
    return {
        key: sorted(rows.values(), key=lambda item: (-item["count"], item["label"]))
        for key, rows in counts.items()
    }


async def fetch_handfree_stats(accounts: list[dict], body: ExcelExportRequest) -> dict:
    units, user_to_unit = _units(accounts)
    if not units:
        return {"source": "handfree", "units": []}
    date_from, date_to = parse_stats_range(body.dateFrom, body.dateTo)
    if not date_from or not date_to:
        raise AppError("REPORT_DATE_REQUIRED", "Vui lòng nhập đầy đủ từ ngày và đến ngày.", 400)
    stats = await cutover.dossier_stats(
        user_ids=list(user_to_unit),
        date_from=date_from,
        date_to=date_to,
        experience="handfree",
    )
    procedures_by_unit = _procedure_rows(stats, user_to_unit)
    return {
        "source": "handfree",
        "units": [
            {
                **unit,
                "matchedAccountCount": sum(
                    1 for key in user_to_unit.values() if key == unit["unitKey"]
                ),
                "procedures": procedures_by_unit.get(unit["unitKey"], []),
            }
            for unit in units
        ],
    }


async def fetch_handfree_daily_stats(
    accounts: list[dict],
    body: ExcelExportRequest,
) -> dict:
    """Lấy toàn khoảng ngày bằng một aggregation local, không gọi HTTP theo từng ngày."""
    units, user_to_unit = _units(accounts)
    if not units:
        return {"source": "handfree", "units": []}
    date_from, date_to = parse_stats_range(body.dateFrom, body.dateTo)
    if not date_from or not date_to:
        raise AppError("REPORT_DATE_REQUIRED", "Vui lòng nhập đầy đủ từ ngày và đến ngày.", 400)
    rows = await cutover.daily_dossier_counts(
        user_ids=list(user_to_unit),
        date_from=date_from,
        date_to=date_to,
        experience="handfree",
    )
    daily_by_unit: dict[str, dict[str, int]] = {
        unit["unitKey"]: {} for unit in units
    }
    for row in rows:
        key = user_to_unit.get(str(row.get("userId") or ""))
        day = str(row.get("date") or "")
        if not key or not day:
            continue
        daily = daily_by_unit[key]
        daily[day] = daily.get(day, 0) + int(row.get("count") or 0)
    return {
        "source": "handfree",
        "units": [
            {
                **unit,
                "dailyCounts": [
                    {"date": day, "count": count}
                    for day, count in sorted(daily_by_unit[unit["unitKey"]].items())
                ],
            }
            for unit in units
        ],
    }


async def fetch_handfree_dashboard_stats(
    *,
    scope: Literal["all", "official"],
    date_from: str | None,
    date_to: str | None,
) -> dict:
    parsed_from, parsed_to = parse_stats_range(date_from, date_to)
    return await traces_repo.stats(
        date_from=parsed_from,
        date_to=parsed_to,
        scope=scope,
        experience="handfree",
    )
