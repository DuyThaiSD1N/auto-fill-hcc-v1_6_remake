"""Mapper tests for food safety certificate process."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.an_toan_thuc_pham import process as agent
from app.pipelines.an_toan_thuc_pham.process import mapper
from app.pipelines.an_toan_thuc_pham.process.prompt import EXTRA_RULES
from app.pipelines.an_toan_thuc_pham.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def test_an_toan_thuc_pham_registered():
    key = "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham"
    proc = get_procedure(key)

    assert proc
    assert proc["mode"] == "agent"
    assert "Bộ Y tế" in proc["label"]
    assert get_pipeline(key) is agent.run


def test_an_toan_thuc_pham_same_requester_and_owner():
    fields = [
        _field("DonDeNghi_ChuCoSoHoTen", "BÙI THỊ LAN"),
        _field("DonDeNghi_DienThoai", "0984.126.036"),
        _field("Person1_HoTen", "BÙI THỊ LAN"),
        _field("Person1_SoDinhDanh", "034175011744"),
        _field("Person1_NgaySinh", "02/09/1975"),
        _field("Person1_GioiTinh", "Nữ"),
        _field("Person1_NgayCap", "22/04/2021"),
        _field("Person1_NoiCap", "Cục Cảnh sát quản lý hành chính về trật tự xã hội"),
        _field("Person1_NoiCuTru", {"tinh": "Lai Châu", "xa": "Phường Tân Phong", "diaChi": "Tổ 16"}),
        _field("GiayKham_HoTen", "BÙI THỊ LAN"),
        _field("GiayKham_KetLuan", "Sức khỏe loại II"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "Bùi Thị Lan", "applicantIdentityNumber": "034175011744"}},
    )
    d = {f["name"]: f["value"] for f in out}

    assert warnings == []
    assert out[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    assert d["data[fullname]"] == "BÙI THỊ LAN"
    assert d["data[birthday]"] == "02/09/1975"
    assert d["data[identityNumber]"] == "034175011744"
    assert d["data[phoneNumber]"] == "0984126036"
    assert d["data[province]"] == "Lai Châu"
    assert d["data[district]"] == "Tân Phong"
    assert d["data[address]"] == "Tổ 16"
    assert d["data[ownerBirthday]"] == "02/09/1975"
    assert "data[ownerFullname]" not in d
    assert "data[ownerIdentityNumber]" not in d
    names = [field["name"] for field in out]
    assert names.index("data[ownerBirthday]") > names.index("data[birthday]")


def test_an_toan_thuc_pham_different_requester_and_owner():
    fields = [
        _field("DonDeNghi_ChuCoSoHoTen", "BÙI THỊ LAN"),
        _field("DonDeNghi_DienThoai", "0984126036"),
        _field("Person1_HoTen", "VŨ THỊ DUYÊN"),
        _field("Person1_SoDinhDanh", "012168002390"),
        _field("Person1_NgaySinh", "06/07/1968"),
        _field("Person1_GioiTinh", "Nữ"),
        _field("Person1_NgayCap", "09/08/2021"),
        _field("Person1_NoiCap", "Cục Cảnh sát quản lý hành chính về trật tự xã hội"),
        _field("Person1_NoiCuTru", {"tinh": "Lai Châu", "xa": "Phường Tân Phong", "diaChi": "Tổ dân phố Bản Mới"}),
        _field("GiayKham_HoTen", "BÙI THỊ LAN"),
        _field("GiayKham_SoDinhDanh", "034175011744"),
        _field("GiayKham_NgaySinh", "02/09/1975"),
        _field("GiayKham_GioiTinh", "Nữ"),
        _field("GiayKham_NgayCap", "22/04/2021"),
        _field("GiayKham_NoiCap", "Cục Cảnh sát quản lý hành chính về trật tự xã hội"),
        _field("GiayKham_NoiOHienTai", {"tinh": "Lai Châu", "xa": "Phường Tân Phong", "diaChi": "Tổ 16"}),
        _field("GiayKham_KetLuan", "Sức khỏe loại II"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "Vũ Thị Duyên", "applicantIdentityNumber": "012168002390"}},
    )
    d = {f["name"]: f["value"] for f in out}

    assert warnings == []
    assert out[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": False}
    assert d["data[fullname]"] == "VŨ THỊ DUYÊN"
    assert d["data[identityNumber]"] == "012168002390"
    assert d["data[ownerFullname]"] == "BÙI THỊ LAN"
    assert d["data[ownerIdentityNumber]"] == "034175011744"
    assert d["data[ownerPhoneNumber]"] == "0984126036"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Tân Phong"
    assert d["data[ownerAddress]"] == "Tổ 16"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert d["data[ghiChu]"] == "Giấy khám sức khỏe: Sức khỏe loại II"


def test_an_toan_thuc_pham_prompt_locks_sources():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Không trả field UI dạng data[...]" in system_prompt
    assert "Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm" in system_prompt
    assert "không gọi Giấy khám sức khỏe là giám định y khoa" in system_prompt
    assert "DonDeNghi_DiaChiChuCoSo chỉ trả nếu đơn có địa chỉ cư trú" in system_prompt


def test_an_toan_thuc_pham_area_remap():
    """Test remap phường/xã cho thủ tục an toàn thực phẩm."""
    fields = [
        _field("DonDeNghi_ChuCoSoHoTen", "NGUYỄN VĂN A"),
        _field("DonDeNghi_DienThoai", "0987654321"),
        _field("Person1_HoTen", "NGUYỄN VĂN A"),
        _field("Person1_SoDinhDanh", "123456789012"),
        _field("Person1_NgaySinh", "01/01/1980"),
        _field("Person1_GioiTinh", "Nam"),
        _field("Person1_NgayCap", "01/01/2021"),
        _field("Person1_NoiCap", "Cục Cảnh sát quản lý hành chính về trật tự xã hội"),
        # Test remap: Đạ Sar (Lâm Đồng cũ) -> Xã Lạc Dương (Lâm Đồng mới)
        _field("Person1_NoiCuTru", {"tinh": "Lâm Đồng", "xa": "Đạ Sar", "diaChi": "Thôn 1"}),
        _field("GiayKham_HoTen", "NGUYỄN VĂN A"),
        _field("GiayKham_KetLuan", "Sức khỏe loại I"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "123456789012"}},
    )
    d = {f["name"]: f["value"] for f in out}

    assert warnings == []
    assert d["data[fullname]"] == "NGUYỄN VĂN A"
    
    # Kiểm tra remap area: Đạ Sar -> Xã Lạc Dương
    assert d["data[province]"] == "Lâm Đồng"
    assert d["data[district]"] == "Lạc Dương"  # _area_label() sẽ bỏ tiền tố "Xã"
    assert d["data[address]"] == "Thôn 1"
