"""Excel báo cáo hằng ngày: sheet Báo cáo (từng dòng) + sheet Theo đơn vị (tài khoản xem nhiều đơn vị)."""
import io
from datetime import date, timedelta, timezone

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.reports.integration import province_name

_HEADER_FILL = PatternFill("solid", fgColor="1256C7")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_THIN = Side(style="thin", color="D3DCE8")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_WRAP = Alignment(vertical="top", wrap_text=True)
_VN = timezone(timedelta(hours=7))
_WEEKDAY = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]


def _dmy(day: str) -> str:
    y, m, d = day.split("-")
    return f"{d}/{m}/{y}"


def _vn_time(value) -> str:
    if not value:
        return ""
    value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value.astimezone(_VN).strftime("%H:%M %d/%m/%Y")


def _sheet(wb: Workbook, title: str, headers: list[tuple[str, int]], rows: list[list]) -> None:
    ws = wb.create_sheet(title)
    for col, (label, width) in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=label)
        cell.fill, cell.font, cell.border = _HEADER_FILL, _HEADER_FONT, _BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = width
    for r, values in enumerate(rows, start=2):
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border, cell.alignment = _BORDER, _WRAP
    ws.freeze_panes = "A2"


def build_workbook(docs: list[dict], units: list[dict] | None) -> bytes:
    """`units` = các đơn vị trong phạm vi lọc (None với tài khoản đơn vị → không có sheet Theo đơn vị)."""
    wb = Workbook()
    wb.remove(wb.active)
    rows = []
    for i, d in enumerate(docs, start=1):
        tl, tt = int(d.get("assistant_count") or 0), int(d.get("actual_count") or 0)
        updated = d.get("updated_at") if d.get("updated_at") != d.get("created_at") else None
        rows.append([
            i, _dmy(d["date"]), _WEEKDAY[date.fromisoformat(d["date"]).weekday()], _vn_time(d.get("created_at")),
            d.get("province") or "", d.get("unit_name") or "", tl, tt, tt - tl,
            d.get("advantages") or "", d.get("difficulties") or "", _vn_time(updated),
        ])
    _sheet(wb, "Báo cáo", [
        ("STT", 6), ("Ngày báo cáo", 13), ("Thứ", 10), ("Gửi lúc", 17), ("Tỉnh, thành phố", 18),
        ("Phường, xã", 26), ("Phát sinh trên Trợ lý", 13), ("Cán bộ ghi nhận thực tế", 14), ("Chênh lệch", 11),
        ("Thuận lợi", 50), ("Khó khăn", 50), ("Cập nhật lúc", 17),
    ], rows)

    if units is not None:
        agg: dict[str, list[int]] = {}
        for d in docs:
            a = agg.setdefault(d.get("unit_id"), [0, 0, 0])
            a[0] += 1
            a[1] += int(d.get("assistant_count") or 0)
            a[2] += int(d.get("actual_count") or 0)
        per_unit = []
        for u in sorted(units, key=lambda u: (province_name(u.get("tinh")), u.get("xa") or u.get("name") or "")):
            n, tl, tt = agg.get(u["unitId"], [0, 0, 0])
            per_unit.append([
                province_name(u.get("tinh")) or "", u.get("xa") or u.get("name") or "", n, tl, tt, tt - tl,
                round(tl / tt * 100) if tt else "",
            ])
        _sheet(wb, "Theo đơn vị", [
            ("Tỉnh, thành phố", 18), ("Phường, xã", 28), ("Số ngày báo cáo", 12), ("Phát sinh trên Trợ lý", 13),
            ("Cán bộ ghi nhận thực tế", 14), ("Chênh lệch", 11), ("Tỷ lệ qua Trợ lý (%)", 13),
        ], per_unit)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
