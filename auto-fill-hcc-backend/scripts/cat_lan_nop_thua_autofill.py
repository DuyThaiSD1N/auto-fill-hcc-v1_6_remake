"""Cắt các lần nộp THỪA của hồ sơ Auto Fill cũ: giữ đúng số hồ sơ mà lượt đính kèm cuối tạo ra.

Trước bản sửa, tab còn giữ khóa hồ sơ thì mọi cú bấm nộp sau đó (bấm lại, hồ sơ làm tay không qua trợ
lý) đều ghi vào khóa cũ → số hồ sơ cộng thừa, "thời gian làm" kéo tới lần nộp cuối. Hạn mức cùng luật với
`app.dossiers.repo.autofill_submit_quota` (tách N tab → N, không đính kèm → 1) — chép lại ở đây để
script chạy được trên image chưa có hàm đó. Giữ N cú bấm
SỚM NHẤT; bản gốc cất vào `submit_trim_backup` để --revert.

Bỏ qua ba thủ tục chứng thực: thống kê đếm mỗi lần nộp của nhóm này là một hồ sơ (app/dossiers/stats.py),
cắt là đổi số đã báo cáo. Thủ tục khác vốn đếm một hồ sơ một document và lấy lần nộp SỚM NHẤT → số báo cáo
không đổi, chỉ sửa "thời gian làm" và số lần nộp hiển thị.

`--chung-thuc`: chỉ ba thủ tục chứng thực, GIỮ NGUYÊN mọi lần nộp (số hồ sơ báo cáo không đổi), chỉ dời
`submit_clicked_at` về lần nộp thứ N → "thời gian làm" tính tới hết lượt trợ lý, khớp luật đang chạy.

Chạy trong container backend:
    python -m scripts.cat_lan_nop_thua_autofill                    # chạy thử: chỉ in số liệu
    python -m scripts.cat_lan_nop_thua_autofill --tu 2026-09-15 --den 2026-11-24
    python -m scripts.cat_lan_nop_thua_autofill --apply
    python -m scripts.cat_lan_nop_thua_autofill --chung-thuc [--apply]
    python -m scripts.cat_lan_nop_thua_autofill --revert           # trả lại bản gốc (cần --apply để ghi)
    python -m scripts.cat_lan_nop_thua_autofill --revert --apply
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.db.mongo import close, connect, get_db

VN = timezone(timedelta(hours=7))
BACKUP = "submit_trim_backup"
CHUNG_THUC = ["chung-thuc-ban-sao", "chung-thuc-chu-ky", "chung-thuc-chu-ky-nguoi-dich-ctv"]


async def _quota(db, dossier_id: str) -> int:
    trace = await db.traces.find_one({"dossier_id": dossier_id, "kind": "attach"}, {"dossier_ids": 1},
                                     sort=[("created_at", -1)])
    return max(len((trace or {}).get("dossier_ids") or []), 1)


def _vn_day(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=VN).astimezone(timezone.utc).replace(tzinfo=None)


def _range(args) -> dict:
    rng: dict = {}
    if args.tu:
        rng["$gte"] = _vn_day(args.tu)
    if args.den:
        rng["$lt"] = _vn_day(args.den) + timedelta(days=1)
    return {"started_at": rng} if rng else {}


async def trim(args) -> None:
    db = get_db()
    query = {"experience": "autofill", "submit_events.1": {"$exists": True}, BACKUP: {"$exists": False},
             "procedure": {"$in" if args.chung_thuc else "$nin": CHUNG_THUC}, **_range(args)}
    scanned = changed = removed = 0
    by_proc: Counter = Counter()
    async for doc in db.dossiers.find(query, {"submit_events": 1, "submit_count": 1, "submit_clicked_at": 1,
                                              "portal_host": 1, "procedure": 1}):
        scanned += 1
        events = sorted(doc.get("submit_events") or [], key=lambda e: e.get("at") or datetime.min)
        quota = await _quota(db, doc["_id"])
        if len(events) <= quota:
            continue
        kept = events[:quota]
        changed += 1
        removed += len(events) - quota
        by_proc[doc.get("procedure") or "?"] += 1
        if not args.apply:
            continue
        if args.chung_thuc:
            await db.dossiers.update_one({"_id": doc["_id"], BACKUP: {"$exists": False}}, {"$set": {
                BACKUP: {"chi_thoi_gian": True, "submit_clicked_at": doc.get("submit_clicked_at"),
                         "portal_host": doc.get("portal_host"), "trimmed_at": datetime.now(timezone.utc)},
                "submit_clicked_at": kept[-1].get("at"),
                "portal_host": kept[-1].get("host") or doc.get("portal_host"),
            }})
            continue
        await db.dossiers.update_one({"_id": doc["_id"], BACKUP: {"$exists": False}}, {"$set": {
            BACKUP: {"submit_events": doc.get("submit_events") or [], "submit_count": doc.get("submit_count"),
                     "submit_clicked_at": doc.get("submit_clicked_at"), "portal_host": doc.get("portal_host"),
                     "trimmed_at": datetime.now(timezone.utc)},
            "submit_events": kept,
            "submit_count": len(kept),
            "submit_clicked_at": kept[-1].get("at"),
            "portal_host": kept[-1].get("host") or doc.get("portal_host"),
        }})
    print(f"Hồ sơ Auto Fill có ≥2 lần nộp: {scanned}")
    print(f"Hồ sơ vượt hạn mức: {changed} · lần nộp thừa: {removed}"
          + (" (giữ nguyên, chỉ dời mốc nộp cuối)" if args.chung_thuc else ""))
    for proc, n in by_proc.most_common(15):
        print(f"  {n:5d}  {proc}")
    print("ĐÃ GHI." if args.apply else "Chạy thử — chưa ghi gì. Thêm --apply để ghi.")


async def revert(args) -> None:
    db = get_db()
    query = {"experience": "autofill", BACKUP: {"$exists": True}, **_range(args)}
    if args.chung_thuc:
        query["procedure"] = {"$in": CHUNG_THUC}
    total = await db.dossiers.count_documents(query)
    print(f"Hồ sơ đã cắt, có bản gốc để trả lại: {total}")
    if not args.apply:
        print("Chạy thử — chưa ghi gì. Thêm --apply để trả lại.")
        return
    async for doc in db.dossiers.find(query, {BACKUP: 1}):
        b = doc[BACKUP]
        if b.get("chi_thoi_gian"):
            await db.dossiers.update_one({"_id": doc["_id"]}, {
                "$set": {"submit_clicked_at": b.get("submit_clicked_at"), "portal_host": b.get("portal_host")},
                "$unset": {BACKUP: ""},
            })
            continue
        await db.dossiers.update_one({"_id": doc["_id"]}, {
            "$set": {"submit_events": b.get("submit_events") or [], "submit_count": b.get("submit_count"),
                     "submit_clicked_at": b.get("submit_clicked_at"), "portal_host": b.get("portal_host")},
            "$unset": {BACKUP: ""},
        })
    print("ĐÃ TRẢ LẠI.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tu", help="ngày bắt đầu hồ sơ (VN), YYYY-MM-DD")
    p.add_argument("--den", help="ngày bắt đầu hồ sơ (VN), YYYY-MM-DD, tính cả ngày này")
    p.add_argument("--apply", action="store_true", help="ghi thật")
    p.add_argument("--revert", action="store_true", help="trả lại bản gốc đã cất")
    p.add_argument("--chung-thuc", action="store_true",
                   help="chỉ ba thủ tục chứng thực: giữ mọi lần nộp, chỉ dời mốc nộp cuối")
    asyncio.run(_run(p.parse_args()))


async def _run(args) -> None:
    connect()
    try:
        await (revert(args) if args.revert else trim(args))
    finally:
        close()


if __name__ == "__main__":
    main()
