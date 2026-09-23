"""[Lào Cai] 1.115652 — hai chế độ xác định NGƯỜI NỘP.

Cổng đổ sẵn Họ tên + Số Căn cước của tài khoản vào hai ô readonly rồi gửi chính chúng (kèm ngày sinh)
sang CSDL quốc gia dân cư để xác thực trước khi cho nộp. Vì vậy cả khối phải là nhân thân của MỘT
người: người đang đăng nhập (mặc định) hoặc người trong tờ khai (khi bật cài đặt), không ghép chéo.
"""

from pathlib import Path

from app.pipelines.dieu_chinh_giao_dat_lao_cai.process import mapper
from app.pipelines.dieu_chinh_giao_dat_lao_cai.process.schema import UI_COMP_BY_NAME

_ANCHOR = {"applicantFullname": "ĐỖ XUÂN THÀNH", "applicantIdentityNumber": "035066009759"}

# Hồ sơ mẫu của BA: chủ hồ sơ là doanh nghiệp, người đại diện pháp luật có CCCD trên ĐKDN, thành viên
# góp vốn thứ hai cũng có số định danh → nhiều ứng viên, phải chọn bằng mốc tài khoản.
_FACTS = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY CỔ PHẦN ĐẦU TƯ X"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300727490"},
    {"name": "ChuHoSo_NoiCuTru",
     "value": {"tinh": "Lào Cai", "xa": "Phường Nam Cường", "diaChi": "Số 177 Phan Chu Trinh"}},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "ĐỖ XUÂN THÀNH", "SoDinhDanh": "035066009759", "NgaySinh": "06/12/1966",
         "GioiTinh": "Nam", "NgayCap": "30/08/2021",
         "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
         "DienThoai": "0913287157",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Phường Nam Cường", "diaChi": "Số nhà 194, phố Soi Tiền"}},
        {"HoTen": "ĐỖ THỊ HẢI YẾN", "SoDinhDanh": "035190009041",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Phường Nam Cường", "diaChi": "Tổ 27"}},
    ]},
    {"name": "NguoiNop_HoTen", "value": "ĐỖ XUÂN THÀNH"},
    {"name": "NguoiNop_SoDinhDanh", "value": "035066009759"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_ho_ten_va_can_cuoc_luon_di_cung_nguoi_voi_phan_nhan_than():
    """Khối nửa của tài khoản nửa của người trong hồ sơ là lỗi đã gặp trên cổng thật."""
    assert "CongDan_tenCongDan" in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" in UI_COMP_BY_NAME

    # Chế độ TÀI KHOẢN: ghi lại ĐÚNG chuỗi mốc, không lấy biến thể trong giấy tờ.
    fields, _ = mapper.enrich(_FACTS, {"formContext": _ANCHOR})
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "ĐỖ XUÂN THÀNH"
    assert values["CongDan_soCmnd"] == "035066009759"
    assert values["CongDan_ngaySinhCongDan"] == "06/12/1966"

    # Chế độ TỜ KHAI: ghi theo người trong hồ sơ.
    fields, _ = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "ĐỖ XUÂN THÀNH"
    assert values["CongDan_soCmnd"] == "035066009759"


def test_khong_xac_dinh_duoc_nguoi_nop_thi_khong_ghi_ho_ten_can_cuoc():
    """Không có mốc → bỏ trống cả khối, kể cả hai ô cổng đã đổ sẵn (không đụng vào)."""
    for options in ({}, None):
        fields, _ = mapper.enrich(_FACTS, options)
        values = _values(fields)
        assert "CongDan_tenCongDan" not in values
        assert "CongDan_soCmnd" not in values


def test_che_do_tai_khoan_lay_nhan_than_cua_chinh_nguoi_dang_nhap():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": _ANCHOR})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "06/12/1966"
    assert values["CongDan_ngayCapCmnd"] == "30/08/2021"
    assert values["CongDan_diDong"] == "0913287157"
    assert values["CongDan_diaChi"] == "Số nhà 194, phố Soi Tiền"
    assert not warnings


def test_che_do_tai_khoan_khong_lay_nguoi_khac_trong_ho_so():
    """Tài khoản là thành viên góp vốn thứ hai → không được lấy nhân thân của người đại diện."""
    fields, _ = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "ĐỖ THỊ HẢI YẾN", "applicantIdentityNumber": "035190009041",
    }})
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert "CongDan_ngayCapCmnd" not in values
    assert "CongDan_diDong" not in values
    assert values["CongDan_diaChi"] == "Tổ 27"


