import json

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.khai_sinh_dang_ky_lai.attach import planner as attachment_dispatcher
from app.pipelines.khai_sinh_dang_ky_lai.attach.dinh_kem_khong_tach import (
    planner as dang_ky_lai_khai_sinh,
)
from app.pipelines.khai_sinh_dang_ky_lai.attach.dinh_kem_tach import planner as split_planner
from app.pipelines.khai_sinh_dang_ky_lai.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as SPLIT_SYSTEM_PROMPT,
)
from app.pipelines.khai_sinh_dang_ky_lai.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_dang_ky_lai_ks_test",
        "procedure": "khai-sinh-dang-ky-lai",
        "fields": [
            {"name": "HoTenKS", "value": "VÀNG A PHỈNH"},
            {"name": "SoDinhDanhCha", "value": "040203015844"},
            {"name": "SoDinhDanhMe", "value": "012193000851"},
        ],
    }


async def test_dang_ky_lai_khai_sinh_attachment_plan_routes_default_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks-ban-sao.pdf", "text": "BẢN SAO GIẤY KHAI SINH"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "birth_certificate_copy", "title": "Giấy khai sinh bản sao"},
                {"index": 1, "type": "personal_supporting_document", "title": "Căn cước công dân"},
                {"index": 2, "type": "authorization", "title": "Văn bản ủy quyền"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("gks-ban-sao.pdf"), _file("cccd.pdf"), _file("uy-quyen.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]
    assert res["extracted"]["attachmentMode"] == "preserve_files"

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Bản sao Giấy khai sinh" in items[0]["componentName"]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 3
    assert "Thẻ căn cước công dân" in items[1]["componentName"]

    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 5
    assert "Văn bản ủy quyền" in items[2]["componentName"]


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_extra_personal_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "hoc-ba.pdf", "text": "HỌC BẠ"},
            {"name": "bang-tot-nghiep.pdf", "text": "BẰNG TỐT NGHIỆP"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "personal_supporting_document", "title": "Căn cước công dân"},
                {"index": 1, "type": "personal_supporting_document", "title": "Học bạ"},
                {"index": 2, "type": "personal_supporting_document", "title": "Bằng tốt nghiệp"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("cccd.pdf"), _file("hoc-ba.pdf"), _file("bang-tot-nghiep.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 3

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["componentName"] == "Học bạ"

    assert items[2]["target"] == "new"
    assert items[2]["componentIndex"] is None
    assert items[2]["componentName"] == "Bằng tốt nghiệp"


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "to-khai-giay.pdf", "text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "paper_declaration", "title": "Tờ khai đăng ký lại khai sinh"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("to-khai-giay.pdf")],
        {},
        _session(),
    )
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["documentName"] == "Tờ khai đăng ký lại khai sinh"
    assert item["componentName"] == "Tờ khai đăng ký lại khai sinh"


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_commitment_statement(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks-ban-sao.pdf", "text": "BẢN SAO GIẤY KHAI SINH"},
            {
                "name": "ban-cam-doan.pdf",
                "text": "BẢN CAM ĐOAN Tôi cam đoan giấy khai sinh bản chính đã bị mất",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "birth_certificate_copy", "title": "Giấy khai sinh bản sao"},
                {"index": 1, "type": "commitment_statement", "title": "Bản cam đoan"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("gks-ban-sao.pdf"), _file("ban-cam-doan.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Bản sao Giấy khai sinh" in items[0]["componentName"]

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["needsAddComponent"] is True
    assert items[1]["documentName"] == "Bản cam đoan"
    assert items[1]["componentName"] == "Bản cam đoan"
    assert items[1]["detectedType"] == "Bản cam đoan"


async def test_dang_ky_lai_khai_sinh_commitment_listing_death_record_is_not_renamed(monkeypatch):
    """Bug: Bản cam đoan LIỆT KÊ 'trích lục khai tử của Cha' trong thân từng bị lưới keyword quét-thân
    đổi tên thành 'Trích lục khai tử'. LLM-first: đã bỏ mọi lưới đè phân loại -> GIỮ NGUYÊN phân loại
    commitment_statement + tên 'Bản cam đoan' mà LLM trả về."""
    async def fake_ocr_per_file(files):
        return [{
            "name": "ban-cam-doan.pdf",
            "text": (
                "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
                "BẢN CAM ĐOAN\n"
                "Tôi xin gửi kèm các giấy tờ có thông tin cá nhân của bản thân, gồm: căn cước công dân "
                "của bản thân, bằng tốt nghiệp Đại học, căn cước công dân của Mẹ, trích lục khai tử của "
                "Cha, xác nhận của nơi công tác.\n"
                "Tôi xin cam đoan nội dung trên là đúng sự thật."
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "commitment_statement", "documentName": "Bản cam đoan"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("ban-cam-doan.pdf")],
        {},
        _session(),
    )
    item = res["attachments"][0]
    classified = res["extracted"]["classified"][0]

    assert item["documentName"] == "Bản cam đoan"
    assert item["documentName"] != "Trích lục khai tử"
    assert item["detectedType"] == "Bản cam đoan"
    # LLM phân loại commitment_statement được GIỮ NGUYÊN, không bị ép về other.
    assert classified["type"] == "commitment_statement"
    assert item["target"] == "new"


def test_dang_ky_lai_khai_sinh_procedure_has_attachment_step():
    proc = get_procedure("khai-sinh-dang-ky-lai")

    assert proc["hasAttachmentStep"] is True
    assert proc["supportsSplitDocuments"] is True


def test_dang_ky_lai_khai_sinh_attachment_prompt_requires_llm_enum():
    assert "commitment_statement" in SYSTEM_PROMPT
    assert "Bản cam đoan" in SYSTEM_PROMPT
    assert '"types":[<allowed_type>]' in SYSTEM_PROMPT
    assert "Chỉ phân loại theo OCR_TEXT" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT
    assert "Trích lục khai tử" in SYSTEM_PROMPT
    assert "KHÔNG phải giấy tờ thay thế" in SYSTEM_PROMPT
    assert "MỖI fileIndex phải có ĐÚNG MỘT kết quả" in SYSTEM_PROMPT
    assert "tuyệt đối không tách trang" in SYSTEM_PROMPT
    assert "Trang trắng" in SYSTEM_PROMPT
    assert '"CCCD HỌ TÊN"' in SYSTEM_PROMPT
    assert '"Hồ sơ đăng ký lại khai sinh"' in SYSTEM_PROMPT
    assert "không lấy tiêu đề của riêng một tài liệu con" in SYSTEM_PROMPT
    assert 'Câu "Tôi cam đoan..." nằm trong Tờ khai' in SYSTEM_PROMPT
    assert "tập fileIndex output phải bằng" in SYSTEM_PROMPT
    assert "không bỏ file và không dịch kết quả sau lên" in SYSTEM_PROMPT
    assert 'documentName "Tài liệu"' in SYSTEM_PROMPT
    assert "Trang tiếp theo của Quyết định ly hôn" in SYSTEM_PROMPT
    assert "Đơn xin xác nhận đăng ký hộ khẩu" in SYSTEM_PROMPT
    assert "Văn bản trả lời cấp bản sao giấy khai sinh" in SYSTEM_PROMPT


async def test_dang_ky_lai_khai_sinh_death_extract_never_uses_birth_component(monkeypatch):
    # LLM-first: prompt buộc Trích lục khai tử là type "other" (không phải birth_certificate_copy).
    # Planner KHÔNG còn lưới keyword đè phân loại; chỉ định tuyến theo type LLM trả -> "other" -> "new".
    async def fake_ocr_per_file(files):
        return [{
            "name": "trich-luc.pdf",
            "text": (
                "THÀNH PHỐ ĐÀ NẴNG\nTRÍCH LỤC KHAI TỬ (BẢN SAO)\n"
                "Họ, chữ đệm, tên: HÀ VĂN SẮT\nĐã chết ngày 02/02/2022"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "type": "other",
                "title": "Trích lục khai tử",
                "documentName": "Trích lục khai tử",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("trich-luc.pdf")],
        {},
        _session(),
    )

    item = res["attachments"][0]
    classified = res["extracted"]["classified"][0]
    assert item["documentName"] == "Trích lục khai tử"
    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["needsAddComponent"] is True
    assert classified["type"] == "other"


def test_dang_ky_lai_khai_sinh_attachment_user_prompt_uses_ocr_text_only():
    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "ban-cam-doan.pdf",
            "text": "BẢN CAM ĐOAN Tôi cam đoan giấy khai sinh bản chính đã bị mất",
        }
    ])

    assert "ocrText" in prompt
    assert "BẢN CAM ĐOAN" in prompt
    assert "FILE_INDEX BẮT BUỘC TRẢ ĐỦ, KHÔNG LỆCH: [0]" in prompt
    assert "ban-cam-doan.pdf" not in prompt
    assert "fileName" not in prompt


async def test_dang_ky_lai_khai_sinh_missing_llm_index_keeps_exact_file_positions(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "to-khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"},
            {"name": "khong-ro.pdf", "text": "Nội dung không xác định"},
            {"name": "cam-doan.pdf", "text": "BẢN CAM ĐOAN"},
        ]

    calls = 0

    async def fake_chat(messages, max_tokens, enable_thinking):
        nonlocal calls
        calls += 1
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "types": ["paper_declaration"],
                    "documentName": "Tờ khai đăng ký lại khai sinh",
                },
                {
                    "fileIndex": 2,
                    "types": ["commitment_statement"],
                    "documentName": "Bản cam đoan",
                },
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("to-khai.pdf"), _file("khong-ro.pdf"), _file("cam-doan.pdf")], {}, _session()
    )

    assert calls == 1
    assert [item["fileIndex"] for item in result["attachments"]] == [0, 1, 2]
    assert [item["documentName"] for item in result["attachments"]] == [
        "Tờ khai đăng ký lại khai sinh",
        "Tài liệu",
        "Bản cam đoan",
    ]


