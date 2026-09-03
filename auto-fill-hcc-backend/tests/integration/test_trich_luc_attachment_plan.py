import json

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.trich_luc.attach import planner as dispatcher
from app.pipelines.trich_luc.attach.dinh_kem_khong_tach import planner as preserve_planner
from app.pipelines.trich_luc.attach.dinh_kem_khong_tach import prompt as preserve_prompt
from app.pipelines.trich_luc.attach.dinh_kem_tach import planner as trich_luc
from app.pipelines.trich_luc.attach.dinh_kem_tach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure, public_list


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_trich_luc_test",
        "procedure": "trich-luc-ks",
        "fields": [
            {"name": "HoSo_LoaiYeuCau", "value": "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)"},
        ],
    }


async def test_trich_luc_dispatcher_defaults_to_preserve_and_only_true_splits(monkeypatch):
    calls = []

    async def fake_preserve(files, options, session=None):
        calls.append(("preserve", options, session))
        return {"branch": "preserve"}

    async def fake_split(files, options, session=None):
        calls.append(("split", options, session))
        return {"branch": "split"}

    monkeypatch.setattr(dispatcher, "plan_without_split", fake_preserve)
    monkeypatch.setattr(dispatcher, "plan_with_split", fake_split)

    assert (await dispatcher.plan_trich_luc_attachments([], None, _session()))["branch"] == "preserve"
    assert (await dispatcher.plan_trich_luc_attachments([], {"splitDocuments": False}, _session()))["branch"] == "preserve"
    assert (await dispatcher.plan_trich_luc_attachments([], {"splitDocuments": True}, _session()))["branch"] == "split"
    assert [call[0] for call in calls] == ["preserve", "preserve", "split"]


