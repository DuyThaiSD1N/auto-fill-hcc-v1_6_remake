"""Tạo / cập nhật user (admin seed). Không có self-registration nên dùng script này.

Cách dùng (cần .env trỏ đúng Mongo):
    python -m scripts.seed_user --username admin --password 'MatKhau123' --name 'Admin' --role admin
    python -m scripts.seed_user --username hcctanphong --password '...' --name 'Phường Tân Phong' --xa 'Tân Phong' --tinh 'Lai Châu'

Dùng --role admin để tạo/nâng cấp tài khoản quản trị đầu tiên (bootstrap trang quản lý tài khoản).
"""
import argparse
import asyncio
from datetime import datetime, timezone

from app.core.security import hash_password
from app.db.mongo import connect, get_db


async def seed(
    username: str,
    password: str,
    name: str | None,
    xa: str | None,
    tinh: str | None,
    role: str,
) -> None:
    connect()
    db = get_db()
    await db.users.create_index("username", unique=True)
    now = datetime.now(timezone.utc)
    set_fields = {
        "password_hash": hash_password(password),
        "name": name,
        "role": role,
        "updated_at": now,
    }
    # Chỉ ghi đè xa/tinh khi được truyền, để không xóa dữ liệu cũ khi chỉ đổi mật khẩu.
    if xa is not None:
        set_fields["xa"] = xa
    if tinh is not None:
        set_fields["tinh"] = tinh
    res = await db.users.update_one(
        {"username": username.lower()},
        {
            "$set": set_fields,
            "$setOnInsert": {"username": username.lower(), "created_at": now},
        },
        upsert=True,
    )
    action = "Tạo mới" if res.upserted_id else "Cập nhật"
    print(f"{action} user: {username} (role={role})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--xa", default=None, help="Tên xã/phường")
    p.add_argument("--tinh", default=None, help="Tên tỉnh/thành")
    p.add_argument("--role", default="user", choices=["admin", "user", "commune", "province"])
    args = p.parse_args()
    if len(args.password) < 8:
        raise SystemExit("Mật khẩu phải >= 8 ký tự")
    asyncio.run(seed(args.username, args.password, args.name, args.xa, args.tinh, args.role))


if __name__ == "__main__":
    main()
