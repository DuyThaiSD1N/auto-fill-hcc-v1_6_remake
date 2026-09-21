"""[Lào Cai] 1.115677 — xác nhận tiếp tục sử dụng đất nông nghiệp (bước 2 CongDan_*/ChuHoSo_*).

Hồ sơ mẫu của file mapping: thửa đất nông nghiệp của ông LÊ VĂN MINH (người sử dụng đất đứng tên ĐẦU ở
mục 1 Đơn Mẫu số 39) và vợ là bà NGUYỄN THỊ VỤ; chính bà Vụ ký "Người làm đơn" và đi nộp.

Khoá những điều dễ vỡ của mapping bước 2:
  * KHÔNG phát `CongDan_tenCongDan` / `CongDan_soCmnd` (readonly; sửa họ tên là cổng xoá trắng Di động
    + Số Căn cước);
  * chủ hồ sơ = người đứng tên ĐẦU mục 1, KHÔNG phải người ký "Người làm đơn";
  * vợ/chồng cùng đứng tên mục 1 đi nộp thì ĐƯỢC dùng địa chỉ liên hệ mục 2 (địa chỉ chung của hộ),
    còn người ngoài hộ thì KHÔNG;
  * Giấy chứng nhận in CMND 9 số cũ → vẫn phải chọn số căn cước 12 số;
  * khối chủ hồ sơ luôn có đủ 3 ô địa chỉ (cổng không copy địa chỉ qua checkbox "Người nộp là chủ hồ sơ").
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import mapper
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import get_attach_pipeline, get_pipeline, public_list

_KEY = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep"

_DIA_CHI_LIEN_HE = {
    "tinh": "Lào Cai",
    "xa": "Phường Văn Phú",
    "diaChi": "Tổ dân phố số 9",
}
_ONG_MINH = {
    "HoTen": "LÊ VĂN MINH",
    "SoDinhDanh": "015071006651",
    "GioiTinh": "Nam",
}
_BA_VU = {
    "HoTen": "NGUYỄN THỊ VỤ",
    "SoDinhDanh": "015172005832",
    "GioiTinh": "Nữ",
}
# Hồ sơ thật KHÔNG kèm ảnh CCCD (mapping sheet "CCCD mô phỏng") — chỉ có Đơn 39 + Giấy chứng nhận.
_HO_SO = [
    {"name": "Don_NguoiSuDungDat", "value": [_ONG_MINH, _BA_VU]},
    {"name": "Don_NguoiLamDon", "value": "Nguyễn Thị Vụ"},
    {"name": "NguoiTrongGiayTo", "value": [_ONG_MINH, _BA_VU]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Lê Văn Minh"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "015071006651"},
    {"name": "ChuHoSo_DiaChiDon", "value": _DIA_CHI_LIEN_HE},
    # Dữ kiện nghiệp vụ mục 3–4 của Đơn Mẫu số 39 (chỉ lưu trace).
    {"name": "ThuaDat_So", "value": "289; 435; 438; 285; 441; 370; 257; 55"},
    {"name": "ThuaDat_ToBanDo", "value": "10; 11 và 20"},
    {"name": "ThuaDat_ThoiHanSuDung", "value": "2013"},
    {"name": "Don_NoiDungDeNghi", "value": "đến ngày 15 tháng 11 năm 2063"},
    {"name": "Gcn_SoPhatHanh", "value": "E 007548"},
    {"name": "Gcn_SoVaoSo", "value": "000085"},
    {"name": "Gcn_NgayCap", "value": "15/11/1996"},
]
# Cổng đã điền sẵn khối người nộp từ tài khoản định danh của bà Vụ (người đi nộp).
_CTX_BA_VU = {
    "formContext": {
        "applicantFullname": "NGUYỄN THỊ VỤ",
        "applicantIdentityNumber": "015172005832",
    }
}


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def test_registry_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    # Bảng "Thành phần hồ sơ" bước 3 — xem test_..._attach.py.
    assert entry["hasAttachmentStep"] is True
    assert get_attach_pipeline(_KEY) is not None
    assert get_pipeline(_KEY) is not None
    # Mã QG 1.115677 dùng chung nhiều cổng iGate tỉnh → phải khoá host Lào Cai.
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert "xác nhận tiếp tục sử dụng đất nông nghiệp" in entry["detect"]["textIncludes"]


def test_khong_phat_hai_o_readonly_cua_khoi_nguoi_nop():
    """`CongDan_tenCongDan` + `CongDan_soCmnd` do tài khoản định danh điền; sửa họ tên là cổng xoá
    trắng Di động + Số Căn cước → không được khai, cũng không được phát."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    fields, _ = mapper.enrich(_HO_SO, _CTX_BA_VU)
    by_name = _names(fields)
    assert "CongDan_tenCongDan" not in by_name
    assert "CongDan_soCmnd" not in by_name


