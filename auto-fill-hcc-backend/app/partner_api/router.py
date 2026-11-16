"""API thống kê cho đối tác: cùng số liệu với web thống kê, xác thực bằng API key.

Mọi số đều đi qua CHÍNH hàm của bảng thống kê (app/dashboard/router.py) nên cùng bộ lọc thì khớp
màn hình. Riêng /daily (hồ sơ mỗi ngày của TỪNG đơn vị) web chưa có: cộng số Auto Fill và Handfree
theo tài khoản-ngày từ cùng hàm đếm (app/stats/cutover.py, đã gộp tổ dân phố vào xã cha).
"""
import logging
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.errors import AppError
from app.dashboard import router as dashboard
from app.dashboard.scope import narrow_to_province, province_options, resolve_dashboard_scope
from app.partner_api.keys import require_stats_key, scope_user
from app.reports.integration import province_name
from app.stats import cutover

router = APIRouter()
logger = logging.getLogger(__name__)

_DAILY_MAX_DAYS = 92
_DATE = "Ngày dạng YYYY-MM-DD theo lịch Việt Nam (bao gồm ngày này). Bỏ trống = không giới hạn."
_UNIT = "Một hoặc nhiều unitId (lấy ở /units), cách nhau dấu phẩy. Bỏ trống = mọi đơn vị."
_PROVINCE = "Tên tỉnh như trong /units (vd \"Tỉnh Lâm Đồng\"). Bỏ trống = mọi tỉnh."


def _user(key: dict) -> dict:
    logger.info("Partner API: key=%s", key.get("name"))
    return scope_user(key)


def _unit(u: dict) -> dict:
    return {"unitId": u["unitId"], "name": u.get("name"), "ward": u.get("xa"), "province": province_name(u.get("tinh")) or None}


@router.get("/units", summary="Danh sách tỉnh, đơn vị (phường/xã, HCC tỉnh)")
async def units(key: dict = Depends(require_stats_key), province: str | None = Query(None, description=_PROVINCE)):
    full = await resolve_dashboard_scope(_user(key))
    scoped = narrow_to_province(full, province)
    return {
        "provinces": province_options(full["units"]),
        "units": [_unit(u) for u in scoped["units"]],
    }


@router.get("/stats", summary="Tổng quan + theo đơn vị + theo thủ tục + theo ngày")
async def stats(
    key: dict = Depends(require_stats_key),
    dateFrom: str | None = Query(None, description=_DATE),
    dateTo: str | None = Query(None, description=_DATE),
    province: str | None = Query(None, description=_PROVINCE),
    unit: str | None = Query(None, description=_UNIT),
):
    """`kpis` và `byProcedure`, `byDay` tính trên đơn vị đang lọc; `units` luôn đủ mọi đơn vị trong
    phạm vi tỉnh đang lọc (giống mục Theo đơn vị của web)."""
    data = await dashboard.summary(user=_user(key), dateFrom=dateFrom, dateTo=dateTo, unit=unit, province=province)
    return {
        "range": data["range"],
        "selectedUnits": [_unit(u) for u in data.get("selectedUnits") or []],
        "sources": data["sources"],
        "counting": data.get("counting"),
        "kpis": {k: v for k, v in data["kpis"].items() if k != "requests"},
        "byProcedure": data["byProcedure"],
        "byDay": data["byDay"],
        "units": [
            {**_unit(u), "dossiers": u["dossiers"], "procedureTypes": u["procedureTypes"], "topProcedure": u["topProcedure"]}
            for u in data["units"]
        ],
    }


