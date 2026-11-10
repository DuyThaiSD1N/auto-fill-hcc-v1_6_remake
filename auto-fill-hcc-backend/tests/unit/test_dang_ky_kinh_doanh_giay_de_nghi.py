"""Tờ khai đăng ký hộ kinh doanh cho cán bộ Auto Fill tải về, tự điền và in.

Mọi họ tên, số định danh, địa chỉ trong file này đều bịa.
"""
import hashlib
import io
import re
import unicodedata
import zipfile

import docx
import fitz
import pytest
from docx.oxml.ns import qn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lxml import etree

from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi import fill as fl
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi import pdf as pd
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi import router as rt
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.fill import GiayDeNghi, to_docx
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.pdf import to_pdf

USER = {"id": "u1", "username": "hcctest", "tinh": "Tỉnh Bắc Ninh", "xa": "Phường Vũ Ninh"}
DIA_CHI_NHA = {"chiTiet": "Số 12, ngõ 3, đường Lê Lợi", "xa": "Phường Vũ Ninh", "tinh": "Tỉnh Bắc Ninh"}
DIA_CHI_O = {"chiTiet": "Số 45, đường Trần Phú", "xa": "Phường Kinh Bắc", "tinh": "Tỉnh Bắc Giang"}
DIA_CHI_SO = {"chiTiet": "Số 7, phố Chợ", "xa": "Phường Đồng Nguyên", "tinh": "Tỉnh Thái Bình"}
DIA_CHI_THUE = {"chiTiet": "Số 9, đường Hoa Sữa", "xa": "Xã Tam Đa", "tinh": "Tỉnh Nam Định"}


def _full(**over) -> GiayDeNghi:
    data = dict(
        diaDanh="Vũ Ninh", ngayLap="08/11/2026", kinhGui="UBND phường Vũ Ninh",
        hoTen="Trần Thị Hoa", ngaySinh="05/09/1985", gioiTinh="Nữ", soDinhDanh="027185001234",
        dienThoai="0912345678", email="hoa@example.vn", danToc="Kinh", quocTich="Việt Nam",
        thuongTru=DIA_CHI_NHA, noiO=DIA_CHI_O,
        tenViet="Hộ kinh doanh Hoa Mai", tenNuocNgoai="HOA MAI GROCERY", tenVietTat="HOA MAI",
        truSo=DIA_CHI_SO, truSoDienThoai="0222123456", truSoFax="0222654321",
        truSoEmail="so@example.vn", truSoWebsite="hoamai.example.vn",
        nganh=[{"ten": "Bán lẻ lương thực trong các cửa hàng chuyên doanh", "ma": "4721", "chinh": True},
               {"ten": "Dịch vụ ăn uống khác", "ma": ""}],
        vonKinhDoanh="150.000.000 đồng (Một trăm năm mươi triệu đồng)",
        thueDiaChi=DIA_CHI_THUE, thueDienThoai="0987654321", thueEmail="thue@example.vn",
        ngayBatDau="15/11/2026", soLaoDong="3", phuongPhapThue="ke_khai", chuThe="ca_nhan",
    )
    data.update(over)
    return GiayDeNghi(**data)


def _member(i: int = 1, **over) -> dict:
    data = {"hoTen": f"TRƯƠNG VĂN BÌNH {i}", "ngaySinh": "12/01/1982", "soDinhDanh": f"02708200{i:04d}",
            "gioiTinh": "Nam", "quocTich": "Việt Nam", "danToc": "Kinh",
            "noiThuongTru": "Số 12, ngõ 3", "noiOHienTai": "Số 45, đường Trần Phú"}
    data.update(over)
    return data


def _doc(form: GiayDeNghi):
    return docx.Document(io.BytesIO(to_docx(form)))


def _pdf(form: GiayDeNghi):
    return fitz.open(stream=to_pdf(form), filetype="pdf")


def _paras(doc) -> list[str]:
    return [p.text for p in doc.paragraphs]


def _line(doc, start: str, nth: int = 0) -> str:
    hits = [t.strip() for t in _paras(doc) if t.strip().startswith(start)]
    return hits[nth]


def _squash(text: str) -> str:
    """Bỏ khoảng trắng + chấm: PDF ngắt dòng và tab chấm khác Word nhưng chữ phải y hệt.

    Times New Roman dùng chung một hình chữ cho "-" và gạch mềm nên lớp chữ của PDF trả gạch mềm; trên giấy in vẫn
    là dấu gạch.
    """
    return re.sub(r"[\s.…]+", "", unicodedata.normalize("NFC", text).replace("\xad", "-"))


def _pdf_text(document) -> str:
    return _squash("".join(page.get_text() for page in document))


def _with_note_marks(p) -> str:
    """Chữ của đoạn kèm số chú thích: bản in có số mũ, `Paragraph.text` thì không."""
    out = []
    for run in p.findall(qn("w:r")):
        for node in run:
            if node.tag == qn("w:t"):
                out.append(node.text or "")
            elif node.tag == qn("w:footnoteReference"):
                out.append(node.get(qn("w:id")))
    return "".join(out)


