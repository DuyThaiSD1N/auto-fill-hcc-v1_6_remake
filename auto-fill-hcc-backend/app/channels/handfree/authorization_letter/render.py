"""Dựng GIẤY ỦY QUYỀN ra .docx (tải về sửa tiếp) và .pdf (in tại quầy) từ CÙNG một mẫu.

Mẫu dựng một lần thành danh sách khối (`_blocks`) rồi hai bộ xuất đọc chung, nên bản in và bản
Word không bao giờ lệch chữ nhau. Ô trống in dòng chấm để công dân viết tay.

Mỗi bên có thể NHIỀU người (đồng ủy quyền / ủy quyền cho nhiều người). Bên một người giữ đúng mẫu
gốc; bên từ hai người trở lên ghi "Bao gồm:" rồi đánh số từng người.
"""
import html as _html
import io
from dataclasses import dataclass, field

import fitz
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = "Times New Roman"


@dataclass
class Party:
    hoTen: str = ""
    ngaySinh: str = ""
    diaChi: str = ""
    soDinhDanh: str = ""
    ngayCap: str = ""
    noiCap: str = ""


@dataclass
class Letter:
    benUyQuyen: list[Party] = field(default_factory=lambda: [Party()])
    benDuocUyQuyen: list[Party] = field(default_factory=lambda: [Party()])
    ghiNgaySinhDuocUyQuyen: bool = False
    noiDung: str = ""
    lapTai: str = ""
    ngayLap: str = ""  # dd/mm/yyyy
    soBan: str = "2"
    moiBenGiu: str = "1"


# Một đoạn = danh sách mảnh (chữ, in đậm?). Giá trị người dùng nhập in đậm như mockup.
Seg = tuple[str, bool]


def _v(value: str, dots: int) -> Seg:
    text = (value or "").strip()
    return (text, True) if text else ("." * dots, False)


def _party_lines(p: Party, with_birth: bool, number: int | None = None) -> list[list[Seg]]:
    name = [(f"{number}. " if number else "", False), ("Họ tên: ", False), _v(p.hoTen, 45)]
    if with_birth:
        name += [(", sinh ngày ", False), _v(p.ngaySinh, 20)]
    return [
        name,
        [("Địa chỉ: ", False), _v(p.diaChi, 70)],
        [("Số CCCD: ", False), _v(p.soDinhDanh, 25), (" Cấp ngày: ", False), _v(p.ngayCap, 18),
         (" Nơi cấp: ", False), _v(p.noiCap, 28)],
    ]


def _side_blocks(people: list[Party], with_birth: bool) -> list[tuple[str, object]]:
    """Một người → mẫu gốc. Từ hai người → "Bao gồm:" + đánh số; dòng địa chỉ/CCCD thụt vào."""
    people = people or [Party()]
    if len(people) == 1:
        return [("p", line) for line in _party_lines(people[0], with_birth)]
    out: list[tuple[str, object]] = [("p", [("Bao gồm:", False)])]
    for i, person in enumerate(people, 1):
        first, *rest = _party_lines(person, with_birth, i)
        out.append(("p", first))
        out.extend(("p_sub", line) for line in rest)
    return out


