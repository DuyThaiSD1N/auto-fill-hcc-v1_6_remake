"""API báo cáo hằng ngày cho web thống kê.

Mỗi ngày đơn vị gửi 1 báo cáo: số hồ sơ phát sinh trên Trợ lý, số hồ sơ cán bộ ghi nhận thực tế,
thuận lợi, khó khăn. Ngày báo cáo do hệ thống tự lấy theo giờ Việt Nam; sửa được đến hết ngày.

Quyền LUÔN phân giải từ token qua phạm vi thống kê (app/dashboard/scope.py), như báo lỗi:
  - HCC xã/phường, HCC tỉnh (reporter): viết + xem báo cáo của chính mình;
  - tài khoản Tỉnh (viewer): xem báo cáo các đơn vị trong tỉnh;
  - admin (manager): xem mọi báo cáo.
"""
import io
import urllib.parse

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.deps import require_dashboard
from app.core.errors import AppError
from app.daily_reports import repo, rules
from app.daily_reports.export import build_workbook
from app.dashboard.scope import narrow_to_province, resolve_dashboard_scope
from app.reports.integration import province_name
from app.users import tdp_rollup

router = APIRouter(prefix="/api/v1/daily-reports", tags=["daily-reports"])


class _Context:
    def __init__(self, user: dict, scope: dict):
        self.user = user
        self.scope = scope
        self.access = rules.access_of(user, scope)
        self.user_id = str(user.get("_id") or user.get("id"))

    def require(self, *allowed: str) -> None:
        if self.access not in allowed:
            raise AppError("DAILY_REPORT_FORBIDDEN", "Tài khoản không có quyền thao tác này.", 403)

    def actor(self) -> dict:
        return {"by_id": self.user_id, "by_name": self.user.get("name") or self.user.get("username")}


async def _context(user: dict) -> _Context:
    return _Context(user, await resolve_dashboard_scope(user))


def _unit_name(unit: dict) -> str:
    return unit.get("xa") or unit.get("name") or ""


def _filters(ctx: _Context, date_from: str | None, date_to: str | None, province: str | None,
             unit: str | None) -> tuple[dict, list[dict]]:
    """Query Mongo + danh sách đơn vị trong phạm vi lọc (để tìm đơn vị chưa báo cáo).

    Phạm vi khoá theo token: reporter chỉ báo cáo của mình, viewer chỉ đơn vị trong tỉnh; tỉnh/đơn vị
    client gửi chỉ thu hẹp thêm, không mở rộng được.
    """
    start = rules.parse_day(date_from, "Từ ngày")
    end = rules.parse_day(date_to, "Đến ngày")
    if start and end and start > end:
        raise AppError("BAD_DATE_RANGE", "Từ ngày phải nhỏ hơn hoặc bằng đến ngày.", 400)
    query: dict = {}
    if start or end:
        query["date"] = {k: v for k, v in (("$gte", start), ("$lte", end)) if v}

    if ctx.access == rules.REPORTER:
        query["user_id"] = ctx.user_id
        return query, []

    units = ctx.scope.get("units") or []
    if ctx.access == rules.MANAGER and province and province != "all":
        units = narrow_to_province(ctx.scope, province)["units"] if ctx.scope["scopeKind"] == "all" else units
        query["province"] = province_name(province)
    elif ctx.access == rules.VIEWER:
        query["unit_id"] = {"$in": [u["unitId"] for u in units]}
    # Ô chọn đơn vị của web gửi một hoặc nhiều unitId cách nhau dấu phẩy.
    wanted = list(dict.fromkeys(x for x in (unit or "").split(",") if x.strip() and x != "all"))
    if wanted:
        by_id = {u["unitId"]: u for u in units}
        if any(x not in by_id for x in wanted):
            raise AppError("UNIT_OUT_OF_SCOPE", "Đơn vị không thuộc phạm vi tài khoản.", 403)
        units = [by_id[x] for x in wanted]
        query["unit_id"] = {"$in": wanted}
    return query, units


@router.get("/summary")
async def summary(user: dict = Depends(require_dashboard)):
    """Vai trò + trạng thái hôm nay cho menu. Web dựa vào `access` để dựng mục Báo cáo hằng ngày."""
    ctx = await _context(user)
    today = rules.today_vn()
    if ctx.access == rules.REPORTER:
        return {"access": ctx.access, "today": today, "sentToday": await repo.find_day(ctx.user_id, today) is not None}
    query, units = _filters(ctx, None, None, None, None)
    reported = await repo.units_on(query, today)
    return {
        "access": ctx.access,
        "today": today,
        "unitCount": len(units),
        "reportedToday": sum(1 for u in units if u["unitId"] in reported),
    }


