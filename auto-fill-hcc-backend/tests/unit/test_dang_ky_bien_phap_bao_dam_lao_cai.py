"""[Lào Cai] 1.011441.H38 — planner đính kèm + khối chủ hồ sơ/ghi chú của mapper. Dữ liệu giả."""

import base64

from app.pipelines.dang_ky_bien_phap_bao_dam_lao_cai.attach import planner
from app.pipelines.dang_ky_bien_phap_bao_dam_lao_cai.process import mapper
from app.pipelines.dang_ky_bien_phap_bao_dam_lao_cai.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)


def _file(name: str, content: bytes = b"x") -> dict:
    return {"name": name, "type": "application/pdf",
            "dataUrl": "data:application/pdf;base64," + base64.b64encode(content).decode()}


def _by_file(attachments):
    out: dict[int, list[dict]] = {}
    for item in attachments:
        out.setdefault(item["fileIndex"], []).append(item)
    return out


# ------------------------------------------------------------------ planner

def test_moi_tep_dung_mot_dong_va_gcn_thu_hai_vao_dong_3():
    files = [_file(f"f{i}.pdf", bytes([i])) for i in range(8)]
    llm = {
        0: {"docType": "phieu_01a"},
        1: {"docType": "hop_dong_the_chap"},
        2: {"docType": "gcn", "gcnSoPhatHanh": "AB 111111", "gcnPages": 2},
        3: {"docType": "gcn", "gcnSoPhatHanh": "CD 222222"},
        4: {"docType": "van_ban_uy_quyen", "documentName": "Giấy giới thiệu"},
        5: {"docType": "cccd", "documentName": "Căn cước công dân Nguyễn Văn A"},
        6: {"docType": "other", "documentName": "Văn bản xác nhận ABC"},
        7: {"docType": "bien_ban_dinh_gia", "documentName": "Biên bản định giá tài sản số 01/2026"},
    }
    attachments, _warnings, classified = planner.build_plan_items(files, llm)
    by_file = _by_file(attachments)

    assert sorted(by_file) == list(range(8))
    assert all(len(items) == 1 for items in by_file.values())
    assert len(classified) == 8
    slot = {i: by_file[i][0].get("slotIndex") for i in by_file}
    assert slot[0] == 2 and slot[1] == 0 and slot[2] == 1 and slot[3] == 3 and slot[4] == 4
    assert by_file[2][0]["soBan"] == 2
    assert all(by_file[i][0]["tickRow"] for i in (0, 1, 2, 3, 4))
    # Dòng 1 và 3 cùng đoạn đầu tên → slotName nguyên văn đầy đủ, khác nhau.
    assert by_file[2][0]["slotName"] != by_file[3][0]["slotName"]
    assert by_file[2][0]["slotName"].startswith("Giấy chứng nhận quyền sử dụng đất hoặc")
    for i in (5, 6, 7):
        item = by_file[i][0]
        assert item["target"] == "new" and item["needsAddComponent"] and item["noChooserClick"]
        assert item["documentName"] and "/" not in item["documentName"]
    assert by_file[7][0]["documentName"] == "Biên bản định giá tài sản số 01-2026"


def test_gcn_cung_so_hoac_khong_doc_duoc_so_deu_vao_dong_1():
    files = [_file("a.pdf", b"a"), _file("b.pdf", b"b"), _file("c.pdf", b"c")]
    llm = {
        0: {"docType": "gcn"},
        1: {"docType": "gcn", "gcnSoPhatHanh": "AB111111"},
        2: {"docType": "gcn", "gcnSoPhatHanh": "ab 111111"},
    }
    attachments, _w, _c = planner.build_plan_items(files, llm)
    assert [a["slotIndex"] for a in attachments] == [1, 1, 1]


def test_tep_khong_phan_loai_duoc_van_dinh_vao_giay_to_khac_va_ten_khong_trung():
    files = [_file("x.pdf", b"1"), _file("y.pdf", b"2"), _file("z.pdf", b"3")]
    llm = {0: {"docType": "cccd"}, 1: {"docType": "cccd"}}
    attachments, warnings, _c = planner.build_plan_items(files, llm)
    names = [a["documentName"] for a in attachments]

    assert len(attachments) == 3
    assert all(a["target"] == "new" for a in attachments)
    assert len(set(names)) == 3
    assert any("BẮT BUỘC" in w for w in warnings)


