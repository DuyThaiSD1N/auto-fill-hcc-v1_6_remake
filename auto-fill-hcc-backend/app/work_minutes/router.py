"""API biên bản làm việc (web thống kê, nhóm Báo cáo hằng ngày).

Biên bản làm việc giữa đơn vị triển khai và Trung tâm PVHCC một xã/phường cho một kỳ: số liệu hệ thống
tự điền (hồ sơ theo thủ tục, có / chưa có giọng nói), còn lại người làm biên bản điền trên bản xem trước
rồi xuất file Word. Ai trong phạm vi cũng làm được ("ai xuất cũng được"):
  - tài khoản đơn vị: biên bản của chính đơn vị mình;
  - tài khoản Tỉnh: các đơn vị trong tỉnh; admin: mọi đơn vị.
Phạm vi LUÔN phân giải từ token qua app/dashboard/scope.py.
"""
import io
import urllib.parse
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.deps import require_dashboard
from app.core.errors import AppError
from app.dashboard import procedures as dashboard_procedures
from app.dashboard.combine import fetch_handfree, merge_procedures
from app.dashboard.scope import resolve_dashboard_scope
from app.reports.integration import account_unit_key, fold, province_name
from app.stats import cutover
from app.traces.date_range import parse_stats_range
from app.work_minutes import repo, rules
from app.work_minutes.export import build_docx

router = APIRouter(prefix="/api/v1/work-minutes", tags=["work-minutes"])

_codes_by_key: dict[str, list[str]] | None = None


class _Context:
    def __init__(self, user: dict, scope: dict):
        self.user = user
        self.scope = scope
        self.user_id = str(user.get("_id") or user.get("id"))

    def unit(self, unit_id: str | None) -> dict:
        """Đơn vị làm biên bản — chỉ trong phạm vi token; tài khoản đơn vị luôn là chính mình."""
        if self.scope.get("scopeKind") == "unit":
            own = self.scope["self"]
            if unit_id and unit_id != own["unitId"]:
                raise AppError("UNIT_OUT_OF_SCOPE", "Đơn vị không thuộc phạm vi tài khoản.", 403)
            return own
        found = next((u for u in self.scope.get("units") or [] if u["unitId"] == unit_id), None)
        if not found:
            raise AppError("UNIT_OUT_OF_SCOPE", "Đơn vị không thuộc phạm vi tài khoản.", 403)
        return found

    def actor(self) -> dict:
        return {"by_id": self.user_id, "by_name": self.user.get("name") or self.user.get("username")}


async def _context(user: dict) -> _Context:
    return _Context(user, await resolve_dashboard_scope(user))


def _period(date_from: str | None, date_to: str | None) -> tuple[str, str]:
    start = rules.parse_day(date_from, "Từ ngày")
    end = rules.parse_day(date_to, "Đến ngày")
    if not start or not end:
        raise AppError("BAD_DATE", "Cần đủ từ ngày và đến ngày của kỳ.", 400)
    if start > end:
        raise AppError("BAD_DATE_RANGE", "Từ ngày phải nhỏ hơn hoặc bằng đến ngày.", 400)
    return start, end


def _code_of(key: str) -> str:
    """Mã TTHC của một dòng thủ tục: khoá gộp "tthc:<mã>", không thì mã trong danh mục thủ tục của Trợ lý."""
    global _codes_by_key
    if key.startswith("tthc:"):
        return key[5:]
    if _codes_by_key is None:
        items = dashboard_procedures.catalog({"scopeKind": "all", "province": None})["items"]
        _codes_by_key = {i["key"]: i["codes"] for i in items}
    codes = _codes_by_key.get(key[4:] if key.startswith("key:") else key) or []
    return codes[0] if codes else ""


