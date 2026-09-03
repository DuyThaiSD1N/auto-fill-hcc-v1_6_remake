"""Liệt kê tài khoản Auto Fill để đối chiếu phạm vi báo cáo.

Cách chạy (dùng đúng .env/Mongo của môi trường cần kiểm tra):
    python -m scripts.list_report_accounts

Chỉ đọc và in 4 trường phục vụ đối chiếu; không lấy mật khẩu, token hay dữ liệu phiên.
"""
import asyncio

from app.db.mongo import close, connect, get_db


_HEADERS = ("username", "name", "xã", "tỉnh")


def _cell(value: object) -> str:
    text = " ".join(str(value or "").split())
    return text or "—"


def format_accounts(accounts: list[dict]) -> str:
    rows = [
        (
            _cell(account.get("username")),
            _cell(account.get("name")),
            _cell(account.get("xa")),
            _cell(account.get("tinh")),
        )
        for account in sorted(accounts, key=lambda item: _cell(item.get("username")).casefold())
    ]
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(_HEADERS)
    ]

    def render(row: tuple[str, ...]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join([render(_HEADERS), separator, *(render(row) for row in rows)])


async def list_accounts() -> list[dict]:
    connect()
    projection = {"username": 1, "name": 1, "xa": 1, "tinh": 1}
    cursor = get_db().users.find({}, projection).sort("username", 1)
    return [account async for account in cursor]


async def main() -> None:
    try:
        accounts = await list_accounts()
        print("Hệ thống: Auto Fill")
        print(f"Tổng tài khoản: {len(accounts)}")
        print(format_accounts(accounts))
    finally:
        close()


if __name__ == "__main__":
    asyncio.run(main())
