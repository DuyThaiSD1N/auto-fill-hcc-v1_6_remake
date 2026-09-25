import json

from app.pipelines.khai_sinh_lien_thong.attach import planner as khai_sinh
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {"request_id": "req_khai_sinh_test", "procedure": "khai-sinh-dang-ky", "fields": []}


async def test_khai_sinh_attach_picks_birth_proof_into_single_slot(monkeypatch):
    """Giấy chứng sinh + CCCD cha/mẹ: tất cả vào STT1 dưới dạng NHIỀU TỆP RỜI (không gộp PDF)."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 040203015844"},
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "cccd-me.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012193000851"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "other"},
            {"index": 1, "docType": "birth_proof"},
            {"index": 2, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("cccd-bo.pdf"), _file("chung-sinh.pdf"), _file("cccd-me.pdf")], {}, _session()
    )
    items = res["attachments"]

    # Trang cho nhiều tệp/hàng → chứng sinh + 2 CCCD là 3 item RỜI cùng ô STT1, KHÔNG gộp PDF.
    assert len(items) == 3
    assert all(it["target"] == "fixed-slot" and it["slotIndex"] == 0 for it in items)
    assert all(it["repeatUpload"] is True for it in items)
    assert all("sourceFileIndexes" not in it for it in items)
    assert all(it["documentName"] == "Giấy chứng sinh" for it in items)
    # Chứng sinh trước, rồi các "other" (CCCD cha/mẹ) theo thứ tự file.
    assert [it["fileIndex"] for it in items] == [1, 0, 2]
    assert [it["fileName"] for it in items] == ["chung-sinh.pdf", "cccd-bo.pdf", "cccd-me.pdf"]
    assert res["extracted"]["birthProof"] == "chung-sinh.pdf"
    assert res["extracted"]["residenceForm"] is None
    assert res["extracted"]["skipped"] == []


async def test_khai_sinh_attach_two_slots_with_residence_form(monkeypatch):
    """Có cả giấy chứng sinh + tờ khai thay đổi thông tin cư trú → đính 2 ô đúng vị trí."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "cu-tru.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
            {"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "birth_proof"},
            {"index": 1, "docType": "residence_form"},
            {"index": 2, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("chung-sinh.pdf"), _file("cu-tru.pdf"), _file("cccd-bo.pdf")], {}, _session()
    )
    items = res["attachments"]

    # STT1 nhận chứng sinh + CCCD bố (2 tệp RỜI, repeatUpload); STT2 tách riêng tờ khai cư trú.
    assert len(items) == 3
    stt1 = [it for it in items if it["slotIndex"] == 0]
    stt2 = [it for it in items if it["slotIndex"] == 1]
    assert [it["fileIndex"] for it in stt1] == [0, 2]   # chứng sinh trước, rồi CCCD bố
    assert all(it["repeatUpload"] is True and "sourceFileIndexes" not in it for it in stt1)
    assert all(it["documentName"] == "Giấy chứng sinh" for it in stt1)
    assert len(stt2) == 1
    assert stt2[0]["fileName"] == "cu-tru.pdf"
    assert stt2[0]["documentName"] == "Tờ khai thay đổi thông tin cư trú"
    assert "repeatUpload" not in stt2[0]   # STT2 chỉ 1 tệp, không cần lặp menu
    assert all(it["target"] == "fixed-slot" for it in items)
    assert res["extracted"]["birthProof"] == "chung-sinh.pdf"
    assert res["extracted"]["residenceForm"] == "cu-tru.pdf"
    assert res["extracted"]["skipped"] == []