async def test_dang_ky_lai_khai_sinh_ocr_noise_is_not_cccd_back(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ocr-rac.pdf",
            "text": "Đặc điểm nhận dạng: 3D 7cm 12cm 18cm 24cm 30cm 36cm",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "types": ["other"],
                "documentName": "Tài liệu",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("ocr-rac.pdf")], {}, _session()
    )

    item = result["attachments"][0]
    assert item["documentName"] == "Tài liệu"
    assert result["extracted"]["classified"][0]["types"] == ["other"]


async def test_dang_ky_lai_khai_sinh_duplicate_file_names_keep_separate_ocr(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "image.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901",
            },
            {
                "name": "image.pdf",
                "text": "BẢN CAM ĐOAN Tôi cam đoan thông tin đăng ký lại khai sinh là đúng",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        user_prompt = messages[-1]["content"]
        assert "012345678901" in user_prompt
        assert "BẢN CAM ĐOAN" in user_prompt
        assert user_prompt.index("012345678901") < user_prompt.index("BẢN CAM ĐOAN")
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": "Căn cước công dân",
                },
                {
                    "fileIndex": 1,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "commitment_statement",
                    "documentName": "Bản cam đoan",
                },
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, _session()
    )

    assert [item["fileIndex"] for item in result["extracted"]["classified"]] == [0, 1]
    assert result["extracted"]["classified"][0]["type"] == "identity"
    assert result["extracted"]["classified"][1]["type"] == "commitment_statement"
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=1 · image.pdf" in result["ocr_text"]


