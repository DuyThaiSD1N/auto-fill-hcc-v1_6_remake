"""Mapper/registry tests cho thủ tục xóa đăng ký tàu cá."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.xoa_dang_ky_tau_ca import process as agent
from app.pipelines.xoa_dang_ky_tau_ca.process import mapper
from app.pipelines.xoa_dang_ky_tau_ca.process.prompt import EXTRA_RULES
from app.pipelines.xoa_dang_ky_tau_ca.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {field["name"]: field["value"] for field in mapped}


def test_xoa_dang_ky_tau_ca_registered():
    key = "xoa-dang-ky-tau-ca"
    procedure = get_procedure(key)

    assert procedure
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlIncludes"] == [
        "apply-online/69394b62da87c4718eca03a3",
        "process=6a588c510c8bb839cdfb06c8",
    ]
    assert get_pipeline(key) is agent.run
    assert get_attach_pipeline(key) is not None


def test_mapper_keeps_unmatched_requester_and_maps_sample_three_roles():
    fields = [
        _field("NguoiDeNghi_HoTen", "HUỲNH THỊ HỒNG"),
        _field("NguoiDeNghi_NgaySinh", "26/9/1970"),
        _field("NguoiDeNghi_GioiTinh", "Nữ"),
        _field("NguoiDeNghi_SoDinhDanh", "0481 7000 0955"),
        _field("NguoiDeNghi_NgayCap", "22-04-2021"),
        _field("NguoiDeNghi_NoiCap", "Cục Cảnh sát QLHC về TTXH"),
        _field("NguoiDeNghi_ThuongTru", {
            "quocGia": "Việt Nam",
            "tinh": "Đà Nẵng",
            "xa": "An Hải Tây",
            "diaChi": "05 An Mỹ 5, Tổ 10",
        }),
        _field("NguoiDeNghi_DiaChiDayDu", "05 An Mỹ 5, Tổ 10, An Hải Tây, Sơn Trà, Đà Nẵng"),
        _field("ToKhai_KinhGui", "Chi cục Biển đảo và Thủy sản Đà Nẵng"),
        _field("ToKhai_LoaiTau", "tau_ca"),
        _field("ToKhai_NgayXoa", "25/06/2026"),
        _field("ChuTau_HoTen", "TRẦN VĂN TIẾP"),
        _field("ChuTau_DiaChi", "Nại Hiền Đông, Sơn Trà, Đà Nẵng"),
        _field("Tau_NoiDangKy", "Chi cục Thủy sản TP Đà Nẵng"),
        _field("Tau_SoDangKy", "ĐNA-90933-TS"),
        _field("Tau_NgayDangKy", "27/8/2024"),
        _field("Tau_CoQuanDangKy", "Chi cục Thủy sản TP Đà Nẵng"),
        _field("ToKhai_LyDoXoa", "Mua bán trong tỉnh"),
        _field("ToKhai_DiaDanh", "Đà Nẵng"),
        _field("ToKhai_NgayKhai", "25/6/2026"),
        _field("ToKhai_NguoiKy", "HUỲNH THỊ HỒNG"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "Nhâm Đắc Đạt", "applicantIdentityNumber": "034203010212"}},
    )
    data = _values(out)
    form = "data[toKhaiDangKyTamThoiTauCa_Mau08]"

    assert warnings == [
        "Không có CCCD upload khớp cả họ tên và số định danh người nộp; giữ nguyên Phần I."
    ]
    # CCCD trong PDF là của chủ hồ sơ, tuyệt đối không ghi đè người nộp tài khoản.
    assert "data[fullname]" not in data
    assert "data[identityNumber]" not in data
    assert data["data[isOwnerDossierCheck]"] is False
    assert data["data[ownerFullname]"] == "HUỲNH THỊ HỒNG"
    assert data["data[ownerIdentityNumber]"] == "048170000955"
    assert data["data[ownerBirthday]"] == "26/09/1970"
    assert data["data[ownerProvince]"] == "Thành phố Đà Nẵng"
    assert data["data[ownerDistrict]"] == "Phường An Hải"
    assert data["data[ownerAddress]"] == "05 An Mỹ 5, Tổ 10"

    # Chủ sở hữu trong Tờ khai là chủ tàu cũ/bên bán, không phải chủ hồ sơ/bên mua.
    assert data[f"{form}[fullname]"] == "TRẦN VĂN TIẾP"
    assert data[f"{form}[address]"] == "Nại Hiên Đông, Sơn Trà, Đà Nẵng"
    assert data[f"{form}[tenNguoiDNXoa]"] == "HUỲNH THỊ HỒNG"
    assert data[f"{form}[diaChiNguoiXoa]"] == "05 An Mỹ 5, Tổ 10, Phường An Hải, Thành phố Đà Nẵng"
    assert data[f"{form}[TiLeSoHuu]"] == "100"
    assert data[f"{form}[deNghi]"] == "Tàu cá/Vessel"
    assert data[f"{form}[SoDangKy]"] == "ĐNa-90933-TS"
    assert data[f"{form}[ngayDK]"] == "27/08/2024"
    assert data[f"{form}[diaDanh]"] == "Thành phố Đà Nẵng"
    assert data[f"{form}[chuCS]"] == "HUỲNH THỊ HỒNG"
    assert f"{form}[Ten]" not in data
    assert f"{form}[HoHieuSoImo]" not in data


def test_mapper_confirms_requester_by_name_and_identity_from_uploaded_cccd():
    fields = [
        _field("Cccd1_HoTen", "VŨ ĐÌNH THIẾT"),
        _field("Cccd1_SoDinhDanh", "0402 0301 5844"),
        _field("Cccd1_NgaySinh", "26/04/2003"),
        _field("Cccd1_GioiTinh", "Nam"),
        _field("Cccd1_NgayCap", "02/07/2021"),
        _field("Cccd1_NoiCap", "Cục Cảnh sát QLHC về TTXH"),
        _field("Cccd1_ThuongTru", {
            "quocGia": "Việt Nam",
            "tinh": "Nghệ An",
            "xa": "Xã Tam Hợp",
            "diaChi": "Xóm Long Thành",
        }),
        _field("Cccd2_HoTen", "HUỲNH THỊ HỒNG"),
        _field("Cccd2_SoDinhDanh", "0481 7000 0955"),
        _field("NguoiDeNghi_HoTen", "HUỲNH THỊ HỒNG"),
        _field("NguoiDeNghi_SoDinhDanh", "048170000955"),
        _field("ChuTau_HoTen", "TRẦN VĂN TIẾP"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )
    data = _values(out)

    assert warnings == []
    assert data["data[fullname]"] == "Vũ Đình Thiết"
    assert data["data[birthday]"] == "26/04/2003"
    assert data["data[gender]"] == "Nam"
    assert data["data[identityNumber]"] == "040203015844"
    assert data["data[identityDate]"] == "02/07/2021"
    assert data["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert data["data[province]"] == "Tỉnh Nghệ An"
    assert data["data[district]"] == "Xã Tam Hợp"
    assert data["data[address]"] == "Xóm Long Thành"
    assert "data[phoneNumber]" not in data
    assert "data[email]" not in data
    assert "data[fax]" not in data
    assert data["data[ownerFullname]"] == "HUỲNH THỊ HỒNG"
    assert data["data[ownerIdentityNumber]"] == "048170000955"
    assert data["data[toKhaiDangKyTamThoiTauCa_Mau08][fullname]"] == "TRẦN VĂN TIẾP"


def test_mapper_same_hong_requester_and_owner_ticks_owner_checkbox():
    fields = [
        _field("Cccd1_HoTen", "HUỲNH THỊ HỒNG"),
        _field("Cccd1_SoDinhDanh", "0481 7000 0955"),
        _field("Cccd1_NgaySinh", "26/09/1970"),
        _field("Cccd1_GioiTinh", "Nữ"),
        _field("Cccd1_NgayCap", "23/04/2021"),
        _field("Cccd1_NoiCap", "Cục Cảnh sát QLHC về TTXH"),
        _field("Cccd1_ThuongTru", {
            "quocGia": "Việt Nam",
            "tinh": "Đà Nẵng",
            "xa": "An Hải Tây",
            "diaChi": "05 An Mỹ 5, Tổ 10",
        }),
        _field("NguoiDeNghi_HoTen", "HUỲNH THỊ HỒNG"),
        _field("NguoiDeNghi_NgaySinh", "26/09/1970"),
        _field("NguoiDeNghi_GioiTinh", "Nữ"),
        _field("NguoiDeNghi_SoDinhDanh", "048170000955"),
        _field("NguoiDeNghi_NgayCap", "23/04/2021"),
        _field("NguoiDeNghi_NoiCap", "Cục Cảnh sát QLHC về TTXH"),
        _field("NguoiDeNghi_ThuongTru", {
            "quocGia": "Việt Nam",
            "tinh": "Đà Nẵng",
            "xa": "An Hải Tây",
            "diaChi": "05 An Mỹ 5, Tổ 10",
        }),
        _field("NguoiDeNghi_DiaChiDayDu", "05 An Mỹ 5, Tổ 10, An Hải Tây, Sơn Trà, Đà Nẵng"),
        _field("ChuTau_HoTen", "TRẦN VĂN TIẾP"),
        _field("ToKhai_NguoiKy", "HUỲNH THỊ HỒNG"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {
            "applicantFullname": "Huỳnh Thị Hồng",
            "applicantIdentityNumber": "048170000955",
        }},
    )
    data = _values(out)

    assert warnings == []
    assert data["data[fullname]"] == "Huỳnh Thị Hồng"
    assert data["data[birthday]"] == "26/09/1970"
    assert data["data[gender]"] == "Nữ"
    assert data["data[identityNumber]"] == "048170000955"
    assert data["data[identityDate]"] == "23/04/2021"
    assert data["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert data["data[province]"] == "Thành phố Đà Nẵng"
    assert data["data[district]"] == "Phường An Hải"
    assert data["data[address]"] == "05 An Mỹ 5, Tổ 10"

    # FE dùng checkbox này để sao chép Phần I sang chủ hồ sơ; không gửi bộ owner* trùng lặp.
    assert data["data[isOwnerDossierCheck]"] is True
    assert "data[ownerFullname]" not in data
    assert "data[ownerIdentityNumber]" not in data

    form = "data[toKhaiDangKyTamThoiTauCa_Mau08]"
    assert data[f"{form}[tenNguoiDNXoa]"] == "HUỲNH THỊ HỒNG"
    assert data[f"{form}[fullname]"] == "TRẦN VĂN TIẾP"


def test_mapper_does_not_fill_requester_when_only_name_matches():
    fields = [
        _field("Cccd1_HoTen", "VŨ ĐÌNH THIẾT"),
        _field("Cccd1_SoDinhDanh", "040203015844"),
        _field("NguoiDeNghi_HoTen", "HUỲNH THỊ HỒNG"),
        _field("NguoiDeNghi_SoDinhDanh", "048170000955"),
        _field("ChuTau_HoTen", "TRẦN VĂN TIẾP"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {
            "applicantFullname": "VŨ ĐÌNH THIẾT",
            "applicantIdentityNumber": "040203015999",
        }},
    )
    data = _values(out)

    assert "data[fullname]" not in data
    assert "data[identityNumber]" not in data
    assert "data[birthday]" not in data
    assert "data[identityDate]" not in data
    assert "data[province]" not in data
    assert data["data[ownerFullname]"] == "HUỲNH THỊ HỒNG"
    assert warnings == [
        "Không có CCCD upload khớp cả họ tên và số định danh người nộp; giữ nguyên Phần I."
    ]


def test_mapper_does_not_infer_requester_without_complete_form_context():
    fields = [
        _field("Cccd1_HoTen", "VŨ ĐÌNH THIẾT"),
        _field("Cccd1_SoDinhDanh", "040203015844"),
        _field("NguoiDeNghi_HoTen", "HUỲNH THỊ HỒNG"),
        _field("ChuTau_HoTen", "TRẦN VĂN TIẾP"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "VŨ ĐÌNH THIẾT"}},
    )
    data = _values(out)

    assert "data[fullname]" not in data
    assert "data[identityNumber]" not in data
    assert "data[birthday]" not in data
    assert "data[identityDate]" not in data
    assert "data[province]" not in data
    assert data["data[ownerFullname]"] == "HUỲNH THỊ HỒNG"
    assert warnings == [
        "Không nhận đủ họ tên và CCCD người nộp từ biểu mẫu; giữ nguyên Phần I."
    ]


def test_mapper_does_not_default_ratio_for_multiple_current_owners():
    out, _ = mapper.enrich([
        _field("NguoiDeNghi_HoTen", "NGUYỄN VĂN A"),
        _field("ChuTau_HoTen", "TRẦN VĂN B và LÊ THỊ C"),
    ])
    data = _values(out)

    assert "data[toKhaiDangKyTamThoiTauCa_Mau08][TiLeSoHuu]" not in data


def test_prompt_locks_buyer_seller_and_requester_roles():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "NGƯỜI NỘP HỒ SƠ" in system_prompt
    assert "NGƯỜI ĐỀ NGHỊ XÓA = CHỦ HỒ SƠ = BÊN MUA" in system_prompt
    assert "CHỦ TÀU ĐANG ĐỨNG TÊN GCN = BÊN BÁN" in system_prompt
    assert "Cccd1_* và Cccd2_*" in system_prompt
    assert "Không lấy\n  số CCCD chỉ được nhắc trong Hợp đồng hoặc Lời chứng" in system_prompt
    assert "NgaySinh, GioiTinh, NgayCap, NoiCap và ThuongTru" in system_prompt
    schema_names = {field["name"] for field in FIELDS}
    assert {
        "Cccd1_NgaySinh", "Cccd1_GioiTinh", "Cccd1_NgayCap", "Cccd1_NoiCap", "Cccd1_ThuongTru",
        "Cccd2_NgaySinh", "Cccd2_GioiTinh", "Cccd2_NgayCap", "Cccd2_NoiCap", "Cccd2_ThuongTru",
    } <= schema_names
    assert "ĐNa-90933-TS" in system_prompt
    assert "KHÔNG trả field UI dạng data[...]" in system_prompt
