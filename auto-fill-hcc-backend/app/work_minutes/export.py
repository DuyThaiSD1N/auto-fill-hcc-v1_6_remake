"""File Word biên bản làm việc (A4, Times New Roman 14) — cùng bố cục bản xem trước trên web.

Ô chưa điền in thành dòng chấm để ghi tay, không tự điền nội dung thay người làm biên bản.
"""
import io
from datetime import date

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Twips

from app.work_minutes.rules import COMPANY, total_of

BLANK = "…………………"
_FONT = "Times New Roman"


def _num(value: int) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _p2(value) -> str:
    text = str(value or "").strip()
    return text.zfill(2) if text.isdigit() and len(text) < 2 else text


def _v(value) -> str:
    return str(value or "").strip() or BLANK


def _dmy(day: str) -> str:
    d = date.fromisoformat(day)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def _scope_line(doc: dict) -> str:
    # Hệ thống chưa phân biệt chắc thủ tục cấp xã / cấp tỉnh → chỉ ghi tổng số thủ tục.
    count = sum(1 for r in doc.get("rows") or [] if int(r.get("n") or 0) > 0)
    return f"{_p2(count)} thủ tục hành chính"


def _sign_title(person: dict | None) -> str:
    # Phó Giám đốc ký thì vẫn là "Đại diện", không in thành chức danh Giám đốc.
    role = str((person or {}).get("r") or "").lower()
    return "GIÁM ĐỐC TRUNG TÂM PVHCC" if "giám đốc" in role and "phó" not in role else "ĐẠI DIỆN TRUNG TÂM PVHCC"


def _pick(people: list[dict], index: int) -> dict | None:
    return people[index] if 0 <= index < len(people) else None


def _para(container, text: str = "", *, bold=False, italic=False, underline=False, size=None, align="both",
          indent=True, before=0, after=4, keep=False, tab_cm=None):
    p = container.add_paragraph()
    fmt = p.paragraph_format
    fmt.alignment = {"both": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                     "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    fmt.first_line_indent = Cm(1) if indent else None
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = 1.2
    fmt.keep_with_next = keep
    if tab_cm:
        fmt.tab_stops.add_tab_stop(Cm(tab_cm))
    if text:
        run = p.add_run(text)
        run.bold, run.italic, run.underline = bold, italic, underline
        if size:
            run.font.size = Pt(size)
    return p


def _borders(table, line: bool) -> None:
    # Ghi thẳng đường kẻ vào bảng (không dựa vào style "Table Grid") để trình xem khác Word cũng hiện đúng.
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single" if line else "nil")
        if line:
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000")
        borders.append(el)
    table._tbl.tblPr.append(borders)


def _no_borders(table) -> None:
    _borders(table, False)


def _widths(table, twips: list[int]) -> None:
    """Cột cố định: ghi cả tblGrid lẫn từng ô, bố cục fixed — thiếu một trong hai thì Word/trình xem tự co cột."""
    table.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    for col, w in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), twips):
        col.set(qn("w:w"), str(w))
    for row in table.rows:
        for cell, w in zip(row.cells, twips):
            cell.width = Twips(w)


def _cell_lines(cell, lines: list[tuple[str, dict]]) -> None:
    cell.paragraphs[0]._element.getparent().remove(cell.paragraphs[0]._element)
    for text, opts in lines:
        _para(cell, text, align="center", indent=False, after=0, **opts)


