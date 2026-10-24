from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta, timezone

from app.archive.keys import with_keys
from app.archive.config import archive_settings
from app.db.mongo import close, connect, get_db
from app.traces.repo import (
    _daily_stats_pipeline,
    _format_daily_dossier_counts,
    _format_stats_facets,
    _stats_pipeline,
)

_NAMES = ["CCCD mặt trước.jpg", "cccd mặt trước.JPG", "CCCD  mặt trước.jpg", "Giấy khai sinh.pdf",
          "GIẤY KHAI SINH.pdf", "giấy khai sinh.PDF", "Đơn đề nghị.docx", "đơn đề nghị.pdf", ".jpg",
          "scan 01.png", "scan 01.jpeg", "Hộ chiếu.pdf", "tai lieu", "", None, "a.b.c.pdf", "x y.pdf"]
_ROLES = ["", "Giấy tờ tùy thân", "Bản chính", "Tài liệu cần chứng thực", "CĂN CƯỚC"]
_PROCS = ["chung-thuc-chu-ky", "chung-thuc-ban-sao", "khai-sinh", "ket-hon"]
_WINDOW = timedelta(days=7)
_LABELS = {"name", "label"}


def _fake_traces(n: int, rng: random.Random) -> list[dict]:
    base = datetime(2026, 8, 20, tzinfo=timezone.utc)
    docs = []
    for i in range(n):
        split = rng.random() < 0.3
        exact = rng.random() < 0.5
        docs.append({
            "request_id": f"r{i}",
            "user_id": f"u{rng.randrange(4)}", "name": "Xã thử", "procedure": rng.choice(_PROCS),
            "experience": "autofill", "split": split,
            "stats_version": 2 if exact else 1,
            "dossier_ids": [f"r{i}:{k}" for k in range(rng.randrange(1, 3))] if exact else [],
            "attachments": [{"name": rng.choice(_NAMES), "role": rng.choice(_ROLES),
                             "sha256": None, "uses": 1} for _ in range(rng.randrange(0, 4))],
            "created_at": base + timedelta(hours=rng.randrange(0, 24 * 40)),
        })
    return docs


async def _run(coll, start: datetime, end: datetime) -> tuple[dict, list]:
    query = {"created_at": {"$gte": start, "$lt": end}}
    total = await coll.aggregate(_stats_pipeline(query), allowDiskUse=True).to_list(length=1)
    daily = await coll.aggregate(_daily_stats_pipeline(query), allowDiskUse=True).to_list(length=1)
    return (_format_stats_facets(total[0] if total else {}),
            _format_daily_dossier_counts(daily[0] if daily else {}))


def _diff(a, b, path: str, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted((set(a) | set(b)) - _LABELS, key=str):
            _diff(a.get(k), b.get(k), f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        ident = lambda x: (x.get("userId"), x.get("key"), x.get("date")) if isinstance(x, dict) else None  # noqa: E731
        ia, ib = [ident(x) for x in a], [ident(x) for x in b]
        if sorted(map(str, ia)) == sorted(map(str, ib)) and ia != ib:
            b = sorted(b, key=lambda x: ia.index(ident(x)))
        if len(a) != len(b):
            out.append(f"{path}: số phần tử {len(a)} ≠ {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            tag = ident(x) if ident(x) and any(ident(x)) else i
            _diff(x, y, f"{path}[{tag}]", out)
    elif a != b:
        out.append(f"{path}: tên={str(a)[:120]!r} khoá={str(b)[:120]!r}")


def _total(stats: dict) -> int:
    return sum(int(w.get("total") or 0) for w in stats.get("wards") or [])


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0, help="Sinh N trace giả thay vì đọc traces thật")
    args = ap.parse_args()
    if not archive_settings.archive_hmac_key:
        print("Thiếu ARCHIVE_HMAC_KEY")
        return 2

    connect()
    db = get_db()
    names, keys = db["_chk_names"], db["_chk_keys"]
    await names.drop()
    await keys.drop()
    try:
        if args.seed:
            source = _fake_traces(args.seed, random.Random(42))
        else:
            source = await db.traces.find({}, {"ocr_text": 0, "llm_output": 0, "report": 0}).to_list(None)
        if not source:
            print("Không có trace nào.")
            return 0
        name_docs, key_docs = [], []
        for doc in source:
            plain = [{k: v for k, v in a.items() if k not in ("nk", "sk", "idd")}
                     for a in doc.get("attachments") or [] if isinstance(a, dict)]
            name_docs.append({**doc, "attachments": plain})
            key_docs.append({**doc, "attachments": [{k: v for k, v in a.items() if k != "name"}
                                                    for a in with_keys(plain)]})
        await names.insert_many(name_docs)
        await keys.insert_many(key_docs)

        dates = [d["created_at"] for d in source if d.get("created_at")]
        start, stop = min(dates), max(dates) + timedelta(seconds=1)
        windows = bad = 0
        sums = [0, 0]
        while start < stop:
            end = min(start + _WINDOW, stop)
            before = await _run(names, start, end)
            after = await _run(keys, start, end)
            windows += 1
            sums[0] += _total(before[0])
            sums[1] += _total(after[0])
            for label, a, b in (("tổng", before[0], after[0]), ("theo ngày", before[1], after[1])):
                out: list[str] = []
                _diff(a, b, "", out)
                if out:
                    bad += 1
                    print(f"LỆCH {start:%Y-%m-%d}→{end:%Y-%m-%d} {label}: {len(out)} chỗ")
                    for line in out[:8]:
                        print(f"  {line}")
            start = end
        print(f"{len(source)} trace ({len(source) - len(dates)} không có created_at) · {windows} tuần · "
              f"tổng hồ sơ: tên={sums[0]} khoá={sums[1]}")
        if bad:
            print("LỆCH — không được xoá tên tệp.")
            return 1
        print("KHỚP — thống kê không đổi khi thay tên bằng khoá băm.")
        return 0
    finally:
        await names.drop()
        await keys.drop()
        close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