def test_chu_ho_so_la_nguoi_dung_ten_dau_khong_phai_nguoi_ky_don():
    """Bà Vụ ký "Người làm đơn" và đi nộp, nhưng chủ hồ sơ vẫn là ông Minh (mục 1, đứng tên đầu)."""
    fields, _ = mapper.enrich(_HO_SO, _CTX_BA_VU)
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert by_name["ChuHoSo_tenChuHoSo"] == "LÊ VĂN MINH"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "015071006651"
    # Xưng hô "Ông" ở mục 1 đủ để chốt giới tính khi hồ sơ không kèm CCCD.
    assert by_name["ChuHoSo_gioiTinhChuHoSo"] == "Nam"
    # Địa chỉ liên hệ mục 2 của Đơn — cổng KHÔNG copy địa chỉ qua checkbox "Người nộp là chủ hồ sơ".
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Văn Phú"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố số 9"


def test_vo_chong_cung_dung_ten_muc_1_duoc_dung_dia_chi_lien_he_cua_ho():
    """Mục 2 Đơn Mẫu số 39 là MỘT địa chỉ liên hệ dùng chung cho cả hộ → bà Vụ (đồng người sử dụng đất)
    đi nộp thì khối người nộp được dùng lại địa chỉ đó."""
    fields, _ = mapper.enrich(_HO_SO, _CTX_BA_VU)
    by_name = _names(fields)

    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert by_name["CongDan_maPhuongXa"] == "Phường Văn Phú"
    assert by_name["CongDan_diaChi"] == "Tổ dân phố số 9"


def test_nguoi_ngoai_ho_khong_duoc_muon_dia_chi_lien_he_cua_ho():
    """Người đăng nhập không có tên ở mục 1 → tuyệt đối không mượn địa chỉ/điện thoại của hộ."""
    ho_so = _HO_SO + [{"name": "Don_DienThoai", "value": "0989082640"}]
    fields, warnings = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "TRƯƠNG ANH TÚ",
                         "applicantIdentityNumber": "027079013270"}},
    )
    by_name = _names(fields)

    for name in ("CongDan_maTinhThanh", "CongDan_maPhuongXa", "CongDan_diaChi", "CongDan_diDong"):
        assert name not in by_name
    assert any("Thông tin người nộp" in w and "Di động" in w for w in warnings)
    # Khối chủ hồ sơ vẫn phải đầy đủ.
    assert by_name["ChuHoSo_tenChuHoSo"] == "LÊ VĂN MINH"
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0989082640"


