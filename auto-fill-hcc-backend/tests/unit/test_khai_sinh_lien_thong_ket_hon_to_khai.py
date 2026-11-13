"""Khai sinh liên thông: thông tin giấy chứng nhận kết hôn chép trên dòng in sẵn của TỜ KHAI (hồ sơ không kèm giấy
kết hôn thật) vẫn phải điền; giấy kết hôn thật thì thắng tờ khai."""
import pytest

from app.pipelines.khai_sinh_lien_thong.process.mapper import _QUOC_TICH_ALIASES, _foreign_nationality, enrich
from app.pipelines.khai_sinh_lien_thong.process.schema import QUOC_TICH_QUOC_GIA


def _gcn(values: dict) -> dict:
    out = enrich([{"name": k, "value": v} for k, v in values.items()])
    return {f["name"]: f.get("value") for f in out if f["name"].startswith("GiayCNKH")}


def test_chi_co_dong_to_khai_van_dien_bo_dau_cham():
    out = _gcn({"Tk_GcnKetHon_So": "49...", "Tk_GcnKetHon_QuyenSo": "....", "Tk_GcnKetHon_NgayCap": "24/06/2023",
                "Tk_GcnKetHon_NoiCap": "UBND xã A"})
    assert out == {"GiayCNKHSo": "49", "GiayCNKHNgayCap": "24/06/2023", "GiayCNKHNoiCap": "UBND xã A"}


def test_giay_ket_hon_that_thang_to_khai_to_khai_bu_o_thieu():
    out = _gcn({"GcnKetHon_So": "12", "GcnKetHon_NgayCap": "01/02/2020", "Tk_GcnKetHon_So": "21",
                "Tk_GcnKetHon_NoiCap": "UBND xã B"})
    assert out == {"GiayCNKHSo": "12", "GiayCNKHNgayCap": "01/02/2020", "GiayCNKHNoiCap": "UBND xã B"}


def _by_name(values: dict) -> dict:
    return {f["name"]: f.get("value") for f in enrich([{"name": k, "value": v} for k, v in values.items()])}


# ── Trích lục kết hôn (bản sao) thay giấy chứng nhận kết hôn ──
# Số "…/TLKH-BS" và ngày ký dưới quốc hiệu là của bản trích lục; số/ngày đăng ký kết hôn nằm dưới "Đăng ký kết hôn tại".
_OCR_TRICH_LUC = """===== hoso.pdf (tiengnoi) =====
───── Trang 2/3 ─────
TỜ KHAI ĐĂNG KÝ KHAI SINH
Thông tin về Giấy chứng nhận kết hôn của cha, mẹ trẻ (nếu cha, mẹ trẻ đã ĐKKH):
Số: 40..., Quyền số: ..., đăng ký ngày 05 tháng 08 năm 2014 tại Xã A
───── Trang 3/3 ─────
UBND XÃ A
Số:40/2024/TLKH-BS
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Xã A, ngày 20 tháng 09 năm 2024
TRÍCH LỤC KẾT HÔN
(BẢN SAO)
Họ, chữ đệm, tên vợ:
TRẦN THỊ MAI
Giấy tờ tùy thân: Thẻ căn cước số
001190000001, Bộ Công an cấp ngày
01/02/2021
Đăng ký kết hôn tại: Ủy ban nhân dân xã A, tỉnh B
Số: 25/2024 ngày 05 tháng 03 năm 2024
Ghi chú:
Họ, chữ đệm, tên chồng:
NGUYỄN VĂN AN
"""
# LLM bỏ qua trích lục, chỉ trả dòng tờ khai mà OCR đọc sai tháng/năm.
_LLM_CHI_CO_TO_KHAI = {"Tk_GcnKetHon_So": "40", "Tk_GcnKetHon_NgayCap": "05/08/2014", "Tk_GcnKetHon_NoiCap": "Xã A"}


def _gcn_ocr(values: dict, ocr_text: str) -> dict:
    out = enrich([{"name": k, "value": v} for k, v in values.items()], ocr_text=ocr_text)
    return {f["name"]: f.get("value") for f in out if f["name"].startswith("GiayCNKH")}


def test_trich_luc_ket_hon_thang_dong_to_khai_ocr_doc_sai():
    out = _gcn_ocr(_LLM_CHI_CO_TO_KHAI, _OCR_TRICH_LUC)
    assert out == {"GiayCNKHSo": "25/2024", "GiayCNKHNgayCap": "05/03/2024",
                   "GiayCNKHNoiCap": "Ủy ban nhân dân xã A, tỉnh B"}


def test_trich_luc_khong_lay_so_va_ngay_cua_ban_trich_luc():
    # Thiếu dòng "Số: … ngày …" dưới nơi đăng ký → không vớ "40/2024/TLKH-BS" hay ngày ký 20/09/2024; tờ khai bù.
    ocr = _OCR_TRICH_LUC.replace("Số: 25/2024 ngày 05 tháng 03 năm 2024\n", "")
    out = _gcn_ocr(_LLM_CHI_CO_TO_KHAI, ocr)
    assert out == {"GiayCNKHSo": "40", "GiayCNKHNgayCap": "05/08/2014",
                   "GiayCNKHNoiCap": "Ủy ban nhân dân xã A, tỉnh B"}


def test_trich_luc_ngay_dang_ky_viet_so_va_co_quyen_so():
    ocr = _OCR_TRICH_LUC.replace("Số: 25/2024 ngày 05 tháng 03 năm 2024",
                                 "Số: 25/2024, Quyển số: 01/2024, ngày 5/3/2024")
    out = _gcn_ocr({}, ocr)
    assert out == {"GiayCNKHSo": "25/2024", "GiayCNKHQuyenSo": "01/2024", "GiayCNKHNgayCap": "05/03/2024",
                   "GiayCNKHNoiCap": "Ủy ban nhân dân xã A, tỉnh B"}


