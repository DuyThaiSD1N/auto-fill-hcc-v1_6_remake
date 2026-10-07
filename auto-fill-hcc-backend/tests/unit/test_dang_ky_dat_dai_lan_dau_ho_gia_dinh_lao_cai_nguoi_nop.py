"""[Lào Cai] 1.115689 (đăng ký đất đai lần đầu, hộ gia đình/cá nhân) — ba luồng khối NGƯỜI NỘP.

Cổng đối chiếu Họ tên + Số Căn cước + Ngày sinh của khối người nộp với CSDL quốc gia dân cư và tài khoản
đăng nhập → cả khối phải là MỘT người. Bản extension cũ (không gửi formContext) giữ nguyên luồng cũ.
Dữ liệu dưới đây là GIẢ.
"""

from pathlib import Path

from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process import mapper

_CHU = "010080000111"
_UQ = "010190000222"
_KHAC = "010170000333"

_CARD_CHU = {
    "HoTen": "LÒ VĂN GIẢ", "SoDinhDanh": _CHU, "NgaySinh": "12/03/1980", "GioiTinh": "Nam",
    "DanToc": "Thái", "NgayCap": "05/08/2024", "NoiCap": "Bộ Công an",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Thôn Một"},
}
_PROXY = {
    "hoTen": "Hoàng Thị Thử", "soDinhDanh": _UQ, "ngaySinh": "20/11/1990",
    "ngayCapCccd": "15/01/2022", "dienThoai": "0912000111",
    "thuongTru": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ Hai"},
}
_NAMED_UQ = {
    "HoTen": "HOÀNG THỊ THỬ", "SoDinhDanh": _UQ, "GioiTinh": "Nữ", "DanToc": "Tày",
    "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}

_FACTS = [
    {"name": "DanhSachCccd", "value": [_CARD_CHU]},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Lò Văn Giả", "SoDinhDanh": _CHU, "NgaySinh": "1980"},
        _NAMED_UQ,
    ]},
    {"name": "NguoiDuocUyQuyen", "value": _PROXY},
    {"name": "ChuHoSo_HoTen", "value": "Lò Văn Giả"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Thôn Một"}},
    {"name": "ChuHoSo_DienThoai", "value": "0987000222"},
    # Khối phẳng do LLM chọn (luồng cũ dùng thẳng).
    {"name": "NguoiNop_HoTen", "value": "Hoàng Thị Thử"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UQ},
    {"name": "NguoiNop_NgaySinh", "value": "20/11/1990"},
    {"name": "NguoiNop_NgayCap", "value": "15/01/2022"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ Hai"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000111"},
    {"name": "ThuaDat_SoThua", "value": "45"},
]

_NHAN_THAN = (
    "CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan",
    "CongDan_danTocCongDan", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd", "CongDan_maTinhThanh",
    "CongDan_maPhuongXa", "CongDan_diaChi", "CongDan_diDong", "CongDan_email",
)


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _without(*names):
    return [f for f in _FACTS if f["name"] not in names]


def test_tai_khoan_khop_cccd_lay_nhan_than_nguoi_dang_nhap_khong_lay_chu_ho_so():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "Hoàng Thị Thử", "applicantIdentityNumber": _UQ,
    }})
    values = _values(fields)

    # Hai ô readonly cổng đã đổ đúng tài khoản → không ghi.
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "20/11/1990"
    # Bù từ giấy tờ khác CỦA CHÍNH người này (cùng số định danh).
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_maPhuongXa"] == "Bắc Lệnh"
    assert values["CongDan_diDong"] == "0912000111"
    assert values["CongDan_ngaySinhCongDan"] != _CARD_CHU["NgaySinh"]
    assert not any("Thông tin người nộp hồ sơ" in w for w in warnings)
    # Khối chủ hồ sơ giữ nguyên.
    assert values["ChuHoSo_tenChuHoSo"] == "Lò Văn Giả"
    assert values["ChuHoSo_soCMNDChuHoSo"] == _CHU


def test_tai_khoan_la_chu_ho_so_thi_ngay_sinh_lay_tu_cccd_du_ngay():
    fields, _ = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "LÒ VĂN GIẢ", "applicantIdentityNumber": _CHU,
    }})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "12/03/1980"
    assert values["CongDan_danTocCongDan"] == "Thái"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    assert values["CongDan_diDong"] == "0987000222"


