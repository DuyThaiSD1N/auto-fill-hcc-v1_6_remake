import json

from app.pipelines.nhan_cha_me_con.attach import planner
from app.pipelines.nhan_cha_me_con.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_nhan_cha_me_con_attach",
        "procedure": "dang-ky-nhan-cha-me-con",
        "fields": [
            {"name": "Requester_FullName", "value": "ĐÈO NGỌC HIẾU"},
            {"name": "Parent_FullName", "value": "ĐÈO NGỌC HIẾU"},
            {"name": "Child_FullName", "value": "VŨ HẠ MY AN"},
        ],
    }


async def test_nhan_cha_me_con_attachment_routes_adn_and_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "adn-gcs-cccd.pdf": (
                "KẾT QUẢ XÉT NGHIỆM ADN\n"
                "ĐÈO NGỌC HIẾU có quan hệ huyết thống bố - con với VŨ MY AN; độ tin cậy > 99,9999%.\n"
                "CĂN CƯỚC CÔNG DÂN Số / No.: 012098005476\n"
                "GIẤY CHỨNG SINH Mã số GCS: 02020.GCS.12096.25"
            ),
            "to-khai.pdf": (
                "TỜ KHAI ĐĂNG KÝ NHẬN CHA, MẸ, CON\n"
                "Quan hệ với người nhận cha/mẹ/con: Bố\n"
                "Tôi cam đoan việc nhận cha con nói trên là đúng sự thật"
            ),
            "cccd-rieng.pdf": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012098005476\nIDVNM098005476",
            "cam-doan.pdf": "VĂN BẢN CAM ĐOAN việc nhận cha con và có người làm chứng",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "gemini"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "identity", "documentName": "Căn cước công dân"},
                {"index": 1, "docType": "other", "documentName": "Tài liệu khác"},
                {"index": 2, "docType": "other", "documentName": "Tài liệu khác"},
                {"index": 3, "docType": "witness_commitment", "documentName": "Văn bản cam đoan"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [_file("adn-gcs-cccd.pdf"), _file("to-khai.pdf"), _file("cccd-rieng.pdf"), _file("cam-doan.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert [item["fileName"] for item in items] == ["adn-gcs-cccd.pdf", "to-khai.pdf", "cccd-rieng.pdf"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "cơ quan y tế" in items[0]["componentName"]
    assert items[0]["documentName"] == "Kết quả xét nghiệm ADN"

    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Tờ khai đăng ký nhận cha mẹ con bản giấy"

    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Căn cước công dân"

    assert any(
        entry["fileName"] == "cam-doan.pdf"
        and entry["docType"] == "witness_commitment"
        and entry["target"] == "skip"
        and entry.get("reason") == "relationship_proof_present"
        for entry in res["extracted"]["classified"]
    )
    assert not res["errors"]


async def test_nhan_cha_me_con_attachment_uses_commitment_when_no_adn(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "cam-doan.pdf": "VĂN BẢN CAM ĐOAN của các bên nhận cha, mẹ, con và hai người làm chứng về mối quan hệ.",
            "giay-chung-sinh.pdf": "GIẤY CHỨNG SINH\nMã số GCS: 02020.GCS.12096.25\nDự định đặt tên con là Vũ My An",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "gemini"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("cam-doan.pdf"), _file("giay-chung-sinh.pdf")], {}, _session())
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 3
    assert "văn bản cam đoan" in items[0]["componentName"].lower()

    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Giấy chứng sinh"


async def test_nhan_cha_me_con_attachment_new_identity_card_not_birth_document(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "the-can-cuoc.pdf",
            "text": (
                "CĂN CƯỚC\n"
                "Số định danh cá nhân / Personal identification number: 025085013037\n"
                "Họ, chữ đệm và tên khai sinh / Full name: TRẦN THANH BÌNH\n"
                "Ngày, tháng, năm sinh / Date of birth: 16/11/1985"
            ),
            "provider": "gemini",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("the-can-cuoc.pdf")], {}, _session())
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentName"] == "Căn cước công dân"
    assert res["extracted"]["classified"][0]["docType"] == "identity"


def test_nhan_cha_me_con_attachment_registry():
    proc = get_procedure("dang-ky-nhan-cha-me-con")

    assert proc["hasAttachmentStep"] is True
    assert get_attach_pipeline("dang-ky-nhan-cha-me-con") is not None


def test_nhan_cha_me_con_attachment_prompt_contract():
    assert "relationship_proof" in SYSTEM_PROMPT
    assert "witness_commitment" in SYSTEM_PROMPT
    assert "STT 1" in SYSTEM_PROMPT
    assert "KẾT QUẢ XÉT NGHIỆM ADN" in SYSTEM_PROMPT
    assert "Tờ khai đăng ký nhận cha, mẹ, con bản giấy là paper_declaration" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([{"index": 0, "fileName": "adn.pdf", "text": "KẾT QUẢ XÉT NGHIỆM ADN"}])
    assert "ocrText" in user_prompt
    assert "KẾT QUẢ XÉT NGHIỆM ADN" in user_prompt
    assert "fileName" not in user_prompt
    assert "adn.pdf" not in user_prompt
