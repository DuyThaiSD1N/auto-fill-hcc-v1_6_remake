"""Vòng đời MỘT hồ sơ: bắt đầu — bấm nộp — đóng. Dùng chung Handfree + Auto Fill.

`_id` = khóa hồ sơ, CHUNG cho hai kênh (cùng giá trị với `traces.dossier_id`):
  - Handfree : conversation_id — một conversation = một hồ sơ (mọi lối "làm thủ tục khác"
    đều xoá phiên và tạo phiên mới);
  - Auto Fill: dossierId sinh trong `autofill_session_<tabId>` của extension.

Vì sao KHÔNG nhét vào `traces`:
  - trace được ghi lúc chạy pipeline, tức TRƯỚC khi công dân bấm nộp;
  - dashboard đang đếm "1 hồ sơ" bằng cách suy đoán tập tên file (traces/metadata.py) —
    thêm cột vào đó là trộn hai mô hình đếm.
Collection này là dữ liệu CỘNG THÊM: không đụng vào cách đếm cũ, deploy không vỡ báo cáo.

KHÔNG đặt TTL. `conversations` tự xoá sau 24h; nếu mốc thời gian nằm ở đó thì hôm sau
xem thống kê là mất sạch — đó chính là lý do tách ra đây.

`duration` cố ý KHÔNG lưu: tính lúc query từ started_at/submit_clicked_at để không bao giờ
lệch với hai mốc gốc.
"""
from datetime import datetime, timezone

from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def upsert_started(
    *,
    dossier_id: str,
    user_id: str,
    username: str | None,
    name: str | None,
    procedure: str | None,
    procedure_label: str | None,
    province: str | None,
    ward: str | None,
    started_at: datetime,
    experience: str = "handfree",
    applicant_name: str | None = None,
) -> None:
    """Ghi/cập nhật hồ sơ đang làm — idempotent, gọi được nhiều lần.

    Handfree gọi mỗi lượt chat; Auto Fill gọi ở mỗi lượt /process và /attachments/plan.

    `started_at` chỉ ghi LẦN ĐẦU ($setOnInsert) → đúng định nghĩa "mốc bắt đầu = lượt
    process/đính kèm đầu tiên"; các lượt sau chỉ cập nhật nhãn thủ tục/nơi làm.
    """
    if not dossier_id:
        return
    changes: dict = {
        "experience": experience,
        "user_id": user_id,
        "username": username,
        "name": name,
        "procedure": procedure,
        "procedure_label": procedure_label,
        "province": province,
        "ward": ward,
        "updated_at": _now(),
    }
    # Tên công dân chỉ ghi khi trích được. Lượt đính kèm nhiều khi không đọc ra tên; ghi đè
    # vô điều kiện sẽ XOÁ mất tên mà lượt quét trước đã lấy đúng.
    if (applicant_name or "").strip():
        changes["applicant_name"] = applicant_name.strip()[:200]
    try:
        await get_db().dossiers.update_one(
            {"_id": dossier_id},
            {"$setOnInsert": {"started_at": started_at, "created_at": _now()}, "$set": changes},
            upsert=True,
        )
    except Exception:  # noqa: BLE001 — ghi vết không được chặn luồng của công dân
        return


# Trần số sự kiện giữ lại. Chứng thực tách nhiều tab mới sinh nhiều lần nộp; 50 là thừa sức,
# đủ để mảng không phình vô hạn nếu ai đó bấm loạn.
_MAX_SUBMIT_EVENTS = 50


