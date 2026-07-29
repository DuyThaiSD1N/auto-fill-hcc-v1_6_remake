"""Xuất Excel thống kê auto-fill theo NGÀY (mặc định: hôm qua).

Mỗi dòng = 1 người làm thủ tục (dedup theo NGƯỜI + THỦ TỤC, giữ bản mới nhất), gồm:
  Mã hồ sơ · Thủ tục · Ngày đo · Tổng trường then chốt · Số trường bóc tách được
  · Đính kèm đủ & đúng (chấm tay) · Hồ sơ đạt tự động (chấm tay) · Loại lỗi · Ghi chú

Chạy:
  .venv/bin/python scripts/export_autofill_stats.py            # hôm qua
  .venv/bin/python scripts/export_autofill_stats.py 2026-07-01 # ngày cụ thể (giờ VN)
  .venv/bin/python scripts/export_autofill_stats.py 2026-07-01 out.xlsx
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.traces.key_fields import KEY_FIELDS_BY_PROCEDURE, count_key_fields, key_fields_total  # noqa: E402

VN_TZ = timezone(timedelta(hours=7))  # created_at lưu UTC; "ngày" tính theo giờ VN (+7)
AUTOFILL_PROCEDURES = set(KEY_FIELDS_BY_PROCEDURE)

HEADERS = [
    "Mã hồ sơ", "Thủ tục", "Ngày đo", "Tổng trường then chốt", "Số trường bóc tách được",
    "Đính kèm đủ & đúng", "Hồ sơ đạt tự động", "Loại lỗi", "Ghi chú",
]


def _day_range_utc(day_vn: datetime) -> tuple[datetime, datetime]:
    """Khoảng [đầu ngày, đầu ngày kế) theo giờ VN, quy về UTC để query created_at."""
    start_vn = day_vn.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=VN_TZ)
    return start_vn.astimezone(timezone.utc), (start_vn + timedelta(days=1)).astimezone(timezone.utc)


def main() -> None:
    # Ngày (giờ VN); mặc định hôm qua.
    if len(sys.argv) > 1 and sys.argv[1]:
        day = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    else:
        day = datetime.now(VN_TZ) - timedelta(days=1)
    out_path = sys.argv[2] if len(sys.argv) > 2 else f"autofill_stats_{day:%Y-%m-%d}.xlsx"
    start_utc, end_utc = _day_range_utc(day)

    client = MongoClient(settings.mongo_dsn)
    db = client[settings.mongo_db]

    # Traces auto-fill trong ngày (bỏ bước đính kèm).
    q = {
        "created_at": {"$gte": start_utc, "$lt": end_utc},
        "procedure": {"$in": list(AUTOFILL_PROCEDURES)},
        "kind": {"$ne": "attach"},
    }
    traces = list(db.traces.find(q).sort("created_at", 1))

    # Nạp UI fields từ process_requests (join theo request_id) để đếm trường bóc tách được cho
    # trace cũ (chưa có key_fields_*). Trace mới đã có sẵn key_fields_filled.
    req_ids = [t.get("request_id") for t in traces if t.get("request_id")]
    fields_by_req: dict[str, list] = {}
    if req_ids:
        for r in db.process_requests.find({"request_id": {"$in": req_ids}}, {"request_id": 1, "fields": 1}):
            fields_by_req[r.get("request_id")] = r.get("fields") or []

    # Dedup theo (người làm, thủ tục) — giữ bản MỚI NHẤT (traces đã sort tăng dần → ghi đè).
    rows: dict[tuple, dict] = {}
    for t in traces:
        proc = t.get("procedure")
        applicant = (t.get("applicant_name") or "").strip()
        key = (applicant.lower(), proc)

        total = t.get("key_fields_total") or key_fields_total(proc)
        filled = t.get("key_fields_filled")
        if filled is None:  # trace cũ → tính lại từ process_requests.fields
            total, filled = count_key_fields(proc, fields_by_req.get(t.get("request_id")))

        created = t.get("created_at")
        ngay = created.astimezone(VN_TZ).strftime("%Y-%m-%d") if isinstance(created, datetime) else ""
        rows[key] = {
            "ma": t.get("request_id") or "",
            "thu_tuc": t.get("procedure_label") or proc,
            "ngay": ngay,
            "total": total,
            "filled": filled,
            "applicant": applicant,
        }

    # Ghi Excel.
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "AutoFill"
    header_fill = PatternFill("solid", fgColor="2F5496")
    header_font = Font(color="FFFFFF", bold=True)
    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(1, c, h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r, data in enumerate(sorted(rows.values(), key=lambda x: (x["thu_tuc"], x["applicant"])), start=2):
        ws.cell(r, 1, data["ma"])
        ws.cell(r, 2, data["thu_tuc"])
        ws.cell(r, 3, data["ngay"])
        ws.cell(r, 4, data["total"])
        ws.cell(r, 5, data["filled"])
        # cột 6,7 (chấm tay) để trống; 8,9 để trống
        ws.cell(r, 9, f"Người làm: {data['applicant'] or '(không xác định)'}")

    widths = [16, 42, 12, 16, 18, 14, 14, 20, 32]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"

    wb.save(out_path)
    client.close()
    print(f"Ngày (VN): {day:%Y-%m-%d} | traces auto-fill: {len(traces)} | dòng (sau dedup người+thủ tục): {len(rows)}")
    print(f"Đã ghi: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
