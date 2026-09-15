"""Xoá các hồ sơ RỖNG đã lỡ vào sổ — mặc định chỉ thống kê, không xoá.

Trong Docker production (đúng khuôn scripts/check_ward_dossier_count.py)::

    # 1) Xem trước — CHỈ đếm và in thử, không đụng dữ liệu
    docker compose -f compose.prod.yml exec app \
      python -m scripts.cleanup_empty_dossiers

    # 2) Xoá thật, sau khi đã nhìn kỹ danh sách ở bước 1
    docker compose -f compose.prod.yml exec app \
      python -m scripts.cleanup_empty_dossiers --apply

    # In nhiều dòng hơn để soi (mặc định 20)
    docker compose -f compose.prod.yml exec app \
      python -m scripts.cleanup_empty_dossiers --limit 100

Máy dev (đã có .env trỏ đúng Mongo)::

    python -m scripts.cleanup_empty_dossiers --apply

Hồ sơ RỖNG = không có lượt điền/đính kèm nào (không trace nào trỏ tới) VÀ chưa từng bấm nộp
VÀ chưa có phiếu đánh giá. Chúng sinh ra vì Handfree chấm mốc bắt đầu ngay lúc xác nhận thủ
tục, nên cán bộ chọn thủ tục rồi bỏ giữa chừng cũng để lại một dòng trong danh sách quản trị.

Bản vá ở `chat/router.py::_sync_dossier` đã chặn sinh mới; script này dọn phần đã lỡ.
Chỉ động vào collection `dossiers`; KHÔNG xoá trace, không xoá file trong data/uploads.
"""
import argparse
import asyncio

from app.db.mongo import close, connect, get_db

# Có bất kỳ dấu hiệu nào trong số này = hồ sơ THẬT, tuyệt đối không đụng tới.
_HAS_WORK = {
    "$or": [
        {"submit_clicked_at": {"$ne": None}},
        {"submit_count": {"$gt": 0}},
        {"rating": {"$ne": None}},
    ]
}


async def _run(apply: bool, limit: int) -> None:
    connect()  # đồng bộ (chỉ dựng AsyncIOMotorClient), KHÔNG await — xem app/db/mongo.py
    db = get_db()
    try:
        # Hồ sơ nào có trace thì giữ. Lấy trọn tập dossier_id đã từng có lượt điền/đính kèm —
        # tập này nhỏ (một dòng mỗi hồ sơ) nên gom về bộ nhớ được, khỏi $lookup từng dòng.
        with_trace = set(await db.traces.distinct("dossier_id", {"dossier_id": {"$ne": None}}))
        print(f"Hồ sơ từng có lượt điền/đính kèm: {len(with_trace)}")

        candidates = []
        async for doc in db.dossiers.find({"$nor": [_HAS_WORK]}, {"_id": 1, "procedure_label": 1,
                                                                 "started_at": 1, "experience": 1}):
            if doc["_id"] not in with_trace:
                candidates.append(doc)

        print(f"Hồ sơ RỖNG tìm thấy: {len(candidates)}")
        for doc in candidates[:limit]:
            print(f"  - {doc['_id']}  {doc.get('started_at')}  [{doc.get('experience')}]  "
                  f"{(doc.get('procedure_label') or '')[:60]}")
        if len(candidates) > limit:
            print(f"  … còn {len(candidates) - limit} dòng nữa")

        if not apply:
            print("\nMới chỉ THỐNG KÊ. Thêm --apply để xoá thật.")
            return
        if not candidates:
            return
        res = await db.dossiers.delete_many({"_id": {"$in": [d["_id"] for d in candidates]}})
        print(f"\nĐã xoá {res.deleted_count} hồ sơ rỗng.")
    finally:
        close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="xoá thật (mặc định chỉ thống kê)")
    parser.add_argument("--limit", type=int, default=20, help="số dòng in ra để xem thử")
    args = parser.parse_args()
    asyncio.run(_run(args.apply, args.limit))


if __name__ == "__main__":
    main()
