"""Thanh tra + điền đợt 2 của liên thông khai sinh (tên, số giả)."""

import asyncio

from app.pipelines._shared.thanh_tra import ten_xa as base_ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.khai_sinh_lien_thong import thanh_tra
from app.pipelines.khai_sinh_lien_thong.thanh_tra import dia_chi, dinh_danh, giay_to, trang
from app.procedures.registry import get_procedure
from app.second_pass import service

_GCS = """SỞ Y TẾ TỈNH A
BỆNH VIỆN ĐA KHOA TỈNH A
GIẤY CHỨNG SINH
Họ, chữ đệm, tên khai sinh của mẹ: PHÙNG THỊ MẨY
Nơi đăng ký thường trú: Bản B, xã C"""
_TO_KHAI = """TỜ KHAI ĐĂNG KÝ KHAI SINH
Họ, chữ đệm, tên người mẹ: Phùng Thị Mấy"""


def test_registry_bat_dot_hai_form_angular():
    proc = get_procedure("khai-sinh-dang-ky")
    assert proc["secondPass"] == "angular"
    assert service.capability(proc) == "secondPassAngular"
    assert [i.key for i in thanh_tra.INSPECTORS] == ["dinh_danh", "dia_chi", "giay_to"]


def test_ten_me_theo_giay_chung_sinh_in_thang_to_khai():
    docs = [{"name": "gcs.pdf", "text": _GCS}, {"name": "tk.pdf", "text": _TO_KHAI}]
    me = next(p for p in dinh_danh.PERSONS if p.key == "me")
    finding = dinh_danh.name_finding(me, {"ThongTinMe_HoTen": "Phùng Thị Mấy"}, trang.pages(docs))
    assert finding and finding.values == {"ThongTinMe_HoTen": "PHÙNG THỊ MẨY"}


def test_doi_dau_chi_dua_vao_dong_ten_tren_the_thi_khong_doi():
    card = "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: LÊ VĂN TƯỜNG\nSố / No.: 001090000001"
    docs = [{"name": "cccd.pdf", "text": card}, {"name": "tk.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI SINH\nCha: Lê Văn Tưởng"}]
    cha = next(p for p in dinh_danh.PERSONS if p.key == "cha")
    assert dinh_danh.name_finding(cha, {"ThongTinBo_HoTen": "Lê Văn Tưởng"}, trang.pages(docs)) is None


def test_chu_ho_khong_lay_the_cua_cha_trung_chu():
    mrz = "IDVNM0940000017001094000001<<8\n9401011M3401011VNM<<<<<<<<<<<6\nLE<<VAN<CHINH<<<<<<<<<<<<<<<<<"
    docs = [{"name": "cccd.pdf", "text": f"CĂN CƯỚC CÔNG DÂN\n{mrz}"}]
    values = {"Ct01_ChuHoHoTen": "Lê Văn Chinh", "Ct01_ChuHoSoDinhDanh": "001068000002",
              "ThongTinBo_HoTen": "Lê Văn Chính", "ThongTinBo_SoDinhDanh": "001094000001"}
    chu_ho = next(p for p in dinh_danh.PERSONS if p.key == "chu_ho")
    assert dinh_danh.card_findings(chu_ho, values, docs) == []


def test_so_dinh_danh_cmnd_9_so_doi_theo_mrz_the_cua_chinh_nguoi_do():
    mrz = "IDVNM0940000017001094000001<<8\n9401011M3401011VNM<<<<<<<<<<<6\nLE<<VAN<AN<<<<<<<<<<<<<<<<<<<"
    docs = [{"name": "cccd.pdf", "text": f"CĂN CƯỚC CÔNG DÂN\n{mrz}"}]
    cha = next(p for p in dinh_danh.PERSONS if p.key == "cha")
    out = dinh_danh.card_findings(cha, {"ThongTinBo_HoTen": "Lê Văn An", "ThongTinBo_SoDinhDanh": "123456789"}, docs)
    assert [f.values for f in out if "ThongTinBo_SoDinhDanh" in f.values] == [{"ThongTinBo_SoDinhDanh": "001094000001"}]


def test_ten_xa_khong_lay_ten_huyen_hay_ten_benh_vien():
    slot = dia_chi.SLOTS["Gcs_NoiSinh"][0]
    blank = {"tinh": "Lai Châu", "xa": "", "diaChi": "Bệnh viện đa khoa Tân Uyên"}
    assert not base_ten_xa._grounded(slot, blank, "Tại: BỆNH VIỆN ĐA KHOA TÂN UYÊN", "Xã Tân Uyên")
    assert base_ten_xa._grounded(slot, blank, "Bệnh viện đa khoa Tân Uyên, xã Tân Uyên, tỉnh Lai Châu", "Xã Tân Uyên")
    mother = dia_chi.SLOTS["ThongTinMe_NoiCuTru"][0]
    value = {"tinh": "Cao Bằng", "xa": "", "diaChi": "Bản Hà"}
    assert not base_ten_xa._grounded(mother, value, "Bản Hà, Xã Ngọc Đào, Huyện Hà Quảng", "Xã Hà Quảng")
    # Dòng "Kính gửi" không làm căn cứ cho nơi sinh khi tên đọc được không gần.
    birth = {"tinh": "Lâm Đồng", "xa": "Lay Giang", "diaChi": ""}
    assert not base_ten_xa._grounded(slot, birth, "Kính gửi: UBND Phường Xuân Hương", "Phường Xuân Hương - Đà Lạt")


