"""Tờ khai bản giấy (Mẫu số 1 — Giấy đề nghị đăng ký hộ kinh doanh) ra .docx từ dữ liệu vòng hỏi đáp.

Chỉ dựng file từ dữ liệu đã có; ô không có dữ liệu in dòng chấm để công dân viết tay (không bịa). Chủ hộ ký tay ở cuối.
Bố cục bám 4 trang của mẫu giấy: trang 1 chủ hộ, trang 2 mục 1–3, trang 3 mục 4–7, trang 4 cam kết + ký.
"""
import io
from dataclasses import dataclass, field
from datetime import date

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = "Times New Roman"
_DOTS = "." * 70
_SHORT = "." * 30
_BOX_ON, _BOX_OFF = "☒", "☐"


@dataclass
class Person:
    hoTen: str = ""
    ngaySinh: str = ""      # dd/mm/yyyy
    gioiTinh: str = ""      # Nam / Nữ
    soDinhDanh: str = ""
    noiO: dict | None = None  # {tinh, xa, diaChi}


@dataclass
class ToKhai:
    ngay: date
    kinhGui: str = ""
    chuHo: Person = field(default_factory=Person)
    ten: str = ""
    tenNuocNgoai: str = ""
    tenVietTat: str = ""
    truSo: dict | None = None
    dienThoai: str = ""
    fax: str = ""
    email: str = ""
    website: str = ""
    khongKdTruSo: bool = False
    nganh: list[tuple[str, str, bool]] = field(default_factory=list)  # (tên, mã, chính)
    von: int | None = None
    thueDiaChi: dict | None = None  # chỉ khi khác địa chỉ trụ sở
    ngayBatDau: str = ""
    soLaoDong: str = ""
    hoGiaDinh: bool | None = None  # None = chưa chọn chủ thể
    thanhVien: list[Person] = field(default_factory=list)


# ── Số tiền bằng chữ ──

_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read3(n: int, full: bool) -> list[str]:
    h, t, u = n // 100, n // 10 % 10, n % 10
    out = []
    if full or h:
        out.append(f"{_DIGITS[h]} trăm")
    if t == 0:
        if u:
            if full or h:
                out.append("linh")
            out.append(_DIGITS[u])
    elif t == 1:
        out.append("mười")
        if u:
            out.append("lăm" if u == 5 else _DIGITS[u])
    else:
        out.append(f"{_DIGITS[t]} mươi")
        if u:
            out.append({1: "mốt", 5: "lăm"}.get(u, _DIGITS[u]))
    return out


def so_thanh_chu(n: int) -> str:
    """50000000 → "Năm mươi triệu đồng" (cách đọc số tiền thông dụng trên giấy tờ)."""
    n = int(n)
    if n <= 0:
        return "Không đồng"
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
    words: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        if not groups[i]:
            continue
        words += _read3(groups[i], full=bool(words))
        if units[i]:
            words.append(units[i])
    text = " ".join(words)
    return text[:1].upper() + text[1:] + " đồng"


def _money(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


# ── Dựng .docx ──

def _run(par, text: str, *, bold=False, italic=False, size=13, underline=False):
    run = par.add_run(text)
    run.bold, run.italic, run.underline = bold, italic, underline
    run.font.size = Pt(size)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return run


def _par(container, *segs, align=None, indent=0.0, size=13, after=3, before=0):
    """segs: chuỗi thường hoặc (chuỗi, "b"/"i"/"bi"/"u")."""
    par = container.add_paragraph()
    par.paragraph_format.space_after = Pt(after)
    par.paragraph_format.space_before = Pt(before)
    if indent:
        par.paragraph_format.left_indent = Cm(indent)
    if align:
        par.alignment = align
    for seg in segs:
        text, style = (seg, "") if isinstance(seg, str) else seg
        _run(par, text, bold="b" in style, italic="i" in style, underline="u" in style, size=size)
    return par


def _v(value, dots: str = _SHORT) -> str:
    value = str(value or "").strip()
    return value or dots


def _addr_lines(container, addr: dict | None, indent: float):
    addr = addr or {}
    _par(container, ("Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: ", ""),
         _v(addr.get("diaChi"), ""), indent=indent)
    if not addr.get("diaChi"):
        _par(container, _DOTS, indent=indent)
    _par(container, "Xã/Phường/Đặc khu: ", _v(addr.get("xa"), _DOTS[:45]), indent=indent)
    _par(container, "Tỉnh/Thành phố trực thuộc trung ương: ", _v(addr.get("tinh"), _DOTS[:35]), indent=indent)


def _addr_text(addr: dict | None) -> str:
    addr = addr or {}
    return ", ".join(p for p in (addr.get("diaChi"), addr.get("xa"), addr.get("tinh")) if p)


def _cell(cell, text: str, *, bold=False, italic=False, center=True, size=11):
    p = cell.paragraphs[0]
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, bold=bold, italic=italic, size=size)


