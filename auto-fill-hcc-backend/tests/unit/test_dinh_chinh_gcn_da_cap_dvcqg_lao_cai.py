"""[Lào Cai] 1.012790 — đính chính Giấy chứng nhận đã cấp: nguồn bước 2 + đính kèm 4 dòng."""

import json
from pathlib import Path

from app.pipelines.dinh_chinh_gcn_da_cap_dvcqg_lao_cai.attach import planner
from app.pipelines.dinh_chinh_gcn_da_cap_dvcqg_lao_cai.process import mapper, schema
from app.procedures import registry

_KEY = "dinh-chinh-gcn-da-cap-dvcqg-lao-cai"
_CHU_HO_SO = "001073000011"
_VO = "001176000022"
_NGUOI_KHAC = "001090000033"

_DON = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Văn Minh"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1973"},  # Giấy chứng nhận chỉ ghi năm sinh
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Mậu A", "diaChi": "Thôn Đơn"}},
    {"name": "ChuHoSo_DiaChiGcn", "value": {"tinh": "Lào Cai", "xa": "Mậu A", "diaChi": "Thôn Cũ"}},
    {"name": "Don_NoiDungBienDong", "value": "Đính chính diện tích đất ở từ 100m2 thành 98,5m2"},
    {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Mậu A", "diaChi": "Thôn Thửa"}},
    {"name": "ThuaDat_DienTich", "value": "98,5 m²"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Trần Văn Minh", "SoDinhDanh": _CHU_HO_SO, "GioiTinh": "Nam"},
        {"HoTen": "Lý Thị Lan", "SoDinhDanh": _VO, "GioiTinh": "Nữ"},
    ]},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def _without(*names):
    return [f for f in _DON if f["name"] not in names]


# ---------------------------------------------------------------- registry / detect


def test_registry_noi_du_process_va_attach_va_trung_key_ke_khai_links():
    assert registry._PIPELINE[_KEY].__module__.endswith("dinh_chinh_gcn_da_cap_dvcqg_lao_cai.process")
    assert registry._ATTACH_PIPELINE[_KEY].__module__.endswith("dinh_chinh_gcn_da_cap_dvcqg_lao_cai.attach")
    proc = registry._BY_KEY[_KEY]
    assert proc["hasAttachmentStep"] is True
    detect = proc["detect"]
    assert "1.012790" in detect["textIncludes"]
    assert detect["textPriority"] is True
    assert detect["urlScope"] == ["laocai.gov.vn"]

    links = json.loads(
        (Path(registry.__file__).parent / "data" / "ke_khai_links.json").read_text(encoding="utf-8")
    )
    assert f'"key": "{_KEY}", "code": "1.012790"' in json.dumps(links, ensure_ascii=False)


def test_khong_cuop_trang_115686():
    # Trang 1.115686 (đính chính GCN cấp lần đầu) không chứa mã 1.012790 và ngược lại.
    rule_115686 = registry._BY_KEY["dinh-chinh-gcn-da-cap-lao-cai"]["detect"]["textIncludes"]
    assert "1.012790" not in rule_115686
    assert "1.115686" not in registry._BY_KEY[_KEY]["detect"]["textIncludes"]


def test_schema_giu_ten_fact_cua_115668():
    for name in ("DanhSachCccd", "NguoiTrongGiayTo", "ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiGcn",
                 "ChuHoSo_DiaChiGcnChinhLy", "Don_DienThoai", "ThuaDat_DienTich"):
        assert name in schema.ALLOWED
    assert schema.COMPACT_COMP_BY_NAME["ChuHoSo_DiaChiGcnChinhLy"] == "x-select-area"
    assert not any(name.startswith(("CongDan_", "ChuHoSo_ten")) for name in schema.ALLOWED)


# ---------------------------------------------------------------- mapper


def test_chu_ho_so_la_nguoi_dung_ten_dau_va_goi_y_thong_tin_cung_cap_them():
    fields, warnings = mapper.enrich(_DON, _ctx("TRẦN VĂN MINH", _CHU_HO_SO))
    values = _values(fields)
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "TRẦN VĂN MINH"
    assert values["ChuHoSo_soCMNDChuHoSo"] == _CHU_HO_SO
    assert values["ChuHoSo_diaChiChuHoSo"] == "Thôn Đơn"  # Đơn đứng trước GCN mục I
    assert "ChuHoSo_ngaySinhChuHoSo" not in values  # chỉ có năm sinh → không bịa ngày
    assert "CongDan_tenCongDan" not in values and "CongDan_soCmnd" not in values
    # "Thông tin cung cấp thêm" không phát field, chỉ gợi ý.
    assert not any(n.startswith("HoSoOnline_") for n in values)
    goi_y = next(w for w in warnings if "Thông tin cung cấp thêm" in w)
    assert "Thôn Thửa" in goi_y and "98,5 m²" in goi_y and "Về việc" in goi_y