def test_nguoi_duoc_uy_quyen_di_nop_lay_nhan_than_tu_giay_uy_quyen():
    uy_quyen = {
        "hoTen": "Ông TRƯƠNG ANH TÚ",
        "ngaySinh": "20/10/1979",
        "gioiTinh": "Nam",
        "soDinhDanh": "027079013270",
        "ngayCapCccd": "19/08/2022",
        "noiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    }
    fields, _ = mapper.enrich(
        _HO_SO + [{"name": "NguoiDuocUyQuyen", "value": uy_quyen}],
        {"formContext": {"applicantFullname": "TRƯƠNG ANH TÚ",
                         "applicantIdentityNumber": "027079013270"}},
    )
    by_name = _names(fields)

    assert by_name["CongDan_ngaySinhCongDan"] == "20/10/1979"
    assert by_name["CongDan_gioiTinhCongDan"] == "Nam"
    assert by_name["CongDan_ngayCapCmnd"] == "19/08/2022"
    # Giấy uỷ quyền không ghi nơi cư trú → KHÔNG được mượn địa chỉ của hộ ông Minh.
    assert "CongDan_maTinhThanh" not in by_name


def test_uu_tien_so_can_cuoc_12_so_khi_gcn_in_cmnd_9_so():
    """Giấy chứng nhận (mục "Những thay đổi sau khi cấp GCN") in CMND cũ 060691791 — CCCD phải thắng."""
    cccd = {**_ONG_MINH, "NgaySinh": "20/03/1971", "NgayCap": "10/05/2021",
            "NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
            "NoiCuTru": _DIA_CHI_LIEN_HE}
    ho_so = [f for f in _HO_SO if f["name"] != "ChuHoSo_SoDinhDanh"]
    ho_so += [
        {"name": "DanhSachCccd", "value": [cccd]},
        # LLM đọc nhầm số CMND 9 số từ trang "Những thay đổi" vào field của Đơn.
        {"name": "ChuHoSo_SoDinhDanh", "value": "060691791"},
    ]
    fields, _ = mapper.enrich(ho_so, _CTX_BA_VU)
    by_name = _names(fields)

    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "015071006651"
    assert by_name["ChuHoSo_ngaySinhChuHoSo"] == "20/03/1971"
    assert by_name["ChuHoSo_ngayCapCMNDCHS"] == "10/05/2021"
    assert by_name["ChuHoSo_noiCapCMNDCHS"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_hai_nguoi_trung_ten_thi_khong_doan_the_nao():
    """`_find_person` được phép lùi về khớp HỌ TÊN khi số lệch, nhưng có từ hai người trùng tên trở lên
    thì phải bỏ qua — thà trống còn hơn lấy nhầm thẻ."""
    trung_ten = [
        {"HoTen": "LÊ VĂN MINH", "SoDinhDanh": "015071006601", "NgaySinh": "20/03/1971"},
        {"HoTen": "Lê Văn Minh", "SoDinhDanh": "015071006602", "NgaySinh": "01/01/1980"},
    ]
    ho_so = [f for f in _HO_SO if f["name"] != "ChuHoSo_SoDinhDanh"]
    ho_so += [
        {"name": "DanhSachCccd", "value": trung_ten},
        {"name": "ChuHoSo_SoDinhDanh", "value": "015071006651"},
    ]
    fields, _ = mapper.enrich(ho_so, _CTX_BA_VU)
    by_name = _names(fields)

    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "015071006651"
    assert "ChuHoSo_ngaySinhChuHoSo" not in by_name


def test_khong_co_form_context_thi_bo_trong_toan_bo_nhan_than_nguoi_nop():
    """Thiếu mốc tài khoản thì không biết ai đi nộp (chồng? vợ? người được uỷ quyền?) — không đoán."""
    fields, warnings = mapper.enrich(_HO_SO, {})
    by_name = _names(fields)

    for name in ("CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan", "CongDan_maTinhThanh",
                 "CongDan_maPhuongXa", "CongDan_diaChi", "CongDan_diDong"):
        assert name not in by_name, f"{name} bị điền khi chưa biết ai đang đi nộp"
    assert any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)
    # Khối chủ hồ sơ vẫn phải điền bình thường — nó không phụ thuộc tài khoản đăng nhập.
    assert by_name["ChuHoSo_tenChuHoSo"] == "LÊ VĂN MINH"


def test_co_cccd_cua_dung_nguoi_dang_nhap_thi_uu_tien_noi_cu_tru_tren_the():
    cccd_ba_vu = {
        **_BA_VU,
        "NgaySinh": "15/07/1972",
        "NgayCap": "10/05/2021",
        "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Tổ 5"},
    }
    fields, _ = mapper.enrich(_HO_SO + [{"name": "DanhSachCccd", "value": [cccd_ba_vu]}], _CTX_BA_VU)
    by_name = _names(fields)

    assert by_name["CongDan_ngaySinhCongDan"] == "15/07/1972"
    assert by_name["CongDan_gioiTinhCongDan"] == "Nữ"
    assert by_name["CongDan_ngayCapCmnd"] == "10/05/2021"
    # Nơi cư trú in trên thẻ đứng trước địa chỉ liên hệ của Đơn.
    assert by_name["CongDan_maPhuongXa"] == "Phường Cam Đường"
    assert by_name["CongDan_diaChi"] == "Tổ 5"


def test_doi_tuong_nop_ho_so_phat_truoc_cac_o_phu_thuoc():
    """"Đối tượng nộp hồ sơ" là driver: chọn CN/DN mới hiện nhóm ô tương ứng."""
    fields, _ = mapper.enrich(_HO_SO, _CTX_BA_VU)
    order = [f["name"] for f in fields]
    driver = order.index("ChuHoSo_maDoiTuongNopHS")
    assert driver < order.index("ChuHoSo_tenChuHoSo")
    assert driver < order.index("ChuHoSo_soCMNDChuHoSo")
    # Tỉnh phải đứng trước Phường/Xã ở cả hai khối: danh mục xã chỉ nạp sau khi chọn tỉnh.
    assert order.index("ChuHoSo_maTinhThanhCHS") < order.index("ChuHoSo_maPhuongXaCHS")
    assert order.index("CongDan_maTinhThanh") < order.index("CongDan_maPhuongXa")


