"""Xuất Excel cho BẢNG THỐNG KÊ (module riêng, độc lập với báo cáo Excel của trang quản trị).

Dựng workbook từ CHÍNH dữ liệu đã gộp Auto Fill + Handfree của /summary (không truy cập DB ở đây
để dễ kiểm thử). Bố cục bám mockup dashboard: 3 sheet thống kê — Tổng quan / Theo đơn vị / Theo
thủ tục — màu xanh #1256C7, gọn và dễ đọc. Chưa gồm thời lượng xử lý.
"""
import io
from datetime import datetime, timezone

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

_VN_TZ = timezone.utc  # nhãn giờ để dạng UTC+7 khi hiển thị
_BLUE = "1256C7"
_BLUE_LIGHT = "EAF1FD"
_TOTAL_FILL = PatternFill("solid", fgColor="DDEBF7")
_HEADER_FILL = PatternFill("solid", fgColor=_BLUE)
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_TITLE_FONT = Font(bold=True, color=_BLUE, size=15)
_META_LABEL = Font(bold=True, color="5B6B85", size=10)
_META_VALUE = Font(size=10, color="0F1B33")
_SECTION_FONT = Font(bold=True, color=_BLUE, size=11)
_BOLD = Font(bold=True)
_THIN = Side(style="thin", color="D3DCE8")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_RIGHT = Alignment(horizontal="right", vertical="center")
_NUMFMT = "#,##0"


def _cap(xa: str | None) -> str:
    text = (xa or "").strip().lower()
    if text.startswith("phường") or text.startswith("phuong"):
        return "Phường"
    if text.startswith("xã") or text.startswith("xa"):
        return "Xã"
    if text.startswith("thị") or text.startswith("thi"):
        return "Thị trấn"
    return "Đơn vị"


def _period_label(rng: dict) -> str:
    start = (rng or {}).get("from")
    end = (rng or {}).get("to")
    if not start and not end:
        return "Tất cả thời gian"
    if start and end and start == end:
        return f"Ngày {start}"
    if start and end:
        return f"Từ {start} đến {end}"
    return f"Đến {end}" if end else f"Từ {start}"


def _scope_label(scope: dict) -> str:
    if scope.get("canViewUnits"):
        province = scope.get("province") or ""
        return f"Toàn tỉnh {province}".strip()
    self_unit = scope.get("self") or {}
    return self_unit.get("xa") or self_unit.get("name") or "Đơn vị của bạn"


def _write_header(ws, row: int, headers: list[tuple[str, str, int]]) -> None:
    """headers = [(nhãn, align 'l'|'c'|'r', width)]; tô nền xanh + freeze dưới header."""
    for col, (label, align, width) in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=label)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _CENTER
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = f"A{row + 1}"


