"""Lưu & truy vấn trace mỗi lần gọi /process: tài khoản (phường), thủ tục, OCR text gộp, JSON LLM.

Collection: traces. Ghi best-effort (lỗi không được làm hỏng request /process).
"""
import copy
import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId

from app.db.mongo import get_db
from app.traces.date_range import VIETNAM_TZ
from app.traces.metadata import count_distinct_attachment_sets
from app.users.roles import OFFICIAL_ACCOUNT_ROLES, normalized_role

# Nhãn hiển thị model OCR theo provider key.
_OCR_LABELS = {"tiengnoi": "vintern-v12"}
_ALL_STATS_ROLES = ("admin", "user", "commune", "province")
_FILE_SUFFIX_RE = re.compile(r"\.[^./\\]+$")
# Mốc migration cố định: 00:00 25/08/2026 giờ Việt Nam.
# Trước mốc giữ nguyên số lịch sử; từ mốc mới bỏ phần mở rộng khi so tên file.
_STEM_RULE_CUTOFF = datetime(2026, 8, 24, 17, tzinfo=timezone.utc)
Experience = Literal["autofill", "handfree"]


def new_request_id() -> str:
    """Sinh mã hỗ trợ dùng chung cho cả Auto Fill và Handfree."""
    return "req_" + uuid.uuid4().hex[:12]


def ocr_label(provider: str | None) -> str:
    return _OCR_LABELS.get(provider or "", provider or "—")


async def _apply_current_account_names(db, docs: list[dict]) -> None:
    """Chuẩn hóa tên hiển thị trace theo tài khoản hiện tại.

    Handfree lịch sử từng ghi ``conv.location`` vào ``name`` nên có thể hiện địa điểm
    công dân chọn thay vì tài khoản thực hiện. Đối chiếu cả user_id và username giúp
    sửa cách hiển thị ngay cả với dữ liệu đã import/đổi id mà không sửa ngược trace gốc.
    """
    if not docs:
        return

    object_ids: list[ObjectId] = []
    usernames: set[str] = set()
    for doc in docs:
        user_id = str(doc.get("user_id") or "").strip()
        if ObjectId.is_valid(user_id):
            object_ids.append(ObjectId(user_id))
        username = str(doc.get("username") or "").strip().lower()
        if username:
            usernames.add(username)

    clauses: list[dict] = []
    if object_ids:
        clauses.append({"_id": {"$in": object_ids}})
    if usernames:
        clauses.append({"username": {"$in": list(usernames)}})
    if not clauses:
        return

    query = clauses[0] if len(clauses) == 1 else {"$or": clauses}
    accounts = await db.users.find(
        query, {"username": 1, "name": 1}
    ).to_list(length=len(object_ids) + len(usernames))
    by_id = {str(account["_id"]): account for account in accounts}
    by_username = {
        str(account.get("username") or "").strip().lower(): account
        for account in accounts
        if account.get("username")
    }

    for doc in docs:
        account = by_id.get(str(doc.get("user_id") or ""))
        if account is None:
            account = by_username.get(str(doc.get("username") or "").strip().lower())
        if account is None:
            continue
        account_name = str(account.get("name") or account.get("username") or "").strip()
        if account_name:
            doc["name"] = account_name