def test_trich_luc_mau_so_dang_ky_khong_co_dau_hai_cham():
    # Trích lục từ sổ cũ: "Đăng ký kết hôn tại UBND …" / "Số 25/2024 ngày …", số bản trích lục đuôi TLHT.
    ocr = (_OCR_TRICH_LUC.replace("Số:40/2024/TLKH-BS", "Số: 40/2024/TLHT-BS")
           .replace("Đăng ký kết hôn tại: Ủy ban nhân dân xã A, tỉnh B", "Đăng ký kết hôn tại UBND Xã A, Huyện C, Tỉnh B")
           .replace("Số: 25/2024 ngày", "Số 25/2024 ngày"))
    out = _gcn_ocr(_LLM_CHI_CO_TO_KHAI, ocr)
    assert out == {"GiayCNKHSo": "25/2024", "GiayCNKHNgayCap": "05/03/2024",
                   "GiayCNKHNoiCap": "UBND Xã A, Huyện C, Tỉnh B"}
    assert _gcn({"GcnKetHon_So": "40/2024/TLHT-BS", "Tk_GcnKetHon_So": "25"}) == {"GiayCNKHSo": "25"}


def test_trich_luc_khong_vo_so_va_ngay_cap_cccd_cua_khoi_chong_ngay_duoi():
    # OCR hai cột đẩy khối chồng lên ngay dưới nơi đăng ký, dòng "Số … ngày …" bị mất.
    ocr = _OCR_TRICH_LUC.replace(
        "Số: 25/2024 ngày 05 tháng 03 năm 2024",
        "Giấy tờ tùy thân: Thẻ căn cước công dân số 001085000001, Bộ Công an cấp ngày 01/02/2021")
    out = _gcn_ocr(_LLM_CHI_CO_TO_KHAI, ocr)
    assert out == {"GiayCNKHSo": "40", "GiayCNKHNgayCap": "05/08/2014",
                   "GiayCNKHNoiCap": "Ủy ban nhân dân xã A, tỉnh B"}


def test_llm_lay_so_ban_trich_luc_thi_bo_dung_so_to_khai():
    out = _gcn({"GcnKetHon_So": "40/2024/TLKH-BS", "Tk_GcnKetHon_So": "25"})
    assert out == {"GiayCNKHSo": "25"}


def test_khong_co_trich_luc_giu_nguyen_giay_ket_hon_llm_tra():
    out = _gcn_ocr({"GcnKetHon_So": "12", "GcnKetHon_NgayCap": "01/02/2020", **_LLM_CHI_CO_TO_KHAI},
                   _OCR_CHONG_NUOC_NGOAI)
    assert out == {"GiayCNKHSo": "12", "GiayCNKHNgayCap": "01/02/2020", "GiayCNKHNoiCap": "Xã A"}


def test_me_chi_co_nam_sinh_lay_ngay_day_du_tu_giay_ket_hon_khi_trung_ten():
    out = _by_name({"ThongTinMe_HoTen": "TRẦN THỊ MAI", "ThongTinMe_SoDinhDanh": "001190000001",
                    "ThongTinMe_NgaySinh": "1990", "GcnKetHon_Vo_HoTen": "Trần Thị Mai",
                    "GcnKetHon_Vo_NgaySinh": "07/05/1990", "GcnKetHon_Vo_SoGiayTo": "123456789"})
    assert out["MeNgaySinh"] == "07/05/1990"
    assert out["MeSoGiayTo"] == "001190000001"


def test_bu_thong_tin_me_khi_trung_so_giay_to_khong_ghi_de_nguon_uu_tien():
    out = _by_name({"ThongTinMe_HoTen": "LÊ THU HÀ", "ThongTinMe_SoDinhDanh": "001190000002",
                    "ThongTinMe_DanToc": "Tày", "GcnKetHon_Vo_HoTen": "Lê Thu Hằng",
                    "GcnKetHon_Vo_SoGiayTo": "001190000002", "GcnKetHon_Vo_NgaySinh": "01/02/1991",
                    "GcnKetHon_Vo_DanToc": "Kinh"})
    assert out["MeNgaySinh"] == "01/02/1991"
    assert out["MeMaDanToc"] == "Tày"


def test_khong_bu_khi_ben_vo_tren_giay_ket_hon_la_nguoi_khac():
    out = _by_name({"ThongTinMe_HoTen": "PHẠM THỊ LAN", "ThongTinMe_NgaySinh": "1992",
                    "GcnKetHon_Vo_HoTen": "Đỗ Thị Hoa", "GcnKetHon_Vo_NgaySinh": "03/04/1992"})
    assert out["MeNgaySinh"] == "1992"


def test_nam_sinh_lech_thi_giu_giay_chung_sinh():
    out = _by_name({"ThongTinMe_HoTen": "PHẠM THỊ LAN", "ThongTinMe_NgaySinh": "1992",
                    "GcnKetHon_Vo_HoTen": "Phạm Thị Lan", "GcnKetHon_Vo_NgaySinh": "03/04/1993"})
    assert out["MeNgaySinh"] == "1992"


def test_ten_benh_vien_in_hoa_viet_lai_theo_quy_tac():
    out = _by_name({"Gcs_HoTenCon": "VŨ AN", "Gcs_NoiSinh": {
        "tinh": "Bắc Ninh", "diaChi": "BỆNH VIỆN SẢN - NHI BẮC NINH SỐ 2 TỈNH BẮC NINH"}})
    assert out["NsDiaChi"]["diaChi"] == "Bệnh viện Sản - Nhi Bắc Ninh số 2"