@router.get("/daily", summary="Số hồ sơ mỗi ngày của từng đơn vị")
async def daily(
    key: dict = Depends(require_stats_key),
    dateFrom: str = Query(..., description="Ngày đầu, YYYY-MM-DD."),
    dateTo: str = Query(..., description=f"Ngày cuối, YYYY-MM-DD. Tối đa {_DAILY_MAX_DAYS} ngày tính cả hai đầu."),
    province: str | None = Query(None, description=_PROVINCE),
    unit: str | None = Query(None, description=_UNIT),
):
    """Mỗi đơn vị một dòng (kể cả đơn vị 0 hồ sơ), `days` chỉ liệt kê ngày có hồ sơ.
    Cộng mọi đơn vị trong một ngày = `byDay` của /stats với cùng bộ lọc."""
    resolved = narrow_to_province(await resolve_dashboard_scope(_user(key)), province)
    date_from, date_to = dashboard._range(dateFrom, dateTo)
    if date_to - date_from > timedelta(days=_DAILY_MAX_DAYS):
        raise AppError("RANGE_TOO_LONG", f"Khoảng ngày tối đa {_DAILY_MAX_DAYS} ngày.", 400)
    ids, chosen = dashboard._resolve_user_ids(resolved, unit)
    sel_units = chosen or resolved["units"]

    per_unit: dict[str, dict[str, int]] = {u["unitId"]: {} for u in sel_units}
    for experience in ("autofill", "handfree") if ids else ():
        for row in await cutover.daily_dossier_counts(
            user_ids=ids, date_from=date_from, date_to=date_to, experience=experience,
        ):
            bucket = per_unit.get(str(row["userId"]))
            if bucket is not None:
                bucket[row["date"]] = bucket.get(row["date"], 0) + int(row["count"])

    rows = []
    for u in sel_units:
        days = per_unit[u["unitId"]]
        rows.append({
            **_unit(u),
            "total": sum(days.values()),
            "days": [{"date": d, "count": days[d]} for d in sorted(days) if days[d]],
        })
    rows.sort(key=lambda r: (-r["total"], r["province"] or "", r["ward"] or r["name"] or ""))
    return {
        "range": {"from": dateFrom, "to": dateTo},
        "units": rows,
    }


@router.get("/ratings", summary="Đánh giá công dân")
async def ratings(
    key: dict = Depends(require_stats_key),
    dateFrom: str | None = Query(None, description=_DATE),
    dateTo: str | None = Query(None, description=_DATE),
    province: str | None = Query(None, description=_PROVINCE),
    unit: str | None = Query(None, description=_UNIT),
):
    """Phiếu đánh giá trên hồ sơ đã nộp. Phần tổng theo đơn vị đang lọc; `units` gồm các đơn vị có hồ sơ đã nộp."""
    user = _user(key)
    data = await dashboard.ratings(user=user, dateFrom=dateFrom, dateTo=dateTo, unit=unit, province=province)
    # Dòng đánh giá theo đơn vị không kèm tỉnh → tra lại từ phạm vi.
    by_id = {u["unitId"]: u for u in (await resolve_dashboard_scope(user))["units"]}
    body = {k: v for k, v in data.items() if k not in ("scope", "selected", "selectedUnits", "units")}
    body["units"] = [
        {**_unit({**by_id.get(u["unitId"], {}), **u}), **{k: v for k, v in u.items() if k not in ("unitId", "name", "xa")}}
        for u in data["units"]
    ]
    return body


@router.get("/dossiers", summary="Nhật ký hồ sơ")
async def dossiers(
    key: dict = Depends(require_stats_key),
    dateFrom: str | None = Query(None, description=_DATE),
    dateTo: str | None = Query(None, description=_DATE),
    province: str | None = Query(None, description=_PROVINCE),
    unit: str | None = Query(None, description=_UNIT),
    status: Literal["all", "submitted", "unsubmitted"] = Query("all", description="submitted = đã bấm nộp."),
    source: Literal["all", "autofill", "handfree"] = Query("all"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100),
):
    """Mỗi hồ sơ một dòng, mới nhất trước. Không có thông tin cá nhân (tên, CCCD, giấy tờ)."""
    data = await dashboard.logs(
        user=_user(key), dateFrom=dateFrom, dateTo=dateTo, unit=unit, province=province,
        status=status, source=source, page=page, pageSize=pageSize,
    )
    return {k: v for k, v in data.items() if k != "scope"}