async def test_dang_ky_lai_khai_sinh_keeps_mixed_pdf_as_one_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ho-so-gop.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901
───── Trang 2/3 ─────
GIẤY KHAI SINH Họ và tên NGUYỄN VĂN A
───── Trang 3/3 ─────
PHẦN GHI CHÚ NHỮNG THÔNG TIN THAY ĐỔI SAU NÀY
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "types": ["identity", "birth_certificate_copy"],
                "documentName": "Căn cước công dân và giấy khai sinh",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("ho-so-gop.pdf")], {}, _session()
    )
    assert len(result["attachments"]) == 1
    item = result["attachments"][0]
    assert item["target"] == "new"
    assert item["documentName"] == "Giấy tờ đăng ký lại khai sinh"
    assert "sourceSegments" not in item
    assert "sourceFileIndexes" not in item
    assert [(item["pageFrom"], item["pageTo"]) for item in result["extracted"]["classified"]] == [(1, 3)]


async def test_dang_ky_lai_khai_sinh_mixed_dossier_rejects_child_document_name(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ho-so-dang-ky-lai.pdf",
            "text": """
───── Trang 1/4 ─────
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
───── Trang 2/4 ─────
BẢN CAM ĐOAN
───── Trang 3/4 ─────
CĂN CƯỚC Số 012345678901 Họ và tên NGUYỄN VĂN A
───── Trang 4/4 ─────
TRÍCH LỤC KHAI TỬ
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "types": ["paper_declaration", "commitment_statement", "identity", "other"],
                "documentName": "Trích lục khai tử",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("ho-so-dang-ky-lai.pdf")], {}, _session()
    )

    item = result["attachments"][0]
    assert item["documentName"] == "Hồ sơ đăng ký lại khai sinh"
    assert item["componentName"] == "Hồ sơ đăng ký lại khai sinh"
    assert item["target"] == "new"
    assert item["needsAddComponent"] is True
    assert result["extracted"]["classified"][0]["documentName"] == "Hồ sơ đăng ký lại khai sinh"


async def test_dang_ky_lai_khai_sinh_keeps_named_single_subject_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "cccd.pdf",
            "text": (
                "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901 "
                "Họ và tên NGUYỄN VĂN A"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "types": ["identity"],
                "documentName": "CCCD NGUYỄN VĂN A",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("cccd.pdf")], {}, _session()
    )

    item = result["attachments"][0]
    assert item["documentName"] == "CCCD NGUYỄN VĂN A"
    assert item["target"] == "existing"
    assert item["componentIndex"] == 3


async def test_dang_ky_lai_khai_sinh_keeps_many_cccds_inside_one_pdf(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ba-cccd.pdf",
            "text": """
───── Trang 1/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037162011511
───── Trang 2/6 ─────
Đặc điểm nhận dạng IDVNM1620115110037162011511
───── Trang 3/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037058009458
───── Trang 4/6 ─────
Đặc điểm nhận dạng IDVNM0580094583037058009458
───── Trang 5/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037091015133
───── Trang 6/6 ─────
Đặc điểm nhận dạng IDVNM0910151335037091015133
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "types": ["identity"],
                "documentName": "Căn cước công dân",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("ba-cccd.pdf")], {}, _session()
    )

    assert len(result["attachments"]) == 1
    item = result["attachments"][0]
    assert item["target"] == "existing"
    assert item["componentIndex"] == 3
    assert item["documentName"] == "Căn cước công dân"
    assert "sourceSegments" not in item
    assert "sourceFileIndexes" not in item


