import json

from app.pipelines.ket_hon_lai.attach import planner as ket_hon_lai
from app.process.schemas import FileItem
from app.services import ocr


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_test",
        "procedure": "dang-ky-lai-ket-hon",
        "fields": [
            {"name": "SoDinhDanh_BenNam", "value": "012086005221"},
            {"name": "SoDinhDanh_BenNu", "value": "012189003303"},
        ],
    }


async def test_ket_hon_lai_attachment_plan_uses_existing_certificate_slot(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN Số: 40/2026"},
            {"name": "nam.pdf", "text": "CĂN CƯỚC CÔNG DÂN Giới tính Sex Nam 012086005221"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "marriage_certificate"},
            {"index": 1, "type": "identity", "side": "nam", "face": "ca_hai"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_lai.client, "chat", fake_chat)

    res = await ket_hon_lai.plan_ket_hon_lai_attachments(
        [_file("gcn.pdf"), _file("nam.pdf")],
        {},
        _session(),
    )

    cert, cccd = res["attachments"]
    assert cert["target"] == "existing"
    assert cert["componentIndex"] == 2
    assert cert["componentName"] == "Bản sao Giấy chứng nhận kết hôn"
    assert cccd["target"] == "new"
    assert cccd["componentName"] == "CCCD bên nam"


async def test_ket_hon_lai_keeps_two_identity_subjects_separate(monkeypatch):
    texts = [
        "CĂN CƯỚC CÔNG DÂN Số: 012086005221 Giới tính Nam",
        "Đặc điểm nhận dạng IDVNM0860052210012086005221<<1",
        "CĂN CƯỚC CÔNG DÂN Số: 012189003303 Giới tính Nữ",
        "Đặc điểm nhận dạng IDVNM1890033030012189003303<<2",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": text} for file, text in zip(files, texts)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "identity", "side": "nam", "face": "truoc"},
            {"index": 1, "type": "identity", "side": "nam", "face": "sau"},
            {"index": 2, "type": "identity", "side": "nu", "face": "truoc"},
            {"index": 3, "type": "identity", "side": "nu", "face": "sau"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_lai.client, "chat", fake_chat)

    result = await ket_hon_lai.plan_ket_hon_lai_attachments(
        [_file("nam-truoc.pdf"), _file("nam-sau.pdf"), _file("nu-truoc.pdf"), _file("nu-sau.pdf")],
        {},
        _session(),
    )

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceFileIndexes"] == [0, 1]
    assert result["attachments"][1]["sourceFileIndexes"] == [2, 3]


async def test_ket_hon_lai_commitment_bundle_without_certificate_goes_to_row_2(monkeypatch):
    # Không còn GCN kết hôn: nộp bộ gộp "bản cam đoan + giấy khai sinh" → vào dòng STT2, không thêm dòng.
    async def fake_ocr_per_file(files):
        return [{
            "name": "bo-giay-to.pdf",
            "text": "BẢN CAM ĐOAN Tôi chỉ còn lưu giữ giấy khai sinh ... GIẤY KHAI SINH (BẢN SAO) Họ và tên: NGUYỄN VĂN A",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "commitment"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_lai.client, "chat", fake_chat)

    res = await ket_hon_lai.plan_ket_hon_lai_attachments([_file("bo-giay-to.pdf")], {}, _session())

    [item] = res["attachments"]
    assert item["target"] == "existing"
    assert item["componentIndex"] == 2
    assert item["needsAddComponent"] is False
    assert item["componentName"] == "Bản sao Giấy chứng nhận kết hôn"
    assert item["documentName"] == "Giấy tờ liên quan đến nội dung đăng ký kết hôn"


async def test_ket_hon_lai_row_2_prefers_certificate_then_personal_document(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cam-doan.pdf", "text": "BẢN CAM ĐOAN"},
            {"name": "khai-sinh.pdf", "text": "GIẤY KHAI SINH (BẢN SAO)"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "commitment"},
            {"index": 1, "type": "other", "documentName": "Giấy khai sinh"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_lai.client, "chat", fake_chat)

    res = await ket_hon_lai.plan_ket_hon_lai_attachments(
        [_file("cam-doan.pdf"), _file("khai-sinh.pdf")], {}, _session(),
    )

    by_file = {item["fileName"]: item for item in res["attachments"]}
    assert by_file["khai-sinh.pdf"]["target"] == "existing"
    assert by_file["khai-sinh.pdf"]["componentIndex"] == 2
    assert by_file["cam-doan.pdf"]["target"] == "new"
    assert by_file["cam-doan.pdf"]["componentName"] == "Bản cam đoan"
