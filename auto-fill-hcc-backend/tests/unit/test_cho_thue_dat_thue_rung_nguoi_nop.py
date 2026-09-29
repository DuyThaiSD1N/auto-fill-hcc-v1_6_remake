"""[Lào Cai] 1.115678 — hai chế độ xác định NGƯỜI NỘP.

Theo tài khoản (mặc định): mốc `formContext` chốt người nộp trùng/khác chủ hồ sơ. Theo tờ khai
(`submitterMode="owner_as_submitter"`): bỏ mốc, người nộp là khối NguoiNop_* (bên được ủy quyền), không
có thì người đứng tên chủ hồ sơ. Hai ô readonly Họ tên/Số Căn cước: tài khoản KHÔNG phát; tờ khai ghi theo
người đã chọn và xoá các ô nhân thân tài khoản mà hồ sơ không có.
"""

from pathlib import Path

from app.pipelines.cho_thue_dat_thue_rung.process import mapper

_CHU_HO_SO = "001099000001"
_NGUOI_NOP = "001088000002"
_KHAC = "001077000003"
_TO_KHAI = {"submitterMode": "owner_as_submitter"}

_CHU = [
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "01/02/1980"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0987000111"},
]
_UY_QUYEN = [
    {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _NGUOI_NOP},
    {"name": "NguoiNop_NgaySinh", "value": "05/06/1988"},
    {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
    {"name": "NguoiNop_NgayCap", "value": "15/01/2022"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Thôn 2"}},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _trong(values, name):
    """Ô không mang giá trị: không phát, hoặc phát lệnh xoá (value "") để bỏ nhân thân tài khoản."""
    return values.get(name, "") == ""


def test_toggle_tat_co_moc_giu_hanh_vi_cu():
    """Tài khoản là chủ hồ sơ → mode B theo mốc: khối người nộp bù từ chủ hồ sơ, không lấy bên ủy quyền."""
    fields, warnings = mapper.enrich(_CHU + _UY_QUYEN, {"formContext": {
        "applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": _CHU_HO_SO,
    }})
    values = _values(fields)

    # Toggle tắt: NguoiNop_* vẫn đổ vào khối người nộp như code cũ, mốc chỉ quyết định mode.
    assert values["CongDan_ngaySinhCongDan"] == "05/06/1988"
    assert values["CongDan_diaChi"] == "Thôn 2"
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert any("Người nộp trùng chủ hồ sơ" in w for w in warnings)
    assert not any("TỜ KHAI" in w for w in warnings)


def test_toggle_bat_co_uy_quyen_lay_ben_duoc_uy_quyen_va_canh_bao_lech():
    fields, warnings = mapper.enrich(_CHU + _UY_QUYEN, {
        **_TO_KHAI,
        "formContext": {"applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": _CHU_HO_SO},
    })
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "05/06/1988"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_ngayCapCmnd"] == "15/01/2022"
    assert values["CongDan_diaChi"] == "Thôn 2"
    # Hai người khác nhau → không mượn số điện thoại của chủ hồ sơ.
    assert _trong(values, "CongDan_diDong")
    # Readonly: theo tờ khai ghi theo bên được ủy quyền (ghi trước các ô khác).
    assert values["CongDan_tenCongDan"] == "TRẦN THỊ B"
    assert values["CongDan_soCmnd"] == _NGUOI_NOP
    # Khối chủ hồ sơ giữ nguyên.
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0987000111"
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)


def test_toggle_bat_khong_uy_quyen_lay_chu_ho_so():
    fields, warnings = mapper.enrich(_CHU, {
        **_TO_KHAI,
        "formContext": {"applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": _CHU_HO_SO},
    })
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1980"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_diDong"] == "0987000111"
    assert values["CongDan_diaChi"] == "Tổ 1"
    assert not any("bị chặn" in w for w in warnings)
    assert not any("Chưa đọc được tài khoản" in w for w in warnings)


def test_toggle_bat_khong_co_moc_khong_bao_thieu_moc():
    _, warnings = mapper.enrich(_CHU + _UY_QUYEN, _TO_KHAI)

    assert not any("tài khoản định danh" in w for w in warnings)
    assert not any("bị chặn" in w for w in warnings)


def test_toggle_bat_khong_gop_nhan_than_nguoi_khac_so_dinh_danh():
    """Khối người nộp thiếu ngày sinh/giới tính; chủ hồ sơ khác số định danh → không được bù sang."""
    facts = _CHU + [
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},  # trùng tên nhưng khác số
        {"name": "NguoiNop_SoDinhDanh", "value": _KHAC},
    ]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert _trong(values, "CongDan_ngaySinhCongDan")
    assert _trong(values, "CongDan_gioiTinhCongDan")
    assert _trong(values, "CongDan_diDong")
    assert _trong(values, "CongDan_diaChi")


