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


_CHU_CO_SO_KHONG_CCCD = [
    _field("DonDeNghi_ChuCoSoHoTen", "NGUYỄN THỊ A"),
    _field("DonDeNghi_DienThoai", "0900000001"),
    # Lấy từ danh sách tập huấn: chỉ có năm sinh.
    _field("Person1_HoTen", "NGUYỄN THỊ A"),
    _field("Person1_SoDinhDanh", "001188000001"),
    _field("Person1_NgaySinh", "1988"),
    _field("Person1_NgayCap", "19/4/2021"),
]


def test_theo_to_khai_nguoi_nop_la_chu_co_so_va_bo_khoa_2_o():
    out, warnings = mapper.enrich(
        _CHU_CO_SO_KHONG_CCCD,
        {"submitterMode": "owner_as_submitter",
         "formContext": {"applicantFullname": "Trần Văn B", "applicantIdentityNumber": "001099000009"}},
    )
    d = {f["name"]: f for f in out}
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is True
    assert d["data[fullname]"]["value"] == "NGUYỄN THỊ A" and d["data[fullname]"].get("enableInput") is True
    assert d["data[identityNumber]"]["value"] == "001188000001" and d["data[identityNumber]"].get("enableInput") is True
    assert d["data[phoneNumber]"]["value"] == "0900000001"
    assert d["data[identityDate]"]["value"] == "19/04/2021"
    # Chỉ có năm sinh → xoá trắng ô ngày sinh cổng đổ sẵn từ tài khoản (không giữ 01/01/<năm>), tô đỏ.
    for name in ("data[birthday]", "data[ownerBirthday]"):
        assert d[name]["value"] == "" and d[name]["clear"] is True and d[name]["markEmpty"] is True
    assert not warnings


def test_theo_tai_khoan_khong_khop_ai_thi_khong_dien_phan_i():
    out, warnings = mapper.enrich(
        _CHU_CO_SO_KHONG_CCCD,
        {"formContext": {"applicantFullname": "Trần Văn B", "applicantIdentityNumber": "001099000009"}},
    )
    d = {f["name"]: f["value"] for f in out}
    assert d["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in d and "data[identityNumber]" not in d
    assert d["data[ownerFullname]"] == "NGUYỄN THỊ A"
    assert not any(f.get("enableInput") for f in out)
    assert any("Không xác định được CCCD người nộp" in w for w in warnings)


def test_khong_co_moc_giu_luong_cu_cccd_duy_nhat_lam_nguoi_nop():
    fields = _CHU_CO_SO_KHONG_CCCD[:2] + [
        _field("Person1_HoTen", "TRẦN VĂN B"),
        _field("Person1_SoDinhDanh", "001099000009"),
    ]
    out, _ = mapper.enrich(fields, {})
    d = {f["name"]: f["value"] for f in out}
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "TRẦN VĂN B"
    assert d["data[ownerFullname]"] == "NGUYỄN THỊ A"


def test_khong_cccd_dia_chi_lay_dia_chi_co_so_don_truoc_roi_nguon_khac_sdt_theo_don():
    area = lambda xa, so: {"tinh": "Lâm Đồng", "xa": xa, "diaChi": so}
    base = [
        _field("DonDeNghi_ChuCoSoHoTen", "NGUYỄN THỊ A"),
        _field("DonDeNghi_DienThoai", "0900000001"),
        _field("CoSoKhac_DienThoai", "0900000002"),
        _field("CoSoKhac_DiaChi", area("Xã Khác", "Số 2")),
    ]
    out, _ = mapper.enrich(base + [_field("DonDeNghi_DiaChiCoSo", area("Xã Đơn", "Số 1"))], {"submitterMode": "owner_as_submitter"})
    d = {f["name"]: f["value"] for f in out}
    assert d["data[address]"] == "Số 1" and d["data[district]"] == "Đơn"
    assert d["data[phoneNumber]"] == "0900000001"

    out, _ = mapper.enrich([f for f in base if f["name"] != "DonDeNghi_DienThoai"], {"submitterMode": "owner_as_submitter"})
    d = {f["name"]: f["value"] for f in out}
    assert d["data[address]"] == "Số 2" and d["data[phoneNumber]"] == "0900000002"
