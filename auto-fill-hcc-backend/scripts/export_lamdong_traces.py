"""Xuất JSON: danh sách request_id DUY NHẤT (không trùng) của trace thuộc tỉnh mục tiêu.

MẶC ĐỊNH: tỉnh Lâm Đồng, trong THÁNG 8/2026 (01/08 → 31/08, giờ VN). Đã dedupe theo request_id.
Cách xác định tỉnh: trace.user_id -> users.tinh (fold dấu so khớp danh sách tỉnh).
Chạy (mặc định đã là Lâm Đồng + tháng 8, không cần set gì thêm ngoài kết nối Mongo):
  MONGO_URI="mongodb://root:callbot@localhost:11004/?authSource=admin" \
  MONGO_DB=autofill_hcc \
  .venv/bin/python export_lamdong_traces.py > lamdong_traces.json
Nếu không set MONGO_URI, script tự dựng từ MONGO_HOST/PORT/USERNAME/PASSWORD/AUTH_SOURCE.
Đổi/thêm tỉnh: set TINH="A, B, C" (phân tách bằng dấu phẩy) hoặc sửa DEFAULT_TINH.

Đổi khoảng NGÀY (ghi đè mặc định tháng 8; giờ Việt Nam UTC+7, bao trọn ngày):
  FROM_DATE=2026-08-01 TO_DATE=2026-08-06   # nhận YYYY-MM-DD hoặc DD/MM/YYYY; đặt 1 trong 2 cũng được.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import pymongo

DEFAULT_TINH = "Lâm Đồng"
# Mặc định lấy request_id trong THÁNG 8/2026 (giờ VN, bao trọn 31/08). Ghi đè bằng FROM_DATE/TO_DATE.
DEFAULT_FROM_DATE = "2026-08-01"
DEFAULT_TO_DATE = "2026-08-31"
VN_TZ = timezone(timedelta(hours=7))  # Việt Nam UTC+7 (không có DST) — người dùng nhập ngày theo giờ này


def parse_date(value: str | None) -> datetime | None:
    """Chuỗi ngày (giờ VN) -> datetime aware tại 00:00 +07:00. Rỗng -> None; sai định dạng -> thoát."""
    s = str(value or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=VN_TZ)
        except ValueError:
            continue
    raise SystemExit(f"[!] Ngày không hợp lệ: {s!r}. Dùng YYYY-MM-DD hoặc DD/MM/YYYY.")


def fold(s: str) -> str:
    """So khớp theo TRƯỜNG tỉnh: bỏ dấu + bỏ tiền tố đơn vị hành chính ("Tỉnh"/"Thành phố"/"TP")
    rồi so BẰNG NHAU. Nhờ vậy 'Tỉnh Lâm Đồng' và 'Lâm Đồng' đều ra 'lam dong' và cùng khớp; KHÔNG phải
    so kiểu chuỗi-chứa (tên xã/thôn có chữ 'lâm đồng' sẽ không dính vì đây là giá trị trường tỉnh)."""
    s = unicodedata.normalize("NFD", str(s or "").lower()).replace("đ", "d")
    s = "".join(c for c in s if not unicodedata.combining(c)).strip()
    return re.sub(r"^(tinh|thanh pho|tp)\.?\s+", "", s).strip()


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
    # Lọc ngày (giờ VN → UTC-aware cho query; created_at lưu UTC). TO bao TRỌN ngày: dùng < (TO + 1 ngày).
    from_dt = parse_date(os.getenv("FROM_DATE") or os.getenv("FROM") or DEFAULT_FROM_DATE)
    to_dt = parse_date(os.getenv("TO_DATE") or os.getenv("TO") or DEFAULT_TO_DATE)
    date_query: dict = {}
    if from_dt:
        date_query["$gte"] = from_dt
    if to_dt:
        date_query["$lt"] = to_dt + timedelta(days=1)

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
    trace_filter: dict = {"user_id": {"$in": list(tinh_by_uid)}}
    if date_query:
        trace_filter["created_at"] = date_query
    cur = db.traces.find(
        trace_filter,
        {"request_id": 1, "user_id": 1, "created_at": 1},
    )
    for t in cur:
        trace_count += 1
        rid = t.get("request_id")
        if not rid:
            continue
        seen.setdefault(rid, {"id": rid, "tinh": tinh_by_uid.get(str(t.get("user_id")))})

    # Xuất DANH SÁCH request_id PHẲNG, đã dedupe theo request_id, sắp xếp cho ổn định (không trùng).
    result = sorted(seen)

    # Chẩn đoán ra stderr (không lẫn vào JSON stdout): tổng + breakdown theo tỉnh.
    by_tinh: dict[str, int] = {}
    for r in seen.values():
        by_tinh[r["tinh"]] = by_tinh.get(r["tinh"], 0) + 1
    date_desc = "tất cả" if not date_query else (
        f"{from_dt.date() if from_dt else '...'} → {to_dt.date() if to_dt else '...'} (giờ VN)"
    )
    print(f"[i] DB={db_name} | tỉnh lọc={sorted(targets)} | ngày={date_desc} | users khớp={len(tinh_by_uid)} | "
          f"trace docs={trace_count} | request_id duy nhất={len(result)}", file=sys.stderr)
    print(f"[i] theo tỉnh: {by_tinh}", file=sys.stderr)
    print("[i] distinct tinh trong users:", file=sys.stderr)
    for k, v in sorted(all_tinh.items(), key=lambda x: -x[1]):
        print(f"      {k!r}: {v}", file=sys.stderr)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
