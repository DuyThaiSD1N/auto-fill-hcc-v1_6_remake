import json

from app.pipelines.ket_hon.attach import planner as ket_hon
from app.process.schemas import FileItem


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _fake_chat_types(types: list[str]):
    """Giả lập LLM phân loại loại giấy tờ trả về theo thứ tự file."""
    async def _chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": i, "type": t} for i, t in enumerate(types)]})
    return _chat


def _session():
    return {
        "request_id": "req_test",
        "procedure": "ket-hon",
        "fields": [
            {"name": "SoDinhDanh_BenNam", "value": "040203015844"},
            {"name": "SoDinhDanh_BenNu", "value": "012193000851"},
        ],
    }


async def test_ket_hon_attachment_plan_maps_two_pdf_files_by_identity_number(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "nam.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 040203015844"},
            {"name": "nu.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012193000851"},
        ]

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", _fake_chat_types(["identity", "identity"]))

    res = await ket_hon.plan_ket_hon_attachments([_file("nam.pdf"), _file("nu.pdf")], {}, _session())
    items = res["attachments"]

    # Cổng mới: CCCD ĐẦU TIÊN vào ô STT2 có sẵn (Hộ chiếu/CMND/Thẻ CCCD...), CCCD còn lại
    # thêm thành phần MỚI; documentName vẫn giữ nhãn theo người để dễ rà.
    assert "CCCD bên nam" in items[0]["documentName"]
    assert items[0]["target"] == "existing" and items[0]["componentIndex"] == 2
    assert "Hộ chiếu" in items[0]["componentName"]
    assert "CCCD bên nữ" in items[1]["componentName"]
    assert items[1]["target"] == "new" and items[1]["needsAddComponent"] is True


async def test_ket_hon_attachment_plan_uses_combined_label_for_single_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cccd-ca-hai.pdf", "text": "040203015844\n012193000851"}]

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", _fake_chat_types(["identity"]))

    res = await ket_hon.plan_ket_hon_attachments([_file("cccd-ca-hai.pdf")], {}, _session())

    item = res["attachments"][0]
    assert item["documentName"].startswith("CCCD của cả bên nam và bên nữ")
    # 1 file CCCD duy nhất → vào ô STT2 có sẵn của cổng mới.
    assert item["target"] == "existing" and item["componentIndex"] == 2
    assert "Hộ chiếu" in item["componentName"]


async def test_ket_hon_attachment_plan_classifies_declaration_and_commitment(monkeypatch):
    """Tờ khai/cam đoan KHÔNG bị gán nhầm thành CCCD; CCCD vẫn ghép nam/nữ."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "camdoan.pdf", "text": "BẢN CAM ĐOAN ... Sùng A Trung"},
            {"name": "cccd_nam.pdf", "text": "CĂN CƯỚC CÔNG DÂN Giới tính Sex Nam 040203015844"},
            {"name": "tokhai.pdf", "text": "TỜ KHAI ĐĂNG KÝ KẾT HÔN bên nam bên nữ"},
            {"name": "cccd_nu.pdf", "text": "CĂN CƯỚC Giới tính Sex Nữ 012193000851"},
        ]

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(
        ket_hon.client, "chat",
        _fake_chat_types(["commitment", "identity", "marriage_declaration", "identity"]),
    )

    res = await ket_hon.plan_ket_hon_attachments(
        [_file("camdoan.pdf"), _file("cccd_nam.pdf"), _file("tokhai.pdf"), _file("cccd_nu.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["componentName"] == "Bản cam đoan"
    # CCCD đầu → ô STT2 có sẵn; CCCD thứ hai → thành phần mới theo người.
    assert "CCCD bên nam" in items[1]["documentName"] and "Hộ chiếu" in items[1]["componentName"]
    assert items[2]["componentName"] == "Tờ khai đăng ký kết hôn"
    assert "CCCD bên nữ" in items[3]["componentName"] and items[3]["target"] == "new"


async def test_ket_hon_attachment_plan_names_other_by_content(monkeypatch):
    """Tài liệu 'other' đặt tên CỤ THỂ theo nội dung (không phải 'Tài liệu kết hôn' chung chung)."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "a.pdf", "text": "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"},
            {"name": "b.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "other", "documentName": "Giấy xác nhận tình trạng hôn nhân"},
            {"index": 1, "type": "other", "documentName": "Quyết định ly hôn"},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    res = await ket_hon.plan_ket_hon_attachments([_file("a.pdf"), _file("b.pdf")], {}, _session())
    names = [a["componentName"] for a in res["attachments"]]

    assert names[0] == "Giấy xác nhận tình trạng hôn nhân"
    assert names[1] == "Quyết định ly hôn"
