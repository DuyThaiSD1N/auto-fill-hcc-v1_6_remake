"""Quản lý API key của nhóm API thống kê đối tác (/partner-api/v1).

Key gốc chỉ in ra MỘT lần khi tạo; Mongo chỉ giữ sha256. Mất key thì thu hồi rồi tạo key mới.
Mặc định chỉ in kế hoạch; thêm ``--apply`` để ghi.

Ví dụ:
    python -m scripts.api_keys list
    python -m scripts.api_keys create --name "Anh Quyền - netbird" --apply
    python -m scripts.api_keys create --name "Sở Lâm Đồng" --province "Tỉnh Lâm Đồng" --apply
    python -m scripts.api_keys revoke --id <id trong list> --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json

from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo import close, get_db
from app.partner_api.keys import GROUP_STATS, hash_key, new_key, now
from app.reports.integration import province_name


def _iso(value):
    return value.isoformat() if value else None


async def _list() -> dict:
    docs = await get_db().api_keys.find({"group": GROUP_STATS}).sort("created_at", -1).to_list(length=None)
    return {"keys": [
        {
            "id": str(d["_id"]),
            "name": d.get("name"),
            "prefix": d.get("prefix"),
            "scope": d.get("scope"),
            "createdAt": _iso(d.get("created_at")),
            "lastUsedAt": _iso(d.get("last_used_at")),
            "revokedAt": _iso(d.get("revoked_at")),
        }
        for d in docs
    ]}


async def _create(name: str, province: str | None, apply: bool) -> dict:
    scope = {"kind": "province", "tinh": province_name(province) or province} if province else {"kind": "all"}
    plan = {"action": "create", "name": name, "scope": scope, "applied": False}
    if not apply:
        return {**plan, "message": "Dry-run; chạy lại với --apply để tạo key."}
    raw = new_key()
    await get_db().api_keys.insert_one({
        "name": name,
        "group": GROUP_STATS,
        "prefix": raw[:14],
        "key_hash": hash_key(raw),
        "scope": scope,
        "created_at": now(),
        "last_used_at": None,
        "revoked_at": None,
    })
    return {**plan, "applied": True, "apiKey": raw, "message": "Lưu key này ngay: không xem lại được."}


async def _revoke(key_id: str, apply: bool) -> dict:
    try:
        oid = ObjectId(key_id)
    except (InvalidId, TypeError):
        raise ValueError("id không hợp lệ")
    doc = await get_db().api_keys.find_one({"_id": oid, "group": GROUP_STATS})
    if not doc:
        raise ValueError("Không tìm thấy key")
    plan = {"action": "revoke", "id": key_id, "name": doc.get("name"), "applied": False}
    if not apply:
        return {**plan, "message": "Dry-run; chạy lại với --apply để thu hồi."}
    await get_db().api_keys.update_one({"_id": oid}, {"$set": {"revoked_at": now()}})
    return {**plan, "applied": True}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Liệt kê key (không in key gốc).")
    create = sub.add_parser("create", help="Tạo key mới.")
    create.add_argument("--name", required=True, help="Tên gợi nhớ: ai dùng, dùng ở đâu.")
    create.add_argument("--province", help="Khoá key theo một tỉnh; bỏ trống = toàn hệ thống.")
    create.add_argument("--apply", action="store_true")
    revoke = sub.add_parser("revoke", help="Thu hồi key.")
    revoke.add_argument("--id", required=True)
    revoke.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.cmd == "list":
            report = asyncio.run(_list())
        elif args.cmd == "create":
            report = asyncio.run(_create(args.name.strip(), args.province, args.apply))
        else:
            report = asyncio.run(_revoke(args.id, args.apply))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI chỉ in loại lỗi.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
