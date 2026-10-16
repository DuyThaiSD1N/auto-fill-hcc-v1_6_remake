"""[Lào Cai] 1.013831 — đăng ký biến động chuyển nhượng: đính kèm 15 dòng + nguồn ngày sinh/địa chỉ/di động."""

from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.attach import planner
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.process import mapper, schema
from app.procedures import registry

_KEY = "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-dvcqg-lao-cai"
_CHU_HO_SO = "001099000011"
_DUOC_UY_QUYEN = "001088000022"

_FACTS = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Lê Văn An"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1990"},
    {"name": "ChuHoSo_NgayCap", "value": "01/02/2026"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_DiaChiHopDong", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Hợp Đồng"}},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Đơn"}},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Trần Văn Bình", "soDinhDanh": _DUOC_UY_QUYEN, "ngaySinh": "1988", "gioiTinh": "Nam",
        "ngayCapCccd": "05/03/2026", "noiCapCccd": "Bộ Công an",
    }},
]
_TO_KHAI = [
    {"name": "ToKhaiThue_HoTen", "value": "Lê Văn Ân"},  # chữ viết tay đọc lệch dấu
    {"name": "ToKhaiThue_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ToKhaiThue_NgaySinh", "value": "12/06/1990"},
    {"name": "ToKhaiThue_DienThoai", "value": "0912 000 222"},
    {"name": "ToKhaiThue_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Tờ Khai"}},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


# ---------------------------------------------------------------- registry / detect


def test_registry_noi_du_process_va_attach():
    assert registry._PIPELINE[_KEY].__module__.endswith(
        "dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.process"
    )
    assert registry._ATTACH_PIPELINE[_KEY].__module__.endswith(
        "dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.attach"
    )
    proc = registry._BY_KEY[_KEY]
    assert proc["hasAttachmentStep"] is True
    detect = proc["detect"]
    # Cùng cụm tên với 1.115668 trên cùng cổng → chỉ tách được bằng mã + textPriority.
    assert "1.013831" in detect["textIncludes"]
    assert detect["textPriority"] is True
    assert detect["urlScope"] == ["laocai.gov.vn"]
    assert proc["label"] != registry._BY_KEY["dang-ky-bien-dong-dat-dai-lao-cai"]["label"]


def test_schema_dung_lai_115668_va_them_nguon_to_khai():
    for name in ("ChuHoSo_DiaChiHopDong", "NguoiDuocUyQuyen", "ToKhaiThue_NgaySinh", "ToKhaiThue_DiaChi",
                 "ToKhaiThue_DienThoai", "ToKhaiThue_SoDinhDanh"):
        assert name in schema.ALLOWED
    assert schema.COMPACT_COMP_BY_NAME["ToKhaiThue_DiaChi"] == "x-select-area"
    assert not any(name.startswith(("CongDan_", "ChuHoSo_ten")) for name in schema.ALLOWED)
    # Không ghi đè ô "Về việc" cổng điền sẵn.
    assert "HoSoOnline_veViec" not in schema.UI_COMP_BY_NAME


# ---------------------------------------------------------------- mapper


def test_ngay_sinh_va_di_dong_chu_ho_so_lay_tu_to_khai_khi_hop_dong_chi_ghi_nam():
    fields, _ = mapper.enrich(_FACTS + _TO_KHAI, _ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN))
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "LÊ VĂN AN"  # không theo chữ viết tay của tờ khai
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "12/06/1990"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0912000222"
    # Địa chỉ: Hợp đồng đứng trước Đơn và Tờ khai.
    assert values["ChuHoSo_diaChiChuHoSo"] == "Thôn Hợp Đồng"
    # Người nộp = bên được ủy quyền (khớp tài khoản): bù ngày/nơi cấp từ giấy ủy quyền, không đụng ô readonly.
    assert values["CongDan_ngayCapCmnd"] == "05/03/2026"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_ngaySinhCongDan" not in values  # giấy ủy quyền chỉ ghi năm sinh


def test_don_ghi_so_dien_thoai_thi_khong_bi_to_khai_de():
    facts = _FACTS + _TO_KHAI + [{"name": "Don_DienThoai", "value": "0987000111"}]
    fields, _ = mapper.enrich(facts, _ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN))
    assert _values(fields)["ChuHoSo_diDongLienLacCHS"] == "0987000111"


