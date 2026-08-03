"""Mapper/registry tests cho cấp GCN ATTP nông, lâm, thủy sản."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san import process as agent
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process import mapper
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process.prompt import EXTRA_RULES
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _value(fields: list[dict], name: str, occurrence=None):
    return next(
        field["value"]
        for field in fields
        if field["name"] == name and field.get("occurrence") == occurrence
    )


def _base_application_fields() -> list[dict]:
    return [
        _field("Don_DiaDanh", "Đà Nẵng"),
        _field("Don_NgayDon", "16/04/2026"),
        _field("Don_KinhGui", "Chi cục Biển đảo và Thủy sản thành phố Đà Nẵng"),
        _field("Don_TenCoSo", "Đặng Minh Hoàng – Tàu cá ĐNA 90679"),
        _field("Don_DiaChiCoSo", {
            "quocGia": "Việt Nam",
            "tinh": "Đà Nẵng",
            "xa": "Phường An Hải",
            "diaChi": "",
        }),
        _field("Don_DienThoai", "0973.329.308"),
        _field("Don_MaSoDKKD", "32C8019879"),
        _field("Don_SoDangKy", "Đăng ký lần đầu"),
        _field("Don_NgayCapDKKD", "14/04/2025"),
        _field("DangKy_NoiCap", "Phòng Tài chính - Kế hoạch thành phố Đà Nẵng"),
        _field("Don_MatHang", "Hải sản"),
        _field("Don_LyDoCap", "Cấp mới"),
        _field("Don_DaiDienCoSo", "ĐẶNG MINH HOÀNG"),
    ]


def test_cap_gcn_attp_nong_lam_thuy_san_registered():
    key = "cap-gcn-attp-nong-lam-thuy-san"
    procedure = get_procedure(key)

    assert procedure
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlIncludes"] == [
        "apply-online/693a99efda87c4718ece1bc7",
        "process=695dbb6de184634c1f3648af",
    ]
    assert "nông, lâm, thủy sản" in procedure["label"]
    assert get_pipeline(key) is agent.run
    assert get_attach_pipeline(key) is not None


def test_mapper_maps_different_requester_owner_and_application_occurrences():
    fields = [
        _field("Person1_HoTen", "VŨ ĐÌNH THIẾT"),
        _field("Person1_SoDinhDanh", "0402 0301 5844"),
        _field("Person1_NgaySinh", "26/04/2003"),
        _field("Person1_GioiTinh", "Nam"),
        _field("Person1_NgayCap", "02/07/2021"),
        _field("Person1_NoiCap", "Cục Cảnh sát QLHC về TTXH"),
        _field("Person1_NoiCuTru", {
            "quocGia": "Việt Nam",
            "tinh": "Nghệ An",
            "xa": "Xã Tam Hợp",
            "diaChi": "Xóm Long Thành",
        }),
        _field("Person2_HoTen", "ĐẶNG MINH HOÀNG"),
        _field("Person2_SoDinhDanh", "048075012345"),
        _field("Person2_NgaySinh", "15/08/1975"),
        _field("Person2_GioiTinh", "Nam"),
        _field("Person2_NgayCap", "20/06/2021"),
        _field("Person2_NoiCap", "Cục Cảnh sát QLHC về TTXH"),
        _field("Person2_NoiCuTru", {
            "quocGia": "Việt Nam",
            "tinh": "Đà Nẵng",
            "xa": "Phường An Hải",
            "diaChi": "Tổ 12",
        }),
        *_base_application_fields(),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )

    assert warnings == []
    assert _value(out, "data[chonDoiTuong]") == "Cá nhân"
    assert next(field for field in out if field["name"] == "data[chonDoiTuong]")["default"] is True
    assert _value(out, "data[isOwnerDossierCheck]") is False
    assert _value(out, "data[fullname]") == "Vũ Đình Thiết"
    assert _value(out, "data[identityNumber]") == "040203015844"
    assert _value(out, "data[address]", occurrence=0) == "Xóm Long Thành"

    assert _value(out, "data[ownerFullname]") == "ĐẶNG MINH HOÀNG"
    assert _value(out, "data[ownerIdentityNumber]") == "048075012345"
    assert _value(out, "data[ownerProvince]") == "Thành phố Đà Nẵng"
    assert _value(out, "data[ownerDistrict]") == "Phường An Hải"
    assert _value(out, "data[ownerAddress]") == "Tổ 12"
    assert _value(out, "data[ownerPhoneNumber]") == "0973329308"

    assert _value(out, "data[diaDanh]") == "Thành phố Đà Nẵng"
    assert _value(out, "data[ngayBC]") == "16/04/2026"
    assert _value(out, "data[kinhGui1]") == "Chi cục Biển đảo và Thủy sản thành phố Đà Nẵng"
    assert _value(out, "data[organization]", occurrence=0) == "Đặng Minh Hoàng – Tàu cá ĐNA 90679"
    assert _value(out, "data[address]", occurrence=1) == "Phường An Hải, Thành phố Đà Nẵng"
    assert _value(out, "data[phoneNumber]", occurrence=1) == "0973329308"
    assert _value(out, "data[maso]") == "32C8019879"
    assert _value(out, "data[soGDK]") == "Đăng ký lần đầu"
    assert _value(out, "data[ngayCap]") == "14/04/2025"
    assert _value(out, "data[noiCap]") == "Phòng Tài chính - Kế hoạch thành phố Đà Nẵng"
    assert _value(out, "data[mathangsx]") == "Hải sản"
    assert _value(out, "data[lydocaplai]") == "Cấp mới"
    assert _value(out, "data[daidiencoso]") == "ĐẶNG MINH HOÀNG"


def test_mapper_same_requester_and_owner_checks_copy_box():
    fields = [
        _field("Person1_HoTen", "ĐẶNG MINH HOÀNG"),
        _field("Person1_SoDinhDanh", "048075012345"),
        _field("Person1_NgaySinh", "15/08/1975"),
        _field("Person1_GioiTinh", "Nam"),
        _field("Person1_NgayCap", "20/06/2021"),
        _field("Person1_NoiCuTru", {
            "quocGia": "Việt Nam",
            "tinh": "Đà Nẵng",
            "xa": "Phường An Hải",
            "diaChi": "Tổ 12",
        }),
        *_base_application_fields(),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {
            "applicantFullname": "Đặng Minh Hoàng",
            "applicantIdentityNumber": "048075012345",
        }},
    )

    assert warnings == []
    assert _value(out, "data[isOwnerDossierCheck]") is True
    assert _value(out, "data[fullname]") == "Đặng Minh Hoàng"
    assert _value(out, "data[identityNumber]") == "048075012345"
    assert not any(field["name"] == "data[ownerFullname]" for field in out)
    assert _value(out, "data[organization]", occurrence=0) == "Đặng Minh Hoàng – Tàu cá ĐNA 90679"


def test_mapper_keeps_owner_when_requester_cccd_does_not_match_context():
    fields = [
        _field("Person1_HoTen", "ĐẶNG MINH HOÀNG"),
        _field("Person1_SoDinhDanh", "048075012345"),
        *_base_application_fields(),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )

    assert warnings == [
        "Không có đúng một CCCD upload khớp cả họ tên và số định danh người nộp; giữ nguyên Phần I."
    ]
    assert not any(field["name"] == "data[fullname]" for field in out)
    assert _value(out, "data[isOwnerDossierCheck]") is False
    assert _value(out, "data[ownerFullname]") == "ĐẶNG MINH HOÀNG"
    assert _value(out, "data[organization]", occurrence=0) == "Đặng Minh Hoàng – Tàu cá ĐNA 90679"


def test_prompt_locks_facility_representative_and_source_priority():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Không trả field UI dạng data[...]" in system_prompt
    assert "Don_TenCoSo" in system_prompt
    assert "Don_DaiDienCoSo" in system_prompt
    assert "Hai field này là hai khái niệm khác nhau" in system_prompt
    assert "Điện thoại của cơ sở" in system_prompt
    assert "Python sẽ đối chiếu cả họ tên và số định danh với formContext" in system_prompt
    assert "Không trích toàn bộ các bảng thiết bị" in system_prompt