def test_toggle_bat_gop_nhan_than_cung_nguoi_va_bo_ngay_chi_co_nam():
    """Khối người nộp không đọc được số → khớp họ tên + năm sinh không mâu thuẫn là cùng người, được bù.
    Ngày sinh cả hai phía chỉ có năm → không phát."""
    facts = [
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
        {"name": "ChuHoSo_NgaySinh", "value": "1980"},
        {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
        {"name": "NguoiNop_HoTen", "value": "NGUYEN VAN A"},
        {"name": "NguoiNop_NgaySinh", "value": "Sinh năm 1980"},
    ]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert _trong(values, "CongDan_ngaySinhCongDan")
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_diaChi"] == "Tổ 1"


def test_toggle_bat_ho_ten_trung_nhung_nam_sinh_lech_la_hai_nguoi():
    facts = _CHU + [
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_NgaySinh", "value": "1955"},
    ]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert _trong(values, "CongDan_ngayCapCmnd")
    assert _trong(values, "CongDan_diaChi")


def test_toggle_bat_khong_xac_dinh_duoc_ai_thi_bo_trong():
    facts = [
        {"name": "ChuHoSo_NgaySinh", "value": "01/02/1980"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    ]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert not [n for n in values if n.startswith("CongDan_")]
    assert any("để trống khối" in w for w in warnings)


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "cho-thue-dat-thue-rung"' in block


# --- Khối người nộp chung Lào Cai (`_shared/lao_cai_nguoi_nop`). Dữ liệu giả. ---
_NOP_TOI_THIEU = [
    {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _NGUOI_NOP},
    {"name": "NguoiNop_NgaySinh", "value": "1988"},
]


def test_to_khai_ghi_ho_ten_can_cuoc_dau_khoi_va_xoa_nhan_than_tai_khoan():
    """Người nộp theo tờ khai chỉ có họ tên + số + năm sinh: hai ô readonly đứng đầu khối, mọi ô nhân thân
    hồ sơ không có đều là lệnh xoá, không ô nào mang nhân thân của chủ hồ sơ."""
    fields, warnings = mapper.enrich(_CHU + _NOP_TOI_THIEU, {
        **_TO_KHAI, "formContext": {"applicantFullname": "PHẠM VĂN TÀI KHOẢN", "applicantIdentityNumber": "001090000099"},
    })
    values = _values(fields)
    cong_dan = [f for f in fields if f["name"].startswith("CongDan_")]

    assert [f["name"] for f in cong_dan[:2]] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "TRẦN THỊ B"
    assert values["CongDan_soCmnd"] == _NGUOI_NOP
    xoa = {f["name"] for f in fields if f.get("clear")}
    assert {"CongDan_ngaySinhCongDan", "CongDan_diDong", "CongDan_diaChi", "CongDan_maTinhThanh", "CongDan_email"} <= xoa
    assert all(f["value"] == "" for f in fields if f.get("clear"))
    # Khối người nộp (kể cả lệnh xoá) xong hẳn trước khi sang khối chủ hồ sơ.
    idx_chs = min(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert all(i < idx_chs for i, f in enumerate(fields) if f["name"].startswith("CongDan_"))
    # Không lẫn nhân thân của người khác.
    gia_tri = {str(f["value"]) for f in cong_dan}
    assert not gia_tri & {_CHU_HO_SO, "01/02/1980", "0987000111", "Tổ 1"}
    # Giới tính không xoá được (select không có option trống) → cảnh báo cán bộ.
    assert any("Giới tính" in w for w in warnings)


def test_tai_khoan_khong_ghi_hai_o_readonly_va_khong_xoa_o_nao():
    fields, _ = mapper.enrich(_CHU + _UY_QUYEN, {"formContext": {"applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _NGUOI_NOP}})
    names = {f["name"] for f in fields}

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & names
    assert not any(f.get("clear") for f in fields)
    assert any(n.startswith("CongDan_") for n in names)
