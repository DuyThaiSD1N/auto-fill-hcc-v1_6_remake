"""[Lào Cai] 1.115670 (biến động do chia/tách/sáp nhập tổ chức) — ba luồng khối NGƯỜI NỘP.

Cổng đối chiếu Họ tên + Số Căn cước + Ngày sinh của khối người nộp với CSDL quốc gia dân cư và tài khoản
đăng nhập → cả khối phải là MỘT người. Bản extension cũ (không gửi formContext) giữ nguyên luồng cũ.
Chủ hồ sơ thường là TỔ CHỨC: ô tên cơ quan/MST của khối người nộp vẫn phát ở mọi chế độ.
Dữ liệu dưới đây là GIẢ.
"""

from pathlib import Path

from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process import mapper

_KY = "010075000444"   # giám đốc ký Đơn Mẫu 24
_UQ = "010192000555"   # bên được ủy quyền đi nộp
_KHAC = "010160000666"
_TO_CHUC = "Trung tâm Dịch vụ Giả Định"

_PROXY = {
    "hoTen": "Đỗ Thị Nộp", "soDinhDanh": _UQ, "ngaySinh": "08/09/1992", "ngayCapCccd": "20/12/2024",
    "dienThoai": "0913000333", "thuongTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ Năm"},
}

_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "ĐỖ THỊ NỘP", "SoDinhDanh": _UQ, "NgaySinh": "08/09/1992", "GioiTinh": "Nữ",
         "DanToc": "Kinh", "NgayCap": "20/12/2024", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ Năm"}},
    ]},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Phạm Văn Ký", "SoDinhDanh": _KY, "NgaySinh": "1975", "GioiTinh": "Nam"},
    ]},
    {"name": "NguoiDuocUyQuyen", "value": _PROXY},
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": _TO_CHUC},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Số 1 đường Giả"}},
    {"name": "ChuHoSo_DienThoai", "value": "02143000111"},
    # Khối phẳng do LLM chọn (luồng cũ dùng thẳng): người ký đơn.
    {"name": "NguoiNop_HoTen", "value": "Phạm Văn Ký"},
    {"name": "NguoiNop_SoDinhDanh", "value": _KY},
    {"name": "NguoiNop_GioiTinh", "value": "Nam"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Số 1 đường Giả"}},
    {"name": "NguoiNop_DienThoai", "value": "02143000111"},
    {"name": "ThuaDat_SoThua", "value": "7"},
]

_NHAN_THAN = (
    "CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan",
    "CongDan_danTocCongDan", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd", "CongDan_maTinhThanh",
    "CongDan_maPhuongXa", "CongDan_diaChi", "CongDan_diDong", "CongDan_email",
)


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _nop_warnings(warnings):
    return [w for w in warnings if "Thông tin người nộp hồ sơ" in w or "NGƯỜI ĐANG ĐI NỘP" in w]


def test_tai_khoan_khop_cccd_lay_ben_duoc_uy_quyen_khong_lay_nguoi_ky_don():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "Đỗ Thị Nộp", "applicantIdentityNumber": _UQ,
    }})
    values = _values(fields)

    # Hai ô readonly cổng đã đổ đúng tài khoản → không ghi.
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "08/09/1992"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    assert "Cam Đường" in values["CongDan_maPhuongXa"]
    assert values["CongDan_diaChi"] == "Tổ Năm"
    assert values["CongDan_diDong"] == "0913000333"
    assert values["CongDan_tenCoQuanToChuc"] == _TO_CHUC
    assert not _nop_warnings(warnings)
    # Khối chủ hồ sơ tổ chức giữ nguyên, không phát 7 ô cá nhân.
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == _TO_CHUC
    assert "ChuHoSo_tenChuHoSo" not in values


def test_tai_khoan_chi_khop_ten_khi_thieu_so():
    facts = [f for f in _FACTS if f["name"] not in ("NguoiNop_SoDinhDanh",)]
    # Mốc không có số → khớp họ tên bỏ dấu, lấy người ký đơn.
    fields, warnings = mapper.enrich(facts, {"formContext": {"applicantFullname": "PHAM VAN KY"}})
    values = _values(fields)

    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert not _nop_warnings(warnings)


def test_form_context_rong_bo_trong_nhan_than_van_phat_o_to_chuc():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {}})
    values = _values(fields)

    for name in _NHAN_THAN:
        assert name not in values, name
    assert values["CongDan_tenCoQuanToChuc"] == _TO_CHUC
    assert any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_tai_khoan_khong_co_trong_ho_so_bo_trong_va_canh_bao():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "Người Lạ Giả", "applicantIdentityNumber": _KHAC,
    }})
    values = _values(fields)

    for name in _NHAN_THAN:
        assert name not in values, name
    assert values["CongDan_tenCoQuanToChuc"] == _TO_CHUC
    assert any("Người Lạ Giả" in w and "để trống" in w for w in warnings)


def test_to_khai_co_uy_quyen_lay_ben_duoc_uy_quyen():
    fields, warnings = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "Đỗ Thị Nộp"
    assert values["CongDan_soCmnd"] == _UQ
    # Bù từ ảnh CCCD của CHÍNH người được ủy quyền.
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_tenCoQuanToChuc"] == _TO_CHUC
    assert not _nop_warnings(warnings)


def test_to_khai_khong_uy_quyen_lay_nguoi_ky_don():
    facts = [f for f in _FACTS if f["name"] != "NguoiDuocUyQuyen"]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "Phạm Văn Ký"
    assert values["CongDan_soCmnd"] == _KY
    # Người ký đơn chỉ có năm sinh → XOÁ ô ngày sinh cổng đổ từ tài khoản.
    assert values["CongDan_ngaySinhCongDan"] == ""


