"""Pipeline "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" (1.013818): chỉ đính kèm, 3 dòng cố định.

Dữ liệu trong test là ví dụ bịa (tên, số giấy tờ, cơ quan) — không lấy từ hồ sơ thật.
"""

from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.attach import planner
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.attach.planner import (
    build_plan_items,
    rule_types,
)
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

_KEY = "dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung"

REGISTRATION_TEXT = (
    "Mẫu TP-TSCC-10 Ban hành kèm theo Thông tư số 06/2025/TT-BTP CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM "
    "GIẤY ĐĂNG KÝ THAM DỰ KIỂM TRA KẾT QUẢ TẬP SỰ HÀNH NGHỀ CÔNG CHỨNG Kính gửi: Bộ Tư pháp "
    "Tôi tên là: NGUYỄN THỊ AN; Giới tính: Nữ; Ngày, tháng, năm sinh: 01/02/1990; "
    "Số thẻ căn cước: 001190000123; Thời gian tập sự: 12 tháng; "
    "Đã được công nhận hoàn thành tập sự theo quyết định số: 12/QĐ-STP ngày 01/03/2026 của Sở Tư pháp tỉnh Ninh Bình;"
)
DECISION_TEXT = (
    "UBND TỈNH NINH BÌNH SỞ TƯ PHÁP Số: 12/QĐ-STP BẢN SAO QUYẾT ĐỊNH "
    "Công nhận hoàn thành tập sự hành nghề công chứng GIÁM ĐỐC SỞ TƯ PHÁP "
    "Điều 1. Công nhận hoàn thành tập sự hành nghề công chứng đối với bà Nguyễn Thị An; Số thẻ căn cước công dân: "
    "001190000123. CHỨNG THỰC BẢN SAO ĐÚNG VỚI BẢN CHÍNH"
)
RECEIPT_TEXT = (
    "BIÊN LAI THU TIỀN PHÍ, LỆ PHÍ Tên loại phí: Phí thẩm định tiêu chuẩn, điều kiện hành nghề công chứng "
    "Số tiền: 3.500.000 đồng Người nộp: Nguyễn Thị An"
)
CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số định danh cá nhân 001190000123 Họ, chữ đệm và tên NGUYỄN THỊ AN"


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _rows(items):
    return {item["componentIndex"]: item for item in items if item["target"] == "existing"}


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.013818"
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    procedure = registry.get_procedure(_KEY)
    assert procedure["label"] == link["label"]
    assert procedure["mode"] == "attach"
    assert "maThuTuc=1.013818" in procedure["detect"]["urlIncludes"]
    assert registry.get_attach_pipeline(_KEY) is planner.plan


def test_rule_types_giay_dang_ky_nhac_quyet_dinh_van_la_giay_dang_ky():
    assert rule_types(REGISTRATION_TEXT) == ["registration"]
    assert rule_types(DECISION_TEXT) == ["decision"]
    assert rule_types(RECEIPT_TEXT) == ["fee_receipt"]
    assert rule_types(CCCD_TEXT) == []
    # File gộp: giấy chính là giấy có tiêu đề xuất hiện trước.
    assert rule_types(REGISTRATION_TEXT + " " + RECEIPT_TEXT) == ["registration", "fee_receipt"]


def test_thieu_chung_tu_nop_phi_dong_2_de_trong_va_canh_bao():
    items, classified, warnings = build_plan_items(
        _files("qd.pdf", "dk.pdf"), {0: DECISION_TEXT, 1: REGISTRATION_TEXT}, {})
    rows = _rows(items)
    assert set(rows) == {1, 3} and len(items) == 2
    assert rows[1]["fileIndex"] == 0 and rows[3]["fileIndex"] == 1
    assert not any("sourceFileIndexes" in item for item in items)
    assert rows[1]["componentName"] == "Quyết định công nhận hoàn thành tập sự"
    assert rows[3]["componentName"] == "Giấy đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng"
    assert all(item["needsAddComponent"] is False for item in items)
    assert warnings == [
        "Hồ sơ đã gửi không có giấy tờ chứng minh đã nộp phí thẩm định tiêu chuẩn, điều kiện hành nghề công chứng "
        "(dòng 2). Cần bổ sung."
    ]
    assert [c["componentIndexes"] for c in classified] == [[1], [3]]


