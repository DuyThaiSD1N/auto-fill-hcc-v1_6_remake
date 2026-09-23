"""[Lào Cai] 1.115668 — hai chế độ xác định NGƯỜI NỘP.

Cùng form bước 2 với 1.115667: cổng đổ sẵn Họ tên/Số căn cước/địa chỉ/Di động của tài khoản định danh
rồi gửi Họ tên + Số căn cước + Ngày sinh sang CSDL quốc gia dân cư để xác thực trước khi cho nộp.
Chế độ theo tài khoản chỉ bù nhân thân của CHÍNH người đó (sửa ô "Họ và tên" là cổng xoá trắng Di động
+ Số căn cước); chế độ theo tờ khai phải ghi đè CẢ khối vì người nộp là người khác.
"""

from pathlib import Path

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import mapper
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import UI_COMP_BY_NAME

_ANCHOR = {"applicantFullname": "NGUYỄN VĂN NAM", "applicantIdentityNumber": "001085000123"}

# Hồ sơ mẫu: bên nhận chuyển nhượng (chủ hồ sơ) là bà Trần Thị Bé, người đi nộp là con trai có thẻ căn
# cước riêng trong hồ sơ.
_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "TRẦN THỊ BÉ", "SoDinhDanh": "034057017088", "NgaySinh": "12/03/1957",
         "GioiTinh": "Nữ", "DanToc": "Kinh", "NgayCap": "20/05/2021", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Tổ dân phố số 21 Kim Tân"}},
        {"HoTen": "NGUYỄN VĂN NAM", "SoDinhDanh": "001085000123", "NgaySinh": "08/09/1985",
         "GioiTinh": "Nam", "DanToc": "Kinh", "NgayCap": "15/01/2022",
         "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 9 ngõ 2"}},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Thị Bé"},
    {"name": "ChuHoSo_XungHo", "value": "Bà"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "034057017088"},
    {"name": "ChuHoSo_DiaChiHopDong",
     "value": {"tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Tổ dân phố số 21 Kim Tân"}},
    {"name": "Don_DienThoai", "value": "0912345678"},
]

_FACTS_TO_CHUC = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN NAM", "SoDinhDanh": "001085000123", "NgaySinh": "08/09/1985",
         "GioiTinh": "Nam", "NgayCap": "15/01/2022", "NoiCap": "Bộ Công an"},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Xây dựng Lào Cai"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300123456"},
    {"name": "ChuHoSo_DiaChiDkdn",
     "value": {"tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Số 1 Hoàng Liên"}},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_che_do_tai_khoan_lay_nhan_than_cua_chinh_nguoi_dang_nhap():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": _ANCHOR})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "08/09/1985"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_ngayCapCmnd"] == "15/01/2022"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert not warnings


def test_che_do_tai_khoan_khong_dung_vao_phan_cong_da_dien_san():
    """Sửa ô "Họ và tên" là cổng xoá trắng Di động + Số căn cước → không ghi đè khi đã đúng người."""
    fields, _ = mapper.enrich(_FACTS, {"formContext": _ANCHOR})
    values = _values(fields)

    for name in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_diDong",
                 "CongDan_maTinhThanh", "CongDan_maPhuongXa", "CongDan_diaChi"):
        assert name not in values, name


def test_che_do_tai_khoan_khong_lay_the_cua_chu_ho_so():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "LÊ THỊ HOA", "applicantIdentityNumber": "001199000777",
    }})
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert "CongDan_ngayCapCmnd" not in values
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)
    # Khối chủ hồ sơ vẫn phải đủ — không phụ thuộc ai đi nộp.
    assert values["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ BÉ"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố số 21 Kim Tân"


def test_khong_co_moc_tai_khoan_thi_bo_trong_khoi_nguoi_nop():
    for options in ({}, None):
        fields, warnings = mapper.enrich(_FACTS, options)
        assert "CongDan_ngaySinhCongDan" not in _values(fields)
        assert any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_nhieu_nguoi_trung_ho_ten_ma_khong_co_so_thi_khong_doan():
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"] + [
        {"name": "DanhSachCccd", "value": [
            {"HoTen": "NGUYỄN VĂN NAM", "NgaySinh": "08/09/1985"},
            {"HoTen": "NGUYỄN VĂN NAM", "NgaySinh": "01/01/1970"},
        ]},
    ]
    fields, warnings = mapper.enrich(facts, {"formContext": {"applicantFullname": "Nguyễn Văn Nam"}})

    assert "CongDan_ngaySinhCongDan" not in _values(fields)
    assert any("trùng họ tên" in w for w in warnings)


def test_che_do_to_khai_ghi_de_ca_khoi_theo_chu_ho_so():
    assert "CongDan_tenCongDan" in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" in UI_COMP_BY_NAME

    fields, warnings = mapper.enrich(_FACTS, {
        "formContext": _ANCHOR, "submitterMode": "owner_as_submitter",
    })
    values = _values(fields)
    order = [f["name"] for f in fields]

    assert values["CongDan_tenCongDan"] == "TRẦN THỊ BÉ"
    assert values["CongDan_soCmnd"] == "034057017088"
    assert values["CongDan_ngaySinhCongDan"] == "12/03/1957"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_diDong"] == "0912345678"
    assert values["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert values["CongDan_diaChi"] == "Tổ dân phố số 21 Kim Tân"
    # Họ tên phải đi TRƯỚC: cổng xoá trắng Di động + Số căn cước khi ô đó đổi.
    assert order.index("CongDan_tenCongDan") < order.index("CongDan_soCmnd")
    assert order.index("CongDan_tenCongDan") < order.index("CongDan_diDong")
    assert any("lệch tài khoản sẽ bị chặn" in w for w in warnings)


def test_che_do_to_khai_uu_tien_ben_duoc_uy_quyen():
    facts = _FACTS + [
        {"name": "NguoiDuocUyQuyen", "value": {
            "hoTen": "PHẠM VĂN CHIẾN", "soDinhDanh": "001188000222", "ngaySinh": "01/02/1988",
            "ngayCapCccd": "05/06/2021", "dienThoai": "0900000123",
            "thuongTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 5"},
        }},
    ]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "PHẠM VĂN CHIẾN"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1988"
    assert values["CongDan_diaChi"] == "Số 5"


def test_che_do_to_khai_chu_ho_so_to_chuc_khong_co_uy_quyen_thi_khong_dien():
    """Tổ chức không tự đi nộp được — không có giấy ủy quyền thì giữ nguyên phần cổng đổ sẵn."""
    fields, warnings = mapper.enrich(_FACTS_TO_CHUC, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert "CongDan_tenCongDan" not in values
    assert "CongDan_ngaySinhCongDan" not in values
    assert any("Chủ hồ sơ là TỔ CHỨC" in w for w in warnings)
    # Tên cơ quan/MST là dữ liệu của TỔ CHỨC nên vẫn phát được.
    assert values["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH XÂY DỰNG LÀO CAI"
    assert values["CongDan_maSoThueNguoiNop"] == "5300123456"


def test_che_do_tai_khoan_van_chay_khi_chu_ho_so_la_to_chuc():
    fields, warnings = mapper.enrich(_FACTS_TO_CHUC, {"formContext": _ANCHOR})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "08/09/1985"
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert not warnings


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "dang-ky-bien-dong-dat-dai-lao-cai"' in block
