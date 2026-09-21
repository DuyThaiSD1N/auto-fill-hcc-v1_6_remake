"""Trích lục hộ tịch: một người có cả CCCD lẫn CMND thì luôn điền theo CCCD.

Hai chuyện tách bạch:

1. NGUỒN của cụm giấy tờ tùy thân ở mục I — thẻ trong hồ sơ hay tờ khai. Cụm (loại, số, ngày cấp,
   nơi cấp) phải đi NGUYÊN KHỐI từ một giấy tờ; trộn số thẻ căn cước với ngày cấp CMND ghi trên đơn
   là dựng ra giấy tờ không tồn tại. Giữa hai nguồn, CCCD 12 số thắng CMND 9 số; cùng hạng thì bản
   IN trên thẻ thắng chữ viết tay.
2. Hồ sơ nộp kèm CẢ hai thẻ của cùng một người: agent tưởng là hai người rồi đẩy thẻ thừa sang vai
   người được đăng ký, làm mục II bị điền bằng giấy tờ cũ của chính người yêu cầu.
"""
from app.pipelines.trich_luc.process.mapper import enrich

_CCCD = "001181030693"
_CMND = "131234567"
_CMND_CU = "120987132"


def _enrich(options=None, **values):
    fields = [
        {"name": name, "comp": "x-input", "value": value}
        for name, value in values.items()
    ]
    return {field["name"]: field["value"] for field in enrich(fields, options)}


def _ho_so(**overrides):
    """Hồ sơ chuẩn: tờ khai + giấy khai sinh của con + thẻ của người yêu cầu."""
    values = {
        "TkNyc_HoTen": "Nguyễn Thị Thanh Nga",
        "TkNyc_LoaiGiayToTuyThan": "Chứng minh nhân dân",
        "TkNyc_SoGiayToTuyThan": _CMND,
        "TkNyc_NgayCapGiayToTuyThan": "05/03/2009",
        "TkNyc_NoiCapGiayToTuyThan": "Công an tỉnh Phú Thọ",
        "Nyc_HoTen": "NGUYỄN THỊ THANH NGA",
        "Nyc_SoDinhDanh": _CCCD,
        "Nyc_NgayCap": "12/06/2021",
        "Nyc_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "HoTich_LoaiSuKien": "birth",
        "HoTich_TenGiayTo": "Giấy khai sinh",
        "HoTich_HoTenNguoiDuocDangKy": "TRẦN MINH KHÔI",
        "HoTich_SoDinhDanh": "025225001150",
        "HoTich_CoQuanDangKy": "UBND xã Hùng Lô",
        "HoTich_So": "47",
        "HoTich_NgayDangKy": "07/05/2025",
    }
    values.update(overrides)
    return {name: value for name, value in values.items() if value is not None}


# --------------------------------------------------------------------------------------
# 1. Chọn nguồn cho cụm giấy tờ tùy thân của mục I
# --------------------------------------------------------------------------------------