def test_dong_chinh_ly_gcn_dung_truoc_don_cccd_dung_dau():
    chinh_ly = {"name": "ChuHoSo_DiaChiGcnChinhLy",
                "value": {"tinh": "Lào Cai", "xa": "Mậu A", "diaChi": "Thôn Chỉnh Lý"}}
    fields, _ = mapper.enrich(_DON + [chinh_ly], _ctx("TRẦN VĂN MINH", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Chỉnh Lý"

    the = {"name": "DanhSachCccd", "value": [{
        "HoTen": "Trần Văn Minh", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "20/08/1973",
        "NgayCap": "15/03/2025", "NoiCuTru": {"tinh": "Lào Cai", "xa": "Mậu A", "diaChi": "Thôn Căn Cước"},
    }]}
    fields, _ = mapper.enrich(_DON + [chinh_ly, the], _ctx("TRẦN VĂN MINH", _CHU_HO_SO))
    values = _values(fields)
    assert values["ChuHoSo_diaChiChuHoSo"] == "Thôn Căn Cước"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "20/08/1973"


def test_khong_don_thi_lay_gcn_muc_i():
    fields, _ = mapper.enrich(_without("ChuHoSo_DiaChiDon"), _ctx("TRẦN VĂN MINH", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Cũ"


def test_nop_thay_dien_di_dong_theo_don_va_canh_bao():
    facts = _DON + [{"name": "Don_DienThoai", "value": "0987 000 111"}]
    fields, warnings = mapper.enrich(facts, _ctx("NGUYỄN VĂN BA", _NGUOI_KHAC))
    values = _values(fields)
    assert values["CongDan_diDong"] == "0987000111"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0987000111"
    assert any("không phải chủ hồ sơ" in w for w in warnings)


def test_sdt_chi_o_nguoi_thu_hai_thi_tam_dung_va_canh_bao():
    facts = _DON + [{"name": "Don_DienThoaiNguoiKhac", "value": "0912000222"}]
    fields, warnings = mapper.enrich(facts, _ctx("TRẦN VĂN MINH", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diDongLienLacCHS"] == "0912000222"
    assert any("mục 1.2" in w for w in warnings)


def test_theo_to_khai_nguoi_nop_la_chu_ho_so():
    options = {**_ctx("NGUYỄN VĂN BA", _NGUOI_KHAC), "submitterMode": "owner_as_submitter"}
    fields, _ = mapper.enrich(_DON, options)
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "TRẦN VĂN MINH"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO


# ---------------------------------------------------------------- attach planner


def _files(*names):
    return [{"name": name, "type": "application/pdf", "dataUrl": ""} for name in names]


def test_dinh_kem_theo_anh_xa_gcn_dong_1_don_dong_4():
    attachments, warnings, _ = planner.build_plan_items(_files("gcn.pdf", "don.pdf"), {0: "gcn", 1: "don_bien_dong"})
    assert {(a["fileIndex"], a["slotIndex"]) for a in attachments} == {(0, 0), (1, 3)}
    assert all(a["target"] == "fixed-slot" and a["tickRow"] and a["soBan"] == 1 for a in attachments)
    # Dòng 2 (chứng minh sai sót), dòng 3 (ủy quyền) không có tệp → không tích.
    assert not any(a["slotIndex"] in (1, 2) for a in attachments)
    assert not any("BẮT BUỘC" in w for w in warnings)
    assert any("BẢN GỐC" in w for w in warnings)


def test_chung_minh_sai_sot_uy_quyen_vao_dong_rieng_cccd_xuong_giay_to_khac():
    attachments, _, _ = planner.build_plan_items(
        _files("ks.pdf", "uq.pdf", "cccd.jpg", "la.pdf"),
        {0: "chung_minh_sai_sot", 1: "uy_quyen", 2: "cccd"},
    )
    by_file = {a["fileIndex"]: a for a in attachments}
    assert by_file[0]["slotIndex"] == 1
    assert by_file[1]["slotIndex"] == 2
    assert by_file[2]["target"] == "new" and by_file[2]["documentName"] == "Căn cước công dân"
    assert by_file[3]["target"] == "new"


def test_thieu_don_va_gcn_thi_nhac():
    _, warnings, _ = planner.build_plan_items(_files("ks.pdf"), {0: "chung_minh_sai_sot"})
    assert any("Đơn đề nghị đính chính" in w and "BẮT BUỘC" in w for w in warnings)
    assert any("Chưa có tệp Giấy chứng nhận" in w for w in warnings)


def test_tep_trung_khong_dinh_lai_va_doc_type_la():
    files = [
        {"name": "gcn1.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,QUJD"},
        {"name": "gcn1 (1).jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,QUJD"},
    ]
    attachments, warnings, classified = planner.build_plan_items(files, {0: "gcn", 1: "gcn"})
    assert [a["fileIndex"] for a in attachments] == [0]
    assert classified[1]["duplicateOf"] == "gcn1.jpg"
    assert any("trùng" in w for w in warnings)
    assert planner._normalize_doc_type("Chung-Minh-Sai-Sot") == "chung_minh_sai_sot"
    assert planner._normalize_doc_type("hop_dong") == "khac"
    assert len(planner._ROWS) == 4