def test_giay_ket_hon_chi_doc_khi_ho_so_co_giay_ket_hon(monkeypatch):
    called = []

    async def fake(inspector, case, title):
        called.append(1)
        return []
    monkeypatch.setattr(giay_to.engine, "llm_findings", fake)
    asyncio.run(giay_to.find(giay_to.INSPECTOR, Case([{"name": "a", "text": _GCS}], "", {}, {}), ""))
    assert not called
    gcn = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY CHỨNG NHẬN KẾT HÔN\nSố: 12/2020"
    asyncio.run(giay_to.find(giay_to.INSPECTOR, Case([{"name": "a", "text": gcn}], "", {}, {}), ""))
    assert called


def test_me_theo_khoi_nguoi_me_tren_giay_chung_sinh():
    gcs = ("SỞ Y TẾ TỈNH A\nBệnh viện A\nGIẤY CHỨNG SINH\nHọ, chữ đệm, tên khai sinh của mẹ: LÊ THỊ HOA Dân tộc: Kinh\n"
           "Ngày, tháng, năm sinh: 02/03/1991\nSố ĐDCN/Hộ chiếu: 001191000123")
    tk = "TỜ KHAI ĐĂNG KÝ KHAI SINH\nHọ, chữ đệm, tên người mẹ: Lê Thị Hòe\nNăm sinh: 02/03/1997"
    docs = [{"name": "gcs.pdf", "text": gcs}, {"name": "tk.pdf", "text": tk}]
    values = {"ThongTinMe_HoTen": "Lê Thị Hòe", "ThongTinMe_SoDinhDanh": "0011910001233",
              "ThongTinMe_NgaySinh": "02/03/1997"}
    out = [f.values for f in dinh_danh.findings_from(Case(docs, "", values, {}))]
    assert {"ThongTinMe_HoTen": "LÊ THỊ HOA"} in out  # khác chữ cái; tên dừng ở nhãn "Dân tộc" cùng dòng
    assert {"ThongTinMe_SoDinhDanh": "001191000123"} in out
    assert {"ThongTinMe_NgaySinh": "02/03/1991"} in out
    # Giấy chứng sinh của người khác (số, tên, ngày sinh đều xa) → không đụng.
    far = {"ThongTinMe_HoTen": "Trần Thị Mai", "ThongTinMe_SoDinhDanh": "079190000999", "ThongTinMe_NgaySinh": "05/06/1985"}
    assert not [f for f in dinh_danh.findings_from(Case(docs, "", far, {})) if "ThongTinMe_HoTen" in f.values]


_THE_CHA = """CĂN CƯỚC
IDENTITY CARD
Nơi cư trú / Place of residence: Khu Phố Kha Lại
Phường D, Tỉnh A"""
_GCS_ME = """SỞ Y TẾ TỈNH A
GIẤY CHỨNG SINH
Nơi cư trú: TDP Kha Lại, Phường D, Tỉnh A"""
_KET_HON = """GIẤY CHỨNG NHẬN KẾT HÔN
Nơi cư trú: Thôn E, xã F, tỉnh G Nơi cư trú: Tổ dân phố Khà Lại, phường D, tỉnh A"""


def test_ten_thon_cua_cha_theo_cach_viet_nhieu_trang_giay_hon():
    pages = trang.pages([{"text": _THE_CHA}, {"text": _GCS_ME}, {"text": _KET_HON}])
    fix = dia_chi.detail_fix("Tổ dân phố Khà Lại", pages)
    assert fix and fix["diaChi"] == "Tổ dân phố Kha Lại"
    # Cách viết của lượt trích có trên nhiều trang hơn → giữ.
    assert dia_chi.detail_fix("TDP Kha Lại", pages) is None


def test_ten_thon_khong_lay_ten_xa_dung_sau_dau_phay_hay_ten_lech_hai_chu():
    pages = trang.pages([{"text": "CĂN CƯỚC\nNơi cư trú: Phường Kha Hồ, Tỉnh A"},
                         {"text": "GIẤY CHỨNG SINH\nNơi cư trú: TDP 5, Phường Kha Hồ, Tỉnh A"}])
    assert dia_chi.detail_fix("TDP Khu Hồ", pages) is None
    pages = trang.pages([{"text": "CĂN CƯỚC\nNơi cư trú: Thôn Yên Lâm"}, {"text": "GIẤY CHỨNG SINH\nNơi cư trú: Thôn Yên Lâm"}])
    assert dia_chi.detail_fix("Thôn Yên Hồng", pages) is None
    # "Hòa" / "Hoà" chỉ khác kiểu bỏ dấu.
    pages = trang.pages([{"text": "CĂN CƯỚC\nNơi cư trú: Tdp Thanh Hoà"}, {"text": "GIẤY CHỨNG SINH\nNơi cư trú: Tdp Thanh Hoà"}])
    assert dia_chi.detail_fix("TDP Thanh Hòa", pages) is None
