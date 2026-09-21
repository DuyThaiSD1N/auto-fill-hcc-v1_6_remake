"""Cơ quan đăng ký khai sinh trước đây phải quy về danh mục hiện hành.

Giấy khai sinh cũ ghi địa giới TRƯỚC sáp nhập 2025 (vd "xã Đông Lỗ, huyện Hiệp Hòa, tỉnh Bắc
Giang"). Ô tỉnh trên cổng chỉ còn "Bắc Ninh", nên trả thẳng tỉnh cũ là cả khối bỏ trắng.
"""
from app.pipelines.khai_sinh_dang_ky_lai.process.mapper import enrich


def _values(fields):
    return {field["name"]: field["value"] for field in fields}


def _enrich(**values):
    return _values(enrich([
        {"name": name, "comp": "x-input", "value": value}
        for name, value in values.items()
    ]))


def test_tinh_cu_duoc_doi_sang_tinh_sau_sap_nhap():
    values = _enrich(
        PreviousRegistration_AgencyProvince="Bắc Giang",
        PreviousRegistration_AgencyCommune="Ủy ban nhân dân xã Đông Lỗ",
    )

    assert values["coQuanDKTruocDay_filter"] == "Bắc Ninh"
    assert values["coQuanDKTruocDay"] == "Xã Hiệp Hòa"


def test_chi_co_tinh_cu_van_doi_duoc():
    values = _enrich(PreviousRegistration_AgencyProvince="Bắc Giang")

    assert values["coQuanDKTruocDay_filter"] == "Bắc Ninh"
    assert "coQuanDKTruocDay" not in values


def test_tinh_chua_sap_nhap_giu_nguyen():
    values = _enrich(
        PreviousRegistration_AgencyProvince="Lai Châu",
        PreviousRegistration_AgencyCommune="Phường Tân Phong",
    )

    assert values["coQuanDKTruocDay_filter"] == "Lai Châu"
    assert values["coQuanDKTruocDay"] == "Phường Tân Phong"


def test_xa_khong_khop_danh_muc_nao_thi_bo_trong_cho_can_bo_chon():
    """Tỉnh đã tổ chức lại thì tên xã cũ chắc chắn không có trong option của tỉnh mới.

    Giữ lại tên đọc được chỉ làm ô treo một giá trị không chọn được; bỏ trống để cán bộ chọn.
    """
    values = _enrich(
        PreviousRegistration_AgencyProvince="Bắc Giang",
        PreviousRegistration_AgencyCommune="Xã Không Có Thật",
    )

    assert values["coQuanDKTruocDay_filter"] == "Bắc Ninh"
    assert "coQuanDKTruocDay" not in values


def test_giay_cap_lai_mang_tinh_moi_kem_ten_xa_cu():
    """Giấy in lại sau sáp nhập ghi tỉnh MỚI nhưng dòng cơ quan còn tên xã CŨ.

    Bảng remap tra nhánh này bằng khóa CÒN DẤU, nên tên xã cũ phải được ghi đúng chính tả
    trong remap_bac_ninh.json ("Đông Lỗ", không phải "Đồng Lỗ") thì mới khớp.
    """
    values = _enrich(
        PreviousRegistration_AgencyProvince="Bắc Ninh",
        PreviousRegistration_AgencyCommune="Xã Đông Lỗ",
    )

    assert values["coQuanDKTruocDay_filter"] == "Bắc Ninh"
    assert values["coQuanDKTruocDay"] == "Xã Hiệp Hòa"


def test_ocr_doc_lech_mot_dau_van_do_ra_dung_xa():
    """Hồ sơ thật req_c0b234e28242: tờ khai viết tay "xã Đông Lỗ" bị OCR đọc ra "xã Đông lễ".

    Không bảng tra nào có "Đông Lễ" (không phải tên hành chính), nên trước đây ô Xã/Phường bỏ
    trắng. Trong phạm vi Bắc Giang chỉ có DUY NHẤT "Đông Lỗ" lệch một ký tự -> gỡ được chắc chắn.
    """
    fields = enrich([
        {"name": "PreviousRegistration_AgencyProvince", "comp": "x-input", "value": "Bắc Giang"},
        {"name": "PreviousRegistration_AgencyCommune", "comp": "x-input", "value": "UBND xã Đông lễ"},
    ])
    commune = next(f for f in fields if f["name"] == "coQuanDKTruocDay")

    assert commune["value"] == "Xã Hiệp Hòa"
    # Phỏng đoán chứ không phải chữ đọc được -> extension phải tô vàng cho cán bộ soát.
    assert commune["default"] is True


def test_ten_doc_dung_khong_bi_danh_dau_phong_doan():
    fields = enrich([
        {"name": "PreviousRegistration_AgencyProvince", "comp": "x-input", "value": "Bắc Giang"},
        {"name": "PreviousRegistration_AgencyCommune", "comp": "x-input", "value": "Xã Đông Lỗ"},
    ])
    commune = next(f for f in fields if f["name"] == "coQuanDKTruocDay")

    assert commune["value"] == "Xã Hiệp Hòa"
    assert "default" not in commune