def test_che_do_tai_khoan_khong_co_moc_thi_bo_trong_ca_khoi():
    """Yêu cầu nghiệp vụ: không có thông tin tài khoản thì NHẤT QUYẾT không điền."""
    fields, warnings = mapper.enrich(_FACTS, {})
    values = _values(fields)

    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd",
                 "CongDan_diDong", "CongDan_maTinhThanh", "CongDan_maPhuongXa", "CongDan_diaChi"):
        assert name not in values, name
    assert any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)
    # Khối chủ hồ sơ vẫn phải đủ — nó là dữ liệu độc lập, không phụ thuộc người đi nộp.
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY CỔ PHẦN ĐẦU TƯ X"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Số 177 Phan Chu Trinh"


def test_che_do_tai_khoan_co_moc_nhung_ho_so_khong_co_giay_to_cua_nguoi_do():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "NHÂM ĐẮC ĐẠT", "applicantIdentityNumber": "001199000111",
    }})
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)
    # Tên cơ quan/MST là của TỔ CHỨC chủ hồ sơ nên vẫn phát được.
    assert values["CongDan_tenCoQuanToChuc"] == "CÔNG TY CỔ PHẦN ĐẦU TƯ X"


def test_chi_khop_ho_ten_khi_khong_doc_duoc_so_dinh_danh():
    """Giấy tờ cũ hay in CMND 9 số → cho khớp theo họ tên khi một trong hai phía thiếu số."""
    facts = [f for f in _FACTS if f["name"] != "NguoiTrongGiayTo"] + [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "ĐỖ XUÂN THÀNH", "NgaySinh": "06/12/1966", "DienThoai": "0913287157"},
        ]},
    ]
    fields, _ = mapper.enrich(facts, {"formContext": {"applicantFullname": "Đỗ Xuân Thành"}})

    assert _values(fields)["CongDan_ngaySinhCongDan"] == "06/12/1966"


def test_che_do_to_khai_uu_tien_ben_duoc_uy_quyen():
    facts = _FACTS + [
        {"name": "NguoiDuocUyQuyen", "value": {
            "hoTen": "NGUYỄN VĂN B", "soDinhDanh": "001188000222", "ngaySinh": "01/02/1988",
            "ngayCapCccd": "05/06/2021", "dienThoai": "0900000000",
            "thuongTru": {"tinh": "Lào Cai", "xa": "Phường Nam Cường", "diaChi": "Số 5"},
        }},
    ]
    fields, warnings = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1988"
    assert values["CongDan_diaChi"] == "Số 5"
    assert not any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_che_do_to_khai_bo_qua_moc_tai_khoan_nhung_canh_bao_khi_lech():
    """Bật cài đặt = cán bộ chủ động lấy theo tờ khai; lệch tài khoản thì cổng chặn nộp → phải báo."""
    fields, warnings = mapper.enrich(_FACTS, {
        "formContext": {"applicantFullname": "NHÂM ĐẮC ĐẠT", "applicantIdentityNumber": "001199000111"},
        "submitterMode": "owner_as_submitter",
    })
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "06/12/1966"
    assert values["CongDan_tenCongDan"] == "ĐỖ XUÂN THÀNH"
    assert any("không đúng với tài khoản đăng nhập" in w for w in warnings)


def test_o_ve_viec_van_phat_du_khi_khong_xac_dinh_duoc_nguoi_nop():
    """Trích yếu là dữ liệu của hồ sơ, không phụ thuộc ai đi nộp."""
    facts = _FACTS + [{"name": "Don_TrichYeu", "value": "Đề nghị điều chỉnh Quyết định số 857/QĐ-UBND"}]
    fields, _ = mapper.enrich(facts, {})

    assert _values(fields)["HoSoOnline_veViec"] == "Đề nghị điều chỉnh Quyết định số 857/QĐ-UBND"


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "dieu-chinh-quyet-dinh-giao-dat-lao-cai"' in block
