"""Dựng pipeline Mongo cho web Monitor — hàm thuần (không I/O) để test được không cần Mongo.

Danh sách "lượt xử lý" = ``traces`` (lịch sử đầy đủ) GỘP các lượt chỉ có ở ``trace_steps``
(``steps_only``: phân loại, chủ hồ sơ, Auto Fill hỏng) qua ``$unionWith`` — hai nguồn được chiếu
về CÙNG một shape nhẹ trước khi lọc/sắp/phân trang.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# Trường nhẹ của timing cho danh sách/biểu đồ — không kéo ocr_text/llm_output/output nặng.
_TIMING_FIELDS = ("wait", "wall", "g", "other", "persist", "persist_wait", "n", "f")


def _range(date_from: datetime | None, date_to: datetime | None) -> dict | None:
    if not (date_from or date_to):
        return None
    rng: dict = {}
    if date_from:
        rng["$gte"] = date_from
    if date_to:
        rng["$lt"] = date_to  # parse_stats_range trả khoảng nửa mở [đầu ngày đầu, đầu ngày sau ngày cuối)
    return rng


def _timing_projection(prefix: str) -> dict:
    return {key: f"${prefix}.{key}" for key in _TIMING_FIELDS}


def runs_base_pipeline(
    *,
    user_id: str | None = None,
    procedure: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Gộp traces + trace_steps(steps_only) về một shape. Lọc theo trường có index TRƯỚC khi chiếu."""
    rng = _range(date_from, date_to)
    trace_match: dict = {}
    steps_match: dict = {"steps_only": True}
    if rng:
        trace_match["created_at"] = rng
        steps_match["created_at"] = rng
    if user_id:
        trace_match["user_id"] = user_id
        steps_match["meta.user_id"] = user_id
    if procedure:
        trace_match["procedure"] = procedure
        steps_match["meta.procedure"] = procedure

    trace_project = {
        "_id": 0,
        "id": {"$toString": "$_id"},
        "request_id": "$request_id",
        "kind": {"$ifNull": ["$kind", "autofill"]},
        # Trace Auto Fill lịch sử chưa backfill experience → coi là autofill (giống with_experience).
        "experience": {"$ifNull": ["$experience", "autofill"]},
        "outcome": {"$ifNull": [
            "$outcome", {"$cond": [{"$eq": ["$status", "error"]}, "error", "ok"]},
        ]},
        "created_at": "$created_at",
        "user_id": "$user_id",
        "username": "$username",
        "name": "$name",
        "procedure": "$procedure",
        "procedure_label": "$procedure_label",
        "applicant_name": "$applicant_name",
        "dossier_id": "$dossier_id",
        "error": "$error_code",
        "timing": _timing_projection("timing"),
        # Lượt trước khi có timing chỉ còn tổng OCR+LLM → vẫn sắp/lọc được theo thời gian.
        "wait_ms": {"$ifNull": ["$timing.wait", "$stats.total_latency_ms"]},
        "legacy": {"$eq": [{"$type": "$timing"}, "missing"]},
        "files": {"$size": {"$ifNull": ["$attachments", []]}},
        "total_bytes": "$total_bytes",
        "key_fields_total": "$key_fields_total",
        "key_fields_filled": "$key_fields_filled",
        "source": {"$literal": "trace"},
    }
    steps_project = {
        "_id": 0,
        "id": {"$literal": None},
        "request_id": "$request_id",
        "kind": "$kind",
        "experience": "$experience",
        "outcome": "$outcome",
        "created_at": "$created_at",
        "user_id": "$meta.user_id",
        "username": "$meta.username",
        "name": "$meta.name",
        "procedure": "$meta.procedure",
        "procedure_label": "$meta.procedure_label",
        "applicant_name": {"$literal": None},
        "dossier_id": "$meta.dossier_id",
        "error": {"$arrayElemAt": ["$errors", 0]},
        "timing": _timing_projection("timing"),
        "wait_ms": "$timing.wait",
        "legacy": {"$literal": False},
        "files": "$meta.files",
        "total_bytes": "$timing.n.bytes",
        "key_fields_total": {"$literal": None},
        "key_fields_filled": {"$literal": None},
        "source": {"$literal": "steps"},
    }
    return [
        {"$match": trace_match},
        {"$project": trace_project},
        {"$unionWith": {"coll": "trace_steps", "pipeline": [
            {"$match": steps_match},
            {"$project": steps_project},
        ]}},
    ]


def runs_filter_stage(
    *,
    q: str | None = None,
    source: str | None = None,
    kind: str | None = None,
    outcome: str | None = None,
    min_wait_ms: int | None = None,
    max_wait_ms: int | None = None,
    metric: str = "wait",
) -> dict:
    """Lọc SAU khi gộp (các trường đã cùng tên ở hai nguồn)."""
    cond: dict[str, Any] = {}
    if source and source != "all":
        cond["experience"] = source
    if kind and kind != "all":
        cond["kind"] = kind
    if outcome == "issues":
        cond["outcome"] = {"$in": ["partial", "error"]}
    elif outcome and outcome != "all":
        cond["outcome"] = outcome
    # Khoảng thời gian áp lên chỉ số đang xem: người dùng chờ (wait_ms — gồm cả lượt cũ) / OCR / LLM.
    field, real, _ = METRICS.get(metric, METRICS["wait"])
    field = "wait_ms" if metric == "wait" else field
    wait: dict = {}
    if min_wait_ms:
        wait["$gte"] = int(min_wait_ms)
    if max_wait_ms:
        wait["$lt"] = int(max_wait_ms)
    if wait:
        cond[field] = wait
    if real and (wait or metric != "wait"):
        cond.update(real)
    text = (q or "").strip()
    if text:
        pattern = {"$regex": re.escape(text), "$options": "i"}
        cond["$or"] = [
            {field: pattern}
            for field in ("request_id", "dossier_id", "applicant_name", "name", "username",
                          "procedure_label", "procedure")
        ]
    return {"$match": cond}


