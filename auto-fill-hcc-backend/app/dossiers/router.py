"""Mốc NỘP hồ sơ do extension Auto Fill báo về.

Handfree không dùng endpoint này: bên đó cú bấm đi theo đường chat (`__event:submit_clicked`)
vì sidebar đang giữ sẵn conversation. Auto Fill không có phiên chat nên báo thẳng qua HTTP.

Chỉ CHẤM MỐC, không xác nhận hồ sơ vào được cổng hay chưa: cổng có thể báo thiếu giấy tờ sau
cú bấm. Bấm lại thì lần cuối ghi đè (xem dossiers/repo.py).
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.deps import require_auth, require_trace_reader
from app.core.errors import AppError
from app.dossiers import repo as dossiers_repo
from app.dossiers.rating_card import level_label
from app.traces import repo as traces_repo
from app.traces.date_range import parse_stats_range

router = APIRouter(prefix="/api/v1/dossiers", tags=["dossiers"])


class SubmitClickReq(BaseModel):
    dossierId: str = Field(min_length=1, max_length=64)
    portalHost: str = Field(default="", max_length=200)
    # Mã trên URL cổng. Với cổng tư pháp đây là mã THỦ TỤC chứ không phải mã hồ sơ (đã kiểm:
    # hai hồ sơ khai tử khác nhau cùng ra /nop-ho-so/144862) → chỉ lưu đối chiếu, KHÔNG làm khóa.
    portalDossierRef: str = Field(default="", max_length=100)


class RatingReq(BaseModel):
    dossierId: str = Field(min_length=1, max_length=64)
    # Bước 1 gửi mỗi `level`; bước 2 gửi thêm lý do/ý kiến. `skipped` cho lượt bỏ qua hẳn.
    level: int | None = Field(default=None, ge=1, le=5)
    reasons: list[str] = Field(default_factory=list, max_length=10)
    note: str = Field(default="", max_length=1000)
    skipped: bool = False


@router.post("/rating")
async def save_rating(body: RatingReq, user: dict = Depends(require_auth)):
    """Phiếu đánh giá trải nghiệm từ extension Auto Fill.

    Gọi được NHIỀU LẦN cho cùng một hồ sơ và lần sau ghi đè lần trước — cố ý: extension ghi
    ngay khi công dân chạm mức (bước 1), rồi ghi lại đầy đủ khi bấm gửi (bước 2). Bỏ dở bước 2
    thì phiếu bước 1 vẫn còn, đúng như Handfree đang làm.

    Handfree không dùng endpoint này: bên đó phiếu đi theo đường chat vì đã có sẵn conversation.
    """
    reasons = [str(x).strip()[:120] for x in body.reasons if str(x).strip()]
    await dossiers_repo.save_rating(
        dossier_id=body.dossierId,
        level=body.level,
        level_label=level_label(body.level),
        reasons=reasons,
        note=body.note.strip(),
        # Bỏ qua = không chạm mức nào và không để lại gì. Tự suy thay vì tin cờ của client để
        # phiếu "chọn mức rồi bỏ dở" không bị đếm nhầm thành phiếu bỏ qua.
        skipped=bool(body.skipped) or (body.level is None and not reasons and not body.note.strip()),
        owner_user_id=str(user.get("id") or ""),
    )
    return {"ok": True}


@router.post("/submit-click")
async def submit_click(body: SubmitClickReq, user: dict = Depends(require_auth)):
    """Cán bộ vừa bấm "Gửi hồ sơ" trên cổng.

    Không tạo document mới: chỉ cập nhật hồ sơ ĐÃ có mốc bắt đầu. Bấm nộp trên một hồ sơ mà
    extension chưa từng điền/đính kèm thì không có gì để chấm — cố ý, vì báo cáo chỉ nên tính
    hồ sơ trợ lý có tham gia.
    """
    await dossiers_repo.add_submit_event(
        dossier_id=body.dossierId,
        clicked_at=datetime.now(timezone.utc),
        portal_host=body.portalHost or None,
        portal_dossier_ref=body.portalDossierRef or None,
        owner_user_id=str(user.get("id") or ""),
    )
    return {"ok": True}


# ── Đọc: trang QUẢN TRỊ (fe/src) ──────────────────────────────────────────────────────────
# Gác require_trace_reader — CÙNG cửa với /api/v1/traces. Dữ liệu ở đây (tên công dân + nhật
# ký giấy tờ) cùng hạng PII với trace, nên không được dùng require_dashboard: dep đó cho cả
# tài khoản phường vào và sẽ lộ hồ sơ toàn hệ thống.
@router.get("")
async def list_dossiers(
    _: dict = Depends(require_trace_reader),
    userId: str | None = Query(None),
    procedure: str | None = Query(None),
    source: Literal["all", "autofill", "handfree"] = Query("all"),
    status: Literal["all", "submitted", "unsubmitted"] = Query("all"),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    date_from, date_to = parse_stats_range(dateFrom, dateTo)
    res = await dossiers_repo.list_dossiers(
        user_id=userId,
        procedure=procedure,
        experience=None if source == "all" else source,
        submitted=None if status == "all" else (status == "submitted"),
        date_from=date_from,
        date_to=date_to,
        skip=(page - 1) * pageSize,
        limit=pageSize,
    )
    return {**res, "page": page, "pageSize": pageSize}


@router.get("/{dossier_id}")
async def get_dossier(dossier_id: str, _: dict = Depends(require_trace_reader)):
    """Chi tiết một hồ sơ + nhật ký các lượt điền/đính kèm của chính nó."""
    doc = await dossiers_repo.get_dossier(dossier_id)
    if not doc:
        raise AppError("DOSSIER_NOT_FOUND", "Không tìm thấy hồ sơ", 404)
    return {**doc, "traces": await traces_repo.list_by_dossier(dossier_id)}
