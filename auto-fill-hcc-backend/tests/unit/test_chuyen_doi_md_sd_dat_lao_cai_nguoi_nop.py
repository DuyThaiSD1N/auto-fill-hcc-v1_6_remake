"""[Lào Cai] 1.115651 — hai chế độ xác định NGƯỜI NỘP.

Theo tài khoản (mặc định): nhân thân khối người nộp lấy từ giấy tờ của CHÍNH người đăng nhập. Theo tờ
khai (`submitterMode="owner_as_submitter"`): bỏ mốc, người nộp là chủ hồ sơ cá nhân, nhân thân bù từ
CCCD/giấy tờ khác cùng người. Hai ô readonly Họ tên/Số Căn cước: tài khoản không phát, tờ khai ghi theo
người đó và xoá ô nhân thân tài khoản mà hồ sơ không có.
"""

from pathlib import Path

from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import mapper
from app.pipelines._shared.lao_cai_nguoi_nop import O_NHAN_THAN_XOA_DUOC

_CHU_HO_SO = "001099000001"
_NGUOI_KHAC = "001088000002"
_TO_KHAI = {"submitterMode": "owner_as_submitter"}

_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "01/02/1980",
         "GioiTinh": "Nam", "DanToc": "Kinh", "NgayCap": "10/06/2021",
         "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {"HoTen": "TRẦN THỊ B", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "05/06/1988",
         "GioiTinh": "Nữ", "DanToc": "Tày", "NgayCap": "15/01/2022", "NoiCap": "Bộ Công an"},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_enrich_van_tra_list_nhu_cu():
    assert isinstance(mapper.enrich(_FACTS, {}), list)


def test_toggle_tat_co_moc_lay_nhan_than_nguoi_dang_nhap():
    """Người đăng nhập là người khác chủ hồ sơ → nhân thân của CHÍNH người đó (hành vi cũ)."""
    fields = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _NGUOI_KHAC,
    }})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "05/06/1988"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"


def test_toggle_bat_lay_chu_ho_so_va_canh_bao_lech_tai_khoan():
    """Mốc tài khoản là người khác → theo tờ khai vẫn lấy chủ hồ sơ, kèm cảnh báo lệch."""
    fields, warnings = mapper.enrich_with_warnings(_FACTS, {
        **_TO_KHAI,
        "formContext": {"applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _NGUOI_KHAC},
    })
    values = _values(fields)

    # Đơn chỉ có năm sinh → nhường ngày đủ trên CCCD cùng số định danh.
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1980"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)


def test_toggle_bat_khop_tai_khoan_va_khong_moc_thi_khong_canh_bao():
    _, warnings = mapper.enrich_with_warnings(_FACTS, {
        **_TO_KHAI,
        "formContext": {"applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": _CHU_HO_SO},
    })
    assert not warnings
    _, warnings = mapper.enrich_with_warnings(_FACTS, _TO_KHAI)
    assert not warnings


def test_toggle_bat_khong_gop_nhan_than_nguoi_khac_so_va_bo_ngay_chi_co_nam():
    """Không có CCCD của chính chủ hồ sơ → không mượn nhân thân của người khác số định danh;
    năm sinh trên Đơn không đủ dd/mm/yyyy → không phát."""
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"] + [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": "001077000003", "NgaySinh": "09/09/1955",
             "GioiTinh": "Nam", "NgayCap": "01/01/2015", "NoiCap": "Công an tỉnh Lào Cai"},
        ]},
    ]
    fields, _ = mapper.enrich_with_warnings(facts, _TO_KHAI)
    values = _values(fields)

    # Không có nguồn của chính người đó → XOÁ ô cổng đổ từ tài khoản.
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_ngayCapCmnd"] == ""
    assert values["CongDan_noiCapCmnd"] == ""
    # Chỉ còn giới tính suy từ xưng hô "Ông" trên Đơn của chính chủ hồ sơ.
    assert values["CongDan_gioiTinhCongDan"] == "Nam"


def test_toggle_bat_gop_theo_ho_ten_khi_don_thieu_so():
    facts = [
        {"name": "DanhSachCccd", "value": [
            {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "01/02/1980",
             "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an"},
        ]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyen Van A"},
        {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    ]
    fields, _ = mapper.enrich_with_warnings(facts, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1980"
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"


def test_toggle_bat_chu_ho_so_to_chuc_thi_bo_trong_nhan_than():
    facts = [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "LÊ VĂN C", "SoDinhDanh": "001066000004", "NgaySinh": "02/02/1970"},
        ]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH X"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    ]
    fields, warnings = mapper.enrich_with_warnings(facts, _TO_KHAI)
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    # Tên cơ quan/MST là dữ liệu của TỔ CHỨC → vẫn phát như cũ.
    assert values["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH X"
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert any("để trống nhân thân" in w for w in warnings)


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert 'cfg.key === "chuyen-muc-dich-su-dung-dat-lao-cai"' in block


def _congdan_names(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ho_ten_can_cuoc_dung_dau_khoi_va_xoa_o_tai_khoan_ho_so_khong_co():
    """Chỉ có thẻ của người khác (tài khoản) → nhân thân chủ hồ sơ thiếu thì xoá, không mượn thẻ đó."""
    facts = [
        {"name": "DanhSachCccd", "value": [_FACTS[0]["value"][1]]},
        *[f for f in _FACTS if f["name"] != "DanhSachCccd"],
    ]
    fields, _ = mapper.enrich_with_warnings(facts, {**_TO_KHAI, "formContext": {
        "applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _NGUOI_KHAC,
    }})

    assert _congdan_names(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    cleared = {f["name"] for f in fields if f.get("clear")}
    # Mọi form Lào Cai chung bộ ô CongDan_*: hồ sơ không có mục nào thì xoá đủ ô tài khoản đã đổ.
    assert cleared == set(O_NHAN_THAN_XOA_DUOC)
    assert all(f["value"] == "" for f in fields if f.get("clear"))
    assert not {"05/06/1988", "Tày", "15/01/2022", _NGUOI_KHAC, "Bộ Công an"} & set(values.values())


def test_to_khai_khong_so_dinh_danh_thi_xoa_o_can_cuoc_ngay_sau_ho_ten():
    facts = [f for f in _FACTS if f["name"] not in ("ChuHoSo_SoDinhDanh", "DanhSachCccd")]
    fields, _ = mapper.enrich_with_warnings(facts, _TO_KHAI)

    assert _congdan_names(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    so_cmnd = next(f for f in fields if f["name"] == "CongDan_soCmnd")
    assert so_cmnd["value"] == "" and so_cmnd.get("clear") is True


def test_tai_khoan_khong_ghi_o_readonly_va_khong_xoa_o_nao():
    ctx = {"formContext": {"applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _NGUOI_KHAC}}
    for options in (ctx, {}):
        fields, _ = mapper.enrich_with_warnings(_FACTS, options)
        assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_congdan_names(fields))
        assert not any(f.get("clear") for f in fields)


def test_to_khai_khong_doc_duoc_ho_ten_thi_khong_ghi_o_readonly_va_khong_xoa():
    """Chưa biết người nộp là ai (chỉ có số, không có họ tên) → không đổi riêng Số Căn cước, không xoá gì."""
    facts = [f for f in _FACTS if f["name"] not in ("ChuHoSo_HoTen", "DanhSachCccd", "NguoiTrongGiayTo")]
    fields = mapper.enrich(facts, _TO_KHAI)
    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_congdan_names(fields))
    assert not any(f.get("clear") for f in fields)