def test_ten_benh_vien_tuyen_tinh_in_hoa_giu_ten_tinh():
    out = _by_name({"Gcs_HoTenCon": "VŨ AN", "Gcs_NoiSinh": {
        "tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "BỆNH VIỆN ĐA KHOA TỈNH LAI CHÂU"}})
    assert out["NsDiaChi"]["diaChi"] == "Bệnh viện đa khoa tỉnh Lai Châu"


def test_ten_benh_vien_da_viet_thuong_giu_nguyen():
    out = _by_name({"Gcs_HoTenCon": "VŨ AN", "Gcs_NoiSinh": {
        "tinh": "Hà Nội", "xa": "Hai Bà Trưng", "diaChi": "Bệnh viện Phụ sản Hà Nội"}})
    assert out["NsDiaChi"]["diaChi"] == "Bệnh viện Phụ sản Hà Nội"


def test_me_khong_co_noi_cu_tru_lay_dong_thuong_tru_tren_giay_chung_sinh():
    out = _by_name({"ThongTinMe_HoTen": "TRẦN THỊ MAI", "Gcs_NoiThuongTruMe": {
        "tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Thôn A"}})
    assert out["MeDiaChi"]["diaChi"] == "Thôn A"
    assert out["MeDiaChi"]["tinh"] == "Bắc Ninh"


def test_noi_cu_tru_me_van_uu_tien_nguon_khac_truoc_giay_chung_sinh():
    out = _by_name({"ThongTinMe_HoTen": "TRẦN THỊ MAI",
                    "ThongTinMe_NoiCuTru": {"tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Thôn B"},
                    "Gcs_NoiThuongTruMe": {"tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Thôn A"}})
    assert out["MeDiaChi"]["diaChi"] == "Thôn B"


def test_khong_co_cccd_cha_lay_cha_tu_ben_chong_tren_giay_ket_hon():
    out = _by_name({"ThongTinMe_HoTen": "TRẦN THỊ MAI", "ThongTinMe_SoDinhDanh": "001190000001",
                    "GcnKetHon_Vo_HoTen": "TRẦN THỊ MAI", "GcnKetHon_Chong_HoTen": "Nguyễn Văn An",
                    "GcnKetHon_Chong_NgaySinh": "06/02/1985", "GcnKetHon_Chong_SoGiayTo": "33A012345678",
                    "GcnKetHon_Chong_DanToc": "Kinh"})
    assert out["ChaHoTen"] == "NGUYỄN VĂN AN"
    assert out["ChaNgaySinh"] == "06/02/1985"
    assert out["ChaMaDanToc"] == "Kinh"
    # Chưa có số định danh → điền số chứng minh quân đội, giữ chữ cái.
    assert out["ChaSoGiayTo"] == "33A012345678"
    assert out["NycQuanHe"]["chaTen"] == "NGUYỄN VĂN AN"


def test_khong_co_cccd_cha_dien_so_cmnd_9_so_tren_giay_ket_hon():
    out = _by_name({"GcnKetHon_Chong_HoTen": "Nguyễn Văn An", "GcnKetHon_Chong_SoGiayTo": "123 456 789"})
    assert out["ChaSoGiayTo"] == "123456789"


def test_da_co_so_dinh_danh_cha_khong_bi_so_tren_giay_ket_hon_de():
    out = _by_name({"ThongTinBo_HoTen": "NGUYỄN VĂN AN", "ThongTinBo_SoDinhDanh": "001085000001",
                    "GcnKetHon_Chong_HoTen": "Nguyễn Văn An", "GcnKetHon_Chong_SoGiayTo": "33A012345678"})
    assert out["ChaSoGiayTo"] == "001085000001"


def test_khong_co_thong_tin_me_lay_me_tu_ben_vo_tren_giay_ket_hon():
    out = _by_name({"ThongTinBo_HoTen": "NGUYỄN VĂN AN", "GcnKetHon_Chong_HoTen": "NGUYỄN VĂN AN",
                    "GcnKetHon_Vo_HoTen": "Trần Thị Mai", "GcnKetHon_Vo_NgaySinh": "07/05/1990",
                    "GcnKetHon_Vo_SoGiayTo": "001190000001"})
    assert (out["MeHo"], out["MeChuDem"], out["MeTen"]) == ("TRẦN", "THỊ", "MAI")
    assert out["MeNgaySinh"] == "07/05/1990"
    assert out["MeSoGiayTo"] == "001190000001"


def test_cha_da_co_tu_nguon_khac_ma_khac_ten_thi_khong_lay_ben_chong():
    out = _by_name({"ThongTinBo_HoTen": "LÊ VĂN BÌNH", "GcnKetHon_Chong_HoTen": "Nguyễn Văn An",
                    "GcnKetHon_Chong_NgaySinh": "06/02/1985"})
    assert out["ChaHoTen"] == "LÊ VĂN BÌNH"
    assert "ChaNgaySinh" not in out


# ── Cha/mẹ là người nước ngoài ──
# OCR giấy kết hôn hai cột: mỗi dòng gộp cả hai bên, cột đầu là vợ.
_OCR_CHONG_NUOC_NGOAI = """===== Kết hôn.pdf (tiengnoi) =====
Số: 12/2026
GIẤY CHỨNG NHẬN KẾT HÔN
Họ, chữ đệm, tên vợ: Họ, chữ đệm, tên chồng:
TRẦN THỊ MAI TRAN JOHN
Ngày, tháng, năm sinh: 07/05/1990 Ngày, tháng, năm sinh: 06/02/1985
Dân tộc: Kinh Dân tộc: Kinh
Quốc tịch: Việt Nam Quốc tịch: Canada
Nơi cư trú: 1 Đường A, phường B, tỉnh C Nơi cư trú: Unit 9, 100 Sample Road, Toronto, Ontario, Ca-na-đa (Canadian)
Giấy tờ tùy thân: Thẻ căn cước công dân số 001190000001, Cục CS QLHC về trật tự xã hội cấp ngày 01/02/2021 Giấy tờ tùy thân: Hộ chiếu số X1234567, Cơ quan có thẩm quyền của Canada cấp ngày 03/04/2025
Nơi đăng ký kết hôn: Ủy ban nhân dân phường B, tỉnh C
"""
_LLM_BO_SOT_QUOC_TICH = {"ThongTinMe_HoTen": "Trần Thị Mai", "ThongTinMe_SoDinhDanh": "001190000001",
                         "ThongTinMe_DanToc": "Kinh", "ThongTinMe_NoiCuTru": {"tinh": "Khánh Hòa", "xa": "Nha Trang"},
                         "GcnKetHon_So": "12/2026", "GcnKetHon_Vo_HoTen": "TRẦN THỊ MAI",
                         "GcnKetHon_Vo_SoGiayTo": "001190000001", "GcnKetHon_Chong_HoTen": "TRAN JOHN",
                         "GcnKetHon_Chong_NgaySinh": "06/02/1985", "GcnKetHon_Chong_SoGiayTo": "X1234567",
                         "GcnKetHon_Chong_DanToc": "Kinh"}


def _enrich_ocr(values: dict, ocr_text: str) -> list[dict]:
    return enrich([{"name": k, "value": v} for k, v in values.items()], ocr_text=ocr_text)


def _values(fields: list[dict]) -> dict:
    return {f["name"]: f.get("value") for f in fields}


def test_llm_bo_sot_quoc_tich_van_doc_duoc_cha_nguoi_nuoc_ngoai_tu_ocr_giay_ket_hon():
    out = _values(_enrich_ocr(_LLM_BO_SOT_QUOC_TICH, _OCR_CHONG_NUOC_NGOAI))
    assert out["ChaMaQuocTich"] == "Ca-na-đa (Canadian)"
    assert out["ChaMaDanToc"] == "Khác"
    assert out["ChaDantocKhac"] == "Ca-na-đa (Canadian)"
    assert (out["ChaHo"], out["ChaTen"]) == ("TRAN", "JOHN")
    assert out["ChaHoChieuSo"] == "X1234567"
    assert out["ChaHoChieuNgayCap"] == "03/04/2025"
    assert out["ChaHoChieuNoiCap"] == "Cơ quan có thẩm quyền của Canada"
    # Ô Quốc gia bị cổng khoá nên tên nước nằm lại trong địa chỉ.
    assert out["ChaDiaChi"] == {"diaChi": "Unit 9, 100 Sample Road, Toronto, Ontario, Ca-na-đa (Canadian)"}
    # Mẹ vẫn là người Việt.
    assert out["MeMaQuocTich"] == "Việt Nam"
    assert out["MeMaDanToc"] == "Kinh"
    assert out["MeSoGiayTo"] == "001190000001"
    assert "MeHoChieuSo" not in out


def test_cha_nuoc_ngoai_khong_gui_o_cong_go_hoac_khoa():
    out = _values(_enrich_ocr(_LLM_BO_SOT_QUOC_TICH, _OCR_CHONG_NUOC_NGOAI))
    # Cổng gỡ ô Số định danh; xoá trắng và khoá Loại cư trú, Quốc gia → gửi chỉ ra "không điền được".
    assert not {"ChaSoGiayTo", "ChaLoaiCuTru", "ChaMaQuocGia"} & set(out)


def test_cha_nuoc_ngoai_quoc_tich_phai_dien_truoc_cac_o_con_lai():
    names = [f["name"] for f in _enrich_ocr(_LLM_BO_SOT_QUOC_TICH, _OCR_CHONG_NUOC_NGOAI)]
    assert names.index("ChaMaQuocTich") < names.index("ChaMaDanToc") < names.index("ChaDantocKhac")
    for later in ("ChaHo", "ChaHoChieuSo", "ChaHoChieuNgayCap", "ChaHoChieuNoiCap", "ChaDiaChi"):
        assert names.index("ChaMaQuocTich") < names.index(later)


def test_cac_o_ho_chieu_di_duong_dien_thuong_dung_loai_o():
    fields = {f["name"]: f for f in _enrich_ocr(_LLM_BO_SOT_QUOC_TICH, _OCR_CHONG_NUOC_NGOAI)}
    assert fields["ChaHoChieuSo"]["comp"] == "text"
    assert fields["ChaHoChieuNgayCap"]["comp"] == "date"
    assert fields["ChaHoChieuNoiCap"]["comp"] == "text"


def test_llm_tra_quoc_tich_va_ho_chieu_thi_ocr_khong_de():
    out = _values(_enrich_ocr({**_LLM_BO_SOT_QUOC_TICH, "ThongTinBo_QuocTich": "Ca-na-đa",
                               "ThongTinBo_NgayCapHoChieu": "05/06/2024", "ThongTinBo_NoiCapHoChieu": "Cơ quan B"},
                              _OCR_CHONG_NUOC_NGOAI))
    assert out["ChaHoChieuSo"] == "X1234567"
    assert out["ChaHoChieuNgayCap"] == "05/06/2024"
    assert out["ChaHoChieuNoiCap"] == "Cơ quan B"


def test_me_nguoi_nuoc_ngoai_cu_tru_tai_viet_nam_giu_dia_chi_viet_nam():
    out = _by_name({"ThongTinMe_HoTen": "KIM MINA", "ThongTinMe_SoDinhDanh": "M12345678",
                    "ThongTinMe_QuocTich": "Hàn Quốc", "ThongTinMe_NgayCapHoChieu": "1/2/2024",
                    "ThongTinMe_NoiCuTru": {"tinh": "Khánh Hòa", "xa": "Nha Trang", "diaChi": "Số 1"},
                    "ThongTinMe_NoiCuTruNuocNgoai": "Số 1, phường Nha Trang, tỉnh Khánh Hòa"})
    assert out["MeMaQuocTich"] == "Hàn Quốc (South Korean)"
    assert out["MeDantocKhac"] == "Hàn Quốc (South Korean)"
    assert out["MeHoChieuSo"] == "M12345678"
    assert out["MeHoChieuNgayCap"] == "01/02/2024"
    assert "MeSoGiayTo" not in out and "MeLoaiCuTru" not in out and "MeMaQuocGia" not in out
    assert out["MeDiaChi"]["xa"].endswith("Nha Trang")


def test_nguoi_nuoc_ngoai_khong_co_dia_chi_thi_khong_gui_dia_chi():
    out = _by_name({"ThongTinBo_HoTen": "JOHN SMITH", "ThongTinBo_QuocTich": "Hoa Kỳ"})
    assert out["ChaMaQuocTich"] == "Hoa Kỳ (American)"
    assert "ChaDiaChi" not in out


def test_dia_chi_nuoc_ngoai_khong_ghi_ten_nuoc_giu_nguyen_dong():
    out = _by_name({"ThongTinBo_HoTen": "JOHN SMITH", "ThongTinBo_QuocTich": "Mỹ",
                    "ThongTinBo_NoiCuTruNuocNgoai": "12 Main Street, Houston, Texas"})
    assert out["ChaDiaChi"] == {"diaChi": "12 Main Street, Houston, Texas"}


def test_ben_chong_tren_giay_ket_hon_la_nguoi_khac_thi_khong_nhan_quoc_tich():
    out = _values(_enrich_ocr({"ThongTinBo_HoTen": "LÊ VĂN BÌNH", "ThongTinBo_SoDinhDanh": "001085000009",
                               "GcnKetHon_Chong_HoTen": "TRAN JOHN", "GcnKetHon_Chong_SoGiayTo": "X1234567"},
                              _OCR_CHONG_NUOC_NGOAI))
    assert out["ChaMaQuocTich"] == "Việt Nam"
    assert out["ChaSoGiayTo"] == "001085000009"
    assert "ChaHoChieuSo" not in out


def test_giay_ket_hon_cot_chong_dung_truoc_khong_gan_nham_ben():
    ocr = _OCR_CHONG_NUOC_NGOAI.replace("tên vợ: Họ, chữ đệm, tên chồng:", "tên chồng: Họ, chữ đệm, tên vợ:")
    out = _values(_enrich_ocr({"ThongTinBo_HoTen": "TRAN JOHN", "GcnKetHon_Chong_HoTen": "TRAN JOHN",
                               "ThongTinMe_HoTen": "TRẦN THỊ MAI", "GcnKetHon_Vo_HoTen": "TRẦN THỊ MAI"}, ocr))
    assert out["ChaMaQuocTich"] == "Việt Nam"
    assert out["MeMaQuocTich"] == "Ca-na-đa (Canadian)"


def test_nguoi_viet_hai_ben_khong_doi_gi():
    ocr = _OCR_CHONG_NUOC_NGOAI.replace("Quốc tịch: Canada", "Quốc tịch: Việt Nam")
    out = _values(_enrich_ocr({"ThongTinBo_HoTen": "TRAN JOHN", "GcnKetHon_Chong_HoTen": "TRAN JOHN",
                               "ThongTinBo_DanToc": "Kinh"}, ocr))
    assert out["ChaMaQuocTich"] == "Việt Nam"
    assert out["ChaMaDanToc"] == "Kinh"
    assert out["ChaLoaiCuTru"] == "Thường trú" and out["ChaMaQuocGia"] == "Việt Nam"
    assert "ChaHoChieuSo" not in out and "ChaDantocKhac" not in out


def test_dan_toc_con_theo_me_khi_cha_nguoi_nuoc_ngoai():
    out = _by_name({"Gcs_NgaySinhCon": "01/01/2026", "Tk_HoTenCon": "TRAN AN", "ThongTinBo_HoTen": "TRAN JOHN",
                    "ThongTinBo_QuocTich": "Canada", "ThongTinBo_DanToc": "Canada",
                    "ThongTinMe_HoTen": "LÒ THỊ MAI", "ThongTinMe_DanToc": "Thái"})
    assert out["MaDanToc"] == "Thái"


def test_que_quan_con_theo_me_khi_cha_nguoi_nuoc_ngoai():
    out = _by_name({"ThongTinBo_HoTen": "TRAN JOHN", "ThongTinBo_QuocTich": "Canada",
                    "Tk_NoiCuTruCha": {"tinh": "Ontario", "xa": "Toronto"},
                    "ThongTinMe_HoTen": "TRẦN THỊ MAI", "ThongTinMe_QueQuan": {"tinh": "Khánh Hòa"}})
    assert out["QqDiaChi"]["tinh"] == "Khánh Hòa"
    khong_co_que_me = _by_name({"ThongTinBo_HoTen": "TRAN JOHN", "ThongTinBo_QuocTich": "Canada",
                                "Tk_NoiCuTruCha": {"tinh": "Ontario", "xa": "Toronto"},
                                "ThongTinMe_HoTen": "TRẦN THỊ MAI"})
    assert "QqDiaChi" not in khong_co_que_me


@pytest.mark.parametrize("raw,quoc_tich,quoc_gia", [
    ("Canada", "Ca-na-đa (Canadian)", "Canađa"),
    ("Ca-na-đa (Canadian)", "Ca-na-đa (Canadian)", "Canađa"),
    ("Canadian", "Ca-na-đa (Canadian)", "Canađa"),
    ("Hoa Kỳ", "Hoa Kỳ (American)", "Hợp chủng quốc Hoa Kỳ"),
    ("USA", "Hoa Kỳ (American)", "Hợp chủng quốc Hoa Kỳ"),
    ("Hợp chủng quốc Hoa Kỳ", "Hoa Kỳ (American)", "Hợp chủng quốc Hoa Kỳ"),
    ("Hàn Quốc", "Hàn Quốc (South Korean)", "Cộng hòa Hàn Quốc"),
    ("Cộng hòa Pháp", "Pháp (French)", "Cộng hòa Pháp"),
    ("Úc", "Ô-xtrây-li-a (Australian)", "Ôxtrâylia"),
    ("Đài Loan", "Trung Quốc (Đài Loan)", "ĐàI Loan, một tỉnh của Trung Quốc"),
    ("Trung Quốc", "Trung Quốc", "Cộng hòa nhân dân Trung Hoa"),
    ("Chinese", "Trung Quốc", "Cộng hòa nhân dân Trung Hoa"),
    ("Nhật Bản", "Nhật Bản (Japanese)", "Nhật"),
    ("Germany", "Đức (German)", "Cộng hòa Liên bang Đức"),
])
def test_ten_nuoc_quy_ve_dung_nhan_hai_o_cua_cong(raw, quoc_tich, quoc_gia):
    assert _foreign_nationality(raw) == quoc_tich
    assert QUOC_TICH_QUOC_GIA[quoc_tich] == quoc_gia


@pytest.mark.parametrize("raw", ["", None, "Việt Nam", "VIỆT NAM", "Vietnam", "Vietnamese", "Việt Nam."])
def test_nguoi_viet_khong_tinh_la_nguoi_nuoc_ngoai(raw):
    assert _foreign_nationality(raw) == ""


def test_nuoc_khong_co_trong_danh_muc_giu_chu_tren_giay():
    assert _foreign_nationality("Wakanda") == "Wakanda"


def test_alias_quoc_tich_tro_dung_nhan_co_trong_danh_muc():
    assert set(_QUOC_TICH_ALIASES.values()) <= set(QUOC_TICH_QUOC_GIA)


def test_benh_vien_co_trong_bang_lay_xa_theo_bang_de_xa_ocr_doc_sai():
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Lâm Đồng", "xa": "Phường Can Lư",
        "diaChi": "Bệnh viện đa khoa tỉnh Lâm Đồng Số 01 Phạm Ngọc Thạch"}})
    assert out["NsDiaChi"]["xa"] == "Phường Cam Ly - Đà Lạt"
    assert out["NsDiaChi"]["tinh"] == "Lâm Đồng"