async def test_dang_ky_lai_khai_sinh_keeps_three_uploaded_bundles(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "cccd.pdf",
                "text": """
───── Trang 1/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037162011511
───── Trang 2/6 ─────
Đặc điểm nhận dạng IDVNM1620115110037162011511
───── Trang 3/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037058009458
───── Trang 4/6 ─────
Đặc điểm nhận dạng IDVNM0580094583037058009458
───── Trang 5/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037091015133
───── Trang 6/6 ─────
Đặc điểm nhận dạng IDVNM0910151335037091015133
""",
            },
            {
                "name": "to-khai-cam-doan.pdf",
                "text": """
───── Trang 1/4 ─────
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
───── Trang 2/4 ─────
Chú thích tờ khai
───── Trang 3/4 ─────
GIẤY CAM ĐOAN Tôi xin cam đoan nội dung đăng ký lại khai sinh
───── Trang 4/4 ─────

""",
            },
            {
                "name": "trich-luc-khai-tu.pdf",
                "text": """
───── Trang 1/2 ─────
TRÍCH LỤC KHAI TỬ (BẢN SAO) Đã chết ngày 24 tháng 09 năm 2024
───── Trang 2/2 ─────
TỈNH LAI CHÂU HÀ NỘI TRƯỜNG THPT PHONG NGỌC
""",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "types": ["identity"], "documentName": "Căn cước công dân"},
                {
                    "fileIndex": 1,
                    "types": ["paper_declaration", "commitment_statement"],
                    "documentName": "Tờ khai và bản cam đoan",
                },
                {"fileIndex": 2, "types": ["other"], "documentName": "Trích lục khai tử"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("cccd.pdf"), _file("to-khai-cam-doan.pdf"), _file("trich-luc-khai-tu.pdf")],
        {},
        _session(),
    )

    assert len(result["attachments"]) == 3
    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Tờ khai và bản cam đoan",
        "Trích lục khai tử",
    ]
    assert result["attachments"][0]["componentIndex"] == 3
    assert result["attachments"][1]["target"] == "new"
    assert result["attachments"][2]["target"] == "new"
    assert all("sourceSegments" not in item for item in result["attachments"])
    assert all("sourceFileIndexes" not in item for item in result["attachments"])
    assert [item["pageTo"] for item in result["extracted"]["classified"]] == [6, 4, 2]