def _all_lines(doc) -> list[str]:
    paragraphs = [p._p for p in doc.paragraphs]
    paragraphs += [p._p for t in doc.tables for r in t.rows for c in r.cells for p in c.paragraphs]
    return [_with_note_marks(p) for p in paragraphs]


def _note_texts(path) -> dict[int, str]:
    xml = zipfile.ZipFile(path).read("word/footnotes.xml")
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    return {int(n.get(w + "id")): "".join(t.text or "" for t in n.iter(w + "t"))
            for n in etree.fromstring(xml).findall(w + "footnote") if int(n.get(w + "id")) > 0}


# ── File mẫu: đúng nguyên bản chính thức, điền trống ra đúng mẫu ──

def test_file_mau_la_nguyen_ban_tai_tu_cong_dang_ky_kinh_doanh():
    assert hashlib.sha256(fl.MAU.read_bytes()).hexdigest() == (
        "f4051f8cb313f0ab9569e55d975e04c4cc55387a8c6d4ad9a5bccaca2c22f329")


def test_gui_rong_ra_dung_cau_chu_cua_mau():
    goc = docx.Document(str(fl.MAU))
    ra = _doc(GiayDeNghi())
    assert [t for t in _paras(ra) if t.strip()] == [t for t in _paras(goc) if t.strip()]
    for bang_ra, bang_goc in zip(ra.tables[:5], goc.tables[:5]):
        assert [[c.text for c in r.cells] for r in bang_ra.rows] == [[c.text for c in r.cells] for r in bang_goc.rows]


def test_giu_nguyen_sau_chu_thich_chan_trang():
    ra = zipfile.ZipFile(io.BytesIO(to_docx(_full())))
    assert ra.read("word/footnotes.xml") == zipfile.ZipFile(fl.MAU).read("word/footnotes.xml")
    assert len(_note_texts(fl.MAU)) == 6


def test_bo_section_letter_sinh_trang_trang_thu_tu():
    goc = docx.Document(str(fl.MAU))
    assert len(goc.sections) == 2 and goc.sections[-1].page_width.twips == 12240  # khổ Letter thừa của file gốc
    ra = _doc(GiayDeNghi())
    assert len(ra.sections) == 1
    assert (ra.sections[0].page_width.twips, ra.sections[0].page_height.twips) == (11909, 16834)  # A4
    assert ra.sections[0].different_first_page_header_footer  # trang đầu vẫn không đánh số


def test_khong_mang_ten_nguoi_soan_cua_file_goc():
    props = _doc(_full()).core_properties
    assert (props.author, props.last_modified_by) == ("", "")
    assert props.title == "Giấy đề nghị đăng ký hộ kinh doanh"


def test_nhan_mau_khop_danh_so_trong_word():
    numbering = zipfile.ZipFile(fl.MAU).read("word/numbering.xml").decode("utf8")
    assert 'w:lvlText w:val="Mẫu số %1"' in numbering
    assert pd._NHAN_MAU == "Mẫu số 1"


# ── Điền đúng ô ──

def test_dien_dau_giay_va_chu_ho():
    doc = _doc(_full())
    assert _line(doc, "Vũ Ninh, ngày") == "Vũ Ninh, ngày 08 tháng 11 năm 2026"
    assert _line(doc, "Kính gửi").endswith("(Cơ quan đăng ký kinh doanh cấp xã) UBND phường Vũ Ninh")
    assert _line(doc, "Tôi là") == "Tôi là (ghi họ tên bằng chữ in hoa): TRẦN THỊ HOA"
    assert _line(doc, "Sinh ngày") == "Sinh ngày: 05/09/1985"
    assert _line(doc, "Giới tính") == "Giới tính: Nữ"
    assert _line(doc, "Số định danh cá nhân") == "Số định danh cá nhân: 027185001234"
    phone = _line(doc, "Điện thoại")
    assert "(nếu có): 0912345678" in phone and phone.endswith("Thư điện tử (nếu có): hoa@example.vn")


def test_khung_ke_khai_them_khong_lan_noi_thuong_tru_voi_noi_o():
    lines = [p.text.strip() for p in _doc(_full()).tables[0].rows[0].cells[0].paragraphs]
    assert lines[0].startswith("Dân tộc: Kinh") and lines[0].endswith("Quốc tịch: Việt Nam")
    assert lines[2].endswith(": Số 12, ngõ 3, đường Lê Lợi")
    assert lines[3].endswith(": Phường Vũ Ninh") and lines[4].endswith(": Tỉnh Bắc Ninh")
    assert lines[6].endswith(": Số 45, đường Trần Phú")
    assert lines[7].endswith(": Phường Kinh Bắc") and lines[8].endswith(": Tỉnh Bắc Giang")


def test_ten_ho_va_tru_so_vao_dung_muc():
    doc = _doc(_full())
    assert _line(doc, "Tên hộ kinh doanh viết bằng tiếng Việt").endswith(": HỘ KINH DOANH HOA MAI")
    assert _line(doc, "Tên hộ kinh doanh viết bằng tiếng nước ngoài").endswith(": HOA MAI GROCERY")
    assert _line(doc, "Tên hộ kinh doanh viết tắt").endswith(": HOA MAI")
    assert _line(doc, "Số nhà/phòng", 0).endswith(": Số 7, phố Chợ")
    assert _line(doc, "Xã/Phường/Đặc khu", 0).endswith(": Phường Đồng Nguyên")
    assert _line(doc, "Tỉnh/Thành phố", 0).endswith(": Tỉnh Thái Bình")
    assert _line(doc, "Điện thoại:") == "Điện thoại: 0222123456\tFax (nếu có): 0222654321"
    assert _line(doc, "Thư điện tử") == "Thư điện tử (nếu có): so@example.vn\tWebsite (nếu có): hoamai.example.vn"


