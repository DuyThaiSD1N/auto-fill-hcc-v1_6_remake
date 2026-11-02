"""Đính kèm không bỏ sót tệp: giấy lạ (other) và CCCD đều phải có item ở dòng cố định của planner.

Phủ các planner: 3 thủ tục hội cấp tỉnh (tách/gộp theo đoạn), 4 thủ tục thi/xét tuyển (một ô Phiếu), cấp nước
sạch, đổi tên nước sạch, cấp lại thẻ HDV du lịch Đà Nẵng.
"""

import pytest

from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.attach import planner as bao_cao_dai_hoi
from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.attach import planner as hdv_da_nang
from app.pipelines.cap_nuoc_sach.attach import planner as cap_nuoc_sach
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach import planner as chia_tach_hoi
from app.pipelines.doi_ten_nuoc_sach.attach import planner as doi_ten_nuoc_sach
from app.pipelines.thi_tuyen_cong_chuc.attach import planner as thi_tuyen
from app.pipelines.thi_tuyen_cong_chuc_mot_cua_moha.attach import planner as thi_tuyen_moha
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach import planner as thong_bao_dai_hoi
from app.pipelines.xet_tuyen_cong_chuc.attach import planner as xet_tuyen_cc
from app.pipelines.xet_tuyen_vien_chuc.attach import planner as xet_tuyen_vc

_CCCD = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001000000001\nHọ và tên: NGUYEN VAN A"
_LA = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY XÁC NHẬN\nXác nhận ông NGUYEN VAN A"


def _files(n: int) -> list[dict]:
    return [{"name": f"f{i}.pdf", "type": "application/pdf"} for i in range(n)]


# ---------------- Hội cấp tỉnh (attp-row, tách/gộp theo đoạn) ----------------
def _hoi_inputs(main_type: str, main_text: str):
    texts = [main_text, _LA, _CCCD]
    types = [main_type, "other", "cccd"]
    segments = [
        {"fileIndex": i, "pageFrom": 1, "pageTo": 1, "type": t, "documentName": ""} for i, t in enumerate(types)
    ]
    file_meta = {i: {"pageCount": 1, "pageBoundariesAvailable": True} for i in range(3)}
    pages_by_file = {i: {1: text} for i, text in enumerate(texts)}
    return _files(3), segments, file_meta, pages_by_file


