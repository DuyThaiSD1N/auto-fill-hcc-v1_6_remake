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


def test_ten_phuong_ngan_ocr_sai_dau_van_sua_ve_danh_muc():
    out = _by_name({"ThongTinBo_HoTen": "NGUYỄN VĂN AN", "Tk_NoiCuTruCha": {
        "tinh": "Hồ Chí Minh", "xa": "Bản Cờ", "diaChi": "12 Đường A"}})
    assert out["ChaDiaChi"]["xa"] == "Phường Bàn Cờ"


def test_ten_phuong_ngan_lech_mot_chu_khong_doan():
    out = _by_name({"ThongTinBo_HoTen": "NGUYỄN VĂN AN", "Tk_NoiCuTruCha": {
        "tinh": "Hồ Chí Minh", "xa": "Bàn Lờ", "diaChi": "12 Đường A"}})
    assert out["ChaDiaChi"]["xa"] == "Bàn Lờ"


def test_noi_de_nghi_dktt_ct01_chi_dien_chi_tiet():
    out = _by_name({"Ct01_ChuHoHoTen": "LÊ VĂN CHỦ", "Ct01_NoiDeNghiDktt": {
        "tinh": "Tỉnh C", "xa": "Phường B", "diaChi": "12 Đường A"}})
    assert out["DkttDiaChi"] == {"diaChi": "12 Đường A"}


def test_noi_de_nghi_dktt_cat_phan_phuong_xa_bi_dinh_vao_chi_tiet():
    out = _by_name({"Ct01_NoiDeNghiDktt": {
        "xa": "Phường B", "diaChi": "Đăng ký thường trú tại 12 Đường A, phường B, tỉnh C"}})
    assert out["DkttDiaChi"] == {"diaChi": "12 Đường A"}
    out = _by_name({"Ct01_NoiDeNghiDktt": {"xa": "B", "diaChi": "12 Đường A phường B"}})
    assert out["DkttDiaChi"] == {"diaChi": "12 Đường A"}


def test_khong_co_noi_de_nghi_dktt_thi_khong_phat_o():
    out = _by_name({"Ct01_ChuHoHoTen": "LÊ VĂN CHỦ", "Ct01_NoiDeNghiDktt": {"tinh": "Tỉnh C", "xa": "Phường B"}})
    assert "DkttDiaChi" not in out


# ── Khối "Thông tin người yêu cầu": BE gửi mọi người trong giấy tờ, extension chọn theo CCCD/tên ──
def _nyc(values: dict) -> list[dict]:
    return (_by_name(values).get("NycBuThieu") or {}).get("nguoi") or []


_CHA_ME = {
    "ThongTinBo_HoTen": "Trần Văn Bố", "ThongTinBo_SoDinhDanh": "001090000011",
    "ThongTinBo_NgayCapCccd": "5/4/2021", "ThongTinBo_NoiCuTru": {"tinh": "Tỉnh C", "xa": "Xã B", "diaChi": "Thôn A"},
    "ThongTinMe_HoTen": "Lê Thị Mẹ", "ThongTinMe_SoDinhDanh": "001190000022",
    "ThongTinMe_NgayCapCccd": "02/08/2024", "ThongTinMe_NoiCapCccd": "BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY",
}