def test_to_khai_ocr_sai_ten_benh_vien_lay_noi_sinh_theo_giay_chung_sinh():
    # Ảnh 13/11: tờ khai viết tay OCR ra "Sắt nhị … thanh mưu" → bảng không nhận ra, ô Phường/Xã trống.
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Tỉnh Lâm Đồng", "xa": "", "diaChi": "Bệnh viện Sắt nhị Tỉnh Lâm Đồng, số 57 thanh mưu"},
        "Gcs_NoiSinh": {"tinh": "Lâm Đồng", "diaChi": "BỆNH VIỆN SẢN NHI LÂM ĐỒNG"}})
    assert out["NsDiaChi"]["xa"] == "Phường Lang Biang - Đà Lạt"
    assert out["NsDiaChi"]["diaChi"] == "Bệnh viện Sản Nhi Lâm Đồng"


def test_to_khai_noi_sinh_khong_phai_co_so_y_te_hoac_khac_tinh_giu_to_khai():
    gcs = {"tinh": "Lâm Đồng", "diaChi": "Bệnh viện Sản Nhi Lâm Đồng"}
    # Sinh ở nhà: tờ khai ghi địa chỉ, không phải cơ sở y tế.
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "Số 5 đường A"}, "Gcs_NoiSinh": gcs})
    assert out["NsDiaChi"]["diaChi"] == "Số 5 đường A"
    # Tờ khai ghi cơ sở ở tỉnh khác giấy chứng sinh.
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Hà Nội", "xa": "Phường Hai Bà Trưng", "diaChi": "Bệnh viện Phụ sản Hà Nội"}, "Gcs_NoiSinh": gcs})
    assert out["NsDiaChi"]["diaChi"] == "Bệnh viện Phụ sản Hà Nội"
    # Giấy chứng sinh cũng không nhận ra → giữ tờ khai.
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Lâm Đồng", "xa": "", "diaChi": "Bệnh viện Sắt nhị"},
        "Gcs_NoiSinh": {"tinh": "Lâm Đồng", "diaChi": "Bệnh viện Sắt nhị"}})
    assert out["NsDiaChi"]["diaChi"] == "Bệnh viện Sắt nhị"