def _footnotes(doc, notes: list[str]):
    _par(doc, "_" * 30, size=10, before=12, after=0)
    for note in notes:
        _par(doc, note, size=10, after=0)


def _page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def to_docx(d: ToKhai) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2)
    sec.left_margin, sec.right_margin = Cm(3), Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(13)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    C, R, J = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.JUSTIFY
    owner = d.chuHo

    # ── Trang 1: chủ hộ ──
    _par(doc, ("Mẫu số 1", "b"), align=R)
    _par(doc, ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "b"), align=C, after=0)
    _par(doc, ("Độc lập - Tự do - Hạnh phúc", "bu"), align=C, after=12)
    _par(doc, (f"ngày {d.ngay.day:02d} tháng {d.ngay.month:02d} năm {d.ngay.year}", "i"), align=R, after=12)
    _par(doc, ("GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH", "b"), align=C, size=14, after=12)
    _par(doc, "Kính gửi: ", _v(d.kinhGui, _DOTS[:50]), align=C, after=10)
    _par(doc, "Tôi là ", ("(ghi họ tên bằng chữ in hoa)", "i"), ": ", _v(owner.hoTen.upper(), _DOTS[:40]), indent=0.6)
    _par(doc, "Sinh ngày: ", _v(owner.ngaySinh, "....../....../.........."), indent=0.6)
    _par(doc, "Giới tính: ", _v(owner.gioiTinh, "............"), indent=0.6)
    _par(doc, "Số định danh cá nhân: ", _v(owner.soDinhDanh, _DOTS[:40]), indent=0.6)
    _par(doc, "Điện thoại ", ("(nếu có)", "i"), ": ", _SHORT[:20], "  Thư điện tử ", ("(nếu có)", "i"), ": ",
         _SHORT[:20], indent=0.6)
    _par(doc, ("Trường hợp việc kết nối giữa Cơ sở dữ liệu về đăng ký hộ kinh doanh với Cơ sở dữ liệu quốc gia về dân "
               "cư bị gián đoạn thì đề nghị kê khai thêm các thông tin cá nhân dưới đây:", "bi"), align=J, before=6)
    box = doc.add_table(rows=1, cols=1, style="Table Grid")
    cell = box.rows[0].cells[0]
    cell.paragraphs[0].text = ""
    _run(cell.paragraphs[0], "Dân tộc: ")
    _run(cell.paragraphs[0], "...............")
    _run(cell.paragraphs[0], "     Quốc tịch: ")
    _run(cell.paragraphs[0], "...............")
    _par(cell, "Nơi thường trú:")
    _addr_lines(cell, None, 0.6)
    _par(cell, "Nơi ở hiện tại:")
    _addr_lines(cell, owner.noiO, 0.6)

    # ── Trang 2: mục 1–3 ──
    _page_break(doc)
    _par(doc, ("Đăng ký hộ kinh doanh do tôi là chủ hộ với các nội dung sau:", "b"), align=C, after=6)
    _par(doc, ("1. Tên hộ kinh doanh:", "b"))
    _par(doc, "Tên hộ kinh doanh viết bằng tiếng Việt ", ("(ghi bằng chữ in hoa)", "i"), ":", indent=0.6)
    _par(doc, _v(d.ten.upper(), _DOTS), indent=0.6)
    _par(doc, "Tên hộ kinh doanh viết bằng tiếng nước ngoài ", ("(nếu có)", "i"), ":", indent=0.6)
    _par(doc, _v(d.tenNuocNgoai, _DOTS), indent=0.6)
    _par(doc, "Tên hộ kinh doanh viết tắt ", ("(nếu có)", "i"), ": ", _v(d.tenVietTat, _DOTS[:40]), indent=0.6)
    _par(doc, ("2. Trụ sở của hộ kinh doanh:", "b"), before=4)
    _addr_lines(doc, d.truSo, 0.6)
    _par(doc, "Điện thoại: ", _v(d.dienThoai), "  Fax ", ("(nếu có)", "i"), ": ", _v(d.fax, _SHORT[:20]), indent=0.6)
    _par(doc, "Thư điện tử ", ("(nếu có)", "i"), ": ", _v(d.email, _SHORT[:25]), "  Website ", ("(nếu có)", "i"),
         ": ", _v(d.website, _SHORT[:20]), indent=0.6)
    _par(doc, _BOX_ON if d.khongKdTruSo else _BOX_OFF, " Không kinh doanh tại trụ sở ",
         ("(đánh dấu X vào ô này nếu hộ kinh doanh không có địa điểm kinh doanh cố định)", "i"), indent=0.6, align=J)
    _par(doc, ("3. Ngành, nghề kinh doanh¹:", "b"), before=4)
    rows = max(5, len(d.nganh))
    table = doc.add_table(rows=rows + 1, cols=4, style="Table Grid")
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, head in zip(table.rows[0].cells, ("STT", "Tên ngành", "Mã ngành²", "Ngành, nghề kinh doanh chính³")):
        _cell(c, head, bold=True)
    for i, (ten, ma, chinh) in enumerate(d.nganh, 1):
        cells = table.rows[i].cells
        _cell(cells[0], str(i))
        _cell(cells[1], ten, center=False)
        _cell(cells[2], ma)
        _cell(cells[3], "X" if chinh else "")
    for row, width in zip(table.columns, (Cm(1.3), Cm(9), Cm(2.4), Cm(3.3))):
        for c in row.cells:
            c.width = width
    _footnotes(doc, [
        "¹ - Hộ kinh doanh có quyền tự do kinh doanh trong những ngành, nghề mà luật không cấm;",
        "- Các ngành, nghề cấm đầu tư kinh doanh quy định tại Điều 6 Luật Đầu tư;",
        "- Đối với những ngành, nghề đầu tư kinh doanh có điều kiện được quy định tại các văn bản quy phạm pháp luật "
        "khác, ngành, nghề kinh doanh được ghi theo ngành, nghề quy định tại các văn bản quy phạm pháp luật đó. Hộ kinh "
        "doanh chỉ được kinh doanh khi có đủ điều kiện theo quy định.",
        "² Ghi tên ngành và mã ngành cấp bốn trong Hệ thống ngành kinh tế Việt Nam đối với ngành, nghề kinh doanh chính. "
        "Đối với các ngành, nghề kinh doanh khác, hộ kinh doanh được ghi tự do và không cần ghi mã ngành cấp bốn.",
        "³ Đánh dấu X để chọn một trong các ngành, nghề đã kê khai làm ngành, nghề kinh doanh chính.",
    ])

    # ── Trang 3: mục 4–7 ──
    _page_break(doc)
    _par(doc, ("4. Vốn kinh doanh:", "b"))
    von = f"{_money(d.von)} ({so_thanh_chu(d.von)})" if d.von else _DOTS[:45]
    _par(doc, "Tổng số ", ("(bằng số, bằng chữ, VNĐ)", "i"), ": ", von, indent=0.6)
    _par(doc, ("5. Thông tin đăng ký thuế:", "b"), before=4)
    _par(doc, "5.1. Địa chỉ nhận thông báo thuế ",
         ("(chỉ kê khai nếu địa chỉ nhận thông báo thuế khác địa chỉ trụ sở)", "i"), ":", indent=0.6, align=J)
    _addr_lines(doc, d.thueDiaChi, 1.0)
    _par(doc, "Điện thoại ", ("(nếu có)", "i"), ": ", _SHORT[:20], "  Thư điện tử ", ("(nếu có)", "i"), ": ",
         _SHORT[:20], indent=1.0)
    _par(doc, "5.2. Ngày bắt đầu hoạt động⁴ ",
         ("(trường hợp hộ kinh doanh dự kiến bắt đầu hoạt động kể từ ngày được cấp Giấy chứng nhận đăng ký hộ kinh "
          "doanh thì không cần kê khai nội dung này)", "i"), ": ", _v(d.ngayBatDau, "....../....../.........."),
         indent=0.6, align=J)
    _par(doc, "5.3. Tổng số lao động ", ("(dự kiến)", "i"), ": ", _v(d.soLaoDong, _DOTS[:40]), indent=0.6)
    _par(doc, "5.4. Phương pháp tính thuế GTGT ", ("(chọn 1 trong 2 phương pháp)", "i"), ":", indent=0.6)
    _par(doc, f"{_BOX_ON} Phương pháp kê khai          {_BOX_OFF} Phương pháp khoán", indent=1.4)
    _par(doc, ("6. Chủ thể thành lập hộ kinh doanh: ", "b"), ("(đánh dấu X vào ô thích hợp)", "i"), before=4)
    personal = _BOX_ON if d.hoGiaDinh is False else _BOX_OFF
    family = _BOX_ON if d.hoGiaDinh is True else _BOX_OFF
    _par(doc, f"{personal} Cá nhân          {family} Các thành viên hộ gia đình", indent=1.4)
    _par(doc, ("7. Thông tin về các thành viên hộ gia đình đăng ký hộ kinh doanh⁵:", "b"), before=4)
    heads = ("STT", "Họ tên", "Ngày, tháng, năm sinh", "Số định danh cá nhân", "Giới tính", "Quốc tịch", "Dân tộc",
             "Nơi thường trú", "Nơi ở hiện tại", "Chữ ký")
    people = ([owner, *d.thanhVien] if d.hoGiaDinh else [])
    table = doc.add_table(rows=max(5, len(people)) + 2, cols=10, style="Table Grid")
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (c, head) in enumerate(zip(table.rows[0].cells, heads)):
        _cell(c, head, bold=True, size=9)
        _cell(table.rows[1].cells[i], str(i + 1), bold=True, size=9)
    for i, p in enumerate(people, 1):
        cells = table.rows[i + 1].cells
        for c, text in zip(cells, (str(i), p.hoTen, p.ngaySinh, p.soDinhDanh, p.gioiTinh, "", "", "",
                                   _addr_text(p.noiO), "")):
            _cell(c, text, size=9)
    _footnotes(doc, [
        "⁴ Trường hợp hộ kinh doanh được cấp Giấy chứng nhận đăng ký hộ kinh doanh sau ngày bắt đầu hoạt động đã kê "
        "khai thì ngày bắt đầu hoạt động là ngày hộ kinh doanh được cấp Giấy chứng nhận đăng ký hộ kinh doanh.",
        "⁵ - Chỉ kê khai trong trường hợp hộ chủ thể thành lập hộ kinh doanh là các thành viên hộ gia đình và kê khai "
        "cả thông tin của chủ hộ tại Bảng này;",
        "- Trường hợp chủ hộ kinh doanh và các thành viên hộ gia đình đăng ký hộ kinh doanh kê khai số định danh cá nhân "
        "thì chỉ kê khai các cột số 1, 2, 3, 4, 5, 10, không phải kê khai các cột số 6, 7, 8, 9 của Bảng này, trừ "
        "trường hợp việc kết nối giữa Cơ sở dữ liệu về đăng ký hộ kinh doanh với Cơ sở dữ liệu quốc gia về dân cư bị "
        "gián đoạn.",
    ])

    # ── Trang 4: cam kết + ký ──
    _page_break(doc)
    _par(doc, "Tôi xin cam kết:", indent=0.6)
    _par(doc, "- Bản thân ", ("(trường hợp hộ kinh doanh do một cá nhân đăng ký thành lập)", "i"),
         "/Bản thân và các thành viên hộ gia đình đăng ký hộ kinh doanh ",
         ("(trường hợp hộ kinh doanh do các thành viên hộ gia đình đăng ký thành lập)", "i"),
         " đồng ý chia sẻ thông tin cá nhân được lưu giữ tại Cơ sở dữ liệu quốc gia về dân cư cho Cơ quan đăng ký kinh "
         "doanh cấp xã, Cơ quan quản lý nhà nước về đăng ký kinh doanh để phục vụ công tác quản lý nhà nước về đăng ký "
         "hộ kinh doanh theo quy định;", indent=0.6, align=J)
    _par(doc, "- Bản thân ", ("(trường hợp hộ kinh doanh do một cá nhân đăng ký thành lập)", "i"),
         "/Bản thân và các thành viên hộ gia đình đăng ký hộ kinh doanh ",
         ("(trường hợp hộ kinh doanh do các thành viên hộ gia đình đăng ký thành lập)", "i"),
         " không thuộc diện pháp luật cấm kinh doanh; không đồng thời là chủ hộ kinh doanh, thành viên hộ gia đình đăng "
         "ký hộ kinh doanh khác; không là chủ doanh nghiệp tư nhân;", indent=0.6, align=J)
    _par(doc, "- Trụ sở thuộc quyền sử dụng hợp pháp của hộ kinh doanh và được sử dụng đúng mục đích theo quy định của "
              "pháp luật (", ("hộ kinh doanh chỉ cam kết trong trường hợp kinh doanh tại trụ sở", "i"), ");",
         indent=0.6, align=J)
    _par(doc, "- Hoàn toàn chịu trách nhiệm trước pháp luật về tính hợp pháp, chính xác và trung thực của nội dung "
              "đăng ký trên.", indent=0.6, align=J)
    sign = doc.add_table(rows=1, cols=2)
    right = sign.rows[0].cells[1]
    _cell(right, "CHỦ HỘ KINH DOANH", bold=True, size=13)
    p = right.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, "(Ký và ghi họ tên)⁶", italic=True)
    for _ in range(5):
        right.add_paragraph()  # chỗ chủ hộ ký và ghi họ tên
    _footnotes(doc, ["⁶ Chủ hộ kinh doanh ký trực tiếp vào phần này."])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