def test_dia_chi_nhan_thue_tach_khoi_tru_so():
    doc = _doc(_full())
    assert _line(doc, "Số nhà/phòng", 1).endswith(": Số 9, đường Hoa Sữa")
    assert _line(doc, "Xã/Phường/Đặc khu", 1).endswith(": Xã Tam Đa")
    assert _line(doc, "Tỉnh/Thành phố", 1).endswith(": Tỉnh Nam Định")
    assert _line(doc, "Điện thoại (nếu có)", 1) == "Điện thoại (nếu có): 0987654321\t Thư điện tử (nếu có): thue@example.vn"


def test_von_ngay_bat_dau_lao_dong():
    doc = _doc(_full())
    assert _line(doc, "Tổng số").endswith(": 150.000.000 đồng (Một trăm năm mươi triệu đồng)")
    assert _line(doc, "5.2.").endswith("không cần kê khai nội dung này): 15/11/2026")
    assert _line(doc, "5.3.").endswith("(dự kiến): 3")


def test_o_de_trong_giu_dong_cham_de_viet_tay():
    doc = _doc(GiayDeNghi(hoTen="Lê An", dienThoai="0912345678"))
    assert _doc_para(doc, "Giới tính").text.endswith("\t")  # tab chấm còn nguyên
    assert "……………" in _line(doc, "Số định danh cá nhân")
    phone = _line(doc, "Điện thoại")
    assert "0912345678" in phone and "………………" in phone  # thư điện tử chưa có vẫn còn chấm


def test_tab_giua_dong_bo_hang_cham_khi_da_co_chu():
    p = next(p for p in _doc(_full(truSoFax="")).paragraphs if p.text.startswith("Điện thoại:"))
    stops = p._p.pPr.find(qn("w:tabs")).findall(qn("w:tab"))
    assert stops[0].get(qn("w:leader")) is None   # sau số điện thoại không còn chấm, "Fax" vẫn đúng cột
    assert stops[1].get(qn("w:leader")) == "dot"  # Fax chưa điền vẫn chấm để viết tay


def test_ky_tu_la_va_chu_to_hop_khong_lam_hong_file():
    doc = _doc(GiayDeNghi(hoTen="Trâ`n\x0b Thị  Hoa​", truSo={"chiTiet": "Số 1\n đường A\tB"}))
    assert _line(doc, "Tôi là").endswith(": TRÂ`N THỊ HOA")
    assert _line(doc, "Số nhà/phòng").endswith(": Số 1 đường A B")


# ── Ô đánh dấu ──

_WPS = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}"
_V = "{urn:schemas-microsoft-com:vml}"


def _ticked(scope) -> int:
    return sum(1 for _ in scope.iter(_WPS + "txbx"))


def _ticks(doc) -> dict:
    p_tru_so = next(p for p in doc.paragraphs if "Không kinh doanh tại trụ sở" in p.text)._p
    p_thue = next(p for p in doc.paragraphs if p.text.strip().startswith("5.4."))._p
    ke_khai = doc.tables[2].rows[0].cells[0]._tc
    chu_the = fl._boxes(doc.tables[3].rows[0].cells[0]._tc)
    return {"khongTruSo": _ticked(p_tru_so), "khoan": _ticked(p_thue), "keKhai": _ticked(ke_khai),
            "caNhan": _ticked(chu_the[0]), "hoGiaDinh": _ticked(chu_the[1])}


@pytest.mark.parametrize("form, on", [
    (dict(phuongPhapThue="ke_khai"), "keKhai"),
    (dict(phuongPhapThue="khoan"), "khoan"),
    (dict(chuThe="ca_nhan"), "caNhan"),
    (dict(chuThe="ho_gia_dinh"), "hoGiaDinh"),
    (dict(khongKinhDoanhTaiTruSo=True), "khongTruSo"),
])
def test_chi_danh_dung_mot_o(form, on):
    ticks = _ticks(_doc(GiayDeNghi(**form)))
    assert ticks == {key: int(key == on) for key in ticks}


def test_khong_chon_gi_thi_khong_o_nao_co_dau_x():
    assert not any(_ticks(_doc(GiayDeNghi())).values())


def test_o_ca_nhan_nam_ben_trai_o_thanh_vien_ho_gia_dinh():
    """Hai ô cùng nằm trong ô bảng đầu; thứ tự trong file ngược thứ tự trên giấy nên phải xếp theo vị trí."""
    left, right = fl._boxes(docx.Document(str(fl.MAU)).tables[3].rows[0].cells[0]._tc)
    wp = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
    assert int(left.find(wp + "positionH")[0].text) < 0 < int(right.find(wp + "positionH")[0].text)


