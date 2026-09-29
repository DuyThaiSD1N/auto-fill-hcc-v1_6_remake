"""[Lào Cai] 1.011443.H38 — khối NGƯỜI NỘP theo hai chế độ (kế thừa mapper 1.115650).

Tài khoản: không ghi hai ô readonly Họ tên/Số Căn cước. Tờ khai: hai ô đó đứng đầu khối, nhân thân tài
khoản mà hồ sơ không có thì xoá; bộ lọc ô ẩn theo đối tượng (CN/DN) chỉ đụng khối chủ hồ sơ. Dữ liệu giả.
"""

from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_lao_cai.process import mapper
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_lao_cai.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)

_NGUOI_KHAC = {
    "HoTen": "Lê Văn Khác", "SoDinhDanh": "001080000099", "NgaySinh": "01/02/1980", "GioiTinh": "Nam",
    "NgayCap": "03/04/2021", "NoiCap": "Bộ Công an", "DienThoai": "0900000099",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Số 99"},
}
_FACTS_CA_NHAN = [
    {"name": "ChuHoSo_HoTen", "value": "Phạm Thị Giả"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001170000011"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    {"name": "NguoiNop_HoTen", "value": "Phạm Thị Giả"},
    {"name": "NguoiNop_SoDinhDanh", "value": "001170000011"},
    {"name": "NguoiNop_NgaySinh", "value": "1970"},
    {"name": "NguoiTrongGiayTo", "value": [_NGUOI_KHAC]},
]
_FACTS_DOANH_NGHIEP = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY GIẢ ĐỊNH"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Văn Ký"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 2"}},
    {"name": "NguoiNop_HoTen", "value": "Trần Văn Ký"},
    {"name": "NguoiNop_GioiTinh", "value": "Nam"},
    {"name": "NguoiTrongGiayTo", "value": [_NGUOI_KHAC]},
]
_TK_KHAC = {"applicantFullname": "NGUYỄN TÀI KHOẢN", "applicantIdentityNumber": "001199000001"}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _congdan(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ca_nhan_ho_ten_can_cuoc_dung_dau_va_xoa_o_ho_so_khong_co():
    fields, _ = mapper.enrich(
        _FACTS_CA_NHAN, {"submitterMode": "owner_as_submitter", "formContext": _TK_KHAC}
    )
    values = _values(fields)

    assert _congdan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Phạm Thị Giả"
    assert values["CongDan_soCmnd"] == "001170000011"
    cleared = {f["name"] for f in fields if f.get("clear")}
    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_diDong", "CongDan_fax"):
        assert name in cleared and values[name] == "", name
    for foreign in ("001080000099", "01/02/1980", "03/04/2021", "0900000099"):
        assert foreign not in values.values(), foreign


def test_to_khai_doanh_nghiep_loc_o_an_khong_dung_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS_DOANH_NGHIEP, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert not INDIVIDUAL_ONLY_FIELDS & set(values)
    assert _congdan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    # Người ký không có số định danh → ô căn cước tài khoản bị xoá, không để sót.
    assert fields[[f["name"] for f in fields].index("CongDan_soCmnd")] == {
        "name": "CongDan_soCmnd", "comp": UI_COMP_BY_NAME["CongDan_soCmnd"], "value": "", "clear": True, "markEmpty": True,
    }
    assert all(f["name"].startswith("CongDan_") for f in fields if f.get("clear"))
    assert "001080000099" not in values.values()


def test_tai_khoan_khong_ghi_hai_o_readonly_va_khong_xoa_o_nao():
    for facts in (_FACTS_CA_NHAN, _FACTS_DOANH_NGHIEP):
        fields, _ = mapper.enrich(facts, {"formContext": {
            "applicantFullname": "LÊ VĂN KHÁC", "applicantIdentityNumber": "001080000099",
        }})
        assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_values(fields))
        assert not any(f.get("clear") for f in fields)
