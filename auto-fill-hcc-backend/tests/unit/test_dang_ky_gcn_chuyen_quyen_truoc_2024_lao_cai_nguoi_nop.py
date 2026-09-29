"""[Lào Cai] 1.115666 — ba luồng xác định khối NGƯỜI NỘP.

Cổng đối chiếu Họ tên + Số Căn cước + Ngày sinh của khối người nộp với CSDL quốc gia dân cư và tài
khoản đăng nhập → cả khối phải là MỘT người. Bản extension cũ (không gửi formContext) giữ nguyên khối
phẳng NguoiNop_*; bản mới chọn theo mốc tài khoản hoặc theo tờ khai. Dữ liệu dưới đây là GIẢ.
"""

from pathlib import Path

from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.process import mapper

_CHU = "001090000111"      # bên nhận chuyển quyền = chủ hồ sơ
_UY_QUYEN = "001190000222"  # bên được ủy quyền đi nộp thay
_BEN_CHUYEN = "001060000333"

_DIA_CHI_CHU = {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}
_DIA_CHI_UQ = {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Tổ 2"}

_CHU_HO_SO = [
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn An"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_NgaySinh", "value": "05/06/1990"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NoiCuTru", "value": _DIA_CHI_CHU},
    {"name": "ChuHoSo_DienThoai", "value": "0911000111"},
]
_THE_CHU = {"HoTen": "NGUYỄN VĂN AN", "SoDinhDanh": _CHU, "NgaySinh": "05/06/1990", "GioiTinh": "Nam",
            "DanToc": "Kinh", "NgayCap": "10/10/2021",
            "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội", "NoiCuTru": _DIA_CHI_CHU}
_UY_QUYEN_OBJ = {"hoTen": "Trần Thị Bình", "soDinhDanh": _UY_QUYEN, "ngaySinh": "07/08/1991",
                 "gioiTinh": "Nữ", "ngayCapCccd": "01/02/2022", "dienThoai": "0922000222",
                 "thuongTru": _DIA_CHI_UQ}
_NGUOI_NOP_PHANG = [
    {"name": "NguoiNop_HoTen", "value": "Trần Thị Bình"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UY_QUYEN},
    {"name": "NguoiNop_NgaySinh", "value": "07/08/1991"},
    {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
    {"name": "NguoiNop_NgayCap", "value": "01/02/2022"},
    {"name": "NguoiNop_NoiCuTru", "value": _DIA_CHI_UQ},
    {"name": "NguoiNop_DienThoai", "value": "0922000222"},
]

_FACTS = _CHU_HO_SO + _NGUOI_NOP_PHANG + [
    {"name": "DanhSachCccd", "value": [_THE_CHU]},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Nguyễn Văn An", "SoDinhDanh": _CHU, "NgaySinh": "1990"},
        {"HoTen": "Trần Thị Bình", "SoDinhDanh": _UY_QUYEN, "NgaySinh": "07/08/1991"},
        {"HoTen": "Lê Văn Cường", "SoDinhDanh": _BEN_CHUYEN, "NgaySinh": "1960"},
    ]},
    {"name": "NguoiDuocUyQuyen", "value": _UY_QUYEN_OBJ},
]

_CONG_DAN_NHAN_THAN = (
    "CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan",
    "CongDan_danTocCongDan", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd", "CongDan_maTinhThanh",
    "CongDan_maPhuongXa", "CongDan_diaChi", "CongDan_diDong", "CongDan_email", "CongDan_fax",
)


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _cong_dan(fields):
    return {k: v for k, v in _values(fields).items() if k.startswith("CongDan_")}