def test_cha_va_me_deu_la_ung_vien_nguoi_yeu_cau():
    people = {p["vaiTro"]: p for p in _nyc(_CHA_ME)}
    assert people["cha"]["cccd"] == "001090000011"
    assert people["cha"]["ten"] == "TRẦN VĂN BỐ"
    assert people["cha"]["gioiTinh"] == "Nam"
    assert people["cha"]["ngayCap"] == "05/04/2021"
    # Không in nơi cấp: CCCD 12 số cấp trước 01/7/2024 → Cục Cảnh sát.
    assert people["cha"]["noiCap"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert people["cha"]["noiCuTru"]["diaChi"] == "Thôn A"
    assert people["cha"]["loaiCuTru"] == "Thường trú" and people["cha"]["quocGia"] == "Việt Nam"
    assert people["me"]["gioiTinh"] == "Nữ"
    assert people["me"]["noiCap"] == "Bộ Công an"
    assert "noiCuTru" not in people["me"] and "loaiCuTru" not in people["me"]


def test_nguoi_thu_ba_tren_cccd_la_ung_vien_rieng():
    people = _nyc({**_CHA_ME, "NguoiKhac_HoTen": "Phạm Văn Ông", "NguoiKhac_SoDinhDanh": "001060000033",
                   "NguoiKhac_GioiTinh": "Nam", "NguoiKhac_NoiCuTru": {"tinh": "Tỉnh C", "xa": "Xã D"}})
    khac = next(p for p in people if p["vaiTro"] == "khac")
    assert khac["cccd"] == "001060000033" and khac["gioiTinh"] == "Nam"
    assert khac["noiCuTru"]["tinh"] == "Tỉnh C"
    assert "ngayCap" not in khac and "noiCap" not in khac  # chỉ có mặt trước: không suy nơi cấp


def test_to_khai_gop_vao_cha_khi_trung_so_dinh_danh_noi_cu_tru_to_khai_thang():
    people = _nyc({**_CHA_ME, "Tk_NguoiYeuCau_HoTen": "Trần Văn Bố", "Tk_NguoiYeuCau_SoGiayTo": "001090000011",
                   "Tk_NguoiYeuCau_NgayCap": "01/01/2020",
                   "Tk_NguoiYeuCau_NoiCuTru": {"tinh": "Tỉnh C", "xa": "Xã E", "diaChi": "Xóm 2"}})
    assert [p["vaiTro"] for p in people] == ["cha", "me"]
    cha = people[0]
    assert cha["ngayCap"] == "05/04/2021"  # ngày in trên thẻ thắng chữ viết tay
    assert cha["noiCuTru"]["diaChi"] == "Xóm 2"


def test_to_khai_gop_vao_me_theo_ten_khi_khong_ghi_so():
    people = _nyc({**_CHA_ME, "Tk_NguoiYeuCau_HoTen": "LE THI ME",
                   "Tk_NguoiYeuCau_NoiCuTru": {"tinh": "Tỉnh C", "xa": "Xã B", "diaChi": "Thôn A"}})
    me = next(p for p in people if p["vaiTro"] == "me")
    assert me["noiCuTru"]["diaChi"] == "Thôn A"
    assert len(people) == 2


def test_to_khai_cung_ten_khac_so_la_nguoi_khac():
    people = _nyc({**_CHA_ME, "Tk_NguoiYeuCau_HoTen": "Trần Văn Bố", "Tk_NguoiYeuCau_SoGiayTo": "001090000099",
                   "Tk_NguoiYeuCau_NoiCuTru": {"tinh": "Tỉnh C", "xa": "Xã F"}})
    assert [p["vaiTro"] for p in people] == ["cha", "me", "toKhai"]


def test_cmnd_9_so_khong_suy_noi_cap():
    people = _nyc({"NguoiKhac_HoTen": "Đỗ Văn Ông", "NguoiKhac_SoDinhDanh": "123456789",
                   "NguoiKhac_NgayCapCccd": "01/01/2015"})
    assert people[0]["ngayCap"] == "01/01/2015" and "noiCap" not in people[0]


def test_khong_co_gi_de_bu_thi_khong_phat_o():
    assert _nyc({"ThongTinBo_HoTen": "Trần Văn Bố"}) == [
        {"vaiTro": "cha", "ten": "TRẦN VĂN BỐ", "gioiTinh": "Nam"}
    ]
    assert "NycBuThieu" not in _by_name({"Gcs_HoTenCon": "TRẦN AN"})


# LLM hay bỏ sót thẻ người thứ ba → mapper đọc thẳng mặt trước/mặt sau thẻ trong văn bản OCR.
_OCR_THE = """===== CCCD cha.pdf =====
CĂN CƯỚC CÔNG DÂN
Số / No.: 001090000011
Họ và tên / Full name:
TRẦN VĂN BỐ
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Nơi thường trú / Place of residence: Thôn A
Xã B, Huyện K, Tỉnh C
Có giá trị đến: 01/01/2040
───── Trang 2/2 ─────
Ngày, tháng, năm / Date, month, year: 3/2/2022
CỤC TRƯỞNG CỤC CẢNH SÁT
IDVNM0900000111001090000011<<4

===== anh_nguoi_nop.jpg =====
CĂN CƯỚC CÔNG DÂN
Số / No: 001204000044
Họ và tên / Full name:
PHẠM VĂN ÔNG
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Nơi thường trú / Place of residence: Tổ 5
Phường D, Quận E, Tỉnh C
Có giá trị đến: 01/01/2045

===== CT01.pdf =====
9. Số định danh cá nhân của chủ hộ: 001090000011
"""


def test_doc_the_nguoi_thu_ba_tu_ocr_khi_llm_bo_sot():
    out = enrich([{"name": "ThongTinBo_HoTen", "value": "Trần Văn Bố"},
                  {"name": "ThongTinBo_SoDinhDanh", "value": "001090000011"}], ocr_text=_OCR_THE)
    people = {p["vaiTro"]: p for p in next(f for f in out if f["name"] == "NycBuThieu")["value"]["nguoi"]}
    assert set(people) == {"cha", "khac"}
    # Cha: LLM không trả ngày cấp → bù từ mặt sau thẻ (ghép theo số định danh trong dòng MRZ).
    assert people["cha"]["ngayCap"] == "03/02/2022"
    assert people["cha"]["noiCap"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    khac = people["khac"]
    assert khac["cccd"] == "001204000044" and khac["ten"] == "PHẠM VĂN ÔNG" and khac["gioiTinh"] == "Nam"
    assert khac["noiCuTru"]["tinh"] == "Tỉnh C"
    assert khac["noiCuTru"]["diaChi"] == "Tổ 5"
    assert "ngayCap" not in khac  # chỉ có mặt trước


def test_so_dinh_danh_tren_giay_khac_khong_thanh_the():
    from app.pipelines.khai_sinh_lien_thong.process.mapper import _cards_from_ocr
    assert [c["cccd"] for c in _cards_from_ocr(_OCR_THE)] == ["001090000011", "001204000044"]
