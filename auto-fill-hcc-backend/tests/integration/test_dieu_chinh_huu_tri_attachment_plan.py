import json

from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import planner
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_dieu_chinh_huu_tri_attach_maps_van_ban_and_skips_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "van-ban.pdf",
                "text": (
                    "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
                    "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
                ),
            },
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố: 031071000001",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps(
            {
                "documents": [
                    {"index": 0, "type": "van_ban_de_nghi_huu_tri", "title": "Văn bản đề nghị trợ cấp hưu trí xã hội"},
                    {"index": 1, "type": "giay_to_tuy_than", "title": "Căn cước công dân"},
                ]
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("van-ban.pdf"), _file("cccd.pdf")], {}, None)

    # Bảng chỉ còn MỘT dòng → mọi file đều vào dòng 1, không bỏ sót.
    assert len(res["attachments"]) == 2
    assert all(item["slotIndex"] == 0 for item in res["attachments"])
    item = res["attachments"][0]
    assert item["fileName"] == "van-ban.pdf"
    assert item["target"] == "fixed-slot"
    assert item["slotIndex"] == 0
    assert item["slotKey"] == "van_ban_de_nghi_huu_tri"
    assert "Văn bản đề nghị" in item["slotName"]
    assert res["attachments"][1]["fileName"] == "cccd.pdf"
    assert any("giấy tờ tùy thân" in err for err in res["errors"])


async def test_dieu_chinh_huu_tri_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "van-ban.pdf",
                "text": (
                    "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
                    "Mẫu số 01\n"
                    "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
                ),
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("van-ban.pdf")], {}, None)

    assert len(res["attachments"]) == 1
    assert res["attachments"][0]["slotKey"] == "van_ban_de_nghi_huu_tri"
    assert any("attachment_agent" in err for err in res["errors"])


def test_dieu_chinh_huu_tri_rule_rejects_explicit_mau_02():
    text = (
        "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
        "Mẫu số 02\n"
        "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
    )

    assert planner.detect_slot_key(text) == ""


# ---------------------------------------------------------------------------
# Hồ sơ thật req_1d66e02a4271: nộp TRÍCH LỤC KHAI TỬ, bị xếp nhầm thành giấy tờ tùy thân và đính vào
# dòng "Một trong các giấy tờ có ảnh…" (add-document-dialog).
# ---------------------------------------------------------------------------
_TRICH_LUC_KHAI_TU = (
    "TỈNH LÂM ĐỒNG UBND PHƯỜNG L. Số: 104/2026/TLKT\n"
    "TRÍCH LỤC KHAI TỬ\n"
    "Họ, chữ đệm, tên: ĐÀO THỊ T.  Ngày, tháng, năm sinh: 12/04/1938\n"
    "Số định danh cá nhân: 0681xxxxxxx\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 0681xxxxxxx, Cục cảnh sát quản lý hành chính về "
    "trật tự xã hội cấp ngày 28/06/2021\n"
    "Đã chết vào lúc 09 giờ 00 phút, ngày 03/09/2026\n"
    "Họ, chữ đệm, tên người đi khai tử: VƯƠNG ĐÌNH P.\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 0680xxxxxxx"
)


def _files_one(name="SKM_550i.pdf"):
    return [{"name": name, "type": "application/pdf"}], [{"name": name, "text": _TRICH_LUC_KHAI_TU}]


def test_trich_luc_khai_tu_khong_bi_xep_thanh_giay_to_tuy_than():
    """Trích lục khai tử NHẮC "Thẻ căn cước công dân số …" trong phần thông tin, nhưng bản thân nó
    KHÔNG phải giấy tờ tùy thân → không được đính vào dòng "Một trong các giấy tờ có ảnh…".
    Vẫn phải được đính (không bỏ sót) vào dòng duy nhất của thủ tục, kèm cảnh báo."""
    files, ocr = _files_one()

    items, warnings = planner.build_plan_items(files, ocr, {0: ""})

    assert len(items) == 1
    assert items[0]["target"] == "fixed-slot"
    assert items[0]["slotIndex"] == 0
    assert all(item.get("target") != "add-document-dialog" for item in items)
    assert any("SKM_550i.pdf" in w for w in warnings)