def test_tai_khoan_chi_khop_ten_khi_giay_to_thieu_so():
    facts = [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Hoàng Thị Thử", "NgaySinh": "20/11/1990",
             "NoiCuTru": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ Hai"}},
        ]},
        {"name": "ChuHoSo_HoTen", "value": "Lò Văn Giả"},
    ]
    fields, warnings = mapper.enrich(facts, {"formContext": {
        "applicantFullname": "HOÀNG THỊ THỬ", "applicantIdentityNumber": _UQ,
    }})
    values = _values(fields)

    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "20/11/1990"
    # Giấy tờ không ghi số → không đoán nơi cấp mặc định.
    assert "CongDan_noiCapCmnd" not in values
    assert not any("Thông tin người nộp hồ sơ" in w for w in warnings)

    # Mốc không có số → khớp theo họ tên bỏ dấu.
    fields, _ = mapper.enrich(facts, {"formContext": {"applicantFullname": "hoang thi thu"}})
    values = _values(fields)
    assert values["CongDan_ngaySinhCongDan"] == "20/11/1990"
    assert "CongDan_soCmnd" not in values


def test_tai_khoan_trung_ten_khac_so_khong_nhan():
    facts = [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Hoàng Thị Thử", "SoDinhDanh": _KHAC, "NgaySinh": "01/01/1970"},
        ]},
    ]
    fields, warnings = mapper.enrich(facts, {"formContext": {
        "applicantFullname": "Hoàng Thị Thử", "applicantIdentityNumber": _UQ,
    }})
    values = _values(fields)

    for name in _NHAN_THAN:
        assert name not in values, name
    assert any("KHÔNG lấy thông tin của người khác" in w for w in warnings)


def test_form_context_rong_bo_trong_khoi_va_canh_bao():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {}})
    values = _values(fields)

    for name in _NHAN_THAN:
        assert name not in values, name
    assert any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)
    assert values["ChuHoSo_tenChuHoSo"] == "Lò Văn Giả"


def test_tai_khoan_khong_co_trong_ho_so_bo_trong_va_canh_bao():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "Người Lạ Giả", "applicantIdentityNumber": _KHAC,
    }})
    values = _values(fields)

    for name in _NHAN_THAN:
        assert name not in values, name
    assert any("Người Lạ Giả" in w and "để trống" in w for w in warnings)


def test_to_khai_co_uy_quyen_lay_ben_duoc_uy_quyen():
    fields, warnings = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "Hoàng Thị Thử"
    assert values["CongDan_soCmnd"] == _UQ
    assert values["CongDan_ngaySinhCongDan"] == "20/11/1990"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_maPhuongXa"] == "Bắc Lệnh"
    assert not any("Thông tin người nộp hồ sơ" in w for w in warnings)


def test_to_khai_khong_uy_quyen_thi_lay_chu_ho_so():
    facts = _without("NguoiDuocUyQuyen", "NguoiNop_HoTen", "NguoiNop_SoDinhDanh", "NguoiNop_NgaySinh",
                     "NguoiNop_NgayCap", "NguoiNop_NoiCuTru", "NguoiNop_DienThoai")
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter", "formContext": {}})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "Lò Văn Giả"
    assert values["CongDan_soCmnd"] == _CHU
    # Đơn chỉ ghi năm sinh → lấy ngày đủ từ CCCD của chính chủ hồ sơ.
    assert values["CongDan_ngaySinhCongDan"] == "12/03/1980"
    assert values["CongDan_diaChi"] == "Thôn Một"
    assert values["CongDan_diDong"] == "0987000222"


def test_to_khai_lech_tai_khoan_thi_canh_bao_cong_chan():
    fields, warnings = mapper.enrich(_FACTS, {
        "submitterMode": "owner_as_submitter",
        "formContext": {"applicantFullname": "Người Lạ Giả", "applicantIdentityNumber": _KHAC},
    })

    assert _values(fields)["CongDan_tenCongDan"] == "Hoàng Thị Thử"
    assert any("lệch là bị chặn" in w and "Lấy người nộp theo tờ khai" in w for w in warnings)


def test_to_khai_khong_xac_dinh_duoc_ai_thi_bo_trong():
    facts = [{"name": "ThuaDat_SoThua", "value": "45"}]
    fields, warnings = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})

    assert not any(f["name"].startswith("CongDan_") for f in fields)
    assert any("để trống khối" in w for w in warnings)


def test_khong_gop_nhan_than_nguoi_khac_so_va_ngay_chi_co_nam_khong_phat():
    facts = [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Lò Văn Giả", "SoDinhDanh": _CHU, "NgaySinh": "1980"},
            # Người trùng tên, khác số định danh (vd cha/con) — không được mượn nhân thân.
            {"HoTen": "Lò Văn Giả", "SoDinhDanh": _KHAC, "NgaySinh": "02/02/1950",
             "NgayCap": "03/03/2020", "DanToc": "Kinh",
             "NoiCuTru": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ Chín"}},
        ]},
    ]
    for options in (
        {"formContext": {"applicantFullname": "Lò Văn Giả", "applicantIdentityNumber": _CHU}},
        {"submitterMode": "owner_as_submitter"},
    ):
        base = facts + ([{"name": "NguoiNop_HoTen", "value": "Lò Văn Giả"},
                         {"name": "NguoiNop_SoDinhDanh", "value": _CHU}]
                        if "submitterMode" in options else [])
        fields, _ = mapper.enrich(base, options)
        values = _values(fields)
        theo_to_khai = "submitterMode" in options
        if theo_to_khai:
            assert values["CongDan_soCmnd"] == _CHU
        else:
            assert "CongDan_soCmnd" not in values
        assert "CongDan_maPhuongXa" not in values
        for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_danTocCongDan",
                     "CongDan_diaChi"):
            # Theo tờ khai: lệnh XOÁ ô cổng đổ từ tài khoản; theo tài khoản: không phát.
            if theo_to_khai:
                assert values[name] == "", (options, name)
            else:
                assert name not in values, (options, name)


