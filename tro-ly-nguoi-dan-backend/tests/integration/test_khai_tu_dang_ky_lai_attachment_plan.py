import json

from app.pipelines.khai_tu_dang_ky_lai.attach import planner
from app.pipelines.khai_tu_dang_ky_lai.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_khai_tu_dang_ky_lai_attach",
        "procedure": "khai-tu-dang-ky-lai",
        "fields": [
            {"name": "HoVaTenC", "value": "TRỊNH THU HÀ"},
            {"name": "HoTen", "value": "TRỊNH THỊ ÉN"},
        ],
    }


async def test_khai_tu_dang_ky_lai_attach_routes_fixed_rows_and_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "to-khai.pdf",
                "text": (
                    "TỜ KHAI ĐĂNG KÝ LẠI KHAI TỬ\n"
                    "Đã chết vào lúc: giờ phút, ngày 27 tháng 4 năm 2008\n"
                    "Giấy chứng tử/Trích lục khai tử số: , quyển số:"
                ),
            },
            {
                "name": "lang-mo.pdf",
                "text": "LĂNG MỘ BÀ TRỊNH THỊ ÉN SINH NĂM 1945 TẠ THẾ 22-03-MẬU TÝ 2008",
            },
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012197004527"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN thực hiện đăng ký lại khai tử"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [_file("to-khai.pdf"), _file("lang-mo.pdf"), _file("cccd.pdf"), _file("uy-quyen.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "new"
    assert items[0]["componentName"] == "Tờ khai bản giấy"

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert "Giấy chứng tử trước đây" in items[1]["componentName"]

    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Căn cước công dân"

    assert items[3]["target"] == "existing"
    assert items[3]["componentIndex"] == 3
    assert "Văn bản ủy quyền" in items[3]["componentName"]


async def test_khai_tu_dang_ky_lai_attach_combined_file_with_death_info_goes_to_row_2(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "ho-so-gop.pdf",
                "text": (
                    "CĂN CƯỚC CÔNG DÂN Số / No.: 012197004527\n"
                    "LĂNG MỘ BÀ TRỊNH THỊ ÉN SINH NĂM 1945 TẠ THẾ 2008"
                ),
            }
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "identity", "documentName": "Căn cước công dân"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("ho-so-gop.pdf")], {}, _session())
    item = res["attachments"][0]

    assert item["target"] == "existing"
    assert item["componentIndex"] == 2
    assert item["needsAddComponent"] is False


def test_khai_tu_dang_ky_lai_registry_has_attachment_pipeline():
    proc = get_procedure("khai-tu-dang-ky-lai")

    assert proc["hasAttachmentStep"] is True
    assert get_attach_pipeline("khai-tu-dang-ky-lai") is not None


def test_khai_tu_dang_ky_lai_attachment_prompt_contract():
    assert "death_proof" in SYSTEM_PROMPT
    assert "LĂNG MỘ" in SYSTEM_PROMPT
    assert "Tờ khai đăng ký lại khai tử bản giấy vẫn là paper_declaration" in SYSTEM_PROMPT
    assert "ủy quyền" in SYSTEM_PROMPT
    assert "authorization" in SYSTEM_PROMPT
    assert "component \"Giấy tờ khác\"" in SYSTEM_PROMPT
    assert "STT 1" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([{"index": 0, "fileName": "lang-mo.pdf", "text": "LĂNG MỘ"}])
    assert "ocrText" in user_prompt
    assert "LĂNG MỘ" in user_prompt
    assert "fileName" not in user_prompt
    assert "lang-mo.pdf" not in user_prompt