def test_du_3_giay_khong_canh_bao():
    items, _, warnings = build_plan_items(
        _files("dk.pdf", "bl.jpg", "qd.pdf"), {0: REGISTRATION_TEXT, 1: RECEIPT_TEXT, 2: DECISION_TEXT}, {})
    rows = _rows(items)
    assert [rows[r]["fileIndex"] for r in (1, 2, 3)] == [2, 1, 0]
    assert [item["componentIndex"] for item in items] == [1, 2, 3]
    assert len({item["documentName"] for item in items}) == 3
    assert warnings == []


def test_nhieu_file_cung_dong_gop_mot_pdf_theo_thu_tu_tai_len():
    items, _, _ = build_plan_items(
        _files("qd.pdf", "bl1.jpg", "dk.pdf", "bl2.jpg"),
        {0: DECISION_TEXT, 1: RECEIPT_TEXT, 2: REGISTRATION_TEXT, 3: RECEIPT_TEXT}, {})
    fee = _rows(items)[2]
    assert fee["fileIndex"] == 1 and fee["sourceFileIndexes"] == [1, 3]


def test_file_gop_dang_ky_kem_bien_lai_dinh_nguyen_file_vao_ca_dong_2():
    items, classified, warnings = build_plan_items(
        _files("qd.pdf", "dk_bl.pdf"), {0: DECISION_TEXT, 1: REGISTRATION_TEXT + " " + RECEIPT_TEXT}, {})
    rows = _rows(items)
    assert rows[2]["fileIndex"] == 1 and rows[3]["fileIndex"] == 1
    assert classified[1]["type"] == "registration" and classified[1]["componentIndexes"] == [2, 3]
    assert any("dòng 2: dk_bl.pdf" in w for w in warnings)
    assert not any("Cần bổ sung" in w for w in warnings)


def test_file_gop_khong_dinh_lai_khi_dong_da_co_file_rieng():
    items, classified, warnings = build_plan_items(
        _files("dk_bl.pdf", "bl.jpg"), {0: REGISTRATION_TEXT + " " + RECEIPT_TEXT, 1: RECEIPT_TEXT}, {})
    rows = _rows(items)
    assert rows[2]["fileIndex"] == 1 and "sourceFileIndexes" not in rows[2]
    assert classified[0]["componentIndexes"] == [3]
    assert not any("nhiều giấy" in w for w in warnings)


def test_can_cuoc_va_giay_khac_them_thanh_phan_moi_khong_bo_file():
    llm = {2: {"type": "other", "documentName": "Giấy xác nhận thời gian tập sự"}, 3: {"type": "other",
                                                                                   "documentName": ""}}
    items, classified, warnings = build_plan_items(
        _files("qd.pdf", "cccd.jpg", "xn.pdf", "la.pdf"), {0: DECISION_TEXT, 1: CCCD_TEXT, 2: "", 3: ""}, llm)
    by_file = {item["fileIndex"]: item for item in items}
    assert set(by_file) == {0, 1, 2, 3}
    for index in (1, 2, 3):
        assert by_file[index]["target"] == "new" and by_file[index]["needsAddComponent"] is True
        assert by_file[index]["componentName"] == by_file[index]["documentName"]
    assert by_file[1]["detectedType"] == "identity" and by_file[1]["documentName"] == "Căn cước công dân"
    assert by_file[2]["documentName"] == "Giấy xác nhận thời gian tập sự"
    assert by_file[3]["documentName"] == "Tài liệu khác"
    assert [c["source"] for c in classified] == ["rule", "default", "llm", "llm"]
    assert any("cccd.jpg, xn.pdf, la.pdf" in w for w in warnings)


