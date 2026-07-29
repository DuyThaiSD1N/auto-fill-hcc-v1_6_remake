"""Lưu & truy vấn trace mỗi lần gọi /process: tài khoản (phường), thủ tục, OCR text gộp, JSON LLM.

Collection: traces. Ghi best-effort (lỗi không được làm hỏng request /process).
"""
import unicodedata
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongo import get_db

# Nhãn hiển thị model OCR theo provider key.
_OCR_LABELS = {"raw": "RAW", "vintern": "Vintern", "gemini": "Gemini", "both": "BOTH",
               "tiengnoi": "vintern-v6"}

# Đếm kiểu "TÁCH HỒ SƠ": trace có split=true (người dùng tick "tách hồ sơ" ở chứng thực
# bản sao/chữ ký, hoặc backfill dữ liệu cũ) → mỗi FILE cần chứng thực là 1 hồ sơ, thay vì
# gom cả lượt bấm thành 1. Trace split=false/None giữ cách đếm cũ.
# Với chứng thực CHỮ KÝ, giấy tùy thân (STT2) chỉ là giấy kèm theo, không phải hồ sơ —
# nhận diện qua tên file + tên ô đích (role) đã fold dấu. Bản sao thì đếm mọi file
# (CCCD ở bản sao chính là giấy được chứng thực bản sao).
_IDENTITY_HINTS_FOLDED = (
    "can cuoc", "cccd", "chung minh nhan dan",
    "ho chieu", "passport", "giay thong hanh", "xuat nhap canh",
)


def _fold_text(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower()).replace("đ", "d")
    return "".join(c for c in s if not unicodedata.combining(c))


def ocr_label(provider: str | None) -> str:
    return _OCR_LABELS.get(provider or "", provider or "—")


async def create_trace(
    *,
    request_id: str,
    user_id: str,
    username: str | None,
    name: str | None,
    procedure: str,
    procedure_label: str | None,
    ocr_provider: str | None,
    ocr_text: str,
    llm_output: dict | None,
    fields_count: int,
    status: str,
    applicant_name: str | None = None,
    attachments: list[dict] | None = None,
    kind: str = "autofill",  # "autofill" (bước điền) | "attach" (bước đính kèm)
    split: bool | None = None,  # lựa chọn "tách hồ sơ" trên popup (chứng thực bản sao/chữ ký);
    # None = không rõ (extension bản cũ chưa gửi cờ / thủ tục không có ô tick)
    key_fields_total: int = 0,   # tổng trường then chốt của thủ tục (chỉ áp cho autofill)
    key_fields_filled: int = 0,  # số trường then chốt BÓC TÁCH ĐƯỢC
    stats: dict | None = None,       # {ocr_latency_ms, llm_latency_ms, total_latency_ms} — thời gian xử lý server (ms)
    total_bytes: int | None = None,  # tổng dung lượng file của lượt (payload)
    error_code: str | None = None,
    created_at: datetime | None = None,
) -> str | None:
    doc = {
        "request_id": request_id,
        "user_id": user_id,
        "username": username,
        "name": name,  # tên hiển thị theo phường (vd "Phường Tân Phong")
        "applicant_name": applicant_name,  # người làm thủ tục (UI/VNeID hoặc parse)
        "attachments": attachments or [],  # [{name, role}] file đã đính kèm
        "kind": kind,  # phân biệt bước điền (autofill) vs bước đính kèm (attach)
        "split": split,  # true/false = người dùng chọn tách/gộp hồ sơ; None = không rõ
        "key_fields_total": key_fields_total,
        "key_fields_filled": key_fields_filled,
        "stats": stats,  # thời gian OCR/LLM/tổng (ms) — hiển thị ở drawer chi tiết trace
        "total_bytes": total_bytes,  # dung lượng hồ sơ (payload) của lượt
        "procedure": procedure,
        "procedure_label": procedure_label,
        "ocr_provider": ocr_provider,  # "raw" | "vintern"
        "ocr_label": ocr_label(ocr_provider),  # "RAW" | "Vintern"
        "ocr_text": ocr_text or "",
        "llm_output": llm_output,
        "fields_count": fields_count,
        "status": status,
        "error_code": error_code,
        "created_at": created_at or datetime.now(timezone.utc),
    }
    try:
        res = await get_db().traces.insert_one(doc)
        return str(res.inserted_id)
    except Exception:  # noqa: BLE001 — trace không được phép làm hỏng request
        return None


