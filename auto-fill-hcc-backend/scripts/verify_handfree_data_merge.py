"""Đối soát số lượng sau khi backfill và merge dữ liệu Handfree vào DB dùng chung."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.config import settings
from app.db.mongo import close, get_db


EXPECTED_TARGET_DB = "autofill_hcc"
COLLECTIONS = ("traces", "process_requests", "audit_logs", "consent_logs")


async def execute(
    *,
    expected_autofill_traces: int | None,
    expected_handfree_traces: int | None,
    expected_users: int | None,
) -> tuple[dict, bool]:
    if settings.mongo_db != EXPECTED_TARGET_DB:
        raise RuntimeError(
            f"Từ chối chạy: MONGO_DB={settings.mongo_db!r}, "
            f"đích bắt buộc là {EXPECTED_TARGET_DB!r}"
        )
    db = get_db()
    report: dict = {"targetDb": settings.mongo_db, "collections": {}, "checks": []}
    valid = True
    for name in COLLECTIONS:
        collection = db[name]
        counts = {
            "total": await collection.count_documents({}),
            "autofill": await collection.count_documents({"experience": "autofill"}),
            "handfree": await collection.count_documents({"experience": "handfree"}),
            "missingOrNull": await collection.count_documents({"$or": [
                {"experience": {"$exists": False}},
                {"experience": None},
            ]}),
            "invalid": await collection.count_documents({
                "experience": {"$exists": True, "$nin": [None, "autofill", "handfree"]},
            }),
        }
        counts["importedFromLegacyHandfree"] = await collection.count_documents({
            "experience": "handfree",
            "migration_source": "tro_ly_nguoi_dan_legacy",
        })
        report["collections"][name] = counts
        if counts["missingOrNull"] or counts["invalid"]:
            valid = False

    users = await db.users.count_documents({})
    report["users"] = users

    def check(label: str, actual: int, expected: int | None) -> None:
        nonlocal valid
        if expected is None:
            return
        passed = actual == expected
        valid = valid and passed
        report["checks"].append({
            "label": label,
            "actual": actual,
            "expected": expected,
            "passed": passed,
        })

    trace_counts = report["collections"]["traces"]
    check("autofillTraces", trace_counts["autofill"], expected_autofill_traces)
    check("handfreeTraces", trace_counts["handfree"], expected_handfree_traces)
    if expected_autofill_traces is not None and expected_handfree_traces is not None:
        check(
            "totalTraces",
            trace_counts["total"],
            expected_autofill_traces + expected_handfree_traces,
        )
    check("users", users, expected_users)
    report["passed"] = valid
    return report, valid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-autofill-traces", type=int)
    parser.add_argument("--expected-handfree-traces", type=int)
    parser.add_argument("--expected-users", type=int)
    args = parser.parse_args()
    try:
        report, valid = asyncio.run(execute(
            expected_autofill_traces=args.expected_autofill_traces,
            expected_handfree_traces=args.expected_handfree_traces,
            expected_users=args.expected_users,
        ))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if valid else 2
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
