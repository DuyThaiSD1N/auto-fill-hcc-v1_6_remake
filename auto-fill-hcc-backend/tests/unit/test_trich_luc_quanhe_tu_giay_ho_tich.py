"""Ô tích quan hệ: lấy vai ghi sẵn trên GIẤY HỘ TỊCH trước khi rơi xuống "Bản thân"/"Khác"."""

from app.pipelines.trich_luc.process import mapper

_SUBJECT_ID = "000000000001"
_FATHER_ID = "000000000002"

_RECORD = [
    {"name": "HoTich_LoaiSuKien", "value": "birth"},
    {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI ĐƯỢC ĐĂNG KÝ"},
    {"name": "HoTich_SoDinhDanh", "value": _SUBJECT_ID},
    {"name": "HoTich_NguoiThan", "value": [
        {"quanHe": "mẹ", "hoTen": "NGƯỜI MẸ"},
        {"quanHe": "cha", "hoTen": "NGƯỜI CHA", "soGiayTo": _FATHER_ID},
    ]},
]


def _quanhe(extra: list[dict], options: dict | None = None):
    out = {f["name"]: f for f in mapper.enrich(_RECORD + extra, options)}
    return out.get("NYC_QuanHe")


def test_khop_so_giay_to_thi_tick_chac_khong_to_vang():
    tick = _quanhe([
        {"name": "Nyc_HoTen", "value": "NGƯỜI CHA"},
        {"name": "Nyc_SoDinhDanh", "value": _FATHER_ID},
    ])

    assert tick["value"] == "Bố Đẻ"
    assert "default" not in tick


def test_khop_ho_ten_thi_van_tick_nhung_to_vang():
    # Người mẹ không có số giấy tờ trên giấy → chỉ khớp được họ tên, có thể trùng tên người khác.
    tick = _quanhe([
        {"name": "Nyc_HoTen", "value": "NGƯỜI MẸ"},
        {"name": "Nyc_SoDinhDanh", "value": "000000000003"},
    ])

    assert tick["value"] == "Mẹ đẻ"
    assert tick["default"] is True


def test_nguoi_yeu_cau_tren_to_khai_cung_duoc_doi_chieu():
    # Hồ sơ có tờ khai nhưng tờ khai KHÔNG ghi dòng quan hệ → vẫn suy được vai từ giấy hộ tịch.
    tick = _quanhe([
        {"name": "TkNyc_HoTen", "value": "NGƯỜI CHA"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": _FATHER_ID},
    ])

    assert tick["value"] == "Bố Đẻ"


def test_to_khai_ghi_quan_he_van_de_len_giay_ho_tich():
    tick = _quanhe([
        {"name": "Nyc_HoTen", "value": "NGƯỜI CHA"},
        {"name": "Nyc_SoDinhDanh", "value": _FATHER_ID},
        {"name": "CopyRequest_QuanHe", "value": "Ông"},
    ])

    assert tick["value"] == "Ông"
    assert "default" not in tick


def test_nguoi_yeu_cau_khong_phai_nguoi_than_thi_giu_hanh_vi_cu():
    tick = _quanhe([
        {"name": "Nyc_HoTen", "value": "NGƯỜI KHÁC"},
        {"name": "Nyc_SoDinhDanh", "value": "000000000009"},
    ])

    assert tick["value"] == "Khác"
    assert tick["default"] is True


def test_nhan_dang_nguoi_cha_nguoi_me_van_nhan_dung_vai():
    out = {f["name"]: f for f in mapper.enrich([
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI ĐƯỢC ĐĂNG KÝ"},
        {"name": "HoTich_NguoiThan", "value": [{"quanHe": "người mẹ", "hoTen": "NGƯỜI MẸ"}]},
        {"name": "Nyc_HoTen", "value": "NGƯỜI MẸ"},
        {"name": "Nyc_SoDinhDanh", "value": "000000000003"},
    ])}

    assert out["NYC_QuanHe"]["value"] == "Mẹ đẻ"


def test_vai_khong_doc_duoc_thi_bo_qua_dong_do():
    out = {f["name"]: f for f in mapper.enrich(_RECORD[:3] + [
        {"name": "HoTich_NguoiThan", "value": [
            {"quanHe": "người khai", "hoTen": "NGƯỜI KHÁC"},   # không phải vai quan hệ
            {"hoTen": "THIẾU VAI"},                            # thiếu quanHe
            "dòng hỏng",                                       # LLM trả rác
        ]},
        {"name": "Nyc_HoTen", "value": "NGƯỜI KHÁC"},
        {"name": "Nyc_SoDinhDanh", "value": "000000000009"},
    ])}

    assert out["NYC_QuanHe"]["value"] == "Khác"


def test_giay_ket_hon_lay_vai_vo_chong():
    out = {f["name"]: f for f in mapper.enrich([
        {"name": "HoTich_LoaiSuKien", "value": "marriage"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI CHỒNG"},
        {"name": "HoTich_NguoiThan", "value": [{"quanHe": "vợ", "hoTen": "NGƯỜI VỢ"}]},
        {"name": "Nyc_HoTen", "value": "NGƯỜI VỢ"},
        {"name": "Nyc_SoDinhDanh", "value": "000000000004"},
    ])}

    assert out["NYC_QuanHe"]["value"] == "Vợ"
