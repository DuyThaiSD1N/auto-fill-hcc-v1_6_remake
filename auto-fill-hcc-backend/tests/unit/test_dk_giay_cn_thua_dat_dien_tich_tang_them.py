"""[Lào Cai] 1.115694 — đăng ký, cấp GCN thửa đất có diện tích tăng thêm (bước 2 CongDan_*/ChuHoSo_*).

Khoá những điều dễ vỡ của mapping bước 2:
  * KHÔNG phát `CongDan_tenCongDan` / `CongDan_soCmnd` (readonly; sửa họ tên là cổng xoá trắng Di động
    + Số Căn cước);
  * hồ sơ nộp THAY theo ủy quyền: khối người nộp chỉ lấy dữ liệu của CHÍNH người nộp, tuyệt đối không
    mượn địa chỉ/điện thoại của chủ hồ sơ, và phải cảnh báo ô (*) còn trống;
  * chủ hồ sơ = bên NHẬN chuyển quyền, ưu tiên CCCD khi Đơn ghi lệch ngày sinh;
  * khối chủ hồ sơ luôn có đủ 3 ô địa chỉ (cổng không copy địa chỉ qua checkbox "Người nộp là chủ hồ sơ").
"""

from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process import mapper
from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import get_attach_pipeline, get_pipeline, public_list

_KEY = "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua"

