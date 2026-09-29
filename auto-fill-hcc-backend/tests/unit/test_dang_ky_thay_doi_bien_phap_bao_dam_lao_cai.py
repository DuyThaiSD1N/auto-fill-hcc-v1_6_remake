"""[Lào Cai] 1.011442.H38 — đăng ký thay đổi biện pháp bảo đảm: planner đính kèm + mapper chủ hồ sơ.

Dữ liệu giả; kết quả LLM phân loại được giả lập qua `llm_types`.
"""

from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_lao_cai.attach.planner import build_plan_items
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_lao_cai.process import mapper
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_lao_cai.process.schema import (
    ALLOWED,
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)


def _files(*names):
    return [{"name": n, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAAA"} for n in names]


def _by_file(attachments):
    out: dict[int, list[dict]] = {}
    for item in attachments:
        out.setdefault(item["fileIndex"], []).append(item)
    return out


# ---------------------------------------------------------------- planner


def test_ho_so_day_du_moi_tep_dung_mot_dong():
    files = _files("phieu.pdf", "gioi_thieu.pdf", "hop_dong.pdf", "gcn.pdf")
    llm = {
        0: {"docType": "phieu_02a"},
        1: {"docType": "van_ban_uy_quyen"},
        2: {"docType": "hop_dong_the_chap"},
        3: {"docType": "gcn", "gcnPages": 6},
    }
    attachments, warnings, classified = build_plan_items(files, llm)
    by_file = _by_file(attachments)

    assert set(by_file) == {0, 1, 2, 3}
    assert all(len(items) == 1 for items in by_file.values())
    assert by_file[0][0]["slotIndex"] == 3
    assert by_file[0][0]["componentName"] == "Đơn yêu cầu đăng ký thế chấp"
    assert "02a" in by_file[0][0]["documentName"]
    assert by_file[1][0]["slotIndex"] == 0
    assert by_file[2][0]["slotIndex"] == 1
    assert by_file[3][0]["slotIndex"] == 2
    assert by_file[3][0]["soBan"] == 6
    for item in attachments:
        assert item["target"] == "fixed-slot" and item["tickRow"] is True
        assert item["slotKey"].startswith("laocai_dktdbpbd_")
    assert not any("bắt buộc" in w for w in warnings)
    assert len(classified) == 4


def test_giay_to_ngoai_danh_muc_di_dong_giay_to_khac_co_ten():
    files = _files("a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf")
    llm = {
        0: {"docType": "phieu_02a"},
        1: {"docType": "van_ban_can_cu_thay_doi", "documentName": "Quyết định số 12/QĐ-NH đổi tên ngân hàng"},
        2: {"docType": "cccd", "documentName": "Căn cước công dân Nguyễn Văn A"},
        3: {"docType": "other", "documentName": ""},
        4: {"docType": "dkdn", "documentName": "Giấy chứng nhận đăng ký hoạt động chi nhánh"},
    }
    attachments, warnings, _ = build_plan_items(files, llm)
    by_file = _by_file(attachments)

    for index in (1, 2, 3, 4):
        item = by_file[index][0]
        assert item["target"] == "new"
        assert item["needsAddComponent"] is True and item["noChooserClick"] is True
        assert item["documentName"] and item["documentName"] == item["componentName"]
        assert len(item["documentName"]) <= 50
        assert "(" not in item["documentName"] and "." not in item["documentName"]
    # Số hiệu văn bản giữ lại, "/" đổi thành "-".
    assert by_file[1][0]["documentName"].startswith("Quyết định số 12-QĐ-NH")
    assert by_file[3][0]["documentName"] == "Giấy tờ kèm theo hồ sơ"
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_nhieu_anh_gcn_cung_mot_dong_so_ban_cong_don():
    files = _files("phieu.jpg", "gcn_1.jpg", "gcn_2.jpg")
    llm = {
        0: {"docType": "phieu_02a"},
        1: {"docType": "gcn", "gcnPages": 1},
        2: {"docType": "gcn", "gcnPages": 2},
    }
    attachments, _, _ = build_plan_items(files, llm)
    gcn = [a for a in attachments if a.get("detectedType") == "gcn"]

    assert [a["fileIndex"] for a in gcn] == [1, 2]
    assert {a["slotIndex"] for a in gcn} == {2}
    assert {a["soBan"] for a in gcn} == {3}


def test_khong_miss_tep_khi_llm_khong_tra_ket_qua():
    files = _files("x.pdf", "y.pdf")
    attachments, warnings, _ = build_plan_items(files, {})

    assert sorted(a["fileIndex"] for a in attachments) == [0, 1]
    assert all(a["target"] == "new" for a in attachments)
    assert len({a["documentName"] for a in attachments}) == 2  # khử trùng tên
    assert any("Phiếu yêu cầu đăng ký thay đổi" in w for w in warnings)


def test_tep_gop_dinh_lai_vao_dong_con_trong():
    files = _files("phieu_kem_gioi_thieu.pdf", "gcn.pdf")
    llm = {
        0: {"docType": "phieu_02a", "alsoTypes": ["van_ban_uy_quyen", "gcn"]},
        1: {"docType": "gcn"},
    }
    attachments, warnings, _ = build_plan_items(files, llm)
    slots_file0 = sorted(a["slotIndex"] for a in attachments if a["fileIndex"] == 0)

    # Dòng GCN đã có tệp riêng → không đính lại; dòng văn bản ủy quyền còn trống → đính lại tệp gộp.
    assert slots_file0 == [0, 3]
    assert any("chứa cả" in w for w in warnings)


def test_canh_bao_tep_qua_6mb():
    big = "A" * (7 * 1024 * 1024 * 4 // 3)
    files = [{"name": "to.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64," + big}]
    _, warnings, _ = build_plan_items(files, {0: {"docType": "phieu_02a"}})
    assert any("6 MB" in w for w in warnings)


# ---------------------------------------------------------------- mapper


_FACTS_NGAN_HANG = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "NGÂN HÀNG TMCP GIẢ ĐỊNH - CHI NHÁNH MẪU"},
    {"name": "ChuHoSo_MaSoThue", "value": "0100000000-001"},
    {"name": "ChuHoSo_HoTen", "value": "Giám Đốc Giả"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001080000123"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1 đường Mẫu"}},
    {"name": "ChuHoSo_DienThoai", "value": "0900.000.111"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_to_chuc_phat_value_dn_truoc_va_loc_o_an():
    fields, _ = mapper.enrich(_FACTS_NGAN_HANG, {"formContext": {"applicantIdentityNumber": "001199000001"}})
    names = [f["name"] for f in fields]
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"
    chs = [n for n in names if n.startswith("ChuHoSo_")]
    assert chs[0] == "ChuHoSo_maDoiTuongNopHS"
    assert not INDIVIDUAL_ONLY_FIELDS & set(names)
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "NGÂN HÀNG TMCP GIẢ ĐỊNH - CHI NHÁNH MẪU"
    assert values["ChuHoSo_maSoThueChuHoSo"] == "0100000000-001"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0900000111"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Số 1 đường Mẫu"
    # Ô tổ chức của khối người nộp = tổ chức chủ hồ sơ khi không có giấy giới thiệu.
    assert values["CongDan_tenCoQuanToChuc"] == "NGÂN HÀNG TMCP GIẢ ĐỊNH - CHI NHÁNH MẪU"


def test_ca_nhan_phat_cn_va_an_o_to_chuc():
    facts = [
        {"name": "ChuHoSo_LaToChuc", "value": False},
        {"name": "ChuHoSo_HoTen", "value": "Ông Nguyễn Văn Giả"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001080000123"},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY LẪN VÀO"},
        {"name": "DanhSachCccd", "value": [{"HoTen": "NGUYỄN VĂN GIẢ", "SoDinhDanh": "001080000123",
                                             "NgaySinh": "02/03/1980", "NgayCap": "04/05/2021"}]},
    ]
    fields, _ = mapper.enrich(facts, {})
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "Nguyễn Văn Giả"
    assert values["ChuHoSo_soCMNDChuHoSo"] == "001080000123"
    # Nhân thân bù từ CCCD của CHÍNH chủ hồ sơ (khớp số).
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "02/03/1980"
    assert values["ChuHoSo_ngayCapCMNDCHS"] == "04/05/2021"
    assert not ORG_ONLY_FIELDS & set(values)


def test_ghi_chu_tep_gop_va_cat_500_ky_tu():
    facts = _FACTS_NGAN_HANG + [
        {"name": "GhiChu_TepDinhChung", "value": "Tệp gcn.pdf gồm: (1) Giấy chứng nhận (tr.1–4); (2) Trang bổ sung số 01 (tr.5)"},
    ]
    fields, _ = mapper.enrich(facts, {})
    assert _values(fields)["HoSoOnline_ghiChu"].startswith("Tệp gcn.pdf gồm")

    long_facts = _FACTS_NGAN_HANG + [{"name": "GhiChu_TepDinhChung", "value": "Tệp a.pdf gồm " + "giấy tờ " * 120}]
    fields, _ = mapper.enrich(long_facts, {})
    assert len(_values(fields)["HoSoOnline_ghiChu"]) <= 500

    fields, _ = mapper.enrich(_FACTS_NGAN_HANG, {})
    assert "HoSoOnline_ghiChu" not in _values(fields)


def test_khong_phat_ve_viec_va_checkbox():
    assert "HoSoOnline_veViec" not in UI_COMP_BY_NAME
    assert "chkbox_nguoinoplachuhs" not in UI_COMP_BY_NAME
    fields, _ = mapper.enrich(_FACTS_NGAN_HANG + [{"name": "Don_NoiDungThayDoi", "value": "Bổ sung tài sản"}], {})
    names = {f["name"] for f in fields}
    assert "HoSoOnline_veViec" not in names
    assert "chkbox_nguoinoplachuhs" not in names
    assert all(name in UI_COMP_BY_NAME for name in names)


def test_schema_co_du_truong_nghiep_vu():
    for name in ("Don_TuCachNguoiYeuCau", "Don_NoiDungThayDoi", "Don_VanBanCanCu", "BenNhanBaoDam_TenMoi",
                 "BenNhanBaoDam_TenCu", "GhiChu_TepDinhChung", "NguoiDuocUyQuyen", "DanhSachCccd",
                 "NguoiTrongGiayTo"):
        assert name in ALLOWED