async def test_khai_sinh_attach_residence_form_rule_fallback(monkeypatch):
    """LLM lỗi → rule nhận ra tờ khai cư trú qua nội dung OCR và vẫn đính ô STT2."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "f1.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "f2.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("f1.pdf"), _file("f2.pdf")], {}, _session()
    )
    by_slot = {it["slotIndex"]: it for it in res["attachments"]}

    assert by_slot[0]["fileName"] == "f1.pdf"
    assert by_slot[1]["fileName"] == "f2.pdf"
    assert by_slot[1]["documentName"] == "Tờ khai thay đổi thông tin cư trú"


async def test_khai_sinh_attach_rule_fallback_when_llm_fails(monkeypatch):
    """LLM lỗi → rule theo nội dung OCR vẫn nhận ra văn bản người làm chứng về việc sinh."""
    async def fake_ocr_per_file(files):
        return [{"name": "lam-chung.pdf", "text": "VĂN BẢN NGƯỜI LÀM CHỨNG XÁC NHẬN VỀ VIỆC SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments([_file("lam-chung.pdf")], {}, _session())
    items = res["attachments"]

    assert len(items) == 1
    assert items[0]["fileName"] == "lam-chung.pdf"
    assert items[0]["target"] == "fixed-slot"


async def test_khai_sinh_attach_no_birth_proof(monkeypatch):
    """Không có giấy chứng sinh → không đính gì, báo lỗi rõ ràng."""
    async def fake_ocr_per_file(files):
        return [{"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "other"}]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments([_file("cccd-bo.pdf")], {}, _session())

    assert res["attachments"] == []
    assert res["extracted"]["birthProof"] is None
    assert any("Không tìm thấy giấy chứng sinh" in e for e in res["errors"])


async def test_khai_sinh_attach_keeps_identity_and_marriage_as_other(monkeypatch):
    """LLM chạy trước, nhưng CCCD/giấy kết hôn không được chiếm 2 ô cố định."""
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "cccd-kiet.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card\nHọ và tên / Full name: VÕ TUẤN KIỆT",
            },
            {
                "name": "cccd-vi.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card\nHọ và tên / Full name: KIỀU THỊ THÙY VI",
            },
            {
                "name": "ket-hon.pdf",
                "text": "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên vợ: KIỀU THỊ THÙY VI",
            },
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH\nĐã sinh con vào lúc 03 giờ 15"},
            {"name": "ct01.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # Cố tình mô phỏng LLM trả sai để chứng minh validation sau LLM không ép
        # CCCD/giấy kết hôn vào hai ô và rule vẫn cứu giấy tờ đích rõ ràng.
        return json.dumps({"documents": [
            {"index": 0, "docType": "birth_proof"},
            {"index": 1, "docType": "residence_form"},
            {"index": 2, "docType": "birth_proof"},
            {"index": 3, "docType": "other"},
            {"index": 4, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [
            _file("cccd-kiet.pdf"),
            _file("cccd-vi.pdf"),
            _file("ket-hon.pdf"),
            _file("chung-sinh.pdf"),
            _file("ct01.pdf"),
        ],
        {},
        _session(),
    )

    items = res["attachments"]
    stt1 = [it for it in items if it["slotIndex"] == 0]
    stt2 = [it for it in items if it["slotIndex"] == 1]
    # chứng sinh (idx3) trước, rồi CCCD×2 + kết hôn (idx0,1,2 = "other") — mỗi tệp RỜI vào STT1.
    assert [it["fileIndex"] for it in stt1] == [3, 0, 1, 2]
    assert all(it["repeatUpload"] is True and "sourceFileIndexes" not in it for it in stt1)
    assert stt1[0]["fileName"] == "chung-sinh.pdf"
    assert len(stt2) == 1 and stt2[0]["fileName"] == "ct01.pdf"
    assert res["extracted"]["skipped"] == []
    by_name = {item["fileName"]: item["docType"] for item in res["extracted"]["classified"]}
    assert by_name["cccd-kiet.pdf"] == "other"
    assert by_name["cccd-vi.pdf"] == "other"
    assert by_name["ket-hon.pdf"] == "other"
    assert res["extracted"]["llmDocuments"] == [
        "cccd-kiet.pdf", "cccd-vi.pdf", "ket-hon.pdf", "chung-sinh.pdf", "ct01.pdf"
    ]


async def test_khai_sinh_llm_result_uses_explicit_index_not_output_order(monkeypatch):
    """LLM được phép trả đảo thứ tự; nhãn vẫn phải theo index gốc, không theo vị trí mảng."""
    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 3, "docType": "birth_proof"},
            {"index": 5, "docType": "residence_form"},
            {"index": 0, "docType": "other"},
            {"index": 1, "docType": "other"},
            {"index": 2, "docType": "other"},
            {"index": 4, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    docs = [{"index": idx, "fileName": f"f{idx}.pdf", "text": "không rõ"} for idx in range(6)]

    classified = await khai_sinh._classify_with_llm(docs)

    assert classified[3] == "birth_proof"
    assert classified[5] == "residence_form"
    assert classified[0] == "other"


def test_khai_sinh_procedure_has_attachment_step():
    proc = get_procedure("khai-sinh-dang-ky-thuong")

    assert proc["hasAttachmentStep"] is True


_DECLARATION_OCR = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI ĐĂNG KÝ KHAI SINH\n"
    "Tôi cam đoan nội dung đề nghị đăng ký khai sinh trên đây là đúng sự thật"
)


def _declaration_ocr_and_chat(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "to-khai.pdf", "text": _DECLARATION_OCR},
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "cccd-me.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "birth_proof"},
            {"index": 1, "docType": "birth_proof"},
            {"index": 2, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    return [_file("to-khai.pdf"), _file("chung-sinh.pdf"), _file("cccd-me.pdf")]


async def test_khai_sinh_attach_omits_declaration_for_nghia_lo(monkeypatch):
    """Cờ Nghĩa Lộ: tờ khai khai sinh không được đính, chứng sinh + CCCD vẫn vào STT1."""
    files = _declaration_ocr_and_chat(monkeypatch)
    options = khai_sinh.with_nghia_lo_attach_options(
        {}, {"tinh": "Tỉnh Quảng Ngãi", "xa": "Phường Nghĩa Lộ"}, "khai-sinh-dang-ky"
    )
    res = await khai_sinh.plan_khai_sinh_attachments(files, options, _session())

    assert [it["fileName"] for it in res["attachments"]] == ["chung-sinh.pdf", "cccd-me.pdf"]
    assert res["extracted"]["birthProof"] == "chung-sinh.pdf"
    assert res["extracted"]["omittedDeclarations"] == ["to-khai.pdf"]
    assert res["extracted"]["skipped"] == []
    assert any("to-khai.pdf" in e and "Nghĩa Lộ" in e for e in res["errors"])


async def test_khai_sinh_attach_keeps_declaration_for_other_accounts(monkeypatch):
    """Tài khoản khác: tờ khai vẫn đính như trước (không cờ)."""
    files = _declaration_ocr_and_chat(monkeypatch)
    options = khai_sinh.with_nghia_lo_attach_options(
        {"omitBirthDeclaration": True}, {"tinh": "Tỉnh Lào Cai", "xa": "Phường Nghĩa Lộ"},
        "khai-sinh-dang-ky",
    )
    assert "omitBirthDeclaration" not in options  # client không tự bật được
    res = await khai_sinh.plan_khai_sinh_attachments(files, options, _session())

    assert sorted(it["fileName"] for it in res["attachments"]) == [
        "cccd-me.pdf", "chung-sinh.pdf", "to-khai.pdf",
    ]
    assert res["extracted"]["omittedDeclarations"] == []


def test_nghia_lo_option_only_for_quang_ngai_ward_and_lien_thong():
    ok = {"tinh": "Quảng Ngãi", "xa": "Phường Nghĩa Lộ"}
    assert khai_sinh.with_nghia_lo_attach_options({}, ok, "khai-sinh-dang-ky") == {
        "omitBirthDeclaration": True
    }
    assert khai_sinh.with_nghia_lo_attach_options({}, ok, "khai-sinh-dang-ky-thuong") == {}
    assert not khai_sinh.is_quang_ngai_nghia_lo({"tinh": "Tỉnh Quảng Ngãi", "xa": "Xã Nghĩa Lộc"})
    assert not khai_sinh.is_quang_ngai_nghia_lo(None)
