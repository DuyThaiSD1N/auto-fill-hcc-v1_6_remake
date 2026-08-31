"""Mapper "thành lập công ty TNHH hai thành viên trở lên": facts -> đúng formcontrolname từng trang.

Dữ liệu mẫu lấy từ cột "Dữ liệu mẫu" trong bảng đặc tả 9 sheet của cổng dangkyquamang.dkkd.gov.vn
(hồ sơ CÔNG TY TNHH DỊCH VỤ VẬN TẢI THƯƠNG HUYỀN NHI), nên test này đồng thời là bản chốt tên
control — sai một ký tự trong tên là điền hụt cả ô trên hồ sơ thật.
"""

from app.pipelines.thanh_lap_ctythnn_2_nguoi.process import mapper
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.schema import PAGES


def _facts(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _map(values: dict, page: str) -> dict[str, object]:
    return {f["name"]: f["value"] for f in mapper.enrich(_facts(values), page=page)}


def _fields(values: dict, page: str) -> dict[str, dict]:
    return {f["name"]: f for f in mapper.enrich(_facts(values), page=page)}


# --------------------------------------------------------------------------- tên doanh nghiệp
def test_ten_doanh_nghiep_tach_tien_to_loai_hinh():
    out = _map(
        {
            "DoanhNghiep_TenLoaiHinh": "Công ty TNHH",
            "DoanhNghiep_TenRieng": "Dịch vụ vận tải Thương Huyền Nhi",
            "DoanhNghiep_TenNuocNgoai": "THUONG HUYEN NHI TRANSPORTATION SERVICES COMPANY LIMITED",
            "DoanhNghiep_TenVietTat": "CÔNG TY TNHH DVVT THƯƠNG HUYỀN NHI",
        },
        "ten-doanh-nghiep",
    )
    assert out["ctl00$C$DROP_NAME_TYPE"] == "CÔNG TY TNHH"
    assert out["ctl00$C$NAMEFld"] == "DỊCH VỤ VẬN TẢI THƯƠNG HUYỀN NHI"
    assert out["ctl00$C$NAME_FFld"].startswith("THUONG HUYEN NHI")
    assert out["ctl00$C$SHORT_NAMEFld"] == "CÔNG TY TNHH DVVT THƯƠNG HUYỀN NHI"


def test_ten_doanh_nghiep_khong_ro_loai_hinh_thi_ve_tnhh_khong_ve_mtv():
    """Giấy mờ chữ tiền tố: mặc định phải là TNHH (hai thành viên), tuyệt đối không rơi về MTV."""
    out = _map({"DoanhNghiep_TenRieng": "ABC"}, "ten-doanh-nghiep")
    assert out["ctl00$C$DROP_NAME_TYPE"] == "CÔNG TY TNHH"


# --------------------------------------------------------------------------- địa chỉ
def test_dia_chi_tach_dia_chi_va_lien_he():
    out = _map(
        {
            "TruSo_DiaChi": {
                "quocGia": "Việt Nam",
                "tinh": "TP Đà Nẵng",
                "xa": "Điện Bàn",
                "diaChi": "37/14 Nguyễn Văn Trỗi",
            },
            "TruSo_DienThoai": "0905514024",
        },
        "dia-chi",
    )
    assert out["ctl00$C$ADDRCtl$COUNTRY_IDFld"] == "Việt Nam"
    assert out["ctl00$C$ADDRCtl$CITY_IDFld"] == "Đà Nẵng"
    assert out["ctl00$C$ADDRCtl$WARD_IDFld"] == "Điện Bàn"
    assert out["ctl00$C$ADDRCtl$STREET_NUMBERFld"] == "37/14 Nguyễn Văn Trỗi"
    # Khối liên hệ của cổng này là DCONTCtl (HkdOnline viết DCONTClt) — dễ chép nhầm.
    assert out["ctl00$C$DCONTCtl$HO_PHONEFld"] == "0905514024"


def test_dia_chi_khong_tich_khu_vuc_khi_giay_to_khong_ghi():
    out = _map({"TruSo_DiaChi": {"tinh": "Đà Nẵng"}}, "dia-chi")
    assert not [k for k in out if "ZONECtl" in k], "Không có căn cứ thì không được tích ô khu vực"


# --------------------------------------------------------------------------- vốn
def test_von_map_bang_nguon_von_va_tai_san_theo_dung_chi_so_dong():
    out = _map(
        {
            "Von_DieuLe": "2.000.000.000",
            "Von_NguonVon": [{"loai": "tu_nhan", "tyLe": "100", "soTien": "2.000.000.000"}],
            "Von_TaiSanGopVon": [{"loai": "dong_vn", "tyLe": "100", "giaTri": "2.000.000.000"}],
        },
        "thong-tin-ve-von",
    )
    base = "ctl00$C$UC_DW_CAPITALEditCtl"
    assert out[f"{base}$CPT_CHARTER_AMOUNTFld"] == "2000000000"
    # "Vốn tư nhân" là dòng THỨ HAI của bảng nguồn vốn -> ctl03.
    assert out[f"{base}$CtlSourceList$ctl03$RATIO_PERCENTFld"] == "100"
    assert out[f"{base}$CtlSourceList$ctl03$AMOUNTFld"] == "2000000000"
    # "Đồng Việt Nam" là dòng ĐẦU của bảng tài sản góp vốn -> ctl02.
    assert out[f"{base}$CtlList$ctl02$ASSET_AMOUNTFld"] == "2000000000"
    assert f"{base}$CtlSourceList$ctl02$AMOUNTFld" not in out, "Vốn ngân sách trống thì không điền"


# --------------------------------------------------------------------------- thành viên
_HAI_THANH_VIEN = {
    "ThanhVien_DanhSach": [
        {
            "hoTen": "Lê Tự Sang",
            "gioiTinh": "Nam",
            "ngaySinh": "22/04/1995",
            "soGiayToPhapLy": "049090503154",
            "quocTich": "Việt Nam",
            "danToc": "Kinh",
            "diaChiLienLac": {"tinh": "TP Đà Nẵng", "xa": "Điện Bàn", "diaChi": "37/14 Nguyễn Văn Trỗi"},
            "vonGop": "1.000.000.000",
            "tyLeSoHuu": "50",
            "soNgayGopVon": "90",
        },
        {
            "hoTen": "Trần Thị Hoài Thương",
            "gioiTinh": "Nữ",
            "ngaySinh": "30/04/1997",
            "soGiayToPhapLy": "049197013201",
            "quocTich": "Việt Nam",
            "danToc": "Kinh",
            "diaChiLienLac": {"tinh": "TP Đà Nẵng", "xa": "Điện Bàn", "diaChi": "37/14 Nguyễn Văn Trỗi"},
            "vonGop": "1.000.000.000",
            "tyLeSoHuu": "50",
            "soNgayGopVon": "90",
        },
    ],
}


def test_thanh_vien_dien_nguoi_dau_tien_dung_control():
    out = _map(_HAI_THANH_VIEN, "thong-tin-thanh-vien")
    person = "ctl00$C$MEM_PCtl$PERSCtl"
    assert out[f"{person}$FULL_NAMEFld"] == "LÊ TỰ SANG"
    assert out[f"{person}$GENDER_IDFld"] == "M"
    assert out[f"{person}$DATE_OF_BIRTHFld"] == "22/04/1995"
    assert out[f"{person}$PERS_DOC_NOFld"] == "049090503154"
    assert out[f"{person}$NATIONALITY_IDFld"] == "Việt Nam"
    assert out[f"{person}$ETHNIC_IDFld"] == "Kinh"
    assert out[f"{person}$ADDRCCtl$WARD_IDFld"] == "Điện Bàn"
    assert out["ctl00$C$MEM_PCtl$CPT_CONTR_AMOUNTFld"] == "1000000000"
    assert out["ctl00$C$MEM_PCtl$CPT_OWNERSHP_PERCENTFld"] == "50"


def test_thanh_vien_giu_du_ca_hai_nguoi_cho_extension_lap():
    """Trang chỉ nhập được 1 thành viên/lần -> mỗi người phải có sẵn BỘ FIELD riêng ở __members."""
    out = _map(_HAI_THANH_VIEN, "thong-tin-thanh-vien")
    members = out["__members"]
    assert [m["fullName"] for m in members] == ["LÊ TỰ SANG", "TRẦN THỊ HOÀI THƯƠNG"]
    assert members[1]["docNo"] == "049197013201"
    # Extension chỉ việc đổ nguyên bộ field này vào form — không tự dựng tên control.
    second = {f["name"]: f["value"] for f in members[1]["fields"]}
    assert second["ctl00$C$MEM_PCtl$PERSCtl$FULL_NAMEFld"] == "TRẦN THỊ HOÀI THƯƠNG"
    assert second["ctl00$C$MEM_PCtl$PERSCtl$GENDER_IDFld"] == "F"
    assert second["ctl00$C$MEM_PCtl$CPT_OWNERSHP_PERCENTFld"] == "50"
    assert second["ctl00$C$MEM_PCtl$PERSCtl$ADDRCCtl$WARD_IDFld"] == "Điện Bàn"
    assert all(f["value"] not in (None, "", {}, []) for f in members[1]["fields"])


def test_thanh_vien_thoi_han_gop_von_chon_dung_nhanh_radio():
    out = _map(_HAI_THANH_VIEN, "thong-tin-thanh-vien")
    assert out["ctl00$C$MEM_PCtl$CPT_CONTR_TIME_TYPEFld"] == "Thời hạn"
    assert out["ctl00$C$MEM_PCtl$DURATIONFld"] == "90"
    assert "ctl00$C$MEM_PCtl$CPT_CONTR_TIMEFld" not in out

    ngay_cu_the = {
        "ThanhVien_DanhSach": [
            {"hoTen": "A", "soGiayToPhapLy": "001", "ngayGopVonCuThe": "01/12/2025"},
        ],
    }
    out2 = _map(ngay_cu_the, "thong-tin-thanh-vien")
    assert out2["ctl00$C$MEM_PCtl$CPT_CONTR_TIME_TYPEFld"] == "Ngày cụ thể"
    assert out2["ctl00$C$MEM_PCtl$CPT_CONTR_TIMEFld"] == "01/12/2025"
    assert "ctl00$C$MEM_PCtl$DURATIONFld" not in out2


def test_thanh_vien_khong_dung_radio_dia_chi_va_tu_dong_tinh_von():
    """Hai radio này cổng đã để sẵn mặc định — ghi đè là đổi hành vi tự tính của form."""
    out = _map(_HAI_THANH_VIEN, "thong-tin-thanh-vien")
    assert "ctl00$C$MEM_PCtl$PERSCtl$SET_AUTO_ADRESSFld" not in out
    assert "ctl00$C$MEM_PCtl$rblSetAutoCalAmount" not in out


# --------------------------------------------------------------------------- người đại diện PL
def test_nguoi_dai_dien_phap_luat():
    out = _fields(
        {
            "NguoiDaiDien_HoTen": "Trần Thị Hoài Thương",
            "NguoiDaiDien_GioiTinh": "Nữ",
            "NguoiDaiDien_NgaySinh": "30/04/1997",
            "NguoiDaiDien_SoDinhDanh": "049197013201",
            "NguoiDaiDien_DiaChi": {"tinh": "TP Đà Nẵng", "xa": "Điện Bàn", "diaChi": "37/14 Nguyễn Văn Trỗi"},
            "NguoiDaiDien_DienThoai": "0905514024",
            "NguoiDaiDien_QuyenHan": "Giám đốc là người đại diện theo pháp luật của công ty.",
        },
        "nguoi-dai-dien-phap-luat",
    )
    person = "ctl00$C$REPCtl$PERSCtl"
    assert out[f"{person}$FULL_NAMEFld"]["value"] == "TRẦN THỊ HOÀI THƯƠNG"
    assert out[f"{person}$GENDER_IDFld"]["value"] == "F"
    assert out[f"{person}$DATE_OF_BIRTHFld"]["value"] == "30/04/1997"
    assert out[f"{person}$PERS_DOC_NOFld"]["value"] == "049197013201"
    assert out[f"{person}$ADDRCCtl$CITY_IDFld"]["value"] == "Đà Nẵng"
    assert out[f"{person}$PHONEFld"]["value"] == "0905514024"
    # Ô Quyền hạn: bảng đặc tả ghi id "POWERSId", alias là lối đặt tên chuẩn của cổng.
    powers = out["ctl00$C$REPCtl$POWERSId"]
    assert powers["value"].startswith("Giám đốc")
    assert powers["aliases"] == ["ctl00$C$REPCtl$POWERSFld"]


# --------------------------------------------------------------------------- thuế
def test_thue_khong_ke_khai_dia_chi_rieng_thi_chon_giong_tru_so():
    out = _map(
        {"TruSo_DiaChi": {"tinh": "Đà Nẵng", "xa": "Điện Bàn", "diaChi": "37/14 Nguyễn Văn Trỗi"}},
        "thong-tin-ve-thue",
    )
    base = "ctl00$C$UC_DW_TAXEditCtl"
    assert out[f"{base}$REP_RECV_ADDR_TYPEFld"] == "Giống địa chỉ trụ sở chính"
    assert f"{base}$ADDRCtl$CITY_IDFld" not in out, "Chọn giống trụ sở thì cổng ẩn khối địa chỉ"


def test_thue_ke_khai_dia_chi_khac_thi_dien_khoi_dia_chi():
    out = _map(
        {
            "TruSo_DiaChi": {"tinh": "Đà Nẵng", "xa": "Điện Bàn", "diaChi": "37/14 Nguyễn Văn Trỗi"},
            "Thue_DiaChiNhanThongBao": {"tinh": "Đà Nẵng", "xa": "Thanh Khê", "diaChi": "12 Lê Duẩn"},
        },
        "thong-tin-ve-thue",
    )
    base = "ctl00$C$UC_DW_TAXEditCtl"
    assert out[f"{base}$REP_RECV_ADDR_TYPEFld"] == "Địa chỉ khác"
    assert out[f"{base}$ADDRCtl$WARD_IDFld"] == "Thanh Khê"


def test_thue_nam_tai_chinh_va_phuong_phap_gtgt():
    out = _map(
        {
            "Thue_NamTaiChinh": {"ngayBatDau": 1, "thangBatDau": 1, "ngayKetThuc": 31, "thangKetThuc": 12},
            "Thue_PhuongPhapGTGT": "Khấu trừ",
            "Thue_SoLaoDong": "05",
            "Thue_HinhThucHachToan": "Hạch toán độc lập",
        },
        "thong-tin-ve-thue",
    )
    base = "ctl00$C$UC_DW_TAXEditCtl"
    assert out[f"{base}$FIN_YEAR_START_DAYFld"] == "1"
    assert out[f"{base}$FIN_YEAR_END_MONTHFld"] == "12"
    assert out[f"{base}$TAX_CAL_METHOD_IDRbBox"] == "DED"
    # Giữ nguyên chữ số như giấy ghi ("05") — ô là input text, cổng không kén số 0 đứng đầu.
    assert out[f"{base}$TOTAL_OF_LABORSFld"] == "05"
    assert out[f"{base}$TAX_ACCOUNTING_IDFld"] == "Hạch toán độc lập"


def test_thue_khong_tich_checkbox_khi_khong_co_can_cu():
    out = _map({"Thue_SoLaoDong": "5"}, "thong-tin-ve-thue")
    assert not [k for k in out if "CONSOLIDATED" in k or "INDZONE" in k or "IS_BOT" in k]


# --------------------------------------------------------------------------- người nộp hồ sơ
def test_nguoi_nop_uy_quyen_va_danh_sach_cccd():
    out = _map(
        {
            "NguoiNop_VaiTro": "Người được ủy quyền",
            "NguoiNop_HoTen": "Lê Thị Hiền Chi",
            "NguoiNop_GioiTinh": "Nữ",
            "NguoiNop_SoDinhDanh": "052176015320",
            "NguoiNop_DiaChi": {"tinh": "TP Đà Nẵng", "xa": "Phường Thanh Khê", "diaChi": "Tổ 30"},
            "Cccd_DanhSach": [
                {"hoTen": "Lê Thị Hiền Chi", "soDinhDanh": "052176015320", "gioiTinh": "Nữ"},
                {"hoTen": "Lê Tự Sang", "soDinhDanh": "049090503154", "gioiTinh": "Nam"},
            ],
        },
        "nguoi-nop-ho-so",
    )
    assert out["ctl00$C$PERS_SUBGroup"] == "IS_AUTHORIZED_BUTTON"
    assert out["ctl00$C$PERSCtl$FULL_NAMEFld"] == "LÊ THỊ HIỀN CHI"
    assert out["ctl00$C$PERSCtl$GENDER_IDFld"] == "F"
    assert out["ctl00$C$PERSCtl$ADDRCCtl$WARD_IDFld"] == "Thanh Khê"
    assert [c["docNo"] for c in out["__identityCandidates"]] == ["052176015320", "049090503154"]


def test_nguoi_nop_khong_ro_vai_tro_thi_giu_mac_dinh_cua_cong():
    out = _map({"NguoiNop_HoTen": "A"}, "nguoi-nop-ho-so")
    assert out["ctl00$C$PERS_SUBGroup"] == "IS_REPRESENTATIVE_BUTTON"


def test_nguoi_nop_gui_kem_nhan_than_nguoi_dai_dien_de_doi_chieu_tai_khoan():
    """Engine chốt vai trò bằng cách đối chiếu TÀI KHOẢN với người đại diện theo pháp luật —
    giống thủ tục hộ kinh doanh đối chiếu với chủ hộ. Mốc này phải có KỂ CẢ khi hồ sơ không kèm
    ảnh CCCD, vì nó đọc từ Giấy đề nghị/Điều lệ."""
    out = _map(
        {
            "NguoiDaiDien_HoTen": "Trần Thị Hoài Thương",
            "NguoiDaiDien_SoDinhDanh": "049197013201",
            "NguoiNop_HoTen": "Lê Thị Hiền Chi",
        },
        "nguoi-nop-ho-so",
    )
    assert out["__legalRep"] == {"fullName": "Trần Thị Hoài Thương", "docNo": "049197013201"}
    assert "__identityCandidates" not in out, "Không có CCCD trong hồ sơ thì không phát danh sách rỗng"


def test_nguoi_nop_khong_doc_duoc_nguoi_dai_dien_thi_khong_phat_moc_doi_chieu():
    out = _map({"NguoiNop_HoTen": "A"}, "nguoi-nop-ho-so")
    assert "__legalRep" not in out, "Không có căn cứ thì phải để engine giữ mặc định của cổng"


# --------------------------------------------------------------------------- toàn bộ trang
def test_enrich_all_phu_kin_dung_bo_trang_da_khai():
    pages = mapper.enrich_all(_facts({**_HAI_THANH_VIEN, "Von_DieuLe": "2000000000"}))
    assert set(pages) == {p["key"] for p in PAGES}
    # Không khai trang "Người đại diện của tổ chức" (chỉ dùng khi thành viên là tổ chức).
    assert "nguoi-dai-dien-to-chuc" not in pages
    # Không có trang cổ phần của công ty cổ phần.
    assert "thong-tin-ve-co-phan" not in pages
    assert pages["thong-tin-thanh-vien"], "Có thành viên thì trang thành viên không được rỗng"


def test_khong_tra_field_rong():
    """Field rỗng lọt xuống extension sẽ XÓA dữ liệu cổng đã điền sẵn."""
    for page in (p["key"] for p in PAGES):
        for field in mapper.enrich(_facts({}), page=page):
            assert field["value"] not in (None, "", {}, []), f"{page}: {field['name']}"
