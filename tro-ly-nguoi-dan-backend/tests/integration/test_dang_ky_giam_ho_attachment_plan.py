import json

from app.pipelines.dang_ky_giam_ho.attach import planner
from app.pipelines.dang_ky_giam_ho.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_dang_ky_giam_ho_attach",
        "procedure": "dang-ky-giam-ho",
        "fields": [
            {"name": "Requester_FullName", "value": "CHÈO TON SƠN"},
            {"name": "Guardian_FullName", "value": "HOÀNG A TOAN"},
            {"name": "Ward_FullName", "value": "CHẺO THÙY MY"},
        ],
    }


async def test_dang_ky_giam_ho_attachment_routes_rows_and_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "to-khai.pdf": "TỜ KHAI ĐĂNG KÝ GIÁM HỘ\nNgười giám hộ: HOÀNG A TOAN",
            "van-ban-cu.pdf": "VĂN BẢN THỎA THUẬN CỬ NGƯỜI GIÁM HỘ\nCử người có tên dưới đây làm người giám hộ",
            "ban-cam-doan.pdf": "BẢN CAM ĐOAN\nTôi có năng lực hành vi dân sự đầy đủ và có nhà riêng",
            "so-do.pdf": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nThửa đất số 45",
            "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012081000601\nIDVNM081000601",
            "uy-quyen.pdf": "VĂN BẢN ỦY QUYỀN thực hiện việc đăng ký giám hộ",
            "hon-nhan.pdf": "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nHọ tên: LÊ HUY CẬN",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "gemini"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [
            _file("to-khai.pdf"),
            _file("van-ban-cu.pdf"),
            _file("ban-cam-doan.pdf"),
            _file("so-do.pdf"),
            _file("cccd.pdf"),
            _file("uy-quyen.pdf"),
            _file("hon-nhan.pdf"),
        ],
        {},
        _session(),
    )
    items = res["attachments"]

    assert [item["fileName"] for item in items] == [
        "to-khai.pdf",
        "van-ban-cu.pdf",
        "ban-cam-doan.pdf",
        "uy-quyen.pdf",
    ]

    assert items[0]["target"] == "new"
    assert items[0]["componentName"] == "Tờ khai đăng ký giám hộ bản giấy"

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert "Văn bản cử người giám hộ" in items[1]["componentName"]

    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 3
    assert items[2]["sourceFileIndexes"] == [2, 3, 4]
    assert "Giấy tờ chứng minh điều kiện giám hộ" in items[2]["componentName"]

    assert items[3]["target"] == "existing"
    assert items[3]["componentIndex"] == 4
    assert "Văn bản ủy quyền" in items[3]["componentName"]
    assert any(entry["fileName"] == "hon-nhan.pdf" and entry["docType"] == "skip" for entry in res["extracted"]["classified"])
    assert all(
        entry.get("mergedIntoFileIndex") == 2
        for entry in res["extracted"]["classified"]
        if entry["fileName"] in {"ban-cam-doan.pdf", "so-do.pdf", "cccd.pdf"}
    )
    assert not res["errors"]


async def test_dang_ky_giam_ho_attachment_puts_all_identity_files_to_row_3(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-nguoi-yeu-cau.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số / No.: 012099002088"},
            {"name": "cccd-than-nhan.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số / No.: 012177003172"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "skip", "documentName": "Không liên quan"},
                {"index": 1, "docType": "other", "documentName": "Tài liệu khác"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("cccd-nguoi-yeu-cau.pdf"), _file("cccd-than-nhan.pdf")], {}, _session())
    items = res["attachments"]

    assert len(items) == 1
    assert items[0]["sourceFileIndexes"] == [0, 1]
    assert {item["componentIndex"] for item in items} == {3}
    assert all(item["target"] == "existing" for item in items)
    assert items[0]["documentName"] == "Giấy tờ chứng minh điều kiện giám hộ"


def test_dang_ky_giam_ho_attachment_registry():
    proc = get_procedure("dang-ky-giam-ho")

    assert proc["hasAttachmentStep"] is True
    assert get_attach_pipeline("dang-ky-giam-ho") is not None


def test_dang_ky_giam_ho_attachment_prompt_contract():
    assert "guardian_appointment" in SYSTEM_PROMPT
    assert "guardian_condition" in SYSTEM_PROMPT
    assert "Tờ khai đăng ký giám hộ bản giấy vẫn là paper_declaration" in SYSTEM_PROMPT
    assert "Mọi CCCD/CMND/căn cước/hộ chiếu" in SYSTEM_PROMPT
    assert "STT 1" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([{"index": 0, "fileName": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}])
    assert "ocrText" in user_prompt
    assert "CĂN CƯỚC CÔNG DÂN" in user_prompt
    assert "fileName" not in user_prompt
    assert "cccd.pdf" not in user_prompt
