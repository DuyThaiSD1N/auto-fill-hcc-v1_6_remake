"""Lớp soát thứ hai của thủ tục đăng ký kết hôn: ba thanh tra chạy cho từng bên, không lấy chéo giữa hai bên."""
import json

import pytest

from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.ket_hon import thanh_tra
from app.pipelines.ket_hon.process import mapper
from app.pipelines.ket_hon.process import runner as ket_hon_runner
from app.pipelines.ket_hon.thanh_tra import chu_the, dia_chi, dinh_danh, dot_hai, tinh_trang
from app.services.llm import client

NAM, NU = chu_the.SIDES
TO_KHAI = """TỜ KHAI ĐĂNG KÝ KẾT HÔN
Kính gửi: UBND xã Đông Mai
Thông tin | Bên nữ | Bên nam
---|---|---
Họ, chữ đệm, tên | Lê Thị Hanh | Trần Văn Em
Ngày, tháng, năm sinh | 05/03/1985 | 02/04/1980
Dân tộc (4) | Tày | Kinh
Nơi cư trú (4) | Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh | Tổ 5
phường Yên Trung
tỉnh Bắc Ninh |
Giấy tờ tùy thân (5) | 001185000007 | 001080000009
Kết hôn lần thứ mấy | Lần đầu | lần 2
Chúng tôi cam đoan những lời khai trên đây là đúng sự thật
Bên nữ | Bên nam
(Ký, ghi rõ họ, chữ đệm, tên) | (Ký, ghi rõ họ, chữ đệm, tên)
Hanh | Em"""
THE_NU = """CĂN CƯỚC CÔNG DÂN
Số / No.: 001185000007
Họ và tên / Full name: LÊ THỊ MANH
Ngày sinh / Date of birth: 05/03/1985
Nơi thường trú / Place of residence: Thôn Hạ
Đông Mai, Yên Phong, Bắc Ninh"""
# Mặt sau thẻ căn cước mới: nơi cư trú không kèm họ tên, khối kết thúc bằng vùng MRZ của chủ thẻ.
THE_NAM_SAU = """Nơi cư trú / Place of residence: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh
Ngày, tháng, năm / Date, month, year: 10/05/2025
BỘ CÔNG AN
IDVNM0800000090001080000009<<6
8004025M4004025VNM<<<<<<<<<<<8
TRAN<<VAN<EM<<<<<<<<<<<<<<<<<<"""
VALUES = {
    "BenNu_HoTen": "Lê Thị Hanh", "BenNu_SoDinhDanh": "001185000007", "BenNu_NgaySinh": "05/03/1985",
    "BenNam_HoTen": "Trần Văn Em", "BenNam_SoDinhDanh": "001080000009", "BenNam_NgaySinh": "02/04/1980",
}
DOCS = [{"name": "tk.pdf", "text": TO_KHAI}, {"name": "nu.pdf", "text": THE_NU}, {"name": "nam.pdf", "text": THE_NAM_SAU}]


def _case(values=None, docs=DOCS):
    return Case(docs, "", chu_the.effective({**VALUES, **(values or {})}), {})


# ───────── Hai chủ thể + bảng tờ khai ─────────
def test_bang_to_khai_tach_cot_theo_dong_tieu_de_va_noi_o_nhieu_dong():
    [table] = chu_the.declaration_tables(DOCS)
    assert table["order"] == ("nu", "nam") and table["doc"] == 1
    assert chu_the.cell(table, "cu_tru", NU)[0] == "Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh"
    assert chu_the.cell(table, "cu_tru", NAM) == ("Tổ 5, phường Yên Trung, tỉnh Bắc Ninh",
                                                  "Nơi cư trú (4) | Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh | Tổ 5")
    assert chu_the.cell(table, "so_lan", NAM)[0] == "lần 2"


def test_hang_khong_tach_dung_hai_o_thi_bo():
    text = TO_KHAI.replace("Dân tộc (4) | Tày | Kinh", "Dân tộc (4) | Tày")
    assert "dan_toc" not in chu_the.declaration_tables([{"text": text}])[0]["rows"]


