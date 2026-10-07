"""Đo nhận diện thủ tục handfree bằng câu gõ/nói — gọi LLM THẬT (cấu hình .env).

    .venv/bin/python -m tests.handfree.eval.eval_procedure_picker --mode picker       # chỉ agent chọn thủ tục
    .venv/bin/python -m tests.handfree.eval.eval_procedure_picker --mode resolve      # intents.resolve ở màn chào
    .venv/bin/python -m tests.handfree.eval.eval_procedure_picker --mode picker --only D,E --out /tmp/kq.json

Đo bản CŨ để so: chép script + bộ câu vào một git worktree ở commit cũ rồi chạy --mode resolve
(resolve chạy đúng code của thư mục đang đứng; bản cũ chỉ thấy câu hiện tại, không lịch sử).

Bộ câu: tests/handfree/eval/procedure_cases_vi.json. Chỉ đọc, không ghi DB.
"""
import argparse
import asyncio
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

CASES = Path(__file__).resolve().parent / "procedure_cases_vi.json"


async def _run_resolve(case: dict) -> dict:
    import inspect

    from app.channels.handfree.chat import intents
    if "conv" in inspect.signature(intents.resolve).parameters:
        it = await intents.resolve(case["text"], "greet", _case_conv(case))
    else:  # bản cũ: resolve(message, state)
        it = await intents.resolve(case["text"], "greet")
    if it.kind == "pick_procedure":
        return {"result": "pick", "key": it.value, "candidates": []}
    if it.kind == "procedure_unclear":
        return {"result": "unclear", "key": "", "candidates": it.payload.get("candidates", [])}
    if it.kind == "ask_question":
        return {"result": "ask_about", "key": it.payload.get("procedure_key", ""), "candidates": []}
    return {"result": "unclear" if it.kind == "unknown" else "other:" + it.kind, "key": "", "candidates": []}


def _case_conv(case: dict) -> dict:
    # Giống router: câu hiện tại đã nằm cuối history trước khi phân loại.
    return {
        "state": "greet",
        "auth_user": {"province_slug": case.get("province", "laichau")},
        "procedure_candidates": case.get("candidates_shown", []),
        "history": [*case.get("history", []), {"role": "user", "text": case["text"]}],
    }


async def _run_picker(case: dict) -> dict:
    from app.channels.handfree.chat import procedure_picker
    res = await procedure_picker.pick(case["text"], _case_conv(case))
    return {"result": res.result, "key": res.key, "candidates": list(res.candidates)}


def _score(expect: dict, got: dict) -> tuple[bool, bool]:
    """(đúng, an_toàn). an_toàn = không chọn bừa một thủ tục sai."""
    picked = got["key"] if got["result"] == "pick" else ""
    if "pick" in expect:
        ok = picked == expect["pick"]
        return ok, ok or not picked
    if "ask_about" in expect:
        ok = got["result"] == "ask_about" and got["key"] == expect["ask_about"]
        return ok, not picked
    if "none" in expect:
        return not picked, not picked
    if "not_pick" in expect:
        ok = picked != expect["not_pick"]
        return ok, ok
    if "unclear" in expect:
        safe = not picked
        want, cands = set(expect["unclear"]), set(got["candidates"])
        hit = want <= cands if expect.get("all") else bool(want & cands)
        return safe and hit, safe
    raise ValueError(expect)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["picker", "resolve"], required=True)
    ap.add_argument("--only", default="", help="lọc theo chữ cái đầu id, vd A,D")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    if args.only:
        prefixes = tuple(p.strip().upper() for p in args.only.split(",") if p.strip())
        cases = [c for c in cases if c["id"].startswith(prefixes)]
    run = _run_picker if args.mode == "picker" else _run_resolve

    rows, by_group, ms_all = [], defaultdict(lambda: [0, 0, 0]), []
    for case in cases:
        t0 = time.perf_counter()
        try:
            got = await run(case)
        except Exception as e:  # noqa: BLE001 — đo tiếp các câu còn lại
            got = {"result": f"error:{type(e).__name__}", "key": "", "candidates": []}
        ms = int((time.perf_counter() - t0) * 1000)
        ms_all.append(ms)
        ok, safe = _score(case["expect"], got)
        g = by_group[case["group"]]
        g[0] += ok
        g[1] += safe
        g[2] += 1
        rows.append({**case, "got": got, "ok": ok, "safe": safe, "ms": ms})
        print(f"{'✓' if ok else ('·' if safe else '✗')} {case['id']} {ms:>5}ms  {case['text'][:48]:<48} "
              f"→ {got['result']} {got['key']} {got['candidates'] or ''}")

    total_ok = sum(g[0] for g in by_group.values())
    total_safe = sum(g[1] for g in by_group.values())
    print(f"\n== mode={args.mode}  đúng {total_ok}/{len(rows)}  an toàn {total_safe}/{len(rows)}")
    for name, (ok, safe, n) in by_group.items():
        print(f"   {name:<24} đúng {ok}/{n}  an toàn {safe}/{n}")
    if ms_all:
        q = sorted(ms_all)
        print(f"   độ trễ p50={int(statistics.median(q))}ms p95={q[int(len(q) * 0.95) - 1]}ms")
    print("   (✓ đúng · · không chọn bừa nhưng chưa đạt · ✗ chọn SAI thủ tục)")
    if args.out:
        Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
