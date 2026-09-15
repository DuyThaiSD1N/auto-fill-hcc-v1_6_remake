import json
from datetime import date

from app.pipelines.nuoi_con_nuoi_trong_nuoc.attach import planner
from app.pipelines.nuoi_con_nuoi_trong_nuoc.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure

_TEXTS = {
    "cccd-chong.jpg": (
        "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001085012345\n"
        "Họ và tên / Full name: NGUYỄN VĂN AN\nNgày sinh / Date of birth: 12/03/1985"
    ),
    "cccd-chong-sau.jpg": "Đặc điểm nhận dạng: Nốt ruồi\nIDVNM0850123451001085012345<<3",
    "cccd-vo.jpg": (
        "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001188054321\n"
        "Họ và tên / Full name: TRẦN THỊ BÌNH\nNgày sinh / Date of birth: 20/07/1988"
    ),
    "cccd-me-de.jpg": (
        "CĂN CƯỚC CÔNG DÂN\nSố / No.: 036199000111\n"
        "Họ và tên / Full name: LÊ THỊ CÚC\nNgày sinh / Date of birth: 01/01/1999"
    ),
    "gksk-chong.pdf": "GIẤY KHÁM SỨC KHỎE\nHọ và tên: NGUYỄN VĂN AN\nNgày, tháng, năm sinh: 12/03/1985",
    "gksk-tre.pdf": (
        "GIẤY KHÁM SỨC KHỎE (Dùng cho người chưa đủ 18 tuổi)\n"
        "Họ và tên: LÊ MINH ĐỨC\nNgày, tháng, năm sinh: 05/05/2023"
    ),
    "hoan-canh.pdf": (
        "GIẤY XÁC NHẬN HOÀN CẢNH GIA ĐÌNH, TÌNH TRẠNG CHỖ Ở, ĐIỀU KIỆN KINH TẾ\n"
        "UBND xã xác nhận ông Nguyễn Văn An và bà Trần Thị Bình đã đăng ký kết hôn"
    ),
    "ket-hon.pdf": "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên: NGUYỄN VĂN AN\nSố định danh cá nhân: 001085012345",
    "khai-sinh.pdf": (
        "GIẤY KHAI SINH\nHọ, chữ đệm, tên: LÊ MINH ĐỨC\nNgày, tháng, năm sinh: 05/05/2023\n"
        "Họ, chữ đệm, tên người mẹ: LÊ THỊ CÚC\nNơi đăng ký khai sinh: UBND xã A"
    ),
    "anh-tre.jpg": "",
}


def _file(name):
    mime = "image/jpeg" if name.endswith(".jpg") else "application/pdf"
    return FileItem(name=name, type=mime, dataUrl=f"data:{mime};base64,AAA", role="doc")


async def test_nuoi_con_nuoi_routes_existing_rows_and_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": _TEXTS[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    names = list(_TEXTS)
    res = await planner.plan([_file(name) for name in names], {}, {"request_id": "req_ncn"})
    items = {item["documentName"]: item for item in res["attachments"]}

    identity = items["Căn cước của người nhận con nuôi"]
    assert identity["target"] == "existing" and identity["componentIndex"] == 1
    # Chồng: mặt trước rồi mặt sau, sau đó tới vợ — gộp hết vào một PDF cho STT 1.
    idx = {name: i for i, name in enumerate(names)}
    assert identity["sourceFileIndexes"] == [idx["cccd-chong.jpg"], idx["cccd-chong-sau.jpg"], idx["cccd-vo.jpg"]]

    assert items["Giấy khám sức khỏe người nhận con nuôi"]["componentIndex"] == 2
    assert items["Văn bản xác nhận hoàn cảnh gia đình"]["componentIndex"] == 3
    assert items["Giấy chứng nhận kết hôn"]["componentIndex"] == 4

    for new_name, file_name in (
        ("Căn cước của cha mẹ đẻ", "cccd-me-de.jpg"),
        ("Giấy khám sức khỏe của trẻ", "gksk-tre.pdf"),
        ("Giấy khai sinh của trẻ", "khai-sinh.pdf"),
        ("Ảnh của trẻ", "anh-tre.jpg"),
    ):
        item = items[new_name]
        assert item["target"] == "new"
        assert item["needsAddComponent"] is True
        assert item["componentName"] == new_name
        assert item["fileName"] == file_name

    assert len(res["attachments"]) == 8
    assert not res["errors"]


def test_nuoi_con_nuoi_llm_identity_role_used_when_no_birth_certificate():
    files = [{"name": "cccd.pdf", "type": "application/pdf"}]
    ocr_results = [{"name": "cccd.pdf", "text": _TEXTS["cccd-me-de.jpg"]}]
    llm = {0: {"type": "birth_parent_identity", "documentName": "CCCD mẹ đẻ"}}

    attachments, classified = planner.build_plan_items(files, ocr_results, llm, today=date(2026, 9, 15))

    assert attachments[0]["target"] == "new"
    assert classified[0]["docType"] == "birth_parent_identity"


def test_nuoi_con_nuoi_other_document_keeps_llm_name():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    ocr_results = [{"name": "x.pdf", "text": "Sổ hộ khẩu gia đình ông Nguyễn Văn An, địa chỉ thôn Đông"}]
    llm = {0: {"type": "other", "documentName": "Sổ hộ khẩu"}}

    attachments, _ = planner.build_plan_items(files, ocr_results, llm)

    assert attachments[0]["target"] == "new"
    assert attachments[0]["componentName"] == "Sổ hộ khẩu"


def test_nuoi_con_nuoi_attachment_registry():
    proc = get_procedure("dang-ky-nuoi-con-nuoi-trong-nuoc")

    assert proc["mode"] == "attach"
    assert get_attach_pipeline("dang-ky-nuoi-con-nuoi-trong-nuoc") is not None


def test_nuoi_con_nuoi_attachment_prompt_contract():
    assert "adopter_identity" in SYSTEM_PROMPT
    assert "birth_parent_identity" in SYSTEM_PROMPT
    user_prompt = build_user_prompt([{"index": 0, "fileName": "cccd.pdf", "text": "CĂN CƯỚC"}])
    assert "ocrText" in user_prompt
    assert "cccd.pdf" not in user_prompt
