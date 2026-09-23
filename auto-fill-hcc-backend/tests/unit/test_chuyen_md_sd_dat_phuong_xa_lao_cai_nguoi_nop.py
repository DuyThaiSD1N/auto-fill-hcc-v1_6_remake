"""[Lào Cai] 1.115679 (nộp ở phường/xã) — hai chế độ xác định NGƯỜI NỘP.

Khối người nộp có SÁU ô bắt buộc mà cổng chỉ đổ "theo tài khoản", nên nhân thân phải là của đúng một
người. Chế độ theo tài khoản giữ nguyên hai ô readonly cổng đã đổ (Họ và tên, Số Căn cước) và chỉ bù
nhân thân của chính người đăng nhập; chế độ theo tờ khai ghi đè CẢ khối vì người nộp là người khác.
"""

from pathlib import Path

from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process import mapper
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.schema import UI_COMP_BY_NAME

# Hồ sơ mẫu HS1: ông Đào Văn Tuấn nộp thay ông Hoàng Trung Thành theo Giấy uỷ quyền.
_CHU_HO_SO = "015085007662"
_NGUOI_NOP = "001088001234"

_FACTS = [
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "HOÀNG TRUNG THÀNH", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "1985",
         "NgayCap": "10/06/2025", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 39"}},
        {"HoTen": "ĐÀO VĂN TUẤN", "SoDinhDanh": _NGUOI_NOP, "NgaySinh": "02/03/1988",
         "GioiTinh": "Nam", "NgayCap": "15/01/2022",
         "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Tổ dân phố số 9"}},
    ]},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Đào Văn Tuấn", "soDinhDanh": _NGUOI_NOP, "ngaySinh": "02/03/1988",
        "ngayCapCccd": "15/01/2022", "dienThoai": "0912000111",
        "thuongTru": {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Tổ dân phố số 9"},
    }},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Hoàng Trung Thành"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2025"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_DiaChiDon",
     "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 39"}},
    {"name": "Don_DienThoai", "value": "0987654321"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_che_do_tai_khoan_lay_nhan_than_cua_chinh_nguoi_dang_nhap():
    """Người đi nộp là bên được uỷ quyền — không được lấy nhân thân của chủ hồ sơ."""
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "ĐÀO VĂN TUẤN", "applicantIdentityNumber": _NGUOI_NOP,
    }})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "02/03/1988"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_ngayCapCmnd"] == "15/01/2022"
    assert values["CongDan_maPhuongXa"] == "Xuân Tăng"
    assert values["CongDan_diaChi"] == "Tổ dân phố số 9"
    # Di động trên Đơn là của chủ hồ sơ → nộp thay thì KHÔNG chép sang khối người nộp.
    assert "CongDan_diDong" not in values
    assert not warnings


def test_che_do_tai_khoan_khong_dung_vao_hai_o_cong_da_do_san():
    fields, _ = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "ĐÀO VĂN TUẤN", "applicantIdentityNumber": _NGUOI_NOP,
    }})
    values = _values(fields)

    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values


def test_che_do_tai_khoan_khong_nhan_ra_nguoi_dang_nhap_thi_bo_trong_va_bao():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "NHÂM ĐẮC ĐẠT", "applicantIdentityNumber": "040204014488",
    }})
    values = _values(fields)

    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_maTinhThanh",
                 "CongDan_maPhuongXa", "CongDan_diaChi"):
        assert name not in values, name
    assert any("để trống nhân thân" in w for w in warnings)
    # Khối chủ hồ sơ là dữ liệu độc lập, vẫn phải đủ.
    assert values["ChuHoSo_tenChuHoSo"] == "HOÀNG TRUNG THÀNH"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Tổ 39"


def test_che_do_to_khai_ghi_de_ca_khoi_theo_ben_duoc_uy_quyen():
    assert "CongDan_tenCongDan" in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" in UI_COMP_BY_NAME

    fields, warnings = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)
    order = [f["name"] for f in fields]

    assert values["CongDan_tenCongDan"] == "ĐÀO VĂN TUẤN"
    assert values["CongDan_soCmnd"] == _NGUOI_NOP
    assert values["CongDan_ngaySinhCongDan"] == "02/03/1988"
    # Nhân thân còn thiếu của bên được uỷ quyền được bù từ giấy tờ khác CỦA CHÍNH người đó.
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["CongDan_diDong"] == "0912000111"
    assert order.index("CongDan_tenCongDan") < order.index("CongDan_soCmnd")
    assert not warnings


def test_che_do_to_khai_khong_co_uy_quyen_thi_lay_chu_ho_so():
    facts = [f for f in _FACTS if f["name"] != "NguoiDuocUyQuyen"]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "HOÀNG TRUNG THÀNH"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    assert values["CongDan_gioiTinhCongDan"] == "Nam", "suy từ xưng hô Ông khi không có ảnh thẻ"
    # Người nộp chính là chủ hồ sơ → số trên Đơn là số của người đó.
    assert values["CongDan_diDong"] == "0987654321"
    assert values["CongDan_diaChi"] == "Tổ 39"


def test_che_do_to_khai_canh_bao_khi_lech_tai_khoan():
    fields, warnings = mapper.enrich(_FACTS, {
        "formContext": {"applicantFullname": "NHÂM ĐẮC ĐẠT",
                        "applicantIdentityNumber": "040204014488"},
        "submitterMode": "owner_as_submitter",
    })

    assert _values(fields)["CongDan_tenCongDan"] == "ĐÀO VĂN TUẤN"
    assert any("lệch" in w and "bị chặn" in w for w in warnings)


def test_che_do_to_khai_chu_ho_so_to_chuc_khong_co_uy_quyen_thi_khong_dien():
    """Tổ chức không tự đi nộp được; không có giấy uỷ quyền thì không suy ra người nộp."""
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Xây dựng Lào Cai"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300123456"},
    ]
    fields, warnings = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert "CongDan_tenCongDan" not in values
    assert any("không có văn bản uỷ quyền" in w for w in warnings)
    # Tên cơ quan/MSDN là dữ liệu của TỔ CHỨC nên vẫn phát được.
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Xây dựng Lào Cai"
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175"' in block