def test_ban_vml_du_phong_cung_co_dau_x():
    doc = _doc(GiayDeNghi(phuongPhapThue="khoan"))
    assert sum(1 for _ in doc.element.body.iter(_V + "textbox")) == 1


# ── Bảng ──

def _rows(table) -> list[list[str]]:
    return [[c.text.strip() for c in r.cells] for r in table.rows]


def test_nganh_nghe_danh_so_va_danh_dau_nganh_chinh():
    rows = _rows(_doc(_full()).tables[1])
    assert rows[1] == ["1", "Bán lẻ lương thực trong các cửa hàng chuyên doanh", "4721", "X"]
    assert rows[2] == ["2", "Dịch vụ ăn uống khác", "", ""]
    assert len(rows) == 3


def test_nganh_nghe_bo_dong_trong_ma_form_con_lai():
    rows = _rows(_doc(GiayDeNghi(nganh=[{"ten": "", "ma": ""}, {"ten": "Bán lẻ khác", "ma": "4799"}])).tables[1])
    assert rows[1][:3] == ["1", "Bán lẻ khác", "4799"] and len(rows) == 2


def test_khong_co_nganh_giu_dong_trang_cua_mau():
    assert _rows(_doc(GiayDeNghi()).tables[1])[1] == ["", "", "", ""]


def test_o_nganh_nghe_khong_con_thut_dau_dong_cua_dong_trang():
    cell = _doc(_full()).tables[1].rows[1].cells[2]
    assert cell.paragraphs[0]._p.pPr.find(qn("w:ind")) is None


def test_thanh_vien_chi_ke_khai_khi_chu_the_la_ho_gia_dinh():
    people = [_member(1), _member(2), _member(3)]
    ca_nhan = _rows(_doc(_full(chuThe="ca_nhan", thanhVien=people)).tables[4])
    assert all(not any(r) for r in ca_nhan[2:])  # chú thích 5: chỉ kê khai khi là thành viên hộ gia đình
    ho = _rows(_doc(_full(chuThe="ho_gia_dinh", thanhVien=people)).tables[4])
    assert len(ho) == 5
    assert ho[2] == ["1", "TRƯƠNG VĂN BÌNH 1", "12/01/1982", "027082000001", "Nam", "Việt Nam", "Kinh",
                     "Số 12, ngõ 3", "Số 45, đường Trần Phú", ""]  # cột chữ ký để trống cho ký tươi
    assert ho[4][0] == "3"


def test_cot_thanh_vien_chia_lai_nhung_tong_van_bang_mau():
    goc = docx.Document(str(fl.MAU)).tables[4]._tbl.tblGrid.findall(qn("w:gridCol"))
    assert sum(fl._THANH_VIEN_COT) == sum(int(g.get(qn("w:w"))) for g in goc)
    ra = _doc(_full(chuThe="ho_gia_dinh", thanhVien=[_member()])).tables[4]._tbl.tblGrid.findall(qn("w:gridCol"))
    assert tuple(int(g.get(qn("w:w"))) for g in ra) == fl._THANH_VIEN_COT


def test_mau_trang_giu_cot_thanh_vien_cua_mau():
    ra = _doc(GiayDeNghi()).tables[4]._tbl.tblGrid.findall(qn("w:gridCol"))
    assert [g.get(qn("w:w")) for g in ra][:2] == ["675", "850"]


def test_tcmar_dung_vi_tri_trong_tcpr():
    """Word đọc tcPr theo thứ tự: tcMar sau vAlign là báo file hỏng."""
    table = _doc(_full(chuThe="ho_gia_dinh", thanhVien=[_member()])).tables[4]
    for tc in table._tbl.iter(qn("w:tc")):
        names = [etree.QName(el).localname for el in tc.tcPr]
        if "vAlign" in names:
            assert names.index("tcMar") < names.index("vAlign")


def test_dong_bang_khong_bi_tach_qua_trang_va_tieu_de_lap_lai():
    doc = _doc(_full(chuThe="ho_gia_dinh", thanhVien=[_member()]))
    for table, headers in ((doc.tables[1], 1), (doc.tables[4], 2)):
        for i, row in enumerate(table.rows):
            assert row._tr.trPr.find(qn("w:cantSplit")) is not None
            assert (row._tr.trPr.find(qn("w:tblHeader")) is not None) == (i < headers)


def test_chu_ky_co_cho_ky_va_ten_in_san():
    cell = _doc(_full()).tables[5].rows[0].cells[2]
    assert [p.text.strip() for p in cell.paragraphs] == ["CHỦ HỘ KINH DOANH", "(Ký và ghi họ tên)", "TRẦN THỊ HOA"]
    assert cell.paragraphs[-1].paragraph_format.space_before.pt == fl._CHO_KY


def test_tieu_de_di_cung_doan_sau():
    doc = _doc(_full())
    for start in fl._GIU_VOI_DOAN_SAU:
        assert _doc_para(doc, start).paragraph_format.keep_with_next, start


def _doc_para(doc, start):
    return next(p for p in doc.paragraphs if p.text.strip().startswith(start))


# ── PDF: chữ phải y hệt bản Word ──