@router.get("/today")
async def get_today(user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    ctx.require(rules.REPORTER)
    today = rules.today_vn()
    doc = await repo.find_day(ctx.user_id, today)
    return {"date": today, "report": rules.serialize(doc, ctx.access, today) if doc else None}


class _TodayBody(BaseModel):
    assistantCount: int
    actualCount: int
    advantages: str = ""
    difficulties: str = ""


@router.put("/today")
async def save_today(body: _TodayBody, user: dict = Depends(require_dashboard)):
    """Gửi hoặc sửa báo cáo HÔM NAY. Ngày lấy ở backend nên không sửa được báo cáo ngày đã qua."""
    ctx = await _context(user)
    ctx.require(rules.REPORTER)
    values = {
        "assistant_count": rules.clean_count(body.assistantCount, "Số hồ sơ phát sinh trên Trợ lý"),
        "actual_count": rules.clean_count(body.actualCount, "Số hồ sơ cán bộ ghi nhận thực tế"),
        "advantages": rules.clean_text(body.advantages),
        "difficulties": rules.clean_text(body.difficulties),
    }
    today = rules.today_vn()
    at = repo.now()
    existed = await repo.find_day(ctx.user_id, today) is not None
    self_unit = ctx.scope.get("self") or {}
    # Tổ dân phố báo cáo thay cho xã cha: tỉnh lọc theo đơn vị nên gắn vào xã cha (cùng cách báo lỗi).
    unit_id = tdp_rollup.TdpRollup(await tdp_rollup.load_tdp_parents(), None).unit(ctx.user_id)
    doc = await repo.upsert_day(
        ctx.user_id, today,
        {**values, "updated_at": at},
        {
            "unit_id": unit_id,
            "unit_name": _unit_name(self_unit),
            "province": province_name(self_unit.get("tinh")) or None,
            "reporter_name": user.get("name") or user.get("username"),
            "created_at": at,
        },
        {"at": at, **ctx.actor(), "action": "update" if existed else "create"},
    )
    return rules.serialize(doc, ctx.access, today)


@router.get("")
async def list_reports(
    user: dict = Depends(require_dashboard),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    province: str | None = Query(None, max_length=200),
    unit: str | None = Query(None, max_length=4000),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
):
    ctx = await _context(user)
    query, units = _filters(ctx, dateFrom, dateTo, province, unit)
    today = rules.today_vn()
    docs, total = await repo.list_page(query, skip=(page - 1) * pageSize, limit=pageSize)
    out = {
        "access": ctx.access,
        "today": today,
        "items": [rules.serialize(doc, ctx.access, today) for doc in docs],
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "totals": await repo.totals(query),
        "byDay": await repo.by_day(query),
    }
    if ctx.access != rules.REPORTER:
        # Đơn vị chưa gửi báo cáo HÔM NAY trong phạm vi đang lọc (không phụ thuộc khoảng ngày).
        scope_query = {k: v for k, v in query.items() if k != "date"}
        reported = await repo.units_on(scope_query, today)
        out["unitCount"] = len(units)
        out["missingToday"] = sorted(
            (
                {"unitId": u["unitId"], "name": _unit_name(u), "province": province_name(u.get("tinh")) or None}
                for u in units if u["unitId"] not in reported
            ),
            key=lambda u: (u["province"] or "", u["name"]),
        )
    return out


@router.get("/export")
async def export(
    user: dict = Depends(require_dashboard),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    province: str | None = Query(None, max_length=200),
    unit: str | None = Query(None, max_length=4000),
):
    """Excel đúng bộ lọc đang xem: sheet Báo cáo; tài khoản xem nhiều đơn vị có thêm sheet Theo đơn vị."""
    ctx = await _context(user)
    query, units = _filters(ctx, dateFrom, dateTo, province, unit)
    docs = await repo.for_export(query)
    content = build_workbook(docs, units if ctx.access != rules.REPORTER else None)
    span = "-".join(x for x in (dateFrom, dateTo) if x) or "tat-ca"
    quoted = urllib.parse.quote(f"Bao cao hang ngay - {span}.xlsx")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )
