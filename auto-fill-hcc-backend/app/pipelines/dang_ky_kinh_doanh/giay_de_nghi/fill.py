"""Điền dữ liệu vào file Word CHÍNH THỨC của Mẫu số 1 (không dựng lại mẫu).

Điền thẳng vào file gốc để giữ nguyên câu chữ, sáu chú thích chân trang, ô đánh dấu và định dạng. Ô để
trống thì giữ nguyên dòng chấm cho viết tay, nên gửi rỗng ra đúng mẫu trắng. Chỉ thêm giá trị và dọn hai
chỗ không đổi chữ: section Letter thừa ở cuối (sinh trang trắng thứ 4) và thông tin tác giả của file gốc.
"""
import copy
import io
import re
import unicodedata
from pathlib import Path
from typing import Literal

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.table import _Cell
from docx.text.paragraph import Paragraph
from pydantic import BaseModel, Field

MAU = Path(__file__).with_name("mau_so_1_phu_luc_ii.docx")
_W_URI = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_NGAY = r"^(\d{2}/\d{2}/\d{4})?$"  # form gửi đúng dd/mm/yyyy hoặc rỗng; rỗng thì giữ dòng chấm
_SO_NGANH_TOI_DA = 50
_SO_THANH_VIEN_TOI_DA = 20
_TITLE = "Giấy đề nghị đăng ký hộ kinh doanh"


class DiaChi(BaseModel):
    chiTiet: str = Field(default="", max_length=300)
    xa: str = Field(default="", max_length=120)
    tinh: str = Field(default="", max_length=120)


class NganhNghe(BaseModel):
    ten: str = Field(default="", max_length=300)
    ma: str = Field(default="", max_length=10)
    chinh: bool = False


class ThanhVien(BaseModel):
    hoTen: str = Field(default="", max_length=120)
    ngaySinh: str = Field(default="", pattern=_NGAY)
    soDinhDanh: str = Field(default="", max_length=20)
    gioiTinh: str = Field(default="", max_length=10)
    quocTich: str = Field(default="", max_length=60)
    danToc: str = Field(default="", max_length=60)
    noiThuongTru: str = Field(default="", max_length=300)
    noiOHienTai: str = Field(default="", max_length=300)


class GiayDeNghi(BaseModel):
    diaDanh: str = Field(default="", max_length=120)
    ngayLap: str = Field(default="", pattern=_NGAY)
    kinhGui: str = Field(default="", max_length=200)
    # Chủ hộ
    hoTen: str = Field(default="", max_length=120)
    ngaySinh: str = Field(default="", pattern=_NGAY)
    gioiTinh: str = Field(default="", max_length=10)
    soDinhDanh: str = Field(default="", max_length=20)
    dienThoai: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)
    # Khối kê khai thêm khi kết nối Cơ sở dữ liệu quốc gia về dân cư bị gián đoạn
    danToc: str = Field(default="", max_length=60)
    quocTich: str = Field(default="", max_length=60)
    thuongTru: DiaChi = Field(default_factory=DiaChi)
    noiO: DiaChi = Field(default_factory=DiaChi)
    # 1. Tên hộ kinh doanh
    tenViet: str = Field(default="", max_length=200)
    tenNuocNgoai: str = Field(default="", max_length=200)
    tenVietTat: str = Field(default="", max_length=120)
    # 2. Trụ sở
    truSo: DiaChi = Field(default_factory=DiaChi)
    truSoDienThoai: str = Field(default="", max_length=30)
    truSoFax: str = Field(default="", max_length=30)
    truSoEmail: str = Field(default="", max_length=120)
    truSoWebsite: str = Field(default="", max_length=120)
    khongKinhDoanhTaiTruSo: bool = False
    # 3, 4
    nganh: list[NganhNghe] = Field(default_factory=list, max_length=_SO_NGANH_TOI_DA)
    vonKinhDoanh: str = Field(default="", max_length=300)
    # 5. Thông tin đăng ký thuế
    thueDiaChi: DiaChi = Field(default_factory=DiaChi)
    thueDienThoai: str = Field(default="", max_length=30)
    thueEmail: str = Field(default="", max_length=120)
    ngayBatDau: str = Field(default="", pattern=_NGAY)
    soLaoDong: str = Field(default="", max_length=20)
    phuongPhapThue: Literal["", "ke_khai", "khoan"] = ""
    # 6, 7
    chuThe: Literal["", "ca_nhan", "ho_gia_dinh"] = ""
    thanhVien: list[ThanhVien] = Field(default_factory=list, max_length=_SO_THANH_VIEN_TOI_DA)


