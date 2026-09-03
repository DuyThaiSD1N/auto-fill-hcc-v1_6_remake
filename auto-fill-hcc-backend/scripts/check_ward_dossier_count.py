"""Đối chiếu cách đếm hồ sơ của một phường trên dữ liệu trace production.

Script chỉ ĐỌC MongoDB. Mặc định kiểm tra đúng tên ``Phường Bắc Giang`` và in:

1. Số hồ sơ theo tiêu chí dashboard hiện tại.
2. Số theo rule dashboard hiện tại nhưng tên file được bỏ đuôi.
3. Số thử nghiệm theo ``dossier_id`` và từng file ``tên bỏ đuôi + SHA/OCR``;
   chỉ fallback theo tên khi thiếu dữ liệu nội dung.

Chạy trong thư mục ``auto-fill-hcc-backend``::

    python -m scripts.check_ward_dossier_count
    python -m scripts.check_ward_dossier_count --from 2026-08-01 --to 2026-08-25
    python -m scripts.check_ward_dossier_count --procedure trich-luc-ks

Trong Docker production::

    docker compose -f compose.prod.yml exec app \
      python -m scripts.check_ward_dossier_count

``--to`` tính hết ngày được nhập theo giờ Việt Nam. Phép đếm thử nghiệm cho phép tập file
cũ là tập con của lượt bổ sung sau; không dùng thời gian làm điều kiện chia hồ sơ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable

from pymongo import MongoClient

from app.config import settings
from app.traces.metadata import count_distinct_attachment_sets, legacy_dossier_count
from app.traces.repo import _format_stats_facets, _stats_pipeline


VN_TZ = timezone(timedelta(hours=7))
DEFAULT_WARD = "Phường Bắc Giang"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CONVERTED_FILE_SUFFIX_RE = re.compile(r"\.(pdf|jpe?g|png|webp|tiff?)$", re.IGNORECASE)
_FILE_SUFFIX_RE = re.compile(r"\.[^./\\]+$")
_RASTER_SUFFIXES = frozenset({"jpg", "jpeg", "png", "webp", "tif", "tiff"})
_OCR_SECTION_HEADER_RE = re.compile(
    r"^=====\s*(?:fileIndex=(?P<index>\d+)\s*·\s*)?"
    r"(?P<name>.+?)\s+\([^)\n]+\)\s*=====\s*$",
    re.MULTILINE,
)
_OCR_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MIN_OCR_TOKENS = 12
_OCR_SHINGLE_SIZE = 3


def _fold_text(value: object) -> str:
    """Khớp chính xác tên đơn vị nhưng không lệ thuộc hoa/thường, dấu hay khoảng trắng."""
    text = unicodedata.normalize("NFD", str(value or "").strip().lower()).replace("đ", "d")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def _normalize_file_name(value: object) -> str:
    """Chuẩn hóa nhẹ tên file; không bỏ dấu vì tên là một phần định danh tài liệu."""
    text = unicodedata.normalize("NFC", str(value or "")).strip().casefold()
    return " ".join(text.split())


def _parse_day(value: str | None, *, end: bool) -> datetime | None:
    if not value:
        return None
    day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=VN_TZ)
    if end:
        day += timedelta(days=1)
    return day.astimezone(timezone.utc)


def _fingerprint_attachments(
    attachments: Iterable[dict], *, request_id: str
) -> tuple[str, bool]:
    """Trả dấu vân tay bộ file và cờ chính xác.

    Dùng set vì một file bị FE gửi lặp hai lần vẫn chỉ là một tài liệu của cùng hồ sơ. Nếu
    trace cũ thiếu hash thì fallback theo tên và đánh dấu ước tính.
    """
    signatures: list[tuple[str, str]] = []
    names: list[str] = []
    complete = True

    for item in attachments or []:
        if not isinstance(item, dict):
            complete = False
            continue
        name = _normalize_file_name(item.get("name"))
        digest = str(item.get("sha256") or "").strip().lower()
        if name:
            names.append(name)
        if not name or not _SHA256_RE.fullmatch(digest):
            complete = False
        else:
            signatures.append((name, digest))

    if complete and signatures:
        payload = json.dumps(sorted(set(signatures)), ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"content:{digest}", True

    if names:
        payload = json.dumps(sorted(set(names)), ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"name-only:{digest}", False

    # Không có metadata file thì tuyệt đối không gom hai request khác nhau làm một hồ sơ.
    return f"empty:{request_id}", False


def _source_name_identity(attachments: Iterable[dict]) -> tuple[str | None, frozenset[str]]:
    """Nhận diện cùng file nguồn khi FE đổi ảnh JPG/PNG thành PDF để đính kèm.

    Mobile upload giữ nguyên phần tên dài duy nhất và chỉ đổi đuôi file. Dùng tập tên gốc
    không đuôi còn giúp lượt retry 4 file (hai ảnh bị lặp) khớp lượt đầu chỉ có hai ảnh.
    Liên kết này chỉ được dùng trong cửa sổ retry ngắn ở ``_content_stats``.
    """
    stems: set[str] = set()
    suffixes: set[str] = set()
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        name = _normalize_file_name(item.get("name"))
        if not name:
            continue
        match = _CONVERTED_FILE_SUFFIX_RE.search(name)
        if match:
            suffixes.add(match.group(1).lower())
        stems.add(_CONVERTED_FILE_SUFFIX_RE.sub("", name))
    stems.discard("")
    if not stems:
        return None, frozenset(suffixes)
    payload = json.dumps(sorted(stems), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), frozenset(suffixes)


def _attachment_stem_set(attachments: Iterable[dict]) -> frozenset[str]:
    """Tập tên file theo rule dashboard hiện tại, nhưng bỏ phần đuôi định dạng."""
    return frozenset(
        _FILE_SUFFIX_RE.sub("", _normalize_file_name(item.get("name")))
        for item in attachments or []
        if isinstance(item, dict) and _normalize_file_name(item.get("name"))
    )


def _attachment_stem(value: object) -> str:
    return _FILE_SUFFIX_RE.sub("", _normalize_file_name(value))


def _split_ocr_by_attachment(attachments: list[dict], ocr_text: object) -> list[str]:
    """Tách OCR gộp về đúng file gốc bằng fileIndex hoặc tên trong header.

    Trace đính kèm có ``fileIndex=N``; trace Auto-fill cũ chỉ có tên file. Trường hợp
    một file duy nhất không có header thì toàn bộ OCR được coi là nội dung file đó.
    """
    result = ["" for _ in attachments]
    text = str(ocr_text or "")
    matches = list(_OCR_SECTION_HEADER_RE.finditer(text))
    if not matches:
        if len(attachments) == 1 and text.strip():
            result[0] = text.strip()
        return result

    used_indexes: set[int] = set()
    for order, match in enumerate(matches):
        content_end = matches[order + 1].start() if order + 1 < len(matches) else len(text)
        content = text[match.end():content_end].strip()
        content = re.sub(r"(?:\r?\n)?\s*---\s*$", "", content).strip()

        raw_index = match.group("index")
        index = int(raw_index) if raw_index is not None else None
        if index is None or not 0 <= index < len(attachments):
            header_name = _normalize_file_name(match.group("name"))
            header_stem = _attachment_stem(header_name)
            index = next(
                (
                    candidate
                    for candidate, item in enumerate(attachments)
                    if candidate not in used_indexes
                    and _normalize_file_name(item.get("name")) == header_name
                ),
                None,
            )
            if index is None:
                index = next(
                    (
                        candidate
                        for candidate, item in enumerate(attachments)
                        if candidate not in used_indexes
                        and _attachment_stem(item.get("name")) == header_stem
                    ),
                    None,
                )
            if index is None:
                index = next(
                    (
                        candidate
                        for candidate in range(len(attachments))
                        if candidate not in used_indexes
                    ),
                    None,
                )

        if index is not None and 0 <= index < len(result):
            result[index] = "\n".join(part for part in (result[index], content) if part)
            used_indexes.add(index)
    return result


def _ocr_shingles(value: object) -> frozenset[str]:
    """Dấu vân tay OCR chịu được sai khác nhỏ giữa hai lần OCR cùng tài liệu."""
    folded = _fold_text(value)
    tokens = _OCR_TOKEN_RE.findall(folded)
    if len(tokens) < _MIN_OCR_TOKENS:
        return frozenset()
    return frozenset(
        " ".join(tokens[index:index + _OCR_SHINGLE_SIZE])
        for index in range(len(tokens) - _OCR_SHINGLE_SIZE + 1)
    )


def _ocr_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _content_file_set(trace: dict) -> tuple[dict, ...]:
    """Dựng tập file logic; file bị FE gửi lặp trong cùng trace chỉ giữ một lần."""
    attachments = [item for item in (trace.get("attachments") or []) if isinstance(item, dict)]
    ocr_sections = _split_ocr_by_attachment(attachments, trace.get("ocr_text"))
    files: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(attachments):
        stem = _attachment_stem(item.get("name"))
        if not stem:
            continue
        digest = str(item.get("sha256") or "").strip().lower()
        digest = digest if _SHA256_RE.fullmatch(digest) else ""
        shingles = _ocr_shingles(ocr_sections[index] if index < len(ocr_sections) else "")
        ocr_digest = ""
        if shingles:
            payload = json.dumps(sorted(shingles), ensure_ascii=False, separators=(",", ":"))
            ocr_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        # SHA cùng nhau là bằng chứng nội dung tuyệt đối, không để sai khác OCR của hai
        # bản ghi FE lặp làm một file bị tính thành hai tài liệu.
        identity = f"sha:{digest}" if digest else f"ocr:{ocr_digest}" if ocr_digest else "name"
        dedupe_key = (stem, identity)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        files.append({"stem": stem, "sha256": digest, "ocr": shingles})
    return tuple(files)


def _file_match_strength(left: dict, right: dict, *, ocr_threshold: float) -> int:
    """0=không khớp, 1=fallback tên, 2=OCR, 3=SHA."""
    if left["stem"] != right["stem"]:
        return 0

    left_sha = left.get("sha256") or ""
    right_sha = right.get("sha256") or ""
    if left_sha and right_sha and left_sha == right_sha:
        return 3

    left_ocr = left.get("ocr") or frozenset()
    right_ocr = right.get("ocr") or frozenset()
    if left_ocr and right_ocr:
        return 2 if _ocr_similarity(left_ocr, right_ocr) >= ocr_threshold else 0

    # Hai SHA đầy đủ nhưng khác nhau là tín hiệu nội dung byte khác. Khi không có OCR để
    # chứng minh đây chỉ là chuyển JPG -> PDF, không được hạ xuống ghép bằng tên.
    if left_sha and right_sha:
        return 0

    # Chỉ fallback theo tên khi ít nhất một phía thật sự thiếu cả SHA/OCR so sánh được.
    return 1


def _is_content_file_subset(
    subset: tuple[dict, ...],
    superset: tuple[dict, ...],
    *,
    ocr_threshold: float,
) -> bool:
    """Ghép 1-1 mọi file của tập nhỏ vào tập lớn bằng bằng chứng mạnh nhất."""
    if not subset or len(subset) > len(superset):
        return False

    candidates = [
        sorted(
            (
                (_file_match_strength(item, target, ocr_threshold=ocr_threshold), target_index)
                for target_index, target in enumerate(superset)
            ),
            reverse=True,
        )
        for item in subset
    ]
    if any(not options or options[0][0] == 0 for options in candidates):
        return False

    order = sorted(
        range(len(subset)),
        key=lambda index: sum(1 for strength, _ in candidates[index] if strength > 0),
    )

    def match(position: int, used: set[int]) -> bool:
        if position >= len(order):
            return True
        source_index = order[position]
        for strength, target_index in candidates[source_index]:
            if strength <= 0 or target_index in used:
                continue
            used.add(target_index)
            if match(position + 1, used):
                return True
            used.remove(target_index)
        return False

    return match(0, set())


def _trace_observations(trace: dict) -> list[dict]:
    """Biến một trace thành một hoặc nhiều quan sát hồ sơ để gom liên thông.

    Lượt thường giữ cả ``dossier_id`` và fingerprint. Vì vậy Auto-fill JPG có thể nối với
    Đính kèm PDF bằng dossier_id, còn hai lượt Auto-fill retry nối bằng fingerprint. Lượt
    tách tab giữ mỗi dossier_id thành một hồ sơ riêng, không nhập các tab chỉ vì chung file.
    """
    request_id = str(trace.get("request_id") or trace.get("_id") or "unknown")
    created_at = trace.get("created_at")
    if trace.get("split") is True:
        dossier_ids = [
            str(value) for value in (trace.get("dossier_ids") or []) if str(value or "").strip()
        ]
        if int(trace.get("stats_version") or 0) >= 2 and dossier_ids:
            return [{
                "dossier_ids": {f"split-id:{value}"},
                "fingerprint": None,
                "source_name_fingerprint": None,
                "fingerprint_exact": None,
                "exact": True,
                "created_at": created_at,
            } for value in dossier_ids]

        count = legacy_dossier_count(
            attachments=trace.get("attachments") or [],
            procedure=str(trace.get("procedure") or ""),
            split=True,
        )
        return [{
            "dossier_ids": {f"split-legacy:{request_id}:{index}"},
            "fingerprint": None,
            "source_name_fingerprint": None,
            "fingerprint_exact": None,
            "exact": False,
            "created_at": created_at,
        } for index in range(count)]

    fingerprint, fingerprint_exact = _fingerprint_attachments(
        trace.get("attachments") or [],
        request_id=request_id,
    )
    dossier_ids: set[str] = set()
    raw_ids = [str(value) for value in (trace.get("dossier_ids") or []) if str(value or "").strip()]
    if int(trace.get("stats_version") or 0) >= 2:
        dossier_ids = {f"dossier-id:{value}" for value in raw_ids}
    source_name_fingerprint, source_suffixes = _source_name_identity(
        trace.get("attachments") or []
    )
    return [{
        "dossier_ids": dossier_ids,
        "fingerprint": fingerprint,
        "source_name_fingerprint": source_name_fingerprint,
        "source_suffixes": source_suffixes,
        "fingerprint_exact": fingerprint_exact,
        "exact": bool(dossier_ids) or fingerprint_exact,
        "created_at": created_at,
    }]


def _content_stats(traces: Iterable[dict], *, retry_window_minutes: int = 30) -> dict:
    """Tổng hợp theo cùng bucket ``(tài khoản, thủ tục)`` như dashboard."""
    observations_by_bucket: dict[tuple[str, str], list[dict]] = defaultdict(list)
    labels: dict[str, str] = {}
    request_ids: set[str] = set()
    missing_sha_traces = 0

    for trace in traces:
        user_id = str(trace.get("user_id") or "—")
        procedure = str(trace.get("procedure") or "—")
        labels.setdefault(procedure, str(trace.get("procedure_label") or procedure))
        request_ids.add(str(trace.get("request_id") or trace.get("_id") or "unknown"))
        observations = _trace_observations(trace)
        if any(observation.get("fingerprint_exact") is False for observation in observations):
            missing_sha_traces += 1
        observations_by_bucket[(user_id, procedure)].extend(observations)

    procedures: list[dict] = []
    total = 0
    estimated = 0
    retry_window = timedelta(minutes=max(retry_window_minutes, 0))
    for (_, procedure), observations in observations_by_bucket.items():
        parent = list(range(len(observations)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        # dossier_id/sessionId là liên kết mạnh nhất và không bị ảnh hưởng khi FE đổi JPG → PDF.
        owner_by_dossier_id: dict[str, int] = {}
        for index, observation in enumerate(observations):
            for dossier_id in observation["dossier_ids"]:
                if dossier_id in owner_by_dossier_id:
                    union(index, owner_by_dossier_id[dossier_id])
                else:
                    owner_by_dossier_id[dossier_id] = index

        # Fingerprint nội dung nối retry cùng định dạng; fingerprint tên nguồn chỉ nối ảnh
        # JPG/PNG với PDF. Cả hai chỉ có hiệu lực trong cửa sổ retry ngắn.
        def union_nearby(
            indexes_by_key: dict[str, list[int]], *, require_image_pdf_conversion: bool = False
        ) -> None:
            for indexes in indexes_by_key.values():
                def time_key(index: int) -> datetime:
                    value = observations[index].get("created_at")
                    if not isinstance(value, datetime):
                        return datetime.min
                    if value.tzinfo is not None:
                        return value.astimezone(timezone.utc).replace(tzinfo=None)
                    return value

                indexes.sort(key=time_key)
                for previous, current in zip(indexes, indexes[1:]):
                    previous_at = observations[previous].get("created_at")
                    current_at = observations[current].get("created_at")
                    # Test/trace rất cũ có thể thiếu created_at: cùng fingerprint vẫn là bằng
                    # chứng tốt nhất còn lại; nếu thiếu SHA thì component vẫn mang cờ ước tính.
                    close_enough = (
                        not isinstance(previous_at, datetime)
                        or not isinstance(current_at, datetime)
                        or current_at - previous_at <= retry_window
                    )
                    previous_suffixes = observations[previous].get("source_suffixes") or frozenset()
                    current_suffixes = observations[current].get("source_suffixes") or frozenset()
                    is_image_pdf_conversion = (
                        ("pdf" in previous_suffixes and bool(current_suffixes & _RASTER_SUFFIXES))
                        or ("pdf" in current_suffixes and bool(previous_suffixes & _RASTER_SUFFIXES))
                    )
                    if close_enough and (
                        not require_image_pdf_conversion or is_image_pdf_conversion
                    ):
                        union(previous, current)

        indexes_by_fingerprint: dict[str, list[int]] = defaultdict(list)
        indexes_by_source_name: dict[str, list[int]] = defaultdict(list)
        for index, observation in enumerate(observations):
            if observation.get("fingerprint"):
                indexes_by_fingerprint[observation["fingerprint"]].append(index)
            if observation.get("source_name_fingerprint"):
                indexes_by_source_name[observation["source_name_fingerprint"]].append(index)
        union_nearby(indexes_by_fingerprint)
        union_nearby(indexes_by_source_name, require_image_pdf_conversion=True)

        components: dict[int, list[int]] = defaultdict(list)
        for index in range(len(observations)):
            components[find(index)].append(index)
        count = len(components)
        estimated_count = sum(
            1
            for indexes in components.values()
            if not any(observations[index]["exact"] for index in indexes)
        )
        total += count
        estimated += estimated_count
        procedures.append({
            "key": procedure,
            "label": labels.get(procedure, procedure),
            "count": count,
            "exact": count - estimated_count,
            "estimated": estimated_count,
        })

    procedures.sort(key=lambda item: (-item["count"], item["label"]))
    return {
        "totalDossiers": total,
        "exactDossiers": total - estimated,
        "estimatedDossiers": estimated,
        "totalRequests": len(request_ids),
        "missingShaTraces": missing_sha_traces,
        "procedures": procedures,
    }


def _dashboard_without_extension_stats(traces: Iterable[dict]) -> dict:
    """Chạy đúng rule dashboard production nhưng so tên file sau khi cắt đuôi.

    Lượt không tách vẫn dùng quan hệ tập bằng nhau/tập con và nối bắc cầu, hoàn toàn không
    dùng SHA hay cửa sổ thời gian. Lượt tách tab giữ nguyên cách đếm bằng dossier_id.
    """
    file_sets_by_bucket: dict[tuple[str, str], list[frozenset[str]]] = defaultdict(list)
    empty_ids_by_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    split_ids_by_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    labels: dict[str, str] = {}

    for trace in traces:
        user_id = str(trace.get("user_id") or "—")
        procedure = str(trace.get("procedure") or "—")
        bucket = (user_id, procedure)
        labels.setdefault(procedure, str(trace.get("procedure_label") or procedure))
        request_id = str(trace.get("request_id") or trace.get("_id") or "unknown")

        if trace.get("split") is True:
            for observation in _trace_observations(trace):
                split_ids_by_bucket[bucket].update(observation["dossier_ids"])
            continue

        file_set = _attachment_stem_set(trace.get("attachments") or [])
        if file_set:
            file_sets_by_bucket[bucket].append(file_set)
            continue

        dossier_ids = [
            str(value) for value in (trace.get("dossier_ids") or []) if str(value or "").strip()
        ]
        empty_id = (
            dossier_ids[0]
            if int(trace.get("stats_version") or 0) >= 2 and dossier_ids
            else request_id
        )
        empty_ids_by_bucket[bucket].add(empty_id)

    buckets = set(file_sets_by_bucket) | set(empty_ids_by_bucket) | set(split_ids_by_bucket)
    counts_by_procedure: dict[str, int] = defaultdict(int)
    for bucket in buckets:
        _, procedure = bucket
        # Một phường có thể có nhiều user_id lịch sử nên cộng riêng từng bucket như production.
        counts_by_procedure[procedure] += count_distinct_attachment_sets(
            file_sets_by_bucket.get(bucket, [])
        )
        counts_by_procedure[procedure] += len(empty_ids_by_bucket.get(bucket, set()))
        counts_by_procedure[procedure] += len(split_ids_by_bucket.get(bucket, set()))

    procedures = [
        {
            "key": procedure,
            "label": labels.get(procedure, procedure),
            "count": count,
        }
        for procedure, count in counts_by_procedure.items()
    ]

    procedures.sort(key=lambda item: (-item["count"], item["label"]))
    return {
        "totalDossiers": sum(counts_by_procedure.values()),
        "procedures": procedures,
    }


def _content_aware_stem_stats(
    traces: Iterable[dict], *, ocr_threshold: float = 0.85
) -> dict:
    """Thử nghiệm: dossier_id -> tên bỏ đuôi + SHA/OCR -> fallback tên khi thiếu.

    Khác ``_content_stats``, phép đếm này cho phép một lượt là tập con của lượt sau nên
    không tách hồ sơ chỉ vì công dân quay lại bổ sung thêm giấy tờ.
    """
    observations_by_bucket: dict[tuple[str, str], list[dict]] = defaultdict(list)
    empty_ids_by_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    split_ids_by_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    labels: dict[str, str] = {}

    for trace in traces:
        user_id = str(trace.get("user_id") or "—")
        procedure = str(trace.get("procedure") or "—")
        bucket = (user_id, procedure)
        labels.setdefault(procedure, str(trace.get("procedure_label") or procedure))
        request_id = str(trace.get("request_id") or trace.get("_id") or "unknown")

        if trace.get("split") is True:
            for observation in _trace_observations(trace):
                split_ids_by_bucket[bucket].update(observation["dossier_ids"])
            continue

        raw_ids = [
            str(value) for value in (trace.get("dossier_ids") or []) if str(value or "").strip()
        ]
        dossier_ids = (
            {f"dossier-id:{value}" for value in raw_ids}
            if int(trace.get("stats_version") or 0) >= 2
            else set()
        )
        files = _content_file_set(trace)
        if not files:
            empty_ids_by_bucket[bucket].add(next(iter(dossier_ids), request_id))
            continue
        observations_by_bucket[bucket].append({
            "dossier_ids": dossier_ids,
            "files": files,
        })

    buckets = set(observations_by_bucket) | set(empty_ids_by_bucket) | set(split_ids_by_bucket)
    counts_by_procedure: dict[str, int] = defaultdict(int)
    for bucket in buckets:
        _, procedure = bucket
        observations = observations_by_bucket.get(bucket, [])
        parent = list(range(len(observations)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        owner_by_dossier_id: dict[str, int] = {}
        for index, observation in enumerate(observations):
            for dossier_id in observation["dossier_ids"]:
                if dossier_id in owner_by_dossier_id:
                    union(index, owner_by_dossier_id[dossier_id])
                else:
                    owner_by_dossier_id[dossier_id] = index

        for left_index, left in enumerate(observations):
            for right_index in range(left_index + 1, len(observations)):
                right = observations[right_index]
                left_files = left["files"]
                right_files = right["files"]
                same_dossier = bool(left["dossier_ids"] & right["dossier_ids"])
                comparable = (
                    _is_content_file_subset(
                        left_files, right_files, ocr_threshold=ocr_threshold
                    )
                    or _is_content_file_subset(
                        right_files, left_files, ocr_threshold=ocr_threshold
                    )
                )
                if same_dossier or comparable:
                    union(left_index, right_index)

        counts_by_procedure[procedure] += len(
            {find(index) for index in range(len(observations))}
        )
        counts_by_procedure[procedure] += len(empty_ids_by_bucket.get(bucket, set()))
        counts_by_procedure[procedure] += len(split_ids_by_bucket.get(bucket, set()))

    procedures = [
        {
            "key": procedure,
            "label": labels.get(procedure, procedure),
            "count": count,
        }
        for procedure, count in counts_by_procedure.items()
    ]
    procedures.sort(key=lambda item: (-item["count"], item["label"]))
    return {
        "totalDossiers": sum(counts_by_procedure.values()),
        "ocrThreshold": ocr_threshold,
        "procedures": procedures,
    }


def _print_accounts(accounts: list[dict]) -> None:
    print(f"Tài khoản khớp tên chính xác: {len(accounts)}")
    for account in accounts:
        print(
            "  - "
            f"{account.get('username') or '—'} | id={account.get('_id')} | "
            f"name={account.get('name') or '—'} | role={account.get('role') or 'user'}"
        )


def _print_comparison(dashboard_stem: dict, content_aware: dict) -> None:
    dashboard_stem_by_key = {
        item["key"]: item for item in dashboard_stem.get("procedures") or []
    }
    content_aware_by_key = {
        item["key"]: item for item in content_aware.get("procedures") or []
    }
    keys = sorted(
        set(dashboard_stem_by_key) | set(content_aware_by_key),
        key=lambda key: (
            -max(
                int(dashboard_stem_by_key.get(key, {}).get("count") or 0),
                int(content_aware_by_key.get(key, {}).get("count") or 0),
            ),
            str(
                content_aware_by_key.get(key, {}).get("label")
                or dashboard_stem_by_key.get(key, {}).get("label")
                or key
            ),
        ),
    )

    print("\nTheo từng thủ tục:")
    print(f"{'Prod-bỏ-đuôi':>12}  {'Tên+Nội dung':>13}  {'Chênh':>6}  Thủ tục")
    for key in keys:
        stem_count = int(dashboard_stem_by_key.get(key, {}).get("count") or 0)
        content_count = int(content_aware_by_key.get(key, {}).get("count") or 0)
        label = (
            content_aware_by_key.get(key, {}).get("label")
            or dashboard_stem_by_key.get(key, {}).get("label")
            or key
        )
        print(
            f"{stem_count:>12,}  {content_count:>13,}  "
            f"{content_count - stem_count:>+6,}  {label} [{key}]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Đối chiếu rule dashboard bỏ đuôi với tên file + nội dung"
    )
    parser.add_argument("--ward", default=DEFAULT_WARD, help=f"Tên đơn vị (mặc định: {DEFAULT_WARD})")
    parser.add_argument("--procedure", help="Chỉ kiểm tra một khóa thủ tục")
    parser.add_argument("--from", dest="date_from", help="Từ ngày YYYY-MM-DD, giờ Việt Nam")
    parser.add_argument("--to", dest="date_to", help="Đến hết ngày YYYY-MM-DD, giờ Việt Nam")
    parser.add_argument(
        "--ocr-similarity",
        type=float,
        default=0.85,
        help="Ngưỡng Jaccard OCR để coi hai file cùng nội dung (mặc định 0.85)",
    )
    args = parser.parse_args()

    try:
        date_from = _parse_day(args.date_from, end=False)
        date_to = _parse_day(args.date_to, end=True)
    except ValueError as exc:
        parser.error(f"Ngày không hợp lệ, cần định dạng YYYY-MM-DD: {exc}")
    if date_from and date_to and date_from >= date_to:
        parser.error("--from phải nhỏ hơn hoặc bằng --to")
    if not 0 <= args.ocr_similarity <= 1:
        parser.error("--ocr-similarity phải nằm trong khoảng 0..1")

    client = MongoClient(settings.mongo_dsn)
    try:
        db = client[settings.mongo_db]
        target = _fold_text(args.ward)
        accounts = [
            account
            for account in db.users.find(
                {}, {"username": 1, "name": 1, "role": 1, "xa": 1, "tinh": 1}
            )
            if _fold_text(account.get("name")) == target
        ]
        _print_accounts(accounts)
        if not accounts:
            print(f'Không tìm thấy tài khoản có name đúng bằng "{args.ward}".')
            return 2

        query: dict = {"user_id": {"$in": [str(account["_id"]) for account in accounts]}}
        if args.procedure:
            query["procedure"] = args.procedure
        date_query: dict = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lt"] = date_to
        if date_query:
            query["created_at"] = date_query

        facets = list(db.traces.aggregate(_stats_pipeline(query), allowDiskUse=True))
        current = _format_stats_facets(facets[0] if facets else {})
        traces = list(db.traces.find(
            query,
            {
                "request_id": 1,
                "user_id": 1,
                "procedure": 1,
                "procedure_label": 1,
                "attachments": 1,
                "ocr_text": 1,
                "created_at": 1,
                "split": 1,
                "stats_version": 1,
                "dossier_ids": 1,
            },
        ))
        candidate = _content_stats(traces)
        dashboard_stem = _dashboard_without_extension_stats(traces)
        content_aware = _content_aware_stem_stats(
            traces, ocr_threshold=args.ocr_similarity
        )
    finally:
        client.close()

    span = f"{args.date_from or 'đầu dữ liệu'} -> {args.date_to or 'hiện tại'}"
    print(f"\nPhạm vi: {args.ward} | {span} | thủ tục={args.procedure or 'tất cả'}")
    print(f"Trace đã xét: {len(traces):,}")
    print(f"Request duy nhất: {candidate['totalRequests']:,}")
    print(f"Hồ sơ theo dashboard hiện tại: {current.get('totalDossiers', 0):,}")
    print(
        "Hồ sơ theo rule dashboard nhưng tên file bỏ đuôi: "
        f"{dashboard_stem['totalDossiers']:,} (không dùng SHA/thời gian)"
    )
    print(
        "Hồ sơ theo tên bỏ đuôi + nội dung: "
        f"{content_aware['totalDossiers']:,} "
        f"(SHA hoặc OCR tương đồng >= {args.ocr_similarity:.0%}; "
        "fallback tên khi thiếu nội dung)"
    )
    print(f"Trace thiếu SHA-256/metadata đầy đủ: {candidate['missingShaTraces']:,}")
    _print_comparison(dashboard_stem, content_aware)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
