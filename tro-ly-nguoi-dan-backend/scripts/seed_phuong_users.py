"""Tạo / cập nhật tài khoản cho các phường (admin seed, không self-registration).

Chạy 1 lần là tạo (hoặc cập nhật mật khẩu) tất cả tài khoản trong DANH_SACH.
Cần .env trỏ đúng Mongo.

    python -m scripts.seed_phuong_users
"""
import asyncio
from datetime import datetime, timezone

from app.core.security import hash_password
from app.db.mongo import connect, get_db

# (username, password, name, xa, tinh, role)
DANH_SACH = [
    ("hcctanphong", "hcctanphong12", "Phường Tân Phong", "Tân Phong", "Lai Châu", "user"),
    ("hccdoanket", "hccdoanket12", "Phường Đoàn Kết", "Đoàn Kết", "Lai Châu", "user"),
    ("hcclamvien", "hcclamvien86", "Phường Lâm Viên - Lâm Đồng", "Lâm Viên", "Lâm Đồng", "user"),
    ("hccxuantruong", "hccxuantruong86", "Phường Xuân Trường - Lâm Đồng", "Xuân Trường", "Lâm Đồng", "user"),
    ("hcclangbiang", "hcclangbiang86", "Phường Lang biang - Lâm Đồng", "Lang Biang", "Lâm Đồng", "user"),
    ("hcccamly", "hcccamly86", "Phường Cam ly - Lâm Đồng", "Cam Ly", "Lâm Đồng", "user"),
    ("hccxuanhuong", "hccxuanhuong86", "Phường Xuân Hương- Lâm Đồng", "Xuân Hương", "Lâm Đồng", "user"),
    ("hcctaleng", "hcctaleng12", "Xã Tả Lèng", "Tả Lèng", "Lai Châu", "user"),
]


async def seed_one(db, username: str, password: str, name: str, xa: str, tinh: str, role: str) -> None:
    now = datetime.now(timezone.utc)
    res = await db.users.update_one(
        {"username": username.lower()},
        {
            "$set": {
                "password_hash": hash_password(password),
                "name": name,
                "xa": xa,
                "tinh": tinh,
                "role": role,
                "updated_at": now,
            },
            "$setOnInsert": {"username": username.lower(), "created_at": now},
        },
        upsert=True,
    )
    action = "Tạo mới" if res.upserted_id else "Cập nhật"
    print(f"{action} user: {username} ({name}) — {xa}/{tinh} [{role}]")


async def seed_all() -> None:
    connect()
    db = get_db()
    await db.users.create_index("username", unique=True)
    for username, password, name, xa, tinh, role in DANH_SACH:
        if len(password) < 8:
            raise SystemExit(f"Mật khẩu của {username} phải >= 8 ký tự")
        await seed_one(db, username, password, name, xa, tinh, role)


if __name__ == "__main__":
    asyncio.run(seed_all())
