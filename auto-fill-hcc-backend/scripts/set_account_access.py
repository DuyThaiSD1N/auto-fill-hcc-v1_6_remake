"""Khóa/mở một tài khoản mà không xóa user hoặc lịch sử hồ sơ.

Ví dụ:
    python -m scripts.set_account_access --username hccnghiahung --off
    python -m scripts.set_account_access --username hccnghiahung --on
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from app.auth.access_control import MAINTENANCE_MESSAGE
from app.db.mongo import close, connect, get_db


async def set_account_access(username: str, *, disabled: bool) -> dict:
    normalized = (username or "").strip().lower()
    if not normalized:
        raise ValueError("Username không được để trống")

    db = get_db()
    user = await db.users.find_one({"username": normalized})
    if not user:
        raise LookupError(f"Không tìm thấy tài khoản: {normalized}")

    now = datetime.now(timezone.utc)
    if disabled:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "access_disabled": True,
                "access_disabled_reason": MAINTENANCE_MESSAGE,
                "access_disabled_at": now,
                "updated_at": now,
            }},
        )
        revoked = await db.refresh_tokens.update_many(
            {"user_id": str(user["_id"]), "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
        return {"username": normalized, "disabled": True, "revoked": revoked.modified_count}

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"access_disabled": False, "updated_at": now},
            "$unset": {"access_disabled_reason": "", "access_disabled_at": ""},
        },
    )
    return {"username": normalized, "disabled": False, "revoked": 0}


async def _run(username: str, *, disabled: bool) -> None:
    connect()
    try:
        result = await set_account_access(username, disabled=disabled)
    finally:
        close()
    if result["disabled"]:
        print(
            f"Đã OFF {result['username']}; thu hồi {result['revoked']} refresh token. "
            f"Thông báo: {MAINTENANCE_MESSAGE}"
        )
    else:
        print(f"Đã ON {result['username']}; tài khoản cần đăng nhập lại.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Khóa/mở tài khoản HCC trong thời gian bảo trì")
    parser.add_argument("--username", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--off", action="store_true", help="Khóa tài khoản và thu hồi refresh token")
    action.add_argument("--on", action="store_true", help="Mở lại tài khoản")
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.username, disabled=args.off))
    except (LookupError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