def test_benh_vien_ten_cu_the_hon_thang_ten_goc():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    assert lookup_hospital("Bệnh viện Sản Nhi Bắc Ninh số 2, đường X")["xa"] == "Phường Võ Cường"
    assert lookup_hospital("BV Đa khoa Anh Quất cơ sở 2")["xa"] == "Phường Tiền Phong"


def test_ten_chung_chung_khong_khop_benh_vien_nao():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    assert lookup_hospital("Bệnh viện đa khoa tỉnh") is None


def test_benh_vien_ninh_thuan_cu_ra_xa_moi_cua_khanh_hoa():
    # Giấy trước 1/7/2025 ghi tỉnh Ninh Thuận, OCR đọc sai xã → xã theo bảng bv_khanh_hoa.json.
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Ninh Thuận", "xa": "Phường Văn Hai", "diaChi": "Bệnh viện Đa khoa tỉnh Ninh Thuận"}})
    assert out["NsDiaChi"]["xa"] == "Phường Ninh Chử"
    assert out["NsDiaChi"]["tinh"] == "Khánh Hòa"


def test_benh_vien_khanh_hoa_ten_cu_ten_moi_va_viet_tat():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    assert lookup_hospital("Bệnh viện đa khoa tỉnh Khánh Hòa, 19 Yersin")["xa"] == "Phường Nha Trang"
    assert lookup_hospital("Bệnh viện Đa khoa Khánh Hoà")["xa"] == "Phường Nha Trang"
    assert lookup_hospital("BVĐKKV Ninh Hòa")["xa"] == "Phường Ninh Hòa"
    assert lookup_hospital("Bệnh viện Đa khoa Ninh Thuận cơ sở 2")["xa"] == "Phường Đô Vinh"
    # TTYT cấp huyện thành TTYT khu vực từ 1/7/2025; TTYT Ninh Hòa ở Ninh Diêm, khác xã với BVĐKKV Ninh Hòa.
    assert lookup_hospital("Trung tâm Y tế huyện Cam Lâm")["xa"] == "Xã Cam Lâm"
    assert lookup_hospital("TTYTKV Cam Lâm")["xa"] == "Xã Cam Lâm"
    assert lookup_hospital("TTYT TX Ninh Hòa")["xa"] == "Phường Đông Ninh Hòa"
    assert lookup_hospital("TTYT TP Phan Rang Tháp Chàm")["xa"] == "Phường Phan Rang"
    assert lookup_hospital("Bệnh viện Ninh Hòa", "Khánh Hòa") is None