async def add_submit_event(
    *,
    dossier_id: str,
    clicked_at: datetime,
    portal_host: str | None = None,
    portal_dossier_ref: str | None = None,
    owner_user_id: str | None = None,
) -> None:
    """Ghi MỘT lần bấm "Gửi hồ sơ" vào nhật ký của hồ sơ.

    Là LOG chứ không phải cờ: chứng thực bản sao tách nhiều tab dùng CHUNG một khóa hồ sơ và
    nộp N lần — số hồ sơ thực tế = số sự kiện ở đây. Bấm hụt (cổng báo thiếu giấy tờ) rồi bấm
    lại cũng thành 2 sự kiện; content script đã chặn bấm dồn trong 3 giây.

    `submit_clicked_at`/`submit_count` là bản rút gọn của mảng, giữ riêng để lọc theo khoảng
    ngày và sắp xếp bằng index — bới trong mảng thì không dùng được index.
    """
    if not dossier_id:
        return
    event: dict = {"at": clicked_at}
    if portal_host:
        event["host"] = portal_host
    if portal_dossier_ref:
        event["ref"] = portal_dossier_ref
    update: dict = {"submit_clicked_at": clicked_at, "updated_at": _now()}
    if portal_host:
        update["portal_host"] = portal_host
    if portal_dossier_ref:
        update["portal_dossier_ref"] = portal_dossier_ref
    # Khóa do client sinh nên phải chốt CHỦ SỞ HỮU: không cho tài khoản này chấm mốc nộp lên
    # hồ sơ của tài khoản khác (dù chỉ là đoán trúng UUID). Không khớp → update_one không
    # chạm document nào, im lặng bỏ qua.
    query: dict = {"_id": dossier_id}
    if owner_user_id:
        query["user_id"] = owner_user_id
    try:
        await get_db().dossiers.update_one(query, {
            "$set": update,
            "$inc": {"submit_count": 1},
            "$push": {"submit_events": {"$each": [event], "$slice": -_MAX_SUBMIT_EVENTS}},
        })
    except Exception:  # noqa: BLE001
        return


async def save_rating(
    *,
    dossier_id: str,
    level: int | None,
    level_label: str = "",
    reasons: list[str] | None = None,
    note: str = "",
    skipped: bool = False,
    at: datetime | None = None,
    owner_user_id: str | None = None,
) -> None:
    """Lưu phiếu đánh giá trải nghiệm của công dân vào hồ sơ (bền, không TTL như conversations).

    Ẩn danh: KHÔNG kèm định danh công dân — chỉ mức hài lòng + lý do chọn + ý kiến (nếu nói).
    Chỉ ghi cho hồ sơ ĐÃ có document (update_one không upsert, giống add_submit_event/mark_closed);
    hồ sơ chưa bắt đầu thì bỏ qua, không tạo document rác.

    GHI ĐÈ nguyên cụm `rating`: bước 1 (chọn mức) ghi phiếu chỉ có mức, bước 2 ghi lại đầy đủ
    kèm lý do/ý kiến. Bỏ dở bước 2 thì phiếu bước 1 vẫn còn — đó là lý do bước 1 phải ghi ngay
    chứ không gom lại chờ bấm "Gửi đánh giá".

    `owner_user_id` cho đường HTTP của Auto Fill: khóa hồ sơ do client sinh nên phải chốt chủ
    sở hữu, không cho tài khoản này ghi đè phiếu lên hồ sơ của tài khoản khác. Handfree không
    cần truyền — conversation đã thuộc về đúng tài khoản.
    """
    if not dossier_id:
        return
    rating = {
        "level": level,
        "level_label": level_label or "",
        "reasons": list(reasons or []),
        "note": note or "",
        "skipped": bool(skipped),
        "at": at or _now(),
    }
    query: dict = {"_id": dossier_id}
    if owner_user_id:
        query["user_id"] = owner_user_id
    try:
        await get_db().dossiers.update_one(
            query,
            {"$set": {"rating": rating, "updated_at": _now()}},
        )
    except Exception:  # noqa: BLE001 — đánh giá không được phép làm hỏng luồng đăng xuất
        return


async def mark_closed(dossier_id: str, reason: str = "") -> None:
    """Hồ sơ kết thúc mà KHÔNG qua đường nộp: Handfree xoá phiên (🔄, rảnh 10 phút, về
    trang chủ DVC); Auto Fill đổi thủ tục / "Tạo phiên mới" / đăng xuất / đóng tab.

    Chỉ ghi cho hồ sơ ĐÃ bắt đầu; chưa có lượt process/đính kèm nào thì không có document.
    Hồ sơ đóng mà không có submit_clicked_at = làm dở.
    """
    if not dossier_id:
        return
    try:
        await get_db().dossiers.update_one(
            {"_id": dossier_id, "closed_at": {"$exists": False}},
            {"$set": {"closed_at": _now(), "close_reason": reason or "", "updated_at": _now()}},
        )
    except Exception:  # noqa: BLE001
        return


