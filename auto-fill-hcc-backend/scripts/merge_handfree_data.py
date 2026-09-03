"""Nhập insert-only dữ liệu lịch sử Handfree vào MongoDB Auto Fill dùng chung.

Chạy riêng từng collection từ file ``mongoexport`` (JSON array hoặc NDJSON). Mặc định
dry-run; phải truyền ``--apply`` mới ghi. Mọi document nguồn được gắn
``experience=handfree`` và ``user_id`` được đổi theo ``userIdMap`` sinh bởi
``merge_handfree_users.py``.

Collection hỗ trợ: traces, process_requests, audit_logs, consent_logs. Script không
update document đích, không in OCR/PII và có thể chạy lại an toàn theo ID nguồn migration.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

from bson import ObjectId, json_util
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.db.mongo import close, get_db


EXPECTED_TARGET_DB = "autofill_hcc"
COLLECTIONS = ("traces", "process_requests", "audit_logs", "consent_logs")
MIGRATION_SOURCE = "tro_ly_nguoi_dan_legacy"


def read_documents(input_path: str) -> list[dict[str, Any]]:
    raw = sys.stdin.read() if input_path == "-" else Path(input_path).read_text(encoding="utf-8")
    if not raw.strip():
        return []
    try:
        decoded = json_util.loads(raw)
    except Exception:
        try:
            decoded = [json_util.loads(line) for line in raw.splitlines() if line.strip()]
        except Exception as exc:
            raise ValueError("Không đọc được JSON/Extended JSON từ mongoexport") from exc
    if isinstance(decoded, dict):
        decoded = decoded.get("items") if isinstance(decoded.get("items"), list) else [decoded]
    if not isinstance(decoded, list) or any(not isinstance(item, dict) for item in decoded):
        raise ValueError("Input phải chứa các document JSON")
    return decoded


def read_user_map(path: str) -> dict[str, str]:
    payload = json_util.loads(Path(path).read_text(encoding="utf-8"))
    mapping = payload.get("userIdMap") if isinstance(payload, dict) else None
    if not isinstance(mapping, dict):
        raise ValueError("File user map phải chứa object userIdMap")
    return {
        str(source): str(target)
        for source, target in mapping.items()
        if str(source) and str(target)
    }


def natural_key(collection: str, document: dict[str, Any]) -> tuple[Any, ...]:
    if collection == "traces":
        request_id = str(document.get("request_id") or "").strip()
        kind = str(document.get("kind") or "").strip()
        if not request_id or not kind:
            raise ValueError("trace thiếu request_id hoặc kind")
        return request_id, kind
    if collection == "process_requests":
        request_id = str(document.get("request_id") or "").strip()
        if not request_id:
            raise ValueError("process_request thiếu request_id")
        return (request_id,)
    if collection == "audit_logs":
        request_id = str(document.get("request_id") or "").strip()
        endpoint = str(document.get("endpoint") or "").strip()
        if not request_id:
            raise ValueError("audit_log thiếu request_id")
        return request_id, endpoint
    if collection == "consent_logs":
        if document.get("_id") is None:
            raise ValueError("consent_log thiếu _id")
        return (str(document["_id"]),)
    raise ValueError(f"Collection không được hỗ trợ: {collection}")


def duplicate_query(collection: str, document: dict[str, Any]) -> dict[str, Any]:
    natural_key(collection, document)
    return {
        "experience": "handfree",
        "migration_source": MIGRATION_SOURCE,
        "migration_source_id": document["migration_source_id"],
    }


def normalize_document(
    collection: str,
    source: dict[str, Any],
    user_id_map: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    document = deepcopy(source)
    if document.get("_id") is None:
        raise ValueError("document nguồn thiếu _id")
    document["experience"] = "handfree"
    # Không khử trùng bằng request_id: một request có thể có nhiều trace hợp lệ. ID
    # document từ Mongo nguồn mới là khóa đảm bảo vừa giữ đủ dữ liệu vừa chạy lại an toàn.
    document["migration_source"] = MIGRATION_SOURCE
    document["migration_source_id"] = str(document["_id"])
    remapped = False
    if document.get("user_id") not in (None, ""):
        source_user_id = str(document["user_id"])
        target_user_id = user_id_map.get(source_user_id)
        if not target_user_id:
            raise ValueError(f"user_id chưa được ánh xạ: {source_user_id}")
        document["user_id"] = target_user_id
        remapped = target_user_id != source_user_id
    natural_key(collection, document)
    return document, remapped


def prepare_documents(
    collection: str,
    source_documents: list[dict[str, Any]],
    user_id_map: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    prepared: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    errors: list[dict[str, Any]] = []
    source_duplicates = 0
    remapped = 0
    for index, source in enumerate(source_documents):
        try:
            document, was_remapped = normalize_document(collection, source, user_id_map)
            key = (document["migration_source_id"],)
            if key in seen:
                source_duplicates += 1
                continue
            seen.add(key)
            prepared.append(document)
            remapped += int(was_remapped)
        except ValueError as exc:
            errors.append({"index": index, "error": str(exc)})
    return prepared, {
        "sourceCount": len(source_documents),
        "preparedCount": len(prepared),
        "sourceDuplicateCount": source_duplicates,
        "remappedUserCount": remapped,
    }, errors


async def execute(
    *,
    collection: str,
    source_documents: list[dict[str, Any]],
    user_id_map: dict[str, str],
    apply: bool,
) -> dict[str, Any]:
    if settings.mongo_db != EXPECTED_TARGET_DB:
        raise RuntimeError(
            f"Từ chối chạy: MONGO_DB={settings.mongo_db!r}, "
            f"đích bắt buộc là {EXPECTED_TARGET_DB!r}"
        )
    prepared, summary, errors = prepare_documents(collection, source_documents, user_id_map)
    report: dict[str, Any] = {
        "mode": "apply" if apply else "dry-run",
        "targetDb": settings.mongo_db,
        "collection": collection,
        **summary,
        "insertedCount": 0,
        "existingCount": 0,
        "regeneratedIdCount": 0,
        "errorCount": len(errors),
        "errors": errors[:20],
    }
    if errors:
        report["applied"] = False
        report["message"] = "Không ghi dữ liệu vì preflight có lỗi."
        return report

    target = get_db()[collection]
    for document in prepared:
        if await target.find_one(duplicate_query(collection, document), {"_id": 1}):
            report["existingCount"] += 1
            continue
        if await target.find_one({"_id": document.get("_id")}, {"_id": 1}):
            # Không suy đoán document trùng chỉ từ _id giữa hai DB độc lập. Giữ đủ bản
            # ghi nguồn bằng ID mới; migration_source_id vẫn bảo đảm lần chạy sau bỏ qua.
            document["_id"] = ObjectId()
            report["regeneratedIdCount"] += 1
        if not apply:
            report["insertedCount"] += 1
            continue
        try:
            await target.insert_one(document)
        except DuplicateKeyError:
            # Đích có thể thay đổi giữa lúc kiểm tra và insert. Chỉ coi là an toàn nếu
            # khóa nghiệp vụ vừa xuất hiện; tuyệt đối không update document đó.
            if await target.find_one(duplicate_query(collection, document), {"_id": 1}):
                report["existingCount"] += 1
                continue
            raise
        report["insertedCount"] += 1
    report["applied"] = apply
    report["message"] = (
        "Merge insert-only hoàn tất."
        if apply
        else "Dry-run thành công; chạy lại với --apply để ghi dữ liệu."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True, choices=COLLECTIONS)
    parser.add_argument("--input", default="-", help="File mongoexport; '-' để đọc stdin.")
    parser.add_argument("--user-map", required=True, help="JSON output từ merge users --apply.")
    parser.add_argument("--apply", action="store_true", help="Ghi insert-only vào MongoDB.")
    args = parser.parse_args()
    try:
        report = asyncio.run(execute(
            collection=args.collection,
            source_documents=read_documents(args.input),
            user_id_map=read_user_map(args.user_map),
            apply=args.apply,
        ))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not report["errorCount"] else 2
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