def test_khong_bia_dien_thoai_khi_don_bo_trong():
    """Hồ sơ mẫu không ghi số điện thoại ở mục 2 — ô (*) Di động phải trống và được cảnh báo."""
    fields, warnings = mapper.enrich(_HO_SO, _CTX_BA_VU)
    by_name = _names(fields)

    assert "CongDan_diDong" not in by_name
    assert "ChuHoSo_diDongLienLacCHS" not in by_name
    assert any("Di động" in w for w in warnings)


def test_chu_ho_so_to_chuc_phat_ten_va_mst_o_ca_hai_khoi():
    fields, warnings = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
            {"name": "ChuHoSo_TenToChuc", "value": "Hợp tác xã nông nghiệp Văn Phú"},
            {"name": "ChuHoSo_MaSoThue", "value": "5200123456"},
            {"name": "ChuHoSo_DiaChiToChuc",
             "value": {"tinh": "Lào Cai", "xa": "Phường Văn Phú", "diaChi": "Tổ dân phố số 1"}},
            {"name": "ToChuc_DienThoai", "value": "0214 3850123"},
        ],
        {},
    )
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert by_name["ChuHoSo_tenCoQuanToChucCHS"] == "HỢP TÁC XÃ NÔNG NGHIỆP VĂN PHÚ"
    assert by_name["ChuHoSo_maSoThueChuHoSo"] == "5200123456"
    # Người nộp đứng ra cho tổ chức → ô tên cơ quan/MST khối người nộp cũng của tổ chức đó.
    assert by_name["CongDan_tenCoQuanToChuc"] == "HỢP TÁC XÃ NÔNG NGHIỆP VĂN PHÚ"
    assert by_name["CongDan_maSoThueNguoiNop"] == "5200123456"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "02143850123"
    # Tổ chức thì không được điền ô của nhóm cá nhân.
    assert "ChuHoSo_tenChuHoSo" not in by_name
    assert "ChuHoSo_soCMNDChuHoSo" not in by_name
    assert not any("địa chỉ chủ hồ sơ" in w for w in warnings)


def test_thieu_chu_ho_so_thi_canh_bao_chu_khong_im_lang():
    fields, warnings = mapper.enrich([{"name": "Don_DienThoai", "value": "0989082640"}], {})
    assert fields == []
    assert any("Chưa xác định được chủ hồ sơ" in w for w in warnings)


def test_du_kien_nghiep_vu_khong_bi_phat_thanh_o_ui():
    """Thửa đất / thời hạn / GCN đã cấp chỉ để lưu trace — bước 2 không có ô tương ứng, khối 'Biểu mẫu
    giấy tờ' ở bước 3 thì chưa render nên chưa có DOM."""
    nghiep_vu = ("ThuaDat_So", "ThuaDat_ToBanDo", "ThuaDat_DienTich", "ThuaDat_MucDichSuDung",
                 "ThuaDat_ThoiHanSuDung", "ThuaDat_TaiSanGanLien", "ThuaDat_DiaChi",
                 "Gcn_SoPhatHanh", "Gcn_SoVaoSo", "Gcn_NgayCap", "Gcn_DonViCap",
                 "Don_NoiDungDeNghi", "Don_KinhGui", "Don_NgayLap", "Don_NguoiLamDon")
    for name in nghiep_vu:
        assert name in ALLOWED
        assert name not in UI_COMP_BY_NAME

    fields, _ = mapper.enrich(_HO_SO, _CTX_BA_VU)
    assert not set(nghiep_vu) & {f["name"] for f in fields}


def test_dia_chi_thua_dat_khong_bao_gio_thanh_dia_chi_nguoi():
    """Mục 3.7 "Địa điểm thửa đất" là vị trí đất — không được rơi vào ô địa chỉ của người."""
    ho_so = [f for f in _HO_SO if f["name"] != "ChuHoSo_DiaChiDon"]
    ho_so.append({"name": "ThuaDat_DiaChi",
                  "value": {"tinh": "Lào Cai", "xa": "Phường Văn Phú", "diaChi": "Thôn 1"}})
    fields, warnings = mapper.enrich(ho_so, _CTX_BA_VU)
    by_name = _names(fields)

    assert "ChuHoSo_diaChiChuHoSo" not in by_name
    assert "CongDan_diaChi" not in by_name
    assert any("địa chỉ chủ hồ sơ" in w for w in warnings)


def test_moi_o_phat_ra_deu_ton_tai_tren_form():
    fields, _ = mapper.enrich(_HO_SO, _CTX_BA_VU)
    for field in fields:
        assert field["name"] in UI_COMP_BY_NAME
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]