def test_gia_tri_dang_dung_the_truoc_to_khai_bu_va_the_nguoi_khac_thi_giu_nguyen():
    area = {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Hạ"}
    out = chu_the.effective({"ToKhaiNu_HoTen": "Lê Thị Hanh", "ToKhaiNu_NgaySinh": "05/03/1985",
                             "BenNu_SoDinhDanh": "001185000007", "BenNu_NoiCuTru_TrongNuoc": area})
    assert out["BenNu_HoTen"] == "Lê Thị Hanh" and out["ToKhaiNu_NoiCuTru_TrongNuoc"] == area
    other = {"BenNam_HoTen": "Phạm Văn Giang", "BenNam_SoDinhDanh": "001070000111",
             "ToKhaiNam_HoTen": "Trần Văn Em", "ToKhaiNam_SoDinhDanh": "001080000009", "ToKhaiNam_NgaySinh": "02/04/1980"}
    assert chu_the.card_is_other(other, NAM) and "BenNam_NgaySinh" not in chu_the.effective(other)


# ───────── Định danh ─────────
def _fake_pages(monkeypatch, replies: dict):
    async def fake_chat(messages, **kwargs):
        page = messages[1]["content"]
        return json.dumps({"nguoi": next((people for marker, people in replies.items() if marker in page), [])})

    monkeypatch.setattr(client, "chat", fake_chat)


_KET_HON = "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nHọ, chữ đệm, tên: LÊ THỊ MANH\nNgày, tháng, năm sinh: 05/03/1985"


async def test_dinh_danh_chi_de_xuat_cho_dung_ben_va_ghi_vao_field_the(monkeypatch):
    _fake_pages(monkeypatch, {
        "TỜ KHAI": [{"ho_ten": "Lê Thị Hanh", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                     "vai": "bên nữ", "loai_giay": "to_khai", "dong": "Họ, chữ đệm, tên | Lê Thị Hanh | Trần Văn Em"},
                    {"ho_ten": "Trần Văn Em", "so_dinh_danh": "001080000009", "ngay_sinh": "02/04/1980",
                     "vai": "bên nam", "loai_giay": "to_khai", "dong": "Họ, chữ đệm, tên | Lê Thị Hanh | Trần Văn Em"}],
        "CĂN CƯỚC CÔNG DÂN": [{"ho_ten": "LÊ THỊ MANH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                               "loai_giay": "can_cuoc", "dong": "Họ và tên / Full name: LÊ THỊ MANH"}],
        "XÁC NHẬN": [{"ho_ten": "LÊ THỊ MANH", "so_dinh_danh": None, "ngay_sinh": "05/03/1985",
                      "loai_giay": "co_quan_cap", "dong": "Họ, chữ đệm, tên: LÊ THỊ MANH"}],
    })
    case = _case(docs=DOCS + [{"name": "xn.pdf", "text": _KET_HON}])
    findings = [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if not f.unit.key.endswith(".the")]
    assert [(f.unit.key, f.values, f.owner, f.backed) for f in findings] == [
        ("nu.ho_ten", {"BenNu_HoTen": "LÊ THỊ MANH"}, "bên nữ", True)]


async def test_ngay_cap_doc_o_mat_sau_the_mang_dung_so_dinh_danh(monkeypatch):
    _fake_pages(monkeypatch, {})
    case = _case({"BenNu_NgayCap": "01/01/2021"})  # bên nam bỏ trống ngày cấp
    findings = [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key.endswith(".the")]
    assert [(f.unit.key, f.values, f.backed) for f in findings] == [("nam.the", {"BenNam_NgayCap": "10/05/2025"}, True)]
    assert "10/05/2025" in findings[0].quote
    # Ngày cấp đang có thì không đổi.
    case = _case({"BenNam_NgayCap": "02/04/2021", "BenNu_NgayCap": "01/01/2021"})
    assert not [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key.endswith(".the")]


async def test_dan_toc_o_dong_cha_me_tren_giay_khai_sinh_cua_con_chi_nhan_khi_trung_ten_va_nam_sinh(monkeypatch):
    birth = "GIẤY KHAI SINH\nHọ và tên cha: Trần Văn Em\nDân tộc: Tày Quốc tịch: Việt Nam Năm sinh: 1980\nHọ và tên mẹ: Lê Thị Hanh\nDân tộc: Nùng Quốc tịch: Việt Nam Năm sinh: 1987"
    _fake_pages(monkeypatch, {"GIẤY KHAI SINH": [
        {"ho_ten": "Trần Văn Em", "ngay_sinh": "1980", "dan_toc": "Tày", "vai": "cha", "loai_giay": "khai_sinh", "dong": "Họ và tên cha: Trần Văn Em"},
        {"ho_ten": "Lê Thị Hanh", "ngay_sinh": "1987", "dan_toc": "Nùng", "vai": "mẹ", "loai_giay": "khai_sinh", "dong": "Họ và tên mẹ: Lê Thị Hanh"}]})
    case = _case(docs=[DOCS[1], DOCS[2], {"name": "ks.pdf", "text": birth}])
    findings = {f.unit.key: f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử")}
    assert findings["nam.dan_toc"].values == {"BenNam_DanToc": "Tày"}   # trùng họ tên + năm sinh 1980
    assert "nu.dan_toc" not in findings                                   # dòng mẹ ghi năm sinh lệch thẻ (1987 / 1985)


async def test_ho_ten_chi_khac_dau_chu_in_thang_chu_viet_tay(monkeypatch):
    _fake_pages(monkeypatch, {"TỜ KHAI": [{"ho_ten": "Lê Thị Hanh", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                                           "vai": "bên nữ", "loai_giay": "to_khai", "dong": "Họ, chữ đệm, tên | Lê Thị Hanh"}],
                              "CĂN CƯỚC CÔNG DÂN": [{"ho_ten": "LÊ THỊ HẠNH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                                                     "loai_giay": "can_cuoc", "dong": "Họ và tên / Full name: LÊ THỊ HẠNH"}]})
    card = THE_NU.replace("LÊ THỊ MANH", "LÊ THỊ HẠNH")
    case = _case({"BenNu_HoTen": "Lê Thị Hanh"}, [DOCS[0], {"name": "nu.pdf", "text": card}])
    [finding] = [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key == "nu.ho_ten"]
    assert finding.values == {"BenNu_HoTen": "LÊ THỊ HẠNH"} and finding.backed


async def test_ho_ten_tren_the_lech_mot_tieng_thi_sua_theo_mrz_cung_so_va_giay_in_khop_mrz(monkeypatch):
    card = THE_NAM_SAU + "\n"
    decision = "TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG\nNguyên đơn: Anh Trần Văn Em\nBị đơn: Chị Phạm Thị Giang"
    _fake_pages(monkeypatch, {"TÒA ÁN": [{"ho_ten": "Trần Văn Em", "vai": "nguyen_don", "loai_giay": "quyet_dinh", "dong": "Nguyên đơn: Anh Trần Văn Em"}]})
    case = _case({"BenNam_HoTen": "TRẦN VĂN EN"}, [{"name": "nam.pdf", "text": card}, {"name": "qd.pdf", "text": decision}])
    [finding] = [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key == "nam.ho_ten"]
    assert finding.values == {"BenNam_HoTen": "Trần Văn Em"} and finding.backed and "IDVNM" in finding.quote


def test_duong_su_ly_hon_lech_mot_tieng_o_ten_van_la_nguoi_do():
    match = thanh_tra.tinh_trang.mapper._divorce_party_matches
    assert match("NGUYỄN THỊ HUỲNH", "Nguyễn Thị Hường; Ngô Quang Bắc")
    assert not match("NGUYỄN THỊ HUỲNH", "Tạ Thị Phương; Nguyễn Văn Thích")   # khác chữ đệm / họ
    assert not match("Nguyễn Văn An", "Nguyễn Thị An; Lê Văn Bình")             # khác chữ đệm


def test_so_dinh_danh_ma_hoa_gioi_tinh_khac_ben_dang_xet_thi_bac():
    unit = dinh_danh.UNITS_BY_SIDE["nam"]["so_dinh_danh"]
    assert dinh_danh.check(unit, {"BenNam_SoDinhDanh": "001185000007"}, _case())  # chữ số thứ tư lẻ = Nữ
    assert not dinh_danh.check(unit, {"BenNam_SoDinhDanh": "001080000009"}, _case())


# ───────── Địa chỉ ─────────
def _fake_area(value, nationality="Việt Nam"):
    ward = {"dong mai": "Xã Đông Mai", "yen trung": "Phường Yên Trung"}.get(dia_chi.base._bare(value.get("xa")), "")
    return {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": ward or str(value.get("xa") or ""),
            "diaChi": str(value.get("diaChi") or "")}


@pytest.fixture
def catalog(monkeypatch):
    monkeypatch.setattr(dia_chi.mapper, "_area", _fake_area)
    monkeypatch.setattr(dia_chi.area_remap, "is_current_area", lambda tinh, xa: xa in ("Xã Đông Mai", "Phường Yên Trung"))
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: None)


def test_dong_cu_tru_gan_voi_tung_ben_bang_cot_to_khai_ten_tren_the_va_mrz(catalog):
    case = _case()
    lines = {side.key: [(item["text"], item["handwritten"]) for item in
                        dia_chi._table_lines(case, side, chu_the.identity(case.values, side)["name"])
                        + dia_chi._card_lines(case, side, chu_the.identity(case.values, side))] for side in chu_the.SIDES}
    assert lines["nu"] == [("Nơi cư trú: Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh", True),
                           ("Nơi thường trú / Place of residence: Thôn Hạ Đông Mai, Yên Phong, Bắc Ninh", False)]
    assert lines["nam"] == [("Nơi cư trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh", True),
                            ("Nơi cư trú / Place of residence: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh", False)]


def test_dia_chi_lay_nham_cot_ben_kia_thi_de_xuat_theo_cot_cua_minh(catalog):
    wrong = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Hạ"}
    finding = dia_chi.side_finding(_case({"ToKhaiNam_NoiCuTru_TrongNuoc": wrong}), NAM)
    assert finding.unit.key == "nam.noi_cu_tru" and finding.owner == "bên nam" and finding.backed
    assert finding.values["ToKhaiNam_NoiCuTru_TrongNuoc"] == {"tinh": "tỉnh Bắc Ninh", "xa": "phường Yên Trung", "diaChi": "Tổ 5"}
    assert finding.quote in TO_KHAI or finding.quote in THE_NAM_SAU  # dòng chứng cứ là dòng OCR thật


def test_dia_chi_da_dung_thi_khong_de_xuat(catalog):
    right = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Tổ 5"}
    assert dia_chi.side_finding(_case({"ToKhaiNam_NoiCuTru_TrongNuoc": right}), NAM) is None


# ───────── Tình trạng hôn nhân ─────────
def test_so_lan_ket_hon_doc_theo_cot_cua_tung_ben():
    case = _case({"BenNam_SoLanKetHon": "1", "BenNu_SoLanKetHon": "1"})
    assert tinh_trang._count_finding(NU, case) is None
    finding = tinh_trang._count_finding(NAM, case)
    assert finding.values == {"BenNam_SoLanKetHon": "2"} and finding.backed and finding.quote.startswith("Kết hôn lần thứ mấy")


@pytest.mark.parametrize("cell,count", [("Lần đầu", "1"), ("lần 2", "2"), ("02", "2"), ("lần thứ hai", "2"), ("", ""), ("....", "")])
def test_doc_so_lan_trong_o(cell, count):
    assert tinh_trang._declared_count(cell) == count


_QUYET_DINH = "TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG\nSố: 12/2020/QĐST-HNGĐ\nYên Phong, ngày 03 tháng 4 năm 2020\nQUYẾT ĐỊNH CÔNG NHẬN THUẬN TÌNH LY HÔN\nAnh Trần Văn Em và chị Phạm Thị Giang"


async def test_van_ban_ly_hon_chi_gan_cho_ben_la_duong_su(monkeypatch):
    async def fake_chat(messages, **kwargs):
        return json.dumps({"bo": [{"viec": "ly_hon", "nguon": "dau_giay", "so": "12/2020/QĐST-HNGĐ", "ngay": "03/04/2020",
                                   "co_quan": "TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG", "nguoi": "Trần Văn Em; Phạm Thị Giang",
                                   "dong": "Số: 12/2020/QĐST-HNGĐ"}]})

    monkeypatch.setattr(client, "chat", fake_chat)
    case = _case({"BenNam_SoLanKetHon": "2", "BenNu_SoLanKetHon": "1"}, DOCS + [{"name": "qd.pdf", "text": _QUYET_DINH}])
    findings = {f.unit.key: f for f in await tinh_trang.find(tinh_trang.INSPECTOR, case, "thử")}
    assert set(findings) == {"nam.ly_hon", "nam.tinh_trang"}
    assert findings["nam.tinh_trang"].values == {"BenNam_TinhTrangHonNhan": "3"}
    assert findings["nam.ly_hon"].values == {
        "BenNam_BanAnLyHon_So": "12/2020/QĐST-HNGĐ", "BenNam_BanAnLyHon_Ngay": "03/04/2020",
        "BenNam_BanAnLyHon_CoQuan": "Tòa án nhân dân huyện Yên Phong",
        "BenNam_BanAnLyHon_DuongSu": "Trần Văn Em; Phạm Thị Giang"}
    assert not tinh_trang.check(findings["nam.ly_hon"].unit, findings["nam.ly_hon"].values, case)


async def test_van_ban_dang_gan_la_cua_nguoi_khac_thi_de_xuat_van_ban_cua_dung_ben_co_can_cu(monkeypatch):
    async def fake_chat(messages, **kwargs):
        return json.dumps({"bo": [{"viec": "ly_hon", "nguon": "dau_giay", "so": "12/2020/QĐST-HNGĐ", "ngay": "03/04/2020",
                                   "co_quan": "TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG", "nguoi": "Trần Văn Em; Phạm Thị Giang",
                                   "dong": "Số: 12/2020/QĐST-HNGĐ"}]})

    monkeypatch.setattr(client, "chat", fake_chat)
    # Lượt trích gán cho bên nam văn bản có đương sự là hai người khác (hồ sơ có hai văn bản ly hôn).
    wrong = {"BenNam_TinhTrangHonNhan": "3", "BenNam_BanAnLyHon_So": "99/2019/QĐST-HNGĐ", "BenNam_BanAnLyHon_Ngay": "01/02/2019",
             "BenNam_BanAnLyHon_CoQuan": "Tòa án nhân dân huyện Yên Phong", "BenNam_BanAnLyHon_DuongSu": "Lê Thị Hanh; Vũ Văn Ba"}
    case = _case(wrong, DOCS + [{"name": "qd.pdf", "text": _QUYET_DINH}])
    findings = {f.unit.key: f for f in await tinh_trang.find(tinh_trang.INSPECTOR, case, "thử")}
    assert findings["nam.ly_hon"].backed and "không có bên nam" in findings["nam.ly_hon"].evidence[0]
    # Văn bản đang gán có ghi bên nam: chỉ lệch số / ngày thì không thêm căn cứ này.
    case = _case({**wrong, "BenNam_BanAnLyHon_DuongSu": "Trần Văn Em; Phạm Thị Giang"}, DOCS + [{"name": "qd.pdf", "text": _QUYET_DINH}])
    findings = {f.unit.key: f for f in await tinh_trang.find(tinh_trang.INSPECTOR, case, "thử")}
    assert "nam.ly_hon" not in findings or "không có bên nam" not in findings["nam.ly_hon"].evidence[0]


_KHAI_TU = "TRÍCH LỤC KHAI TỬ\nSố: 05/TLKT-BS\nHọ, chữ đệm, tên: PHẠM THỊ GIANG\nGiới tính: Nữ\nĐã chết vào lúc: ngày 02 tháng 3 năm 2019"


async def test_giay_khai_tu_cua_nguoi_khac_gioi_gan_cho_ben_do_va_thay_ma_ly_hon_khong_co_van_ban(monkeypatch):
    async def fake_chat(messages, **kwargs):
        return json.dumps({"bo": [{"viec": "khai_tu", "nguon": "dau_giay", "so": "05/TLKT-BS", "ngay": "04/03/2019",
                                   "co_quan": "UBND xã Đông Mai", "nguoi": "Phạm Thị Giang", "gioi_tinh": "Nữ",
                                   "dong": "Số: 05/TLKT-BS"}]})

    monkeypatch.setattr(client, "chat", fake_chat)
    docs = DOCS + [{"name": "kt.pdf", "text": _KHAI_TU}]
    # Tờ khai ghi bên nam lần 2; lượt trích ghi "đã ly hôn" (theo dòng gộp "ly hôn hoặc góa") mà không có văn bản ly hôn.
    findings = {f.unit.key: f for f in await tinh_trang.find(tinh_trang.INSPECTOR, _case({"BenNam_TinhTrangHonNhan": "3"}, docs), "thử")}
    assert findings["nam.tinh_trang"].values == {"BenNam_TinhTrangHonNhan": "4"} and "nam.khai_tu" in findings
    assert not [key for key in findings if key.startswith("nu.") and key != "nu.so_lan"]
    # Tờ khai ghi bên đó kết hôn LẦN ĐẦU: giấy khai tử không phải của vợ / chồng trước của họ.
    first = [{"name": "tk.pdf", "text": TO_KHAI.replace("Lần đầu | lần 2", "Lần đầu | Lần đầu")}] + DOCS[1:] + [{"name": "kt.pdf", "text": _KHAI_TU}]
    findings = {f.unit.key for f in await tinh_trang.find(tinh_trang.INSPECTOR, _case(docs=first), "thử")}
    assert not {"nam.khai_tu", "nam.tinh_trang"} & findings


# ───────── Điền đợt 2 ─────────
def _fields(values: dict) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


async def test_ban_va_chi_gom_o_lop_soat_doi_kem_gia_tri_luot_dau(monkeypatch):
    async def review(documents, values, options=None):
        return Result({**values, "BenNu_HoTen": "LÊ THỊ MANH", "BenNam_SoLanKetHon": "2"}, [{"outcome": "sua"}], {})

    monkeypatch.setattr(dot_hai, "review", review)
    base = mapper.enrich(_fields(VALUES), {})
    out = await dot_hai.patch(DOCS, _fields(VALUES), base, {})
    assert {f["name"]: (f["value"], f["from"], f["by"]) for f in out["fields"]} == {
        "HoTenBenNu": ("LÊ THỊ MANH", "LÊ THỊ HANH", "dinh_danh"),
        "SoLanKetHon_BenNam": ("2", "1", "tinh_trang")}


async def test_runner_chi_tra_ham_dot_hai_khi_duoc_bat(monkeypatch):
    from app.config import settings
    from app.services import ocr

    async def fake_uncached(files):
        return [{"name": f.get("name"), "text": THE_NU, "provider": "tiengnoi"} for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return '{"fields": {"BenNu_HoTen": "Lê Thị Manh", "BenNu_SoDinhDanh": "001185000007"}}'

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    files = {"": [{"name": "the.png", "type": "image/png", "dataUrl": "data:image/png;base64,QUJD"}]}
    plain = await ket_hon_runner.run(files, {})
    wanted = await ket_hon_runner.run(files, {"_secondPass": True})
    assert "_second_pass" not in plain and callable(wanted.pop("_second_pass"))
    assert plain["fields"] == wanted["fields"]


def test_bo_thanh_tra_du_ba_nhom_cho_ca_hai_ben():
    assert [i.key for i in thanh_tra.INSPECTORS] == ["dinh_danh", "dia_chi", "tinh_trang"]
    for inspector in thanh_tra.INSPECTORS:
        assert {unit.key.split(".")[0] for unit in inspector.units} == {"nam", "nu"}


def test_form_cu_can_nang_luc_rieng_de_chay_dot_hai():
    from app.procedures.registry import get_procedure
    from app.second_pass import service

    assert get_procedure("ket-hon")["secondPass"] == "legacy"
    assert service.capability(get_procedure("ket-hon")) == "secondPassLegacy"
    # Thủ tục form SurveyJS và thủ tục không khai giữ tên năng lực cũ.
    assert service.capability(get_procedure("xac-nhan-tinh-trang-hon-nhan")) == "secondPass"
    assert service.capability(None) == "secondPass"


def test_to_khai_co_o_cu_tru_khong_tach_duoc_thi_khong_doi_dia_chi_theo_the(catalog):
    # Tờ khai là nơi cư trú hiện tại; ô tờ khai viết tắt không tách được cấp → không lấy nơi thường trú cũ trên thẻ.
    text = TO_KHAI.replace("Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh", "TDP Hưng Đạo P. YP - BN")
    current = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "TDP Hưng Đạo"}
    docs = [{"name": "tk.pdf", "text": text}, DOCS[1], DOCS[2]]
    assert dia_chi.side_finding(_case({"ToKhaiNu_NoiCuTru_TrongNuoc": current}, docs), NU) is None


def test_ten_xa_cu_la_ten_to_dan_pho_thi_khong_cat_khoi_chi_tiet(monkeypatch):
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: {"xa": "Phường Yên Trung"} if split["xa"] in (
        "Đại Bái", "Thạch Thang") else None)
    # Không chắc cụm cuối là xã cũ hay tên tổ dân phố → báo "không rõ" để bỏ cách tách hai cấp của dòng đó.
    assert dia_chi._trailing_old_ward("TDP Đại Bái", "Yên Trung", "Bắc Ninh", "yen trung x") == dia_chi._AMBIGUOUS_TAIL
    assert dia_chi._trailing_old_ward("Tổ dân phố Quyết Đại Bái", "Yên Trung", "Bắc Ninh", "yen trung x") == dia_chi._AMBIGUOUS_TAIL
    assert dia_chi._trailing_old_ward("Thôn Hạ", "Yên Trung", "Bắc Ninh", "yen trung x") is None
    assert dia_chi._trailing_old_ward("Tổ 21 Thạch Thang", "Yên Trung", "Bắc Ninh", "yen trung x") == ("Tổ 21", "Thạch Thang")


def test_so_nha_khac_nhau_khong_phai_mot_chi_tiet_doc_lech():
    key = dia_chi._detail_key
    assert not dia_chi._same_detail(key("K266/H79/45A2 Hoàng Diệu"), key("K266 H79/42, Hoàng Diệu"))
    assert dia_chi._same_detail(key("57 Cao Thắng"), key("57 Cao Tháng"))


async def test_ho_ten_ngang_diem_voi_giay_khac_thi_giu_theo_the(monkeypatch):
    # Thẻ in một cách viết, giấy khai sinh của con (do cơ quan cấp) in cách viết khác dấu: kết hôn điền theo thẻ.
    khai_sinh = "GIẤY KHAI SINH\nHọ, chữ đệm, tên người mẹ: LÊ THỊ MÀNH\nNgày, tháng, năm sinh: 05/03/1985"
    _fake_pages(monkeypatch, {
        "CĂN CƯỚC CÔNG DÂN": [{"ho_ten": "LÊ THỊ MANH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                               "loai_giay": "can_cuoc", "dong": "Họ và tên / Full name: LÊ THỊ MANH"}],
        "KHAI SINH": [{"ho_ten": "LÊ THỊ MÀNH", "so_dinh_danh": None, "ngay_sinh": "05/03/1985",
                       "loai_giay": "co_quan_cap", "dong": "Họ, chữ đệm, tên người mẹ: LÊ THỊ MÀNH"}],
    })
    case = _case({"BenNu_HoTen": "LÊ THỊ MANH"}, [DOCS[1], {"name": "ks.pdf", "text": khai_sinh}])
    assert not [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key == "nu.ho_ten"]


def test_dia_chi_bon_cap_khong_doc_thanh_hai_cap(monkeypatch):
    # Tên huyện cũ trùng tên một xã hiện hành: cụm trần đứng trước nó là xã cũ, không phải chi tiết.
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: {"xa": "Phường Yên Trung"} if (
        split.get("xa") == "Yên Trung" and not split.get("huyen")) else None)
    item = {"line": "Nơi thường trú: 326/5B Lê Hồng Phong, Phước Long, Yên Trung, Bắc Ninh",
            "text": "Nơi thường trú: 326/5B Lê Hồng Phong, Phước Long, Yên Trung, Bắc Ninh"}
    assert dia_chi.catalog_split(item, Case([], "", {}, {})) is None
    item = {"line": "Nơi cư trú: Đông Lâm", "text": "Nơi cư trú: Đông Lâm Yên Trung, Bắc Ninh"}
    assert dia_chi.catalog_split(item, Case([], "", {}, {})) == {"tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Đông Lâm"}


async def test_ho_ten_chi_khac_dau_ma_khong_du_dau_hon_thi_khong_de_xuat(monkeypatch):
    # Cùng một thẻ quét hai lần, hai lần đọc lệch dấu: không phải hai nguồn độc lập.
    card = THE_NU.replace("LÊ THỊ MANH", "LÊ THỊ HÀNH")
    _fake_pages(monkeypatch, {"CĂN CƯỚC CÔNG DÂN": [
        {"ho_ten": "LÊ THỊ HÀNH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985", "loai_giay": "can_cuoc",
         "dong": "Họ và tên / Full name: LÊ THỊ HÀNH"}]})
    docs = [{"name": "a.pdf", "text": card}, {"name": "b.pdf", "text": card + "\n(bản quét lần hai)"}]
    case = _case({"BenNu_HoTen": "LÊ THỊ HẠNH"}, docs)
    assert not [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key == "nu.ho_ten"]


def test_dong_the_khong_noi_dong_ke_khi_dia_chi_da_du_hoac_dong_ke_la_ngay(catalog):
    card = THE_NU.replace("Nơi thường trú / Place of residence: Thôn Hạ\nĐông Mai, Yên Phong, Bắc Ninh",
                          "Nơi thường trú / Place of residence: Thôn Hạ, Đông Mai, Yên Phong, Bắc Ninh\nCó giá trị đến 05/03/2045")
    case = _case(docs=[{"name": "nu.pdf", "text": card}])
    [line] = dia_chi._card_lines(case, NU, chu_the.identity(case.values, NU))
    assert line["text"] == "Nơi thường trú / Place of residence: Thôn Hạ, Đông Mai, Yên Phong, Bắc Ninh"


def test_xa_dang_chon_duoc_khong_doi_theo_the_khi_khong_co_can_cu_khac(catalog):
    # Không có tờ khai; địa chỉ đang có ở một xã chọn được, thẻ in xã khác: không đủ căn cứ để đổi xã.
    current = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Tổ 9"}
    case = _case({"ToKhaiNu_NoiCuTru_TrongNuoc": current}, [DOCS[1].copy() | {"text": THE_NU.replace(
        "Nơi thường trú / Place of residence: Thôn Hạ\nĐông Mai, Yên Phong, Bắc Ninh",
        "Nơi thường trú / Place of residence: Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh")}])
    assert dia_chi.side_finding(case, NU) is None


async def test_so_dinh_danh_va_ngay_sinh_lay_theo_vung_mrz_cua_chinh_ben_do(monkeypatch):
    # Lượt trích cắt nhầm 12 chữ số trong dòng IDVNM và đọc lệch năm sinh; MRZ của thẻ mang tên bên nam ghi đúng.
    _fake_pages(monkeypatch, {})
    case = _case({"BenNam_SoDinhDanh": "080000009000", "BenNam_NgaySinh": "02/04/1908"})
    findings = {f.unit.key: f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key.startswith("nam.")}
    assert findings["nam.so_dinh_danh"].values == {"BenNam_SoDinhDanh": "001080000009"}
    assert findings["nam.ngay_sinh"].values == {"BenNam_NgaySinh": "02/04/1980"}
    assert all(f.backed and "MRZ" in f.evidence[0] for f in findings.values())
    assert findings["nam.so_dinh_danh"].quote.startswith("IDVNM") and findings["nam.ngay_sinh"].quote.startswith("800402")
    # Lượt trích đã đúng theo MRZ thì không đề xuất gì.
    assert not [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, _case(), "thử")
                if f.unit.key in ("nam.so_dinh_danh", "nam.ngay_sinh")]


async def test_mrz_khac_ho_ten_hoac_khong_khop_noi_bo_thi_khong_dung(monkeypatch):
    _fake_pages(monkeypatch, {})
    other = THE_NAM_SAU.replace("TRAN<<VAN<EM", "TRAN<<VAN<ANH")                 # thẻ của người khác tên
    broken = THE_NAM_SAU.replace("8004025M4004025", "7904025M4004025")           # năm sinh MRZ lệch mã năm trong số
    for text in (other, broken):
        case = _case({"BenNam_SoDinhDanh": "080000009000"}, [DOCS[0], DOCS[1], {"name": "nam.pdf", "text": text}])
        assert not [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key == "nam.so_dinh_danh"]


async def test_so_cmnd_chin_so_khong_can_viec_nhan_so_dinh_danh_tren_giay_khac(monkeypatch):
    phieu = "PHIẾU THÔNG TIN CÔNG DÂN\nHọ và tên: LÊ THỊ HANH\nSố CMND/CCCD/ĐDCN: 001185000007\nNgày, tháng, năm sinh: 05/03/1985"
    _fake_pages(monkeypatch, {"PHIẾU": [{"ho_ten": "LÊ THỊ HANH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                                         "loai_giay": "co_quan_cap", "dong": "Họ và tên: LÊ THỊ HANH"}]})
    case = _case({"BenNu_SoDinhDanh": "125201179"}, [{"name": "phieu.pdf", "text": phieu}])
    findings = [f for f in await dinh_danh.find(dinh_danh.INSPECTOR, case, "thử") if f.unit.key == "nu.so_dinh_danh"]
    assert [(f.values, f.backed) for f in findings] == [({"BenNu_SoDinhDanh": "001185000007"}, True)]


# ───────── Lượt trích: prompt + mapper ─────────
def test_prompt_ket_hon_chi_dung_ten_field_co_trong_schema():
    import re

    from app.pipelines.ket_hon.process import base_prompt
    from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
    from app.pipelines.ket_hon.process.schema import ALLOWED, FIELDS

    prompt = base_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    names = set(re.findall(r"\b(?:BenNam|BenNu|ToKhaiNam|ToKhaiNu|ToKhai|CopyRequest|CccdNam|CccdNu)_[A-Za-z]\w*", prompt))
    assert not sorted(name for name in names if name not in ALLOWED and not name.endswith("_"))
    # Prompt nền trỏ tới khối luật ly hôn: khối đó phải có thật.
    assert "<ly_hon>" in EXTRA_RULES and "</ly_hon>" in EXTRA_RULES


def test_ma_da_ly_hon_theo_van_ban_khong_ghi_ten_ben_do_thi_bo():
    # Quyết định ly hôn của bên nữ với chồng cũ bị gán cả cho bên nam: bên nam không phải đương sự.
    decision = {"BanAnLyHon_So": "12/2020/QĐST-HNGĐ", "BanAnLyHon_Ngay": "03/04/2020",
                "BanAnLyHon_CoQuan": "Tòa án nhân dân huyện Yên Phong", "BanAnLyHon_DuongSu": "Lê Thị Hanh; Phạm Văn Giang",
                "TinhTrangHonNhan": "3"}
    values = {**VALUES, **{f"BenNam_{k}": v for k, v in decision.items()}, **{f"BenNu_{k}": v for k, v in decision.items()}}
    out = {f["name"]: f for f in mapper.enrich(_fields(values), {})}
    assert out["LoaiTinhTrangHonNhan_BenNu"]["value"].startswith("Đã đăng ký kết hôn") and "TTHN_LyHonBenNu" in out
    assert out["LoaiTinhTrangHonNhan_BenNam"]["value"].startswith("Hiện tại chưa đăng ký") and "TTHN_LyHonBenNam" not in out
    assert out["LoaiTinhTrangHonNhan_BenNam"].get("default") is True


# ───────── Địa chỉ: lệch cấp, giấy ghi địa chỉ sau sáp nhập, loại đơn vị ─────────
@pytest.fixture
def old_card_catalog(monkeypatch):
    """Danh mục giả: "Đông Mai" là xã cũ của huyện "Yên Phong"; "Yên Phong" cũng là tên một xã hiện hành."""
    wards = {"dong mai": "Xã Đông Mai", "yen trung": "Phường Yên Trung", "yen phong": "Xã Yên Phong"}

    def area(value, nationality="Việt Nam"):
        return {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "diaChi": str(value.get("diaChi") or ""),
                "xa": wards.get(dia_chi.base._bare(value.get("xa")), str(value.get("xa") or ""))}

    monkeypatch.setattr(dia_chi.mapper, "_area", area)
    monkeypatch.setattr(dia_chi.area_remap, "is_current_area", lambda tinh, xa: xa in wards.values())
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: {"xa": "Xã Đông Mai"} if (
        split.get("xa") == "Đông Mai" and split.get("huyen") == "Yên Phong") else None)


_THE_NU_DUNG_TEN = {"name": "nu.pdf", "text": THE_NU.replace("LÊ THỊ MANH", "LÊ THỊ HANH")}


def test_o_xa_mang_ten_huyen_cua_chinh_dong_the_thi_doi_theo_dong_do(old_card_catalog):
    # Không có tờ khai: xã và chi tiết đang có đều nằm trên dòng thẻ, ô xã là tên HUYỆN của dòng đó.
    shifted = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Yên Phong", "diaChi": "Thôn Hạ Đông Mai"}
    finding = dia_chi.side_finding(_case({"ToKhaiNu_NoiCuTru_TrongNuoc": shifted}, [_THE_NU_DUNG_TEN]), NU)
    assert finding.values["ToKhaiNu_NoiCuTru_TrongNuoc"] == {
        "tinh": "Bắc Ninh", "huyen": "Yên Phong", "xa": "Đông Mai", "diaChi": "Thôn Hạ"}
    # Chi tiết đang có không nằm trên dòng thẻ: địa chỉ đọc từ giấy khác, "Yên Phong" có thể là xã thật → không đổi.
    elsewhere = {**shifted, "diaChi": "Tổ 9"}
    assert dia_chi.side_finding(_case({"ToKhaiNu_NoiCuTru_TrongNuoc": elsewhere}, [_THE_NU_DUNG_TEN]), NU) is None


def test_giay_in_ghi_dia_chi_sau_sap_nhap_cua_chinh_nguoi_do_thang_dia_chi_cu_tren_the(old_card_catalog):
    residence = ("XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ\nHọ, chữ đệm và tên: LÊ THỊ HANH\n"
                 "Nơi thường trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh")
    from_card = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Hạ"}
    case = _case({"ToKhaiNu_NoiCuTru_TrongNuoc": from_card}, [_THE_NU_DUNG_TEN, {"name": "cu-tru.pdf", "text": residence}])
    finding = dia_chi.side_finding(case, NU)
    assert finding.values["ToKhaiNu_NoiCuTru_TrongNuoc"] == {"tinh": "tỉnh Bắc Ninh", "xa": "phường Yên Trung", "diaChi": "Tổ 5"}
    assert any(dia_chi._POST_MERGER_REASON in line for line in finding.evidence)


def _detail_cand(number, detail, printed):
    return {"number": number, "detail": detail, "printed": printed, "new_format": not printed, "trust": 2 if printed else 0}


def test_to_khai_ghi_to_dan_pho_thi_khong_lui_ve_thon_cua_dong_in_cung_ten():
    written, card = _detail_cand(1, "TDP Hạ", False), _detail_cand(2, "Thôn Hạ", True)
    lines = [{"text": "Nơi cư trú: TDP Hạ phường Yên Trung tỉnh Bắc Ninh"}, {"text": "Nơi thường trú: Thôn Hạ"}]
    detail, why, sure = dia_chi._pick_detail(written, [written, card], lines)
    assert (detail, sure) == ("TDP Hạ", True) and "tổ dân phố" in why
    # Cùng loại đơn vị thì vẫn lấy cách viết của dòng in.
    assert dia_chi._pick_detail(_detail_cand(1, "Thôn Ha", False), [_detail_cand(1, "Thôn Ha", False), card], lines)[0] == "Thôn Hạ"


def test_chi_tiet_viet_tay_roi_chu_ma_dong_in_ghi_ten_khac_thi_khong_de_xuat_chi_tiet():
    written, card = _detail_cand(1, "TP Hạ", False), _detail_cand(2, "TDP Trung", True)
    lines = [{"text": "Nơi cư trú: TP Hạ, phường Yên Trung"}, {"text": "Nơi thường trú: TDP Trung"}]
    detail, _, sure = dia_chi._pick_detail(written, [written, card], lines)
    assert (detail, sure) == ("", False)


def test_ten_xa_viet_lien_sau_chi_tiet_co_so_thi_tach_theo_danh_muc(monkeypatch):
    monkeypatch.setattr(dia_chi.area_remap, "canonical_ward", lambda tinh, xa: "Phường Yên Trung" if xa == "Yên Trung" else None)
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: {"xa": "Phường Yên Trung"} if split.get("xa") in (
        "Yên Trung", "Đông Mai") else None)
    split = lambda text: dia_chi.catalog_split({"line": text, "text": text}, Case([], "", {}, {}))
    # Xã hiện hành viết liền sau số nhà / tên đường, các cấp ngăn bằng gạch nối.
    assert split("Nơi cư trú: Thôn 9 - số nhà 12 đường Lê Lợi Yên Trung - Bắc Ninh") == {
        "tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Thôn 9, số nhà 12 đường Lê Lợi"}
    # Xã cũ viết liền sau tổ đánh số, còn đủ huyện và tỉnh.
    assert split("Nơi thường trú: Tổ 3 Đông Mai, TP. Yên Phong, Bắc Ninh") == {
        "tinh": "Bắc Ninh", "huyen": "TP. Yên Phong", "xa": "Đông Mai", "diaChi": "Tổ 3"}
    # Sau chữ chỉ loại là chữ: đó là TÊN tổ dân phố, không tách.
    assert split("Nơi cư trú: TDP Yên Trung - Bắc Ninh") is None


async def test_o_xa_khong_chon_duoc_thi_model_doi_chieu_danh_muc_va_ma_chan_ten_khong_giong(catalog, monkeypatch):
    # Tờ khai viết tắt tên phường bằng chữ cái đầu: ô xã không chọn được, phần ghép không có đề xuất.
    docs = [{"name": "tk.pdf", "text": TO_KHAI.replace("Tổ 5\nphường Yên Trung\ntỉnh Bắc Ninh", "Tổ 5, phường YT, tỉnh Bắc Ninh")}]
    short = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "phường YT", "diaChi": "Tổ 5"}
    monkeypatch.setattr(dia_chi.danh_muc_xa, "wards_of", lambda province: ("Phường Yên Trung", "Xã Đông Mai", "Phường Yên Phong"))
    asked = []

    def model(answer):
        async def chat(messages, **kwargs):
            asked.append(messages[-1]["content"])
            return json.dumps({"muc": [{"so": 1, "xa": answer}]}, ensure_ascii=False)
        monkeypatch.setattr(client, "chat", chat)

    model("Phường Yên Trung")
    nam = lambda findings: [finding for finding in findings if finding.unit.key == "nam.noi_cu_tru"]
    [finding] = nam(await dia_chi.find(dia_chi.INSPECTOR, _case({"ToKhaiNam_NoiCuTru_TrongNuoc": short}, docs), "thử"))
    assert finding.backed
    assert finding.values["ToKhaiNam_NoiCuTru_TrongNuoc"] == {"tinh": "Bắc Ninh", "xa": "Phường Yên Trung", "diaChi": "Tổ 5"}
    assert "Danh sách Bắc Ninh: Phường Yên Trung; Xã Đông Mai; Phường Yên Phong" in asked[0] and "phường YT" in asked[0]
    # Model trả một tên có trong danh sách nhưng không giống chữ trên giấy → mã bỏ.
    model("Xã Đông Mai")
    assert nam(await dia_chi.find(dia_chi.INSPECTOR, _case({"ToKhaiNam_NoiCuTru_TrongNuoc": short}, docs), "thử")) == []


async def test_doi_chieu_danh_muc_dua_danh_sach_tinh_cua_ca_hai_ben(monkeypatch):
    # Bên nam ghi tỉnh của bên nữ; tên phường viết tắt chỉ giống một tên của tỉnh còn lại → nhận kèm tỉnh đó.
    lists = {"Bắc Ninh": ("Phường Yên Trung", "Xã Đông Mai"), "Lạng Sơn": ("Xã Văn Quan", "Xã Tân Đoàn")}
    monkeypatch.setattr(dia_chi.danh_muc_xa, "wards_of", lambda province: lists.get(province, ()))
    monkeypatch.setattr(dia_chi.mapper, "_area", lambda value, nationality="Việt Nam": {
        "quocGia": "Việt Nam", "tinh": str(value.get("tinh") or ""), "xa": str(value.get("xa") or ""),
        "diaChi": str(value.get("diaChi") or "")})
    monkeypatch.setattr(dia_chi.area_remap, "is_current_area", lambda tinh, xa: xa in lists.get(tinh, ()))
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: None)
    monkeypatch.setattr(dia_chi, "side_finding", lambda case, side: None)
    docs = [{"name": "tk.pdf", "text": TO_KHAI.replace("Tổ 5\nphường Yên Trung\ntỉnh Bắc Ninh", "Tổ 5, phường YT, tỉnh Lạng Sơn")}]
    asked = []

    async def chat(messages, **kwargs):
        asked.append(messages[-1]["content"])
        return json.dumps({"muc": [{"so": 1, "tinh": "Bắc Ninh", "xa": "Phường Yên Trung"}]}, ensure_ascii=False)
    monkeypatch.setattr(client, "chat", chat)
    values = {"ToKhaiNam_NoiCuTru_TrongNuoc": {"tinh": "Lạng Sơn", "xa": "phường YT", "diaChi": "Tổ 5"},
              "ToKhaiNu_NoiCuTru_TrongNuoc": {"tinh": "Bắc Ninh", "xa": "Xã Đông Mai", "diaChi": "Thôn Hạ"}}
    [finding] = await dia_chi.find(dia_chi.INSPECTOR, _case(values, docs), "thử")
    assert finding.values["ToKhaiNam_NoiCuTru_TrongNuoc"] == {"tinh": "Bắc Ninh", "xa": "Phường Yên Trung", "diaChi": "Tổ 5"}
    assert asked[0].count("Danh sách Lạng Sơn:") == 1 and asked[0].count("Danh sách Bắc Ninh:") == 1


def test_chot_chan_ten_xa_chi_nhan_ten_duy_nhat_giong_nhat(monkeypatch):
    monkeypatch.setattr(dia_chi.danh_muc_xa, "wards_of", lambda province: ("Phường Yên Trung", "Phường Yên Trang", "Xã Hòa Đình", "Xã Mỹ Đình"))
    match = dia_chi.danh_muc_xa.only_match
    assert match("Yen Trung", "x", "Phường Yên Trung") == "Phường Yên Trung"   # trùng khi bỏ dấu thắng tên chỉ na ná
    assert match("Đình", "x", "Xã Mỹ Đình") == ""                              # OCR cắt chữ, hai tên cùng đuôi
    assert match("Yên Trung", "x", "Phường Yên Bái") == ""                     # tên không có trong danh sách


def test_dong_hktt_chung_duoi_cap_duong_su_la_noi_thuong_tru_cua_ben_do(catalog):
    decision = ("TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG\nNguyên đơn: Chị Lê Thị Hanh, sinh năm 1985.\n"
                "Bị đơn: Anh Vũ Văn Ba, sinh năm 1983.\nHKTT: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh.")
    case = _case(docs=[{"name": "qd.pdf", "text": decision}])
    [line] = dia_chi._shared_home_lines(case, chu_the.identity(case.values, NU))
    assert line["text"] == "Nơi thường trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh" and not line["handwritten"]
    # Bên không phải đương sự của văn bản; hoặc dòng HKTT không đứng ngay dưới cặp đương sự → không lấy.
    assert dia_chi._shared_home_lines(case, chu_the.identity(case.values, NAM)) == []
    lone = _case(docs=[{"name": "qd.pdf", "text": decision.replace("Bị đơn: Anh Vũ Văn Ba, sinh năm 1983.\n", "")}])
    assert dia_chi._shared_home_lines(lone, chu_the.identity(lone.values, NU)) == []


def test_bang_to_khai_co_cot_trong_thua_lay_o_theo_tieu_de_hang_lech_cot_thi_bo():
    text = ("| Thông tin | | Bên nữ | Bên nam |\n|---|---|---|\n| Nơi cư trú (4) | | Xã A, tỉnh B | Tổ 5, phường C |\n"
            "| Ngày, tháng, năm sinh | 01/02/1990 | | 03/04/1991 |")
    [table] = chu_the.declaration_tables([{"text": text}])
    assert chu_the.cell(table, "cu_tru", NU)[0] == "Xã A, tỉnh B" and chu_the.cell(table, "cu_tru", NAM)[0] == "Tổ 5, phường C"
    assert "ngay_sinh" not in table["rows"]  # cột thừa có chữ: không đoán ô nào của ai


def test_dong_noi_thuong_tru_duoi_dong_duong_su_la_cua_ben_do():
    decision = ("TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG\n- Nguyên đơn: Bà Lê Thị Hanh, sinh năm 1985\n"
                "Nơi thường trú: Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh\n- Bị đơn: Ông Trần Văn Em, sinh năm 1980\n"
                "Nơi thường trú và cư trú: Số 9, Tổ 5, phường Yên Trung, tỉnh Bắc Ninh")
    case = _case(docs=[{"name": "qd.pdf", "text": decision}])
    [line] = dia_chi._party_home_lines(case, chu_the.identity(case.values, NAM))
    assert line["text"] == "Nơi thường trú: Số 9, Tổ 5, phường Yên Trung, tỉnh Bắc Ninh" and not line["handwritten"]
    [line] = dia_chi._party_home_lines(case, chu_the.identity(case.values, NU))
    assert line["text"] == "Nơi thường trú: Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh"


def test_hai_ben_khai_cung_noi_cu_tru_thi_dong_in_cua_ben_kia_dung_chung():
    text = TO_KHAI.replace("Tổ 5\nphường Yên Trung\ntỉnh Bắc Ninh", "Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh")
    case = _case(docs=[{"name": "tk.pdf", "text": text}, {"name": "nu.pdf", "text": THE_NU}])
    lines = dia_chi._shared_residence_lines(case, NAM, chu_the.identity(case.values, NAM))
    assert [line["text"] for line in lines] == ["Nơi thường trú / Place of residence: Thôn Hạ Đông Mai, Yên Phong, Bắc Ninh"]
    assert dia_chi._shared_residence_lines(_case(), NAM, chu_the.identity(_case().values, NAM)) == []


def test_o_to_khai_viet_tren_dong_cham_thi_bo_cham():
    text = TO_KHAI.replace("Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh |", "Thôn Hạ... xã... Đông... Mai... tỉnh Bắc Ninh.... |")
    [line] = dia_chi._table_lines(_case(docs=[{"name": "tk.pdf", "text": text}]), NU, "Lê Thị Hanh")
    assert line["text"] == "Nơi cư trú: Thôn Hạ xã Đông Mai tỉnh Bắc Ninh"


def test_a_lay_chi_tiet_dong_the_cu_doi_chu_loai_thi_theo_o_to_khai_cung_xa(old_card_catalog):
    # Ô tờ khai ghi nơi cư trú hiện tại (ba cấp, chi tiết khác); A lấy chi tiết của dòng thẻ in địa chỉ cũ, đổi chữ loại.
    text = TO_KHAI.replace("Thôn Hạ, xã Đông Mai, tỉnh Bắc Ninh |", "TDP Sơn, xã Đông Mai, tỉnh Bắc Ninh |")
    case = _case({"ToKhaiNu_NoiCuTru_TrongNuoc": {"tinh": "Bắc Ninh", "xa": "Xã Đông Mai", "diaChi": "Khu Hạ"}},
                 [{"name": "tk.pdf", "text": text}, _THE_NU_DUNG_TEN])
    finding = dia_chi.side_finding(case, NU)
    assert finding.values["ToKhaiNu_NoiCuTru_TrongNuoc"]["diaChi"] == "TDP Sơn"