def _body_cell(ws, row: int, col: int, value, align: str, *, num=False, bold=False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.border = _BORDER
    cell.alignment = {"l": _LEFT, "c": _CENTER, "r": _RIGHT}[align]
    if bold:
        cell.font = _BOLD
    if num:
        cell.number_format = _NUMFMT
    return cell


def _sheet_overview(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("Tổng hợp")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 22

    scope = data.get("scope") or {}
    kpis = data.get("kpis") or {}
    sources = data.get("sources") or {}

    title = ws.cell(row=2, column=2, value="BÁO CÁO THỐNG KÊ HỒ SƠ HÀNH CHÍNH CÔNG")
    title.font = _TITLE_FONT
    ws.merge_cells("B2:D2")

    now = datetime.now(timezone.utc)
    hf = "Auto Fill + Handfree" if sources.get("handfree") else "Auto Fill (chưa gộp Handfree)"
    meta = [
        ("Phạm vi", _scope_label(scope)),
        ("Kỳ báo cáo", _period_label(data.get("range") or {})),
        ("Nguồn số liệu", hf),
        ("Thời điểm xuất", _fmt_now(now)),
    ]
    r = 4
    for label, value in meta:
        lc = ws.cell(row=r, column=2, value=label)
        lc.font = _META_LABEL
        vc = ws.cell(row=r, column=3, value=value)
        vc.font = _META_VALUE
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        r += 1

    r += 1
    sect = ws.cell(row=r, column=2, value="CHỈ SỐ CHÍNH")
    sect.font = _SECTION_FONT
    r += 1
    top = kpis.get("topProcedure") or {}
    rows = [("Tổng hồ sơ tiếp nhận", kpis.get("dossiers", 0), True)]
    if scope.get("canViewUnits"):
        rows.append(("Số đơn vị trong phạm vi", scope.get("unitCount", 0), True))
    rows.append(("Loại thủ tục phát sinh", kpis.get("procedureTypes", 0), True))
    rows.append(("Thủ tục nhiều hồ sơ nhất", top.get("count", 0) if top else 0, True))
    for label, value, num in rows:
        lc = ws.cell(row=r, column=2, value=label)
        lc.border = _BORDER
        lc.alignment = _LEFT
        vc = ws.cell(row=r, column=3, value=value)
        vc.border = _BORDER
        vc.alignment = _RIGHT
        vc.font = _BOLD
        if num:
            vc.number_format = _NUMFMT
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        r += 1
    if top:
        lc = ws.cell(row=r, column=2, value="— Tên thủ tục nhiều nhất")
        lc.font = Font(italic=True, size=10, color="5B6B85")
        lc.alignment = _LEFT
        vc = ws.cell(row=r, column=3, value=top.get("label") or "")
        vc.alignment = _LEFT
        vc.font = Font(size=10)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        r += 1

    by_day = data.get("byDay") or []
    if by_day:
        r += 1
        ws.cell(row=r, column=2, value="HỒ SƠ THEO NGÀY").font = _SECTION_FONT
        r += 1
        for col, label in ((2, "Ngày"), (3, "Số hồ sơ")):
            cell = ws.cell(row=r, column=col, value=label)
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = _CENTER
            cell.border = _BORDER
        r += 1
        for item in by_day:
            _body_cell(ws, r, 2, item.get("date"), "c")
            _body_cell(ws, r, 3, int(item.get("count") or 0), "r", num=True)
            r += 1


def _sheet_units(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("Theo đơn vị")
    ws.sheet_view.showGridLines = False
    units = data.get("units") or []
    _write_header(ws, 1, [
        ("STT", "c", 6),
        ("Đơn vị", "l", 34),
        ("Cấp", "c", 12),
        ("Số hồ sơ", "r", 13),
        ("Loại thủ tục", "r", 13),
        ("Thủ tục nhiều nhất", "l", 42),
    ])
    ranked = sorted(units, key=lambda u: (-int(u.get("dossiers") or 0), (u.get("xa") or ""), u.get("name") or ""))
    total = 0
    r = 2
    for idx, u in enumerate(ranked, start=1):
        top = u.get("topProcedure") or {}
        dossiers = int(u.get("dossiers") or 0)
        total += dossiers
        _body_cell(ws, r, 1, idx, "c")
        _body_cell(ws, r, 2, u.get("xa") or u.get("name") or "—", "l")
        _body_cell(ws, r, 3, _cap(u.get("xa")), "c")
        _body_cell(ws, r, 4, dossiers, "r", num=True, bold=True)
        _body_cell(ws, r, 5, int(u.get("procedureTypes") or 0), "r", num=True)
        _body_cell(ws, r, 6, (top.get("label") or "—") if top else "—", "l")
        r += 1
    _total_row(ws, r, total, span_label="A{0}:C{0}", value_col=4, extra_cols=[5, 6])


def _sheet_procedures(wb: Workbook, data: dict) -> None:
    ws = wb.create_sheet("Theo thủ tục")
    ws.sheet_view.showGridLines = False
    procs = data.get("byProcedure") or []
    show_units = bool((data.get("scope") or {}).get("canViewUnits")) and not data.get("selected")
    headers = [("Hạng", "c", 6), ("Tên thủ tục", "l", 52), ("Số hồ sơ", "r", 13)]
    if show_units:
        headers.append(("Đơn vị phát sinh", "r", 16))
    headers.append(("Tỷ trọng", "r", 12))
    _write_header(ws, 1, headers)

    total = sum(int(p.get("count") or 0) for p in procs)
    r = 2
    for idx, p in enumerate(procs, start=1):
        count = int(p.get("count") or 0)
        _body_cell(ws, r, 1, idx, "c")
        _body_cell(ws, r, 2, p.get("label") or "—", "l")
        _body_cell(ws, r, 3, count, "r", num=True, bold=True)
        col = 4
        if show_units:
            _body_cell(ws, r, col, int(p.get("units") or 0), "r", num=True)
            col += 1
        pct = round(count / total * 100, 1) if total else 0
        pc = _body_cell(ws, r, col, pct / 100, "r")
        pc.number_format = "0.0%"
        r += 1
    last_col = 5 if show_units else 4
    _total_row(ws, r, total, span_label=f"A{{0}}:B{{0}}", value_col=3,
               extra_cols=[c for c in range(4, last_col + 1)])


def _total_row(ws, row: int, total: int, *, span_label: str, value_col: int, extra_cols: list[int]) -> None:
    ws.merge_cells(span_label.format(row))
    label = ws.cell(row=row, column=1, value="TỔNG CỘNG")
    label.font = _BOLD
    label.alignment = _CENTER
    for col in range(1, value_col + 1 + len(extra_cols)):
        cell = ws.cell(row=row, column=col)
        cell.fill = _TOTAL_FILL
        cell.border = _BORDER
    val = ws.cell(row=row, column=value_col, value=total)
    val.font = _BOLD
    val.alignment = _RIGHT
    val.number_format = _NUMFMT
    val.fill = _TOTAL_FILL


def _fmt_now(now: datetime) -> str:
    # Hiển thị theo giờ Việt Nam (UTC+7).
    from datetime import timedelta
    vn = now.astimezone(timezone(timedelta(hours=7)))
    return vn.strftime("%H:%M ngày %d/%m/%Y (giờ Việt Nam)")


def _fmt_received(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        from datetime import timedelta
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=7))).strftime("%H:%M %d/%m/%Y")
    except (ValueError, TypeError):
        return str(iso)


def _sheet_logs(wb: Workbook, logs: list[dict]) -> None:
    ws = wb.create_sheet("Nhật ký hồ sơ")
    ws.sheet_view.showGridLines = False
    # Mỗi dòng là một HỒ SƠ (không còn là một lượt điền/đính kèm) → bỏ cột "Bước", thêm mốc
    # nộp và phiếu đánh giá. Giữ đúng thứ tự cột của bảng trên màn hình.
    _write_header(ws, 1, [
        ("Mã hồ sơ", "l", 22),
        ("Thời gian tiếp nhận", "c", 20),
        ("Thời gian nộp hồ sơ", "c", 20),
        ("Đơn vị tiếp nhận", "l", 28),
        ("Thủ tục", "l", 52),
        ("Đánh giá", "c", 16),
    ])
    if not logs:
        cell = ws.cell(row=2, column=1, value="Chưa có hồ sơ nào trong kỳ.")
        cell.alignment = _LEFT
        ws.merge_cells("A2:F2")
        return
    r = 2
    for it in logs:
        rating = it.get("rating") or {}
        # Phân biệt ba trạng thái: chưa từng được hỏi (—), hỏi mà bỏ qua, và có mức thật.
        if not rating:
            rating_text = "—"
        elif rating.get("level") is None:
            rating_text = "Bỏ qua"
        else:
            rating_text = rating.get("levelLabel") or str(rating.get("level"))
        _body_cell(ws, r, 1, it.get("dossierId") or "—", "l")
        _body_cell(ws, r, 2, _fmt_received(it.get("receivedAt")), "c")
        _body_cell(ws, r, 3, _fmt_received(it.get("submittedAt")) if it.get("submittedAt") else "chưa nộp", "c")
        _body_cell(ws, r, 4, it.get("unitName") or "—", "l")
        _body_cell(ws, r, 5, it.get("procedureLabel") or "—", "l")
        _body_cell(ws, r, 6, rating_text, "c")
        r += 1


def build_dashboard_workbook(data: dict, logs: list[dict] | None = None) -> bytes:
    """4 sheet cho tài khoản Tỉnh (có 'Theo đơn vị'); 3 sheet cho HCC xã/phường (bỏ 'Theo đơn vị')."""
    wb = Workbook()
    wb.remove(wb.active)
    _sheet_overview(wb, data)
    if (data.get("scope") or {}).get("canViewUnits"):
        _sheet_units(wb, data)
    _sheet_procedures(wb, data)
    _sheet_logs(wb, logs or [])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def export_filename(data: dict) -> str:
    scope = data.get("scope") or {}
    selected = data.get("selected") or {}
    if selected:
        who = selected.get("xa") or selected.get("name") or "don-vi"
    else:
        who = _scope_label(scope)
    period = _period_label(data.get("range") or {})
    return f"Thong ke ho so - {who} - {period}.xlsx".replace("/", "-")
