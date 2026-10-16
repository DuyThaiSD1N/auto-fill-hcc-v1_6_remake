"""[Lào Cai] 1.013947 — xác nhận tiếp tục sử dụng đất nông nghiệp: đính kèm 3 dòng + nguồn địa chỉ phụ."""

from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.attach import planner
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.process import mapper, schema
from app.procedures import registry

_KEY = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-lao-cai"
_CHU_HO_SO = "001099000011"

_FACTS = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Lê Văn An"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "Don_NguoiSuDungDat", "value": [{"HoTen": "Lê Văn An", "SoDinhDanh": _CHU_HO_SO}]},
    {"name": "Don_DienThoai", "value": "0987000111"},
    {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Đông"}},
]
_DON_24 = [
    {"name": "DonBienDong_HoTen", "value": "Ông Lê Văn An"},
    {"name": "DonBienDong_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Tây"}},
    {"name": "DonBienDong_DienThoai", "value": "0912 000 222"},
]
_GCN_DIA_CHI = {"name": "Gcn_DiaChiNguoiSuDung",
                "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Nam"}}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


# ---------------------------------------------------------------- registry / detect


def test_registry_noi_du_process_va_attach():
    assert registry._PIPELINE[_KEY].__module__.endswith("xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.process")
    assert registry._ATTACH_PIPELINE[_KEY].__module__.endswith(
        "xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.attach"
    )
    proc = registry._BY_KEY[_KEY]
    assert proc["hasAttachmentStep"] is True
    detect = proc["detect"]
    # Cùng tên với 1.115677 trên cùng cổng → chỉ tách được bằng mã + textPriority.
    assert "1.013947" in detect["textIncludes"]
    assert detect["textPriority"] is True
    assert detect["urlScope"] == ["laocai.gov.vn"]
    assert proc["label"] != registry._BY_KEY["xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep"]["label"]


def test_schema_dung_lai_115677_va_them_nguon_phu():
    for name in ("ChuHoSo_DiaChiDon", "Don_DienThoai", "Gcn_DiaChiNguoiSuDung", "DonBienDong_DiaChi",
                 "DonBienDong_DienThoai", "DonBienDong_HoTen"):
        assert name in schema.ALLOWED
    assert schema.COMPACT_COMP_BY_NAME["DonBienDong_DiaChi"] == "x-select-area"
    assert schema.COMPACT_COMP_BY_NAME["Gcn_DiaChiNguoiSuDung"] == "x-select-area"
    assert not any(name.startswith(("CongDan_", "ChuHoSo_ten")) for name in schema.ALLOWED)


# ---------------------------------------------------------------- mapper


def test_don_khong_ghi_dia_chi_lay_theo_don_bien_dong_mau_24():
    fields, _ = mapper.enrich(_FACTS + _DON_24 + [_GCN_DIA_CHI], _ctx("LÊ VĂN AN", _CHU_HO_SO))
    values = _values(fields)

    assert values["ChuHoSo_tenChuHoSo"] == "LÊ VĂN AN"
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Thôn Tây"
    assert values["CongDan_diaChi"] == "Thôn Tây"
    # Đơn đã ghi số → không bị Mẫu 24 đè.
    assert values["ChuHoSo_diDongLienLacCHS"] == "0987000111"
    # Mục 3.7 (vị trí thửa đất) không bao giờ thành nơi cư trú.
    assert "Thôn Đông" not in values.values()


def test_khong_co_mau_24_thi_lay_dia_chi_muc_i_gcn():
    fields, _ = mapper.enrich(_FACTS + [_GCN_DIA_CHI], _ctx("LÊ VĂN AN", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Nam"


def test_don_ghi_dia_chi_thi_giu_nguon_don():
    facts = _FACTS + _DON_24 + [
        {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Bắc"}},
    ]
    fields, _ = mapper.enrich(facts, _ctx("LÊ VĂN AN", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Bắc"


def test_don_khong_ghi_so_dien_thoai_lay_theo_mau_24():
    facts = [f for f in _FACTS if f["name"] != "Don_DienThoai"] + _DON_24
    fields, _ = mapper.enrich(facts, _ctx("LÊ VĂN AN", _CHU_HO_SO))
    values = _values(fields)
    assert values["ChuHoSo_diDongLienLacCHS"] == "0912000222"
    assert values["CongDan_diDong"] == "0912000222"


def test_mau_24_cua_nguoi_khac_thi_bo_qua():
    don_24_khac = [
        {"name": "DonBienDong_HoTen", "value": "Trần Thị Bình"},
        {"name": "DonBienDong_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Tây"}},
        {"name": "DonBienDong_DienThoai", "value": "0912000222"},
    ]
    facts = [f for f in _FACTS if f["name"] != "Don_DienThoai"] + don_24_khac
    fields, warnings = mapper.enrich(facts, _ctx("LÊ VĂN AN", _CHU_HO_SO))
    values = _values(fields)
    assert "ChuHoSo_diaChiChuHoSo" not in values
    assert "ChuHoSo_diDongLienLacCHS" not in values
    assert any("địa chỉ chủ hồ sơ" in w for w in warnings)


# ---------------------------------------------------------------- attach planner


def _files(*names):
    return [{"name": name, "type": "image/jpeg", "dataUrl": ""} for name in names]


def test_dinh_kem_don_dong_1_gcn_nhieu_anh_dong_2_bo_trong_dong_b21():
    files = _files("don.jpg", "gcn-bia.jpg", "gcn-trong.jpg", "don-bien-dong.jpg")
    attachments, warnings, _ = planner.build_plan_items(
        files, {0: "don_de_nghi", 1: "gcn", 2: "gcn", 3: "don_bien_dong"}
    )
    fixed = [a for a in attachments if a["target"] == "fixed-slot"]
    assert {(a["fileIndex"], a["slotIndex"]) for a in fixed} == {(0, 1), (1, 2), (2, 2)}
    assert all(a["tickRow"] for a in fixed)
    # Hai ảnh Giấy chứng nhận chung một slotKey để FE gom một lần bơm tệp.
    assert len({a["slotKey"] for a in fixed if a["slotIndex"] == 2}) == 1
    assert not any(a.get("slotIndex") == 0 for a in attachments)

    other = [a for a in attachments if a["target"] == "new"]
    assert [a["fileIndex"] for a in other] == [3]
    assert "Mẫu số 24" in other[0]["documentName"]
    assert len(attachments) == len(files)
    assert any("KHÔNG thuộc thành phần hồ sơ" in w for w in warnings)
    assert not any("Chưa có tệp nào" in w for w in warnings)


def test_thieu_gcn_thi_nhac_va_loai_la_xuong_giay_to_khac():
    attachments, warnings, _ = planner.build_plan_items(_files("don.pdf", "la.jpg"), {0: "don_de_nghi"})
    assert attachments[1]["target"] == "new"
    assert any("Giấy chứng nhận đã cấp" in w and "Chưa có tệp nào" in w for w in warnings)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_doc_type_la_quy_ve_khac():
    assert planner._normalize_doc_type("Don-De-Nghi") == "don_de_nghi"
    assert planner._normalize_doc_type("so_ho_khau") == "khac"
