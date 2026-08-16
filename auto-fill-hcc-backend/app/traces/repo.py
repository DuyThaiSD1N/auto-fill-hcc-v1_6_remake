"""Lưu & truy vấn trace mỗi lần gọi /process: tài khoản (phường), thủ tục, OCR text gộp, JSON LLM.

Collection: traces. Ghi best-effort (lỗi không được làm hỏng request /process).
"""
import re
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongo import get_db
from app.traces.metadata import count_distinct_attachment_sets
from app.users.roles import OFFICIAL_ACCOUNT_ROLES, normalized_role

# Nhãn hiển thị model OCR theo provider key.
_OCR_LABELS = {"raw": "RAW", "vintern": "Vintern", "gemini": "Gemini", "both": "BOTH",
               "tiengnoi": "vintern-v6"}
_ALL_STATS_ROLES = ("admin", "user", "commune", "province")


def ocr_label(provider: str | None) -> str:
    return _OCR_LABELS.get(provider or "", provider or "—")


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


async def list_traces(
    *,
    user_id: str | None = None,
    procedure: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    request_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    db = get_db()
    query = _build_query(
        user_id=user_id, procedure=procedure, date_from=date_from, date_to=date_to,
        request_id=request_id,
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
    attachment_name_set = {
        "$sortArray": {
            "input": {
                "$setUnion": [
                    {
                        "$filter": {
                            "input": {
                                "$map": {
                                    "input": {"$ifNull": ["$attachments", []]},
                                    "as": "attachment",
                                    "in": normalized_attachment_name,
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
                "_stats_file_set": attachment_name_set,
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
                "_stats_empty_id": {
                    "$cond": [
                        {"$gt": [{"$size": "$_stats_file_set"}, 0]},
                        None,
                        {
                            "$cond": [
                                "$_stats_exact",
                                {"$arrayElemAt": ["$dossier_ids", 0]},
                                "$_stats_request_id",
                            ]
                        },
                    ]
                },
            }
        },
        {
            "$facet": {
                "nonSplitFileSets": [
                    {"$match": {"_stats_is_split": False}},
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

    file_sets_by_bucket: dict[tuple[str, str], list[frozenset[str]]] = {}
    for item in facets.get("nonSplitFileSets", []):
        uid = item["_id"]["userId"]
        procedure = item["_id"]["procedure"]
        key = (uid, procedure)
        file_set = frozenset(item["_id"].get("fileSet") or [])
        # Mongo đã gom fileSet trùng nhau. Riêng tập rỗng dùng emptyId để mỗi request cũ
        # vẫn là một hồ sơ; cùng dossier_id v2 chỉ xuất hiện một lần.
        file_sets_by_bucket.setdefault(key, []).append(file_set)
        bucket = bucket_map.setdefault(key, {
            "_id": {"userId": uid, "procedure": procedure},
            "name": item.get("name"),
            "label": item.get("label"),
            "count": 0,
            "estimatedCount": 0,
        })

    for key, file_sets in file_sets_by_bucket.items():
        count = count_distinct_attachment_sets(file_sets)
        bucket_map[key]["count"] = int(bucket_map[key].get("count") or 0) + count
        # Tiêu chí tên file là suy luận nghiệp vụ; trường này giữ compatibility API, FE chỉ hiện số.
        bucket_map[key]["estimatedCount"] = int(
            bucket_map[key].get("estimatedCount") or 0
        ) + count

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
) -> dict:
    """Thống kê theo bộ file như tiêu chí cũ; date_to là mốc loại trừ của khoảng nửa mở."""
    db = get_db()
    accounts = [account async for account in db.users.find({}, {"role": 1})]
    roles_by_user, included_user_ids = _stats_account_context(accounts, scope)
    query = _build_query(user_id=None, procedure=None, date_from=date_from, date_to=None)
    if scope == "official":
        query["user_id"] = {"$in": included_user_ids}
    if date_to:
        query.setdefault("created_at", {})["$lt"] = date_to
    rows = await db.traces.aggregate(_stats_pipeline(query), allowDiskUse=True).to_list(length=1)
    result = _format_stats_facets(rows[0] if rows else {})
    for ward in result["wards"]:
        ward["role"] = roles_by_user.get(ward["userId"])
    included_roles = list(
        sorted(OFFICIAL_ACCOUNT_ROLES) if scope == "official" else _ALL_STATS_ROLES
    )
    result.update({
        "scope": scope,
        "accountCount": len(included_user_ids),
        "includedRoles": included_roles,
    })
    return result


async def stats_by_user_ids(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
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
    rows = await get_db().traces.aggregate(
        _stats_pipeline(query), allowDiskUse=True
    ).to_list(length=1)
    return _format_stats_facets(rows[0] if rows else {})


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    created = doc.get("created_at")
    if isinstance(created, datetime):
        doc["created_at"] = created.astimezone(timezone.utc).isoformat()
    return doc