def _blocks(d: Letter) -> list[tuple[str, object]]:
    day = month = year = ""
    parts = (d.ngayLap or "").strip().split("/")
    if len(parts) == 3:
        day, month, year = parts
    content = (d.noiDung or "").strip()
    return [
        ("nation", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"),
        ("motto", "Độc lập – Tự do – Hạnh phúc"),
        ("title", "GIẤY ỦY QUYỀN"),
        ("p_i", [("Hôm nay, ngày ", False), _v(day, 6), (" tháng ", False), _v(month, 6),
                 (" năm ", False), _v(year, 6), (".", False)]),
        ("p_i", [("Tại ", False), _v(d.lapTai, 40), (".", False)]),
        ("p_i", [("Chúng tôi gồm có:", False)]),
        ("sec", "I. BÊN ỦY QUYỀN:"),
        *_side_blocks(d.benUyQuyen, True),
        ("sec", "II. BÊN ĐƯỢC ỦY QUYỀN:"),
        *_side_blocks(d.benDuocUyQuyen, d.ghiNgaySinhDuocUyQuyen),
        ("sec", "III. NỘI DUNG ỦY QUYỀN:"),
        *([("p", [(line, False)]) for line in content.splitlines() if line.strip()]
          or [("p", [("." * 90, False)])]),
        ("sec", "IV. THỜI GIAN ỦY QUYỀN"),
        ("p", [("Đến khi hoàn tất nội dung ủy quyền nêu trên hoặc giấy ủy quyền hết hiệu lực theo quy "
                "định của pháp luật.", False)]),
        ("sec", "V. CAM KẾT"),
        ("p", [("- Hai bên cam kết sẽ hoàn toàn chịu trách nhiệm trước Pháp luật về mọi thông tin ủy "
                "quyền ở trên.", False)]),
        ("p", [("- Mọi tranh chấp phát sinh giữa bên ủy quyền và bên được ủy quyền sẽ do hai bên tự "
                "giải quyết.", False)]),
        ("p", [("Giấy ủy quyền được lập thành ", False), _v(d.soBan, 4), (" bản, mỗi bên giữ ", False),
               _v(d.moiBenGiu, 4), (" bản.", False)]),
        ("sign", ([p.hoTen.strip() for p in d.benUyQuyen or [Party()]],
                  [p.hoTen.strip() for p in d.benDuocUyQuyen or [Party()]])),
    ]


# ── DOCX ──

def _run(par, text: str, *, bold=False, italic=False, size=13):
    run = par.add_run(text)
    run.bold, run.italic = bold, italic
    run.font.size = Pt(size)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return run


def to_docx(d: Letter) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = sec.right_margin = Cm(2)
    sec.left_margin = Cm(3)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(13)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    for kind, value in _blocks(d):
        if kind == "sign":
            left, right = value
            gap = 4 if max(len(left), len(right)) == 1 else 3  # khớp bản PDF (_sign_html)
            table = doc.add_table(rows=1, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            for cell, role, names in zip(table.rows[0].cells, ("BÊN ỦY QUYỀN", "BÊN ĐƯỢC ỦY QUYỀN"), (left, right)):
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _run(p, role, bold=True)
                p2 = cell.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _run(p2, "(Ký, ghi rõ họ tên)", italic=True)
                # Mỗi người một khoảng trống để ký tươi, tên in ngay dưới chỗ ký.
                for name in names:
                    for _ in range(gap):
                        cell.add_paragraph()
                    p3 = cell.add_paragraph()
                    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    _run(p3, name, bold=True)
            continue
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(4)
        if kind in ("nation", "motto", "title"):
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(par, value, bold=True, size={"title": 16}.get(kind, 13))
            if kind == "title":
                par.paragraph_format.space_before = Pt(12)
                par.paragraph_format.space_after = Pt(12)
        elif kind == "sec":
            par.paragraph_format.space_before = Pt(6)
            _run(par, value, bold=True)
        else:
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if kind == "p_sub":
                par.paragraph_format.left_indent = Cm(0.6)
            for text, bold in value:
                _run(par, text, bold=bold, italic=(kind == "p_i" and not bold))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── PDF ──

def _esc(s: str) -> str:
    return _html.escape(s or "")


_FONT_SIZES = (12.5, 12, 11.5)  # thử giảm nhẹ để giấy NHIỀU người vẫn vừa một trang cùng chỗ ký


def _body_style(size: float) -> str:
    return f"font-family:serif;font-size:{size}pt;line-height:1.3"


def _sign_html(left: list[str], right: list[str], size: float) -> str:
    td = '<td style="width:50%;text-align:center;vertical-align:top">{}</td>'

    # Khoảng ký tươi: 4 dòng như mẫu gốc; nhiều người thì 3 dòng (~1,8 cm, vẫn đủ ký) để cả khối
    # chữ ký còn nằm chung trang với nội dung.
    gap = "<br>" * (4 if max(len(left), len(right)) == 1 else 3)

    def col(role: str, names: list[str]) -> str:
        signs = "".join(f"{gap}<b>{_esc(n)}</b>" for n in names)
        return td.format(f"<b>{role}</b><br><i>(Ký, ghi rõ họ tên)</i>{signs}")
    return (f'<div style="{_body_style(size)}"><table style="width:100%">'
            f'<tr>{col("BÊN ỦY QUYỀN", left)}{col("BÊN ĐƯỢC ỦY QUYỀN", right)}</tr></table></div>')


def _html_doc(d: Letter, size: float) -> str:
    out = []
    for kind, value in _blocks(d):
        if kind == "nation":
            out.append(f'<p style="text-align:center;font-weight:bold;margin:0">{_esc(value)}</p>')
        elif kind == "motto":
            out.append(f'<p style="text-align:center;font-weight:bold;margin:0 0 8pt">{_esc(value)}</p>')
        elif kind == "title":
            out.append(f'<p style="text-align:center;font-weight:bold;font-size:16pt;margin:6pt 0 8pt">'
                       f'{_esc(value)}</p>')
        elif kind == "sec":
            out.append(f'<p style="font-weight:bold;margin:5pt 0 1pt">{_esc(value)}</p>')
        elif kind == "sign":
            continue  # khối chữ ký đặt riêng ở to_pdf (bảng trong Story bị cắt mất hàng khi giáp đáy trang)
        else:
            segs = "".join(f"<b>{_esc(t)}</b>" if b else _esc(t) for t, b in value)
            style = "margin:1pt 0;text-align:justify" + (";font-style:italic" if kind == "p_i" else "")
            if kind == "p_sub":
                style += ";margin-left:17pt"
            out.append(f'<p style="{style}">{segs}</p>')
    return f'<div style="{_body_style(size)}">{"".join(out)}</div>'


def _pdf_at(d: Letter, size: float) -> fitz.Document:
    story = fitz.Story(html=_html_doc(d, size))
    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    more, filled = 1, _WHERE
    while more:
        device = writer.begin_page(_PAGE)
        more, filled = story.place(_WHERE)
        filled = fitz.Rect(filled)
        story.draw(device)
        writer.end_page()
    writer.close()

    doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
    left, right = next(v for k, v in _blocks(d) if k == "sign")
    sign = _sign_html(left or [""], right or [""], size)
    box = fitz.Rect(_WHERE.x0, filled.y1 + 14, _WHERE.x1, _WHERE.y1)
    spare, _ = doc[-1].insert_htmlbox(box, sign, scale_low=1) if box.height > 40 else (-1, 1)
    if spare < 0:
        page = doc.new_page(width=_PAGE.width, height=_PAGE.height)
        page.insert_htmlbox(_WHERE, sign, scale_low=1)
    return doc


_PAGE = fitz.paper_rect("a4")
# A4, lề trái 3 cm, còn lại 2 cm (khớp bản Word).
_WHERE = fitz.Rect(_PAGE.x0 + 85, _PAGE.y0 + 57, _PAGE.x1 - 57, _PAGE.y1 - 57)


def to_pdf(d: Letter) -> bytes:
    """Nội dung dài tự sang trang.

    Khối chữ ký đặt RIÊNG sau phần nội dung: bảng trong Story giáp đáy trang bị cắt mất hàng mà
    không báo (mất tên người ký). Đo chỗ còn lại; không đủ thì sang trang mới, không cắt. Trước khi
    chịu sang trang, thử giảm nhẹ cỡ chữ — giấy nhiều người tràn vài dòng thì vẫn gọn một trang.
    """
    doc = None
    for size in _FONT_SIZES:
        doc = _pdf_at(d, size)
        if len(doc) == 1:
            break
    if len(doc) > 1:
        doc = _pdf_at(d, _FONT_SIZES[0])  # nhiều trang thì in cỡ chuẩn
    return doc.tobytes(garbage=3, deflate=True)