def _stats_account_context(accounts: list[dict], scope: str) -> tuple[dict[str, str], list[str]]:
    """Role hiện tại là nguồn phân loại; đổi role sẽ áp dụng lại cho toàn bộ trace lịch sử."""
    if scope not in {"all", "official"}:
        raise ValueError(f"Unsupported stats scope: {scope}")
    roles = {
        str(account["_id"]): normalized_role(account.get("role"))
        for account in accounts
        if account.get("_id") is not None
    }
    if scope == "official":
        included_ids = [
            user_id for user_id, role in roles.items() if role in OFFICIAL_ACCOUNT_ROLES
        ]
    else:
        included_ids = list(roles)
    return roles, included_ids


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
    stats_version: int = 1,
    dossier_ids: list[str] | None = None,
    key_fields_total: int = 0,   # tổng trường then chốt của thủ tục (chỉ áp cho autofill)
    key_fields_filled: int = 0,  # số trường then chốt BÓC TÁCH ĐƯỢC
    stats: dict | None = None,       # {ocr_latency_ms, llm_latency_ms, total_latency_ms} — thời gian xử lý server (ms)
    total_bytes: int | None = None,  # tổng dung lượng file của lượt (payload)
    error_code: str | None = None,
    created_at: datetime | None = None,
    experience: Experience = "autofill",
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
        # v2 giữ dossier_id để một lượt tách tab tạo đúng nhiều hồ sơ; lượt thường trên dashboard
        # vẫn được gom theo tập tên file để tương thích tiêu chí thống kê cũ.
        "stats_version": stats_version,
        "dossier_ids": dossier_ids or [],
        "key_fields_total": key_fields_total,
        "key_fields_filled": key_fields_filled,
        "stats": stats,  # thời gian OCR/LLM/tổng (ms) — hiển thị ở drawer chi tiết trace
        "total_bytes": total_bytes,  # dung lượng hồ sơ (payload) của lượt
        "procedure": procedure,
        "procedure_label": procedure_label,
        "ocr_provider": ocr_provider,  # "tiengnoi" (DOCX có thể kèm nhãn nguồn)
        "ocr_label": ocr_label(ocr_provider),
        "ocr_text": ocr_text or "",
        "llm_output": llm_output,
        "fields_count": fields_count,
        "status": status,
        "error_code": error_code,
        # Hai extension dùng chung collection; field này là khóa phân nguồn duy nhất cho
        # dashboard/báo cáo. Không suy luận từ username/kind vì các giá trị đó có thể trùng.
        "experience": experience,
        "created_at": created_at or datetime.now(timezone.utc),
    }
    try:
        res = await get_db().traces.insert_one(doc)
        return str(res.inserted_id)
    except Exception:  # noqa: BLE001 — trace không được phép làm hỏng request
        return None


async def set_report(request_id: str, kind: str, report: dict) -> None:
    """Handfree báo kết quả thao tác DOM thật để gắn vào đúng trace process/attach."""
    await get_db().traces.update_one(
        {"request_id": request_id, "kind": kind, "experience": "handfree"},
        {"$set": {"report": report}},
    )


def _build_query(
    *,
    user_id: str | None,
    procedure: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    request_id: str | None = None,
) -> dict:
    query: dict = {}
    # Mã hỗ trợ: tìm GẦN ĐÚNG (CHỨA chuỗi), không phân biệt hoa/thường → cán bộ gõ 1 phần mã
    # (hoặc dán dư/thiếu ký tự) vẫn ra. Có mã thì bỏ qua các bộ lọc khác cho tiện tra.
    # re.escape để ký tự đặc biệt không phá regex; unanchored nên không dùng index (tra tay, chấp nhận).
    code = (request_id or "").strip()
    if code:
        query["request_id"] = {"$regex": re.escape(code), "$options": "i"}
        return query
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


def with_experience(query: dict, experience: Experience | None) -> dict:
    """Ghép bộ lọc nguồn mà vẫn đọc đúng dữ liệu Auto Fill legacy chưa backfill.

    Handfree chỉ nhận document được gắn rõ ``handfree``. Document thiếu field thuộc DB
    Auto Fill lịch sử nên tạm được coi là ``autofill``; script backfill sẽ chuẩn hóa sau.
    """
    if experience is None:
        return query
    if experience == "handfree":
        return {**query, "experience": "handfree"}
    source_filter = {
        "$or": [
            {"experience": "autofill"},
            {"experience": {"$exists": False}},
            {"experience": None},
        ]
    }
    return {"$and": [query, source_filter]} if query else source_filter