async def _system(unit: dict, date_from: str, date_to: str) -> dict:
    """Hồ sơ của đơn vị trong kỳ, đếm cùng cách trang Theo đơn vị (Auto Fill + Handfree, tổ dân phố tính vào
    xã cha). Có giọng nói = Handfree (Trợ lý nhân dân), chưa có giọng nói = Auto Fill."""
    start, end = parse_stats_range(date_from, date_to)
    uid = unit["unitId"]
    af = await cutover.dossier_stats(user_ids=[uid], date_from=start, date_to=end, experience="autofill")
    af_procs = next((w.get("procedures") or [] for w in af.get("wards") or [] if w.get("userId") == uid), [])
    hf_units, _, hf_ok = await fetch_handfree([unit], start, end, want_daily=False)
    hf_procs = (hf_units.get(account_unit_key(unit.get("tinh"), unit.get("xa"), uid)) or {}).get("procedures") or []
    rows = [{"code": _code_of(p["key"]), "name": p["label"], "n": p["count"]} for p in merge_procedures(af_procs, hf_procs)]
    voice = sum(max(0, int(p.get("count") or 0)) for p in hf_procs)
    no_voice = sum(max(0, int(p.get("count") or 0)) for p in af_procs)
    return {"rows": rows, "v": voice, "nv": no_voice, "total": voice + no_voice, "handfreeOk": hf_ok}


def _unit_info(unit: dict) -> dict:
    return {
        "unitId": unit["unitId"],
        "name": unit.get("xa") or unit.get("name"),
        "province": province_name(unit.get("tinh")) or None,
        "place": rules.place_of(unit),
        "prov": rules.prov_of(unit),
    }


async def _fresh_draft(unit: dict) -> dict:
    today = rules.today_vn()
    last = await repo.latest(unit["unitId"])
    start = rules.default_from((last or {}).get("period_to"), today)
    doc = rules.build_doc(unit, await _system(unit, start, today), last)
    return {"unitId": unit["unitId"], "editingId": None, "from": start, "to": today, "lap": today,
            "doc": doc, "base": doc, "saved": False}


@router.get("")
async def state(user: dict = Depends(require_dashboard), unit: str | None = Query(None, max_length=64)):
    """Mọi thứ để mở trang cho một đơn vị: bản nháp đang làm (hoặc bản nháp mới chưa lưu), biên bản đã lập,
    văn bản mẫu dùng trên bản xem trước."""
    ctx = await _context(user)
    target = ctx.unit(unit)
    saved = await repo.get_draft(target["unitId"])
    return {
        "scopeKind": ctx.scope.get("scopeKind"),
        "today": rules.today_vn(),
        "unit": _unit_info(target),
        "template": {"company": rules.COMPANY, "noIssue": rules.NO_ISSUE, "next": rules.NEXT_DEFAULT},
        "draft": rules.serialize_draft(saved) if saved else await _fresh_draft(target),
        "minutes": [rules.serialize_summary(d) for d in await repo.history(target["unitId"])],
    }


@router.get("/system")
async def system(
    user: dict = Depends(require_dashboard),
    unit: str | None = Query(None, max_length=64),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
):
    """Số liệu hệ thống của kỳ + gợi ý khó khăn từ báo cáo hằng ngày cùng kỳ."""
    ctx = await _context(user)
    target = ctx.unit(unit)
    start, end = _period(dateFrom, dateTo)
    return {
        **await _system(target, start, end),
        "suggestions": await repo.difficulties(target["unitId"], start, end),
    }


class _DraftBody(BaseModel):
    unitId: str = Field(..., max_length=64)
    editingId: str | None = Field(None, max_length=64)
    from_: str = Field(..., alias="from")
    to: str
    lap: str
    doc: rules.Doc
    base: rules.Doc | None = None


def _clean(ctx: _Context, body: _DraftBody) -> tuple[dict, dict]:
    target = ctx.unit(body.unitId)
    start, end = _period(body.from_, body.to)
    lap = rules.parse_day(body.lap, "Ngày lập biên bản")
    if not lap:
        raise AppError("BAD_DATE", "Cần ngày lập biên bản.", 400)
    doc = body.doc.model_dump()
    values = {
        "period_from": start,
        "period_to": end,
        "lap_date": lap,
        "doc": doc,
        "base": body.base.model_dump() if body.base else doc,
    }
    return target, values