def test_luoi_keyword_cu_da_bi_go_khoi_luong_quyet_dinh():
    """`is_excluded_document` vẫn khớp nhầm (giữ lại để đối chứng) nhưng KHÔNG còn được dùng để định
    tuyến — nếu ai đó nối lại vào build_plan_items thì test trên sẽ vỡ."""
    assert planner.is_excluded_document(_TRICH_LUC_KHAI_TU) is True
    assert "KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH" in planner.is_excluded_document.__doc__


def test_cccd_cung_vao_dong_1_vi_cong_da_bo_nut_them_giay_to():
    """Cổng đã bỏ thành phần phụ + nút "Thêm giấy tờ" (chốt user 2026-09-15) → CCCD cũng vào dòng 1,
    KHÔNG còn target add-document-dialog. Tên hiển thị vẫn phân biệt để cán bộ soát."""
    files = [{"name": "cccd.pdf", "type": "application/pdf"}]
    ocr = [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN / CITIZEN IDENTITY CARD ..."}]

    items, warnings = planner.build_plan_items(files, ocr, {0: "giay_to_tuy_than"})

    assert len(items) == 1
    assert items[0]["target"] == "fixed-slot"
    assert items[0]["slotIndex"] == 0
    assert "tùy thân" in items[0]["documentName"]
    assert any("giấy tờ tùy thân" in w for w in warnings)


def test_khong_con_bat_ky_target_add_document_dialog_nao():
    files = [{"name": f"{n}.pdf", "type": "application/pdf"} for n in ("a", "b", "c")]
    for llm in ({}, {0: "van_ban_de_nghi_huu_tri", 1: "giay_to_tuy_than", 2: "other"}):
        items, _ = planner.build_plan_items(files, [], llm)
        assert len(items) == 3
        assert all(item["target"] == "fixed-slot" and item["slotIndex"] == 0 for item in items)
        assert all(item["needsAddComponent"] is False for item in items)


def test_tuyet_doi_khong_bo_sot_file_ke_ca_khi_llm_chet():
    """Chốt user: KHÔNG lưới keyword nào (kể cả làm phao) và KHÔNG được bỏ sót file. LLM im lặng →
    mọi file về dòng Văn bản đề nghị kèm cảnh báo, chứ không đoán mò bằng keyword."""
    names = ["khai-tu.pdf", "don.pdf", "cccd.pdf"]
    files = [{"name": n, "type": "application/pdf"} for n in names]
    ocr = [
        {"name": "khai-tu.pdf", "text": _TRICH_LUC_KHAI_TU},
        {"name": "don.pdf", "text": "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI (Mẫu số 01)"},
        {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN / CITIZEN IDENTITY CARD"},
    ]

    items, warnings = planner.build_plan_items(files, ocr, {})

    assert [item["fileIndex"] for item in items] == [0, 1, 2]
    assert all(item["target"] == "fixed-slot" for item in items)
    assert len(warnings) == 3
    # detect_slot_key VẪN nhận ra "don.pdf" nếu bị gọi → chứng minh nó đã bị gỡ khỏi luồng.
    assert planner.detect_slot_key(ocr[1]["text"]) == planner.SLOT["slotKey"]


def test_khong_con_luoi_keyword_nao_trong_luong_quyet_dinh():
    for fn in (planner.is_excluded_document, planner.detect_slot_key):
        assert "KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH" in (fn.__doc__ or ""), fn.__name__


def test_prompt_co_type_rieng_va_chan_bay_trich_luc_khai_tu():
    from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach.prompt import SYSTEM_PROMPT

    assert "giay_to_tuy_than" in SYSTEM_PROMPT
    assert "TRÍCH LỤC KHAI TỬ" in SYSTEM_PROMPT
    assert "KHÔNG biến tài liệu thành giấy tờ" in SYSTEM_PROMPT


def test_slot_name_khop_text_that_cua_cong():
    assert "Mẫu số 01 ban hành kèm theo Nghị định số 176/2025/NĐ-CP" in planner.SLOT["slotName"]