def _clean(value) -> str:
    """Bỏ ký tự điều khiển (XML không nhận, chữ dán từ nơi khác hay dính) và dựng lại chữ NFC cho font."""
    text = unicodedata.normalize("NFC", str(value or ""))
    text = "".join(" " if unicodedata.category(ch)[0] == "C" else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


# ── Điền vào đoạn ──

# Nhóm chấm trong mẫu ("……", "….............", "…../…../"); số mục "5.1." chỉ có chấm đơn nên không khớp.
_DOTS = re.compile(r"[.…]{2,}")
_T, _TAB, _R, _P = qn("w:t"), qn("w:tab"), qn("w:r"), qn("w:p")
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _text_nodes(p):
    return [node for run in p.findall(_R) for node in run.findall(_T)]


def _tabs(p):
    return [tab for run in p.findall(_R) for tab in run.findall(_TAB)]


def _fill_dots(p, *values: str):
    """Thay lần lượt từng nhóm chấm; giá trị rỗng giữ nguyên chấm của nhóm đó."""
    pending = iter(values)
    filled = False

    def swap(match):
        nonlocal filled
        value = next(pending, "")
        filled = filled or bool(value)
        return value or match.group(0)

    for node in _text_nodes(p):
        node.text = _DOTS.sub(swap, node.text or "")
    if filled:  # tab đuôi của dòng trong khung kê khai thêm: có chữ rồi thì bỏ, chữ dài khỏi rớt thêm dòng trắng
        for tab in _tabs(p):
            if _is_last(tab):
                tab.getparent().remove(tab)


def _is_last(tab) -> bool:
    run = tab.getparent()
    after = list(run)[list(run).index(tab) + 1:]
    p = run.getparent()
    after += [child for r in list(p)[list(p).index(run) + 1:] if r.tag == _R for child in r]
    return not any(el.tag in (_T, _TAB) for el in after)


def _fill_tabs(p, *values: str, drop_all: bool = False):
    """Ghi giá trị vào trước từng tab chấm của đoạn, theo thứ tự.

    Tab cuối đoạn có chữ rồi thì bỏ. Tab giữa đoạn giữ lại để cột sau không xê dịch (vd "Fax" vẫn nằm đúng
    chỗ) nhưng bỏ hàng chấm, chấm chỉ để viết tay. `drop_all` dùng cho ngày dạng "tab/tab/tab", nơi tab chỉ là
    khoảng để viết tay.
    """
    for i, (tab, value) in enumerate(zip(_tabs(p), values)):
        if not value:
            continue
        node = parse_xml(f'<w:t xmlns:w="{_W_URI}" xml:space="preserve"/>')
        node.text = value
        tab.addprevious(node)
        if drop_all or _is_last(tab):
            tab.getparent().remove(tab)
        else:
            p.pPr.find(qn("w:tabs")).findall(qn("w:tab"))[i].attrib.pop(qn("w:leader"), None)


class _Mau:
    """Đi xuôi thân văn bản và lấy đoạn theo chữ mở đầu: "Số nhà/phòng…" lặp ba lần nên không tra theo tên."""

    def __init__(self, doc):
        self.paras, self.at = doc.paragraphs, 0

    def next(self, start: str):
        for i in range(self.at, len(self.paras)):
            if self.paras[i].text.strip().startswith(start):
                self.at = i + 1
                return self.paras[i]._p
        raise ValueError(f"Mẫu không còn đoạn mở đầu bằng: {start}")


def _ngay(value: str) -> tuple[str, str, str]:
    parts = (value or "").split("/")
    return (parts[0], parts[1], parts[2]) if len(parts) == 3 else ("", "", "")


# ── Ô đánh dấu: hình vuông vẽ nổi trong mẫu, đánh dấu bằng chữ X nằm trong chính hình đó ──

_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_V = "urn:schemas-microsoft-com:vml"
_MARK = (f'<w:txbxContent xmlns:w="{_W_URI}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/>'
         '<w:sz w:val="26"/></w:rPr><w:t>X</w:t></w:r></w:p></w:txbxContent>')


def _boxes(scope) -> list:
    """Các ô vuông trong một phần tử, trái sang phải; kèm hình VML dự phòng cùng lượt để hai bản khớp nhau."""
    found = []
    for anchor in scope.iter(f"{{{_WP}}}anchor"):
        offset = int(anchor.find(f"{{{_WP}}}positionH").find(f"{{{_WP}}}posOffset").text)
        found.append((offset, anchor))
    return [anchor for _, anchor in sorted(found, key=lambda item: item[0])]


def _tick(anchor):
    shape = next(anchor.iter(f"{{{_WPS}}}wsp"))
    body = shape.find(f"{{{_WPS}}}bodyPr")
    box = parse_xml(f'<wps:txbx xmlns:wps="{_WPS}">{_MARK}</wps:txbx>')
    body.addprevious(box)
    for inset in ("lIns", "tIns", "rIns", "bIns"):
        body.set(inset, "0")
    body.set("anchor", "ctr")
    # Bản VML dự phòng (mc:Fallback) cho trình đọc không hiểu wps: thiếu thì chỗ đó hiện ô trống.
    fallback = next(el for el in anchor.iterancestors() if el.tag.endswith("}AlternateContent"))
    for rect in fallback.iter(f"{{{_V}}}rect"):
        rect.append(parse_xml(f'<v:textbox xmlns:v="{_V}" inset="0,0,0,0">{_MARK}</v:textbox>'))


# ── Bảng ──

def _cell(cell: _Cell, text: str, *, size: float, align=WD_ALIGN_PARAGRAPH.LEFT, bold: bool = False):
    para = cell.paragraphs[0]
    ppr = para._p.get_or_add_pPr()
    for tag in ("w:ind", "w:tabs"):  # dòng trống của mẫu thụt đầu dòng: chữ trong ô sẽ lệch khỏi tâm
        for el in ppr.findall(qn(tag)):
            ppr.remove(el)
    para.alignment = align
    run = para.add_run(text)
    run.font.size, run.bold = Pt(size), bold


def _no_split(row):
    trpr = row._tr.get_or_add_trPr()
    if trpr.find(qn("w:cantSplit")) is None:
        trpr.append(parse_xml(f'<w:cantSplit xmlns:w="{_W_URI}"/>'))


def _repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    if trpr.find(qn("w:tblHeader")) is None:
        trpr.append(parse_xml(f'<w:tblHeader xmlns:w="{_W_URI}"/>'))


def _grow(table, first_blank: int, count: int):
    """Bảng mẫu chỉ có sẵn vài dòng trắng: chép dòng trắng đầu cho đủ `count` dòng."""
    blank = table.rows[first_blank]._tr
    have = len(table.rows) - first_blank
    for _ in range(count - have):
        blank.addnext(copy.deepcopy(blank))


def _fill_nganh(table, rows: list[NganhNghe]):
    _repeat_header(table.rows[0])
    filled = [(_clean(r.ten), _clean(r.ma), r.chinh) for r in rows]
    filled = [r for r in filled if r[0] or r[1]]
    _grow(table, 1, len(filled))
    for i, (ten, ma, chinh) in enumerate(filled, 1):
        row = table.rows[i]
        _cell(row.cells[0], str(i), size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell(row.cells[1], ten, size=14)
        _cell(row.cells[2], ma, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell(row.cells[3], "X" if chinh else "", size=14, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    for row in table.rows:
        _no_split(row)


# Bề rộng cột của mẫu dành cho viết tay: 12 số định danh hay họ "NGUYỄN" cỡ 10 không vừa ô, Word phải bẻ giữa
# chữ. Chỉ chia lại khi có dữ liệu; tổng vẫn đúng bề rộng bảng của mẫu (9096).
_THANH_VIEN_COT = (540, 1190, 1100, 1320, 560, 700, 620, 1130, 1130, 806)
_THANH_VIEN_LE = 40  # lề trái/phải của ô, twip
_THANH_VIEN_CO_CHU = 10


def _fit_columns(table):
    tbl = table._tbl
    for grid, width in zip(tbl.tblGrid.findall(qn("w:gridCol")), _THANH_VIEN_COT):
        grid.set(qn("w:w"), str(width))
    for row in table.rows:
        for tc, width in zip(row._tr.findall(qn("w:tc")), _THANH_VIEN_COT):
            tcpr = tc.get_or_add_tcPr()
            tcpr.find(qn("w:tcW")).set(qn("w:w"), str(width))
            margin = parse_xml(f'<w:tcMar xmlns:w="{_W_URI}"><w:left w:w="{_THANH_VIEN_LE}" w:type="dxa"/>'
                               f'<w:right w:w="{_THANH_VIEN_LE}" w:type="dxa"/></w:tcMar>')
            # Word đòi đúng thứ tự con của tcPr (tcMar đứng trước vAlign), sai là báo file hỏng.
            after = tcpr.find(qn("w:vAlign"))
            if after is not None:
                after.addprevious(margin)
            else:
                tcpr.append(margin)


def _fill_thanh_vien(table, people: list[ThanhVien]):
    for row in table.rows[:2]:
        _repeat_header(row)
    rows = [[_clean(v) for v in (p.hoTen, p.ngaySinh, p.soDinhDanh, p.gioiTinh, p.quocTich, p.danToc,
                                 p.noiThuongTru, p.noiOHienTai)] for p in people]
    rows = [r for r in rows if any(r)]
    if rows:
        _grow(table, 2, len(rows))
        _fit_columns(table)
    for i, values in enumerate(rows):
        cells = table.rows[i + 2].cells
        _cell(cells[0], str(i + 1), size=_THANH_VIEN_CO_CHU, align=WD_ALIGN_PARAGRAPH.CENTER)
        for cell, value in zip(cells[1:9], values):
            _cell(cell, value, size=_THANH_VIEN_CO_CHU)
    for row in table.rows:
        _no_split(row)


# ── Chữ ký + dọn đuôi file ──

_CHO_KY = 62  # pt để ký tươi; mẫu gốc không chừa khoảng nào giữa "(Ký và ghi họ tên)" và chú thích


def _fill_chu_ky(table, ho_ten: str):
    _no_split(table.rows[0])
    cell = table.rows[0].cells[2]
    para = cell.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(_CHO_KY)
    run = para.add_run(ho_ten)
    run.font.size, run.bold = Pt(14), True


def _drop_letter_section(doc):
    """Đoạn cuối của mẫu nằm ở một section khổ Letter riêng nên Word luôn in thêm trang 4 trắng."""
    body = doc.element.body
    holder = next(p for p in body.findall(_P) if p.pPr is not None and p.pPr.find(qn("w:sectPr")) is not None)
    inner = holder.pPr.find(qn("w:sectPr"))
    holder.pPr.remove(inner)
    for extra in list(holder.itersiblings(_P)):
        body.remove(extra)
    body.replace(body.find(qn("w:sectPr")), inner)
    # Đoạn bắt buộc sau bảng chữ ký: thu thật nhỏ để không tự đẩy thành một trang mới.
    holder.replace(holder.pPr, parse_xml(
        f'<w:pPr xmlns:w="{_W_URI}"><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
        '<w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr>'))


# Tiêu đề không nằm lại cuối trang; đoạn 5.4 phải đi cùng bảng vì ô "Phương pháp khoán" neo vào đoạn này; câu
# cam kết cuối đi cùng chữ ký để chữ ký không đứng một mình trên trang mới.
_GIU_VOI_DOAN_SAU = ("1. Tên hộ kinh doanh", "2. Trụ sở", "3. Ngành, nghề", "4. Vốn kinh doanh",
                     "5. Thông tin đăng ký thuế", "5.1.", "5.4.", "6. Chủ thể", "7. Thông tin về",
                     "Tôi xin cam kết", "- Hoàn toàn chịu trách nhiệm")


def _keep_titles(doc):
    mau = _Mau(doc)
    for start in _GIU_VOI_DOAN_SAU:
        Paragraph(mau.next(start), None).paragraph_format.keep_with_next = True


def fill(d: GiayDeNghi):
    """Trả Document đã điền; to_docx lưu nó, bản PDF đọc chính nó."""
    doc = Document(str(MAU))
    mau = _Mau(doc)
    tables = doc.tables  # 0 khung kê khai thêm · 1 ngành · 2 phương pháp thuế · 3 chủ thể · 4 thành viên · 5 ký

    day, month, year = _ngay(d.ngayLap)
    _fill_dots(mau.next("……, ngày"), _clean(d.diaDanh), f"{day} " if day else "", month, year)
    _fill_dots(mau.next("Kính gửi"), _clean(d.kinhGui))

    _fill_tabs(mau.next("Tôi là"), _clean(d.hoTen).upper())
    _fill_tabs(mau.next("Sinh ngày"), *_ngay(d.ngaySinh), drop_all=True)
    _fill_tabs(mau.next("Giới tính"), _clean(d.gioiTinh))
    _fill_dots(mau.next("Số định danh cá nhân"), _clean(d.soDinhDanh))
    _fill_dots(mau.next("Điện thoại"), _clean(d.dienThoai), _clean(d.email))

    extra = [p._p for p in tables[0].rows[0].cells[0].paragraphs]
    _fill_dots(extra[0], _clean(d.danToc), _clean(d.quocTich))
    for lines, address in ((extra[2:5], d.thuongTru), (extra[6:9], d.noiO)):
        for p, value in zip(lines, (address.chiTiet, address.xa, address.tinh)):
            _fill_dots(p, _clean(value))

    _fill_tabs(mau.next("Tên hộ kinh doanh viết bằng tiếng Việt"), _clean(d.tenViet).upper())
    _fill_tabs(mau.next("Tên hộ kinh doanh viết bằng tiếng nước ngoài"), _clean(d.tenNuocNgoai))
    _fill_tabs(mau.next("Tên hộ kinh doanh viết tắt"), _clean(d.tenVietTat))

    _fill_tabs(mau.next("Số nhà/phòng"), _clean(d.truSo.chiTiet))
    _fill_tabs(mau.next("Xã/Phường/Đặc khu"), _clean(d.truSo.xa))
    _fill_tabs(mau.next("Tỉnh/Thành phố"), _clean(d.truSo.tinh))
    phone = _clean(d.truSoDienThoai)  # mẫu viết "Điện thoại:" liền tab, không có dấu cách
    _fill_tabs(mau.next("Điện thoại:"), f" {phone}" if phone else "", _clean(d.truSoFax))
    _fill_tabs(mau.next("Thư điện tử"), _clean(d.truSoEmail), _clean(d.truSoWebsite))
    khong_tai_tru_so = mau.next("Không kinh doanh tại trụ sở")
    if d.khongKinhDoanhTaiTruSo:
        _tick(_boxes(khong_tai_tru_so)[0])

    _fill_nganh(tables[1], d.nganh)
    _fill_tabs(mau.next("Tổng số"), _clean(d.vonKinhDoanh))

    _fill_tabs(mau.next("Số nhà/phòng"), _clean(d.thueDiaChi.chiTiet))
    _fill_tabs(mau.next("Xã/Phường/Đặc khu"), _clean(d.thueDiaChi.xa))
    _fill_tabs(mau.next("Tỉnh/Thành phố"), _clean(d.thueDiaChi.tinh))
    _fill_tabs(mau.next("Điện thoại"), _clean(d.thueDienThoai), _clean(d.thueEmail))
    _fill_dots(mau.next("5.2."), *_ngay(d.ngayBatDau))
    _fill_tabs(mau.next("5.3."), _clean(d.soLaoDong))

    # Ô "Phương pháp khoán" neo vào đoạn 5.4 chứ không nằm trong bảng; ô "kê khai" nằm trong ô bảng.
    phuong_phap = mau.next("5.4.")
    if d.phuongPhapThue == "khoan":
        _tick(_boxes(phuong_phap)[0])
    elif d.phuongPhapThue == "ke_khai":
        _tick(_boxes(tables[2].rows[0].cells[0]._tc)[0])

    boxes = _boxes(tables[3].rows[0].cells[0]._tc)  # trái sang phải: Cá nhân, Các thành viên hộ gia đình
    if d.chuThe == "ca_nhan":
        _tick(boxes[0])
    elif d.chuThe == "ho_gia_dinh":
        _tick(boxes[1])

    # Bảng 7 chỉ kê khai khi chủ thể là các thành viên hộ gia đình (chú thích 5 của mẫu).
    _fill_thanh_vien(tables[4], d.thanhVien if d.chuThe == "ho_gia_dinh" else [])
    _fill_chu_ky(tables[5], _clean(d.hoTen).upper())

    _keep_titles(doc)
    _drop_letter_section(doc)
    props = doc.core_properties
    props.author = props.last_modified_by = ""
    props.title = _TITLE
    return doc


def to_docx(d: GiayDeNghi) -> bytes:
    buf = io.BytesIO()
    fill(d).save(buf)
    return buf.getvalue()