def test_pdf_mau_trang_co_du_moi_cau_cua_mau():
    text = _pdf_text(_pdf(GiayDeNghi()))
    for line in _all_lines(docx.Document(str(fl.MAU))):
        assert _squash(line) in text, line
    for note in _note_texts(fl.MAU).values():
        assert _squash(note) in text, note
    assert _squash("Mẫu số 1") in text


def test_pdf_cung_chu_voi_ban_word_khi_da_dien():
    form = _full(chuThe="ho_gia_dinh", thanhVien=[_member(1), _member(2)], khongKinhDoanhTaiTruSo=True)
    text = _pdf_text(_pdf(form))
    for line in _all_lines(_doc(form)):
        assert _squash(line) in text, line


def test_pdf_lop_chu_tach_dung_tu_de_tim_kiem_va_sao_chep():
    document = _pdf(_full())
    words = [w[4] for page in document for w in page.get_text("words")]
    assert "THỊ" in words and "HOA" in words
    tail = document[-1].get_text()
    assert "Chủ hộ kinh doanh ký trực tiếp vào phần này" in " ".join(tail.split())


def _footnote_page(document, needle: str) -> int:
    key = _squash(needle)
    return next(i for i, page in enumerate(document) if key in _squash(page.get_text()))


@pytest.mark.parametrize("form", [GiayDeNghi(), _full(), _full(
    chuThe="ho_gia_dinh", thanhVien=[_member(i) for i in range(1, 8)],
    nganh=[{"ten": f"Ngành nghề số {i}", "ma": "4799", "chinh": i == 1} for i in range(1, 16)])])
def test_chu_thich_nam_cung_trang_voi_cho_dan_chieu(form):
    document = _pdf(form)
    pairs = (("3. Ngành, nghề kinh doanh", "Hộ kinh doanh có quyền tự do kinh doanh"),
             ("Tên ngành", "Ghi tên ngành và mã ngành cấp bốn"),
             ("Tên ngành", "Đánh dấu X để chọn một trong các ngành"),
             ("5.2. Ngày bắt đầu hoạt động", "Trường hợp hộ kinh doanh được cấp Giấy chứng nhận"),
             ("7. Thông tin về các thành viên", "Chỉ kê khai trong trường hợp chủ thể"),
             ("CHỦ HỘ KINH DOANH", "Chủ hộ kinh doanh ký trực tiếp vào phần này"))
    for anchor, note in pairs:
        assert _footnote_page(document, anchor) == _footnote_page(document, note), note


def test_pdf_so_trang_o_dau_trang_tu_trang_hai():
    document = _pdf(_full())
    tops = [[w[4] for w in page.get_text("words") if w[3] < 40] for page in document]
    assert tops[0] == [] and tops[1] == ["2"] and tops[2] == ["3"]


def test_pdf_trang_a4_nhung_font_times():
    document = _pdf(_full())
    assert round(document[0].rect.width) == 595 and round(document[0].rect.height) == 842
    assert any("Times" in font[3] for font in document[0].get_fonts())


def _mark_label(document) -> list[str]:
    """Mỗi dấu X trên ô vuông → chữ nhãn ngay bên phải ô."""
    labels = []
    for page in document:
        boxes = [fitz.Rect(d["rect"]) for d in page.get_drawings()
                 if d["items"][0][0] == "re" and 16 < fitz.Rect(d["rect"]).height < 19 and 16 < fitz.Rect(d["rect"]).width < 19]
        words = page.get_text("words")
        for x0, y0, x1, y1, text, *_ in words:
            if text != "X":
                continue
            hit = next((b for b in boxes if b.contains(fitz.Point((x0 + x1) / 2, (y0 + y1) / 2))), None)
            if hit:
                right = [w for w in words if w[0] >= hit.x1 - 1 and abs((w[1] + w[3]) / 2 - (hit.y0 + hit.y1) / 2) < 8]
                labels.append(" ".join(w[4] for w in sorted(right, key=lambda w: w[0])[:3]))
    return labels


@pytest.mark.parametrize("form, label", [
    (dict(phuongPhapThue="ke_khai"), "Phương pháp kê"),
    (dict(phuongPhapThue="khoan"), "Phương pháp khoán"),
    (dict(chuThe="ca_nhan"), "Cá nhân Các"),
    (dict(chuThe="ho_gia_dinh"), "Các thành viên"),
    (dict(khongKinhDoanhTaiTruSo=True), "Không kinh doanh"),
])
def test_pdf_dau_x_nam_trong_dung_o(form, label):
    assert _mark_label(_pdf(GiayDeNghi(**form))) == [label]


def test_pdf_mau_trang_khong_co_dau_x_nao_trong_o():
    assert _mark_label(_pdf(GiayDeNghi())) == []


def test_pdf_chu_ky_khong_dung_mot_minh_tren_trang():
    for form in (GiayDeNghi(), _full(), _full(nganh=[{"ten": f"Ngành {i}", "ma": "4799"} for i in range(1, 24)])):
        document = _pdf(form)
        page = _footnote_page(document, "CHỦ HỘ KINH DOANH")
        assert _squash("Hoàn toàn chịu trách nhiệm trước pháp luật") in _squash(document[page].get_text())