def test_to_khai_khong_uy_quyen_chu_ho_so_ca_nhan():
    facts = [
        {"name": "ChuHoSo_LaToChuc", "value": False},
        {"name": "ChuHoSo_HoTen", "value": "Vi Thị Chủ"},
        {"name": "ChuHoSo_SoDinhDanh", "value": _KHAC},
        {"name": "ChuHoSo_NgaySinh", "value": "04/04/1960"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ Bảy"}},
    ]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "Vi Thị Chủ"
    assert values["CongDan_soCmnd"] == _KHAC
    assert values["CongDan_ngaySinhCongDan"] == "04/04/1960"
    assert values["CongDan_diaChi"] == "Tổ Bảy"


def test_to_khai_to_chuc_khong_ai_di_nop_thi_bo_trong():
    facts = [f for f in _FACTS if not f["name"].startswith("NguoiNop_") and f["name"] != "NguoiDuocUyQuyen"]
    fields, warnings = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    for name in _NHAN_THAN:
        assert name not in values, name
    assert values["CongDan_tenCoQuanToChuc"] == _TO_CHUC
    assert any("để trống khối" in w for w in warnings)


def test_to_khai_lech_tai_khoan_thi_canh_bao_cong_chan():
    fields, warnings = mapper.enrich(_FACTS, {
        "submitterMode": "owner_as_submitter",
        "formContext": {"applicantFullname": "Phạm Văn Ký", "applicantIdentityNumber": _KY},
    })

    assert _values(fields)["CongDan_tenCongDan"] == "Đỗ Thị Nộp"
    assert any("lệch là bị chặn" in w for w in warnings)


def test_khong_gop_nhan_than_nguoi_khac_so_va_ngay_chi_co_nam_khong_phat():
    facts = [
        {"name": "ChuHoSo_TenToChuc", "value": _TO_CHUC},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Phạm Văn Ký", "SoDinhDanh": _KY, "NgaySinh": "1975"},
            {"HoTen": "Phạm Văn Ký", "SoDinhDanh": _KHAC, "NgaySinh": "06/06/1950",
             "NgayCap": "07/07/2021", "DanToc": "Tày",
             "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ Tám"}},
        ]},
        {"name": "NguoiNop_HoTen", "value": "Phạm Văn Ký"},
        {"name": "NguoiNop_SoDinhDanh", "value": _KY},
    ]
    for options in (
        {"formContext": {"applicantFullname": "Phạm Văn Ký", "applicantIdentityNumber": _KY}},
        {"submitterMode": "owner_as_submitter"},
    ):
        fields, _ = mapper.enrich(facts, options)
        values = _values(fields)
        theo_to_khai = "submitterMode" in options
        if theo_to_khai:
            assert values["CongDan_soCmnd"] == _KY
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
    from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process.prompt import EXTRA_RULES
    from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process.schema import (
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
    assert 'cfg.key === "dang-ky-bien-dong-chia-tach-to-chuc-lao-cai"' in block


# ----- Chốt khối người nộp theo chính sách chung Lào Cai (_shared/lao_cai_nguoi_nop) -----
_TK_KHAC = {"formContext": {"applicantFullname": "Người Lạ Giả", "applicantIdentityNumber": _KHAC}}


def _ten_cong_dan(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ho_ten_va_so_can_cuoc_dung_dau_xoa_o_nhan_than_thieu():
    fields, _ = mapper.enrich(_FACTS, {**_TK_KHAC, "submitterMode": "owner_as_submitter"})
    assert _ten_cong_dan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    values = {k: v for k, v in _values(fields).items() if k.startswith("CongDan_")}
    assert values["CongDan_tenCongDan"] == "Đỗ Thị Nộp"
    assert values["CongDan_soCmnd"] == _UQ
    assert values["CongDan_ngaySinhCongDan"] == "08/09/1992"
    assert values["CongDan_tenCoQuanToChuc"] == _TO_CHUC
    # Bên được ủy quyền không có email/fax trong hồ sơ → xoá ô cổng đổ từ tài khoản.
    cleared = {f["name"]: f["value"] for f in fields if f.get("clear")}
    assert cleared == {"CongDan_email": "", "CongDan_fax": ""}
    # Không lẫn nhân thân người ký đơn, của tổ chức hay của tài khoản.
    assert not {_KY, "02143000111", "Số 1 đường Giả", _KHAC} & set(values.values())
    # Lệnh xoá nằm trong khối người nộp, trước khối chủ hồ sơ.
    dau_chu = next(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert all(i < dau_chu for i, f in enumerate(fields) if f.get("clear"))


def test_to_khai_thieu_so_can_cuoc_thi_xoa_o_so_va_ngay_sinh():
    facts = [
        {"name": "ChuHoSo_TenToChuc", "value": _TO_CHUC},
        {"name": "NguoiDuocUyQuyen", "value": {"hoTen": "Đỗ Thị Nộp", "gioiTinh": "Nữ"}},
    ]
    fields, _ = mapper.enrich(facts, {**_TK_KHAC, "submitterMode": "owner_as_submitter"})
    cong_dan = [f for f in fields if f["name"].startswith("CongDan_")]
    assert [f["name"] for f in cong_dan[:2]] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert cong_dan[1] == {"name": "CongDan_soCmnd", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True}
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "Đỗ Thị Nộp"
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"


def test_tai_khoan_khong_ghi_o_readonly_khong_xoa_o_nao():
    for options in (
        {"formContext": {"applicantFullname": "ĐỖ THỊ NỘP", "applicantIdentityNumber": _UQ}},
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
