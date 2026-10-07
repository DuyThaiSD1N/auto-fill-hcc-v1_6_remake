"""Đo nhận ý định theo TỪNG BƯỚC (nút đang hiện + câu nói → lệnh đúng) — gọi LLM THẬT (.env).

    .venv/bin/python -m tests.handfree.eval.eval_step_intents
    .venv/bin/python -m tests.handfree.eval.eval_step_intents --only XN,XP

Bộ câu: tests/handfree/eval/step_cases_vi.json. Chạy đúng intents.resolve như router (kể cả agent
chọn thủ tục / agent nơi làm khi bộ phân loại chuyển sang). Chỉ đọc, không ghi DB.
"""
import argparse
import asyncio
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

CASES = Path(__file__).resolve().parent / "step_cases_vi.json"
BN = {"province": "Thành phố Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Phương Liễu"}


def _labels(intent, buttons: list[dict]) -> set[str]:
    """Các cách gọi kết quả để so với expect: send:<lệnh nút>, <kind>, <kind>:<value>."""
    out = {intent.kind, f"{intent.kind}:{intent.value}"}
    send = (intent.payload or {}).get("_voice_button")
    if send:
        out.add(f"send:{send}")
    return out


async def _run(case: dict):
    from app.channels.handfree.chat import intents
    state = case["state"]
    conv = {
        "_id": "eval", "state": state, "procedure_key": case.get("procedure"),
        "location": dict(BN), "auth_user": {"province_slug": "bacninh"}, "execution_subject": "self",
        "voice_options": {"state": state, "items": case.get("buttons", [])},
        "history": [*case.get("history", []), {"role": "user", "text": case["text"]}],
    }
    return await intents.resolve(case["text"], state, conv)


def _score(expect: dict, intent, buttons) -> bool:
    got = _labels(intent, buttons)
    if "any" in expect and not (got & set(expect["any"])):
        return False
    if "not" in expect and got & set(expect["not"]):
        return False
    if "place" in expect:
        if (intent.kind, intent.value) != ("action", "set_place"):
            return False
        return all((intent.payload or {}).get(k) == v for k, v in expect["place"].items())
    return True


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="lọc theo tiền tố id, vd XN,XP")
    args = ap.parse_args()
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    if args.only:
        prefixes = tuple(p.strip().upper() for p in args.only.split(",") if p.strip())
        cases = [c for c in cases if c["id"].startswith(prefixes)]

    by_state, ms_all, total = defaultdict(lambda: [0, 0]), [], 0
    for case in cases:
        t0 = time.perf_counter()
        try:
            intent = await _run(case)
            ok = _score(case["expect"], intent, case.get("buttons", []))
            shown = f"{intent.kind}:{intent.value} {json.dumps(intent.payload, ensure_ascii=False)[:90]}"
        except Exception as e:  # noqa: BLE001 — đo tiếp các câu còn lại
            ok, shown = False, f"error:{type(e).__name__}: {e}"
        ms = int((time.perf_counter() - t0) * 1000)
        ms_all.append(ms)
        by_state[case["state"]][0] += ok
        by_state[case["state"]][1] += 1
        total += ok
        print(f"{'✓' if ok else '✗'} {case['id']:4} {ms:>5}ms  {case['text'][:44]:<44} → {shown}")
    print(f"\n== đúng {total}/{len(cases)}")
    for state, (ok, n) in by_state.items():
        print(f"   {state:<22} {ok}/{n}")
    if ms_all:
        q = sorted(ms_all)
        print(f"   độ trễ p50={int(statistics.median(q))}ms p95={q[max(0, int(len(q) * 0.95) - 1)]}ms")


if __name__ == "__main__":
    asyncio.run(main())
