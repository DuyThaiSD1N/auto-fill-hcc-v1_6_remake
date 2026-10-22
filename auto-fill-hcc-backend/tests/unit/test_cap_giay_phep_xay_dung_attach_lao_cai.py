"""GPXD đính kèm: Lào Cai đính khối 1–5 (STT 1/2/4); tên Đơn kèm họ tên chủ đầu tư. Dữ liệu giả."""

from app.pipelines.cap_giay_phep_xay_dung.attach import planner

_FILES = [{"name": n, "type": "application/pdf"} for n in ("don.pdf", "gcn.pdf", "banve.pdf", "camket.pdf")]
_OCR = [{"name": f["name"], "text": "ocr"} for f in _FILES]
_LLM = {
    0: {"type": "building_permit_application", "title": "Đơn đề nghị cấp giấy phép xây dựng", "chuDauTu": "Nguyễn Văn A"},
    1: {"type": "land_legal_document", "title": "Giấy chứng nhận"},
    2: {"type": "construction_design_drawings", "title": "Bản vẽ"},
    3: {"type": "safety_commitment", "title": "Bản cam kết"},
}


def _stt(nhanh):
    items, _, _ = planner.build_plan_items(_FILES, _OCR, _LLM, nhanh)
    return {it["fileName"]: it["componentIndex"] for it in items}, items


def test_khoi_khong_theo_tuyen_stt_1_2_4_cam_ket_vao_ban_ve():
    stt, items = _stt("khong_theo_tuyen")
    assert stt == {"don.pdf": 1, "gcn.pdf": 2, "banve.pdf": 4, "camket.pdf": 4}
    assert all(it["slotIndex"] == it["componentIndex"] - 1 for it in items)
    assert all(it["slotKey"].startswith("gpxd_ktt_") for it in items)


def test_nha_o_rieng_le_giu_12_13_16():
    stt, _ = _stt("nha_o_rieng_le")
    assert stt == {"don.pdf": 12, "gcn.pdf": 13, "banve.pdf": 16, "camket.pdf": 16}


def test_ten_don_kem_ho_ten_chu_dau_tu_chi_cho_don():
    _, items = _stt("nha_o_rieng_le")
    names = {it["fileName"]: it["documentName"] for it in items}
    assert names["don.pdf"] == "Đơn đề nghị cấp giấy phép xây dựng Nguyễn Văn A"
    assert "Nguyễn Văn A" not in names["gcn.pdf"]
    assert len(planner._label_for_type("building_permit_application", "", "Nguyễn Thị Phương Thảo Hoài")) <= 50


def test_hook_chi_bat_cho_tai_khoan_lao_cai():
    key = planner.PROCEDURE_KEY
    on = planner.with_account_attach_options({}, {"tinh": "Tỉnh Lào Cai", "xa": "Phường Yên Bái"}, key)
    assert on[planner.KHONG_THEO_TUYEN_OPTION] is True
    off = planner.with_account_attach_options({planner.KHONG_THEO_TUYEN_OPTION: True}, {"tinh": "Hà Nội"}, key)
    assert planner.KHONG_THEO_TUYEN_OPTION not in off
    other = planner.with_account_attach_options({}, {"tinh": "Tỉnh Lào Cai"}, "thu-tuc-khac")
    assert planner.KHONG_THEO_TUYEN_OPTION not in other
