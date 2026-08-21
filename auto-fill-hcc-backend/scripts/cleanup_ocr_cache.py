"""Dọn OCR cache cũ theo batch rồi chuyển TTL index, mặc định chỉ thống kê.

Chạy trong container backend:
    python -m scripts.cleanup_ocr_cache
    python -m scripts.cleanup_ocr_cache --apply

Mặc định xóa cache có ``created_at`` cũ hơn 12 giờ, mỗi batch 1.000 bản ghi. Khi
chạy ``--apply``, TTL index chỉ được đổi sang 12 giờ sau khi không còn cache quá hạn.
Script chỉ tác động collection MongoDB ``ocr_cache``; không xóa file trong data/uploads.
"""
import argparse
import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from app.db.mongo import close, connect, get_db


_CREATED_AT_KEY = {"created_at": 1}


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("giá trị phải lớn hơn 0")
    return parsed


async def cleanup(
    *,
    older_than_hours: int,
    batch_size: int,
    pause_ms: int,
    apply: bool,
) -> int:
    connect()
    db = get_db()
    collection = db.ocr_cache
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    ttl_seconds = older_than_hours * 3600
    expired_query = {"created_at": {"$lt": cutoff}}

    indexes = await collection.list_indexes().to_list(length=None)
    ttl_index = next(
        (index for index in indexes if dict(index.get("key", {})) == _CREATED_AT_KEY),
        None,
    )
    current_ttl = ttl_index.get("expireAfterSeconds") if ttl_index else None

    expired_before = await collection.count_documents(expired_query)
    invalid_created_at = await collection.count_documents({
        "$or": [
            {"created_at": {"$exists": False}},
            {"created_at": {"$not": {"$type": "date"}}},
        ]
    })

    print(f"Mongo database: {db.name}")
    print(f"Ngưỡng thời gian UTC: {cutoff.isoformat()}")
    print(f"Cache OCR quá {older_than_hours} giờ: {expired_before}")
    print(f"Cache không có created_at hợp lệ (không tự xóa): {invalid_created_at}")
    print(f"TTL index hiện tại: {current_ttl if current_ttl is not None else 'chưa có'} giây")
    print(f"TTL index mục tiêu: {ttl_seconds} giây")

    if not apply:
        print("DRY RUN: chưa xóa dữ liệu. Thêm --apply để thực hiện.")
        return 0

    deleted = 0
    while True:
        documents = await collection.find(
            expired_query,
            {"_id": 1},
        ).sort("created_at", 1).limit(batch_size).to_list(length=batch_size)
        if not documents:
            break

        # Giữ điều kiện created_at trong lệnh delete: nếu request OCR vừa ghi mới lại cùng
        # hash giữa lúc find và delete thì không xóa nhầm cache vừa được làm mới.
        result = await collection.delete_many({
            "_id": {"$in": [document["_id"] for document in documents]},
            "created_at": {"$lt": cutoff},
        })
        deleted += result.deleted_count
        print(f"Đã xóa: {deleted}/{expired_before}")

        if result.deleted_count == 0:
            # Tránh lặp vô hạn nếu toàn bộ batch vừa được request khác cập nhật created_at.
            break
        if pause_ms:
            await asyncio.sleep(pause_ms / 1000)

    remaining = await collection.count_documents(expired_query)
    print(f"Hoàn tất. Đã xóa: {deleted}")
    print(f"Còn lại quá {older_than_hours} giờ: {remaining}")
    if remaining:
        print("KHÔNG đổi TTL index vì vẫn còn cache quá hạn.")
        return 2

    if ttl_index is None:
        await collection.create_index("created_at", expireAfterSeconds=ttl_seconds)
        print(f"Đã tạo TTL index: {ttl_seconds} giây.")
    elif current_ttl != ttl_seconds:
        # create_index không thể đổi option của index đã tồn tại. collMod giữ nguyên index,
        # tránh phải drop/recreate và chỉ chạy sau khi dữ liệu cũ đã được dọn theo batch.
        await db.command({
            "collMod": collection.name,
            "index": {
                "name": ttl_index["name"],
                "expireAfterSeconds": ttl_seconds,
            },
        })
        print(f"Đã đổi TTL index: {current_ttl} -> {ttl_seconds} giây.")
    else:
        print("TTL index đã đúng, không cần thay đổi.")
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dọn MongoDB OCR cache cũ theo batch (mặc định dry-run).",
    )
    parser.add_argument(
        "--older-than-hours",
        type=_positive_int,
        default=12,
        help="Xóa cache cũ hơn số giờ này (mặc định: 12)",
    )
    parser.add_argument(
        "--batch-size",
        type=_positive_int,
        default=1000,
        help="Số bản ghi tối đa mỗi lượt xóa (mặc định: 1000)",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=100,
        help="Thời gian nghỉ giữa các batch, milliseconds (mặc định: 100)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Thực sự xóa; không truyền cờ này thì chỉ thống kê",
    )
    args = parser.parse_args(argv)
    if args.pause_ms < 0:
        parser.error("--pause-ms không được âm")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return asyncio.run(cleanup(
            older_than_hours=args.older_than_hours,
            batch_size=args.batch_size,
            pause_ms=args.pause_ms,
            apply=args.apply,
        ))
    finally:
        close()


if __name__ == "__main__":
    raise SystemExit(main())