def test_giay_gioi_thieu_gop_trong_phieu_duoc_dinh_them_vao_dong_4():
    files = [_file("p.pdf", b"p"), _file("g.pdf", b"g")]
    llm = {0: {"docType": "phieu_01a", "alsoTypes": ["van_ban_uy_quyen", "gcn"]}, 1: {"docType": "gcn"}}
    attachments, _w, _c = planner.build_plan_items(files, llm)
    slots = sorted((a["fileIndex"], a["slotIndex"]) for a in attachments)
    assert slots == [(0, 2), (0, 4), (1, 1)]


def test_tep_trung_noi_dung_van_dinh_du_va_canh_bao():
    files = [_file("a.pdf", b"same"), _file("b.pdf", b"same")]
    llm = {0: {"docType": "hop_dong_the_chap"}, 1: {"docType": "hop_dong_the_chap"}}
    attachments, warnings, _c = planner.build_plan_items(files, llm)
    assert len(attachments) == 2
    assert any("trùng nội dung" in w for w in warnings)


# ------------------------------------------------------------------ mapper: chủ hồ sơ + ghi chú

_CA_NHAN = [
    {"name": "ChuHoSo_HoTen", "value": "ÔNG (BÀ): Nguyễn Văn Giả,"},
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001080000011"},
    {"name": "ChuHoSo_NgayCap", "value": "01/02/2021"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0900.000.011"},
    {"name": "BenNhanBaoDam_Ten", "value": "QUỸ TÍN DỤNG GIẢ ĐỊNH"},
]
_TO_CHUC = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "NGÂN HÀNG GIẢ ĐỊNH - CHI NHÁNH MẪU"},
    {"name": "ChuHoSo_MaSoThue", "value": "0100000001-001"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Văn Ký"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001080000022"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1"}},
]


def _names(fields):
    return [f["name"] for f in fields]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_chu_ho_so_ca_nhan_phat_CN_truoc_va_loc_o_to_chuc():
    fields, _ = mapper.enrich(_CA_NHAN, {})
    names = _names(fields)
    values = _values(fields)
    chs = [n for n in names if n.startswith("ChuHoSo_")]

    assert chs[0] == "ChuHoSo_maDoiTuongNopHS" and values[chs[0]] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN GIẢ"
    assert values["ChuHoSo_soCMNDChuHoSo"] == "001080000011"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0900000011"
    assert values["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    # Chỉ có năm sinh → không bịa ngày.
    assert "ChuHoSo_ngaySinhChuHoSo" not in values
    assert not ORG_ONLY_FIELDS & set(names)
    # Nơi cấp mặc định (không từ giấy tờ) phải gắn cờ default.
    noi_cap = next(f for f in fields if f["name"] == "ChuHoSo_noiCapCMNDCHS")
    assert noi_cap.get("default") is True


def test_chu_ho_so_to_chuc_phat_DN_giu_ma_chi_nhanh_va_loc_o_ca_nhan():
    fields, _ = mapper.enrich(_TO_CHUC, {})
    names = _names(fields)
    values = _values(fields)
    chs = [n for n in names if n.startswith("ChuHoSo_")]

    assert chs[0] == "ChuHoSo_maDoiTuongNopHS" and values[chs[0]] == "DN"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "NGÂN HÀNG GIẢ ĐỊNH - CHI NHÁNH MẪU"
    assert values["ChuHoSo_maSoThueChuHoSo"] == "0100000001-001"
    assert not INDIVIDUAL_ONLY_FIELDS & set(names)
    # Người nộp đại diện cho tổ chức chủ hồ sơ.
    assert values["CongDan_tenCoQuanToChuc"] == "NGÂN HÀNG GIẢ ĐỊNH - CHI NHÁNH MẪU"
    assert values["CongDan_maSoThueNguoiNop"] == "0100000001-001"


def test_ghi_chu_tep_gop_cat_500_ky_tu_va_khong_phat_ve_viec():
    long_note = "Tệp hopdong.pdf gồm: " + "; ".join(f"({i}) Giấy tờ giả định số {i} (tr.{i})" for i in range(1, 40))
    fields, _ = mapper.enrich([*_CA_NHAN, {"name": "GhiChu_TepDinhChung", "value": long_note}], {})
    values = _values(fields)

    assert "HoSoOnline_ghiChu" in values
    assert len(values["HoSoOnline_ghiChu"]) <= 500
    assert values["HoSoOnline_ghiChu"].startswith("Tệp hopdong.pdf gồm:")
    assert "HoSoOnline_veViec" not in values
    assert "HoSoOnline_veViec" not in UI_COMP_BY_NAME
    assert "chkbox_nguoinoplachuhs" not in UI_COMP_BY_NAME


def test_khong_co_tep_gop_thi_khong_phat_ghi_chu():
    fields, _ = mapper.enrich(_CA_NHAN, {})
    assert "HoSoOnline_ghiChu" not in _values(fields)
