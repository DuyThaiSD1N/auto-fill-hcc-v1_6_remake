"""API bảng thống kê (self-service HCC xã/tỉnh + báo cáo cấp Tỉnh).

Chỉ trả SỐ LIỆU TỔNG HỢP (không PII/OCR). Phạm vi LUÔN khóa theo token qua app/dashboard/scope.py:
HCC xã/tỉnh xem chính mình (1 đơn vị); tài khoản Tỉnh (province_admin) xem mọi HCC xã/tỉnh cùng
tỉnh; admin xem toàn hệ thống. Endpoint KHÔNG nhận tỉnh/xã/userId tùy ý từ client — tham số `unit`
chỉ được chấp nhận nếu nằm trong phạm vi đã phân giải.

Số liệu = TỔNG hai hệ Auto Fill + Handfree (Handfree best-effort, xem app/dashboard/combine.py).
`/summary` trả luôn `units[]` (bảng Theo đơn vị) để mỗi lần tải chỉ gọi Handfree một lần.
"""
import io
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.deps import require_dashboard
from app.core.errors import AppError
from app.dashboard.combine import (
    fetch_handfree,
    fetch_handfree_daily,
    merge_daily,
    merge_procedures,
)
from app.dashboard.export import build_dashboard_workbook, export_filename
from app.dashboard.scope import resolve_dashboard_scope
from app.reports.integration import unit_key
from app.traces import repo
from app.traces.date_range import parse_stats_range

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_EXPORT_LOG_CAP = 5000  # số dòng nhật ký tối đa đưa vào file Excel


def _scope_summary(scope: dict) -> dict:
    return {
        "role": scope["role"],
        "scopeKind": scope["scopeKind"],
        "province": scope["province"],
        "canViewUnits": scope["canViewUnits"],
        "unitCount": len(scope["units"]),
        "self": scope["self"],
    }


def _range(dateFrom: str | None, dateTo: str | None) -> tuple[datetime, datetime]:
    start, end = parse_stats_range(dateFrom, dateTo)
    date_from = start or _EPOCH
    date_to = end or (datetime.now(timezone.utc) + timedelta(days=1))
    return date_from, date_to


def _resolve_user_ids(scope: dict, unit: str | None) -> tuple[list[str], dict | None]:
    units = scope["units"]
    if unit and unit != "all":
        selected = next((u for u in units if u["unitId"] == unit), None)
        if not selected:
            raise AppError("UNIT_OUT_OF_SCOPE", "Đơn vị không thuộc phạm vi tài khoản.", 403)
        return [selected["unitId"]], selected
    return [u["unitId"] for u in units], None


@router.get("/scope")
async def scope(user: dict = Depends(require_dashboard)):
    """Phạm vi + danh sách đơn vị (dựng bộ chọn đơn vị). Không kèm số liệu → không gọi Handfree."""
    resolved = await resolve_dashboard_scope(user)
    return {**_scope_summary(resolved), "units": resolved["units"]}


@router.get("/summary")
async def summary(
    user: dict = Depends(require_dashboard),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    unit: str | None = Query(None),
):
    resolved = await resolve_dashboard_scope(user)
    date_from, date_to = _range(dateFrom, dateTo)
    all_units = resolved["units"]
    all_ids = [u["unitId"] for u in all_units]
    ids, selected = _resolve_user_ids(resolved, unit)
    sel_units = [selected] if selected else all_units

    # Auto Fill: MỘT aggregation cho toàn phạm vi → wards per-đơn-vị + procedures + total.
    af = (
        await repo.stats_by_user_ids(
            user_ids=all_ids,
            date_from=date_from,
            date_to=date_to,
            experience="autofill",
        )
        if all_ids else {"wards": [], "procedures": [], "totalDossiers": 0, "totalRequests": 0}
    )
    af_wards = {ward["userId"]: ward for ward in af.get("wards") or []}

    # Handfree: một lần gọi per-đơn-vị cho toàn phạm vi. Nếu KHÔNG lọc đơn vị thì lấy luôn theo ngày.
    hf_units_by_key, hf_daily_all, hf_ok = await fetch_handfree(
        all_units, date_from, date_to, want_daily=selected is None
    )

    def _hf_key(u: dict) -> str:
        return unit_key(u.get("tinh"), u.get("xa"))

    # Bảng Theo đơn vị: gộp AF + HF từng đơn vị (đơn vị 0 hồ sơ vẫn liệt kê).
    unit_rows: list[dict] = []
    units_by_proc: dict[str, int] = {}
    for u in all_units:
        af_procs = (af_wards.get(u["unitId"]) or {}).get("procedures") or []
        hf_procs = (hf_units_by_key.get(_hf_key(u)) or {}).get("procedures") or []
        procs = merge_procedures(af_procs, hf_procs)
        dossiers = sum(p["count"] for p in procs)
        top = procs[0] if procs else None
        for proc in procs:
            units_by_proc[proc["key"]] = units_by_proc.get(proc["key"], 0) + 1
        unit_rows.append({
            "unitId": u["unitId"],
            "name": u["name"],
            "xa": u.get("xa"),
            "tinh": u.get("tinh"),
            "role": u.get("role"),
            "dossiers": dossiers,
            "requests": int((af_wards.get(u["unitId"]) or {}).get("requests") or 0),
            "procedureTypes": len(procs),
            "topProcedure": {"label": top["label"], "count": top["count"]} if top else None,
        })
    unit_rows.sort(key=lambda r: (-r["dossiers"], (r["xa"] or ""), r["name"] or ""))

    # Phần đang chọn (KPIs + Theo thủ tục): 1 đơn vị → lấy từ ward tương ứng; toàn phạm vi → tổng.
    if selected:
        af_procs_sel = (af_wards.get(selected["unitId"]) or {}).get("procedures") or []
        af_requests = int((af_wards.get(selected["unitId"]) or {}).get("requests") or 0)
    else:
        af_procs_sel = af.get("procedures") or []
        af_requests = int(af.get("totalRequests") or 0)
    hf_procs_sel: list[dict] = []
    for u in sel_units:
        hf_unit = hf_units_by_key.get(_hf_key(u))
        if hf_unit:
            hf_procs_sel.extend(hf_unit.get("procedures") or [])

    by_procedure = merge_procedures(af_procs_sel, hf_procs_sel)
    total = sum(p["count"] for p in by_procedure)
    top = by_procedure[0] if by_procedure else None
    by_procedure = [{**p, "units": units_by_proc.get(p["key"], 0)} for p in by_procedure]

    # Biểu đồ theo ngày = hồ sơ/ngày Auto Fill + Handfree (chỉ gộp HF khi khoảng đủ ngắn).
    af_daily = (
        await repo.daily_dossier_counts_by_user_ids(
            user_ids=ids,
            date_from=date_from,
            date_to=date_to,
            experience="autofill",
        )
        if ids else []
    )
    hf_daily = hf_daily_all if selected is None else await fetch_handfree_daily(sel_units, date_from, date_to)
    by_day = merge_daily(af_daily, hf_daily)

    return {
        "scope": _scope_summary(resolved),
        "selected": selected,
        "range": {"from": dateFrom, "to": dateTo},
        "sources": {"autofill": True, "handfree": hf_ok},
        "kpis": {
            "dossiers": total,
            "requests": af_requests,
            "procedureTypes": len(by_procedure),
            "topProcedure": {"label": top["label"], "count": top["count"]} if top else None,
        },
        "byProcedure": by_procedure,
        "byDay": by_day,
        "units": unit_rows,
    }