# ── Đọc cho trang quản trị ────────────────────────────────────────────────────────────────
def _iso(value):
    """Chuỗi ISO có KÈM offset UTC.

    Driver không bật tz_aware nên Mongo trả datetime NAIVE (giá trị là UTC vì mọi chỗ ghi đều
    dùng datetime.now(timezone.utc)). Trả thẳng datetime naive ra API thì isoformat() không có
    offset, trình duyệt hiểu là giờ ĐỊA PHƯƠNG và hiển thị lệch 7 tiếng.

    Dùng replace() chứ KHÔNG dùng astimezone(): astimezone() coi naive là giờ máy chủ nên chỉ
    đúng khi máy chủ chạy UTC — dời máy chủ sang múi khác là sai âm thầm.
    """
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
    return value


def _serialize_rating(rating) -> dict | None:
    """camelCase phiếu đánh giá cho FE/dashboard; None nếu hồ sơ chưa có đánh giá."""
    if not isinstance(rating, dict):
        return None
    return {
        "level": rating.get("level"),
        "levelLabel": rating.get("level_label") or "",
        "reasons": list(rating.get("reasons") or []),
        "note": rating.get("note") or "",
        "skipped": bool(rating.get("skipped")),
        "at": _iso(rating.get("at")),
    }


def _procedure_label(doc: dict) -> str | None:
    """Tên thủ tục lấy từ registry LÕI theo `procedure` (khóa), không dùng nhãn đã lưu.

    Kênh Handfree có `shortLabel` riêng cho card chọn thủ tục ("Chứng thực chữ ký"), ngắn hơn
    tên hành chính thật ("Chứng thực chữ ký trong các giấy tờ, văn bản (áp dụng cho cả...)").
    Báo cáo phải là tên THẬT.

    Tra lúc ĐỌC nên: (1) dòng đã lưu nhãn ngắn từ trước cũng hiện đúng, khỏi migrate;
    (2) đổi tên thủ tục trong registry là báo cáo đổi theo.
    Khóa không còn trong registry (thủ tục đã gỡ) thì rơi về nhãn đã lưu.
    """
    from app.procedures.registry import get_procedure

    proc = get_procedure(str(doc.get("procedure") or "")) or {}
    return proc.get("label") or doc.get("procedure_label")


def _serialize(doc: dict) -> dict:
    """camelCase cho FE, giống hợp đồng của /api/v1/traces."""
    events = doc.get("submit_events") or []
    started = doc.get("started_at")
    submitted = doc.get("submit_clicked_at")
    return {
        "id": doc.get("_id"),
        "experience": doc.get("experience"),
        "userId": doc.get("user_id"),
        "username": doc.get("username"),
        "name": doc.get("name"),
        "applicantName": doc.get("applicant_name"),
        "procedure": doc.get("procedure"),
        "procedureLabel": _procedure_label(doc),
        "province": doc.get("province"),
        "ward": doc.get("ward"),
        "startedAt": _iso(started),
        "submittedAt": _iso(submitted),
        # Số hồ sơ THỰC TẾ của lượt này: chứng thực tách nhiều tab dùng chung một khóa và nộp
        # nhiều lần, mỗi lần là một hồ sơ trên cổng.
        "submitCount": int(doc.get("submit_count") or 0),
        "submitEvents": [
            {"at": _iso(e.get("at")), "host": e.get("host"), "ref": e.get("ref")} for e in events
        ],
        "closedAt": _iso(doc.get("closed_at")),
        "closeReason": doc.get("close_reason") or "",
        # Phiếu đánh giá trải nghiệm (ẩn danh), CHUNG cho cả hai kênh — trang Hồ sơ hiện ở cột
        # "Đánh giá" và trong bảng chi tiết. Dashboard công báo chưa tổng hợp mức hài lòng.
        "rating": _serialize_rating(doc.get("rating")),
        "portalHost": doc.get("portal_host"),
        "portalDossierRef": doc.get("portal_dossier_ref"),
        # Tính lúc đọc, KHÔNG lưu — để không bao giờ lệch với hai mốc gốc.
        "durationMs": (
            int((submitted - started).total_seconds() * 1000)
            if started and submitted and submitted >= started else None
        ),
    }