def test_bang_benh_vien_khanh_hoa_khong_keo_benh_vien_tinh_khac():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    assert lookup_hospital("Bệnh viện Đa khoa Sài Gòn", "Thành phố Hồ Chí Minh") is None
    assert lookup_hospital("Bệnh viện Đa khoa Tâm Trí", "Tỉnh Đồng Tháp") is None
    # Hàm Thuận Bắc (Bình Thuận cũ) lấy theo bv_lam_dong.json, không phải một dòng Khánh Hòa.
    assert lookup_hospital("Trung tâm Y tế huyện Hàm Thuận Bắc", "Tỉnh Lâm Đồng")["tinh"] == "Tỉnh Lâm Đồng"


def test_bang_benh_vien_khanh_hoa_chi_dung_xa_hien_hanh():
    import json
    from pathlib import Path

    from app.pipelines._shared.area_remap import is_current_area
    import app.pipelines._shared.hospital_lookup as hl
    rows = json.loads((Path(hl.__file__).parent / "data_bv" / "bv_khanh_hoa.json").read_text(encoding="utf-8"))
    assert [r["ten"] for r in rows if not is_current_area(r["tinh"], r["xa"])] == []


def test_benh_vien_bac_ninh_ten_cu_ten_moi_ca_hai_tinh_cu():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    # Ảnh 12/11: tỉnh "Thành phố Bắc Ninh", chi tiết "Bệnh viện đa khoa Yên Phong" mà ô xã để trống.
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Thành phố Bắc Ninh", "xa": "", "diaChi": "Bệnh viện đa khoa Yên Phong"}})
    assert out["NsDiaChi"]["xa"] == "Phường Yên Phong"
    # Ba đời tên tuyến huyện: BVĐK huyện (trước 2018) → TTYT huyện → BVĐK (từ 1/1/2026).
    assert lookup_hospital("BVĐK huyện Yên Phong")["xa"] == "Phường Yên Phong"
    assert lookup_hospital("TTYT huyện Tiên Du")["xa"] == "Xã Liên Bão"
    assert lookup_hospital("Trung tâm Y tế thị xã Từ Sơn")["xa"] == "Phường Đồng Nguyên"
    assert lookup_hospital("TTYT huyện Lục Ngạn")["xa"] == "Phường Chũ"
    # Tuyến tỉnh: tên trước 1/7/2025 và tên "số 1" (Bắc Giang cũ) / "số 2" (Bắc Ninh cũ).
    assert lookup_hospital("Bệnh viện đa khoa tỉnh Bắc Ninh")["xa"] == "Phường Võ Cường"
    assert lookup_hospital("BVĐK tỉnh Bắc Giang")["xa"] == "Phường Bắc Giang"
    assert lookup_hospital("Bệnh viện Sản Nhi Bắc Ninh")["xa"] == "Phường Võ Cường"
    assert lookup_hospital("Bệnh viện Sản Nhi Bắc Ninh số 1")["xa"] == "Phường Bắc Giang"
    assert lookup_hospital("BV Phổi Bắc Ninh số 1")["xa"] == "Phường Đa Mai"


