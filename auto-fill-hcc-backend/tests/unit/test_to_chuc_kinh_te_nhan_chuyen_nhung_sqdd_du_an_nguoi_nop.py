"""[Lào Cai] 1.115681 — hai chế độ xác định NGƯỜI NỘP.

Chế độ theo tài khoản (mặc định) chỉ mở khối người nộp khi khớp mốc tài khoản với khối NguoiNop_*
(bên được uỷ quyền) hoặc NguoiDaiDien_* (người đại diện theo pháp luật). Chế độ theo tờ khai
(`submitterMode="owner_as_submitter"`) bỏ mốc: bên được uỷ quyền nếu là người khác người đại diện,
không thì người đại diện ký đơn. Hai ô Họ tên/Số Căn cước readonly: tài khoản KHÔNG phát; tờ khai ghi theo
người đã chọn và xoá các ô nhân thân tài khoản mà hồ sơ không có.
"""

from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process import mapper

_DAI_DIEN = "001199000001"   # chữ số thứ 4 lẻ → Nữ
_UY_QUYEN = "001099000002"   # chữ số thứ 4 chẵn → Nam
_KHAC = "001099000009"

_TO_CHUC = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Thử Nghiệm A"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    {"name": "ChuHoSo_TruSoChinh", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0200000001"},
]
_DAI_DIEN_FACTS = [
    {"name": "NguoiDaiDien_HoTen", "value": "Trần Thị B"},
    {"name": "NguoiDaiDien_SoDinhDanh", "value": _DAI_DIEN},
    {"name": "NguoiDaiDien_NgaySinh", "value": "04/05/1990"},
    {"name": "NguoiDaiDien_DanToc", "value": "Tày"},
    {"name": "NguoiDaiDien_NgayCap", "value": "01/02/2022"},
    {"name": "NguoiDaiDien_NoiCap", "value": "Bộ Công an"},
    {"name": "NguoiDaiDien_NoiThuongTru", "value": {"tinh": "Lào Cai", "xa": "Cốc San", "diaChi": "Thôn 2"}},
]
_UY_QUYEN_FACTS = [
    {"name": "NguoiNop_HoTen", "value": "Nguyễn Văn A"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UY_QUYEN},
    {"name": "NguoiNop_NgaySinh", "value": "1988"},
    {"name": "NguoiNop_NgayCap", "value": "10/06/2021"},
    {"name": "NguoiNop_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiNop_TenToChuc", "value": "Công ty CP Được Uỷ Quyền B"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ 5"}},
]
_FACTS_UY_QUYEN = _TO_CHUC + _DAI_DIEN_FACTS + _UY_QUYEN_FACTS

_TO_KHAI = {"submitterMode": "owner_as_submitter"}
_MOC_DAI_DIEN = {"applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _DAI_DIEN}
_MOC_KHAC = {"applicantFullname": "LÊ VĂN C", "applicantIdentityNumber": _KHAC}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _trong(values, name):
    """Ô không mang giá trị: không phát, hoặc phát lệnh xoá (value "") để bỏ nhân thân tài khoản."""
    return values.get(name, "") == ""


def test_che_do_tai_khoan_giu_hanh_vi_cu_theo_moc():
    """Mốc là người đại diện → khối người nộp theo người đại diện dù hồ sơ có uỷ quyền."""
    fields, warnings = mapper.enrich(_FACTS_UY_QUYEN, {"formContext": _MOC_DAI_DIEN})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "04/05/1990"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Thử Nghiệm A"
    assert values["CongDan_diDong"] == "0200000001"
    assert any("trực tiếp đăng nhập" in w for w in warnings)


def test_che_do_tai_khoan_khong_moc_thi_bo_trong_nhu_cu():
    fields, warnings = mapper.enrich(_FACTS_UY_QUYEN, {})
    values = _values(fields)

    assert not any(name.startswith("CongDan_") for name in values)
    assert any("Chưa đọc được tài khoản" in w for w in warnings)


def test_che_do_to_khai_lay_ben_duoc_uy_quyen_du_moc_la_nguoi_khac():
    fields, warnings = mapper.enrich(_FACTS_UY_QUYEN, {**_TO_KHAI, "formContext": _MOC_DAI_DIEN})
    values = _values(fields)

    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty CP Được Uỷ Quyền B"
    assert values["CongDan_diaChi"] == "Tổ 5"
    # Nhân thân KHÔNG lấy của người đại diện (người khác số định danh); năm sinh trơ thì bỏ.
    assert _trong(values, "CongDan_ngaySinhCongDan")
    assert _trong(values, "CongDan_danTocCongDan")
    # Liên lạc của tổ chức chủ hồ sơ không mượn cho người nộp thay.
    assert _trong(values, "CongDan_diDong")
    assert values["CongDan_tenCongDan"] == "Nguyễn Văn A"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)
    assert not any("Chưa đọc được tài khoản" in w or "trực tiếp đăng nhập" in w for w in warnings)


def test_che_do_to_khai_khong_uy_quyen_thi_lay_nguoi_dai_dien():
    fields, warnings = mapper.enrich(_TO_CHUC + _DAI_DIEN_FACTS, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "04/05/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_diaChi"] == "Thôn 2"
    # Người đại diện tự nộp → ô tên cơ quan/MST + liên lạc của khối người nộp là của tổ chức chủ hồ sơ.
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Thử Nghiệm A"
    assert values["CongDan_maSoThueNguoiNop"] == "5300000001"
    assert values["CongDan_diDong"] == "0200000001"
    assert not any("bị chặn" in w or "Chưa đọc được tài khoản" in w for w in warnings)


def test_che_do_to_khai_nguoi_nop_chep_lai_nguoi_dai_dien_thi_la_tu_nop():
    """Không có uỷ quyền, LLM chép lại người đại diện vào NguoiNop_* → vẫn là người đại diện tự nộp."""
    chep_lai = [
        {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
        {"name": "NguoiNop_SoDinhDanh", "value": _DAI_DIEN},
    ]
    fields, warnings = mapper.enrich(_TO_CHUC + _DAI_DIEN_FACTS + chep_lai, {
        **_TO_KHAI, "formContext": _MOC_DAI_DIEN,
    })
    values = _values(fields)

    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Thử Nghiệm A"
    assert values["CongDan_ngaySinhCongDan"] == "04/05/1990"
    assert not any("bị chặn" in w for w in warnings)


def test_che_do_to_khai_trung_ten_khac_ngay_sinh_khong_ghep_cheo():
    """Thiếu số ở một phía, trùng họ tên nhưng ngày sinh mâu thuẫn → hai người, không bù chéo."""
    nguoi_nop = [
        {"name": "NguoiNop_HoTen", "value": "Trần Thị B"},
        {"name": "NguoiNop_NgaySinh", "value": "09/09/1970"},
    ]
    fields, _ = mapper.enrich(_TO_CHUC + _DAI_DIEN_FACTS + nguoi_nop, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "09/09/1970"
    assert _trong(values, "CongDan_danTocCongDan")
    assert _trong(values, "CongDan_ngayCapCmnd")
    assert _trong(values, "CongDan_diaChi")


def test_che_do_to_khai_khong_xac_dinh_duoc_ai_thi_bo_trong_va_canh_bao():
    fields, warnings = mapper.enrich(_TO_CHUC, {**_TO_KHAI, "formContext": _MOC_KHAC})
    values = _values(fields)

    assert not any(name.startswith("CongDan_") for name in values)
    assert any("để trống nhân thân" in w for w in warnings)
    assert not any("Chưa đọc được tài khoản" in w or "KHÔNG có giấy tờ tuỳ thân" in w for w in warnings)


# --- Khối người nộp chung Lào Cai (`_shared/lao_cai_nguoi_nop`). Dữ liệu giả. ---
_NOP_TOI_THIEU = [
    {"name": "NguoiNop_HoTen", "value": "Nguyễn Văn A"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UY_QUYEN},
    {"name": "NguoiNop_NgaySinh", "value": "1988"},
]


def test_to_khai_ghi_ho_ten_can_cuoc_dau_khoi_va_xoa_nhan_than_tai_khoan():
    """Người nộp theo tờ khai chỉ có họ tên + số + năm sinh: hai ô readonly đứng đầu khối, mọi ô nhân thân
    hồ sơ không có đều là lệnh xoá, không ô nào mang nhân thân của người đại diện/tổ chức."""
    fields, warnings = mapper.enrich(_TO_CHUC + _DAI_DIEN_FACTS + _NOP_TOI_THIEU, {
        **_TO_KHAI, "formContext": {"applicantFullname": "PHẠM VĂN TÀI KHOẢN", "applicantIdentityNumber": "001090000099"},
    })
    values = _values(fields)
    cong_dan = [f for f in fields if f["name"].startswith("CongDan_")]

    assert [f["name"] for f in cong_dan[:2]] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Nguyễn Văn A"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    xoa = {f["name"] for f in fields if f.get("clear")}
    assert {"CongDan_ngaySinhCongDan", "CongDan_danTocCongDan", "CongDan_ngayCapCmnd", "CongDan_diDong", "CongDan_diaChi"} <= xoa
    assert all(f["value"] == "" for f in fields if f.get("clear"))
    # Khối người nộp (kể cả lệnh xoá) xong hẳn trước khi sang khối chủ hồ sơ.
    idx_chs = min(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert all(i < idx_chs for i, f in enumerate(fields) if f["name"].startswith("CongDan_"))
    # Không lẫn nhân thân của người khác.
    gia_tri = {str(f["value"]) for f in cong_dan}
    assert not gia_tri & {_DAI_DIEN, "04/05/1990", "Tày", "01/02/2022", "0200000001", "Thôn 2", "Số 1"}


def test_tai_khoan_khong_ghi_hai_o_readonly_va_khong_xoa_o_nao():
    fields, _ = mapper.enrich(_FACTS_UY_QUYEN, {"formContext": _MOC_DAI_DIEN})
    names = {f["name"] for f in fields}

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & names
    assert not any(f.get("clear") for f in fields)
    assert any(n.startswith("CongDan_") for n in names)
