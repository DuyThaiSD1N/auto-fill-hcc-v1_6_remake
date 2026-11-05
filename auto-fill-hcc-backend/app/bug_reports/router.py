"""API báo lỗi cho web thống kê.

Quyền LUÔN phân giải từ token qua phạm vi thống kê (app/dashboard/scope.py) — không nhận
tỉnh/xã/userId từ client:
  - phường/xã (reporter): gửi lỗi, xem/xoá lỗi của chính mình (đủ nội dung + ảnh);
  - Tỉnh (viewer): chỉ xem danh sách lỗi các xã trong tỉnh — mã, tên, thủ tục, đơn vị, trạng thái;
  - admin (manager): xem, sửa tên/nội dung, đổi trạng thái mọi lỗi.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.bug_reports import images, repo, rules
from app.core.deps import require_dashboard
from app.core.errors import AppError
from app.dashboard.scope import resolve_dashboard_scope
from app.dossiers import repo as dossiers_repo
from app.reports.integration import province_name
from app.traces.date_range import parse_stats_range
from app.users import tdp_rollup

router = APIRouter(prefix="/api/v1/bug-reports", tags=["bug-reports"])

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_RECENT_DOSSIERS = 10


class _Context:
    def __init__(self, user: dict, scope: dict):
        self.user = user
        self.scope = scope
        self.access = rules.access_of(user, scope)
        self.user_id = str(user.get("_id") or user.get("id"))

    def base_query(self) -> dict:
        if self.access == rules.MANAGER:
            return {**repo.NOT_DELETED}
        if self.access == rules.VIEWER:
            return {**repo.NOT_DELETED, "unit_id": {"$in": [u["unitId"] for u in self.scope["units"]]}}
        return {**repo.NOT_DELETED, "user_id": self.user_id}

    def actor(self) -> dict:
        return {"by_id": self.user_id, "by_name": self.user.get("name") or self.user.get("username")}


async def _context(user: dict) -> _Context:
    return _Context(user, await resolve_dashboard_scope(user))


def _require(ctx: _Context, *allowed: str) -> None:
    if ctx.access not in allowed:
        raise AppError("BUG_REPORT_FORBIDDEN", "Tài khoản không có quyền thao tác này.", 403)


async def _owned_or_managed(ctx: _Context, report_id: str) -> dict:
    doc = await repo.get(report_id)
    if doc is None:
        raise AppError("BUG_REPORT_NOT_FOUND", "Không tìm thấy lỗi.", 404)
    if ctx.access == rules.MANAGER or (ctx.access == rules.REPORTER and doc.get("user_id") == ctx.user_id):
        return doc
    # Không phân biệt "không có" với "không được xem" để khỏi dò được mã lỗi của đơn vị khác.
    raise AppError("BUG_REPORT_NOT_FOUND", "Không tìm thấy lỗi.", 404)


def _status_counts(counts: dict[str, int]) -> dict[str, int]:
    return {status: counts.get(status, 0) for status in rules.STATUSES}


@router.get("/summary")
async def summary(user: dict = Depends(require_dashboard)):
    """Vai trò + số trên menu. Web thống kê dựa vào `access` để dựng mục Báo lỗi."""
    ctx = await _context(user)
    counts = _status_counts(await repo.count_by(ctx.base_query(), "status"))
    return {
        "access": ctx.access,
        "total": sum(counts.values()),
        "open": counts["new"] + counts["doing"],
        "new": counts["new"],
    }


@router.get("/recent-dossiers")
async def recent_dossiers(user: dict = Depends(require_dashboard)):
    """10 hồ sơ gần nhất của tài khoản (gồm tổ dân phố trực thuộc) để gắn vào báo lỗi."""
    ctx = await _context(user)
    _require(ctx, rules.REPORTER)
    rollup = tdp_rollup.TdpRollup(await tdp_rollup.load_tdp_parents(), [ctx.user_id])
    result = await dossiers_repo.list_for_dashboard(
        user_ids=rollup.expand([ctx.user_id]), date_from=_EPOCH,
        date_to=datetime.now(timezone.utc) + timedelta(days=1),
        limit=_RECENT_DOSSIERS, experience=None,
    )
    return {"items": [
        {
            "dossierId": row["dossierId"],
            "procedure": row["procedure"],
            "procedureLabel": row["procedureLabel"] or row["procedure"],
            "startedAt": row["startedAt"],
            "experience": row["experience"],
        }
        for row in result["items"]
    ]}


@router.get("")
async def list_reports(
    user: dict = Depends(require_dashboard),
    status: Literal["all", "new", "doing", "done"] = Query("all"),
    q: str | None = Query(None, max_length=200),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    province: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
):
    ctx = await _context(user)
    base = ctx.base_query()
    # Lọc tỉnh chỉ dành cho admin; tài khoản Tỉnh đã bị khoá về tỉnh mình ở base_query.
    scoped = {**base, "province": province} if province and ctx.access == rules.MANAGER else base

    query = dict(scoped)
    if status != "all":
        query["status"] = status
    start, end = parse_stats_range(dateFrom, dateTo)
    if start or end:
        query["created_at"] = {k: v for k, v in (("$gte", start), ("$lt", end)) if v}
    term = (q or "").strip()
    if term:
        fields = ["code", "title", "dossier.procedure_label"]
        if ctx.access != rules.REPORTER:
            fields.append("unit_name")
        if ctx.access == rules.MANAGER:
            fields += ["text", "province", "dossier.dossier_id"]
        pattern = {"$regex": re.escape(term), "$options": "i"}
        query["$or"] = [{field: pattern} for field in fields]

    docs, total = await repo.list_page(query, skip=(page - 1) * pageSize, limit=pageSize)
    # Số trên chip tính trên phạm vi (kèm tỉnh đang chọn), chưa áp trạng thái/từ khoá/thời gian.
    counts = {"status": _status_counts(await repo.count_by(scoped, "status"))}
    if ctx.access == rules.MANAGER:
        by_province = await repo.count_by(base, "province")
        counts["provinces"] = sorted(
            ({"province": name, "count": n} for name, n in by_province.items() if name),
            key=lambda row: (-row["count"], row["province"]),
        )
    return {
        "access": ctx.access,
        "items": [rules.serialize(doc, ctx.access) for doc in docs],
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "counts": counts,
    }


@router.post("")
async def create_report(
    user: dict = Depends(require_dashboard),
    text: str = Form(""),
    dossierId: str | None = Form(None),
    files: list[UploadFile] | None = File(None),
):
    ctx = await _context(user)
    _require(ctx, rules.REPORTER)
    text = text.strip()
    uploads = files or []
    if len(text) > rules.MAX_TEXT:
        raise AppError("BUG_TEXT_TOO_LONG", f"Nội dung tối đa {rules.MAX_TEXT} ký tự.", 400)
    if len(uploads) > rules.MAX_IMAGES:
        raise AppError("BUG_TOO_MANY_IMAGES", f"Mỗi báo lỗi đính kèm tối đa {rules.MAX_IMAGES} ảnh.", 400)
    if not text and not uploads:
        raise AppError("BUG_EMPTY", "Hãy nhập mô tả lỗi hoặc đính kèm ảnh.", 400)

    checked = []
    for upload in uploads:
        raw = await upload.read(images.MAX_BYTES + 1)
        checked.append((raw, *images.inspect(raw)))

    links = await tdp_rollup.load_tdp_parents()
    dossier = None
    if dossierId:
        found = await repo.find_dossier(dossierId, tdp_rollup.TdpRollup(links, [ctx.user_id]).expand([ctx.user_id]))
        if found is None:
            raise AppError("BUG_DOSSIER_NOT_FOUND", "Hồ sơ đã chọn không thuộc tài khoản này.", 400)
        dossier = {
            "dossier_id": dossierId,
            "procedure": found.get("procedure"),
            "procedure_label": found.get("procedure_label") or found.get("procedure"),
            "started_at": found.get("started_at"),
            "experience": found.get("experience") or "autofill",
        }

    self_unit = ctx.scope.get("self") or {}
    # Tổ dân phố báo lỗi thay cho xã cha: tỉnh lọc theo đơn vị nên phải gắn vào xã cha.
    unit_id = tdp_rollup.TdpRollup(links, None).unit(ctx.user_id)
    prefix = rules.code_prefix(self_unit.get("xa"), self_unit.get("name"))
    code = rules.format_code(prefix, await repo.next_seq(prefix))
    report_id = ObjectId()
    at = repo.now()
    try:
        saved = images.save_all(str(report_id), checked)
        doc = {
            "_id": report_id,
            "code": code,
            "title": rules.make_title(text, dossier and dossier["procedure_label"]),
            "text": text,
            "status": "new",
            "user_id": ctx.user_id,
            "reporter_name": user.get("name") or user.get("username"),
            "unit_id": unit_id,
            "unit_name": self_unit.get("xa") or self_unit.get("name"),
            "province": province_name(self_unit.get("tinh")) or None,
            "dossier": dossier,
            "images": saved,
            "log": [{"at": at, **ctx.actor(), "action": "create"}],
            "created_at": at,
            "updated_at": at,
            "deleted_at": None,
        }
        await repo.insert(doc)
    except Exception:
        images.remove_all(str(report_id))
        raise
    return rules.serialize(doc, ctx.access)


@router.get("/{report_id}")
async def get_report(report_id: str, user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    _require(ctx, rules.REPORTER, rules.MANAGER)
    doc = await _owned_or_managed(ctx, report_id)
    out = rules.serialize(doc, ctx.access)
    if ctx.access == rules.MANAGER:
        out["log"] = rules.serialize_log(doc.get("log"))
        dossier_id = (doc.get("dossier") or {}).get("dossier_id")
        traces = await repo.trace_requests(dossier_id) if dossier_id else []
        out["requests"] = [
            {"requestId": t.get("request_id"), "kind": t.get("kind"), "at": rules.iso(t.get("created_at"))}
            for t in traces if t.get("request_id")
        ]
    return out


class ReportPatch(BaseModel):
    title: str | None = None
    text: str | None = None
    status: Literal["new", "doing", "done"] | None = None


@router.patch("/{report_id}")
async def patch_report(report_id: str, body: ReportPatch, user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    _require(ctx, rules.MANAGER)
    doc = await _owned_or_managed(ctx, report_id)
    at = repo.now()
    changes: dict = {}
    log: list[dict] = []
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise AppError("BUG_TITLE_EMPTY", "Hãy nhập tên lỗi.", 400)
        if len(title) > rules.MAX_TITLE:
            raise AppError("BUG_TITLE_TOO_LONG", f"Tên lỗi tối đa {rules.MAX_TITLE} ký tự.", 400)
        if title != doc.get("title"):
            changes["title"] = title
            log.append({"at": at, **ctx.actor(), "action": "title"})
    if body.text is not None:
        text = body.text.strip()
        if len(text) > rules.MAX_TEXT:
            raise AppError("BUG_TEXT_TOO_LONG", f"Nội dung tối đa {rules.MAX_TEXT} ký tự.", 400)
        if text != (doc.get("text") or ""):
            changes["text"] = text
            log.append({"at": at, **ctx.actor(), "action": "text"})
    if body.status is not None and body.status != doc.get("status"):
        changes["status"] = body.status
        log.append({"at": at, **ctx.actor(), "action": "status", "to": body.status})
    if changes:
        changes["updated_at"] = at
        await repo.update(doc["_id"], changes, log)
    return await get_report(report_id, user)


@router.delete("/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    _require(ctx, rules.REPORTER)
    doc = await _owned_or_managed(ctx, report_id)
    at = repo.now()
    await repo.update(doc["_id"], {"deleted_at": at, "updated_at": at}, [{"at": at, **ctx.actor(), "action": "delete"}])
    return {"ok": True, "code": doc.get("code")}


@router.get("/{report_id}/images/{index}")
async def get_image(report_id: str, index: int, user: dict = Depends(require_dashboard)):
    ctx = await _context(user)
    _require(ctx, rules.REPORTER, rules.MANAGER)
    doc = await _owned_or_managed(ctx, report_id)
    saved = doc.get("images") or []
    if index < 0 or index >= len(saved) or not saved[index].get("path"):
        raise AppError("BUG_IMAGE_NOT_FOUND", "Không tìm thấy ảnh.", 404)
    return FileResponse(
        images.absolute_path(saved[index]["path"]),
        media_type=saved[index].get("type") or "image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )
