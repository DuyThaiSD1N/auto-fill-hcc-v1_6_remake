"""Ô tích "(5) Quan hệ với người được cấp Giấy XNTTHN" phải LUÔN được chốt.

Cổng bắt buộc ô này (viền đỏ khi trống) nhưng trước đây mapper chỉ tick khi tờ khai ghi rõ chữ
quan hệ, hoặc khi tài khoản VNeID trùng thẻ upload — hồ sơ chỉ có mỗi CCCD thì bỏ trống cả ô tích
lẫn ô kẻ chấm cạnh "Khác". Quy tắc mới: so chính người ở MỤC I với người ở MỤC II — trùng số định
danh hoặc trùng tên → "Bản thân"; khác người → "Khác" kèm chữ quan hệ ở ô cạnh nó.
"""

from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


_CCCD = [
    {"name": "Cccd_HoTen", "value": "NGUYỄN HOÀI NAM"},
    {"name": "Cccd_SoDinhDanh", "value": "001066023420"},
    {"name": "Cccd_NgaySinh", "value": "30/07/1966"},
    {"name": "Cccd_NgayCap", "value": "16/07/2026"},
    {"name": "Cccd_NoiCap", "value": "Bộ Công an"},
]


def test_chi_co_cccd_va_vneid_la_nguoi_khac_van_tick_ban_than():
    """Ca trong ảnh chụp: mục I và mục II cùng là chủ thẻ, ô tích vẫn để trống (viền đỏ).

    Tài khoản VNeID đăng nhập là người khác (cán bộ một cửa nộp hộ trên máy cơ quan) nên
    is_self=False, nhưng mapper vẫn điền CẢ HAI mục bằng thẻ trong hồ sơ → phải là "Bản thân".
    """
    result = _by_name(enrich(list(_CCCD), {"formContext": {
        "applicantFullname": "TRẦN VĂN CÁN",
        "applicantIdentityNumber": "048199000111",
    }}))

    assert result["HoVaTenC"]["value"] == result["HoVaTenC1"]["value"]
    assert result["quanhevoinguoiduocxacminh"]["value"] == "1"
    assert "quanhekhac" not in result


def test_trung_ten_khong_co_so_thi_van_la_ban_than():
    """Tờ khai chỉ ghi tên người yêu cầu, trùng tên người được cấp → cùng một người."""
    fields = list(_CCCD) + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "Nguyễn Hoài Nam"},
        {"name": "ToKhaiYeuCau_NgayCapGiayTo", "value": "16/07/2026"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    result = _by_name(enrich(fields, None))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "1"
    assert "quanhekhac" not in result


def test_khac_so_dinh_danh_thi_tick_khac_du_tron_ten():
    """Trùng tên nhưng khác số định danh là HAI người (tên Việt rất hay trùng)."""
    fields = list(_CCCD) + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001099001234"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    result = _by_name(enrich(fields, None))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
    assert result["quanhekhac"]["value"], 'Tick "Khác" thì ô kẻ chấm cạnh nó không được để trống'


def test_khac_nguoi_ma_to_khai_khong_ghi_quan_he_thi_dien_chu_trung_tinh():
    """Không suy ra được quan hệ thật → điền chữ trung tính và đánh dấu default (viền vàng)."""
    fields = list(_CCCD) + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "Nguyễn Thị Lan"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001199004567"},
        {"name": "ToKhaiYeuCau_NgayCapGiayTo", "value": "02/03/2022"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    result = _by_name(enrich(fields, None))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
    assert result["quanhekhac"]["value"] == "Người thân"
    assert result["quanhekhac"].get("default") is True, "Chữ đoán phải được tô viền vàng để soát lại"


def test_chu_quan_he_tren_to_khai_van_duoc_uu_tien_khi_thieu_so():
    """Tờ khai ghi rõ quan hệ mà OCR rơi mất số người yêu cầu → dùng nguyên chữ khai."""
    fields = list(_CCCD) + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "Nguyễn Thị Lan"},
        {"name": "ToKhaiYeuCau_QuanHe", "value": "là con đẻ"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    result = _by_name(enrich(fields, None))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
    assert result["quanhekhac"]["value"] == "Con đẻ"
    assert result["quanhekhac"].get("default") is not True, "Chữ đọc từ tờ khai không phải giá trị đoán"


def test_o_quan_he_luon_phat_truoc_khoi_nhan_than_muc_i():
    """Cổng dựng lại mục I mỗi lần đổi ô tích: tick SAU sẽ xóa sạch nhân thân vừa điền."""
    fields = list(_CCCD) + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "Nguyễn Thị Lan"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001199004567"},
        {"name": "ToKhaiYeuCau_NgayCapGiayTo", "value": "02/03/2022"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    names = [field["name"] for field in enrich(fields, None)]

    assert names.index("quanhevoinguoiduocxacminh") < names.index("HoVaTenC")
    assert names.index("quanhekhac") < names.index("HoVaTenC"), "Ô 'Khác' phải điền ngay sau khi tick"


def test_uy_quyen_luon_la_khac_va_co_chu_trong_o_ke_cham():
    """Có giấy ủy quyền là chắc chắn hai người; tờ khai không ghi quan hệ thì suy từ giấy."""
    fields = list(_CCCD) + [
        {"name": "PoA_SubjectName", "value": "NGUYỄN THỊ HOA"},
        {"name": "PoA_SubjectIdNumber", "value": "001165000999"},
        {"name": "PoA_SubjectIdDate", "value": "10/05/2021"},
    ]
    result = _by_name(enrich(fields, None))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
    assert result["quanhekhac"]["value"] == "Người được ủy quyền"