def test_bang_benh_vien_bac_ninh_chi_dung_xa_hien_hanh():
    import json
    from pathlib import Path

    from app.pipelines._shared.area_remap import is_current_area
    import app.pipelines._shared.hospital_lookup as hl
    rows = json.loads((Path(hl.__file__).parent / "data_bv" / "bv_bac_ninh.json").read_text(encoding="utf-8"))
    assert [r["ten"] for r in rows if not is_current_area(r["tinh"], r["xa"])] == []


def test_benh_vien_quang_tri_ca_hai_tinh_cu_va_ba_doi_ten():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Quảng Trị", "xa": "Phường Đông Lường", "diaChi": "Bệnh viện Đa khoa tỉnh Quảng Trị, 266 Hùng Vương"}})
    assert out["NsDiaChi"]["xa"] == "Phường Nam Đông Hà"
    assert lookup_hospital("Bệnh viện Hữu nghị Việt Nam Cu Ba Đồng Hới")["xa"] == "Phường Đồng Hới"
    assert lookup_hospital("BV đa khoa huyện Bố Trạch")["xa"] == "Xã Hoàn Lão"
    # TTYT huyện → TTYT khu vực (7/2025) → BVĐKKV (QĐ 936/QĐ-UBND 19/3/2026).
    assert lookup_hospital("TTYT huyện Hải Lăng")["xa"] == "Xã Diên Sanh"
    assert lookup_hospital("TTYTKV Thạch Hãn")["xa"] == "Phường Quảng Trị"
    assert lookup_hospital("BVĐKKV Đakrông")["xa"] == "Xã Hướng Hiệp"
    assert lookup_hospital("TTYT huyện Triệu Phong")["xa"] == "Xã Triệu Phong"
    assert lookup_hospital("TTYT huyện Triệu Phong cơ sở 2")["xa"] == "Xã Nam Cửa Việt"
    # Huyện Quảng Ninh (Quảng Bình cũ) không được kéo BVĐK tỉnh Quảng Ninh về.
    assert lookup_hospital("Bệnh viện Đa khoa Quảng Ninh", "Tỉnh Quảng Ninh") is None