@router.get("/logs")
async def logs(
    user: dict = Depends(require_dashboard),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    unit: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(15, ge=1, le=100),
):
    """Nhật ký hồ sơ (mỗi lượt làm việc với Trợ lý = 1 dòng). Auto Fill; KHÔNG PII, không thời lượng.

    Nhật ký này chủ đích chỉ gồm Auto Fill; màn quản lý trace có bộ lọc nguồn riêng.
    """
    resolved = await resolve_dashboard_scope(user)
    date_from, date_to = _range(dateFrom, dateTo)
    ids, _selected = _resolve_user_ids(resolved, unit)
    unit_by_id = {u["unitId"]: u for u in resolved["units"]}

    result = await repo.list_dossier_log(
        user_ids=ids, date_from=date_from, date_to=date_to,
        skip=(page - 1) * pageSize, limit=pageSize, experience="autofill",
    )
    items = []
    for row in result["items"]:
        unit_meta = unit_by_id.get(row["userId"]) or {}
        items.append({
            "requestId": row["requestId"],
            "receivedAt": row["createdAt"],
            "unitId": row["userId"],
            "unitName": unit_meta.get("xa") or unit_meta.get("name") or "—",
            "procedure": row["procedure"],
            "procedureLabel": row["procedureLabel"] or row["procedure"],
            "kind": row["kind"],
        })
    return {
        "scope": _scope_summary(resolved),
        "range": {"from": dateFrom, "to": dateTo},
        "source": "autofill",
        "items": items,
        "total": result["total"],
        "page": page,
        "pageSize": pageSize,
    }


@router.get("/export")
async def export(
    user: dict = Depends(require_dashboard),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    unit: str | None = Query(None),
):
    """Xuất Excel thống kê từ dữ liệu đã gộp AF+HF. Tỉnh: 4 sheet (kèm Theo đơn vị); xã/phường: 3 sheet.

    Nhật ký hồ sơ (Auto Fill) đưa vào sheet cuối. Ghi log mỗi lượt xuất để phục vụ audit.
    """
    data = await summary(user=user, dateFrom=dateFrom, dateTo=dateTo, unit=unit)

    # Nhật ký hồ sơ cho sheet cuối: lấy theo đúng phạm vi đang xuất (đơn vị đang chọn hoặc toàn bộ).
    units = data.get("units") or []
    selected = data.get("selected")
    ids = [selected["unitId"]] if selected else [u["unitId"] for u in units]
    date_from, date_to = _range(dateFrom, dateTo)
    unit_by_id = {u["unitId"]: u for u in units}
    log_res = await repo.list_dossier_log(
        user_ids=ids,
        date_from=date_from,
        date_to=date_to,
        skip=0,
        limit=_EXPORT_LOG_CAP,
        experience="autofill",
    )
    logs = [
        {
            "requestId": row["requestId"],
            "receivedAt": row["createdAt"],
            "unitName": (unit_by_id.get(row["userId"]) or {}).get("xa")
            or (unit_by_id.get(row["userId"]) or {}).get("name")
            or "—",
            "procedureLabel": row["procedureLabel"] or row["procedure"],
            "kind": row["kind"],
        }
        for row in log_res["items"]
    ]

    content = build_dashboard_workbook(data, logs)
    filename = export_filename(data)
    logger.info(
        "Xuất Excel dashboard: user=%s role=%s scope=%s unit=%s log_rows=%s",
        user.get("id"), user.get("role"), data["scope"]["scopeKind"], unit or "all", len(logs),
    )
    quoted = urllib.parse.quote(filename)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )
