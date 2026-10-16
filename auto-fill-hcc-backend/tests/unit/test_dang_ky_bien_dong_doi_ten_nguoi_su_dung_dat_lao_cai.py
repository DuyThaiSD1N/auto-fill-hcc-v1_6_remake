"""[Lào Cai] 1.013833 — đăng ký biến động đổi tên/thay đổi thông tin: đính kèm 7 dòng + nguồn bước 2."""

import json
from pathlib import Path

from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.attach import planner
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.process import mapper, schema
from app.procedures import registry

_KEY = "dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-lao-cai"
_CHU_HO_SO = "001069000011"
_VO = "001169000022"
_NGUOI_KHAC = "001090000033"
_NOI_CAP = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

_DON = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Lê Văn An"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1969"},  # Giấy chứng nhận chỉ ghi năm sinh
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Đơn"}},
    {"name": "ChuHoSo_DiaChiGcn", "value": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Giấy Chứng Nhận"}},
    {"name": "Don_DienThoaiNguoiKhac", "value": "0912 000 222"},
]
_CAM_KET = {"name": "NguoiTrongGiayTo", "value": [
    {"HoTen": "Lê Văn An", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "12/06/1969", "GioiTinh": "Nam",
     "NgayCap": "22/04/2021", "NoiCap": _NOI_CAP,
     "NoiCuTru": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Cam Kết"}},
    {"HoTen": "Phạm Thị Bích", "SoDinhDanh": _VO, "NgaySinh": "01/01/1970", "GioiTinh": "Nữ",
     "NgayCap": "08/05/2021", "NoiCap": _NOI_CAP},
]}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _names(fields):
    return [f["name"] for f in fields]


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


# ---------------------------------------------------------------- registry / detect


def test_registry_noi_du_process_va_attach_va_trung_key_ke_khai_links():
    assert registry._PIPELINE[_KEY].__module__.endswith("dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.process")
    assert registry._ATTACH_PIPELINE[_KEY].__module__.endswith(
        "dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.attach"
    )
    proc = registry._BY_KEY[_KEY]
    assert proc["hasAttachmentStep"] is True
    detect = proc["detect"]
    # Chỉ khớp mã: tên thủ tục trên cổng Lào Cai không trùng nguyên văn tên DVCQG.
    assert detect["textIncludes"] == ["1.013833"]
    assert detect["textPriority"] is True
    assert detect["urlScope"] == ["laocai.gov.vn"]

    # Tên pipeline bám key của ke_khai_links.json để dễ đối chiếu.
    links = json.loads(
        (Path(registry.__file__).parent / "data" / "ke_khai_links.json").read_text(encoding="utf-8")
    )
    assert f'"key": "{_KEY}", "code": "1.013833"' in json.dumps(links, ensure_ascii=False)


def test_schema_giu_ten_fact_cua_115668_va_them_nguon_gcn():
    for name in ("DanhSachCccd", "NguoiTrongGiayTo", "ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiGcn",
                 "Don_DienThoai", "Don_DienThoaiNguoiKhac"):
        assert name in schema.ALLOWED
    assert schema.COMPACT_COMP_BY_NAME["ChuHoSo_DiaChiGcn"] == "x-select-area"
    # Không có hợp đồng chuyển nhượng trong thủ tục này.
    assert "ChuHoSo_DiaChiHopDong" not in schema.ALLOWED
    assert not any(name.startswith(("CongDan_", "ChuHoSo_ten")) for name in schema.ALLOWED)
    assert "HoSoOnline_veViec" not in schema.UI_COMP_BY_NAME


# ---------------------------------------------------------------- mapper


def test_chu_ho_so_tu_nop_lay_van_ban_cam_ket_va_sdt_muc_1_2():
    fields, warnings = mapper.enrich(_DON + [_CAM_KET], _ctx("LÊ VĂN AN", _CHU_HO_SO))
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "LÊ VĂN AN"
    assert values["ChuHoSo_soCMNDChuHoSo"] == _CHU_HO_SO
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "12/06/1969"  # văn bản cam kết, không phải năm trên GCN
    assert values["ChuHoSo_gioiTinhChuHoSo"] == "Nam"
    assert values["ChuHoSo_ngayCapCMNDCHS"] == "22/04/2021"
    assert values["ChuHoSo_noiCapCMNDCHS"] == _NOI_CAP
    # Địa chỉ: Đơn đứng trước văn bản cam kết và Giấy chứng nhận.
    assert values["ChuHoSo_diaChiChuHoSo"] == "Thôn Đơn"
    # Đơn mục 1.1 trống điện thoại → tạm dùng số ở mục 1.2 và cảnh báo.
    assert values["ChuHoSo_diDongLienLacCHS"] == "0912000222"
    assert any("mục 1.2" in w for w in warnings)

    # Người nộp = chủ hồ sơ: bù nhân thân + Di động, không đụng hai ô readonly.
    assert values["CongDan_ngayCapCmnd"] == "22/04/2021"
    assert values["CongDan_ngaySinhCongDan"] == "12/06/1969"
    assert values["CongDan_diDong"] == "0912000222"
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    names = _names(fields)
    assert names.index("CongDan_diDong") < names.index("ChuHoSo_maDoiTuongNopHS")


def test_nop_thay_van_dien_di_dong_nguoi_nop_theo_don_va_canh_bao():
    # Di động người nộp là ô (*) cổng không đổ sẵn; file mapping lấy từ Đơn.
    fields, warnings = mapper.enrich(_DON + [_CAM_KET], _ctx("TRẦN VĂN BÌNH", _NGUOI_KHAC))
    values = _values(fields)
    assert values["CongDan_diDong"] == "0912000222"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0912000222"
    assert any("không phải chủ hồ sơ" in w for w in warnings)


def test_chu_ho_so_tu_nop_thi_khong_canh_bao_di_dong_nop_thay():
    facts = _DON + [_CAM_KET, {"name": "Don_DienThoai", "value": "0987000111"}]
    _, warnings = mapper.enrich(facts, _ctx("LÊ VĂN AN", _CHU_HO_SO))
    assert not any("không phải chủ hồ sơ" in w for w in warnings)


def test_vo_dang_nhap_nop_thi_nguoi_nop_la_vo_nhung_chu_ho_so_van_la_muc_1_1():
    fields, _ = mapper.enrich(_DON + [_CAM_KET], _ctx("PHẠM THỊ BÍCH", _VO))
    values = _values(fields)
    assert values["ChuHoSo_tenChuHoSo"] == "LÊ VĂN AN"
    assert values["CongDan_ngayCapCmnd"] == "08/05/2021"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"


def test_don_ghi_sdt_muc_1_1_thi_dung_so_do_khong_canh_bao():
    facts = _DON + [_CAM_KET, {"name": "Don_DienThoai", "value": "0987000111"}]
    fields, warnings = mapper.enrich(facts, _ctx("LÊ VĂN AN", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diDongLienLacCHS"] == "0987000111"
    assert not any("mục 1.2" in w for w in warnings)


def test_cccd_dung_dau_nguon_dia_chi():
    the = {"name": "DanhSachCccd", "value": [{
        "HoTen": "Lê Văn An", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "12/06/1969",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Gia Phú", "diaChi": "Thôn Căn Cước"},
    }]}
    fields, _ = mapper.enrich(_DON + [_CAM_KET, the], _ctx("LÊ VĂN AN", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Căn Cước"


def test_khong_don_thi_lay_van_ban_cam_ket_roi_moi_den_giay_chung_nhan():
    khong_don = [f for f in _DON if f["name"] != "ChuHoSo_DiaChiDon"]
    fields, _ = mapper.enrich(khong_don + [_CAM_KET], _ctx("LÊ VĂN AN", _CHU_HO_SO))
    assert _values(fields)["ChuHoSo_diaChiChuHoSo"] == "Thôn Cam Kết"

    fields, _ = mapper.enrich(khong_don, _ctx("LÊ VĂN AN", _CHU_HO_SO))
    values = _values(fields)
    assert values["ChuHoSo_diaChiChuHoSo"] == "Thôn Giấy Chứng Nhận"
    # Chỉ có năm sinh trên Giấy chứng nhận → không bịa ngày.
    assert "ChuHoSo_ngaySinhChuHoSo" not in values


def test_theo_to_khai_nguoi_nop_la_chu_ho_so():
    options = {**_ctx("TRẦN VĂN BÌNH", _NGUOI_KHAC), "submitterMode": "owner_as_submitter"}
    fields, _ = mapper.enrich(_DON + [_CAM_KET], options)
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "LÊ VĂN AN"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    assert values["CongDan_diDong"] == "0912000222"


# ---------------------------------------------------------------- attach planner


def _files(*names):
    return [{"name": name, "type": "application/pdf", "dataUrl": ""} for name in names]


def test_dinh_kem_theo_anh_xa_cam_ket_don_gcn():
    attachments, warnings, _ = planner.build_plan_items(
        _files("vb.pdf", "don.pdf", "gcn.pdf"), {0: "cam_ket_ho_gia_dinh", 1: "don_bien_dong", 2: "gcn"}
    )
    assert {(a["fileIndex"], a["slotIndex"]) for a in attachments} == {(0, 1), (1, 3), (2, 5)}
    assert all(a["target"] == "fixed-slot" and a["tickRow"] and a["soBan"] == 1 for a in attachments)
    # Dòng 7 "thay đổi quyền của người có quyền lợi liên quan" KHÔNG đính lại văn bản cam kết.
    assert not any(a["slotIndex"] == 6 for a in attachments)
    assert not any("Chưa có tệp nào" in w for w in warnings)
    assert any("BẢN GỐC" in w for w in warnings)


def test_uy_quyen_vao_dong_dai_dien_ket_hon_xuong_giay_to_khac():
    attachments, _, _ = planner.build_plan_items(
        _files("uq.pdf", "kh.pdf", "cccd.jpg"), {0: "uy_quyen", 1: "ket_hon", 2: "cccd"}
    )
    by_file = {a["fileIndex"]: a for a in attachments}
    assert by_file[0]["slotIndex"] == 2
    assert by_file[1]["target"] == "new" and by_file[1]["documentName"] == "Giấy chứng nhận kết hôn"
    assert by_file[2]["slotIndex"] == 0


def test_nhieu_anh_gcn_gom_mot_dong_va_tep_trung_khong_dinh_lai():
    files = [
        {"name": "gcn1.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,QUJD"},
        {"name": "gcn2.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,REVG"},
        {"name": "gcn1 (1).jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,QUJD"},
    ]
    attachments, warnings, classified = planner.build_plan_items(files, {0: "gcn", 1: "gcn", 2: "gcn"})
    assert [a["fileIndex"] for a in attachments] == [0, 1]
    assert len({a["slotKey"] for a in attachments}) == 1
    assert {a["soBan"] for a in attachments} == {2}
    assert classified[2]["duplicateOf"] == "gcn1.jpg"
    assert any("trùng" in w for w in warnings)


def test_thieu_don_gcn_thi_nhac_va_loai_la_xuong_giay_to_khac():
    attachments, warnings, _ = planner.build_plan_items(_files("vb.pdf", "la.jpg"), {0: "cam_ket_ho_gia_dinh"})
    assert attachments[1]["target"] == "new"
    assert any("Đơn đăng ký biến động" in w and "Giấy chứng nhận" in w and "Chưa có tệp nào" in w
               for w in warnings)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_doc_type_la_quy_ve_khac():
    assert planner._normalize_doc_type("Cam-Ket-Ho-Gia-Dinh") == "cam_ket_ho_gia_dinh"
    assert planner._normalize_doc_type("hop_dong") == "khac"
    assert len(planner._ROWS) == 7