def test_pdf_co_cho_ky_giua_nhan_va_ten():
    document = _pdf(_full())
    page = document[_footnote_page(document, "CHỦ HỘ KINH DOANH")]
    words = page.get_text("words")
    label = next(w for w in words if w[4].startswith("tên)"))
    name = next(w for w in words if w[4] == "TRẦN" and w[1] > label[1])
    assert name[1] - label[3] >= fl._CHO_KY - 5


# ── PDF: dữ liệu dài không được mất chữ, không tràn lề ──

def _within_margins(document, *, bottom_gap: float = 20):
    for number, page in enumerate(document, 1):
        for x0, y0, x1, y1, text, *_ in page.get_text("words"):
            assert x0 >= 75 and x1 <= page.rect.width - 45, (number, text, x0, x1)
            assert y1 <= page.rect.height - bottom_gap, (number, text, y1)


def _longest() -> GiayDeNghi:
    address = {"chiTiet": "Số nhà dài thật dài trên đường dài " * 8, "xa": "Phường " + "Đông Tây " * 12, "tinh": "Tỉnh " + "Nam Bắc " * 13}
    return GiayDeNghi(
        diaDanh="Địa danh " * 13, ngayLap="31/12/2026", kinhGui="Cơ quan đăng ký " * 12,
        hoTen="Công Tôn Nữ Thị " * 7, ngaySinh="31/12/1999", gioiTinh="Nữ", soDinhDanh="0" * 12,
        dienThoai="0" * 30, email="a" * 109 + "@example.vn", danToc="Kinh" * 15, quocTich="Việt Nam " * 6,
        thuongTru=address, noiO=address, tenViet="Tên hộ kinh doanh " * 11, tenNuocNgoai="Foreign name " * 15,
        tenVietTat="Viết tắt " * 13, truSo=address, truSoDienThoai="0" * 30, truSoFax="0" * 30,
        truSoEmail="b" * 109 + "@example.vn", truSoWebsite="c" * 117 + ".vn", khongKinhDoanhTaiTruSo=True,
        nganh=[{"ten": "Tên ngành nghề rất dài " * 13, "ma": "4799", "chinh": i == 0} for i in range(50)],
        vonKinhDoanh="9" * 300, thueDiaChi=address, thueDienThoai="0" * 30, thueEmail="d" * 109 + "@example.vn",
        ngayBatDau="31/12/2026", soLaoDong="9" * 20, phuongPhapThue="khoan", chuThe="ho_gia_dinh",
        thanhVien=[_member(i, hoTen="Họ và tên " * 12, noiThuongTru="e" * 300, noiOHienTai="Nơi ở " * 50,
                           quocTich="Việt Nam " * 6, danToc="Kinh" * 15) for i in range(20)],
    )


def test_pdf_du_lieu_dai_toi_da_khong_mat_chu_khong_tran_le():
    form = _longest()
    document = _pdf(form)
    _within_margins(document)
    text = _pdf_text(document)
    for line in _all_lines(_doc(form)):
        assert _squash(line) in text, line[:60]


def test_du_lieu_dai_toi_da_khong_vuot_gioi_han_mot_trang_moi_dong():
    """Một dòng bảng cao hơn trang là chữ tràn đáy trang, không ai báo. Giới hạn độ dài ô phải chặn được."""
    document = _pdf(_longest())
    assert len(document) >= 10
    for number, page in enumerate(document, 1):
        words = page.get_text("words")
        assert words, f"trang {number} trắng"
        assert max(w[3] for w in words) <= page.rect.height - 20


def test_chu_khong_co_khoang_trang_van_duoc_cat_xuong_dong():
    document = _pdf(GiayDeNghi(truSoEmail="x" * 109 + "@example.vn"))
    _within_margins(document)
    assert _squash("x" * 109 + "@example.vn") in _pdf_text(document)


def test_bang_sang_trang_lap_lai_tieu_de_khong_mat_dong():
    document = _pdf(GiayDeNghi(nganh=[{"ten": f"Ngành nghề thứ {i}", "ma": f"{i:04d}"} for i in range(1, 51)]))
    pages = [i for i, page in enumerate(document) if _squash("Tên ngành") in _squash(page.get_text())]
    assert len(pages) >= 3
    text = _pdf_text(document)
    for i in range(1, 51):
        assert _squash(f"Ngành nghề thứ {i}") in text


def test_dong_bang_khong_bi_cat_qua_trang():
    document = _pdf(GiayDeNghi(nganh=[{"ten": f"Ngành nghề thứ {i}", "ma": "4799"} for i in range(1, 41)]))
    for page in document:
        for drawing in page.get_drawings():
            assert fitz.Rect(drawing["rect"]).y1 <= page.rect.height - 26


def test_khong_co_font_times_van_ra_pdf(monkeypatch):
    monkeypatch.setattr(pd, "_FONT_DIRS", ())
    pd._fonts.cache_clear()
    try:
        assert len(_pdf(_full())) >= 3
    finally:
        pd._fonts.cache_clear()


# ── API ──

def _client(user=USER) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(rt.router)
    if user:
        app.dependency_overrides[require_auth] = lambda: user
    return TestClient(app)