@pytest.mark.parametrize(
    ("mod", "main_type", "main_text", "main_row"),
    [
        (bao_cao_dai_hoi, "bao_cao_to_chuc_dai_hoi",
         "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBÁO CÁO tổ chức đại hội nhiệm kỳ\nKính gửi: Sở Nội vụ", 15),
        (chia_tach_hoi, "don_de_nghi", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ chia, tách hội", 2),
        (thong_bao_dai_hoi, "bao_cao_ket_qua",
         "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBÁO CÁO kết quả đại hội\nKính gửi: Sở Nội vụ", 1),
    ],
)
def test_hoi_cap_tinh_doan_la_va_cccd_thanh_item_rieng_o_dong_chinh(mod, main_type, main_text, main_row):
    out = mod.build_plan_items(*_hoi_inputs(main_type, main_text))
    attachments, classified, warnings = out[0], out[1], out[2]
    assert [(a["fileIndex"], a["componentIndex"]) for a in attachments if a["fileIndex"] == 0] == [(0, main_row)]
    shared = [a for a in attachments if a["fileIndex"] in (1, 2)]
    assert [(a["fileIndex"], a["componentIndex"], a["target"], a["detectedType"]) for a in shared] == [
        (1, main_row, "attp-row", "other"),
        (2, main_row, "attp-row", "cccd"),
    ]
    # Mỗi đoạn một item; đoạn phủ trọn tệp thì đính nguyên tệp (không cắt trang).
    assert not any(a.get("sourceSegments") or a.get("sourceFileIndexes") for a in attachments)
    assert [a["documentName"] for a in shared] == ["f1", "f2"]
    assert not any(c.get("target") == "skip" for c in classified)
    assert any("đã đính chung dòng" in w and "f1.pdf" in w and "f2.pdf" in w for w in warnings)


# ---------------- Thi/xét tuyển (fixed-slot, một ô Phiếu) ----------------
@pytest.mark.parametrize("mod", [thi_tuyen, thi_tuyen_moha, xet_tuyen_cc, xet_tuyen_vc])
def test_tuyen_giay_la_va_cccd_dinh_chung_o_phieu(mod):
    files = _files(3)
    ocr = [{"name": "f0.pdf", "text": "PHIẾU ĐĂNG KÝ DỰ TUYỂN"}, {"name": "f1.pdf", "text": _LA},
           {"name": "f2.pdf", "text": _CCCD}]
    items, warnings = mod.build_plan_items(files, ocr, {0: "phieu_dang_ky_du_tuyen"})
    assert [(i["fileIndex"], i["slotIndex"], i["target"]) for i in items] == [
        (0, 0, "fixed-slot"), (1, 0, "fixed-slot"), (2, 0, "fixed-slot")
    ]
    assert [i["documentName"] for i in items[1:]] == ["f1.pdf", "f2.pdf"]
    assert [i["detectedType"] for i in items[1:]] == ["other", "other"]
    assert len(warnings) == 1 and "f1.pdf, f2.pdf" in warnings[0]


# ---------------- Nước sạch (fixed-slot) ----------------
def test_cap_nuoc_sach_giay_la_vao_o_don_ho_gia_dinh_cccd_giu_dong_moi():
    files = _files(3)
    items, warnings, classified = cap_nuoc_sach.build_plan_items(
        files, [], {0: "household_application", 1: "other", 2: "identity_document"}
    )
    assert [(i["fileIndex"], i["target"], i.get("slotIndex")) for i in items] == [
        (0, "fixed-slot", 0), (1, "fixed-slot", 0), (2, "new", None)
    ]
    assert items[1]["documentName"] == "f1.pdf" and items[1]["detectedType"] == "other"
    assert classified[1]["routedTo"] == "household_application"
    assert "f1.pdf" in warnings[0]


def test_cap_nuoc_sach_lo_to_chuc_thi_giay_la_vao_o_don_to_chuc():
    items, _, _ = cap_nuoc_sach.build_plan_items(_files(2), [], {0: "organization_application", 1: "other"})
    assert [i["slotIndex"] for i in items] == [1, 1]


def test_doi_ten_nuoc_sach_giay_la_vao_o_don_cccd_giu_dong_moi():
    items, warnings, _ = doi_ten_nuoc_sach.build_plan_items(
        _files(3), [], {0: "template_name_change_application", 1: "other", 2: "identity_document"}
    )
    assert [(i["fileIndex"], i["target"], i.get("slotIndex")) for i in items] == [
        (0, "fixed-slot", 4), (1, "fixed-slot", 4), (2, "new", None)
    ]
    assert "f1.pdf" in warnings[0]


def test_doi_ten_nuoc_sach_chua_co_don_thi_vao_o_don_co_xac_nhan():
    items, _, _ = doi_ten_nuoc_sach.build_plan_items(_files(1), [], {0: "other"})
    assert [(i["slotIndex"], i["documentName"]) for i in items] == [(1, "f0.pdf")]


# ---------------- Cấp lại thẻ HDV du lịch Đà Nẵng (fixed-slot) ----------------
def test_hdv_da_nang_giay_la_va_cccd_dinh_chung_dong_giay_to():
    items, warnings, classified = hdv_da_nang.build_plan_items(
        _files(3), {0: ("don_cap_lai", []), 1: ("other", []), 2: ("cccd", [])}
    )
    assert [(i["fileIndex"], i["slotIndex"], i["target"]) for i in items] == [
        (0, 1, "fixed-slot"), (1, 0, "fixed-slot"), (2, 0, "fixed-slot")
    ]
    assert [i["documentName"] for i in items[1:]] == ["f1.pdf", "f2.pdf"]
    assert items[2]["detectedType"] == "cccd"
    assert not any(c.get("target") == "skip" for c in classified)
    assert any("đã đính chung dòng" in w and "f1.pdf" in w and "f2.pdf" in w for w in warnings)


def test_hdv_da_nang_trang_cccd_trong_pdf_gop_thanh_item_rieng():
    items, _, _ = hdv_da_nang.build_plan_items(
        _files(1), {}, {0: ["don_cap_lai", "cccd", "chung_chi_nghiep_vu"]}
    )
    assert [(i["slotIndex"], i["detectedType"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        (1, "don_cap_lai", [0]), (0, "cccd", [1]), (0, "chung_chi_nghiep_vu", [2])
    ]
