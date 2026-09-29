"""[Lào Cai] 1.115682 — hai chế độ xác định NGƯỜI NỘP.

Mặc định (toggle tắt) giữ nguyên hành vi theo tài khoản: chỉ điền nhân thân khối người nộp khi khớp mốc
`options.formContext`. Bật "Người nộp = chủ hồ sơ" (`submitterMode="owner_as_submitter"`) thì người nộp lấy
theo tờ khai: khối NguoiNop_* (bên được ủy quyền) → không có thì chủ hồ sơ cá nhân; hai ô readonly Họ tên/Số
Căn cước ghi theo người đó, ô nhân thân tài khoản mà hồ sơ không có thì xoá.
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process import mapper

_CHU_HO_SO = "001099000001"
_NGUOI_NOP = "001199000002"
_NGUOI_KHAC = "001088000003"

_CHU_HO_SO_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1985"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_DanToc", "value": "Kinh"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0912000001"},
]

_NGUOI_NOP_FACTS = [
    {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _NGUOI_NOP},
    {"name": "NguoiNop_NgaySinh", "value": "05/06/1990"},
    {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
    {"name": "NguoiNop_NgayCap", "value": "01/02/2022"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000002"},
    {"name": "UyQuyen_SoGiay", "value": "12/2025"},
]

_UY_QUYEN = _CHU_HO_SO_FACTS + _NGUOI_NOP_FACTS
_TO_KHAI = {"submitterMode": "owner_as_submitter"}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _trong(values, name):
    """Ô không mang giá trị: không phát, hoặc phát lệnh xoá (value "") để bỏ nhân thân tài khoản."""
    return values.get(name, "") == ""


def test_toggle_tat_giu_hanh_vi_theo_tai_khoan():
    fields, warnings = mapper.enrich(_UY_QUYEN, _ctx("TRẦN THỊ B", _NGUOI_NOP))
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "05/06/1990"
    assert values["CongDan_diDong"] == "0912000002"
    assert values["CongDan_diaChi"] == "Tổ 5"
    # Nộp thay: không chép dân tộc của chủ hồ sơ sang người nộp.
    assert "CongDan_danTocCongDan" not in values
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    # submitterMode lạ/trống = toggle tắt → kết quả y hệt.
    assert mapper.enrich(_UY_QUYEN, {**_ctx("TRẦN THỊ B", _NGUOI_NOP), "submitterMode": ""}) == (
        fields, warnings)


def test_toggle_tat_khong_co_moc_van_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_UY_QUYEN, {})
    values = _values(fields)

    assert not [name for name in values if name.startswith("CongDan_")]
    assert any("Chưa đọc được tài khoản" in w for w in warnings)


def test_to_khai_co_uy_quyen_lay_ben_duoc_uy_quyen_va_canh_bao_lech_tai_khoan():
    fields, warnings = mapper.enrich(_UY_QUYEN, {**_ctx("LÊ VĂN C", _NGUOI_KHAC), **_TO_KHAI})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "05/06/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_ngayCapCmnd"] == "01/02/2022"
    assert values["CongDan_diDong"] == "0912000002"
    assert "Cam Đường" in values["CongDan_maPhuongXa"]
    assert values["CongDan_diaChi"] == "Tổ 5"
    # Dân tộc "Kinh" là của chủ hồ sơ (số định danh khác) → không được lấy sang.
    assert _trong(values, "CongDan_danTocCongDan")
    # Hai ô readonly ghi theo bên được ủy quyền.
    assert values["CongDan_tenCongDan"] == "TRẦN THỊ B"
    assert values["CongDan_soCmnd"] == _NGUOI_NOP
    # Khối chủ hồ sơ giữ nguyên, không lẫn người nộp.
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0912000001"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Tổ 1"
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)
    assert not any("Chưa đọc được tài khoản" in w or "KHÔNG có giấy tờ tuỳ thân" in w for w in warnings)


def test_to_khai_trung_tai_khoan_thi_khong_canh_bao_lech():
    _, warnings = mapper.enrich(_UY_QUYEN, {**_ctx("Trần Thị B", _NGUOI_NOP), **_TO_KHAI})

    assert not any("TỜ KHAI" in w for w in warnings)


def test_to_khai_khong_co_uy_quyen_lay_chu_ho_so_ca_nhan():
    fields, warnings = mapper.enrich(_CHU_HO_SO_FACTS, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_diDong"] == "0912000001"
    assert values["CongDan_diaChi"] == "Tổ 1"
    # Chủ hồ sơ chỉ có năm sinh → không phát ngày sinh, không bịa 01/01.
    assert _trong(values, "CongDan_ngaySinhCongDan")
    assert "ChuHoSo_ngaySinhChuHoSo" not in values
    # Không có mốc tài khoản → không có cảnh báo kiểu "thiếu mốc" ở chế độ tờ khai.
    assert not any("tài khoản" in w for w in warnings)


def test_to_khai_gop_nhan_than_cung_nguoi_khong_lay_cua_nguoi_khac_so():
    # Khối người nộp chỉ chép tên + số của chủ hồ sơ → phần còn thiếu bù từ khối chủ hồ sơ (cùng số).
    cung_nguoi = _CHU_HO_SO_FACTS + [
        {"name": "NguoiNop_HoTen", "value": "Nguyễn Văn A"},
        {"name": "NguoiNop_SoDinhDanh", "value": _CHU_HO_SO},
    ]
    values = _values(mapper.enrich(cung_nguoi, _TO_KHAI)[0])
    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_diaChi"] == "Tổ 1"
    assert _trong(values, "CongDan_ngaySinhCongDan")

    # Trùng họ tên nhưng KHÁC số định danh → hai người, không lấy nhân thân của chủ hồ sơ.
    khac_so = _CHU_HO_SO_FACTS + [
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_SoDinhDanh", "value": _NGUOI_KHAC},
        {"name": "NguoiNop_NgaySinh", "value": "1970"},
    ]
    values = _values(mapper.enrich(khac_so, _TO_KHAI)[0])
    for name in ("CongDan_danTocCongDan", "CongDan_diaChi", "CongDan_diDong", "CongDan_ngayCapCmnd",
                 "CongDan_ngaySinhCongDan"):
        assert _trong(values, name), name


def test_to_khai_chu_ho_so_to_chuc_khong_co_nguoi_nop_thi_bo_trong_va_bao():
    facts = [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Thử Nghiệm"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ 1"}},
    ]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert not [name for name in values if name.startswith("CongDan_")]
    assert any("không xác định được người nộp" in w for w in warnings)
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Công ty TNHH Thử Nghiệm"


# --- Khối người nộp chung Lào Cai (`_shared/lao_cai_nguoi_nop`). Dữ liệu giả. ---
_NOP_TOI_THIEU = [
    {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _NGUOI_NOP},
    {"name": "NguoiNop_NgaySinh", "value": "1990"},
]


def test_to_khai_ghi_ho_ten_can_cuoc_dau_khoi_va_xoa_nhan_than_tai_khoan():
    """Người nộp theo tờ khai chỉ có họ tên + số + năm sinh: hai ô readonly đứng đầu khối, mọi ô nhân thân
    hồ sơ không có đều là lệnh xoá, không ô nào mang nhân thân của chủ hồ sơ."""
    fields, warnings = mapper.enrich(_CHU_HO_SO_FACTS + _NOP_TOI_THIEU, {
        **_TO_KHAI, "formContext": {"applicantFullname": "PHẠM VĂN TÀI KHOẢN", "applicantIdentityNumber": "001090000099"},
    })
    values = _values(fields)
    cong_dan = [f for f in fields if f["name"].startswith("CongDan_")]

    assert [f["name"] for f in cong_dan[:2]] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "TRẦN THỊ B"
    assert values["CongDan_soCmnd"] == _NGUOI_NOP
    xoa = {f["name"] for f in fields if f.get("clear")}
    assert {"CongDan_ngaySinhCongDan", "CongDan_danTocCongDan", "CongDan_ngayCapCmnd", "CongDan_diDong", "CongDan_diaChi"} <= xoa
    assert all(f["value"] == "" for f in fields if f.get("clear"))
    # Khối người nộp (kể cả lệnh xoá) xong hẳn trước khi sang khối chủ hồ sơ.
    idx_chs = min(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert all(i < idx_chs for i, f in enumerate(fields) if f["name"].startswith("CongDan_"))
    # Không lẫn nhân thân của người khác.
    gia_tri = {str(f["value"]) for f in cong_dan}
    assert not gia_tri & {_CHU_HO_SO, "Kinh", "10/06/2021", "0912000001", "Tổ 1"}
    # Giới tính không xoá được (select không có option trống) → cảnh báo cán bộ.
    assert any("Giới tính" in w for w in warnings)


def test_tai_khoan_khong_ghi_hai_o_readonly_va_khong_xoa_o_nao():
    fields, _ = mapper.enrich(_UY_QUYEN, _ctx("TRẦN THỊ B", _NGUOI_NOP))
    names = {f["name"] for f in fields}

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & names
    assert not any(f.get("clear") for f in fields)
    assert any(n.startswith("CongDan_") for n in names)
