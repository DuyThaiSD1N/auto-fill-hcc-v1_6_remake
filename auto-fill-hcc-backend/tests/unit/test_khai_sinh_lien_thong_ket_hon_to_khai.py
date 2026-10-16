"""Khai sinh liên thông: thông tin giấy chứng nhận kết hôn chép trên dòng in sẵn của TỜ KHAI (hồ sơ không kèm giấy
kết hôn thật) vẫn phải điền; giấy kết hôn thật thì thắng tờ khai."""
from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


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
