"""Tạo hoặc đổi mật khẩu tài khoản nội bộ dành riêng cho web Monitor.

Mặc định chỉ kiểm tra và in kế hoạch. Truyền ``--apply`` để ghi MongoDB; mật khẩu được nhập
bằng getpass nên không xuất hiện trong source, process list hay shell history.

Ví dụ:
    python -m scripts.manage_super_admin --username monitor.admin
    python -m scripts.manage_super_admin --username monitor.admin --apply
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from getpass import getpass
import json

from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.core.security import hash_password
from app.db.mongo import close, get_db
from app.users.roles import SUPER_ADMIN_ROLE


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _username(value: str) -> str:
    normalized = (value or "").strip().lower()
    if len(normalized) < 3:
        raise argparse.ArgumentTypeError("Tên đăng nhập phải có ít nhất 3 ký tự")
    return normalized


def _password_from_terminal() -> str:
    password = getpass("Mật khẩu super admin mới: ")
    if len(password) < 12:
        raise ValueError("Mật khẩu super admin phải có ít nhất 12 ký tự")
    if password != getpass("Nhập lại mật khẩu: "):
        raise ValueError("Hai lần nhập mật khẩu không khớp")
    return password


async def _execute(
    *, username: str, name: str | None, apply: bool, password: str | None
) -> dict:
    db = get_db()
    current = await db.users.find_one({"username": username})
    if current and current.get("role") != SUPER_ADMIN_ROLE:
        raise RuntimeError(
            "Username đã thuộc một tài khoản thường. Từ chối tự động nâng quyền; "
            "hãy chọn username riêng cho Monitor."
        )

    report = {
        "mode": "apply" if apply else "dry-run",
        "database": settings.mongo_db,
        "username": username,
        "role": SUPER_ADMIN_ROLE,
        "action": "rotate_credentials" if current else "create",
        "applied": False,
    }
    if not apply:
        report["message"] = "Dry-run thành công; chạy lại với --apply để nhập mật khẩu và ghi."
        return report
    if password is None:
        raise ValueError("Thiếu mật khẩu khi chạy apply")

    now = _now()
    if current:
        updates = {
            "password_hash": hash_password(password),
            "role": SUPER_ADMIN_ROLE,
            "access_disabled": False,
            "updated_at": now,
        }
        if name is not None:
            updates["name"] = name.strip() or None
        await db.users.update_one(
            {"_id": current["_id"], "role": SUPER_ADMIN_ROLE},
            {
                "$set": updates,
                "$unset": {"access_disabled_reason": "", "access_disabled_at": ""},
            },
        )
        # Đổi mật khẩu phải kết thúc toàn bộ phiên Monitor cũ.
        await db.refresh_tokens.update_many(
            {"user_id": str(current["_id"]), "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
        user_id = str(current["_id"])
    else:
        document = {
            "username": username,
            "password_hash": hash_password(password),
            "name": (name or "Quản trị Monitor").strip() or "Quản trị Monitor",
            "xa": None,
            "tinh": None,
            "role": SUPER_ADMIN_ROLE,
            "access_disabled": False,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await db.users.insert_one(document)
        except DuplicateKeyError as exc:
            raise RuntimeError("Username vừa được tạo bởi tiến trình khác; hãy chạy lại.") from exc
        user_id = str(result.inserted_id)

    report.update({
        "userId": user_id,
        "applied": True,
        "message": "Tài khoản Monitor đã sẵn sàng.",
    })
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True, type=_username)
    parser.add_argument("--name", help="Tên hiển thị; bỏ trống để giữ tên hiện có.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi thay đổi. Khi dùng cờ này script sẽ hỏi mật khẩu hai lần.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        password = _password_from_terminal() if args.apply else None
        report = asyncio.run(_execute(
            username=args.username,
            name=args.name,
            apply=args.apply,
            password=password,
        ))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI chỉ in loại lỗi, không in bí mật.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
