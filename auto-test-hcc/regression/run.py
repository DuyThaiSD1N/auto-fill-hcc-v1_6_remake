"""Chạy bộ ca hồi quy trên một cây backend. Dùng được trên máy, trong dịch vụ agent và trong CI:

    python auto-test-hcc/regression/run.py --be <thư mục backend> [ca.json | thư mục ...] [--json kết-quả.json]

Không truyền ca thì chạy cả ``auto-test-hcc/regression/cases``. Thoát mã 1 nếu có ca trượt hoặc lỗi.
Cần cài requirements.txt của backend. Không gọi mạng, không cần Mongo, không cần .env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _cases(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths or [str(HERE / "cases")]:
        path = Path(raw)
        found.extend(sorted(path.rglob("*.json")) if path.is_dir() else [path])
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--be", required=True, help="thư mục backend (chứa app/)")
    parser.add_argument("--json", help="ghi kết quả ra tệp JSON")
    parser.add_argument("cases", nargs="*")
    args = parser.parse_args()

    be = Path(args.be).resolve()
    if not (be / "app").is_dir():
        print(f"Không thấy {be}/app", file=sys.stderr)
        return 2
    os.chdir(be)
    sys.path.insert(0, str(be))
    sys.path.insert(0, str(HERE))
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    import harness

    harness.block_network()
    results = []
    for path in _cases(args.cases):
        case = json.loads(path.read_text(encoding="utf-8"))
        try:
            result = harness.run_case(case)
        except Exception as reason:  # noqa: BLE001 — một ca hỏng không được làm dừng cả bộ
            result = {"id": case.get("id"), "ok": False, "error": f"{type(reason).__name__}: {reason}",
                      "trace": traceback.format_exc()[-1500:]}
        result["file"] = path.name
        result.setdefault("id", path.stem)
        results.append(result)
        mark = "ĐẠT " if result.get("ok") else "TRƯỢT"
        print(f"{mark} {case.get('procedure')} · {result['id']}" + (f" · {result.get('error')}" if result.get("error") else ""))

    passed = sum(1 for r in results if r.get("ok"))
    print(f"{passed}/{len(results)} ca hồi quy đạt")
    if args.json:
        Path(args.json).write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
