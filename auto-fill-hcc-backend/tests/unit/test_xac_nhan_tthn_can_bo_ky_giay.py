"""Giấy XNTTHN ĐÃ CẤP mở đầu bằng "Xét đề nghị của ông/bà: <cán bộ tư pháp hộ tịch>".

Tên đó là CÁN BỘ của UBND đề nghị cấp giấy, không phải người yêu cầu. Agent hay bắt nhầm nó thành
ToKhaiYeuCau_HoTen; mapper phải tự loại, nếu không mục I ra tên cán bộ ghép với số định danh của
người được cấp — sai kiểu trông vẫn hợp lệ nên không ai soát ra.
"""

from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


# Hồ sơ thật req của ông Nguyễn Hoài Nam: quyết định ly hôn + giấy XNTTHN cũ + căn cước. KHÔNG có
# tờ khai, nên ToKhaiYeuCau_* bên dưới hoàn toàn do agent bắt nhầm từ giấy đã cấp.
_HO_SO = [
    {"name": "Cccd_HoTen", "value": "NGUYỄN HOÀI NAM"},
    {"name": "Cccd_SoDinhDanh", "value": "001066023420"},
    {"name": "Cccd_NgaySinh", "value": "30/07/1966"},
    {"name": "Cccd_NgayCap", "value": "16/07/2026"},
    {"name": "Cccd_NoiCap", "value": "Bộ Công an"},
    {"name": "ToKhaiYeuCau_HoTen", "value": "Trần Thị Hoa"},
    {"name": "ToKhaiYeuCau_QuanHe", "value": "công chức tư pháp hộ tịch"},
    {"name": "ToKhaiYeuCau_NoiCuTru",
     "value": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Thạch Thang", "diaChi": ""}},
    {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
    {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    {"name": "ToKhai_NoiCuTru",
     "value": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Thạch Thang",
               "diaChi": "K57/10 Nguyễn Chí Thanh"}},
    {"name": "DivorceDecision_Number", "value": "01/2019/QĐST-HNGD"},
    {"name": "DivorceDecision_Date", "value": "03/01/2019"},
    {"name": "DivorceDecision_Agency", "value": "Tòa án nhân dân huyện Hòa Vang, thành phố Đà Nẵng"},
]
_VNEID = {"formContext": {
    "applicantFullname": "NGUYỄN HOÀI NAM",
    "applicantIdentityNumber": "001066023420",
}}


def test_can_bo_ky_giay_khong_duoc_thanh_nguoi_yeu_cau():
    result = _by_name(enrich(list(_HO_SO), _VNEID))

    assert result["HoVaTenC"]["value"] == "NGUYỄN HOÀI NAM", "Mục I phải là người đi xin giấy"
    assert result["SoDinhDanhC"]["value"] == "001066023420"
    # Tên một người ghép số định danh người khác là ca hỏng nguy hiểm nhất — chặn tường minh.
    assert result["HoVaTenC"]["value"] != "Trần Thị Hoa"


def test_can_bo_ky_giay_khong_lam_lech_o_quan_he():
    """Chức danh cán bộ không phải quan hệ nhân thân → không được tick "Khác: Công chức"."""
    result = _by_name(enrich(list(_HO_SO), _VNEID))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "1", "Tự đi xin cho mình → Bản thân"
    assert "quanhekhac" not in result, 'Không được điền chữ chức danh vào ô cạnh "Khác"'


def test_quan_he_nhan_than_that_van_duoc_giu():
    """Chỉ chặn CHỨC DANH; quan hệ thật trên tờ khai vẫn phải đi tiếp như cũ."""
    fields = [f for f in _HO_SO if f["name"] != "ToKhaiYeuCau_QuanHe"]
    fields.append({"name": "ToKhaiYeuCau_QuanHe", "value": "là con đẻ"})
    fields.append({"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001099001234"})
    result = _by_name(enrich(fields, _VNEID))

    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
    assert result["quanhekhac"]["value"] == "Con đẻ"
    assert result["SoDinhDanhC"]["value"] == "001099001234", "Người yêu cầu có số riêng thì dùng số đó"


def test_khong_muon_cccd_cua_nguoi_khac_cho_muc_i():
    """Người yêu cầu khai tên riêng, không có số: thẻ trong hồ sơ là của NGƯỜI KHÁC → không mượn."""
    fields = [f for f in _HO_SO if f["name"] != "ToKhaiYeuCau_QuanHe"]
    fields.append({"name": "ToKhaiYeuCau_QuanHe", "value": "là chị ruột"})
    result = _by_name(enrich(fields, _VNEID))

    assert result["HoVaTenC"]["value"] == "Trần Thị Hoa"
    assert "SoDinhDanhC" not in result, "Không được đắp số định danh của người được cấp sang mục I"
    assert "NgaySinhC" not in result, "Ngày sinh trên thẻ cũng là của người khác"


# Lần chạy sau khi siết prompt: agent BỎ ToKhaiYeuCau_QuanHe nhưng VẪN giữ tên cán bộ ở
# ToKhaiYeuCau_HoTen. Chốt chặn không được phụ thuộc field quan hệ.
_HO_SO_KHONG_CO_QUAN_HE = [f for f in _HO_SO if f["name"] != "ToKhaiYeuCau_QuanHe"]


def test_ten_tro_troi_khong_du_de_lam_nguoi_yeu_cau():
    """Tên không kèm giấy tờ lẫn quan hệ = tên bắt nhầm ở tài liệu khác, không phải khối tờ khai."""
    result = _by_name(enrich(list(_HO_SO_KHONG_CO_QUAN_HE), _VNEID))

    assert result["HoVaTenC"]["value"] == "NGUYỄN HOÀI NAM"
    assert result["SoDinhDanhC"]["value"] == "001066023420"


def test_muc_i_phai_day_du_chu_khong_chi_moi_cai_ten():
    """Ca hỏng cũ: mục I chỉ có tên, còn số/ngày sinh/địa chỉ vẫn là của tài khoản VNeID."""
    result = _by_name(enrich(list(_HO_SO_KHONG_CO_QUAN_HE), _VNEID))

    for name in ("NgaySinhC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "nycNoiCuTru_TrongNuoc"):
        assert name in result, f"Mục I thiếu {name} — cổng sẽ giữ nguyên dữ liệu người đăng nhập"
    assert result["NgaySinhC"]["value"] == "30/07/1966"
    area = result["nycNoiCuTru_TrongNuoc"]["value"]
    assert area["diaChi"] == "K57/10 Nguyễn Chí Thanh"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "1"


def test_to_khai_that_chi_co_ten_va_quan_he_van_duoc_dung():
    """Tờ khai thật mà OCR rơi mất số giấy tờ: dòng QUAN HỆ là bằng chứng đủ, không được chặn oan."""
    fields = list(_HO_SO_KHONG_CO_QUAN_HE)
    fields.append({"name": "ToKhaiYeuCau_QuanHe", "value": "là con đẻ"})
    result = _by_name(enrich(fields, _VNEID))

    assert result["HoVaTenC"]["value"] == "Trần Thị Hoa"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
