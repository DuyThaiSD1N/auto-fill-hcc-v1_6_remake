"""[Lào Cai] 1.115680 (cấp xã) — khối NGƯỜI NỘP theo hai chế độ.

Tài khoản: không ghi hai ô readonly Họ tên/Số Căn cước (cổng đã đổ đúng). Tờ khai: hai ô đó đứng đầu
khối, nhân thân tài khoản mà hồ sơ không có thì xoá để khối không thành nửa tài khoản nửa hồ sơ.
Dữ liệu giả.
"""

from app.pipelines.dieu_chinh_giao_dat_cap_xa_lao_cai.process import mapper
from app.pipelines.dieu_chinh_giao_dat_cap_xa_lao_cai.process.schema import UI_COMP_BY_NAME

_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "Phạm Thị Giả"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    {"name": "NguoiNop_HoTen", "value": "Phạm Thị Giả"},
    {"name": "NguoiNop_SoDinhDanh", "value": "001170000011"},
    {"name": "NguoiNop_NgaySinh", "value": "1970"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Lê Văn Khác", "SoDinhDanh": "001080000099", "NgaySinh": "01/02/1980",
         "GioiTinh": "Nam", "NgayCap": "03/04/2021", "NoiCap": "Bộ Công an", "DienThoai": "0900000099",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Số 99"}},
    ]},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_to_khai_ho_ten_can_cuoc_dung_dau_va_xoa_nhan_than_tai_khoan_ho_so_khong_co():
    fields, warnings = mapper.enrich(_FACTS, {
        "submitterMode": "owner_as_submitter",
        "formContext": {"applicantFullname": "NGUYỄN TÀI KHOẢN", "applicantIdentityNumber": "001199000001"},
    })
    values = _values(fields)
    names = [f["name"] for f in fields if f["name"].startswith("CongDan_")]

    assert names[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Phạm Thị Giả"
    assert values["CongDan_soCmnd"] == "001170000011"
    cleared = {f["name"] for f in fields if f.get("clear")}
    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_diDong",
                 "CongDan_danTocCongDan", "CongDan_email", "CongDan_fax"):
        assert name in cleared and values[name] == "", name
    for foreign in ("001080000099", "01/02/1980", "03/04/2021", "0900000099"):
        assert foreign not in values.values(), foreign
    assert any("tài khoản đang đăng nhập" in w for w in warnings)


def test_to_khai_khong_co_so_dinh_danh_thi_xoa_o_can_cuoc_ngay_sau_ho_ten():
    facts = [f for f in _FACTS if f["name"] != "NguoiNop_SoDinhDanh"]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    congdan = [f for f in fields if f["name"].startswith("CongDan_")]

    assert congdan[0]["name"] == "CongDan_tenCongDan"
    assert congdan[1] == {"name": "CongDan_soCmnd", "comp": UI_COMP_BY_NAME["CongDan_soCmnd"],
                          "value": "", "clear": True, "markEmpty": True}


def test_tai_khoan_khong_ghi_hai_o_readonly_va_khong_xoa_o_nao():
    fields, _ = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "LÊ VĂN KHÁC", "applicantIdentityNumber": "001080000099",
    }})
    values = _values(fields)

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(values)
    assert not any(f.get("clear") for f in fields)
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1980"