def test_benh_vien_dong_nai_ca_hai_tinh_cu_va_ten_de_nham():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Đồng Nai", "xa": "", "diaChi": "Bệnh viện Đa khoa Đồng Nai"}})
    assert out["NsDiaChi"]["xa"] == "Phường Tam Hiệp"
    assert lookup_hospital("BVĐK Thống Nhất Đồng Nai")["xa"] == "Phường Long Bình"
    # TTYT Thống Nhất ở Bàu Hàm 2 (Dầu Giây); BVĐKKV và TTYT KV Long Khánh là hai nơi.
    assert lookup_hospital("TTYT huyện Thống Nhất")["xa"] == "Phường Dầu Giây"
    assert lookup_hospital("BVĐKKV Long Khánh")["xa"] == "Phường Bình Lộc"
    assert lookup_hospital("TTYT KV Long Khánh")["xa"] == "Phường Long Khánh"
    assert lookup_hospital("Bệnh viện đa khoa tỉnh Bình Phước")["xa"] == "Phường Đồng Xoài"
    assert lookup_hospital("TTYT huyện Bù Gia Mập")["xa"] == "Xã Phú Nghĩa"
    assert lookup_hospital("Bệnh viện Thống Nhất", "Thành phố Hồ Chí Minh") is None
    assert lookup_hospital("Bệnh viện Nhi đồng 1", "Thành phố Hồ Chí Minh") is None
    assert lookup_hospital("Trung tâm Y tế quận Tân Phú", "Thành phố Hồ Chí Minh") is None


def test_bang_benh_vien_quang_tri_dong_nai_chi_dung_xa_hien_hanh():
    import json
    from pathlib import Path

    from app.pipelines._shared.area_remap import is_current_area
    import app.pipelines._shared.hospital_lookup as hl
    for name in ("bv_quang_tri.json", "bv_dong_nai.json"):
        rows = json.loads((Path(hl.__file__).parent / "data_bv" / name).read_text(encoding="utf-8"))
        assert [r["ten"] for r in rows if not is_current_area(r["tinh"], r["xa"])] == []


def test_benh_vien_lam_dong_ca_ba_tinh_cu_va_ten_viet_tat():
    from app.pipelines._shared.hospital_lookup import lookup_hospital
    # Tờ khai ghi tên bệnh viện kèm số nhà, không có chữ "tỉnh" (trước đây không tra ra).
    assert lookup_hospital("Bệnh viện Sản Nhi Lâm Đồng, số 57 Thánh Mẫu")["xa"] == "Phường Lang Biang - Đà Lạt"
    assert lookup_hospital("Bệnh viện Nhi Lâm Đồng")["xa"] == "Phường Lang Biang - Đà Lạt"
    assert lookup_hospital("Bệnh viện Đa khoa Lâm Đồng, số 01 Phạm Ngọc Thạch")["xa"] == "Phường Cam Ly - Đà Lạt"
    assert lookup_hospital("Bệnh viện 2 Lâm Đồng")["xa"] == "Phường B'Lao"
    # Lâm Đồng cũ: TTYT huyện → TTYT khu vực (7/2025).
    assert lookup_hospital("TTYT TP Đà Lạt")["xa"] == "Phường Xuân Hương - Đà Lạt"
    assert lookup_hospital("TTYT TP Bảo Lộc")["xa"] == "Phường 1 Bảo Lộc"
    assert lookup_hospital("TTYT huyện Lâm Hà")["xa"] == "Xã Đinh Văn Lâm Hà"
    assert lookup_hospital("TTYTKV Lạc Dương")["xa"] == "Phường Lang Biang - Đà Lạt"
    # Đắk Nông cũ: TTYT Đắk Mil nay ở Thuận An (TT Đắk Mil cũ là Xã Đức Lập), Krông Nô ở Nam Đà.
    assert lookup_hospital("TTYT huyện Đắk Mil")["xa"] == "Xã Thuận An"
    assert lookup_hospital("TTYTKV Krông Nô")["xa"] == "Xã Nam Đà"
    assert lookup_hospital("TTYT Đăk Rlấp")["xa"] == "Xã Kiến Đức"
    assert lookup_hospital("Bệnh viện đa khoa tỉnh Đắk Nông")["xa"] == "Phường Đông Gia Nghĩa"
    # Bình Thuận cũ.
    assert lookup_hospital("Bệnh viện đa khoa tỉnh Bình Thuận")["xa"] == "Phường Bình Thuận"
    assert lookup_hospital("BVĐKKV phía Nam Bình Thuận")["xa"] == "Xã Đức Linh"
    assert lookup_hospital("TTYT huyện Hàm Thuận Bắc")["xa"] == "Xã Hàm Thuận"
    assert lookup_hospital("TTYT Quân dân y Phú Quý")["xa"] == "Đặc khu Phú Quý"
    # Huyện Bảo Lâm có cả ở Cao Bằng; "Bệnh viện Đà Lạt" không rõ bệnh viện nào.
    assert lookup_hospital("Trung tâm Y tế huyện Bảo Lâm", "Tỉnh Cao Bằng") is None
    assert lookup_hospital("Bệnh viện Đà Lạt") is None


def test_bang_benh_vien_lam_dong_chi_dung_xa_hien_hanh():
    import json
    from pathlib import Path

    from app.pipelines._shared.area_remap import is_current_area
    import app.pipelines._shared.hospital_lookup as hl
    rows = json.loads((Path(hl.__file__).parent / "data_bv" / "bv_lam_dong.json").read_text(encoding="utf-8"))
    assert [r["ten"] for r in rows if not is_current_area(r["tinh"], r["xa"])] == []


def test_benh_vien_khong_co_trong_bang_giu_xa_cua_giay():
    out = _by_name({"Tk_HoTenCon": "VŨ AN", "Tk_NoiSinh": {
        "tinh": "Hà Nội", "xa": "Phường Hai Bà Trưng", "diaChi": "Bệnh viện Phụ sản Hà Nội"}})
    assert out["NsDiaChi"]["xa"] == "Phường Hai Bà Trưng"