# Hồ sơ mẫu: bà TRẦN THỊ MINH HUỆ (bên nhận chuyển nhượng) uỷ quyền cho ông TRƯƠNG ANH TÚ đi nộp.
_CCCD_CHU_HO_SO = {
    "HoTen": "TRẦN THỊ MINH HUỆ",
    "SoDinhDanh": "001169020213",
    "NgaySinh": "20/11/1969",
    "GioiTinh": "Nữ",
    "NgayCap": "13/03/2021",
    "NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "NoiCuTru": {
        "tinh": "Hà Nội",
        "xa": "Phường Hai Bà Trưng",
        "diaChi": "Số 12 Đoàn Trần Nghiệp",
    },
}
_CCCD_NGUOI_DUOC_UY_QUYEN = {
    "HoTen": "TRƯƠNG ANH TÚ",
    "SoDinhDanh": "027079013270",
    "NgaySinh": "20/10/1979",
    "GioiTinh": "Nam",
    "NgayCap": "19/08/2022",
    "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}
_NGUOI_DUOC_UY_QUYEN = {
    # LLM hay trả kèm xưng hô ("Ông Trương Anh Tú") — mapper phải bóc ra trước khi so khớp người.
    "hoTen": "Ông TRƯƠNG ANH TÚ",
    "ngaySinh": "20/10/1979",
    "gioiTinh": "Nam",
    "soDinhDanh": "027079013270",
    "ngayCapCccd": "19/08/2022",
    "noiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}
_HO_SO_UY_QUYEN = [
    {"name": "NguoiDuocUyQuyen", "value": _NGUOI_DUOC_UY_QUYEN},
    {"name": "DanhSachCccd", "value": [_CCCD_CHU_HO_SO]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Thị Minh Huệ"},
    {"name": "ChuHoSo_XungHo", "value": "Bà"},
    # Đơn đăng ký biến động ghi LỆCH ngày sinh so với CCCD — phải theo CCCD.
    {"name": "ChuHoSo_NgaySinh", "value": "13/07/1969"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001169020213"},
    {"name": "ChuHoSo_DanToc", "value": "Kinh"},
    {"name": "Don_DienThoai", "value": "0989082640"},
    {"name": "HopDong_Email", "value": "tranthiminhhue69@yahoo.com.vn"},
]
# Cổng đã điền sẵn khối người nộp từ tài khoản định danh của người ĐI NỘP.
_CTX_UY_QUYEN = {
    "formContext": {
        "applicantFullname": "TRƯƠNG ANH TÚ",
        "applicantIdentityNumber": "027079013270",
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
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    # Cụm phân biệt với bản Lâm Đồng 1.116356 (form Form.io khác hẳn) phải còn nguyên.
    assert (
        "nhận chuyển quyền sử dụng một phần thửa đất đã được cấp giấy chứng nhận"
        in entry["detect"]["textIncludes"]
    )


def test_khong_phat_hai_o_readonly_cua_khoi_nguoi_nop():
    """`CongDan_tenCongDan` + `CongDan_soCmnd` do tài khoản định danh điền; sửa họ tên là cổng xoá
    trắng Di động + Số Căn cước → không được khai, cũng không được phát."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    fields, _ = mapper.enrich(_HO_SO_UY_QUYEN, _CTX_UY_QUYEN)
    by_name = _names(fields)
    assert "CongDan_tenCongDan" not in by_name
    assert "CongDan_soCmnd" not in by_name


def test_nop_thay_lay_nhan_than_nguoi_duoc_uy_quyen_khong_muon_cua_chu_ho_so():
    fields, warnings = mapper.enrich(_HO_SO_UY_QUYEN, _CTX_UY_QUYEN)
    by_name = _names(fields)

    # Khối người nộp = ông Trương Anh Tú (bên được uỷ quyền), lấy từ chính Giấy uỷ quyền.
    assert by_name["CongDan_ngaySinhCongDan"] == "20/10/1979"
    assert by_name["CongDan_gioiTinhCongDan"] == "Nam"
    assert by_name["CongDan_ngayCapCmnd"] == "19/08/2022"
    assert by_name["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

    # Giấy uỷ quyền không ghi nơi cư trú/điện thoại của người được uỷ quyền → BỎ TRỐNG, không được
    # mượn địa chỉ và số điện thoại của bà Huệ (chủ hồ sơ).
    for name in ("CongDan_maTinhThanh", "CongDan_maPhuongXa", "CongDan_diaChi", "CongDan_diDong"):
        assert name not in by_name
    assert any("Thông tin người nộp" in w and "Di động" in w for w in warnings)


def test_chu_ho_so_uu_tien_cccd_khi_don_ghi_lech_va_du_ba_o_dia_chi():
    fields, warnings = mapper.enrich(_HO_SO_UY_QUYEN, _CTX_UY_QUYEN)
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert by_name["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ MINH HUỆ"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "001169020213"
    # Đơn ghi 13/07/1969, CCCD ghi 20/11/1969 → theo CCCD.
    assert by_name["ChuHoSo_ngaySinhChuHoSo"] == "20/11/1969"
    assert by_name["ChuHoSo_gioiTinhChuHoSo"] == "Nữ"
    assert by_name["ChuHoSo_danTocChuHoSo"] == "Kinh"
    assert by_name["ChuHoSo_ngayCapCMNDCHS"] == "13/03/2021"
    assert by_name["ChuHoSo_noiCapCMNDCHS"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

    # Checkbox "Người nộp là chủ hồ sơ" của cổng KHÔNG copy địa chỉ → mapper phải phát đủ cả 3 ô.
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Thành phố Hà Nội"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Hai Bà Trưng"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Số 12 Đoàn Trần Nghiệp"
    # Điện thoại lấy ở Đơn, email chỉ có trên hợp đồng mua bán.
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0989082640"
    assert by_name["ChuHoSo_emailChuHoSo"] == "tranthiminhhue69@yahoo.com.vn"
    assert not any("địa chỉ chủ hồ sơ" in w for w in warnings)


def test_doi_tuong_nop_ho_so_phat_truoc_cac_o_phu_thuoc():
    """"Đối tượng nộp hồ sơ" là driver: chọn CN/DN mới hiện nhóm ô tương ứng."""
    fields, _ = mapper.enrich(_HO_SO_UY_QUYEN, _CTX_UY_QUYEN)
    order = [f["name"] for f in fields]
    driver = order.index("ChuHoSo_maDoiTuongNopHS")
    assert driver < order.index("ChuHoSo_tenChuHoSo")
    assert driver < order.index("ChuHoSo_soCMNDChuHoSo")
    # Tỉnh phải đứng trước Phường/Xã: danh mục xã chỉ nạp sau khi chọn tỉnh.
    assert order.index("ChuHoSo_maTinhThanhCHS") < order.index("ChuHoSo_maPhuongXaCHS")

    # Cùng ràng buộc đó ở khối người nộp (hồ sơ tự nộp mới có đủ 2 ô để kiểm).
    ho_so = [f for f in _HO_SO_UY_QUYEN if f["name"] != "NguoiDuocUyQuyen"]
    tu_nop, _ = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "TRẦN THỊ MINH HUỆ",
                         "applicantIdentityNumber": "001169020213"}},
    )
    order_tu_nop = [f["name"] for f in tu_nop]
    assert order_tu_nop.index("CongDan_maTinhThanh") < order_tu_nop.index("CongDan_maPhuongXa")


def test_tu_nop_duoc_dung_dia_chi_va_lien_he_cua_chinh_minh():
    """Không có uỷ quyền, người đăng nhập chính là chủ hồ sơ → khối người nộp dùng lại nguồn của
    chủ hồ sơ (cùng một người), không phát cảnh báo thiếu ô."""
    ho_so = [f for f in _HO_SO_UY_QUYEN if f["name"] != "NguoiDuocUyQuyen"]
    fields, warnings = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "TRẦN THỊ MINH HUỆ",
                         "applicantIdentityNumber": "001169020213"}},
    )
    by_name = _names(fields)

    assert by_name["CongDan_maTinhThanh"] == "Thành phố Hà Nội"
    assert by_name["CongDan_maPhuongXa"] == "Phường Hai Bà Trưng"
    assert by_name["CongDan_diaChi"] == "Số 12 Đoàn Trần Nghiệp"
    assert by_name["CongDan_diDong"] == "0989082640"
    assert by_name["CongDan_ngaySinhCongDan"] == "20/11/1969"
    assert not any("Thông tin người nộp" in w for w in warnings)


def test_khong_co_form_context_thi_bo_trong_toan_bo_nhan_than_nguoi_nop():
    """Hồ sơ thật req_f5368d5b7ef6: tài khoản đăng nhập là ông Nguyễn Duy Thái, nhưng popup chưa gửi
    formContext nên mapper cũ rơi về người được ủy quyền (ông Trương Anh Tú) và điền nhầm ngày sinh
    20/10/1979 + ngày cấp 19/08/2022 của ông Tú vào khối người nộp. Thiếu mốc thì KHÔNG được đoán."""
    fields, warnings = mapper.enrich(_HO_SO_UY_QUYEN, {})
    by_name = _names(fields)

    for name in ("CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan", "CongDan_ngayCapCmnd",
                 "CongDan_noiCapCmnd", "CongDan_maTinhThanh", "CongDan_maPhuongXa",
                 "CongDan_diaChi", "CongDan_diDong", "CongDan_email"):
        assert name not in by_name, f"{name} bị điền khi chưa biết ai đang đi nộp"
    assert any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)
    # Khối chủ hồ sơ vẫn phải điền bình thường — nó không phụ thuộc tài khoản đăng nhập.
    assert by_name["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ MINH HUỆ"


def test_tai_khoan_khac_moi_nguoi_trong_ho_so_thi_khong_muon_nhan_than_cua_ai():
    """Đúng tình huống ảnh chụp: đăng nhập bằng tài khoản ông Nguyễn Duy Thái (001204018566) mà hồ sơ
    không có giấy tờ nào của ông ấy → 4 ô nhân thân phải TRỐNG, không lấy của ông Trương Anh Tú."""
    ho_so = _HO_SO_UY_QUYEN + [
        {"name": "DanhSachCccd", "value": [_CCCD_CHU_HO_SO, _CCCD_NGUOI_DUOC_UY_QUYEN]},
    ]
    fields, warnings = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "Nguyễn Duy Thái",
                         "applicantIdentityNumber": "001204018566"}},
    )
    by_name = _names(fields)

    assert "CongDan_ngaySinhCongDan" not in by_name
    assert "CongDan_gioiTinhCongDan" not in by_name
    assert "CongDan_ngayCapCmnd" not in by_name
    assert "CongDan_noiCapCmnd" not in by_name
    assert any("Nguyễn Duy Thái" in w for w in warnings)


def test_co_cccd_cua_dung_nguoi_dang_nhap_thi_moi_dien_khoi_nguoi_nop():
    """"Phải đưa CCCD của Nguyễn Duy Thái thì mới điền" — đưa vào thì phải điền đúng của ông ấy."""
    cccd_nguoi_nop = {
        "HoTen": "NGUYỄN DUY THÁI",
        "SoDinhDanh": "001204018566",
        "NgaySinh": "02/05/1985",
        "GioiTinh": "Nam",
        "NgayCap": "10/01/2023",
        "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "NoiCuTru": {"tinh": "Hà Nội", "xa": "Phường Từ Liêm", "diaChi": "TDP Số 30 Mỹ Đình"},
    }
    ho_so = [f for f in _HO_SO_UY_QUYEN if f["name"] != "DanhSachCccd"]
    ho_so.append({"name": "DanhSachCccd", "value": [_CCCD_CHU_HO_SO, cccd_nguoi_nop]})
    fields, _ = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "Nguyễn Duy Thái",
                         "applicantIdentityNumber": "001204018566"}},
    )
    by_name = _names(fields)

    assert by_name["CongDan_ngaySinhCongDan"] == "02/05/1985"
    assert by_name["CongDan_ngayCapCmnd"] == "10/01/2023"
    assert by_name["CongDan_maTinhThanh"] == "Thành phố Hà Nội"
    assert by_name["CongDan_maPhuongXa"] == "Phường Từ Liêm"
    assert by_name["CongDan_diaChi"] == "TDP Số 30 Mỹ Đình"
    # Không được nhiễm số điện thoại của chủ hồ sơ (bà Huệ) sang người nộp.
    assert "CongDan_diDong" not in by_name
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0989082640"


def test_khop_cccd_theo_ten_dang_nhap_khi_so_dinh_danh_lech():
    """Tên đăng nhập đã có sẵn trên form → chỉ cần CCCD upload trùng TÊN tài khoản là điền, kể cả khi
    số trên thẻ lệch số của tài khoản (OCR sai một chữ số, hoặc thẻ là CMND 9 số cũ)."""
    cccd_ocr_lech_so = {
        "HoTen": "NGUYỄN DUY THÁI",
        "SoDinhDanh": "001204018599",  # OCR lệch 2 số cuối so với tài khoản 001204018566
        "NgaySinh": "02/05/1985",
        "GioiTinh": "Nam",
        "NgayCap": "10/01/2023",
        "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "NoiCuTru": {"tinh": "Hà Nội", "xa": "Phường Từ Liêm", "diaChi": "TDP Số 30 Mỹ Đình"},
    }
    ho_so = [f for f in _HO_SO_UY_QUYEN if f["name"] != "DanhSachCccd"]
    ho_so.append({"name": "DanhSachCccd", "value": [_CCCD_CHU_HO_SO, cccd_ocr_lech_so]})
    fields, _ = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "Nguyễn Duy Thái",
                         "applicantIdentityNumber": "001204018566"}},
    )
    by_name = _names(fields)

    assert by_name["CongDan_ngaySinhCongDan"] == "02/05/1985"
    assert by_name["CongDan_gioiTinhCongDan"] == "Nam"
    assert by_name["CongDan_ngayCapCmnd"] == "10/01/2023"
    assert by_name["CongDan_maPhuongXa"] == "Phường Từ Liêm"


def test_hai_nguoi_trung_ten_thi_khong_doan():
    """`_match_by_name` bỏ qua khi có từ hai người trùng tên — thà trống còn hơn chọn nhầm thẻ."""
    trung_ten = [
        {**_CCCD_CHU_HO_SO, "HoTen": "NGUYỄN DUY THÁI", "SoDinhDanh": "001204018501"},
        {**_CCCD_CHU_HO_SO, "HoTen": "Nguyễn Duy Thái", "SoDinhDanh": "001204018502"},
    ]
    ho_so = [f for f in _HO_SO_UY_QUYEN if f["name"] != "DanhSachCccd"]
    ho_so.append({"name": "DanhSachCccd", "value": trung_ten})
    fields, _ = mapper.enrich(
        ho_so,
        {"formContext": {"applicantFullname": "Nguyễn Duy Thái",
                         "applicantIdentityNumber": "001204018566"}},
    )
    assert "CongDan_ngaySinhCongDan" not in _names(fields)


def test_khong_dung_giay_uy_quyen_khi_tai_khoan_dang_nhap_la_nguoi_khac():
    """Tài khoản đăng nhập KHÁC bên được uỷ quyền → không được gán nhân thân của bên được uỷ quyền
    cho khối người nộp."""
    fields, _ = mapper.enrich(
        _HO_SO_UY_QUYEN,
        {"formContext": {"applicantFullname": "NGUYỄN VĂN B",
                         "applicantIdentityNumber": "001090001234"}},
    )
    by_name = _names(fields)
    assert "CongDan_ngaySinhCongDan" not in by_name
    assert "CongDan_ngayCapCmnd" not in by_name
    # Chủ hồ sơ vẫn phải được điền đầy đủ.
    assert by_name["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ MINH HUỆ"


def test_chu_ho_so_to_chuc_phat_ten_va_mst_o_ca_hai_khoi():
    fields, warnings = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
            {"name": "ChuHoSo_TenToChuc", "value": "Công ty cổ phần bất động sản HANO-VID"},
            {"name": "ChuHoSo_MaSoThue", "value": "0105025361"},
            {"name": "ChuHoSo_DiaChiDkdn",
             "value": {"tinh": "Hà Nội", "xa": "Phường Hà Đông", "diaChi": "Số 430 Cầu Am"}},
            {"name": "Dkdn_DienThoai", "value": "0243 5723535"},
        ],
        {},
    )
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert by_name["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY CỔ PHẦN BẤT ĐỘNG SẢN HANO-VID"
    assert by_name["ChuHoSo_maSoThueChuHoSo"] == "0105025361"
    # Người nộp đứng ra cho tổ chức → ô tên cơ quan/MST khối người nộp cũng của tổ chức đó.
    assert by_name["CongDan_tenCoQuanToChuc"] == "CÔNG TY CỔ PHẦN BẤT ĐỘNG SẢN HANO-VID"
    assert by_name["CongDan_maSoThueNguoiNop"] == "0105025361"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Thành phố Hà Nội"
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "02435723535"
    # Tổ chức thì không được điền ô của nhóm cá nhân.
    assert "ChuHoSo_tenChuHoSo" not in by_name
    assert "ChuHoSo_soCMNDChuHoSo" not in by_name
    # Người nộp là một CÁ NHÂN đại diện cho tổ chức, hồ sơ không có giấy tờ của người đó →
    # nhắc cán bộ nhập tay 4 ô (*) thay vì mượn địa chỉ trụ sở của tổ chức.
    assert any("Thông tin người nộp" in w for w in warnings)
    assert not any("địa chỉ chủ hồ sơ" in w for w in warnings)


def test_thieu_chu_ho_so_thi_canh_bao_chu_khong_im_lang():
    fields, warnings = mapper.enrich([{"name": "Don_DienThoai", "value": "0989082640"}], {})
    assert fields == []
    assert any("Chưa xác định được chủ hồ sơ" in w for w in warnings)


def test_du_kien_nghiep_vu_khong_bi_phat_thanh_o_ui():
    """Thửa đất / GCN đã cấp / diện tích tăng thêm chỉ để lưu trace — bước 2 không có ô tương ứng."""
    for name in ("ThuaDat_So", "ThuaDat_ToBanDo", "DienTich_TangThem", "Gcn_SoPhatHanh",
                 "Gcn_SoVaoSo", "Gcn_NgayCap", "Gcn_DonViCap", "Don_NoiDungDeNghi"):
        assert name in ALLOWED
        assert name not in UI_COMP_BY_NAME

    fields, _ = mapper.enrich(
        _HO_SO_UY_QUYEN
        + [
            {"name": "ThuaDat_So", "value": "862"},
            {"name": "ThuaDat_ToBanDo", "value": "44"},
            {"name": "DienTich_TangThem", "value": "163,8 m2"},
            {"name": "Gcn_SoPhatHanh", "value": "AA 06583358"},
        ],
        _CTX_UY_QUYEN,
    )
    assert not {"ThuaDat_So", "ThuaDat_ToBanDo", "DienTich_TangThem", "Gcn_SoPhatHanh"} & {
        f["name"] for f in fields
    }


def test_moi_o_phat_ra_deu_ton_tai_tren_form():
    fields, _ = mapper.enrich(_HO_SO_UY_QUYEN, _CTX_UY_QUYEN)
    for field in fields:
        assert field["name"] in UI_COMP_BY_NAME
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]