def test_schema_co_ung_vien_va_prompt_co_quy_tac():
    from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process.prompt import EXTRA_RULES
    from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process.schema import (
        ALLOWED,
        COMPACT_COMP_BY_NAME,
    )

    for name in ("NguoiDuocUyQuyen", "DanhSachCccd", "NguoiTrongGiayTo", "NguoiNop_HoTen"):
        assert name in ALLOWED and name in COMPACT_COMP_BY_NAME
    assert "<ung_vien_nguoi_nop_rules>" in EXTRA_RULES
    assert EXTRA_RULES.rstrip().endswith("</nhan_than_dung_nguoi>")


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "dang-ky-dat-dai-lan-dau-ho-gia-dinh-lao-cai"' in block


# ----- Chốt khối người nộp theo chính sách chung Lào Cai (_shared/lao_cai_nguoi_nop) -----
_TK_KHAC = {"formContext": {"applicantFullname": "Người Lạ Giả", "applicantIdentityNumber": _KHAC}}


def _ten_cong_dan(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ho_ten_va_so_can_cuoc_dung_dau_xoa_o_nhan_than_thieu():
    fields, _ = mapper.enrich(_FACTS, {**_TK_KHAC, "submitterMode": "owner_as_submitter"})
    assert _ten_cong_dan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    values = {k: v for k, v in _values(fields).items() if k.startswith("CongDan_")}
    assert values["CongDan_tenCongDan"] == "Hoàng Thị Thử"
    assert values["CongDan_soCmnd"] == _UQ
    assert values["CongDan_danTocCongDan"] == "Tày"
    # Bên được ủy quyền không có email/fax trong hồ sơ → xoá ô cổng đổ từ tài khoản.
    cleared = {f["name"]: f["value"] for f in fields if f.get("clear")}
    assert cleared == {"CongDan_email": "", "CongDan_fax": ""}
    # Không lẫn nhân thân của chủ hồ sơ hay của tài khoản.
    assert not {"Thái", _CHU, "0987000222", "12/03/1980", _KHAC} & set(values.values())
    # Lệnh xoá nằm trong khối người nộp, trước khối chủ hồ sơ.
    dau_chu = next(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert all(i < dau_chu for i, f in enumerate(fields) if f.get("clear"))


def test_to_khai_thieu_so_can_cuoc_thi_xoa_o_so_va_ngay_sinh():
    facts = [
        {"name": "ChuHoSo_HoTen", "value": "Lò Văn Giả"},
        {"name": "NguoiDuocUyQuyen", "value": {"hoTen": "Hoàng Thị Thử", "gioiTinh": "Nữ"}},
    ]
    fields, _ = mapper.enrich(facts, {**_TK_KHAC, "submitterMode": "owner_as_submitter"})
    cong_dan = [f for f in fields if f["name"].startswith("CongDan_")]
    assert [f["name"] for f in cong_dan[:2]] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert cong_dan[1] == {"name": "CongDan_soCmnd", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True}
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "Hoàng Thị Thử"
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"


def test_tai_khoan_khong_ghi_o_readonly_khong_xoa_o_nao():
    for options in (
        {"formContext": {"applicantFullname": "LÒ VĂN GIẢ", "applicantIdentityNumber": _CHU}},
        _TK_KHAC,
        {"formContext": {}},
    ):
        fields, _ = mapper.enrich(_FACTS, options)
        assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & {f["name"] for f in fields}
        assert not any(f.get("clear") for f in fields)


def test_thieu_form_context_coi_nhu_tai_khoan_chua_co_moc():
    """Popup không gửi mốc (bản extension cũ, hoặc chưa F5 trang sau khi tải lại extension) → không ghi họ
    tên/căn cước, không điền nhân thân người nộp của ai — tránh khối nửa tài khoản nửa người trong Đơn."""
    nhan_than = {"CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan",
                 "CongDan_danTocCongDan", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd", "CongDan_diDong",
                 "CongDan_email", "CongDan_fax"}
    for options in (None, {}, {"extVersion": "1.19.0"}):
        fields, warnings = mapper.enrich(_FACTS, options)
        assert not {f["name"] for f in fields} & nhan_than
        assert not any(f.get("clear") for f in fields)
        assert any("F5 trang cổng" in w for w in warnings)