def test_cccd_chu_ho_so_dung_dau_nguon_dia_chi():
    the = {"name": "DanhSachCccd", "value": [{
        "HoTen": "Lê Văn An", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "12/06/1990",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Căn Cước"},
    }]}
    fields, _ = mapper.enrich(_FACTS + [the], _ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Căn Cước"


def test_khong_hop_dong_khong_don_thi_lay_dia_chi_to_khai():
    facts = [f for f in _FACTS if f["name"] not in ("ChuHoSo_DiaChiHopDong", "ChuHoSo_DiaChiDon")] + _TO_KHAI
    fields, _ = mapper.enrich(facts, _ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Tờ Khai"


def test_to_khai_cua_nguoi_khac_thi_bo_qua():
    to_khai_khac = [
        {"name": "ToKhaiThue_HoTen", "value": "Phạm Thị Cúc"},
        {"name": "ToKhaiThue_SoDinhDanh", "value": "001170000033"},
        {"name": "ToKhaiThue_NgaySinh", "value": "01/01/1970"},
        {"name": "ToKhaiThue_DienThoai", "value": "0912000222"},
    ]
    fields, _ = mapper.enrich(_FACTS + to_khai_khac, _ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN))
    values = _values(fields)
    assert "ChuHoSo_ngaySinhChuHoSo" not in values
    assert "ChuHoSo_diDongLienLacCHS" not in values


def test_nam_sinh_lech_to_khai_thi_khong_lay_ngay():
    to_khai = [f for f in _TO_KHAI if f["name"] != "ToKhaiThue_NgaySinh"]
    to_khai.append({"name": "ToKhaiThue_NgaySinh", "value": "12/06/1991"})
    fields, _ = mapper.enrich(_FACTS + to_khai, _ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN))
    assert "ChuHoSo_ngaySinhChuHoSo" not in _values(fields)


def test_theo_to_khai_nguoi_nop_la_ben_duoc_uy_quyen():
    options = {**_ctx("TRẦN VĂN BÌNH", _DUOC_UY_QUYEN), "submitterMode": "owner_as_submitter"}
    fields, _ = mapper.enrich(_FACTS + _TO_KHAI, options)
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "TRẦN VĂN BÌNH"
    assert values["CongDan_soCmnd"] == _DUOC_UY_QUYEN


# ---------------------------------------------------------------- attach planner


def _files(*names):
    return [{"name": name, "type": "application/pdf", "dataUrl": ""} for name in names]


def test_dinh_kem_ho_so_hai_thua_theo_anh_xa():
    files = _files("tncn.pdf", "don1.pdf", "don2.pdf", "gcn1.pdf", "gcn2.pdf", "hdcn.pdf", "lptb1.pdf",
                   "lptb2.pdf", "uq.pdf")
    types = {0: "to_khai_tncn", 1: "don_bien_dong", 2: "don_bien_dong", 3: "gcn", 4: "gcn", 5: "hop_dong",
             6: "to_khai_lptb", 7: "to_khai_lptb", 8: "uy_quyen"}
    attachments, warnings, _ = planner.build_plan_items(files, types)

    fixed = [a for a in attachments if a["target"] == "fixed-slot"]
    assert {(a["fileIndex"], a["slotIndex"]) for a in fixed} == {
        (0, 1), (1, 5), (2, 5), (3, 6), (4, 6), (5, 8), (6, 14), (7, 14),
    }
    assert all(a["tickRow"] for a in fixed)
    # Hai Đơn chung một slotKey để FE gom một lần bơm tệp; Số bản = số tệp của dòng.
    assert len({a["slotKey"] for a in fixed if a["slotIndex"] == 5}) == 1
    assert {a["soBan"] for a in fixed if a["slotIndex"] in (5, 6, 14)} == {2}
    assert next(a for a in fixed if a["slotIndex"] == 1)["soBan"] == 1
    # Giấy ủy quyền KHÔNG vào dòng 10 "Văn bản về việc đại diện" mà xuống Giấy tờ khác tên "Ủy quyền".
    assert not any(a.get("slotIndex") == 9 for a in attachments)
    other = [a for a in attachments if a["target"] == "new"]
    assert [(a["fileIndex"], a["documentName"]) for a in other] == [(8, "Ủy quyền")]
    # 2 GCN mà chỉ 1 tờ khai TNCN → nhắc bổ sung.
    assert any("Tờ khai thuế thu nhập cá nhân" in w and "2 Giấy chứng nhận" in w for w in warnings)
    assert not any("Chưa có tệp nào" in w for w in warnings)


def test_tep_trung_noi_dung_khong_dinh_lai():
    files = [
        {"name": "don.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QUJD"},
        {"name": "don (1).pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QUJD"},
        {"name": "gcn.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,REVG"},
    ]
    attachments, warnings, classified = planner.build_plan_items(
        files, {0: "don_bien_dong", 1: "don_bien_dong", 2: "gcn"}
    )
    assert [a["fileIndex"] for a in attachments] == [0, 2]
    assert next(a for a in attachments if a["fileIndex"] == 0)["soBan"] == 1
    assert any("don (1).pdf" in w and "trùng" in w for w in warnings)
    assert classified[1]["duplicateOf"] == "don.pdf"


def test_thieu_don_gcn_thi_nhac_va_loai_la_xuong_giay_to_khac():
    attachments, warnings, _ = planner.build_plan_items(_files("hdcn.pdf", "la.jpg"), {0: "hop_dong"})
    assert attachments[1]["target"] == "new"
    assert any("Đơn đăng ký biến động" in w and "Giấy chứng nhận" in w and "Chưa có tệp nào" in w
               for w in warnings)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_doc_type_la_quy_ve_khac():
    assert planner._normalize_doc_type("To-Khai-LPTB") == "to_khai_lptb"
    assert planner._normalize_doc_type("so_ho_khau") == "khac"
    assert len(planner._ROWS) == 15
