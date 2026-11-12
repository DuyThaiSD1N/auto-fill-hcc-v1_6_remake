"""Bù mốc nộp cho hồ sơ thủ tục cổng Khánh Hòa làm trước khi BE có luật nhận nộp của cổng này.

Cổng dichvucong.khanhhoa.gov.vn chưa có trong app/procedures/portal_submit.py nên cú bấm "Đồng ý" (nút nộp) không
được ghi → hồ sơ đã nộp vẫn nằm ở "chưa nộp". Không có dữ liệu cú bấm thật, nên mốc nộp tái tạo
= lượt đính kèm CUỐI của hồ sơ (trace kind="attach") + N phút. Hồ sơ không có lượt đính kèm nào thì bỏ qua.

Chỉ chạm hồ sơ: đúng tên đơn vị (dossiers.name), thủ tục có urlScope khanhhoa.gov.vn, đang chưa có mốc nộp.
Sự kiện ghi qua dossiers.repo.add_submit_event, mang id "backfill-khanhhoa:<id hồ sơ>" → chạy lại không ghi đôi,
--revert gỡ đúng các sự kiện này.

Chạy trong container backend:
    python -m scripts.backfill_submit_khanh_hoa --ten "HCC Phường Nam Nha Trang" --den 2026-11-12
    python -m scripts.backfill_submit_khanh_hoa --ten "HCC Phường Nam Nha Trang" --den 2026-11-12 --apply
    python -m scripts.backfill_submit_khanh_hoa --ten "HCC Phường Nam Nha Trang" --revert --apply
"""
import argparse
import asyncio
import re
from datetime import datetime, timedelta, timezone

from app.db.mongo import close, connect, get_db
from app.dossiers import repo as dossiers_repo
from app.procedures.registry import PROCEDURES

VN = timezone(timedelta(hours=7))
HOST = "dichvucong.khanhhoa.gov.vn"
ID_PREFIX = "backfill-khanhhoa:"


def _procedure_keys() -> list[str]:
    return [
        p["key"] for p in PROCEDURES
        if "khanhhoa.gov.vn" in ((p.get("detect") or {}).get("urlScope") or [])
    ]


def _vn_day(value: str, end: bool) -> datetime:
    """Ngày VN (YYYY-MM-DD) → datetime UTC naive như Motor lưu; end=True lấy hết ngày đó."""
    day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=VN)
    if end:
        day += timedelta(days=1) - timedelta(microseconds=1)
    return day.astimezone(timezone.utc).replace(tzinfo=None)


def _vn(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.replace(tzinfo=timezone.utc).astimezone(VN).strftime("%H:%M %d/%m/%Y")


def _name_query(name: str) -> dict:
    return {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}


async def backfill(*, name: str, date_from: str | None, date_to: str | None, minutes: int, apply: bool) -> None:
    db = get_db()
    keys = _procedure_keys()
    query: dict = {"name": _name_query(name), "procedure": {"$in": keys}, "submit_clicked_at": None}
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["$gte"] = _vn_day(date_from, end=False)
        if date_to:
            rng["$lte"] = _vn_day(date_to, end=True)
        query["started_at"] = rng
    docs = await db.dossiers.find(
        query, {"_id": 1, "procedure": 1, "started_at": 1, "username": 1}
    ).sort("started_at", 1).to_list(length=None)
    print(f"Thủ tục Khánh Hòa: {len(keys)} · hồ sơ chưa nộp khớp lọc: {len(docs)}")

    planned, skipped = 0, 0
    for doc in docs:
        last = await db.traces.find_one(
            {"dossier_id": doc["_id"], "kind": "attach"}, {"created_at": 1}, sort=[("created_at", -1)]
        )
        if not last or not last.get("created_at"):
            skipped += 1
            print(f"  BỎ (không có lượt đính kèm)  {doc['_id']}  bắt đầu {_vn(doc.get('started_at'))}  {doc.get('procedure')}")
            continue
        at = last["created_at"] + timedelta(minutes=minutes)
        planned += 1
        print(f"  NỘP {_vn(at)}  (đính cuối {_vn(last['created_at'])})  {doc['_id']}  "
              f"bắt đầu {_vn(doc.get('started_at'))}  {doc.get('username')}  {doc.get('procedure')}")
        if apply:
            await dossiers_repo.add_submit_event(
                dossier_id=doc["_id"],
                clicked_at=at.replace(tzinfo=timezone.utc),
                portal_host=HOST,
                click_id=ID_PREFIX + doc["_id"],
                source="backfill",
            )
    print(f"Ghi mốc: {planned} · bỏ qua: {skipped} · {'ĐÃ GHI' if apply else 'CHẠY THỬ — thêm --apply để ghi'}")


async def revert(*, name: str, apply: bool) -> None:
    db = get_db()
    docs = await db.dossiers.find(
        {"name": _name_query(name), "submit_events.id": {"$regex": f"^{re.escape(ID_PREFIX)}"}},
        {"_id": 1, "submit_events": 1},
    ).to_list(length=None)
    print(f"Hồ sơ có mốc bù: {len(docs)}")
    for doc in docs:
        events = doc.get("submit_events") or []
        keep = [e for e in events if not str(e.get("id") or "").startswith(ID_PREFIX)]
        removed = len(events) - len(keep)
        latest = max((e["at"] for e in keep if e.get("at")), default=None)
        print(f"  GỠ {removed} mốc  {doc['_id']}  → còn {len(keep)} mốc, mốc nộp {_vn(latest)}")
        if apply:
            update: dict = {"$set": {"submit_events": keep, "submit_count": len(keep), "submit_clicked_at": latest}}
            if not keep:
                update["$unset"] = {"portal_host": ""}
            await db.dossiers.update_one({"_id": doc["_id"]}, update)
    print("ĐÃ GỠ" if apply else "CHẠY THỬ — thêm --apply để gỡ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ten", required=True, help='Tên đơn vị đúng như cột Phường, vd "HCC Phường Nam Nha Trang"')
    parser.add_argument("--tu", help="Lọc ngày bắt đầu hồ sơ từ (YYYY-MM-DD, giờ VN)")
    parser.add_argument("--den", help="Lọc ngày bắt đầu hồ sơ đến hết ngày (YYYY-MM-DD, giờ VN)")
    parser.add_argument("--phut", type=int, default=3, help="Mốc nộp = đính kèm cuối + số phút (mặc định 3)")
    parser.add_argument("--revert", action="store_true", help="Gỡ các mốc nộp do script này ghi")
    parser.add_argument("--apply", action="store_true", help="Ghi thật (mặc định chỉ chạy thử)")
    args = parser.parse_args()

    async def run() -> None:
        connect()
        try:
            if args.revert:
                await revert(name=args.ten, apply=args.apply)
            else:
                await backfill(name=args.ten, date_from=args.tu, date_to=args.den,
                               minutes=args.phut, apply=args.apply)
        finally:
            close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