def _build_query(
    *,
    user_id: str | None,
    procedure: str | None,
    experience: str | None,
    submitted: bool | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict:
    query: dict = {}
    if user_id:
        query["user_id"] = user_id
    if procedure:
        query["procedure"] = procedure
    if experience:
        query["experience"] = experience
    if submitted is True:
        query["submit_clicked_at"] = {"$ne": None}
    elif submitted is False:
        query["submit_clicked_at"] = None
    # Lọc theo lúc BẮT ĐẦU: hồ sơ làm dở không có mốc nộp, lọc theo mốc nộp là mất hẳn chúng
    # khỏi danh sách — mà "bao nhiêu hồ sơ bỏ dở" chính là thứ cần nhìn.
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        query["started_at"] = rng
    return query


async def list_dossiers(
    *,
    user_id: str | None = None,
    procedure: str | None = None,
    experience: str | None = None,
    submitted: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    db = get_db()
    query = _build_query(
        user_id=user_id, procedure=procedure, experience=experience,
        submitted=submitted, date_from=date_from, date_to=date_to,
    )
    total = await db.dossiers.count_documents(query)
    # Danh sách không cần nhật ký sự kiện (chỉ màn chi tiết dùng) → bỏ cho nhẹ payload.
    cursor = (
        db.dossiers.find(query, {"submit_events": 0})
        .sort("started_at", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    docs = await cursor.to_list(length=limit)
    return {"items": [_serialize(d) for d in docs], "total": total}


async def list_for_dashboard(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    skip: int = 0,
    limit: int = 15,
    experience: str = "autofill",
    submitted: bool | None = None,
) -> dict:
    """Nhật ký hồ sơ cho bảng thống kê: mỗi HỒ SƠ = 1 dòng, KHÔNG PII.

    Khác `list_dossiers` (trang quản trị, kèm tên công dân): chỉ trả metadata tối thiểu và khoá
    theo TẬP user_id của phạm vi tài khoản đang xem — cùng lối với traces.list_dossier_log.

    Khác chính `list_dossier_log`: bên đó mỗi *lượt* điền/đính kèm là một dòng, nên một hồ sơ
    làm hai bước sẽ đếm thành hai. Ở đây một hồ sơ đúng một dòng, và có thêm mốc NỘP + phiếu
    đánh giá — hai thứ không tồn tại ở tầng trace.

    Lọc theo lúc BẮT ĐẦU, không theo lúc nộp: lọc theo mốc nộp là hồ sơ bỏ dở biến mất khỏi
    nhật ký, mà "bao nhiêu hồ sơ bỏ dở" mới là thứ cần nhìn.

    `submitted=True` lọc riêng hồ sơ ĐÃ HOÀN THÀNH (đã bấm nộp) — đúng tập mà thống kê đang
    đếm từ 15/9/2026, để cán bộ đối chiếu được con số trên KPI với từng dòng hồ sơ.
    """
    unique_ids = list(dict.fromkeys(str(value) for value in user_ids if value))
    if not unique_ids:
        return {"items": [], "total": 0}
    query: dict = {
        "user_id": {"$in": unique_ids},
        "started_at": {"$gte": date_from, "$lt": date_to},
    }
    if experience:
        query["experience"] = experience
    if submitted is True:
        query["submit_clicked_at"] = {"$ne": None}
    elif submitted is False:
        query["submit_clicked_at"] = None
    db = get_db()
    total = await db.dossiers.count_documents(query)
    cursor = (
        db.dossiers.find(query, {
            "_id": 1, "user_id": 1, "procedure": 1, "procedure_label": 1,
            "started_at": 1, "submit_clicked_at": 1, "submit_count": 1, "rating": 1,
        })
        .sort("started_at", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    items = [
        {
            "dossierId": str(doc["_id"]),
            "userId": str(doc.get("user_id") or ""),
            "procedure": doc.get("procedure"),
            "procedureLabel": doc.get("procedure_label"),
            "startedAt": _iso(doc.get("started_at")),
            "submittedAt": _iso(doc.get("submit_clicked_at")),
            "submitCount": int(doc.get("submit_count") or 0),
            "rating": _serialize_rating(doc.get("rating")),
        }
        async for doc in cursor
    ]
    return {"items": items, "total": total}


async def get_dossier(dossier_id: str) -> dict | None:
    doc = await get_db().dossiers.find_one({"_id": dossier_id})
    return _serialize(doc) if doc else None