async def list_traces(
    *,
    user_id: str | None = None,
    procedure: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    request_id: str | None = None,
    experience: Experience | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    db = get_db()
    query = with_experience(_build_query(
        user_id=user_id, procedure=procedure, date_from=date_from, date_to=date_to,
        request_id=request_id,
    ), experience)
    total = await db.traces.count_documents(query)
    # Danh sách: không trả ocr_text/llm_output (nặng) — chỉ trả khi xem chi tiết.
    projection = {"ocr_text": 0, "llm_output": 0}
    cursor = (
        db.traces.find(query, projection)
        .sort("created_at", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    docs = await cursor.to_list(length=limit)
    await _apply_current_account_names(db, docs)
    items = [_serialize(d) for d in docs]
    return {"items": items, "total": total}


async def get_trace(trace_id: str) -> dict | None:
    try:
        oid = ObjectId(trace_id)
    except Exception:  # noqa: BLE001
        return None
    db = get_db()
    doc = await db.traces.find_one({"_id": oid})
    if doc:
        await _apply_current_account_names(db, [doc])
    return _serialize(doc) if doc else None


async def facets(experience: Experience | None = None) -> dict:
    """Giá trị phục vụ bộ lọc: danh sách phường (user) và thủ tục đã xuất hiện trong traces."""
    db = get_db()
    source_match = [{"$match": with_experience({}, experience)}] if experience else []
    users = await db.traces.aggregate([*source_match,
        {"$group": {"_id": "$user_id", "username": {"$first": "$username"},
                    "name": {"$first": "$name"}}},
        {"$sort": {"name": 1}},
    ]).to_list(length=500)
    facet_users = [
        {"user_id": user["_id"], "username": user.get("username"), "name": user.get("name")}
        for user in users
    ]
    await _apply_current_account_names(db, facet_users)
    facet_users.sort(key=lambda user: str(user.get("name") or "").casefold())
    procedures = await db.traces.aggregate([*source_match,
        {"$group": {"_id": "$procedure", "label": {"$first": "$procedure_label"}}},
        {"$sort": {"label": 1}},
    ]).to_list(length=200)
    return {
        "users": [
            {"userId": user["user_id"], "username": user.get("username"),
             "name": user.get("name")}
            for user in facet_users
        ],
        "procedures": [
            {"key": p["_id"], "label": p.get("label")} for p in procedures
        ],
    }


def _stats_pipeline(query: dict) -> list[dict]:
    """Aggregation chỉ trả các bucket nhỏ, không kéo toàn bộ trace về Python.

    Lượt không tách được gom trước theo tập tên file duy nhất; Python chỉ phải so sánh các tập
    duy nhất để khôi phục tiêu chí cũ (tập bằng nhau hoặc là tập con). Lượt tách tab vẫn dùng
    dossier_ids để giữ đúng một hồ sơ cho mỗi tab.
    """
    exact = {
        "$and": [
            {"$gte": [{"$ifNull": ["$stats_version", 0]}, 2]},
            {"$gt": [{"$size": {"$ifNull": ["$dossier_ids", []]}}, 0]},
        ]
    }
    identity_text = {
        "$concat": [
            {"$ifNull": ["$$attachment.name", ""]}, " ",
            {"$ifNull": ["$$attachment.role", ""]},
        ]
    }
    legacy_split_count = {
        "$max": [
            1,
            {
                "$size": {
                    "$filter": {
                        "input": {"$ifNull": ["$attachments", []]},
                        "as": "attachment",
                        "cond": {
                            "$or": [
                                {"$ne": ["$procedure", "chung-thuc-chu-ky"]},
                                {
                                    "$not": [
                                        {
                                            "$regexMatch": {
                                                "input": identity_text,
                                                "regex": (
                                                    "cccd|căn\\s*cước|can\\s*cuoc|"
                                                    "chứng\\s*minh|chung\\s*minh|"
                                                    "hộ\\s*chiếu|ho\\s*chieu|passport|giấy\\s*tờ\\s*tùy\\s*thân"
                                                ),
                                                "options": "i",
                                            }
                                        }
                                    ]
                                },
                            ]
                        },
                    }
                }
            },
        ]
    }
    raw_attachment_name = {
        "$toLower": {
            "$convert": {
                "input": {"$ifNull": ["$$attachment.name", ""]},
                "to": "string",
                "onError": "",
                "onNull": "",
            }
        }
    }
    # Tương đương Python: " ".join(name.split()).lower(). Mongo chỉ trả mỗi tập tên file
    # một lần nên retry trùng hoàn toàn không làm phình dữ liệu đưa về ứng dụng.
    normalized_attachment_name = {
        "$reduce": {
            "input": {
                "$map": {
                    "input": {"$regexFindAll": {"input": raw_attachment_name, "regex": r"\S+"}},
                    "as": "token",
                    "in": "$$token.match",
                }
            },
            "initialValue": "",
            "in": {
                "$concat": [
                    "$$value",
                    {"$cond": [{"$eq": ["$$value", ""]}, "", " "]},
                    "$$this",
                ]
            },
        }
    }
    def attachment_set(value_expression: dict) -> dict:
        return {
            "$sortArray": {
                "input": {
                    "$setUnion": [
                        {
                            "$filter": {
                                "input": {
                                    "$map": {
                                        "input": {"$ifNull": ["$attachments", []]},
                                        "as": "attachment",
                                        "in": value_expression,
                                    }
                                },
                                "as": "name",
                                "cond": {"$ne": ["$$name", ""]},
                            }
                        },
                        [],
                    ]
                },
                "sortBy": 1,
            }
        }

    attachment_name_set = attachment_set(normalized_attachment_name)

    def empty_id(file_set_field: str) -> dict:
        return {
            "$cond": [
                {"$gt": [{"$size": file_set_field}, 0]},
                None,
                {
                    "$cond": [
                        "$_stats_exact",
                        {"$arrayElemAt": ["$dossier_ids", 0]},
                        "$_stats_request_id",
                    ]
                },
            ]
        }

    return [
        {"$match": query},
        {
            "$set": {
                "_stats_exact": exact,
                "_stats_request_id": {"$ifNull": ["$request_id", {"$toString": "$_id"}]},
                "_stats_user_id": {"$ifNull": ["$user_id", "—"]},
                "_stats_procedure": {"$ifNull": ["$procedure", "—"]},
                "_stats_name": {"$ifNull": ["$name", {"$ifNull": ["$username", "—"]}]},
                "_stats_label": {"$ifNull": ["$procedure_label", {"$ifNull": ["$procedure", "—"]}]},
                "_stats_is_split": {"$eq": ["$split", True]},
            }
        },
        {
            "$set": {
                "_stats_legacy_count": {
                    "$cond": [{"$eq": ["$split", True]}, legacy_split_count, 1]
                }
            }
        },
        {
            "$set": {
                "_stats_dossier_ids": {
                    "$cond": [
                        "$_stats_exact",
                        "$dossier_ids",
                        {
                            "$map": {
                                "input": {"$range": [0, "$_stats_legacy_count"]},
                                "as": "index",
                                "in": {
                                    "$concat": [
                                        "$_stats_request_id", ":legacy:", {"$toString": "$$index"}
                                    ]
                                },
                            }
                        },
                    ]
                },
            }
        },
        {
            "$facet": {
                "nonSplitFileSets": [
                    {
                        "$match": {
                            "_stats_is_split": False,
                            "$or": [
                                {"created_at": {"$lt": _STEM_RULE_CUTOFF}},
                                {"created_at": {"$exists": False}},
                                {"created_at": None},
                            ],
                        }
                    },
                    {"$set": {"_stats_file_set": attachment_name_set}},
                    {"$set": {"_stats_empty_id": empty_id("$_stats_file_set")}},
                    {
                        "$group": {
                            "_id": {
                                "userId": "$_stats_user_id",
                                "procedure": "$_stats_procedure",
                                "fileSet": "$_stats_file_set",
                                "emptyId": "$_stats_empty_id",
                            },
                            "name": {"$first": "$_stats_name"},
                            "label": {"$first": "$_stats_label"},
                            "requests": {"$sum": 1},
                            "estimated": {"$max": {"$cond": ["$_stats_exact", 0, 1]}},
                        }
                    },
                ],
                "stemNonSplitFileSets": [
                    {
                        "$match": {
                            "_stats_is_split": False,
                            "created_at": {"$gte": _STEM_RULE_CUTOFF},
                        }
                    },
                    # Mongo chỉ gom theo tập tên đầy đủ. Bỏ đuôi ở Python trên các bucket
                    # đã rút gọn để tương thích cả MongoDB không có `$regexReplace`.
                    {"$set": {"_stats_file_set": attachment_name_set}},
                    {"$set": {"_stats_empty_id": empty_id("$_stats_file_set")}},
                    {
                        "$group": {
                            "_id": {
                                "userId": "$_stats_user_id",
                                "procedure": "$_stats_procedure",
                                "fileSet": "$_stats_file_set",
                                "emptyId": "$_stats_empty_id",
                            },
                            "name": {"$first": "$_stats_name"},
                            "label": {"$first": "$_stats_label"},
                            "requests": {"$sum": 1},
                            "estimated": {"$max": {"$cond": ["$_stats_exact", 0, 1]}},
                        }
                    },
                ],
                "splitBuckets": [
                    {"$match": {"_stats_is_split": True}},
                    {"$unwind": "$_stats_dossier_ids"},
                    {
                        "$group": {
                            "_id": {
                                "userId": "$_stats_user_id",
                                "procedure": "$_stats_procedure",
                                "dossierId": "$_stats_dossier_ids",
                            },
                            "name": {"$first": "$_stats_name"},
                            "label": {"$first": "$_stats_label"},
                            "estimated": {"$max": {"$cond": ["$_stats_exact", 0, 1]}},
                        }
                    },
                    {
                        "$group": {
                            "_id": {
                                "userId": "$_id.userId",
                                "procedure": "$_id.procedure",
                            },
                            "name": {"$first": "$name"},
                            "label": {"$first": "$label"},
                            "count": {"$sum": 1},
                            "estimatedCount": {"$sum": "$estimated"},
                        }
                    },
                ],
                "requests": [
                    {
                        "$group": {
                            "_id": {
                                "userId": "$_stats_user_id",
                                "procedure": "$_stats_procedure",
                                "requestId": "$_stats_request_id",
                            },
                            "estimated": {"$max": {"$cond": ["$_stats_exact", 0, 1]}},
                        }
                    },
                    {
                        "$group": {
                            "_id": {
                                "userId": "$_id.userId",
                                "procedure": "$_id.procedure",
                            },
                            "requests": {"$sum": 1},
                            "estimatedRequests": {"$sum": "$estimated"},
                        }
                    },
                ],
                "documents": [
                    {"$match": {"_stats_exact": True}},
                    {"$unwind": "$attachments"},
                    {"$match": {"attachments.sha256": {"$type": "string", "$ne": ""}}},
                    {
                        "$group": {
                            "_id": "$attachments.sha256",
                            "uses": {"$sum": {"$max": [1, {"$ifNull": ["$attachments.uses", 1]}]}},
                        }
                    },
                    {"$group": {"_id": None, "unique": {"$sum": 1}, "uses": {"$sum": "$uses"}}},
                ],
            }
        },
    ]


def _format_stats_facets(facets: dict) -> dict:
    request_by_bucket = {
        (item["_id"]["userId"], item["_id"]["procedure"]): item
        for item in facets.get("requests", [])
    }
    # Giữ đọc được shape `buckets` cũ để không làm vỡ caller/test đang truyền dữ liệu đã tổng hợp.
    bucket_map: dict[tuple[str, str], dict] = {}
    for item in facets.get("buckets", []):
        key = (item["_id"]["userId"], item["_id"]["procedure"])
        bucket_map[key] = dict(item)

    def add_file_set_rows(rows: list[dict], *, strip_suffix: bool = False) -> None:
        file_sets_by_bucket: dict[tuple[str, str], list[frozenset[str]]] = {}
        for item in rows:
            uid = item["_id"]["userId"]
            procedure = item["_id"]["procedure"]
            key = (uid, procedure)
            normalized_names: list[str] = []
            for value in item["_id"].get("fileSet") or []:
                name = str(value or "")
                if strip_suffix:
                    name = _FILE_SUFFIX_RE.sub("", name)
                if name:
                    normalized_names.append(name)
            file_set = frozenset(normalized_names)
            file_sets_by_bucket.setdefault(key, []).append(file_set)
            bucket_map.setdefault(key, {
                "_id": {"userId": uid, "procedure": procedure},
                "name": item.get("name"),
                "label": item.get("label"),
                "count": 0,
                "estimatedCount": 0,
            })

        for key, file_sets in file_sets_by_bucket.items():
            count = count_distinct_attachment_sets(file_sets)
            bucket_map[key]["count"] = int(bucket_map[key].get("count") or 0) + count
            bucket_map[key]["estimatedCount"] = int(
                bucket_map[key].get("estimatedCount") or 0
            ) + count

    # Hai vùng thời gian phải đếm riêng để không gộp hồ sơ xuyên qua mốc migration.
    add_file_set_rows(facets.get("nonSplitFileSets", []))
    add_file_set_rows(facets.get("stemNonSplitFileSets", []), strip_suffix=True)

    for item in facets.get("splitBuckets", []):
        uid = item["_id"]["userId"]
        procedure = item["_id"]["procedure"]
        key = (uid, procedure)
        bucket = bucket_map.setdefault(key, {
            "_id": {"userId": uid, "procedure": procedure},
            "name": item.get("name"),
            "label": item.get("label"),
            "count": 0,
            "estimatedCount": 0,
        })
        bucket["count"] += int(item.get("count") or 0)
        bucket["estimatedCount"] += int(item.get("estimatedCount") or 0)

    wards: dict[str, dict] = {}
    procedures: dict[str, dict] = {}
    total_dossiers = 0
    estimated_dossiers = 0

    for item in bucket_map.values():
        uid = item["_id"]["userId"]
        procedure = item["_id"]["procedure"]
        count = int(item.get("count") or 0)
        estimated = int(item.get("estimatedCount") or 0)
        request_item = request_by_bucket.get((uid, procedure), {})
        requests = int(request_item.get("requests") or 0)
        ward = wards.setdefault(uid, {
            "userId": uid,
            "name": item.get("name") or uid,
            "total": 0,
            "exact": 0,
            "estimated": 0,
            "requests": 0,
            "procedures": [],
        })
        ward["total"] += count
        ward["exact"] += count - estimated
        ward["estimated"] += estimated
        ward["requests"] += requests
        ward["procedures"].append({
            "key": procedure,
            "label": item.get("label") or procedure,
            "count": count,
            "exact": count - estimated,
            "estimated": estimated,
            "requests": requests,
        })
        proc = procedures.setdefault(procedure, {
            "key": procedure,
            "label": item.get("label") or procedure,
            "count": 0,
            "requests": 0,
            "exact": 0,
            "estimated": 0,
        })
        proc["count"] += count
        proc["requests"] += requests
        proc["exact"] += count - estimated
        proc["estimated"] += estimated
        total_dossiers += count
        estimated_dossiers += estimated

    for ward in wards.values():
        ward["procedures"].sort(key=lambda proc: (-proc["count"], proc["label"]))

    total_requests = sum(int(item.get("requests") or 0) for item in facets.get("requests", []))
    estimated_requests = sum(
        int(item.get("estimatedRequests") or 0) for item in facets.get("requests", [])
    )
    documents = (facets.get("documents") or [{}])[0]
    unique_documents = int(documents.get("unique") or 0)
    total_document_uses = int(documents.get("uses") or 0)
    exact_dossiers = total_dossiers - estimated_dossiers
    if estimated_dossiers == 0:
        quality = "exact"
    elif exact_dossiers == 0:
        quality = "estimated"
    else:
        quality = "mixed"

    return {
        "wards": sorted(wards.values(), key=lambda ward: (-ward["total"], ward["name"])),
        "procedures": sorted(procedures.values(), key=lambda proc: (-proc["count"], proc["label"])),
        "totalDossiers": total_dossiers,
        "exactDossiers": exact_dossiers,
        "estimatedDossiers": estimated_dossiers,
        "dataQuality": quality,
        "totalRequests": total_requests,
        "estimatedRequests": estimated_requests,
        "uniqueDocuments": unique_documents,
        "totalDocumentUses": total_document_uses,
        "reusedDocumentUses": max(total_document_uses - unique_documents, 0),
        "documentDataQuality": "exact" if estimated_requests == 0 else "partial",
    }


async def stats(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    scope: str = "all",
    experience: Experience | None = "autofill",
) -> dict:
    """Thống kê tên đầy đủ trước mốc, tên bỏ đuôi từ mốc; date_to là mốc loại trừ."""
    db = get_db()
    accounts = [account async for account in db.users.find({}, {"role": 1})]
    roles_by_user, included_user_ids = _stats_account_context(accounts, scope)
    query = _build_query(user_id=None, procedure=None, date_from=date_from, date_to=None)
    if scope == "official":
        query["user_id"] = {"$in": included_user_ids}
    if date_to:
        query.setdefault("created_at", {})["$lt"] = date_to
    query = with_experience(query, experience)
    rows = await db.traces.aggregate(_stats_pipeline(query), allowDiskUse=True).to_list(length=1)
    result = _format_stats_facets(rows[0] if rows else {})
    for ward in result["wards"]:
        ward["role"] = roles_by_user.get(ward["userId"])
    included_roles = list(
        sorted(OFFICIAL_ACCOUNT_ROLES) if scope == "official" else _ALL_STATS_ROLES
    )
    result.update({
        "scope": scope,
        "source": experience or "all",
        "accountCount": len(included_user_ids),
        "includedRoles": included_roles,
    })
    return result


async def stats_by_user_ids(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    experience: Experience = "autofill",
) -> dict:
    """Tổng hợp đúng tiêu chí dashboard cho một tập tài khoản xác định.

    Module báo cáo truyền danh sách ``user_id`` hiện hành; không fallback theo tên xã/tài khoản
    vì khớp chuỗi có thể kéo nhầm trace của đơn vị khác vào file chính thức.
    """
    unique_ids = list(dict.fromkeys(str(value) for value in user_ids if value))
    if not unique_ids:
        return _format_stats_facets({})
    query = {
        "user_id": {"$in": unique_ids},
        "created_at": {"$gte": date_from, "$lt": date_to},
    }
    query = with_experience(query, experience)
    rows = await get_db().traces.aggregate(
        _stats_pipeline(query), allowDiskUse=True
    ).to_list(length=1)
    return _format_stats_facets(rows[0] if rows else {})


def _daily_stats_pipeline(query: dict) -> list[dict]:
    """Giữ nguyên rule gom hồ sơ hiện tại nhưng lấy ngày phát sinh đầu tiên.

    Tái sử dụng chính các stage chuẩn hóa của dashboard để hai báo cáo không trôi
    tiêu chí theo thời gian. Facet theo ngày bỏ phần request/tài liệu không cần thiết,
    nên Mongo chỉ trả các tập file và dossier_id đã rút gọn.
    """
    base = _stats_pipeline(query)
    source_facets = base[-1]["$facet"]

    legacy = copy.deepcopy(source_facets["nonSplitFileSets"])
    legacy[-1]["$group"]["firstAt"] = {"$min": "$created_at"}

    stem = copy.deepcopy(source_facets["stemNonSplitFileSets"])
    stem[-1]["$group"]["firstAt"] = {"$min": "$created_at"}

    # Stage group đầu tiên đã khử trùng theo từng dossier_id; không gộp tiếp theo
    # user/procedure vì cần giữ ngày đầu của từng hồ sơ tách.
    split = copy.deepcopy(source_facets["splitBuckets"][:3])
    split[-1]["$group"]["firstAt"] = {"$min": "$created_at"}

    return [*base[:-1], {"$facet": {
        "nonSplitFileSets": legacy,
        "stemNonSplitFileSets": stem,
        "splitDossiers": split,
    }}]


def _format_daily_dossier_counts(facets: dict) -> list[dict]:
    counts: dict[tuple[str, str], int] = {}

    def add(user_id: str, created_at: datetime | None) -> None:
        if not isinstance(created_at, datetime):
            return
        # PyMongo có thể trả datetime UTC dạng naive tùy cấu hình codec.
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        date_key = created_at.astimezone(VIETNAM_TZ).strftime("%Y-%m-%d")
        key = (str(user_id or "—"), date_key)
        counts[key] = counts.get(key, 0) + 1

    def add_file_set_rows(rows: list[dict], *, strip_suffix: bool) -> None:
        by_bucket: dict[tuple[str, str], list[tuple[frozenset[str], datetime | None]]] = {}
        for item in rows:
            item_id = item.get("_id") or {}
            names: list[str] = []
            for value in item_id.get("fileSet") or []:
                name = str(value or "")
                if strip_suffix:
                    name = _FILE_SUFFIX_RE.sub("", name)
                if name:
                    names.append(name)
            by_bucket.setdefault(
                (str(item_id.get("userId") or "—"), str(item_id.get("procedure") or "—")),
                [],
            ).append((frozenset(names), item.get("firstAt")))

        for (user_id, _procedure), occurrences in by_bucket.items():
            non_empty: dict[frozenset[str], datetime | None] = {}
            for file_set, first_at in occurrences:
                if not file_set:
                    add(user_id, first_at)
                    continue
                previous = non_empty.get(file_set)
                if previous is None or (isinstance(first_at, datetime) and first_at < previous):
                    non_empty[file_set] = first_at

            file_sets = list(non_empty)
            parent = list(range(len(file_sets)))

            def find(index: int) -> int:
                while parent[index] != index:
                    parent[index] = parent[parent[index]]
                    index = parent[index]
                return index

            for left_index, left in enumerate(file_sets):
                for right_index in range(left_index + 1, len(file_sets)):
                    right = file_sets[right_index]
                    if left <= right or right <= left:
                        parent[find(left_index)] = find(right_index)

            earliest: dict[int, datetime | None] = {}
            for index, file_set in enumerate(file_sets):
                root = find(index)
                first_at = non_empty[file_set]
                previous = earliest.get(root)
                if previous is None or (isinstance(first_at, datetime) and first_at < previous):
                    earliest[root] = first_at
            for first_at in earliest.values():
                add(user_id, first_at)

    add_file_set_rows(facets.get("nonSplitFileSets", []), strip_suffix=False)
    add_file_set_rows(facets.get("stemNonSplitFileSets", []), strip_suffix=True)
    for item in facets.get("splitDossiers", []):
        add((item.get("_id") or {}).get("userId"), item.get("firstAt"))

    return [
        {"userId": user_id, "date": day, "count": count}
        for (user_id, day), count in sorted(counts.items())
    ]


async def daily_dossier_counts_by_user_ids(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    experience: Experience = "autofill",
) -> list[dict]:
    """Đếm hồ sơ theo ngày đầu phát sinh, không đếm thô từng trace."""
    unique_ids = list(dict.fromkeys(str(value) for value in user_ids if value))
    if not unique_ids:
        return []
    query = {
        "user_id": {"$in": unique_ids},
        "created_at": {"$gte": date_from, "$lt": date_to},
    }
    query = with_experience(query, experience)
    rows = await get_db().traces.aggregate(
        _daily_stats_pipeline(query), allowDiskUse=True
    ).to_list(length=1)
    return _format_daily_dossier_counts(rows[0] if rows else {})


async def list_dossier_log(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    procedure: str | None = None,
    skip: int = 0,
    limit: int = 20,
    experience: Experience = "autofill",
) -> dict:
    """Nhật ký hồ sơ cho bảng thống kê: mỗi trace = 1 dòng, KHÔNG PII (không tên/ocr/file).

    Khác list_traces (admin, kèm PII): chỉ trả metadata tối thiểu và khóa theo tập user_id của
    phạm vi. Mỗi lượt làm việc với Trợ lý (điền/đính kèm) là một dòng.
    """
    unique_ids = list(dict.fromkeys(str(value) for value in user_ids if value))
    if not unique_ids:
        return {"items": [], "total": 0}
    query: dict = {
        "user_id": {"$in": unique_ids},
        "created_at": {"$gte": date_from, "$lt": date_to},
    }
    if procedure:
        query["procedure"] = procedure
    query = with_experience(query, experience)
    db = get_db()
    total = await db.traces.count_documents(query)
    projection = {
        "_id": 0, "request_id": 1, "user_id": 1, "procedure": 1,
        "procedure_label": 1, "kind": 1, "created_at": 1,
    }
    # Trần cao để xuất Excel lấy được nhiều dòng; route /logs vẫn tự giới hạn pageSize <= 100.
    capped = max(min(limit, 100000), 1)
    cursor = (
        db.traces.find(query, projection)
        .sort("created_at", -1)
        .skip(max(skip, 0))
        .limit(capped)
    )
    items = []
    for doc in await cursor.to_list(length=capped):
        created = doc.get("created_at")
        if isinstance(created, datetime) and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        items.append({
            "requestId": doc.get("request_id"),
            "userId": str(doc.get("user_id") or ""),
            "procedure": doc.get("procedure"),
            "procedureLabel": doc.get("procedure_label"),
            "kind": doc.get("kind") or "autofill",
            "createdAt": created.isoformat() if isinstance(created, datetime) else None,
        })
    return {"items": items, "total": total}


async def daily_counts_by_user_ids(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    experience: Experience = "autofill",
) -> list[dict]:
    """Số LƯỢT xử lý (mỗi trace = 1 lượt /process) theo ngày cho một tập tài khoản.

    Dùng vẽ biểu đồ diễn biến theo thời gian trên dashboard phường. Gom ngày theo múi giờ
    Việt Nam để mốc trùng với cách hiển thị khoảng ngày. Khác "hồ sơ riêng biệt" (đã gộp
    trùng bộ file) — ở đây đếm thô từng lượt, nên nhãn FE ghi rõ "lượt xử lý".
    """
    unique_ids = list(dict.fromkeys(str(value) for value in user_ids if value))
    if not unique_ids:
        return []
    query = with_experience({
        "user_id": {"$in": unique_ids},
        "created_at": {"$gte": date_from, "$lt": date_to},
    }, experience)
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "+07:00"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = await get_db().traces.aggregate(pipeline, allowDiskUse=True).to_list(length=100000)
    return [{"date": row["_id"], "count": int(row["count"])} for row in rows if row.get("_id")]


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    created = doc.get("created_at")
    if isinstance(created, datetime):
        doc["created_at"] = created.astimezone(timezone.utc).isoformat()
    return doc