def _build_query(
    *,
    user_id: str | None,
    procedure: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict:
    query: dict = {}
    if user_id:
        query["user_id"] = user_id
    if procedure:
        query["procedure"] = procedure
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        query["created_at"] = rng
    return query


async def list_traces(
    *,
    user_id: str | None = None,
    procedure: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    db = get_db()
    query = _build_query(
        user_id=user_id, procedure=procedure, date_from=date_from, date_to=date_to
    )
    total = await db.traces.count_documents(query)
    # Danh sách: không trả ocr_text/llm_output (nặng) — chỉ trả khi xem chi tiết.
    projection = {"ocr_text": 0, "llm_output": 0}
    cursor = (
        db.traces.find(query, projection)
        .sort("created_at", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    items = [_serialize(d) for d in await cursor.to_list(length=limit)]
    return {"items": items, "total": total}


async def get_trace(trace_id: str) -> dict | None:
    try:
        oid = ObjectId(trace_id)
    except Exception:  # noqa: BLE001
        return None
    doc = await get_db().traces.find_one({"_id": oid})
    return _serialize(doc) if doc else None


async def facets() -> dict:
    """Giá trị phục vụ bộ lọc: danh sách phường (user) và thủ tục đã xuất hiện trong traces."""
    db = get_db()
    users = await db.traces.aggregate([
        {"$group": {"_id": "$user_id", "username": {"$first": "$username"},
                    "name": {"$first": "$name"}}},
        {"$sort": {"name": 1}},
    ]).to_list(length=500)
    procedures = await db.traces.aggregate([
        {"$group": {"_id": "$procedure", "label": {"$first": "$procedure_label"}}},
        {"$sort": {"label": 1}},
    ]).to_list(length=200)
    return {
        "users": [
            {"userId": u["_id"], "username": u.get("username"), "name": u.get("name")}
            for u in users
        ],
        "procedures": [
            {"key": p["_id"], "label": p.get("label")} for p in procedures
        ],
    }


def _norm_file_set(attachments) -> frozenset:
    """Tập tên file (chuẩn hóa: gộp khoảng trắng + lowercase) của một lần bấm."""
    return frozenset(
        " ".join(str(a.get("name") or "").split()).lower()
        for a in (attachments or [])
        if a and a.get("name")
    )


def _certified_file_names(attachments, procedure: str) -> set[str]:
    """Tập tên file (chuẩn hóa) được tính là hồ sơ theo cách đếm tách.

    Chữ ký: loại file tùy thân (STT2). Trùng tên giữa các lượt bấm (bấm lại cùng bộ file)
    tự khử khi union theo tên.
    """
    names: set[str] = set()
    for a in attachments or []:
        if not a or not a.get("name"):
            continue
        name = " ".join(str(a["name"]).split()).lower()
        if procedure == "chung-thuc-chu-ky":
            hay = _fold_text(name + " " + str(a.get("role") or ""))
            if any(kw in hay for kw in _IDENTITY_HINTS_FOLDED):
                continue
        names.add(name)
    return names


def _count_distinct_dossiers(file_sets: list[frozenset]) -> int:
    """Gom các lần bấm thành hồ sơ riêng biệt: 2 lần là CÙNG hồ sơ nếu tập file cái này ⊆ cái kia
    (bao gồm bằng nhau). Union-find; tập RỖNG không gộp với ai (mỗi cái tính 1 hồ sơ)."""
    n = len(file_sets)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        a = file_sets[i]
        if not a:
            continue
        for j in range(i + 1, n):
            b = file_sets[j]
            if b and (a <= b or b <= a):
                parent[find(i)] = find(j)

    return len({find(i) for i in range(n)})


async def stats(*, date_from: datetime | None = None, date_to: datetime | None = None) -> dict:
    """Thống kê số HỒ SƠ RIÊNG BIỆT theo phường (tài khoản) × thủ tục.

    Nhiều lần bấm (autofill/đính kèm) cùng một bộ giấy tờ (tập file trùng hoặc là con của nhau)
    được tính là 1 hồ sơ. NGOẠI LỆ: trace split=true (tách hồ sơ khi nộp chứng thực)
    → mỗi file cần chứng thực tính 1 hồ sơ.
    """
    db = get_db()
    query = _build_query(user_id=None, procedure=None, date_from=date_from, date_to=date_to)
    projection = {
        "user_id": 1, "name": 1, "username": 1, "split": 1,
        "procedure": 1, "procedure_label": 1, "attachments": 1, "created_at": 1,
    }
    docs = await db.traces.find(query, projection).to_list(length=200000)

    from collections import defaultdict

    buckets: dict[tuple[str, str], list[frozenset]] = defaultdict(list)
    # Bucket đếm kiểu tách hồ sơ: union tên file chứng thực + số lượt bấm.
    split_buckets: dict[tuple[str, str], dict] = {}
    ward_name: dict[str, str] = {}
    proc_label: dict[str, str] = {}
    for d in docs:
        uid = d.get("user_id") or "—"
        proc = d.get("procedure") or "—"
        ward_name[uid] = d.get("name") or d.get("username") or uid
        proc_label[proc] = d.get("procedure_label") or proc
        if d.get("split") is True:
            sb = split_buckets.setdefault((uid, proc), {"names": set(), "requests": 0})
            sb["names"] |= _certified_file_names(d.get("attachments"), proc)
            sb["requests"] += 1
        else:
            buckets[(uid, proc)].append(_norm_file_set(d.get("attachments")))

    wards: dict[str, dict] = {}
    grand: dict[str, int] = defaultdict(int)

    def _add(uid: str, proc: str, count: int, requests: int) -> None:
        ward = wards.setdefault(uid, {"userId": uid, "name": ward_name[uid], "total": 0, "requests": 0, "procedures": []})
        ward["procedures"].append({"key": proc, "label": proc_label[proc], "count": count, "requests": requests})
        ward["total"] += count
        ward["requests"] += requests
        grand[proc] += count

    # Một bucket có thể lẫn cả lượt tách lẫn lượt gộp (người dùng đổi lựa chọn giữa chừng)
    # → cộng 2 cách đếm, vẫn ra đúng 1 dòng thủ tục.
    for uid, proc in set(buckets) | set(split_buckets):
        sets = buckets.get((uid, proc), [])
        count = _count_distinct_dossiers(sets) if sets else 0
        requests = len(sets)
        sb = split_buckets.get((uid, proc))
        if sb:
            count += len(sb["names"])
            requests += sb["requests"]
        _add(uid, proc, count, requests)

    for ward in wards.values():
        ward["procedures"].sort(key=lambda p: (-p["count"], p["label"]))

    return {
        "wards": sorted(wards.values(), key=lambda w: -w["total"]),
        "procedures": sorted(
            ({"key": k, "label": proc_label[k], "count": v} for k, v in grand.items()),
            key=lambda p: (-p["count"], p["label"]),
        ),
        "totalDossiers": sum(grand.values()),
        "totalRequests": len(docs),
    }


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    created = doc.get("created_at")
    if isinstance(created, datetime):
        doc["created_at"] = created.astimezone(timezone.utc).isoformat()
    return doc
