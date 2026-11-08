"""Đo cách hiểu câu trả lời của trợ lý thành lập hộ kinh doanh — gọi LLM THẬT (.env), dữ liệu giả.

    .venv/bin/python -m tests.handfree.eval.eval_hkd_agents                 # hai lớp agent (mặc định)
    .venv/bin/python -m tests.handfree.eval.eval_hkd_agents --old           # cách hiểu một lượt cũ (mốc so sánh)
    .venv/bin/python -m tests.handfree.eval.eval_hkd_agents --only H01,H07 --repeat 3

Bộ câu: hkd_agents_cases.json. Một câu ĐẠT khi hành động nằm trong danh sách cho phép và mọi giá trị kỳ vọng khớp
(chuỗi: so không dấu, kỳ vọng nằm trong giá trị; địa chỉ: từng phần; số / có-không: bằng nhau). Chỉ đọc, không ghi DB.
"""
import argparse
import asyncio
import json
import statistics
import time
from datetime import date
from pathlib import Path

CASES = Path(__file__).resolve().parent / "hkd_agents_cases.json"


def _special(value):
    if value == "__next_month_1__":
        today = date.today()
        y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return f"01/{m:02d}/{y}"
    return value


def _state(case: dict) -> tuple[dict, dict]:
    from app.channels.handfree.chat import hkd_tro_ly as hkd
    st = {"mode": case.get("mode", "khong_giay"), "values": dict(case.get("values") or {}), "nganh": [], "chinh": "",
          "skipped": list(case.get("skipped") or []), "members": [], "member": dict(case.get("member") or {}),
          "force_self": False, "loc": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Kinh Bắc"},
          "thread": list(case.get("thread") or []), "asked": True}
    st["block"] = hkd._blocks(st).index(case["page"])
    st.update(phase="confirm" if case["field"] == hkd._CONFIRM else "ask", field=case["field"])
    conv = {"_id": "eval", "history": [*case.get("history", []), {"role": "user", "text": case["text"]}],
            "location": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Kinh Bắc"}}
    return conv, st


def _same(got, want) -> bool:
    from app.channels.handfree.chat.intents import fold
    want = _special(want)
    if isinstance(want, dict):
        return isinstance(got, dict) and all(
            fold(str(v)) in fold(str(got.get(k) or "")) if v else not got.get(k) for k, v in want.items())
    if isinstance(want, (bool, int)) or want is None:
        return got == want
    return isinstance(got, str) and fold(str(want)) in fold(got)


async def _run(case: dict, old: bool) -> tuple[bool, str, float]:
    from app.channels.handfree.chat import hkd_tro_ly as hkd
    from app.channels.handfree.chat.hkd_tro_ly import agents, hoi_dap
    conv, st = _state(case)
    key = st["field"]
    t0 = time.perf_counter()
    if old:
        question = hkd._question(st, key)[0] if key != hkd._CONFIRM else hoi_dap.prompt.CONFIRM_QUESTION
        got = await hoi_dap.interpret(case["text"], key if key != hkd._CONFIRM else "tom_tat", question,
                                      hkd._open_slots(st), {**st["values"], **st["member"]}, "Phường Kinh Bắc, Bắc Ninh")
    else:
        got = await agents.understand(hkd._catalog(st), hkd._current_info(st, key), st["thread"], conv, case["text"])
    took = time.perf_counter() - t0
    exp = case["expect"]
    problems = []
    if got.action not in exp["action"]:
        problems.append(f"hành động {got.action} ∉ {exp['action']}")
    for k, want in (exp.get("values") or {}).items():
        if not _same(got.values.get(k), want):
            problems.append(f"{k}: {got.values.get(k)!r} ≠ {_special(want)!r}")
    if exp.get("nganh") and not getattr(got, "nganh_text", ""):
        problems.append("thiếu lời về việc kinh doanh cho agent ngành")
    detail = f"{got.action} {json.dumps(got.values, ensure_ascii=False, default=str)}"
    return not problems, "; ".join(problems) or detail, took


async def main(only: set[str], repeat: int, old: bool):
    cases = [c for c in json.loads(CASES.read_text(encoding="utf-8"))["cases"] if not only or c["id"] in only]
    passed, total, times, fails = 0, 0, [], []
    for case in cases:
        for _ in range(repeat):
            ok, info, took = await _run(case, old)
            total += 1
            passed += ok
            times.append(took)
            print(f"{'✅' if ok else '❌'} {case['id']:4} {took:5.2f}s  {case['text'][:55]:55}  {info[:160]}", flush=True)
            if not ok:
                fails.append(case["id"])
    print(f"\n{'MỘT LƯỢT (cũ)' if old else 'HAI LỚP'}: đạt {passed}/{total}  ·  trung vị {statistics.median(times):.2f}s, "
          f"chậm nhất {max(times):.2f}s")
    if fails:
        print("Trượt:", ", ".join(dict.fromkeys(fails)))


if __name__ == "__main__":
    import logging
    logging.disable(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--old", action="store_true")
    args = parser.parse_args()
    asyncio.run(main({x for x in args.only.split(",") if x}, args.repeat, args.old))