def test_don_ghi_cmnd_cu_thi_ca_cum_lay_theo_cccd_trong_ho_so():
    out = _enrich(**_ho_so())

    assert out["SoDinhDanhC"] == _CCCD
    assert out["NgayCapDDC"] == "12/06/2021"
    assert out["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert out["HoVaTenC"] == "NGUYỄN THỊ THANH NGA"


def test_khong_tron_so_cccd_voi_ngay_noi_cap_cua_cmnd_tren_don():
    """Lỗi cũ: số lấy từ thẻ căn cước còn ngày/nơi cấp lấy từ dòng CMND của tờ khai."""
    out = _enrich(**_ho_so())

    assert out["NgayCapDDC"] != "05/03/2009"
    assert out["NoiCapDDC"] != "Công an tỉnh Phú Thọ"


def test_don_ghi_cccd_ma_the_trong_ho_so_la_cmnd_thi_lay_theo_don():
    """Ưu tiên CCCD áp dụng cho cả hai chiều, không phải 'thẻ luôn thắng'."""
    out = _enrich(**_ho_so(
        TkNyc_LoaiGiayToTuyThan="Căn cước công dân",
        TkNyc_SoGiayToTuyThan=_CCCD,
        TkNyc_NgayCapGiayToTuyThan="12/06/2021",
        TkNyc_NoiCapGiayToTuyThan="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        Nyc_SoDinhDanh=_CMND,
        Nyc_NgayCap="05/03/2009",
        Nyc_NoiCap="Công an tỉnh Phú Thọ",
    ))

    assert out["SoDinhDanhC"] == _CCCD
    assert out["NgayCapDDC"] == "12/06/2021"
    assert out["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"


def test_cung_mot_giay_to_thi_the_van_bu_duoc_o_don_khong_doc_ra():
    """Số khớp nhau = cùng một giấy tờ, lúc đó hai nguồn được gộp như trước."""
    out = _enrich(**_ho_so(
        TkNyc_LoaiGiayToTuyThan="Căn cước công dân",
        TkNyc_SoGiayToTuyThan=_CCCD,
        TkNyc_NgayCapGiayToTuyThan="12/06/2021",
        TkNyc_NoiCapGiayToTuyThan="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        Nyc_NgayCap=None,
        Nyc_NoiCap=None,
    ))

    assert out["SoDinhDanhC"] == _CCCD
    assert out["NgayCapDDC"] == "12/06/2021"
    assert out["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_don_khong_doc_ra_so_thi_van_bu_ngay_noi_cap_cho_the():
    """Tờ khai chỉ đọc được ngày/nơi cấp: không có bằng chứng là giấy tờ khác nên vẫn bù."""
    out = _enrich(**_ho_so(
        TkNyc_SoGiayToTuyThan=None,
        TkNyc_LoaiGiayToTuyThan=None,
        Nyc_SoDinhDanh=None,
        Nyc_NgayCap=None,
        Nyc_NoiCap=None,
    ))

    assert out["NgayCapDDC"] == "05/03/2009"
    assert out["NoiCapDDC"] == "Công an tỉnh Phú Thọ"


def test_chi_co_don_thi_giu_nguyen_cum_cua_don():
    out = _enrich(**_ho_so(Nyc_HoTen=None, Nyc_SoDinhDanh=None, Nyc_NgayCap=None, Nyc_NoiCap=None))

    assert out["SoDinhDanhC"] == _CMND
    assert out["NgayCapDDC"] == "05/03/2009"
    assert out["NoiCapDDC"] == "Công an tỉnh Phú Thọ"
    assert out["LoaiGiayToDinhDanhC"] == "Chứng minh nhân dân"


def test_ten_lay_theo_the_in_thay_vi_chu_viet_tay_tren_don():
    out = _enrich(**_ho_so(TkNyc_HoTen="Nguyễn Thị Thanh Ngà"))

    assert out["HoVaTenC"] == "NGUYỄN THỊ THANH NGA"


def test_the_cua_nguoi_khac_thi_khong_duoc_dung_cho_muc_I():
    """Tờ khai ghi người yêu cầu là A, thẻ trong hồ sơ là B → cụm vẫn theo tờ khai."""
    out = _enrich(**_ho_so(
        Nyc_HoTen="LÊ VĂN BỐN",
        Nyc_SoDinhDanh="036090001234",
    ))

    assert out["HoVaTenC"] == "NGUYỄN THỊ THANH NGA"
    assert out["SoDinhDanhC"] == _CMND


def test_noi_cu_tru_van_lay_theo_don():
    """Ưu tiên CCCD chỉ áp cho cụm giấy tờ tùy thân; phần còn lại vẫn là đơn."""
    out = _enrich(**_ho_so(
        TkNyc_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Phú Thọ", "xa": "Hùng Lô", "diaChi": "Khu 2"},
        Nyc_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Phú Thọ", "xa": "Hùng Lô", "diaChi": "Khu 9"},
    ))

    assert out["NYC_NoiCuTru_TrongNuoc"]["diaChi"] == "Khu 2"


# --------------------------------------------------------------------------------------
# 2. Hồ sơ nộp kèm cả CCCD lẫn CMND của cùng một người
# --------------------------------------------------------------------------------------


def test_cmnd_cu_cua_chinh_nguoi_yeu_cau_khong_bi_coi_la_nguoi_duoc_dang_ky():
    out = _enrich(**_ho_so(
        ChuThe_HoTen="NGUYỄN THỊ THANH NGA",
        ChuThe_SoDinhDanh=_CMND,
        ChuThe_NgayCap="05/03/2009",
        ChuThe_NoiCap="Công an tỉnh Phú Thọ",
    ))

    assert out["SoDinhDanhC"] == _CCCD
    # Mục II vẫn là người trên giấy khai sinh, không phải CMND cũ của người yêu cầu.
    assert out["NDK_HoVaTen"] == "TRẦN MINH KHÔI"
    assert out.get("NDK_SoGiayToTuyThan") != _CMND


def test_cccd_bi_xep_nham_sang_vai_chu_the_thi_duoc_tra_ve_muc_I():
    out = _enrich(**_ho_so(
        Nyc_SoDinhDanh=_CMND,
        Nyc_NgayCap="05/03/2009",
        Nyc_NoiCap="Công an tỉnh Phú Thọ",
        ChuThe_HoTen="NGUYỄN THỊ THANH NGA",
        ChuThe_SoDinhDanh=_CCCD,
        ChuThe_NgayCap="12/06/2021",
        ChuThe_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    ))

    assert out["SoDinhDanhC"] == _CCCD
    assert out["NgayCapDDC"] == "12/06/2021"
    assert out["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert out["NDK_HoVaTen"] == "TRẦN MINH KHÔI"


def test_hai_the_cua_hai_nguoi_khac_nhau_van_giu_nguyen_hai_vai():
    """Luật 'thẻ còn lại là chủ thể' không được đụng tới khi đúng là hai người."""
    out = _enrich(**_ho_so(
        HoTich_HoTenNguoiDuocDangKy="TRẦN MINH KHÔI",
        HoTich_SoDinhDanh="025225001150",
        ChuThe_HoTen="TRẦN MINH KHÔI",
        ChuThe_SoDinhDanh="025225001150",
        ChuThe_NgaySinh="06/05/2005",
    ))

    assert out["SoDinhDanhC"] == _CCCD
    assert out["NDK_HoVaTen"] == "TRẦN MINH KHÔI"
    assert out["NDK_SoDinhDanh"] == "025225001150"


def test_hai_the_trung_ten_nhung_deu_12_so_thi_khong_gop_vai():
    """Hai thẻ cùng 12 số là hai người trùng tên (hoặc thẻ cấp lại) — không tự ý bỏ thẻ nào."""
    out = _enrich(**_ho_so(
        ChuThe_HoTen="NGUYỄN THỊ THANH NGA",
        ChuThe_SoDinhDanh="036090001234",
        ChuThe_NgaySinh="06/05/2005",
    ))

    assert out["SoDinhDanhC"] == _CCCD
    assert "ChuThe_SoDinhDanh" not in out


# --------------------------------------------------------------------------------------
# 3. Mục II (người được cấp bản sao): tờ khai ghi CMND cũ, hồ sơ có thẻ căn cước
# --------------------------------------------------------------------------------------


def _tu_xin_cho_minh(**overrides):
    """Người tự xin bản sao khai sinh của mình: tờ khai ghi CMND 9 số, hồ sơ có CCCD 12 số.

    Dựng đúng theo hồ sơ thật (trace 2026-09-21 08:16): tờ khai vào nhóm ToKhai_*, thẻ vào Nyc_*.
    """
    values = {
        "Nyc_HoTen": "HÀ THỊ NGA",
        "Nyc_SoDinhDanh": _CCCD,
        "Nyc_NgaySinh": "01/01/1965",
        "Nyc_GioiTinh": "Nữ",
        "Nyc_NgayCap": "24/12/2024",
        "Nyc_NoiCap": "Bộ Công an",
        "ToKhai_HoTenNguoiDuocCap": "HÀ THỊ NGA",
        "ToKhai_NgaySinh": "01/01/1965",
        "ToKhai_GioiTinh": "Nữ",
        "ToKhai_LoaiSuKien": "birth",
        "ToKhai_TenGiayTo": "Giấy khai sinh",
        "ToKhai_So": "447/2021",
        "ToKhai_NgayDangKy": "06/09/2021",
        "ToKhai_CoQuanDangKy": "Ủy ban nhân dân Xã Đoan Bái, huyện Hiệp Hòa, tỉnh Bắc Giang",
        "ToKhai_SoGiayToTuyThan": _CMND_CU,
        "ToKhai_NgayCapGiayToTuyThan": "09/06/2010",
        "ToKhai_NoiCapGiayToTuyThan": "Công an tỉnh Bắc Giang",
    }
    values.update(overrides)
    return {name: value for name, value in values.items() if value is not None}


def test_muc_II_lay_cccd_thay_vi_cmnd_cu_ghi_tren_to_khai():
    out = _enrich(**_tu_xin_cho_minh())

    assert out["NDK_SoDinhDanh"] == _CCCD
    assert out["NDK_SoGiayToTuyThan"] == _CCCD
    assert out["NDK_NgayCap"] == "24/12/2024"
    assert out["NDK_NoiCap"] == "Bộ Công an"
    assert out["NDK_LoaiGiayToTuyThan"] == "Thẻ Căn cước"


def test_muc_II_khong_tron_so_cccd_voi_ngay_noi_cap_cua_cmnd():
    out = _enrich(**_tu_xin_cho_minh())

    assert out["NDK_NgayCap"] != "09/06/2010"
    assert out["NDK_NoiCap"] != "Công an tỉnh Bắc Giang"


def test_muc_II_the_cua_chinh_chu_the_cung_thang_cmnd_tren_to_khai():
    """Thẻ nằm ở ChuThe_* (chủ thể có thẻ riêng) chứ không phải Nyc_*."""
    out = _enrich(**_tu_xin_cho_minh(
        Nyc_HoTen=None, Nyc_SoDinhDanh=None, Nyc_NgayCap=None, Nyc_NoiCap=None,
        ChuThe_HoTen="HÀ THỊ NGA",
        ChuThe_SoDinhDanh=_CCCD,
        ChuThe_NgaySinh="01/01/1965",
        ChuThe_NgayCap="24/12/2024",
        ChuThe_NoiCap="Bộ Công an",
    ))

    assert out["NDK_SoGiayToTuyThan"] == _CCCD
    assert out["NDK_NgayCap"] == "24/12/2024"
    assert out["NDK_NoiCap"] == "Bộ Công an"


def test_muc_II_to_khai_ghi_cccd_thi_van_theo_to_khai():
    """Hai nguồn cùng hạng → giữ nguyên thứ tự cũ: tờ khai/giấy hộ tịch là nguồn chính."""
    out = _enrich(**_tu_xin_cho_minh(
        ToKhai_SoGiayToTuyThan="024165099999",
        ToKhai_NgayCapGiayToTuyThan="01/02/2023",
        ToKhai_NoiCapGiayToTuyThan="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    ))

    assert out["NDK_SoGiayToTuyThan"] == "024165099999"
    assert out["NDK_NgayCap"] == "01/02/2023"


def test_muc_II_khong_co_the_thi_giu_nguyen_cmnd_cua_to_khai():
    out = _enrich(**_tu_xin_cho_minh(
        Nyc_HoTen=None, Nyc_SoDinhDanh=None, Nyc_NgayCap=None, Nyc_NoiCap=None,
    ))

    assert out["NDK_SoGiayToTuyThan"] == _CMND_CU
    assert out["NDK_NgayCap"] == "09/06/2010"
    assert out["NDK_LoaiGiayToTuyThan"] == "Chứng minh nhân dân"


def test_muc_II_the_cua_nguoi_khac_khong_duoc_dung_cho_chu_the():
    """Người yêu cầu KHÁC người được cấp bản sao → thẻ của họ không được đắp sang mục II."""
    out = _enrich(**_tu_xin_cho_minh(
        Nyc_HoTen="LÊ VĂN BỐN",
        Nyc_SoDinhDanh="036090001234",
    ))

    assert out["NDK_SoGiayToTuyThan"] == _CMND_CU
    assert out["NDK_NgayCap"] == "09/06/2010"


# --------------------------------------------------------------------------------------
# 4. Người chỉ có CMND cũ (rất phổ biến ở hồ sơ người cao tuổi)
# --------------------------------------------------------------------------------------

_CMND_CU_ONLY = "120987132"
_SO_DINH_DANH = "024145012958"


def _chi_co_cmnd(**overrides):
    """Cụ tự đi xin bản sao khai sinh của mình, giấy tờ duy nhất là CMND 9 số."""
    values = {
        "Nyc_HoTen": "HÀ THỊ NGA",
        "Nyc_SoDinhDanh": _CMND_CU_ONLY,
        "Nyc_NgaySinh": "01/01/1945",
        "Nyc_GioiTinh": "Nữ",
        "Nyc_NgayCap": "09/06/2010",
        "Nyc_NoiCap": "Công an tỉnh Bắc Giang",
        "HoTich_LoaiSuKien": "birth",
        "HoTich_TenGiayTo": "Giấy khai sinh",
        "HoTich_HoTenNguoiDuocDangKy": "HÀ THỊ NGA",
        "HoTich_NgaySinh": "01/01/1945",
        "HoTich_GioiTinh": "Nữ",
        "HoTich_CoQuanDangKy": "Ủy ban nhân dân xã Đoan Bái",
        "HoTich_So": "447/2021",
        "HoTich_NgayDangKy": "06/09/2021",
    }
    values.update(overrides)
    return {name: value for name, value in values.items() if value is not None}


_CTX_CU = {"formContext": {
    "applicantFullname": "HÀ THỊ NGA",
    "applicantIdentityNumber": _CMND_CU_ONLY,
}}


def test_chi_co_cmnd_van_dien_du_ca_hai_muc():
    out = _enrich(_CTX_CU, **_chi_co_cmnd())

    assert out["SoDinhDanhC"] == _CMND_CU_ONLY
    assert out["LoaiGiayToDinhDanhC"] == "Chứng minh nhân dân"
    assert out["NgayCapDDC"] == "09/06/2010"
    assert out["NoiCapDDC"] == "Công an tỉnh Bắc Giang"
    assert out["NDK_SoGiayToTuyThan"] == _CMND_CU_ONLY
    assert out["NDK_LoaiGiayToTuyThan"] == "Chứng minh nhân dân"
    assert out["NDK_NgayCap"] == "09/06/2010"


def test_co_so_dinh_danh_tren_giay_khai_sinh_nhung_chi_co_the_cmnd():
    """Số định danh 12 số và CMND 9 số là hai thứ khác nhau — không được gộp làm một giấy tờ."""
    out = _enrich(_CTX_CU, **_chi_co_cmnd(HoTich_SoDinhDanh=_SO_DINH_DANH))

    assert out["NDK_SoDinhDanh"] == _SO_DINH_DANH
    assert out["NDK_SoGiayToTuyThan"] == _CMND_CU_ONLY
    assert out["NDK_LoaiGiayToTuyThan"] == "Chứng minh nhân dân"
    assert out["NDK_NgayCap"] == "09/06/2010"
    assert out["NDK_NoiCap"] == "Công an tỉnh Bắc Giang"


def test_khong_gan_nhan_can_cuoc_cho_so_9_chu_so():
    """Lỗi cũ: nhánh fallback chốt cứng loại 'Căn cước' cho mọi thẻ của người yêu cầu."""
    out = _enrich(_CTX_CU, **_chi_co_cmnd(HoTich_SoDinhDanh=_SO_DINH_DANH))

    assert "ăn cước" not in out["NDK_LoaiGiayToTuyThan"]


def test_chi_co_cmnd_khong_giay_ho_tich_van_dien_duoc():
    out = _enrich(_CTX_CU, **{
        k: v for k, v in _chi_co_cmnd().items() if not k.startswith("HoTich_")
    })

    assert out["SoDinhDanhC"] == _CMND_CU_ONLY
    assert out["LoaiGiayToDinhDanhC"] == "Chứng minh nhân dân"
    assert out["NDK_SoGiayToTuyThan"] == _CMND_CU_ONLY


def test_cmnd_cua_nguoi_yeu_cau_khong_chay_sang_chu_the_khac_nguoi():
    """Cụ dùng CMND đi xin cho con: mục II phải theo giấy khai sinh của con."""
    out = _enrich(_CTX_CU, **_chi_co_cmnd(
        HoTich_HoTenNguoiDuocDangKy="HÀ VĂN BỐN",
        HoTich_NgaySinh="12/03/1979",
        HoTich_GioiTinh="Nam",
        HoTich_SoDinhDanh="024195012345",
    ))

    assert out["SoDinhDanhC"] == _CMND_CU_ONLY
    assert out["NDK_HoVaTen"] == "HÀ VĂN BỐN"
    assert out["NDK_SoDinhDanh"] == "024195012345"
    assert out.get("NDK_SoGiayToTuyThan") != _CMND_CU_ONLY
    assert out.get("NDK_NgayCap") != "09/06/2010"