def _tai_khoan(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def test_tai_khoan_khop_cccd_lay_dung_nhan_than_nguoi_dang_nhap():
    fields, warnings = mapper.enrich(_FACTS, _tai_khoan("NGUYỄN VĂN AN", _CHU))
    values = _values(fields)
    # Hai ô readonly cổng đã đổ đúng tài khoản → không ghi.
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "05/06/1990"
    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_ngayCapCmnd"] == "10/10/2021"
    assert values["CongDan_diaChi"] == "Tổ 1"
    # Số di động trên đơn của chính chủ hồ sơ (khớp số định danh) → được bù.
    assert values["CongDan_diDong"] == "0911000111"
    assert not warnings

    # Bên được ủy quyền đăng nhập → KHÔNG lấy nhân thân chủ hồ sơ.
    fields, warnings = mapper.enrich(_FACTS, _tai_khoan("TRẦN THỊ BÌNH", _UY_QUYEN))
    values = _values(fields)
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1991"
    assert values["CongDan_diaChi"] == "Tổ 2"
    assert values["CongDan_diDong"] == "0922000222"
    assert "CongDan_danTocCongDan" not in values
    # Khối chủ hồ sơ giữ nguyên.
    assert values["ChuHoSo_tenChuHoSo"] == "Nguyễn Văn An"
    assert values["ChuHoSo_soCMNDChuHoSo"] == _CHU
    assert not warnings


def test_tai_khoan_chi_khop_ten_khi_mot_phia_thieu_so():
    facts = _CHU_HO_SO + [
        # Cùng họ tên nhưng mang số KHÁC mốc → người khác, không được chọn/gộp.
        {"name": "DanhSachCccd", "value": [
            {"HoTen": "Trần Thị Bình", "SoDinhDanh": "002195000444", "NgaySinh": "01/01/1995",
             "DanToc": "Tày"},
        ]},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Trần Thị Bình", "NgaySinh": "07/08/1991", "NoiCuTru": _DIA_CHI_UQ},
        ]},
    ]
    fields, warnings = mapper.enrich(facts, _tai_khoan("Trần Thị Bình", _UY_QUYEN))
    values = _cong_dan(fields)
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1991"
    assert values["CongDan_diaChi"] == "Tổ 2"
    assert "CongDan_danTocCongDan" not in values
    # Không có giấy tờ định danh của người này → không đặt nơi cấp mặc định.
    assert "CongDan_noiCapCmnd" not in values
    assert not warnings

    # Mốc thiếu số → khớp tên; hai ô readonly vẫn không ghi.
    fields, _ = mapper.enrich(_FACTS, {"formContext": {"applicantFullname": "trần thị bình"}})
    values = _cong_dan(fields)
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1991"


def test_form_context_rong_hoac_khong_tim_thay_thi_bo_trong_va_canh_bao():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {}})
    values = _values(fields)
    assert not any(k in values for k in _CONG_DAN_NHAN_THAN)
    assert values["ChuHoSo_tenChuHoSo"] == "Nguyễn Văn An"
    assert any("tài khoản đăng nhập" in w for w in warnings)

    fields, warnings = mapper.enrich(_FACTS, _tai_khoan("PHẠM VĂN DŨNG", "001080000555"))
    values = _values(fields)
    assert not any(k in values for k in _CONG_DAN_NHAN_THAN)
    assert any("PHẠM VĂN DŨNG" in w for w in warnings)


def test_form_context_to_chuc_van_phat_o_to_chuc():
    facts = _FACTS + [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Mẫu Thử"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000000"},
    ]
    fields, warnings = mapper.enrich(facts, {"formContext": {}})
    values = _values(fields)
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Mẫu Thử"
    assert values["CongDan_maSoThueNguoiNop"] == "5300000000"
    assert "CongDan_tenCongDan" not in values
    assert warnings


def test_to_khai_co_uy_quyen_lay_ben_duoc_uy_quyen_va_canh_bao_lech_tai_khoan():
    options = {**_tai_khoan("NGUYỄN VĂN AN", _CHU), "submitterMode": "owner_as_submitter"}
    fields, warnings = mapper.enrich(_FACTS, options)
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "Trần Thị Bình"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1991"
    assert values["CongDan_diaChi"] == "Tổ 2"
    assert any("chặn" in w and "NGUYỄN VĂN AN" in w for w in warnings)

    # Không có formContext (toggle bật trên bản không gửi mốc) → vẫn theo tờ khai, không cảnh báo lệch.
    fields, warnings = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter"})
    assert _values(fields)["CongDan_tenCongDan"] == "Trần Thị Bình"
    assert not warnings