@router.put("/draft")
async def save_draft(body: _DraftBody, user: dict = Depends(require_dashboard)):
    """Tự lưu bản nháp (mỗi đơn vị một bản) để đổi máy vẫn làm tiếp."""
    ctx = await _context(user)
    target, values = _clean(ctx, body)
    if body.editingId and not await _owned(target, body.editingId):
        raise AppError("WORK_MINUTES_NOT_FOUND", "Không tìm thấy biên bản.", 404)
    actor = ctx.actor()
    saved = await repo.save_draft(target["unitId"], {
        **values, "editing_id": body.editingId, "updated_at": repo.now(),
        "updated_by_id": actor["by_id"], "updated_by_name": actor["by_name"],
    })
    return rules.serialize_draft(saved)


@router.delete("/draft")
async def discard_draft(user: dict = Depends(require_dashboard), unit: str | None = Query(None, max_length=64)):
    """Bỏ bản nháp, trả bản nháp mới (kỳ nối tiếp biên bản gần nhất, số liệu hệ thống)."""
    ctx = await _context(user)
    target = ctx.unit(unit)
    await repo.delete_draft(target["unitId"])
    return await _fresh_draft(target)


async def _owned(unit: dict, minutes_id: str) -> dict | None:
    doc = await repo.get(minutes_id)
    return doc if doc and doc.get("unit_id") == unit["unitId"] else None


@router.post("")
async def save_minutes(body: _DraftBody, user: dict = Depends(require_dashboard)):
    """Lưu biên bản khi xuất file: biên bản mới, hoặc cập nhật biên bản đang mở để sửa. Xong thì bỏ bản nháp."""
    ctx = await _context(user)
    target, values = _clean(ctx, body)
    at = repo.now()
    actor = ctx.actor()
    stamp = {"updated_at": at, "updated_by_id": actor["by_id"], "updated_by_name": actor["by_name"]}
    if body.editingId:
        current = await _owned(target, body.editingId)
        if not current:
            raise AppError("WORK_MINUTES_NOT_FOUND", "Không tìm thấy biên bản.", 404)
        saved = await repo.update(current["_id"], {**values, **stamp}, {"at": at, **actor, "action": "update"})
    else:
        saved = await repo.insert({
            **values, **stamp,
            "unit_id": target["unitId"],
            "unit_name": target.get("xa") or target.get("name"),
            "province": province_name(target.get("tinh")) or None,
            "created_at": at, "created_by_id": actor["by_id"], "created_by_name": actor["by_name"],
            "log": [{"at": at, **actor, "action": "create"}],
        })
    await repo.delete_draft(target["unitId"])
    return rules.serialize_full(saved)


async def _readable(ctx: _Context, minutes_id: str) -> dict:
    doc = await repo.get(minutes_id)
    if not doc:
        raise AppError("WORK_MINUTES_NOT_FOUND", "Không tìm thấy biên bản.", 404)
    ctx.unit(doc.get("unit_id"))  # ngoài phạm vi → 403
    return doc


@router.get("/{minutes_id}")
async def get_minutes(minutes_id: str, user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    return rules.serialize_full(await _readable(ctx, minutes_id))


def _file_name(doc: dict) -> str:
    lap = date.fromisoformat(doc["lap_date"])
    name = "".join(w[:1].upper() + w[1:] for w in fold(doc.get("unit_name") or "").replace("-", " ").split())
    return f"Bien ban lam viec - {name or 'Don vi'} - {lap.day:02d}-{lap.month:02d}-{lap.year}.docx"


@router.get("/{minutes_id}/docx")
async def download(minutes_id: str, user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    doc = await _readable(ctx, minutes_id)
    content = build_docx({"from": doc["period_from"], "to": doc["period_to"], "lap": doc["lap_date"], "doc": doc["doc"]})
    quoted = urllib.parse.quote(_file_name(doc))
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )
