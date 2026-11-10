"""Đo vòng bổ sung ô bản 2 (agent điều phối → agent chuyên môn → kiểm tra) — gọi LLM THẬT (.env).

    .venv/bin/python -m tests.handfree.eval.eval_field_review_v2
    .venv/bin/python -m tests.handfree.eval.eval_field_review_v2 --only N01,S05 --repeat 3

Bộ câu: tests/handfree/eval/field_review_v2_cases.json (tờ khai giả, không dữ liệu thật). Chạy đúng coordinator.decide +
specialist.solve như luồng thật; chỉ đọc, không ghi DB. Một câu ĐẠT khi: quyết định nằm trong danh sách cho phép, đúng ô
được giao / ô đích, và giá trị sau kiểm tra khớp ("ask" = phải hỏi lại, không được điền).
"""
import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

CASES = Path(__file__).resolve().parent / "field_review_v2_cases.json"


def _state(data: dict, case: dict) -> tuple[dict, dict]:
    form = [dict(f) for f in data["forms"][case["form"]]]
    for f in form:
        f["value"] = (case.get("fill") or {}).get(f["key"], f.get("value", ""))
        f["options"] = (case.get("options") or {}).get(f["key"], [])
    current = next(f for f in form if f["key"] == case["current"])
    st = {"catalog": form, "current": current, "visited": [], "log": data["logs"].get(case.get("log"), []),
          "partial": {}, "thread": list(case.get("thread") or [])}
    if case.get("confirm"):
        st["confirm"] = {"items": case["confirm"]}
    if case.get("group"):
        st["group"] = {"title": case.get("group_title") or "", "keys": list(case["group"])}
    conv = {"_id": "eval", "history": [*case.get("history", []), {"role": "user", "text": case["text"]}]}
    return conv, st


async def _run(data: dict, case: dict, vocabulary: str) -> tuple[bool, str, float]:
    from app.channels.handfree.chat.field_review.v2 import specialist, coordinator, context
    conv, st = _state(data, case)
    ctx = context.build(st)
    t0 = time.perf_counter()
    decision = await coordinator.decide(ctx, st, conv, case["text"], vocabulary)
    exp = case["expect"]
    problems = []
    if decision.kind not in exp["quyet_dinh"]:
        problems.append(f"quyết định {decision.kind} ∉ {exp['quyet_dinh']}")
    keys = [t[0]["key"] for t in decision.targets]
    if "o" in exp and decision.kind == "chuyen_mon" and sorted(keys) != sorted(exp["o"]):
        problems.append(f"ô {keys} ≠ {exp['o']}")
    if "goi_y" in exp and sorted(f["key"] for f in decision.suggest) != sorted(exp["goi_y"]):
        problems.append(f"gợi ý {[f['key'] for f in decision.suggest]} ≠ {exp['goi_y']}")
    if "toi" in exp and decision.kind in {"di_toi", "khoi_phuc"} and (decision.goal or {}).get("key") not in exp["toi"]:
        problems.append(f"ô đích {(decision.goal or {}).get('key')} ∉ {exp['toi']}")
    detail = decision.kind
    if decision.kind == "chuyen_mon" and exp.get("values"):
        st["last_text"] = case["text"]
        st["specialist_thread"] = list(case.get("thread") or [])
        assigned = [*decision.targets, *((f, "goi_y") for f in decision.suggest)]
        outcomes = await specialist.solve(assigned, case["text"], conv, st)
        got = {o.field["key"]: (o.checked.value if o.kind == "ok" else "ask" if o.kind == "ask" else "none")
               for o in outcomes}
        unsure = [o.field["key"] for o in outcomes if o.kind == "ok" and o.confirm]
        detail += " " + json.dumps(got, ensure_ascii=False) + (f" · chưa chắc (đọc lại): {unsure}" if unsure else "")
        from app.channels.handfree.chat.field_review.v2 import _match_option
        for key, want in exp["values"].items():
            # Ô tỉnh / xã: "Xã Tam Hợp" và "Tam Hợp" khớp cùng một dòng danh sách lúc điền.
            same_option = key.endswith(("#tinh", "#xa")) and _match_option(str(got.get(key)), [str(want)])
            if key in got and str(got[key]).casefold() != str(want).casefold() and not same_option:
                problems.append(f"{key}: {got[key]!r} ≠ {want!r}")
    return not problems, "; ".join(problems) or detail, time.perf_counter() - t0


async def main(only: set[str], repeat: int):
    from app.channels.handfree.chat.field_review import registry
    data = json.loads(CASES.read_text(encoding="utf-8"))
    vocabulary = (registry.get("ket-hon") or {}).get("vocabulary", "")
    cases = [c for c in data["cases"] if not only or c["id"] in only]
    passed, total, times, fails = 0, 0, [], []
    for case in cases:
        for _ in range(repeat):
            ok, info, took = await _run(data, case, vocabulary)
            total += 1
            passed += ok
            times.append(took)
            print(f"{'✅' if ok else '❌'} {case['id']:4} {took:5.2f}s  {case['text'][:60]:60}  {info}")
            if not ok:
                fails.append(case["id"])
    print(f"\nĐạt {passed}/{total}  ·  thời gian trung vị {statistics.median(times):.2f}s, chậm nhất {max(times):.2f}s")
    if fails:
        print("Trượt:", ", ".join(dict.fromkeys(fails)))


if __name__ == "__main__":
    import logging
    logging.disable(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(main({x for x in args.only.split(",") if x}, args.repeat))