async def test_dang_ky_lai_khai_sinh_merges_all_cccds_without_mixing_faces(monkeypatch):
    cccd_a = "012345678901"
    cccd_b = "109876543210"

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": f"Citizen Identity Card Số {cccd_a} Họ và tên NGUYỄN A"},
            {"name": "image.pdf", "text": f"Citizen Identity Card Số {cccd_b} Họ và tên NGUYỄN B"},
            {"name": "image.pdf", "text": f"Đặc điểm nhận dạng IDVNM{cccd_a}"},
            {"name": "image.pdf", "text": f"Đặc điểm nhận dạng IDVNM{cccd_b}"},
        ]

    calls = 0

    async def fake_chat(messages, max_tokens, enable_thinking):
        nonlocal calls
        calls += 1
        return json.dumps({
            "documents": [
                {
                    "fileIndex": index,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": (
                        "CCCD NGUYỄN A" if index == 0 else
                        "CCCD NGUYỄN B" if index == 1 else
                        "Căn cước công dân"
                    ),
                }
                for index in range(4)
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("image.pdf") for _ in range(4)], {}, _session()
    )

    assert calls == 1
    assert len(result["attachments"]) == 2
    first, second = result["attachments"]
    assert first["componentIndex"] == 3
    assert first["documentName"] == "CCCD NGUYỄN A"
    assert first["sourceFileIndexes"] == [0, 2]
    assert "sourceSegments" not in first
    assert second["target"] == "new"
    assert second["documentName"] == "CCCD NGUYỄN B"
    assert second["sourceFileIndexes"] == [1, 3]
    assert "sourceSegments" not in second


async def test_dang_ky_lai_khai_sinh_cccd_has_priority_over_earlier_supporting_document(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "hoc-ba.pdf", "text": "HỌC BẠ Họ tên NGUYỄN VĂN A"},
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "personal_supporting_document",
                    "documentName": "Học bạ",
                },
                {
                    "fileIndex": 1,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": "Căn cước công dân",
                },
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("hoc-ba.pdf"), _file("cccd.pdf")], {}, _session()
    )

    hoc_ba = next(item for item in result["attachments"] if item["documentName"] == "Học bạ")
    cccd = next(item for item in result["attachments"] if item["documentName"] == "Căn cước công dân")
    assert hoc_ba["target"] == "new"
    assert cccd["target"] == "existing"
    assert cccd["componentIndex"] == 3


async def test_dang_ky_lai_khai_sinh_llm_failure_keeps_every_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "Nội dung chưa xác định A"},
            {"name": "image.pdf", "text": "Nội dung chưa xác định B"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, _session()
    )

    assert len(result["attachments"]) == 2
    assert len(result["extracted"]["classified"]) == 2
    assert any("attachment_agent" in error for error in result["errors"])


async def test_dang_ky_lai_khai_sinh_dispatches_split_only_for_boolean_true(monkeypatch):
    calls = []

    async def fake_preserve(files, options, session=None):
        calls.append(("preserve", options))
        return {"mode": "preserve"}

    async def fake_split(files, options, session=None):
        calls.append(("split", options))
        return {"mode": "split"}

    monkeypatch.setattr(attachment_dispatcher, "plan_without_split", fake_preserve)
    monkeypatch.setattr(attachment_dispatcher, "plan_with_split", fake_split)

    assert (await attachment_dispatcher.plan([], None, _session()))["mode"] == "preserve"
    assert (
        await attachment_dispatcher.plan([], {"splitDocuments": False}, _session())
    )["mode"] == "preserve"
    assert (
        await attachment_dispatcher.plan([], {"splitDocuments": "true"}, _session())
    )["mode"] == "preserve"
    assert (
        await attachment_dispatcher.plan([], {"splitDocuments": True}, _session())
    )["mode"] == "split"
    assert [mode for mode, _ in calls] == ["preserve", "preserve", "preserve", "split"]