async def test_trich_luc_preserve_keeps_mixed_file_and_uses_bundle_name(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/4 ─────\nTỜ KHAI YÊU CẦU CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH\n"
                "───── Trang 2/4 ─────\nCHÚ THÍCH\nGhi số căn cước công dân nếu có\n"
                "───── Trang 3/4 ─────\nCĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\n"
                "───── Trang 4/4 ─────\nGIẤY KHAI SINH"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # Tái hiện LLM chỉ nhìn trang đầu; planner vẫn phải nhận ra đây là nguyên bộ hồ sơ.
        return json.dumps({
            "documents": [{
                "fileIndex": 0, "type": "paper_declaration", "documentName": "Tờ khai bản giấy",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await preserve_planner.plan_trich_luc_attachments_without_split(
        [_file("mixed.pdf")], {}, _session(),
    )
    AttachmentPlanResp.model_validate(result)

    assert result["extracted"]["attachmentMode"] == "preserve_files"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Hồ sơ trích lục hộ tịch"
    assert result["attachments"][0]["target"] == "new"
    assert "sourceSegments" not in result["attachments"][0]
    assert result["extracted"]["classified"][0]["type"] == "other"


async def test_trich_luc_preserve_single_cccd_uses_subject_name(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 024188001759"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0, "type": "identity", "documentName": "Căn cước công dân",
                "subjectName": "NGUYỄN VĂN A",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await preserve_planner.plan_trich_luc_attachments_without_split(
        [_file("cccd.pdf")], {}, _session(),
    )

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "CCCD NGUYỄN VĂN A"
    assert result["attachments"][0]["componentIndex"] == 3
    assert "sourceSegments" not in result["attachments"][0]


async def test_trich_luc_preserve_multiple_cccds_in_one_file_stays_one_generic_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "cccds.pdf",
            "text": (
                "───── Trang 1/2 ─────\nCĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 024188001759\n"
                "───── Trang 2/2 ─────\nCĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 068190002468"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0, "type": "identity", "documentName": "Căn cước công dân",
                "subjectName": "",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await preserve_planner.plan_trich_luc_attachments_without_split(
        [_file("cccds.pdf")], {}, _session(),
    )

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Căn cước công dân"
    assert result["attachments"][0]["componentIndex"] == 3


async def test_trich_luc_attachment_plan_routes_civil_status_documents_to_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks.pdf", "text": "GIẤY KHAI SINH"},
            {"name": "ket-hon.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN"},
            {"name": "khai-tu.pdf", "text": "TRÍCH LỤC KHAI TỬ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "civil_status_birth", "title": "Giấy khai sinh"},
                {"index": 1, "type": "civil_status_marriage", "title": "Giấy chứng nhận kết hôn"},
                {"index": 2, "type": "civil_status_death", "title": "Trích lục khai tử"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    res = await trich_luc.plan_trich_luc_attachments(
        [_file("gks.pdf"), _file("ket-hon.pdf"), _file("khai-tu.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "new"
    assert items[0]["componentName"] == "Giấy khai sinh"
    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Giấy đăng ký kết hôn"
    assert items[1]["documentName"] == "Giấy đăng ký kết hôn"
    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Trích lục khai tử"


async def test_trich_luc_attachment_plan_routes_default_existing_rows(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "cu-tru.pdf", "text": "GIẤY XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "authorization", "title": "Văn bản ủy quyền"},
                {"index": 1, "type": "identity", "title": "Căn cước công dân"},
                {"index": 2, "type": "residence_proof", "title": "Giấy tờ chứng minh cư trú"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    res = await trich_luc.plan_trich_luc_attachments(
        [_file("uy-quyen.pdf"), _file("cccd.pdf"), _file("cu-tru.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Văn bản ủy quyền" in items[0]["componentName"]
    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 3
    assert "Thẻ căn cước công dân" in items[1]["componentName"]
    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 4
    assert "chứng minh thông tin về cư trú" in items[2]["componentName"]


async def test_trich_luc_duplicate_names_keep_ocr_by_file_index_and_use_one_llm_call(monkeypatch):
    calls = []

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "GIẤY KHAI SINH A"},
            {"name": "image.pdf", "text": "TRÍCH LỤC KHAI TỬ B"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        user_prompt = messages[1]["content"]
        assert "GIẤY KHAI SINH A" in user_prompt
        assert "TRÍCH LỤC KHAI TỬ B" in user_prompt
        assert '"fileIndex": 0' in user_prompt
        assert '"fileIndex": 1' in user_prompt
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "civil_status_birth"},
                {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "civil_status_death"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    result = await trich_luc.plan_trich_luc_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, _session()
    )

    assert len(calls) == 1
    assert [item["documentName"] for item in result["attachments"]] == ["Giấy khai sinh", "Trích lục khai tử"]
    assert [item["fileIndex"] for item in result["extracted"]["classified"]] == [0, 1]
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=1 · image.pdf" in result["ocr_text"]


async def test_trich_luc_splits_mixed_pdf_by_page_ranges(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/3 ─────\nCĂN CƯỚC CÔNG DÂN\nSố: 024188001759\n"
                "───── Trang 2/3 ─────\nGIẤY KHAI SINH\nTẠ HOÀNG NHÃ UYÊN\n"
                "───── Trang 3/3 ─────\nPHẦN GHI CHÚ NHỮNG THÔNG TIN THAY ĐỔI"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
                {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "civil_status_birth"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    result = await trich_luc.plan_trich_luc_attachments([_file("mixed.pdf")], {}, _session())
    serialized = AttachmentPlanResp.model_validate(result).model_dump(mode="json")
    assert serialized["attachments"][0]["sourceSegments"][0]["pageIndexes"] == [0]
    identity, birth = result["attachments"]

    assert identity["componentIndex"] == 3
    assert identity["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert birth["target"] == "new"
    assert birth["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]
    assert [(item["pageFrom"], item["pageTo"]) for item in result["extracted"]["classified"]] == [(1, 1), (2, 3)]


async def test_trich_luc_merges_every_identity_into_row_three_in_person_face_order(monkeypatch):
    texts = [
        "Đặc điểm nhận dạng IDVNM024188001759 CỤC TRƯỞNG CỤC CẢNH SÁT",
        "CĂN CƯỚC CÔNG DÂN Citizen Identity Số 024188001759 Họ và tên NGUYỄN A",
        "Đặc điểm nhận dạng IDVNM068190002468 CỤC TRƯỞNG CỤC CẢNH SÁT",
        "CĂN CƯỚC CÔNG DÂN Citizen Identity Số 068190002468 Họ và tên NGUYỄN B",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file.name if hasattr(file, "name") else file.get("name"), "text": text}
                for file, text in zip(files, texts)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": index, "pageFrom": 1, "pageTo": 1, "type": "identity",
                    "subjectName": "NGUYỄN A" if index == 1 else "NGUYỄN B" if index == 3 else "",
                }
                for index in range(4)
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    result = await trich_luc.plan_trich_luc_attachments(
        [_file(f"cccd-{index}.pdf") for index in range(4)], {}, _session()
    )

    assert len(result["attachments"]) == 2
    first, second = result["attachments"]
    assert first["componentIndex"] == 3
    assert first["documentName"] == "CCCD NGUYỄN A"
    assert [segment["fileIndex"] for segment in first["sourceSegments"]] == [1, 0]
    assert second["target"] == "new"
    assert second["documentName"] == "CCCD NGUYỄN B"
    assert [segment["fileIndex"] for segment in second["sourceSegments"]] == [3, 2]
    assert len(result["extracted"]["classified"]) == 4


async def test_trich_luc_split_discards_blank_pages(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "birth.pdf",
            "text": "───── Trang 1/2 ─────\nGIẤY KHAI SINH\n───── Trang 2/2 ─────\n",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "civil_status_birth"},
                {
                    "fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "blank_page",
                    "documentName": "Trang trắng",
                },
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    result = await trich_luc.plan_trich_luc_attachments([_file("birth.pdf")], {}, _session())

    assert result["extracted"]["attachmentMode"] == "split_documents"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Giấy khai sinh"
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert result["extracted"]["classified"][1]["target"] == "ignored"


async def test_trich_luc_does_not_block_split_for_pdf_signature_flags(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "signed.pdf",
            "text": "───── Trang 1/2 ─────\nCĂN CƯỚC CÔNG DÂN\n───── Trang 2/2 ─────\nGIẤY KHAI SINH",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
                {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "civil_status_birth"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)
    monkeypatch.setattr(trich_luc, "_pdf_page_count", lambda file: 2)

    result = await trich_luc.plan_trich_luc_attachments([_file("signed.pdf")], {}, _session())

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert result["attachments"][1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    assert not any("chữ ký số" in error for error in result["errors"])


def test_trich_luc_procedure_has_attachment_step():
    proc = get_procedure("trich-luc-ks")

    assert proc["hasAttachmentStep"] is True
    assert proc["supportsSplitDocuments"] is True
    assert "Trích lục hộ tịch" in proc["label"]


def test_registry_does_not_expose_nonexistent_death_extract_procedure():
    removed_key = "trich-luc-khai-tu"
    assert get_procedure(removed_key) is None
    assert get_pipeline(removed_key) is None
    assert get_attach_pipeline(removed_key) is None
    assert removed_key not in {item["key"] for item in public_list()}


def test_trich_luc_attachment_prompt_uses_ocr_text_only():
    assert "civil_status_marriage" in SYSTEM_PROMPT
    assert "identity" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "chung-nhan-ket-hon.pdf",
            "text": "GIẤY CHỨNG NHẬN KẾT HÔN",
        }
    ])

    assert "ocrText" in prompt
    assert "GIẤY CHỨNG NHẬN KẾT HÔN" in prompt
    assert "chung-nhan-ket-hon.pdf" not in prompt
    assert "fileName" not in prompt

    assert "Hồ sơ trích lục hộ tịch" in preserve_prompt.SYSTEM_PROMPT
    assert "GIỐNG HỆT tập fileIndex đầu vào" in preserve_prompt.SYSTEM_PROMPT
    assert "không mượn loại, tên hoặc chủ thể" in preserve_prompt.SYSTEM_PROMPT
    assert "danh sách giấy tờ được kể" in preserve_prompt.SYSTEM_PROMPT
    assert 'Riêng cụm\n   "Đặc điểm nhận dạng" không đủ' in preserve_prompt.SYSTEM_PROMPT
    assert "Tài liệu trích lục hộ tịch" == preserve_planner._OTHER_LABEL

    preserve_user_prompt = preserve_prompt.build_user_prompt([
        {"fileIndex": 4, "ocrText": "TỜ KHAI YÊU CẦU CẤP BẢN SAO"},
        {"fileIndex": 7, "ocrText": "CĂN CƯỚC CÔNG DÂN"},
    ])
    assert "FILE_INDEX BẮT BUỘC: [4, 7]" in preserve_user_prompt

    split_user_prompt = build_user_prompt([
        {
            "fileIndex": 4,
            "pageCount": 2,
            "pageBoundariesAvailable": True,
            "pages": [
                {"pageNumber": 1, "ocrText": "QUYẾT ĐỊNH"},
                {"pageNumber": 2, "ocrText": "Trang tiếp theo"},
            ],
        },
    ])
    assert 'FILE_INDEX VÀ TRANG BẮT BUỘC: [{"fileIndex": 4, "pages": [1, 2]}]' in split_user_prompt
    assert "không mượn" in SYSTEM_PROMPT
    assert "trang nội dung tiếp nối" in SYSTEM_PROMPT
    assert "KHÔNG tạo thành tài liệu mới" in SYSTEM_PROMPT
    assert "Riêng cụm 'Đặc điểm nhận dạng' không đủ" in SYSTEM_PROMPT


def test_trich_luc_preserve_identity_fallback_requires_strong_back_evidence():
    assert preserve_planner._has_identity_evidence("Đặc điểm nhận dạng: sẹo nhỏ") is False
    assert preserve_planner._rule_doc_type("Đặc điểm nhận dạng: sẹo nhỏ") == "other"

    assert preserve_planner._has_identity_evidence(
        "Đặc điểm nhận dạng; Ngón trỏ trái; CỤC TRƯỞNG CỤC CẢNH SÁT"
    ) is True
    assert preserve_planner._rule_doc_type(
        "Đặc điểm nhận dạng; Ngón trỏ trái; CỤC TRƯỞNG CỤC CẢNH SÁT"
    ) == "identity"
    assert preserve_planner._has_identity_evidence("IDVNM0680063689") is True


def test_trich_luc_preserve_declaration_reference_is_not_an_independent_document():
    text = (
        "TỜ KHAI YÊU CẦU CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH\n"
        "Giấy tờ tùy thân: Căn cước công dân số 012345678901\n"
        "Kèm theo nếu có: giấy khai sinh, trích lục kết hôn"
    )

    assert preserve_planner._rule_doc_type(text) == "paper_declaration"
    assert preserve_planner._is_mixed_bundle(text) is False