PATH = "/api/v1/ho-kinh-doanh/giay-de-nghi"


def test_api_bat_buoc_dang_nhap():
    client = _client(user=None)
    assert client.get(f"{PATH}/config").status_code == 401
    assert client.post(f"{PATH}/render", json={"format": "pdf"}).status_code == 401


def test_config_dien_san_theo_dia_ban_tai_khoan():
    body = _client().get(f"{PATH}/config").json()
    assert body["kinhGui"] == "UBND phường Vũ Ninh"
    assert body["diaDanh"] == "Vũ Ninh"
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", body["today"])


@pytest.mark.parametrize("xa, kinh_gui, dia_danh", [
    ("Xã Thượng Lâm", "UBND xã Thượng Lâm", "Thượng Lâm"),
    ("Đặc khu Cô Tô", "UBND đặc khu Cô Tô", "Cô Tô"),
    ("", "", ""),
])
def test_config_cac_don_vi_khac(xa, kinh_gui, dia_danh):
    body = _client({**USER, "xa": xa}).get(f"{PATH}/config").json()
    assert (body["kinhGui"], body["diaDanh"]) == (kinh_gui, dia_danh)


def test_config_gui_danh_muc_nganh_gon():
    nganh = _client().get(f"{PATH}/config").json()["nganh"]
    assert len(nganh) > 400 and set(nganh[0]) == {"ma", "ten"}
    assert all(re.fullmatch(r"\d{4}", item["ma"]) for item in nganh)


def test_render_word_va_pdf():
    client = _client()
    word = client.post(f"{PATH}/render", json={"format": "docx", "tenViet": "Tạp hóa Đức", "hoTen": "Lê An"})
    assert word.status_code == 200
    assert word.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert 'filename="Giay_de_nghi_dang_ky_ho_kinh_doanh_Tap_hoa_Duc.docx"' in word.headers["content-disposition"]
    assert word.headers["cache-control"] == "no-store"
    assert "TẠP HÓA ĐỨC" in _line(docx.Document(io.BytesIO(word.content)), "Tên hộ kinh doanh viết bằng tiếng Việt")

    pdf = client.post(f"{PATH}/render", json={"format": "pdf", "hoTen": "Lê An"})
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert 'Giay_de_nghi_dang_ky_ho_kinh_doanh_Le_An.pdf' in pdf.headers["content-disposition"]


def test_render_mau_trang_ten_tep_khong_co_duoi_ten():
    res = _client().post(f"{PATH}/render", json={"format": "docx"})
    assert 'filename="Giay_de_nghi_dang_ky_ho_kinh_doanh.docx"' in res.headers["content-disposition"]


@pytest.mark.parametrize("body", [
    {"format": "doc"},
    {"format": "pdf", "ngaySinh": "5/9/1990"},
    {"format": "pdf", "ngayBatDau": "2026-11-15"},
    {"format": "pdf", "phuongPhapThue": "khac"},
    {"format": "pdf", "chuThe": "cong_ty"},
    {"format": "pdf", "nganh": [{"ten": "x"}] * 51},
    {"format": "pdf", "thanhVien": [{"hoTen": "x"}] * 21},
    {"format": "pdf", "hoTen": "x" * 121},
])
def test_render_tu_choi_du_lieu_sai_dang(body):
    assert _client().post(f"{PATH}/render", json=body).status_code == 422


def test_main_gan_router_ngoai_co_handfree():
    """Auto Fill vẫn dùng khi tắt Handfree nên router không được nằm trong khối `if settings.handfree_enabled`."""
    source = (rt.Path(rt.__file__).parents[3] / "main.py").read_text(encoding="utf-8")
    line = next(ln for ln in source.splitlines() if "include_router(giay_de_nghi_hkd_router)" in ln)
    assert not line.startswith(" ")


# ── Auto Fill điền cổng thẳng từ tờ khai đã nhập, không OCR ──

import asyncio  # noqa: E402

from app.pipelines.dang_ky_kinh_doanh.process import mapper as hkd_mapper  # noqa: E402
from app.pipelines.dang_ky_kinh_doanh.process import runner as hkd_runner  # noqa: E402
from app.process import service as process_service  # noqa: E402
from app.process.schemas import ProcessReq  # noqa: E402


def _pages_from(form: dict) -> dict:
    async def _khong_ocr(*_a, **_k):
        raise AssertionError("có tờ khai thì không được OCR/LLM")

    import app.pipelines._shared.compact_agent.runner as compact_runner
    old = compact_runner.run
    compact_runner.run = _khong_ocr
    try:
        res = asyncio.run(hkd_runner.run({}, {"page": "__all__", "allPages": True, "giayDeNghi": form}))
    finally:
        compact_runner.run = old
    return res


def _values(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields}