def test_to_khai_khong_uy_quyen_thi_nguoi_nop_la_chu_ho_so():
    facts = _CHU_HO_SO + [{"name": "DanhSachCccd", "value": [_THE_CHU]}]
    options = {**_tai_khoan("NGUYỄN VĂN AN", _CHU), "submitterMode": "owner_as_submitter"}
    fields, warnings = mapper.enrich(facts, options)
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "Nguyễn Văn An"
    assert values["CongDan_soCmnd"] == _CHU
    assert values["CongDan_ngaySinhCongDan"] == "05/06/1990"
    assert values["CongDan_danTocCongDan"] == "Kinh"  # bù từ CCCD cùng số định danh
    assert values["CongDan_diDong"] == "0911000111"
    assert not warnings

    fields, warnings = mapper.enrich([{"name": "Don_TrichYeu", "value": "x"}],
                                     {"submitterMode": "owner_as_submitter"})
    assert not any(k in _values(fields) for k in _CONG_DAN_NHAN_THAN)
    assert warnings


def test_khong_gop_nhan_than_nguoi_khac_so_va_ngay_chi_co_nam_khong_phat():
    facts = [
        {"name": "NguoiDuocUyQuyen", "value": {"hoTen": "Trần Thị Bình", "soDinhDanh": _UY_QUYEN}},
        {"name": "DanhSachCccd", "value": [
            {"HoTen": "Trần Thị Bình", "SoDinhDanh": "002195000444", "NgaySinh": "01/01/1995",
             "DanToc": "Tày", "NoiCuTru": _DIA_CHI_CHU},
        ]},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Trần Thị Bình", "SoDinhDanh": _UY_QUYEN, "NgaySinh": "1991"},
        ]},
    ]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _cong_dan(fields)
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    # Không có dữ liệu của đúng người → lệnh XOÁ ô cổng đổ từ tài khoản, không lấy của người khác.
    assert values["CongDan_ngaySinhCongDan"] == ""   # chỉ có năm
    assert values["CongDan_danTocCongDan"] == ""     # của người trùng tên khác số
    assert values["CongDan_diaChi"] == ""


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "dang-ky-gcn-chuyen-quyen-truoc-2024-lao-cai"' in block


# ----- Chốt khối người nộp theo chính sách chung Lào Cai (_shared/lao_cai_nguoi_nop) -----
_TK_KHAC = _tai_khoan("PHẠM THỊ TÀI KHOẢN", "001080000999")


def _ten_cong_dan(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ho_ten_va_so_can_cuoc_dung_dau_xoa_o_nhan_than_thieu():
    fields, _ = mapper.enrich(_FACTS, {**_TK_KHAC, "submitterMode": "owner_as_submitter"})
    assert _ten_cong_dan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    values = _cong_dan(fields)
    assert values["CongDan_tenCongDan"] == "Trần Thị Bình"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1991"
    # Bên được ủy quyền không có dân tộc/email/fax trong hồ sơ → xoá ô cổng đổ từ tài khoản.
    cleared = {f["name"]: f["value"] for f in fields if f.get("clear")}
    assert cleared == {"CongDan_danTocCongDan": "", "CongDan_email": "", "CongDan_fax": ""}
    # Không lẫn nhân thân của chủ hồ sơ hay của tài khoản.
    assert not {"Kinh", _CHU, "0911000111", "001080000999"} & set(values.values())
    # Lệnh xoá nằm trong khối người nộp, trước khối chủ hồ sơ.
    dau_chu = next(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert all(i < dau_chu for i, f in enumerate(fields) if f.get("clear"))


def test_to_khai_thieu_so_can_cuoc_thi_xoa_o_so_va_ngay_sinh():
    facts = _CHU_HO_SO + [
        {"name": "NguoiDuocUyQuyen", "value": {"hoTen": "Trần Thị Bình", "gioiTinh": "Nữ"}},
    ]
    fields, _ = mapper.enrich(facts, {**_TK_KHAC, "submitterMode": "owner_as_submitter"})
    cong_dan = [f for f in fields if f["name"].startswith("CongDan_")]
    assert [f["name"] for f in cong_dan[:2]] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert cong_dan[1] == {"name": "CongDan_soCmnd", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True}
    values = _cong_dan(fields)
    assert values["CongDan_tenCongDan"] == "Trần Thị Bình"
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"


def test_tai_khoan_khong_ghi_o_readonly_khong_xoa_o_nao():
    for options in (_tai_khoan("NGUYỄN VĂN AN", _CHU), _TK_KHAC, {"formContext": {}}):
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