def runs_list_pipeline(*, sort: str = "new", skip: int = 0, limit: int = 50, **filters) -> list[dict]:
    base_keys = ("user_id", "procedure", "date_from", "date_to")
    base = runs_base_pipeline(**{k: filters.get(k) for k in base_keys})
    post = runs_filter_stage(**{k: v for k, v in filters.items() if k not in base_keys})
    metric = filters.get("metric") or "wait"
    slow_field = "wait_ms" if metric == "wait" else METRICS.get(metric, METRICS["wait"])[0]
    order = {slow_field: -1, "created_at": -1} if sort == "slow" else {"created_at": -1}
    return [
        *base,
        post,
        {"$facet": {
            "items": [{"$sort": order}, {"$skip": max(skip, 0)}, {"$limit": max(min(limit, 200), 1)}],
            "total": [{"$count": "n"}],
        }},
    ]


# Chỉ số thời gian của Tổng quan: (đường dẫn field sau khi gộp, điều kiện "lượt có chạy thật", mốc
# phân bố ms). OCR chỉ tính lượt có gọi OCR thật — lượt dùng lại kết quả OCR cũ có OCR ≈ 0 s sẽ kéo
# số liệu xuống sai; LLM chỉ tính lượt có gọi LLM. Mốc OCR/LLM ngắn hơn vì hai bước này ngắn hơn cả lượt.
METRICS: dict[str, tuple[str, dict | None, tuple[int, int, int]]] = {
    "wait": ("timing.wait", None, (5000, 10000, 20000)),
    "ocr": ("timing.g.ocr", {"timing.n.ocr_miss": {"$gt": 0}}, (2000, 5000, 10000)),
    "llm": ("timing.g.llm", {"timing.n.llm_calls": {"$gt": 0}}, (3000, 6000, 12000)),
}


def _bucket(field: str, lo: int | None, hi: int | None) -> dict:
    conds = []
    if lo is not None:
        conds.append({"$gte": [f"${field}", lo]})
    if hi is not None:
        conds.append({"$lt": [f"${field}", hi]})
    return {"$sum": {"$cond": [{"$and": conds}, 1, 0]}}


def latency_group_pipeline(*, group: str, metric: str = "wait", **filters) -> list[dict]:
    """Chỉ số thời gian (chờ / OCR / LLM) trung bình / nhanh nhất / lâu nhất (kèm mã lượt) + trung bình
    từng nhóm công đoạn + số lượt theo mốc; gom theo ngày / thủ tục / đơn vị / tất cả.

    Dùng trung bình + cực trị (không phân vị) để người đọc không chuyên hiểu được; đuôi chậm thể
    hiện bằng phân bố theo mốc. Không cần $percentile → chạy được trên mọi phiên bản Mongo.
    """
    field, real, bounds = METRICS.get(metric, METRICS["wait"])
    base_keys = ("user_id", "procedure", "date_from", "date_to")
    base = runs_base_pipeline(**{k: filters.get(k) for k in base_keys})
    post = runs_filter_stage(**{k: v for k, v in filters.items() if k not in base_keys})
    if group == "day":
        key: Any = {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "+07:00"}}
    elif group == "procedure":
        key = "$procedure"
    elif group == "unit":
        key = "$user_id"
    else:
        key = None
    run_ref = {"request_id": "$request_id", "kind": "$kind", "value": f"${field}"}
    b1, b2, b3 = bounds
    accumulators: dict[str, Any] = {
        "n": {"$sum": 1},
        "avg": {"$avg": f"${field}"},
        # Đã sắp theo chỉ số tăng dần trước $group → $first = nhanh nhất, $last = lâu nhất.
        "fastest": {"$first": run_ref},
        "slowest": {"$last": run_ref},
        "pre": {"$avg": "$timing.g.pre"},
        "ocr": {"$avg": "$timing.g.ocr"},
        "llm": {"$avg": "$timing.g.llm"},
        "post": {"$avg": "$timing.g.post"},
        "other": {"$avg": "$timing.other"},
        "persist_wait": {"$avg": "$timing.persist_wait"},
        "b0": _bucket(field, None, b1),
        "b1": _bucket(field, b1, b2),
        "b2": _bucket(field, b2, b3),
        "b3": _bucket(field, b3, None),
        "llm_calls": {"$avg": "$timing.n.llm_calls"},
        "tok_out": {"$avg": "$timing.n.tok_out"},
        "ocr_hit": {"$sum": {"$ifNull": ["$timing.n.ocr_hit", 0]}},
        "ocr_miss": {"$sum": {"$ifNull": ["$timing.n.ocr_miss", 0]}},
        "errors": {"$sum": {"$cond": [{"$eq": ["$outcome", "error"]}, 1, 0]}},
        "partial": {"$sum": {"$cond": [{"$eq": ["$outcome", "partial"]}, 1, 0]}},
        "label": {"$first": {"$ifNull": ["$procedure_label", "$name"]}},
        "name": {"$first": "$name"},
    }
    return [
        *base,
        post,
        # Chỉ lượt đã có timing chi tiết (sau khi bật bộ ghi) + có chạy thật bước của chỉ số.
        {"$match": {"timing.wait": {"$type": "number"}, **(real or {})}},
        {"$sort": {field: 1}},
        {"$group": {"_id": key, **accumulators}},
        {"$sort": {"_id": 1} if group == "day" else {"n": -1}},
        {"$limit": 500},
    ]

