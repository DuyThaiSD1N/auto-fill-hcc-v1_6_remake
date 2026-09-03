"""Gắn ``experience=autofill`` cho dữ liệu Auto Fill cũ chưa có discriminator.

Mặc định chỉ thống kê. Truyền ``--apply`` mới cập nhật và chỉ cập nhật document có
``experience`` thiếu hoặc null; dữ liệu đã mang nhãn Handfree không bao giờ bị chạm tới.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from app.config import settings
from app.db.mongo import close, get_db


EXPECTED_TARGET_DB = "autofill_hcc"
COLLECTIONS = ("traces", "process_requests", "audit_logs", "consent_logs")
LEGACY_FILTER = {
    "$or": [
        {"experience": {"$exists": False}},
        {"experience": None},
    ]
}


async def execute(*, apply: bool) -> dict:
    if settings.mongo_db != EXPECTED_TARGET_DB:
        raise RuntimeError(
            f"Từ chối chạy: MONGO_DB={settings.mongo_db!r}, "
            f"đích bắt buộc là {EXPECTED_TARGET_DB!r}"
        )
    db = get_db()
    report: dict = {
        "mode": "apply" if apply else "dry-run",
        "targetDb": settings.mongo_db,
        "collections": {},
        "legacyTotal": 0,
        "modifiedTotal": 0,
    }
    for name in COLLECTIONS:
        collection = db[name]
        total = await collection.count_documents({})
        legacy = await collection.count_documents(LEGACY_FILTER)
        invalid = await collection.count_documents({
            "experience": {"$exists": True, "$nin": [None, "autofill", "handfree"]},
        })
        modified = 0
        if apply and legacy:
            result = await collection.update_many(
                LEGACY_FILTER,
                {"$set": {"experience": "autofill"}},
            )
            modified = result.modified_count
        report["collections"][name] = {
            "total": total,
            "legacyOrNull": legacy,
            "invalidExperience": invalid,
            "modified": modified,
        }
        report["legacyTotal"] += legacy
        report["modifiedTotal"] += modified
    report["applied"] = apply
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Ghi nhãn vào MongoDB.")
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(execute(apply=args.apply)), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
