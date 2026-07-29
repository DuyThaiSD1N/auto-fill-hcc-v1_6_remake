import json

from app.pipelines.cap_nuoc_sach.attach import planner as cap_nuoc_sach_attach
from app.procedures.registry import get_attach_pipeline, get_procedure
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_cap_nuoc_sach_attach_maps_household_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "CCCD LÊ THỊ DUNG.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 010184000972\nHọ và tên: LÊ THỊ DUNG",
            },
            {
                "name": "Đơn đăng ký_0001.pdf",
                "text": (
                    "MẪU HỘ GIA ĐÌNH\nĐƠN ĐỀ NGHỊ CẤP NƯỚC SẠCH\n"
                    "Chủ hộ: Lò Thị Duy Điện thoại 0975754384\n"
                    "Địa chỉ đề nghị cấp nước: Đường Lý Tự Trọng, Tổ 26, P. Tân Phong"
                ),
            },
            {
                "name": "sđ Dung_0001.pdf",
                "text": (
                    "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
                    "Thửa đất số: 107; tờ bản đồ số: 172\nAA 05565655"
                ),
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "identity_document", "title": "Căn cước công dân"},
                {"index": 1, "docType": "household_application", "title": "Đơn đề nghị cấp nước sạch hộ gia đình"},
                {"index": 2, "docType": "legal_land_house_document", "title": "Giấy chứng nhận quyền sử dụng đất"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr(cap_nuoc_sach_attach, "_ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(cap_nuoc_sach_attach.client, "chat", fake_chat)

    res = await cap_nuoc_sach_attach.plan(
        [_file("CCCD LÊ THỊ DUNG.pdf"), _file("Đơn đăng ký_0001.pdf"), _file("sđ Dung_0001.pdf")],
        {},
        {"procedure": "dang-ky-lap-dat-su-dung-nuoc-sach"},
    )

    by_file = {item["fileName"]: item for item in res["attachments"]}
    assert by_file["CCCD LÊ THỊ DUNG.pdf"]["target"] == "new"
    assert by_file["CCCD LÊ THỊ DUNG.pdf"]["componentName"] == "Căn cước công dân người nộp"
    assert by_file["Đơn đăng ký_0001.pdf"]["target"] == "fixed-slot"
    assert by_file["Đơn đăng ký_0001.pdf"]["slotKey"] == "household_application"
    assert by_file["Đơn đăng ký_0001.pdf"]["slotIndex"] == 0
    assert by_file["sđ Dung_0001.pdf"]["slotKey"] == "legal_land_house_document"
    assert by_file["sđ Dung_0001.pdf"]["slotIndex"] == 3


async def test_cap_nuoc_sach_attach_maps_enterprise_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "cccd GĐ_0001.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012301005867\nNGUYỄN THỊ BÍCH PHƯỢNG",
            },
            {
                "name": "Đơn đăng ký_0001 (1).pdf",
                "text": (
                    "MẪU CƠ QUAN\nĐƠN ĐỀ NGHỊ CẤP NƯỚC SẠCH\n"
                    "Tên cơ quan: Công ty C.P chè Lai Châu Điện thoại: 0393273913\n"
                    "Người đại diện: Nguyễn Thị Bích Phượng Chức vụ: Giám đốc\nMST CQ/DN: 6200120834"
                ),
            },
            {
                "name": "GĐK KD_0001.pdf",
                "text": (
                    "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\n"
                    "Mã số doanh nghiệp: 6200120834\nTên công ty: CÔNG TY CỔ PHẦN CHÈ LAI CHÂU"
                ),
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "identity_document", "title": "Căn cước công dân"},
                {"index": 1, "docType": "organization_application", "title": "Đơn đề nghị cấp nước sạch tổ chức"},
                {"index": 2, "docType": "business_registration_or_establishment", "title": "Giấy chứng nhận đăng ký doanh nghiệp"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr(cap_nuoc_sach_attach, "_ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(cap_nuoc_sach_attach.client, "chat", fake_chat)

    res = await cap_nuoc_sach_attach.plan(
        [_file("cccd GĐ_0001.pdf"), _file("Đơn đăng ký_0001 (1).pdf"), _file("GĐK KD_0001.pdf")],
        {},
        None,
    )

    by_file = {item["fileName"]: item for item in res["attachments"]}
    assert by_file["cccd GĐ_0001.pdf"]["target"] == "new"
    assert by_file["Đơn đăng ký_0001 (1).pdf"]["slotKey"] == "organization_application"
    assert by_file["Đơn đăng ký_0001 (1).pdf"]["slotIndex"] == 1
    assert by_file["GĐK KD_0001.pdf"]["slotKey"] == "business_registration_or_establishment"
    assert by_file["GĐK KD_0001.pdf"]["slotIndex"] == 2


async def test_cap_nuoc_sach_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "don.pdf", "text": "MẪU HỘ GIA ĐÌNH\nĐƠN ĐỀ NGHỊ CẤP NƯỚC SẠCH\nChủ hộ: Lê Thị Dung"},
            {"name": "gdk.pdf", "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\nMã số doanh nghiệp: 6200120834"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(cap_nuoc_sach_attach, "_ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(cap_nuoc_sach_attach.client, "chat", fake_chat)

    res = await cap_nuoc_sach_attach.plan([_file("don.pdf"), _file("gdk.pdf")], {}, None)
    by_file = {item["fileName"]: item for item in res["attachments"]}

    assert by_file["don.pdf"]["slotKey"] == "household_application"
    assert by_file["gdk.pdf"]["slotKey"] == "business_registration_or_establishment"
    assert any("attachment_agent" in err for err in res["errors"])


def test_registry_uses_cap_nuoc_sach_attachment_pipeline():
    procedure = get_procedure("dang-ky-lap-dat-su-dung-nuoc-sach")
    assert procedure["hasAttachmentStep"] is True
    assert get_attach_pipeline("dang-ky-lap-dat-su-dung-nuoc-sach") is not None