def test_llm_phan_loai_file_khong_co_tieu_de():
    items, _, warnings = build_plan_items(
        _files("anh_chuyen_khoan.jpg", "dk.pdf"), {0: "Vietcombank 3.500.000 VND", 1: REGISTRATION_TEXT},
        {0: {"type": "fee_receipt", "documentName": ""}})
    assert _rows(items)[2]["fileIndex"] == 0
    assert any("(dòng 1)" in w for w in warnings) and not any("(dòng 2)" in w for w in warnings)


def test_validated_classifications_bo_index_sai_va_chuan_hoa_type():
    out = planner._validated_classifications(
        [{"fileIndex": 0, "type": "bien_lai"}, {"fileIndex": 5, "type": "decision"}, {"fileIndex": 1, "type": "xyz"},
         {"fileIndex": 0, "type": "decision"}], 2)
    assert out == {0: {"type": "fee_receipt", "documentName": ""}, 1: {"type": "other", "documentName": ""}}


async def test_plan_chi_hoi_llm_file_tieu_de_khong_nhan_ra(monkeypatch):
    texts = {"qd.pdf": DECISION_TEXT, "dk.pdf": REGISTRATION_TEXT, "ck.jpg": "Giao dich 3.500.000"}
    asked: list[list[int]] = []

    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_classify(documents):
        asked.append([doc["fileIndex"] for doc in documents])
        # Trả cả index của file rule đã nhận → phải bị bỏ qua.
        return [{"fileIndex": 2, "type": "fee_receipt"}, {"fileIndex": 0, "type": "other"}]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)
    files = [FileItem(name=n, type="image/jpeg" if n.endswith(".jpg") else "application/pdf", dataUrl="data:,",
                      role="")
             for n in ("qd.pdf", "dk.pdf", "ck.jpg")]
    out = await planner.plan(files, {}, {"request_id": "req-test"})
    assert asked == [[2]]
    assert [(a["componentIndex"], a["fileIndex"]) for a in out["attachments"]] == [(1, 0), (2, 2), (3, 1)]
    assert out["errors"] == []
    assert out["extracted"]["llmDocuments"] == ["ck.jpg"]
    assert out["extracted"]["attachmentMode"] == "preserve_files"


async def test_plan_llm_loi_van_giu_du_file(monkeypatch):
    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": CCCD_TEXT if f["name"] == "cccd.jpg" else ""} for f in files]

    async def boom(_documents):
        raise RuntimeError("llm down")

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", boom)
    files = [FileItem(name="cccd.jpg", type="image/jpeg", dataUrl="data:,", role=""),
             FileItem(name="la.pdf", type="application/pdf", dataUrl="data:,", role="")]
    out = await planner.plan(files)
    assert [a["detectedType"] for a in out["attachments"]] == ["identity", "other"]
    assert any(e.startswith("attachment_agent:") for e in out["errors"])
    assert sum("Cần bổ sung" in e for e in out["errors"]) == 3


def test_tro_ly_cung_key_chon_so_va_attach_only():
    from app.channels.handfree.procedure_registry import get_attach_pipeline, get_procedure

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    proc = get_procedure(_KEY)
    assert proc["mode"] == "attach" and proc["flowProfile"] == "tu-phap"
    assert proc["keKhaiUrl"] == link["url"]
    assert proc["agencyProvinceOnly"] is True and proc["agencySoFirst"] is True
    assert proc["agencyDeptLabel"] == "Sở Tư pháp"
    assert proc["requiresConsent"] is False and proc["ownerInfo"]["enabled"] is False
    assert proc["guidedSteps"] == get_procedure("bau-to-truong-to-hoa-giai")["guidedSteps"]
    assert "maThuTuc=1.013818" in proc["detect"]["urlIncludes"]
    assert [d["key"] for d in proc["requiredDocs"]] == ["quyet_dinh", "nop_phi", "giay_dang_ky", "khac"]
    assert get_attach_pipeline(_KEY) is registry.get_attach_pipeline(_KEY)