async def test_dang_ky_lai_khai_sinh_split_documents_and_ignores_blank_page(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ho-so-gop.pdf",
            "text": """
───── Trang 1/4 ─────
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
───── Trang 2/4 ─────
Chú thích của tờ khai
───── Trang 3/4 ─────
GIẤY CAM ĐOAN Tôi xin cam đoan nội dung khai sinh là đúng
───── Trang 4/4 ─────
Làm quen với việc sử dụng các công cụ lập trình khác nhau để tạo ra ứng dụng web.
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 2,
                    "type": "paper_declaration",
                    "documentName": "Tờ khai đăng ký lại khai sinh",
                    "subjectName": "",
                },
                {
                    "fileIndex": 0,
                    "pageFrom": 3,
                    "pageTo": 3,
                    "type": "commitment_statement",
                    "documentName": "Bản cam đoan",
                    "subjectName": "",
                },
                {
                    "fileIndex": 0,
                    "pageFrom": 4,
                    "pageTo": 4,
                    "type": "blank_page",
                    "documentName": "Trang trắng",
                    "subjectName": "",
                },
            ]
        })

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await split_planner.plan([_file("ho-so-gop.pdf")], {}, _session())
    AttachmentPlanResp.model_validate(result)

    assert result["extracted"]["attachmentMode"] == "split_documents"
    assert [item["documentName"] for item in result["attachments"]] == [
        "Tờ khai đăng ký lại khai sinh",
        "Bản cam đoan",
    ]
    assert [item["sourceSegments"][0]["pageIndexes"] for item in result["attachments"]] == [
        [0, 1],
        [2],
    ]
    ignored = next(item for item in result["extracted"]["classified"] if item["type"] == "blank_page")
    assert ignored["target"] == "ignored"


async def test_dang_ky_lai_khai_sinh_split_groups_cccd_faces_per_subject(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ba-cccd.pdf",
            "text": """
───── Trang 1/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037162011511 Họ và tên NGÔ THỊ HỒNG THÊU
───── Trang 2/6 ─────
Đặc điểm nhận dạng IDVNM1620115110037162011511
───── Trang 3/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037058009458 Họ và tên VŨ HUY HOÀN
───── Trang 4/6 ─────
Đặc điểm nhận dạng IDVNM0580094583037058009458
───── Trang 5/6 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 037091015133 Họ và tên VŨ HUY HÒA
───── Trang 6/6 ─────
Đặc điểm nhận dạng IDVNM0910151335037091015133
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        subjects = ["NGÔ THỊ HỒNG THÊU", "VŨ HUY HOÀN", "VŨ HUY HÒA"]
        return json.dumps({
            "documents": [
                segment
                for index, subject in enumerate(subjects)
                for segment in (
                    {
                        "fileIndex": 0,
                        "pageFrom": index * 2 + 1,
                        "pageTo": index * 2 + 1,
                        "type": "identity",
                        "documentName": f"CCCD {subject}",
                        "subjectName": subject,
                    },
                    {
                        "fileIndex": 0,
                        "pageFrom": index * 2 + 2,
                        "pageTo": index * 2 + 2,
                        "type": "identity",
                        "documentName": "Căn cước công dân",
                        "subjectName": "",
                    },
                )
            ]
        })

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await split_planner.plan([_file("ba-cccd.pdf")], {}, _session())
    AttachmentPlanResp.model_validate(result)
    items = result["attachments"]

    assert [item["documentName"] for item in items] == [
        "CCCD NGÔ THỊ HỒNG THÊU",
        "CCCD VŨ HUY HOÀN",
        "CCCD VŨ HUY HÒA",
    ]
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 3
    assert all(item["target"] == "new" for item in items[1:])
    assert [[source["pageIndexes"] for source in item["sourceSegments"]] for item in items] == [
        [[0], [1]],
        [[2], [3]],
        [[4], [5]],
    ]


async def test_dang_ky_lai_khai_sinh_split_death_document_never_uses_birth_row(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "trich-luc.pdf",
            "text": "───── Trang 1/1 ─────\nTRÍCH LỤC KHAI TỬ (BẢN SAO) Đã chết ngày 24/09/2024",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "type": "birth_certificate_copy",
                "documentName": "Trích lục khai tử",
                "subjectName": "",
            }]
        })

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await split_planner.plan([_file("trich-luc.pdf")], {}, _session())
    item = result["attachments"][0]

    assert item["documentName"] == "Trích lục khai tử"
    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert result["extracted"]["classified"][0]["type"] == "death_document"