def test_auto_fill_dien_tu_to_khai_khong_ocr():
    res = _pages_from(_full().model_dump())
    pages = {key: _values(fields) for key, fields in res["pages"].items()}
    assert res["extracted"]["nguon"] == "to-khai"
    assert pages["hinh-thuc-dang-ky"]["ctl00$C$REORGCtl$REORG_TYPE_IDFld"] == "Thành lập mới"
    assert pages["dia-chi"]["ctl00$C$ADDRCtl$STREET_NUMBERFld"] == "Số 7, phố Chợ"
    assert pages["dia-chi"]["ctl00$C$DCONTClt$HO_PHONEFld"] == "0222123456"
    lines = pages["nganh-nghe-kinh-doanh"]["__businessLines"]
    assert lines["codes"] == ["4721"] and lines["main"] == "4721"
    assert lines["items"][0]["name"].startswith("Bán lẻ") and lines["items"][0]["main"]
    assert pages["ten-ho-kinh-doanh"]["ctl00$C$NAMEFld"] == "Hoa Mai"
    chu_ho = pages["chu-ho-kinh-doanh"]
    assert chu_ho["ctl00$C$OWN_PCtl$PERSCtl$FULL_NAMEFld"] == "Trần Thị Hoa"
    assert chu_ho["ctl00$C$OWN_PCtl$PERSCtl$GENDER_IDFld"] == "F"
    assert chu_ho["ctl00$C$OWN_PCtl$PERSCtl$PERS_DOC_NOFld"] == "027185001234"
    # Nơi ở hiện tại đi trước nơi thường trú, như khi đọc giấy.
    assert chu_ho["ctl00$C$OWN_PCtl$PERSCtl$ADDRCCtl$STREET_NUMBERFld"] == "Số 45, đường Trần Phú"
    assert pages["thong-tin-ve-von"]["ctl00$C$CPT_CHARTER_AMOUNTFld"] == "150.000.000"
    thue = pages["thong-tin-ve-thue"]
    assert thue["ctl00$C$UC_DW_TAXEditCtl$REP_RECV_ADDR_TYPEFld"] == "0"
    assert thue["ctl00$C$UC_DW_TAXEditCtl$ADDRCtl$STREET_NUMBERFld"] == "Số 9, đường Hoa Sữa"
    assert thue["ctl00$C$UC_DW_TAXEditCtl$TOTAL_OF_LABORSFld"] == "3"
    assert thue["ctl00$C$UC_DW_TAXEditCtl$TAX_CAL_METHOD_IDRbBox"] == "DEC"
    nop = pages["nguoi-nop-ho-so"]
    assert nop["ctl00$C$PERS_SUBGroup"] == hkd_mapper._PERS_SUB_SELF_LABEL
    assert nop["__identityCandidates"][0]["soDinhDanh"] == "027185001234"


def test_to_khai_thanh_vien_ho_gia_dinh_khong_thanh_nguoi_nop_thay():
    form = _full(chuThe="ho_gia_dinh", thanhVien=[_member(1), _member(2)]).model_dump()
    nop = _values(_pages_from(form)["pages"]["nguoi-nop-ho-so"])
    assert nop["ctl00$C$PERS_SUBGroup"] == hkd_mapper._PERS_SUB_SELF_LABEL
    assert len(nop["__identityCandidates"]) == 1


def test_to_khai_trong_dia_chi_thue_thi_giong_tru_so():
    form = _full(thueDiaChi={}, noiO={}).model_dump()
    pages = {key: _values(fields) for key, fields in _pages_from(form)["pages"].items()}
    assert pages["thong-tin-ve-thue"]["ctl00$C$UC_DW_TAXEditCtl$REP_RECV_ADDR_TYPEFld"] == "1"
    # Không có nơi ở hiện tại → lấy nơi thường trú.
    assert pages["chu-ho-kinh-doanh"]["ctl00$C$OWN_PCtl$PERSCtl$ADDRCCtl$STREET_NUMBERFld"] == "Số 12, ngõ 3, đường Lê Lợi"


def test_to_khai_trong_khong_dien_bua():
    pages = _pages_from({})["pages"]
    assert _values(pages["chu-ho-kinh-doanh"]) == {"ctl00$C$OWNER_TYPE_RbBox": "P"}
    assert pages["thong-tin-ve-von"] == []


@pytest.mark.parametrize("form", [{"ngaySinh": "5/9/1990"}, "khong-phai-object", {"phuongPhapThue": "khac"}])
def test_to_khai_sai_dang_bao_400(form):
    with pytest.raises(AppError) as err:
        asyncio.run(hkd_runner.run({}, {"giayDeNghi": form}))
    assert err.value.code == 400 and err.value.error == "BAD_TO_KHAI"


def test_process_nhan_luot_khong_tep_khi_co_to_khai():
    with_form = ProcessReq(procedure="dang-ky-kinh-doanh", options={"giayDeNghi": {}}, files=[])
    assert process_service.has_form_input(with_form)
    other = ProcessReq(procedure="khai-tu", options={"giayDeNghi": {}}, files=[])
    assert not process_service.has_form_input(other)
    with pytest.raises(AppError) as err:
        process_service.prepare_process(
            ProcessReq(procedure="dang-ky-kinh-doanh", options={}, files=[]),
            proc={"roles": []}, pipeline=hkd_runner.run, include_review=False)
    assert err.value.error == "NO_FILES"
    prepared = process_service.prepare_process(
        with_form, proc={"roles": []}, pipeline=hkd_runner.run, include_review=False)
    assert prepared.files_by_role == {} and prepared.pipeline_options["giayDeNghi"] == {}
