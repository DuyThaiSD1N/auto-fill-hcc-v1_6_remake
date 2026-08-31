from app.pipelines.trich_luc.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


def test_trich_luc_maps_declaration_relationship_to_radio_label():
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Con đẻ"},
    ]))

    assert result["NYC_QuanHe"]["comp"] == "x-radio"
    assert result["NYC_QuanHe"]["value"] == "Con Đẻ"


def test_trich_luc_does_not_guess_ambiguous_ba_relationship():
    """Chữ mơ hồ trên tờ khai: không đoán vai cụ thể, nhưng cũng không để trống ô tích."""
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Ba"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True


def test_trich_luc_ticks_relationship_before_filling_requester_block():
    """eForm dựng lại mục I + mục II mỗi lần đổi ô tích (5) → radio phải đứng trước nhân thân."""
    names = [field["name"] for field in enrich([
        {"name": "TkNyc_HoTen", "value": "LIỄU THỊ PHỤNG"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024167001234"},
        {"name": "CopyRequest_QuanHe", "value": "Vợ"},
        {"name": "ToKhai_LoaiSuKien", "value": "death"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "LƯƠNG VĂN NGHỊ"},
        {"name": "ToKhai_CoQuanDangKy", "value": "UBND xã Đồng Khởi"},
    ])]

    assert names.index("NYC_QuanHe") < names.index("HoVaTenC")
    assert names.index("NYC_QuanHe") < names.index("NDK_HoVaTen")


def test_trich_luc_declaration_relationship_beats_identity_comparison():
    """Tờ khai ghi rõ quan hệ thì dùng nguyên văn, không suy lại từ việc trùng/khác người."""
    result = _by_name(enrich([
        {"name": "TkNyc_HoTen", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Con đẻ"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Con Đẻ"
    assert "default" not in result["NYC_QuanHe"]


def test_trich_luc_infers_ban_than_from_matching_personal_id():
    result = _by_name(enrich([
        {"name": "TkNyc_SoGiayToTuyThan", "value": "012086005221"},
        {"name": "TkNyc_HoTen", "value": "SÙNG A CO"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "SÙNG A CO"},
        {"name": "ToKhai_SoDinhDanh", "value": "012086005221"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"
    assert "default" not in result["NYC_QuanHe"]


def test_trich_luc_infers_khac_when_requester_differs_from_subject():
    result = _by_name(enrich([
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Nyc_SoDinhDanh", "value": "012345678901"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "TRẦN BÉ"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True


def test_trich_luc_ticks_khac_when_no_source_at_all():
    """Cạn nguồn vẫn phải tick: ô "(5) Quan hệ" không được để trống, mặc định "Khác" (tô vàng)."""
    result = _by_name(enrich([
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "TRẦN BÉ"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True


def test_trich_luc_cmnd_and_personal_id_lengths_do_not_force_khac():
    """CMND 9 số của người yêu cầu vs định danh 12 số của chủ thể: so tên, không so số."""
    result = _by_name(enrich([
        {"name": "TkNyc_SoGiayToTuyThan", "value": "123456789"},
        {"name": "TkNyc_HoTen", "value": "SÙNG A CO"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "SÙNG A CO"},
        {"name": "ToKhai_SoDinhDanh", "value": "012086005221"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"


def test_trich_luc_id_match_beats_unreadable_declaration():
    """Tờ khai ghi quan hệ khó đọc nhưng CCCD mục I trùng mục II → vẫn là "Bản thân"."""
    result = _by_name(enrich([
        {"name": "CopyRequest_QuanHe", "value": "tự mình"},
        {"name": "TkNyc_HoTen", "value": "NGUYỄN DUY THÁI"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "001204018566"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "NGUYỄN DUY THÁI"},
        {"name": "ToKhai_SoDinhDanh", "value": "001204018566"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"
    assert "default" not in result["NYC_QuanHe"]


_KHAI_SINH_CUA_CHINH_MINH = [
    {"name": "Nyc_HoTen", "value": "NGUYỄN DUY THÁI"},
    {"name": "Nyc_SoDinhDanh", "value": "001204018566"},
    {"name": "HoTich_LoaiSuKien", "value": "birth"},
    {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN DUY THÁI"},
    {"name": "HoTich_SoDinhDanh", "value": "001204018566"},
    {"name": "HoTich_NguoiThan", "value": [
        {"quanHe": "Mẹ đẻ", "hoTen": "TRẦN THỊ B", "soGiayTo": "001180001111"},
    ]},
]


def test_trich_luc_id_match_beats_relatives_listed_on_record():
    """Giấy khai sinh có ghi cha/mẹ, nhưng người yêu cầu chính là chủ thể → "Bản thân"."""
    result = _by_name(enrich(list(_KHAI_SINH_CUA_CHINH_MINH), {"formContext": {
        "applicantFullname": "NGUYỄN DUY THÁI",
        "applicantIdentityNumber": "001204018566",
    }}))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"
    assert "default" not in result["NYC_QuanHe"]


def test_trich_luc_the_trung_chu_the_ma_khong_co_moc_vneid_thi_khong_ket_luan():
    """Thẻ trong hồ sơ trùng CHÍNH người được đăng ký: không mỏ neo VNeID thì chưa biết ai đang xin.

    Có thể là tự xin cho mình, cũng có thể là người khác cầm thẻ của chủ thể đi làm hộ — đúng ranh
    giới mà _requester_trusted() đã vạch để quyết có ghi đè mục I hay không. Ô tích phải theo cùng
    một luật: chưa phân biệt được thì "Khác" (tô vàng), không vơ thành "Bản thân".
    """
    result = _by_name(enrich(list(_KHAI_SINH_CUA_CHINH_MINH)))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True


def test_trich_luc_name_match_still_yields_to_role_written_on_record():
    """Cha/con trùng tên, không có số để phân xử: vai ghi trên giấy vẫn thắng so-tên."""
    result = _by_name(enrich([
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN A"},
        {"name": "HoTich_NguoiThan", "value": [
            {"quanHe": "Bố đẻ", "hoTen": "NGUYỄN VĂN A"},
        ]},
    ], {"formContext": {"applicantFullname": "NGUYỄN VĂN A"}}))

    assert result["NYC_QuanHe"]["value"] == "Bố Đẻ"


def test_trich_luc_different_id_stays_khac_even_when_names_match():
    """Hai số định danh cùng độ dài mà khác nhau là bằng chứng khác người, dù trùng họ tên."""
    result = _by_name(enrich([
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Nyc_SoDinhDanh", "value": "001204018566"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN A"},
        {"name": "HoTich_SoDinhDanh", "value": "001990009999"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True


# --- Ca thật: chỉ tải MỘT CCCD của chính mình, không tờ khai, không giấy hộ tịch ---------------
_MOT_CCCD = [
    {"name": "Nyc_HoTen", "value": "NGUYỄN DUY THÁI"},
    {"name": "Nyc_SoDinhDanh", "value": "001204018566"},
    {"name": "Nyc_NgaySinh", "value": "11/08/2004"},
    {"name": "Nyc_GioiTinh", "value": "Nam"},
    {"name": "Nyc_NgayCap", "value": "10/04/2021"},
    {"name": "Nyc_NoiCuTru", "value": "TDP 13 Nhân Mỹ, Phường Từ Liêm, Thành phố Hà Nội"},
]
_VNEID = {"formContext": {
    "applicantFullname": "NGUYỄN DUY THÁI",
    "applicantIdentityNumber": "001204018566",
}}


def test_trich_luc_tu_xin_cho_minh_mot_cccd_tick_ban_than():
    """Mục II được đắp từ CHÍNH thẻ người yêu cầu thì ô (5) phải là "Bản thân", không phải "Khác"."""
    result = _by_name(enrich(list(_MOT_CCCD), _VNEID))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"
    assert "default" not in result["NYC_QuanHe"]
    # Ô tích phải nhất quán với khối mục II mà chính mapper vừa điền.
    assert result["NDK_SoDinhDanh"]["value"] == "001204018566"
    assert result["NDK_HoVaTen"]["value"] == "NGUYỄN DUY THÁI"


def test_trich_luc_mot_cccd_khong_khop_vneid_thi_khong_vo_ban_than():
    """Thẻ trong hồ sơ KHÁC người đăng nhập → không suy "tự xin cho mình" (mục II cũng bỏ trống)."""
    result = _by_name(enrich(list(_MOT_CCCD), {"formContext": {
        "applicantFullname": "TRẦN VĂN B",
        "applicantIdentityNumber": "012345678901",
    }}))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True
    assert "NDK_SoDinhDanh" not in result


def test_trich_luc_the_chu_the_bi_gan_nham_sang_nyc_khong_thanh_ban_than():
    """Ca thật req_6273a23b3b77: agent gán CÙNG thẻ CCCD của chủ thể vào cả Nyc_* lẫn ChuThe_*.

    Người đăng nhập là NGƯỜI KHÁC (mục I do cổng điền từ VNeID, mapper không ghi đè vì thẻ không
    phải của họ). Tin thẳng Nyc_* thì mục I và mục II "trùng số" giả tạo → tick nhầm "Bản thân".
    """
    result = _by_name(enrich([
        {"name": "Nyc_HoTen", "value": "NGUYỄN THỊ HOA"},
        {"name": "Nyc_SoDinhDanh", "value": "024308001989"},
        {"name": "Nyc_NgayCap", "value": "22/12/2022"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Giấy khai sinh"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN THỊ HOÀ"},
        {"name": "HoTich_NgaySinh", "value": "10/09/2008"},
        {"name": "HoTich_NguoiThan", "value": [
            {"quanHe": "cha", "hoTen": "Nguyễn Văn Đức", "soGiayTo": ""},
            {"quanHe": "mẹ", "hoTen": "Chu Thị Hà", "soGiayTo": ""},
        ]},
        {"name": "ChuThe_HoTen", "value": "NGUYỄN THỊ HOA"},
        {"name": "ChuThe_SoDinhDanh", "value": "024308001989"},
        {"name": "ChuThe_NgayCap", "value": "22/12/2022"},
    ], {"formContext": {
        "applicantFullname": "NGUYỄN DUY THÁI",
        "applicantIdentityNumber": "001204018566",
    }}))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True
    # Mục I phải để nguyên dữ liệu VNeID của cổng — không đắp thẻ của chủ thể sang.
    assert "SoDinhDanhC" not in result
    assert result["NDK_SoDinhDanh"]["value"] == "024308001989"
