import json

from app.pipelines.chung_thuc_phan_chia_di_san.attach import planner
from app.pipelines.chung_thuc_phan_chia_di_san.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_phan_chia_di_san_attachment_plan_groups_row1_and_routes_draft(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "so-do.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nThửa đất số 12"},
            {"name": "trich-luc-khai-tu.pdf", "text": "TRÍCH LỤC KHAI TỬ\nNgười chết: Nguyễn Văn A"},
            {
                "name": "thoa-thuan.pdf",
                "text": "VĂN BẢN THỎA THUẬN PHÂN CHIA DI SẢN THỪA KẾ",
            },
            {"name": "do-dac.pdf", "text": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 040203015844"},
            {"name": "du-thao.pdf", "text": "DỰ THẢO VĂN BẢN PHÂN CHIA DI SẢN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [
            _file("so-do.pdf"),
            _file("trich-luc-khai-tu.pdf"),
            _file("thoa-thuan.pdf"),
            _file("do-dac.pdf"),
            _file("cccd.pdf"),
            _file("du-thao.pdf"),
        ],
        {},
        None,
    )
    items = res["attachments"]

    assert len(items) == 2
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert "giấy chứng nhận quyền sở hữu, quyền sử dụng" in items[0]["componentName"]
    assert items[0]["documentName"] == "Giấy tờ kèm theo hồ sơ phân chia di sản"
    assert items[0]["sourceFileIndexes"] == [0, 1, 3, 4]
    assert items[0]["needsAddComponent"] is False

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert items[1]["componentName"] == "Dự thảo văn bản phân chia di sản"
    assert items[1]["documentName"] == "Dự thảo văn bản phân chia di sản"
    assert items[1]["sourceFileIndexes"] == [2, 5]
    assert items[1]["needsAddComponent"] is False


async def test_phan_chia_di_san_multiple_drafts_merge_into_row2(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "du-thao-1.pdf", "text": "DỰ THẢO VĂN BẢN PHÂN CHIA DI SẢN trang 1"},
            {"name": "du-thao-2.pdf", "text": "VĂN BẢN PHÂN CHIA DI SẢN trang 2"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("du-thao-1.pdf"), _file("du-thao-2.pdf")], {}, None)
    items = res["attachments"]

    assert len(items) == 1
    assert items[0]["componentIndex"] == 2
    assert items[0]["sourceFileIndexes"] == [0, 1]


async def test_phan_chia_di_san_draft_thoa_thuan_stays_on_row2(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "du-thao-thoa-thuan.pdf",
                "text": "DỰ THẢO VĂN BẢN THỎA THUẬN PHÂN CHIA DI SẢN",
            }
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "index": 0,
                    "type": "inheritance_agreement",
                    "title": "Văn bản thỏa thuận phân chia di sản thừa kế",
                }
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("du-thao-thoa-thuan.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["componentIndex"] == 2
    assert item["componentName"] == "Dự thảo văn bản phân chia di sản"
    assert item["sourceFileIndexes"] == [0]
    assert res["extracted"]["classified"][0]["type"] == "division_draft"


async def test_phan_chia_di_san_thoa_thuan_goes_to_row2(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "thoa-thuan.pdf",
                "text": (
                    "VĂN BẢN THỎA THUẬN PHÂN CHIA DI SẢN THỪA KẾ\n"
                    "Theo thông tin trích lục khai tử số 37/2025/TLKT.\n"
                    "Theo Giấy chứng nhận quyền sử dụng đất số BC 466500.\n"
                    "Bà Lù Thị Khen, CCCD số 012173002914."
                ),
            }
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{"index": 0, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"}]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("thoa-thuan.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["componentIndex"] == 2
    assert item["sourceFileIndexes"] == [0]
    assert res["extracted"]["classified"][0]["type"] == "division_draft"
    assert res["extracted"]["classified"][0]["source"] == "rule"


async def test_phan_chia_di_san_unknown_document_is_skipped(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "phieu-hen.pdf", "text": "PHIẾU HẸN TRẢ KẾT QUẢ"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": "Phiếu hẹn"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("phieu-hen.pdf")], {}, None)

    assert res["attachments"] == []
    assert any("đã bỏ qua" in err for err in res["errors"])


def test_phan_chia_di_san_procedure_is_attach_only():
    proc = get_procedure("chung-thuc-phan-chia-di-san")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert proc["detect"]["textPriority"] is True
    assert "không thêm dòng mới" in proc["uploadHint"]
    assert "Dự thảo/văn bản thỏa thuận phân chia di sản thừa kế" in proc["uploadHint"]
    assert get_pipeline("chung-thuc-phan-chia-di-san") is None
    assert get_attach_pipeline("chung-thuc-phan-chia-di-san") is not None


def test_phan_chia_di_san_prompt_uses_ocr_text_only():
    assert "division_draft" in SYSTEM_PROMPT
    assert "death_proof" in SYSTEM_PROMPT
    assert "inheritance_agreement" in SYSTEM_PROMPT
    assert "Dòng 1 nhận và gộp chung" in SYSTEM_PROMPT
    assert "Dòng 2 nhận dự thảo" in SYSTEM_PROMPT
    assert "VĂN BẢN THỎA THUẬN PHÂN CHIA DI SẢN THỪA KẾ" in SYSTEM_PROMPT
    assert "DỰ THẢO\" + \"PHÂN CHIA DI SẢN" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "du-thao.pdf",
            "text": "DỰ THẢO VĂN BẢN PHÂN CHIA DI SẢN",
        }
    ])

    assert "ocrText" in prompt
    assert "DỰ THẢO VĂN BẢN PHÂN CHIA DI SẢN" in prompt
    assert "du-thao.pdf" not in prompt
    assert "fileName" not in prompt
