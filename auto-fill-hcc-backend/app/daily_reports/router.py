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
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.deps import require_dashboard
from app.core.errors import AppError
from app.daily_reports import repo, rules
from app.daily_reports.export import build_workbook
from app.dashboard.scope import narrow_to_province, resolve_dashboard_scope
from app.reports.integration import fold, province_name
from app.stats import cutover
from app.traces.date_range import parse_stats_range
from app.users import tdp_rollup

router = APIRouter(prefix="/api/v1/daily-reports", tags=["daily-reports"])

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


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


async def _active_ids(units: list[dict], date_from: str | None, date_to: str | None) -> set[str]:
    """Tài khoản có phát sinh hồ sơ trong khoảng ngày (Auto Fill + Handfree, cùng cách đếm bảng thống kê,
    hồ sơ tổ dân phố tính vào xã cha). Đơn vị không có hồ sơ thì không cần báo cáo."""
    ids = [u["unitId"] for u in units]
    if not ids:
        return set()
    start, end = parse_stats_range(date_from, date_to)
    start = start or _EPOCH
    end = end or datetime.now(timezone.utc) + timedelta(days=1)
    active: set[str] = set()
    for experience in ("autofill", "handfree"):
        for row in await cutover.daily_dossier_counts(user_ids=ids, date_from=start, date_to=end, experience=experience):
            if int(row.get("count") or 0) > 0:
                active.add(str(row["userId"]))
    return active


def _today_status(units: list[dict], reported: list[dict], active: set[str]) -> tuple[int, list[list[dict]]]:
    """(số đơn vị phải báo cáo hôm nay, đơn vị chưa gửi — mỗi đơn vị là danh sách tài khoản của nó).

    Chỉ đơn vị CÓ PHÁT SINH hồ sơ hôm nay mới phải báo cáo (`active`); đơn vị không có hồ sơ mà vẫn gửi thì
    tính vào mẫu số như đã báo cáo. Một xã có thể có nhiều tài khoản (hoặc tài khoản cũ còn sót): đếm theo
    ĐƠN VỊ = tỉnh + tên xã, xã có một tài khoản đã gửi là xong. Tài khoản tạm khoá không tính.
    """
    def key(province, name) -> tuple[str, str]:
        return fold(province_name(province)), fold(name)

    done_ids = {str(d.get("unit_id")) for d in reported}
    done_keys = {key(d.get("province"), d.get("unit_name")) for d in reported}
    groups: dict[tuple[str, str], list[dict]] = {}
    for u in units:
        if not u.get("accessDisabled"):
            groups.setdefault(key(u.get("tinh"), _unit_name(u)), []).append(u)
    count, missing = 0, []
    for k, accounts in groups.items():
        done = k in done_keys or any(a["unitId"] in done_ids for a in accounts)
        if done or any(a["unitId"] in active for a in accounts):
            count += 1
            if not done:
                missing.append(accounts)
    return count, missing


@router.get("/summary")
async def summary(user: dict = Depends(require_dashboard)):
    """Vai trò + trạng thái hôm nay cho menu. Web dựa vào `access` để dựng mục Báo cáo hằng ngày."""
    ctx = await _context(user)
    today = rules.today_vn()
    if ctx.access == rules.REPORTER:
        return {"access": ctx.access, "today": today, "sentToday": await repo.find_day(ctx.user_id, today) is not None}
    return {"access": ctx.access, "today": today}


@router.get("/today")
async def get_today(user: dict = Depends(require_dashboard), date: str | None = Query(None)):
    """Báo cáo của đơn vị cho một ngày (mặc định hôm nay) — chọn ngày đã qua để gửi bù hoặc sửa."""
    ctx = await _context(user)
    ctx.require(rules.REPORTER)
    today = rules.today_vn()
    day = rules.report_day(date, today)
    doc = await repo.find_day(ctx.user_id, day)
    return {"date": day, "today": today, "report": rules.serialize(doc, ctx.access, today) if doc else None}


class _TodayBody(BaseModel):
    # Bỏ trống = hôm nay (web bản cũ không gửi trường này).
    date: str | None = None
    assistantCount: int
    actualCount: int
    advantages: str = ""
    difficulties: str = ""


@router.put("/today")
async def save_today(body: _TodayBody, user: dict = Depends(require_dashboard)):
    """Gửi hoặc sửa báo cáo của một ngày (mặc định hôm nay; được chọn ngày đã qua để gửi bù, không có ngày
    tương lai). Giờ gửi luôn là giờ thật lúc bấm gửi nên vẫn biết báo cáo nào gửi bù."""
    ctx = await _context(user)
    ctx.require(rules.REPORTER)
    values = {
        "assistant_count": rules.clean_count(body.assistantCount, "Số hồ sơ phát sinh trên Trợ lý"),
        "actual_count": rules.clean_count(body.actualCount, "Số hồ sơ cán bộ ghi nhận thực tế"),
        "advantages": rules.clean_text(body.advantages),
        "difficulties": rules.clean_text(body.difficulties),
    }
    today = rules.today_vn()
    day = rules.report_day(body.date, today)
    at = repo.now()
    existed = await repo.find_day(ctx.user_id, day) is not None
    self_unit = ctx.scope.get("self") or {}
    # Tổ dân phố báo cáo thay cho xã cha: tỉnh lọc theo đơn vị nên gắn vào xã cha (cùng cách báo lỗi).
    unit_id = tdp_rollup.TdpRollup(await tdp_rollup.load_tdp_parents(), None).unit(ctx.user_id)
    doc = await repo.upsert_day(
        ctx.user_id, day,
        {**values, "updated_at": at},
        {
            "unit_id": unit_id,
            "unit_name": _unit_name(self_unit),
            "province": province_name(self_unit.get("tinh")) or None,
            "reporter_name": user.get("name") or user.get("username"),
            "created_at": at,
        },
        {"at": at, **ctx.actor(), "action": "update" if existed else "create", **({"late": True} if day < today else {})},
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
        # Đơn vị "trong báo cáo" của khoảng ngày = có phát sinh hồ sơ hoặc đã gửi báo cáo. Tính trên toàn
        # phạm vi tài khoản (mọi tỉnh) để web dựng ô chọn tỉnh/đơn vị; mẫu số "Từ x/y" theo bộ lọc hiện tại.
        all_units = ctx.scope.get("units") or []
        range_query, _ = _filters(ctx, dateFrom, dateTo, None, None)
        involved = await _active_ids(all_units, dateFrom, dateTo) | await repo.unit_ids(range_query)
        out["activeUnits"] = [
            {"unitId": u["unitId"], "name": u.get("name"), "xa": u.get("xa"), "tinh": u.get("tinh")}
            for u in all_units if u["unitId"] in involved
        ]
        out["unitCount"] = sum(1 for u in units if u["unitId"] in involved)
        # Đơn vị CÓ HỒ SƠ HÔM NAY mà chưa gửi báo cáo hôm nay, trong phạm vi đang lọc (không theo khoảng ngày).
        scope_query = {k: v for k, v in query.items() if k != "date"}
        active_today = await _active_ids(units, today, today)
        today_count, missing = _today_status(units, await repo.reported_on(scope_query, today), active_today)
        out["todayUnitCount"] = today_count
        out["missingToday"] = sorted(
            (
                {
                    "unitId": accounts[0]["unitId"],
                    # Mọi tài khoản của đơn vị: web lọc "báo cáo cũ" theo cả nhóm.
                    "unitIds": [a["unitId"] for a in accounts],
                    "name": _unit_name(accounts[0]),
                    "province": province_name(accounts[0].get("tinh")) or None,
                }
                for accounts in missing
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