def build_docx(minutes: dict) -> bytes:
    """`minutes`: {from, to, lap, doc} — doc theo rules.Doc."""
    doc = minutes["doc"]
    place = str(doc.get("place") or "").strip() or BLANK
    prov = str(doc.get("prov") or "").strip() or BLANK
    lap = date.fromisoformat(minutes["lap"])

    out = Document()
    section = out.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = section.right_margin = Cm(2)
    section.left_margin = Cm(3)
    normal = out.styles["Normal"]
    normal.font.name = _FONT
    normal.font.size = Pt(14)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), _FONT)

    head = out.add_table(rows=1, cols=2)
    _no_borders(head)
    _widths(head, [4000, 5400])
    # Hai khối chữ đầu trang rộng hơn vùng chữ: lấn ra lề trái một chút như mẫu biên bản giấy.
    indent = OxmlElement("w:tblInd")
    indent.set(qn("w:w"), "-300")
    indent.set(qn("w:type"), "dxa")
    head._tbl.tblPr.append(indent)
    _cell_lines(head.cell(0, 0), [(COMPANY["l1"], {"bold": True, "size": 12}), (COMPANY["l2"], {"bold": True, "size": 12})])
    _cell_lines(head.cell(0, 1), [("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", {"bold": True, "size": 12}),
                                  ("Độc lập - Tự do - Hạnh phúc", {"bold": True, "underline": True, "size": 13})])

    for i, title in enumerate(["BIÊN BẢN", "Làm việc về triển khai Trợ lý Nhân dân hỗ trợ người dân",
                               "thực hiện thủ tục hành chính tại Trung tâm Phục vụ hành chính công", f"{place}, {prov}"]):
        _para(out, title, bold=True, align="center", indent=False, before=12 if i == 0 else 0, after=0)
    _para(out, f"Hôm nay, vào hồi {_v(doc.get('start'))} ngày {lap.day:02d} tháng {lap.month:02d} năm {lap.year}, "
               f"tại Trung tâm Phục vụ hành chính công {place}, {prov}, chúng tôi gồm:", before=12)

    def heading(text: str) -> None:
        _para(out, text, bold=True, align="left", before=3, keep=True)

    def people(items: list[dict]) -> None:
        for person in items or []:
            _para(out, f"- {person.get('x') or 'Ông/Bà'}: {_v(person.get('n'))}\tChức vụ: {_v(person.get('r'))}", tab_cm=9)

    heading("I. THÀNH PHẦN THAM DỰ")
    heading(f"1. Đại diện đơn vị triển khai ({COMPANY['full']})")
    people(doc.get("cty"))
    heading(f"2. Đại diện Trung tâm Phục vụ hành chính công {place}, {prov}")
    people(doc.get("tt"))

    d_from, d_to = _dmy(minutes["from"]), _dmy(minutes["to"])
    heading(f"II. KẾT QUẢ CÔNG VIỆC TỪ NGÀY {d_from} ĐẾN NGÀY {d_to}")
    note = str(doc.get("mayNote") or "").strip()
    _para(out, f"- Cài đặt công cụ trên {_v(_p2(doc.get('may')))} máy tại Trung tâm{' ' + note if note else ''}.")
    _para(out, f"- Thiết bị bổ sung (nếu có): {_v(doc.get('thietBi')).rstrip('.')}.")
    total = total_of(doc)
    _para(out, f"- Số hồ sơ thực tế đã hỗ trợ tiếp nhận, xử lý cho người dân từ ngày {d_from} đến hết ngày {d_to}: "
               f"{_num(total)} hồ sơ, thuộc {_scope_line(doc)}; trong đó {_num(doc.get('v'))} hồ sơ tiếp nhận qua "
               f"phiên bản đã tích hợp giọng nói và {_num(doc.get('nv'))} hồ sơ qua phiên bản chưa tích hợp giọng nói "
               "(chi tiết tại bảng dưới đây).")
    _para(out, f"- Số cán bộ được hướng dẫn, tập huấn: {_v(_p2(doc.get('canBo')))} cán bộ.")

    rows = doc.get("rows") or []
    table = out.add_table(rows=len(rows) + 2, cols=4)
    _borders(table, True)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    def cell(r: int, c: int, text: str, *, bold=False, align="center") -> None:
        target = table.cell(r, c)
        target.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        target.paragraphs[0]._element.getparent().remove(target.paragraphs[0]._element)
        _para(target, text, bold=bold, size=13, align=align, indent=False, after=0)

    for c, text in enumerate(["STT", "Mã thủ tục", "Tên thủ tục", "Tổng số hồ sơ"]):
        cell(0, c, text, bold=True)
    header = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    header.append(repeat)
    for i, row in enumerate(rows, start=1):
        cell(i, 0, str(i))
        cell(i, 1, str(row.get("code") or "").strip() or "—")
        cell(i, 2, str(row.get("name") or ""), align="both")
        cell(i, 3, _num(row.get("n")))
    last = len(rows) + 1
    merged = table.cell(last, 0).merge(table.cell(last, 2))
    merged.paragraphs[0]._element.getparent().remove(merged.paragraphs[0]._element)
    for extra in merged.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    _para(merged, "Tổng", bold=True, size=13, align="center", indent=False, after=0)
    cell(last, 3, _num(total), bold=True)
    _widths(table, [680, 1300, 5791, 1300])
    _para(out, "", after=0)

    for title, key in (("III. KHÓ KHĂN, VƯỚNG MẮC VÀ HƯỚNG XỬ LÝ", "issues"), ("IV. ĐÁNH GIÁ CỦA TRUNG TÂM", "evals"),
                       ("V. CÔNG VIỆC DỰ KIẾN TIẾP THEO", "next")):
        heading(title)
        lines = [str(t).strip() for t in doc.get(key) or [] if str(t).strip()]
        for text in lines or [BLANK]:
            _para(out, text)
    _para(out, f"Biên bản kết thúc vào lúc {_v(doc.get('end'))} cùng ngày, được lập thành 02 bản có giá trị như nhau, "
               "mỗi bên giữ 01 bản; đã được đọc lại cho các thành phần tham dự cùng nghe, nhất trí và ký tên dưới đây./.")

    tt_sign = _pick(doc.get("tt") or [], int(doc.get("signTT", -1)))
    cty_sign = _pick(doc.get("cty") or [], int(doc.get("signCty", -1)))
    _para(out, "", after=0, keep=True)
    sign = out.add_table(rows=1, cols=2)
    _no_borders(sign)
    _widths(sign, [4535, 4536])
    blank4 = [("", {})] * 4
    _cell_lines(sign.cell(0, 0), [(_sign_title(tt_sign), {"bold": True}), (str(doc.get("place") or "").strip().upper(), {"bold": True}),
                                  ("(Ký, ghi rõ họ tên)", {"italic": True}), *blank4,
                                  ((tt_sign or {}).get("n") or "", {"bold": True})])
    _cell_lines(sign.cell(0, 1), [("ĐẠI DIỆN ĐƠN VỊ TRIỂN KHAI", {"bold": True}), ("", {}),
                                  ("(Ký, ghi rõ họ tên)", {"italic": True}), *blank4,
                                  ((cty_sign or {}).get("n") or "", {"bold": True})])

    _para(out, "", after=0)
    _para(out, "Nơi nhận:", bold=True, italic=True, size=12, align="left", indent=False, after=0)
    for text in (f"- Trung tâm PVHCC {place} (01 bản);", f"- {COMPANY['short']} (01 bản)."):
        _para(out, text, size=11, align="left", indent=False, after=0)

    out.core_properties.title = f"Biên bản làm việc - {doc.get('place') or ''}"
    out.core_properties.author = COMPANY["full"]
    buffer = io.BytesIO()
    out.save(buffer)
    return buffer.getvalue()
