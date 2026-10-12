"""Dòng lệnh luồng mới 2 — xem scripts/luongmoi/luong2.py.

Chạy (từ auto-fill-hcc-backend):
  .venv/bin/python -m scripts.luongmoi.run2 --manifest <manifest.json> --first 50 \
      --v1-tu <thư mục kết quả luồng cũ> [--cham <thư mục chấm>] [--concurrency 3]

--v1-tu: dùng lại đúng v1 (và thời gian lần 1) của luồng cũ → hai luồng so trên cùng đầu vào, và kết quả chấm
cũ (--cham, chấm theo v1 đó) dùng lại được. Cờ mới chưa ai chấm được ghi ra <out>/cham/nhom*.json để agent chấm.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

from scripts.luongmoi import du_lieu, luong2
from scripts.luongmoi.thu_do_chac import in_truth, load_rows


def _short(value, width: int = 70) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _label(row: dict) -> str:
    if row["flag"] == "sua":
        return "SỬA+CAM" if row.get("muc") == "cam" else "SỬA"
    return {"do": "ĐỎ", "cam": "CAM"}.get(row.get("muc"), "CẢNH BÁO")


def _q(xs: list[float]) -> str:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return "-"
    return f"trung vị {statistics.median(xs):.1f} · p90 {xs[max(0, int(len(xs) * 0.9) - 1)]:.1f} · max {xs[-1]:.1f} (n={len(xs)})"


async def main() -> None:
    ap = argparse.ArgumentParser(description="Luồng mới 2: Qwen trích xuất nguyên bộ từ ảnh + code so từng ô")
    ap.add_argument("rids", nargs="*")
    ap.add_argument("--manifest")
    ap.add_argument("--first", type=int, default=0, help="chỉ lấy N mã đầu của manifest")
    ap.add_argument("--v1-tu", help="thư mục kết quả luồng cũ (<rid>_l1.json) để dùng lại v1")
    ap.add_argument("--cham", nargs="*", default=[], help="các thư mục chấm cũ (nhom*.json + ket_qua*.json)")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--b-moi", action="store_true", help="bỏ cache bản đọc thứ hai")
    args = ap.parse_args()

    rids = list(args.rids)
    if args.manifest:
        picked = [r["request_id"] for r in json.loads(Path(args.manifest).read_text(encoding="utf-8"))["picked"]]
        rids += picked[: args.first] if args.first else picked
    old = {}
    if args.v1_tu:
        for rid in rids:
            path = Path(args.v1_tu) / f"{rid}_l1.json"
            if path.is_file():
                old[rid] = json.loads(path.read_text(encoding="utf-8"))
    out_dir = du_lieu.out_root() / "_luongmoi" / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_l2")
    out_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(args.concurrency)

    async def one(rid: str) -> dict:
        async with sem:
            case = du_lieu.load(rid)
            prev = old.get(rid)
            try:
                res = await luong2.chay(case, (prev or {}).get("output1", {}).get("llm"),
                                        ((prev or {}).get("thoi_gian") or {}).get("uoc_output1_s"), refresh_b=args.b_moi)
            except Exception as exc:  # noqa: BLE001 — một hồ sơ lỗi không dừng cả lượt
                return {"rid": rid, "error": repr(exc)}
        (out_dir / f"{rid}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return res

    results = await asyncio.gather(*(one(r) for r in rids))
    graded = {(r["rid"], r["field"]): r for d in args.cham for r in load_rows(Path(d), set())}

    lines, tally, truth = [], Counter(), Counter()
    times = {k: [] for k in ("output1_s", "ban_doc_2_s", "muc_dich_s", "uoc_output2_s")}
    fresh_b = []
    to_grade: dict[str, list[dict]] = {}
    for res in sorted(results, key=lambda r: r["rid"]):
        rid = res["rid"]
        if res.get("error"):
            lines.append(f"===== {rid} LỖI {res['error']}")
            continue
        t = res["thoi_gian"]
        for k in times:
            times[k].append(t.get(k))
        if not res["ban_doc_2"].get("cached"):
            fresh_b.append(t["ban_doc_2_s"])
        flags = res["output2"]["review"]
        old_flags = {r["name"] for r in (old.get(rid) or {}).get("output2", {}).get("review", [])}
        lines.append(f"===== {rid}  lần1≈{t['output1_s']}s · đọc lần 2 {t['ban_doc_2_s']}s · mục đích {t['muc_dich_s']}s"
                     f" → lần2≈{t['uoc_output2_s']}s · luồng cũ có {len(old_flags)} cờ")
        for row in flags:
            g = graded.get((rid, row["name"]))
            mark = ""
            if g:
                v1_sai = g["ket_luan"] in ("trung", "dung", "chua_toi")
                if row["flag"] == "sua":
                    ok = in_truth(luong2._kind(row["name"]) or "chu", row["value"], g["tren_giay"])
                    mark = f"«đã chấm: v1 {'sai' if v1_sai else 'đúng'}; giá trị mới {'khớp giấy' if ok else 'chưa khớp giấy'}»"
                    truth[f"sửa · v1 {'sai' if v1_sai else 'đúng'} · mới {'khớp' if ok else 'chưa khớp'}"] += 1
                else:
                    mark = f"«đã chấm: v1 {'sai' if v1_sai else 'đúng'}»"
                    truth[f"{_label(row)} · v1 {'sai' if v1_sai else 'đúng'}"] += 1
            else:
                to_grade.setdefault(rid, []).append(row)
            shown = row["value"] if row["flag"] == "sua" else row.get("goi_y")
            lines.append(f"  [{_label(row):3}] {row['name']}: {_short(row['old'], 45)}"
                         + (f"  →  {_short(shown, 50)}" if shown not in (None, "") else "")
                         + (f"  (p={row['p']:.2f})" if isinstance(row.get("p"), float) else "")
                         + f"  | {_short(row.get('ly_do'), 80)}  → ô {','.join(row.get('ui_keys') or [])}"
                         + (f"  {mark}" if mark else "") + ("  [cũ cũng cờ]" if row["name"] in old_flags else ""))
            tally[_label(row)] += 1
        # Lỗi thật đã biết (từ lần chấm cũ) mà luồng mới không gắn cờ.
        flagged = {r["name"] for r in flags}
        for (g_rid, field), g in graded.items():
            if g_rid == rid and g["ket_luan"] in ("trung", "dung", "chua_toi") and field not in flagged:
                lines.append(f"  [LỌT] {field}: v1={_short(g['v1'], 40)} | giấy={_short(g['tren_giay'], 60)}")
                truth["lỗi đã biết · luồng mới KHÔNG cờ"] += 1
        if not flags:
            lines.append("  (không có cờ)")

    n_ok = sum(1 for r in results if not r.get("error"))
    n_old = sum(len((old.get(r["rid"]) or {}).get("output2", {}).get("review", [])) for r in results)
    lines += ["", f"===== TỔNG ({n_ok} hồ sơ)",
              "  cờ luồng mới: " + " · ".join(f"{k} {v}" for k, v in sorted(tally.items()))
              + f" · trung bình {sum(tally.values()) / max(n_ok, 1):.2f} cờ/hồ sơ",
              f"  cờ luồng cũ trên cùng hồ sơ: {n_old}",
              "  đối chiếu ô đã chấm: " + (" · ".join(f"{k}: {v}" for k, v in sorted(truth.items())) or "-"),
              "", "===== THỜI GIAN (giây)"]
    for k, xs in times.items():
        lines.append(f"  {k:14}: {_q(xs)}")
    lines.append(f"  đọc lần 2 (chạy mới, không cache): {_q(fresh_b)}")

    grade_dir = out_dir / "cham"
    grade_dir.mkdir(exist_ok=True)
    items = sorted(to_grade.items(), key=lambda kv: -len(kv[1]))
    n_groups = max(1, min(8, (sum(len(v) for _, v in items) + 19) // 20))
    groups: list[dict] = [{} for _ in range(n_groups)]
    load = [0] * n_groups
    for rid, rows in items:
        i = load.index(min(load))
        groups[i][rid] = [{"stt": j + 1, "field": r["name"], "flag": r["flag"], "muc": r.get("muc"), "v1": r["old"],
                           "de_xuat": r["value"] if r["flag"] == "sua" else r.get("goi_y"), "ly_do_agent": r.get("ly_do"),
                           "nguon": r.get("nguon"), "chot": None} for j, r in enumerate(rows)]
        load[i] += len(rows)
    for i, g in enumerate(groups, 1):
        (grade_dir / f"nhom{i}.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    lines.append(f"\n  cờ chưa chấm: {sum(load)} trong {len(to_grade)} hồ sơ → {grade_dir}/nhom1..{n_groups}.json")

    text = "\n".join(lines)
    (out_dir / "tong_hop.md").write_text("```\n" + text + "\n```\n", encoding="utf-8")
    print(text)
    print(f"\n→ {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
