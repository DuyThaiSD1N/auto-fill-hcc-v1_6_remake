"""Mapper "thành lập công ty cổ phần": facts -> đúng formcontrolname của từng trang WebForms.

Dữ liệu mẫu lấy từ cột "Dữ liệu mẫu" trong bảng đặc tả cổng dangkyquamang.dkkd.gov.vn, nên test này
đồng thời là bản chốt tên control — sai một ký tự trong tên là điền hụt cả ô trên hồ sơ thật.
"""

from app.pipelines.thanh_lap_ctcp.process import mapper


def _facts(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _map(values: dict, page: str) -> dict[str, object]:
    return {f["name"]: f["value"] for f in mapper.enrich(_facts(values), page=page)}


def test_dia_chi_tach_dia_chi_va_lien_he():
    out = _map(
        {
            "TruSo_DiaChi": {
                "quocGia": "Việt Nam",
                "tinh": "Thành phố Đà Nẵng",
                "xa": "Phường Thanh Khê",
                "diaChi": "189 Dũng Sĩ Thanh Khê",
            },
            "TruSo_DienThoai": "0965772585",
            "TruSo_Email": "a@b.vn",
        },
        "dia-chi",
    )
    # Tiền tố "Thành phố"/"Phường" bị bỏ để extension khớp được với option trên cổng.
    assert out["ctl00$C$ADDRCtl$CITY_IDFld"] == "Đà Nẵng"
    assert out["ctl00$C$ADDRCtl$WARD_IDFld"] == "Thanh Khê"
    assert out["ctl00$C$ADDRCtl$STREET_NUMBERFld"] == "189 Dũng Sĩ Thanh Khê"
    assert out["ctl00$C$ADDRCtl$COUNTRY_IDFld"] == "Việt Nam"
    # Khối liên hệ của cổng này là DCONTCtl (HkdOnline viết DCONTClt) — dễ chép nhầm.
    assert out["ctl00$C$DCONTCtl$HO_PHONEFld"] == "0965772585"
    assert out["ctl00$C$DCONTCtl$HO_EMAILFld"] == "a@b.vn"


def test_dia_chi_khong_tich_khu_vuc_khi_giay_to_khong_ghi():
    out = _map({"TruSo_DiaChi": {"tinh": "Đà Nẵng"}}, "dia-chi")
    assert not [k for k in out if "ZONECtl" in k], "Không có căn cứ thì không được tích ô khu vực"


def test_dia_chi_tich_dung_o_khu_vuc_duoc_ghi():
    out = _map({"TruSo_KhuVuc": ["Khu công nghệ cao"]}, "dia-chi")
    assert out["ctl00$C$ZONECtl$HO_IN_HTPFld"] is True
    assert "ctl00$C$ZONECtl$HO_IN_IZFld" not in out


def test_ten_doanh_nghiep_tach_tien_to_loai_hinh():
    out = _map(
        {
            "DoanhNghiep_TenLoaiHinh": "Công ty cổ phần",
            "DoanhNghiep_TenRieng": "Quản lý vận động viên trẻ quốc gia",
            "DoanhNghiep_TenVietTat": "NYA",
        },
        "ten-doanh-nghiep",
    )
    assert out["ctl00$C$DROP_NAME_TYPE"] == "CÔNG TY CỔ PHẦN"
    assert out["ctl00$C$NAMEFld"] == "QUẢN LÝ VẬN ĐỘNG VIÊN TRẺ QUỐC GIA"
    assert out["ctl00$C$SHORT_NAMEFld"] == "NYA"


def test_von_map_bang_nguon_von_theo_dung_chi_so_dong():
    out = _map(
        {
            "Von_DieuLe": "5.000.000.000",
            "Von_NguonVon": [
                {"loai": "tu_nhan", "tyLe": "100", "soTien": "5.000.000.000"},
            ],
            "Von_TaiSanGopVon": [
                {"loai": "dong_vn", "tyLe": "100", "giaTri": "5.000.000.000"},
            ],
        },
        "thong-tin-ve-von",
    )
    base = "ctl00$C$UC_DW_CAPITALEditCtl"
    assert out[f"{base}$CPT_CHARTER_AMOUNTFld"] == "5000000000"
    # "Vốn tư nhân" là dòng thứ HAI của bảng nguồn vốn -> ctl03.
    assert out[f"{base}$CtlSourceList$ctl03$AMOUNTFld"] == "5000000000"
    assert out[f"{base}$CtlSourceList$ctl03$RATIO_PERCENTFld"] == "100"
    # "Đồng Việt Nam" là dòng ĐẦU của bảng tài sản góp vốn -> ctl02.
    assert out[f"{base}$CtlList$ctl02$ASSET_AMOUNTFld"] == "5000000000"
    # Dòng không có dữ liệu thì KHÔNG điền (form đã mặc định 0).
    assert f"{base}$CtlSourceList$ctl02$AMOUNTFld" not in out
    # Dòng "Tổng" (ctl06/ctl08) do cổng tự cộng, disabled -> tuyệt đối không map.
    assert f"{base}$CtlSourceList$ctl06$AMOUNTFld" not in out
    assert f"{base}$CtlList$ctl08$ASSET_AMOUNTFld" not in out


def test_co_phan_map_dong_pho_thong_va_chao_ban():
    out = _map(
        {
            "CoPhan_MenhGia": "10.000",
            "CoPhan_DanhSach": [
                {"loai": "pho_thong", "soLuong": "500000", "menhGia": "10000",
                 "giaTri": "5000000000", "tyLe": "100"},
            ],
            "CoPhan_ChaoBan": [{"loai": "pho_thong", "soLuong": "500000"}],
        },
        "thong-tin-ve-co-phan",
    )
    base = "ctl00$C$UC_DW_OTHEREditCtl"
    assert out[f"{base}$VALUE_OF_EACH_SHAREFld"] == "10000"
    assert out[f"{base}$CtlList$ctl02$QUANTITYFld"] == "500000"
    assert out[f"{base}$CtlList$ctl02$TOTAL_VALUEFld"] == "5000000000"
    assert out[f"{base}$CtlListSales$ctl02$QUANTITYFld"] == "500000"
    # Tổng (ctl07, hậu tố _Tt trên cổng) do hệ thống cộng -> không map.
    assert not [k for k in out if k.endswith("_Tt")]


def test_thue_chon_giong_tru_so_khi_khong_ke_khai_rieng():
    out = _map({"TruSo_DiaChi": {"tinh": "Đà Nẵng", "xa": "Thanh Khê"}}, "thong-tin-ve-thue")
    assert out["ctl00$C$UC_DW_TAXEditCtl$REP_RECV_ADDR_TYPEFld"] == "1"
    assert not [k for k in out if "UC_DW_TAXEditCtl$ADDRCtl" in k]


def test_thue_dien_khoi_dia_chi_khi_khac_tru_so():
    out = _map(
        {
            "TruSo_DiaChi": {"tinh": "Đà Nẵng", "xa": "Thanh Khê", "diaChi": "189 Dũng Sĩ"},
            "Thue_DiaChiNhanThongBao": {"tinh": "Đà Nẵng", "xa": "Hải Châu", "diaChi": "24 Trần Phú"},
            "Thue_NamTaiChinh": {"ngayBatDau": 1, "thangBatDau": 1, "ngayKetThuc": 31, "thangKetThuc": 12},
            "Thue_PhuongPhapGTGT": "Khấu trừ",
            "Thue_SoLaoDong": "10 người",
        },
        "thong-tin-ve-thue",
    )
    base = "ctl00$C$UC_DW_TAXEditCtl"
    assert out[f"{base}$REP_RECV_ADDR_TYPEFld"] == "0"
    assert out[f"{base}$ADDRCtl$WARD_IDFld"] == "Hải Châu"
    assert out[f"{base}$FIN_YEAR_END_MONTHFld"] == "12"
    assert out[f"{base}$TAX_CAL_METHOD_IDRbBox"] == "DED"
    assert out[f"{base}$TOTAL_OF_LABORSFld"] == "10"


def test_nguoi_nop_mac_dinh_la_nguoi_co_tham_quyen_ky():
    out = _map({"NguoiNop_HoTen": "Bùi Thị Phương Hạnh"}, "nguoi-nop-ho-so")
    assert out["ctl00$C$PERS_SUBGroup"] == "IS_REPRESENTATIVE_BUTTON"
    assert out["ctl00$C$PERSCtl$FULL_NAMEFld"] == "BÙI THỊ PHƯƠNG HẠNH"


def test_nguoi_nop_uy_quyen_va_gioi_tinh():
    out = _map(
        {
            "NguoiNop_VaiTro": "Người được ủy quyền",
            "NguoiNop_GioiTinh": "Nữ",
            "NguoiNop_SoDinhDanh": "049184011649",
            "NguoiNop_DienThoai": "0987147714",
        },
        "nguoi-nop-ho-so",
    )
    assert out["ctl00$C$PERS_SUBGroup"] == "IS_AUTHORIZED_BUTTON"
    assert out["ctl00$C$PERSCtl$GENDER_IDFld"] == "F"
    assert out["ctl00$C$PERSCtl$PERS_DOC_NOFld"] == "049184011649"
    assert out["ctl00$C$PERSCtl$PHONEFld"] == "0987147714"


def test_nganh_nghe_gom_ma_va_danh_dau_nganh_chinh():
    out = _map(
        {
            "NganhNghe_DanhSach": [
                {"ma": "9319", "ten": "Hoạt động của các cơ sở thể thao", "chinh": True},
                {"ma": "8551", "ten": "Giáo dục thể thao và giải trí"},
            ],
        },
        "nganh-nghe-kinh-doanh",
    )
    lines = out["__businessLines"]
    assert lines["codes"] == ["9319", "8551"]
    assert lines["main"] == "9319"
    assert out["ctl00$C$newBusinessLineCode"] == "9319"


def test_enrich_all_tra_du_8_trang_dung_thu_tu_menu():
    pages = mapper.enrich_all(_facts({"TruSo_DiaChi": {"tinh": "Đà Nẵng"}}))
    assert list(pages) == [
        "hinh-thuc-dang-ky", "dia-chi", "nganh-nghe-kinh-doanh", "ten-doanh-nghiep",
        "thong-tin-ve-von", "thong-tin-ve-co-phan", "thong-tin-ve-thue", "nguoi-nop-ho-so",
    ]


def test_hinh_thuc_dang_ky_luon_chot_thanh_lap_moi():
    """Trang đầu khối dữ liệu: cổng đã chọn sẵn "Thành lập mới", extension chỉ cần Lưu để đi tiếp.

    Vẫn phải trả field kể cả khi hồ sơ KHÔNG có dữ liệu gì — nếu trả rỗng thì trang này không lọt
    vào thứ tự chạy của extension và cả luồng dừng ngay từ bước một.
    """
    out = _map({}, "hinh-thuc-dang-ky")
    assert out["ctl00$C$REORGCtl$REORG_TYPE_IDFld"] == "Thành lập mới"
