"""Đo hiểu câu nói 3 lớp (chat/cach_noi) — gọi LLM THẬT (.env): nhãn cách nói, lệnh cuối, số lượt LLM, độ trễ.

    .venv/bin/python -m tests.handfree.eval.eval_cach_noi
    .venv/bin/python -m tests.handfree.eval.eval_cach_noi --only KK,TP --repeat 3
    .venv/bin/python -m tests.handfree.eval.eval_cach_noi --json /tmp/cach_noi.json   # cho CI đêm

Bộ câu: tests/handfree/eval/cach_noi_cases_vi.json — mỗi câu: bước, nút đang hiện (preset "nut"), câu trợ lý vừa nói,
câu công dân, kỳ vọng: "cach_noi" (các nhãn chấp nhận), "any"/"not" (kết quả cuối: send:<lệnh nút> | <kind> |
<kind>:<value>), "khong_bam" (câu nhiễu: không được sinh hành động / xác nhận / chọn gì), "max_calls". Chạy đúng intents.resolve như router; chỉ đọc, không ghi DB.
"""
import argparse
import asyncio
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

CASES = Path(__file__).resolve().parent / "cach_noi_cases_vi.json"
BN = {"province": "Thành phố Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Phương Liễu"}


def _labels(intent) -> set[str]:
    out = {intent.kind, f"{intent.kind}:{intent.value}"}
    send = (intent.payload or {}).get("_voice_button")
    if send:
        out.add(f"send:{send}")
    return out


def _conv(data: dict, case: dict) -> dict:
    state = case["state"]
    buttons = [dict(b) for b in data["nut"].get(case.get("nut") or "", [])]
    for b in buttons:
        b.setdefault("chip", {"label": b["label"], "send": b["send"]})
    history = [{"role": "bot", "text": case.get("bot") or ""}] if case.get("bot") else []
    return {
        "_id": "eval", "state": state, "procedure_key": case.get("procedure", "ket-hon"),
        "location": dict(BN), "auth_user": {"province_slug": "bacninh"}, "execution_subject": "self",
        "client_capabilities": {"supportsFieldReview": True, "supportsFlowV2": True, "supportsStepBack": True,
                                "supportsGuidedSteps": True},
        "voice_options": {"state": state, "items": buttons},
        "history": [*history, {"role": "user", "text": case["text"]}],
        **(case.get("conv") or {}),
    }


def _score(case: dict, intent) -> tuple[bool, str]:
    exp, p = case["expect"], intent.payload or {}
    got = _labels(intent)
    if "cach_noi" in exp and p.get("cach_noi") not in exp["cach_noi"]:
        return False, f"nhãn {p.get('cach_noi')} ∉ {exp['cach_noi']}"
    if "any" in exp and not (got & set(exp["any"])):
        return False, f"kết quả {sorted(got)} không có {exp['any']}"
    if "not" in exp and got & set(exp["not"]):
        return False, f"kết quả dính {sorted(got & set(exp['not']))}"
    if exp.get("khong_bam") and (p.get("_voice_button") or (intent.kind == "action" and intent.value != "repeat")
                                 or intent.kind in ("confirm", "deny", "pick_doc_method", "pick_procedure")):
        return False, f"câu nhiễu mà sinh hành động {intent.kind}:{intent.value}"
    if int(p.get("llm_calls") or 0) > int(exp.get("max_calls", 2)):
        return False, f"gọi LLM {p.get('llm_calls')} lượt"
    return True, ""


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="lọc theo tiền tố id, vd KK,TP")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--json", default="", help="ghi tổng kết JSON ra file (CI)")
    args = ap.parse_args()
    data = json.loads(CASES.read_text(encoding="utf-8"))
    cases = data["cases"]
    if args.only:
        prefixes = tuple(p.strip().upper() for p in args.only.split(",") if p.strip())
        cases = [c for c in cases if c["id"].startswith(prefixes)]

    from app.channels.handfree.chat import intents
    by_label, by_calls, ms_by_calls = defaultdict(lambda: [0, 0]), Counter(), defaultdict(list)
    total = ok_total = 0
    failures = []
    for case in cases:
        for _ in range(args.repeat):
            t0 = time.perf_counter()
            try:
                intent = await intents.resolve(case["text"], case["state"], _conv(data, case))
                ok, why = _score(case, intent)
                p = intent.payload or {}
                shown = f"{p.get('cach_noi')}/{p.get('do_chac')} llm={p.get('llm_calls')} → {intent.kind}:{intent.value}"
                calls = int(p.get("llm_calls") or 0)
            except Exception as e:  # noqa: BLE001 — đo tiếp
                ok, why, shown, calls = False, f"{type(e).__name__}: {e}", "error", 0
            ms = int((time.perf_counter() - t0) * 1000)
            label = (case["expect"].get("cach_noi") or ["?"])[0]
            by_label[label][0] += ok
            by_label[label][1] += 1
            by_calls[calls] += 1
            ms_by_calls[calls].append(ms)
            total += 1
            ok_total += ok
            if not ok:
                failures.append({"id": case["id"], "text": case["text"], "got": shown, "why": why})
            print(f"{'✓' if ok else '✗'} {case['id']:6} {ms:>5}ms  {case['text'][:46]:<46} → {shown}  {why}")

    print(f"\n== đúng {ok_total}/{total}")
    for label, (ok, n) in sorted(by_label.items()):
        print(f"   {label:14} {ok}/{n}")
    print("== số lượt LLM / câu:", ", ".join(f"{k} lượt: {v} câu ({100 * v // max(total, 1)}%)" for k, v in sorted(by_calls.items())))
    for k in sorted(ms_by_calls):
        xs = sorted(ms_by_calls[k])
        print(f"   {k} lượt: p50={int(statistics.median(xs))}ms p95={xs[int(len(xs) * 0.95) - 1] if len(xs) > 1 else xs[0]}ms")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "total": total, "ok": ok_total, "by_label": by_label, "by_calls": by_calls,
            "p50_by_calls": {k: int(statistics.median(v)) for k, v in ms_by_calls.items()}, "failures": failures,
        }, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
