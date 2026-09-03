"""Gộp tài khoản Handfree vào DB Auto Fill theo username, không làm mất dữ liệu đích.

Script nhận bản export đầy đủ collection ``users`` của Handfree qua file hoặc stdin.
Mặc định chỉ lập kế hoạch; phải truyền ``--apply`` mới ghi vào MongoDB Auto Fill.

Quy tắc:
- Username đã có ở Auto Fill: giữ nguyên TOÀN BỘ tài khoản Auto Fill, chỉ sinh ánh xạ ID.
- Username chỉ có ở Handfree: tạo tài khoản mới và giữ password_hash hiện tại.
- ``hcchaichau`` là username cũ của Handfree, được ánh xạ sang
  ``hccphuonghaichau`` đang có ở Auto Fill.
- Không nhập refresh token hoặc bất kỳ collection nào ngoài users.

Output stdout chỉ chứa báo cáo và ánh xạ ID, tuyệt đối không in password_hash.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from bson import ObjectId, json_util
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.core.errors import AppError
from app.db.mongo import close, get_db
from app.locations.catalog import canonical_location


EXPECTED_TARGET_DB = "autofill_hcc"
USERNAME_ALIASES = {
    "hcchaichau": "hccphuonghaichau",
}
ALLOWED_ROLES = {"admin", "user", "commune", "province", "province_admin"}
PUBLIC_COMPARE_FIELDS = ("name", "tinh", "xa", "role", "access_disabled")

# Ba quyết định đã được xác nhận riêng. Chúng đều tuân theo chính sách chung:
# tài khoản Auto Fill hiện có là bản chuẩn và không bị update bởi dữ liệu Handfree.
CONFIRMED_TARGET_WINS = {
    "hcctester": "Giữ nguyên tài khoản Auto Fill, không tạo mới.",
    "skquangngai": "Giữ role và các thuộc tính của Auto Fill.",
    "hccnghiahung": "Giữ trạng thái đang hoạt động của Auto Fill.",
}


@dataclass(frozen=True)
class PlannedInsert:
    source_user_id: str
    target_user_id: str
    document: dict[str, Any]
    id_collision: bool


@dataclass(frozen=True)
class MergePlan:
    inserts: list[PlannedInsert]
    report: dict[str, Any]


def canonical_username(value: Any) -> str:
    username = str(value or "").strip().lower()
    return USERNAME_ALIASES.get(username, username)


def _object_id(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError) as exc:
        raise ValueError("_id không phải ObjectId hợp lệ") from exc


def _read_source_users(input_path: str) -> list[dict[str, Any]]:
    raw = sys.stdin.read() if input_path == "-" else Path(input_path).read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError("Bản export users Handfree đang rỗng")

    try:
        decoded = json_util.loads(raw)
    except Exception:
        # Hỗ trợ cả mongoexport không có --jsonArray (mỗi dòng là một document).
        try:
            decoded = [json_util.loads(line) for line in raw.splitlines() if line.strip()]
        except Exception as exc:
            raise ValueError("Không đọc được JSON/Extended JSON của users Handfree") from exc

    if isinstance(decoded, dict) and isinstance(decoded.get("items"), list):
        decoded = decoded["items"]
    if not isinstance(decoded, list) or any(not isinstance(item, dict) for item in decoded):
        raise ValueError("Input phải là danh sách document users Handfree")
    return decoded


def _iso_or_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _differences(source: dict[str, Any], target: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for field in PUBLIC_COMPARE_FIELDS:
        source_value = source.get(field)
        target_value = target.get(field)
        if field == "access_disabled":
            source_value = source_value is True
            target_value = target_value is True
        if source_value != target_value:
            result[field] = {
                "handfree": _iso_or_value(source_value),
                "autoFillKept": _iso_or_value(target_value),
            }
    return result


def _insert_document(
    source: dict[str, Any],
    *,
    username: str,
    target_id: ObjectId,
    now: datetime,
) -> dict[str, Any]:
    password_hash = source.get("password_hash")
    if not isinstance(password_hash, str) or not password_hash.strip():
        raise ValueError(
            "thiếu password_hash; hãy dùng mongoexport collection users đầy đủ, "
            "không dùng JSON từ API /users"
        )

    role = source.get("role") or "user"
    if role not in ALLOWED_ROLES:
        raise ValueError(f"role không hợp lệ: {role!r}")

    try:
        tinh, xa = canonical_location(source.get("tinh"), source.get("xa"))
    except AppError as exc:
        raise ValueError(exc.message) from exc

    created_at = source.get("created_at")
    updated_at = source.get("updated_at")
    document: dict[str, Any] = {
        "_id": target_id,
        "username": username,
        "password_hash": password_hash,
        "name": source.get("name"),
        "xa": xa,
        "tinh": tinh,
        "role": role,
        "access_disabled": source.get("access_disabled") is True,
        "created_at": created_at if isinstance(created_at, datetime) else now,
        "updated_at": updated_at if isinstance(updated_at, datetime) else now,
    }
    if isinstance(source.get("last_login_at"), datetime):
        document["last_login_at"] = source["last_login_at"]
    if document["access_disabled"]:
        if source.get("access_disabled_reason") is not None:
            document["access_disabled_reason"] = source["access_disabled_reason"]
        if isinstance(source.get("access_disabled_at"), datetime):
            document["access_disabled_at"] = source["access_disabled_at"]
    return document


def build_merge_plan(
    source_users: list[dict[str, Any]],
    target_users: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> MergePlan:
    now = now or datetime.now(timezone.utc)
    errors: list[dict[str, str]] = []
    target_by_username: dict[str, dict[str, Any]] = {}
    target_ids: set[ObjectId] = set()

    for target in target_users:
        username = canonical_username(target.get("username"))
        if not username:
            errors.append({"scope": "autoFill", "error": "Có user đích thiếu username"})
            continue
        if username in target_by_username:
            errors.append({
                "scope": "autoFill",
                "username": username,
                "error": "Có nhiều user Auto Fill trùng username sau chuẩn hóa",
            })
            continue
        try:
            target_ids.add(_object_id(target.get("_id")))
        except ValueError as exc:
            errors.append({"scope": "autoFill", "username": username, "error": str(exc)})
            continue
        target_by_username[username] = target

    source_by_username: dict[str, dict[str, Any]] = {}
    for source in source_users:
        username = canonical_username(source.get("username"))
        if not username:
            errors.append({"scope": "handfree", "error": "Có user nguồn thiếu username"})
            continue
        if username in source_by_username:
            errors.append({
                "scope": "handfree",
                "username": username,
                "error": "Có nhiều user Handfree trùng username sau khi áp dụng alias",
            })
            continue
        source_by_username[username] = source

    matches: list[dict[str, Any]] = []
    insert_reports: list[dict[str, Any]] = []
    inserts: list[PlannedInsert] = []
    user_id_map: dict[str, str] = {}

    for username in sorted(source_by_username):
        source = source_by_username[username]
        try:
            source_id = _object_id(source.get("_id"))
        except ValueError as exc:
            errors.append({"scope": "handfree", "username": username, "error": str(exc)})
            continue

        target = target_by_username.get(username)
        if username in CONFIRMED_TARGET_WINS and target is None:
            errors.append({
                "scope": "autoFill",
                "username": username,
                "error": "Thiếu tài khoản Auto Fill đã được chốt làm bản chuẩn; từ chối tạo mới từ Handfree",
            })
            continue
        if target is not None:
            target_id = _object_id(target.get("_id"))
            user_id_map[str(source_id)] = str(target_id)
            if username == "hccnghiahung" and target.get("access_disabled") is True:
                errors.append({
                    "scope": "autoFill",
                    "username": username,
                    "error": "Tài khoản Auto Fill đang bị khóa, không đúng quyết định giữ trạng thái hoạt động",
                })
            matches.append({
                "username": username,
                "sourceUsername": str(source.get("username") or ""),
                "sourceUserId": str(source_id),
                "targetUserId": str(target_id),
                "policy": "auto_fill_kept",
                "confirmedDecision": CONFIRMED_TARGET_WINS.get(username),
                "differences": _differences(source, target),
            })
            continue

        id_collision = source_id in target_ids
        target_id = ObjectId() if id_collision else source_id
        try:
            document = _insert_document(
                source,
                username=username,
                target_id=target_id,
                now=now,
            )
        except ValueError as exc:
            errors.append({"scope": "handfree", "username": username, "error": str(exc)})
            continue

        target_ids.add(target_id)
        user_id_map[str(source_id)] = str(target_id)
        inserts.append(PlannedInsert(str(source_id), str(target_id), document, id_collision))
        insert_reports.append({
            "username": username,
            "sourceUserId": str(source_id),
            "targetUserId": str(target_id),
            "idCollision": id_collision,
            "role": document["role"],
            "accessDisabled": document["access_disabled"],
        })

    report = {
        "sourceCount": len(source_users),
        "targetBefore": len(target_users),
        "targetAfterPlanned": len(target_users) + len(inserts),
        "matchedCount": len(matches),
        "insertCount": len(inserts),
        "errorCount": len(errors),
        "matched": matches,
        "insertedOrPlanned": insert_reports,
        "errors": errors,
        "userIdMap": user_id_map,
    }
    return MergePlan(inserts=inserts, report=report)


async def _execute(source_users: list[dict[str, Any]], *, apply: bool) -> dict[str, Any]:
    if settings.mongo_db != EXPECTED_TARGET_DB:
        raise RuntimeError(
            f"Từ chối chạy: MONGO_DB={settings.mongo_db!r}, "
            f"đích bắt buộc là {EXPECTED_TARGET_DB!r}"
        )

    db = get_db()
    target_users = [user async for user in db.users.find({})]
    plan = build_merge_plan(source_users, target_users)
    report = {"mode": "apply" if apply else "dry-run", "targetDb": settings.mongo_db, **plan.report}

    if report["errors"]:
        report["applied"] = False
        report["message"] = "Không ghi dữ liệu vì preflight có lỗi."
        return report

    if not apply:
        report["applied"] = False
        report["message"] = "Dry-run thành công; chạy lại với --apply để ghi dữ liệu."
        return report

    inserted_count = 0
    for item in plan.inserts:
        try:
            await db.users.insert_one(item.document)
        except DuplicateKeyError as exc:
            raise RuntimeError(
                f"Dữ liệu đích thay đổi trong lúc merge tại user "
                f"{item.document['username']!r}; hãy chạy lại dry-run"
            ) from exc
        inserted_count += 1

    report["applied"] = True
    report["insertedCount"] = inserted_count
    report["targetAfter"] = await db.users.count_documents({})
    report["message"] = "Merge users hoàn tất; tài khoản Auto Fill trùng username không bị sửa."
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="-",
        help="File mongoexport users Handfree; dùng '-' để đọc stdin (mặc định).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi user mới vào DB Auto Fill. Không truyền cờ này thì chỉ dry-run.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        source_users = _read_source_users(args.input)
        report = asyncio.run(_execute(source_users, apply=args.apply))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not report.get("errors") else 2
    except Exception as exc:
        # Không in document nguồn để password_hash không lọt vào log terminal/CI.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
