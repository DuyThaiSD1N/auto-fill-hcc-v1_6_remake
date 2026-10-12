"""Dòng lệnh luồng mới — xem scripts/luongmoi/__init__.py."""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from scripts.luongmoi import cham, du_lieu, luong


def _short(value, width: int = 90) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _report(result: dict, ket_qua: dict) -> list[str]:
    t = result["thoi_gian"]
    lines = [f"===== {result['rid']} (lượt {result['luot']})",
             f"  thời gian: output1≈{t['uoc_output1_s']}s · OCR Qwen {t['qwen_ocr_s']}s"
             f"{' (cache)' if t['qwen_tu_cache'] else ''} · agent {t['agent_s']}s → output2≈{t['uoc_output2_s']}s"]
    goi_y = result["agent"]["goi_y"]
    if not goi_y.startswith("- (không"):
        lines.append("  gợi ý code: " + goi_y.replace("\n", " | "))
    for row in result["output2"]["review"]:
        kq = (ket_qua.get("co") or {}).get(row["name"], "")
        lines.append(f"  [{row['flag']:8}] {row['name']}: {_short(row['old'], 60)}"
                     + (f"  →  {_short(row['value'], 70)}" if row["flag"] == "sua" else f"  | qwen: {_short(row['qwen'], 50)}")
                     + (f"   «{kq}»" if kq else "") + (f"   ({row['chot']})" if row.get("chot") else "")
                     + f"   → ô {','.join(row.get('ui_keys') or [])}")
    for row in ket_qua.get("lot") or []:
        lines.append(f"  [LỌT {row['nhom']}] {row['name']}: v1={_short(row['v1'], 60)} | giấy={_short(row['giay'], 70)}")
    if not result["output2"]["review"]:
        lines.append("  (không có cờ)")
    return lines


async def main() -> None:
    ap = argparse.ArgumentParser(description="Thử luồng rà soát lần 2 bằng OCR Qwen (TTHN)")
    ap.add_argument("rids", nargs="*")
    ap.add_argument("--manifest", help="manifest.json của prod_trace collect — lấy mọi mã trong đó")
    ap.add_argument("--files", nargs="*", default=[], help="tệp lẻ không có trace prod; mỗi tệp là một hồ sơ")
    ap.add_argument("--runs", type=int, default=1, help="số lượt mỗi hồ sơ (v1 dao động giữa các lượt)")
    ap.add_argument("--qwen-moi", action="store_true", help="OCR Qwen lại, bỏ cache")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()

    if args.manifest:
        args.rids += [r["request_id"] for r in json.loads(open(args.manifest).read())["picked"]]
    out_dir = du_lieu.out_root() / "_luongmoi" / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = {rid: du_lieu.load(rid) for rid in args.rids}
    for path in args.files:
        case = await du_lieu.load_file(Path(path).resolve())
        cases[case["rid"]] = case
        args.rids.append(case["rid"])
    # OCR Qwen mỗi hồ sơ một lần trước (lượt đầu đo thời gian thật), các lượt sau dùng cache.
    sem = asyncio.Semaphore(args.concurrency)

    async def one(rid: str, luot: int):
        async with sem:
            res = await luong.chay(cases[rid], refresh_qwen=args.qwen_moi and luot == 1)
        res["luot"] = luot
        return res

    results = []
    for luot in range(1, args.runs + 1):
        results += await asyncio.gather(*(one(rid, luot) for rid in args.rids))

    lines, tally, times = [], Counter(), {"agent_s": [], "uoc_output2_s": []}
    by_group: dict[str, Counter] = defaultdict(Counter)
    for res in sorted(results, key=lambda r: (r["rid"], r["luot"])):
        path = out_dir / f"{res['rid']}_l{res['luot']}.json"
        path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        ket_qua = cham.danh_gia(res, cham.load(cases[res["rid"]]["dir"]))
        res["cham"] = ket_qua
        path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        lines += _report(res, ket_qua)
        tally.update(res_kq for res_kq in (ket_qua.get("co") or {}).values())
        tally.update(f"{r['loai']} {r['nhom']}" for r in ket_qua.get("lot") or [])
        for name, kq in (ket_qua.get("co") or {}).items():
            by_group[cham.nhom(name)][kq.split(" (")[0]] += 1
        for r in ket_qua.get("lot") or []:
            if r["loai"] == "lọt":
                by_group[cham.nhom(r["name"])]["lọt"] += 1
        tally.update(f"cờ {r['flag']}" for r in res["output2"]["review"])
        for k in times:
            times[k].append(res["thoi_gian"][k])
    lines += ["", f"===== TỔNG ({len(results)} lượt hồ sơ)", "  " + " · ".join(f"{k}: {v}" for k, v in sorted(tally.items())),
              "  agent: trung vị {:.1f}s, max {:.1f}s · output2 ước: trung vị {:.1f}s, max {:.1f}s".format(
                  statistics.median(times["agent_s"]), max(times["agent_s"]),
                  statistics.median(times["uoc_output2_s"]), max(times["uoc_output2_s"]))]
    lines += ["", "===== THEO NHÓM Ô (gộp mọi lượt)"]
    for group, counter in sorted(by_group.items()):
        lines.append(f"  {group:9} " + " · ".join(f"{k}: {v}" for k, v in sorted(counter.items())))
    text = "\n".join(lines)
    (out_dir / "tong_hop.md").write_text("```\n" + text + "\n```\n", encoding="utf-8")
    print(text)
    print(f"\n→ {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
