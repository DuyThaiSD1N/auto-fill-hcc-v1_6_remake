"""Xuất JSON: mọi request_id trace thuộc các tỉnh mục tiêu (mặc định Lai Châu, Bắc Ninh, Lâm Đồng).

Cách xác định tỉnh: trace.user_id -> users.tinh (fold dấu so khớp danh sách tỉnh).
Chạy:
  MONGO_URI="mongodb://root:callbot@localhost:11004/?authSource=admin" \
  MONGO_DB=autofill_hcc TINH="Lai Châu, Bắc Ninh, Lâm Đồng" \
  .venv/bin/python export_lamdong_traces.py > lamdong_traces.json
Nếu không set MONGO_URI, script tự dựng từ MONGO_HOST/PORT/USERNAME/PASSWORD/AUTH_SOURCE.
Đổi/thêm tỉnh: set TINH="A, B, C" (phân tách bằng dấu phẩy) hoặc sửa DEFAULT_TINH.
"""
import json
import os
import sys
import unicodedata
from urllib.parse import quote_plus

import pymongo

DEFAULT_TINH = "Lai Châu, Bắc Ninh, Lâm Đồng"


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower()).replace("đ", "d")
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def build_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.environ["MONGO_URI"]
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "11004")
    user = os.getenv("MONGO_USERNAME", "root")
    pwd = os.getenv("MONGO_PASSWORD", "callbot")
    auth = os.getenv("MONGO_AUTH_SOURCE", "admin")
    if user:
        return f"mongodb://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}/?authSource={auth}"
    return f"mongodb://{host}:{port}"


def main() -> None:
    targets = {fold(t) for t in os.getenv("TINH", DEFAULT_TINH).split(",") if fold(t)}
    db_name = os.getenv("MONGO_DB", "autofill_hcc")
    client = pymongo.MongoClient(build_uri(), serverSelectionTimeoutMS=5000)
    db = client[db_name]

    # 1) Users thuộc bất kỳ tỉnh mục tiêu nào (fold dấu). Lưu tinh gốc để đưa vào output.
    tinh_by_uid: dict[str, str] = {}
    all_tinh: dict[str, int] = {}
    for u in db.users.find({}, {"tinh": 1}):
        raw = u.get("tinh")
        all_tinh[str(raw)] = all_tinh.get(str(raw), 0) + 1
        if fold(raw) in targets:
            tinh_by_uid[str(u["_id"])] = raw

    # 2) Traces của các user đó. user_id trong trace là chuỗi str(ObjectId).
    seen: dict[str, dict] = {}  # request_id -> {id, tinh} (dedupe theo request_id)
    trace_count = 0
    cur = db.traces.find(
        {"user_id": {"$in": list(tinh_by_uid)}},
        {"request_id": 1, "user_id": 1, "created_at": 1},
    )
    for t in cur:
        trace_count += 1
        rid = t.get("request_id")
        if not rid:
            continue
        seen.setdefault(rid, {"id": rid, "tinh": tinh_by_uid.get(str(t.get("user_id")))})

    result = list(seen.values())

    # Chẩn đoán ra stderr (không lẫn vào JSON stdout): tổng + breakdown theo tỉnh.
    by_tinh: dict[str, int] = {}
    for r in result:
        by_tinh[r["tinh"]] = by_tinh.get(r["tinh"], 0) + 1
    print(f"[i] DB={db_name} | tỉnh lọc={sorted(targets)} | users khớp={len(tinh_by_uid)} | "
          f"trace docs={trace_count} | request_id duy nhất={len(result)}", file=sys.stderr)
    print(f"[i] theo tỉnh: {by_tinh}", file=sys.stderr)
    print("[i] distinct tinh trong users:", file=sys.stderr)
    for k, v in sorted(all_tinh.items(), key=lambda x: -x[1]):
        print(f"      {k!r}: {v}", file=sys.stderr)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