async def test_dang_ky_lai_khai_sinh_split_title_overrides_mentioned_document_and_false_identity(
    monkeypatch,
):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ho-so-gop.pdf",
            "text": """
───── Trang 1/4 ─────
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
BẢN CAM ĐOAN
Các giấy tờ hiện có: CCCD, Giấy phép lái xe, Trích lục khai tử của cha.
Tôi chịu trách nhiệm trước pháp luật về nội dung đã cam đoan.
───── Trang 2/4 ─────
BỘ GIAO THÔNG VẬN TẢI
GIẤY PHÉP LÁI XE
Họ và tên NGÔ VĂN TIẾN Năm sinh 1968 Quốc tịch Việt Nam
───── Trang 3/4 ─────
CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Họ và tên NGÔ VĂN TIẾN
IDVNM0680063689024068006368
───── Trang 4/4 ─────
TRÍCH LỤC KHAI TỬ
(BẢN SAO)
Đã chết vào lúc 10 giờ 15 phút
Nơi chết: thành phố Bắc Giang
Đã được đăng ký khai tử tại UBND xã Dĩnh Kế
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # Cố tình mô phỏng lỗi thực tế: bám giấy tờ được nhắc trong Bản cam đoan và coi GPLX là CCCD.
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "death_document",
                    "documentName": "Trích lục khai tử",
                    "subjectName": "",
                },
                {
                    "fileIndex": 0,
                    "pageFrom": 2,
                    "pageTo": 2,
                    "type": "identity",
                    "documentName": "CCCD Ngô Văn Tiến",
                    "subjectName": "NGÔ VĂN TIẾN",
                },
                {
                    "fileIndex": 0,
                    "pageFrom": 3,
                    "pageTo": 3,
                    "type": "identity",
                    "documentName": "CCCD Ngô Văn Tiến",
                    "subjectName": "NGÔ VĂN TIẾN",
                },
                {
                    "fileIndex": 0,
                    "pageFrom": 4,
                    "pageTo": 4,
                    "type": "birth_certificate_copy",
                    "documentName": "Trích lục khai tử",
                    "subjectName": "",
                },
            ]
        })

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await split_planner.plan([_file("ho-so-gop.pdf")], {}, _session())

    assert [item["documentName"] for item in result["attachments"]] == [
        "Bản cam đoan",
        "Giấy phép lái xe",
        "CCCD NGÔ VĂN TIẾN",
        "Trích lục khai tử",
    ]
    assert [item["type"] for item in result["extracted"]["classified"]] == [
        "commitment_statement",
        "personal_supporting_document",
        "identity",
        "death_document",
    ]
    cccd = result["attachments"][2]
    assert cccd["target"] == "existing"
    assert cccd["componentIndex"] == 3
    assert "CCCD Ngô Văn Tiến 2" not in {
        item["documentName"] for item in result["attachments"]
    }
    assert "Trích lục khai tử 2" not in {
        item["documentName"] for item in result["attachments"]
    }


def test_dang_ky_lai_khai_sinh_split_prompt_has_page_and_cccd_safety_rules():
    assert "Mỗi trang đầu vào xuất hiện đúng một lần" in SPLIT_SYSTEM_PROMPT
    assert "blank_page" in SPLIT_SYSTEM_PROMPT
    assert "OCR sinh ra một câu/đoạn rời rạc" in SPLIT_SYSTEM_PROMPT
    assert "CCCD của các chủ thể" in SPLIT_SYSTEM_PROMPT
    assert "khác nhau phải là các kết quả khác nhau" in SPLIT_SYSTEM_PROMPT
    assert "death_document" in SPLIT_SYSTEM_PROMPT
    assert "tiêu đề là bằng chứng phân loại cao nhất" in SPLIT_SYSTEM_PROMPT
    assert "không phải là tiêu đề" in SPLIT_SYSTEM_PROMPT
    assert "Tiêu đề thực tế > cấu trúc đặc trưng" in SPLIT_SYSTEM_PROMPT
    assert "\n" in split_planner._truncate_text("BẢN CAM ĐOAN\nTrích lục khai tử của cha")
