import json

from app.pipelines.doi_ten_nuoc_sach.attach import planner as doi_ten_attach
from app.procedures.registry import get_attach_pipeline, get_procedure
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_doi_ten_nuoc_sach_attach_maps_household_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "sđ Bình.pdf",
                "text": (
                    "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
                    "Thửa đất số: 31; tờ bản đồ số: 8\n"
                    "Chuyển nhượng cho ông Trần Thanh Bình\nAA 00200361"
                ),
            },
            {
                "name": "Đơn đổi tên_0001.pdf",
                "text": (
                    "ĐƠN XIN ĐỔI TÊN TRONG HỢP ĐỒNG DỊCH VỤ CẤP NƯỚC\n"
                    "Tên tôi là: Trần Thanh Bình\n"
                    "Người đứng tên trong hợp đồng sử dụng nước cũ: Nguyễn Chí Công\n"
                    "BÊN CHUYỂN NHƯỢNG\nBÊN NHẬN CHUYỂN NHƯỢNG"
                ),
            },
            {
                "name": "cccd Bình.pdf",
                "text": "CĂN CƯỚC\nSố định danh cá nhân: 025085013037\nTRẦN THANH BÌNH",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "legal_land_house_document", "title": "Giấy chứng nhận quyền sử dụng đất"},
                {"index": 1, "docType": "confirmed_name_change_application", "title": "Đơn xin đổi tên"},
                {"index": 2, "docType": "identity_document", "title": "Căn cước công dân"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr(doi_ten_attach, "_ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(doi_ten_attach.client, "chat", fake_chat)

    res = await doi_ten_attach.plan(
        [_file("sđ Bình.pdf"), _file("Đơn đổi tên_0001.pdf"), _file("cccd Bình.pdf")],
        {},
        {"procedure": "chuyen-doi-ten-hop-dong-nuoc-sach"},
    )

    by_file = {item["fileName"]: item for item in res["attachments"]}
    assert by_file["sđ Bình.pdf"]["target"] == "fixed-slot"
    assert by_file["sđ Bình.pdf"]["slotKey"] == "doi_ten_legal_land_house_document"
    assert by_file["sđ Bình.pdf"]["slotIndex"] == 0
    assert by_file["Đơn đổi tên_0001.pdf"]["slotKey"] == "doi_ten_confirmed_name_change_application"
    assert by_file["Đơn đổi tên_0001.pdf"]["slotIndex"] == 1
    assert by_file["cccd Bình.pdf"]["target"] == "new"
    assert by_file["cccd Bình.pdf"]["componentName"] == "Căn cước công dân người nộp"


async def test_doi_ten_nuoc_sach_attach_maps_enterprise_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "cccd Quỳnh gđ.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 010184000258\nNGUYỄN THỊ QUỲNH",
            },
            {
                "name": "Đơn đổi tên_0001 (1).pdf",
                "text": (
                    "ĐƠN XIN ĐỔI TÊN TRONG HỢP ĐỒNG DỊCH VỤ CẤP NƯỚC\n"
                    "Tên cơ quan: Cty TNHH MTV SX và TM Pờ Ma Lung Lai Châu\n"
                    "Người đại diện: Nguyễn Thị Quỳnh Chức vụ: Giám đốc\n"
                    "BÊN GIAO\nBÊN NHẬN"
                ),
            },
            {
                "name": "GĐK KD_0001.pdf",
                "text": (
                    "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\n"
                    "Mã số doanh nghiệp: 6200123497\n"
                    "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH MTV SX & TM PÒ MA LUNG LAI CHÂU"
                ),
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "identity_document", "title": "Căn cước công dân"},
                {"index": 1, "docType": "confirmed_name_change_application", "title": "Đơn xin đổi tên"},
                {"index": 2, "docType": "business_registration_or_establishment", "title": "Giấy chứng nhận đăng ký doanh nghiệp"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr(doi_ten_attach, "_ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(doi_ten_attach.client, "chat", fake_chat)

    res = await doi_ten_attach.plan(
        [_file("cccd Quỳnh gđ.pdf"), _file("Đơn đổi tên_0001 (1).pdf"), _file("GĐK KD_0001.pdf")],
        {},
        None,
    )

    by_file = {item["fileName"]: item for item in res["attachments"]}
    assert by_file["cccd Quỳnh gđ.pdf"]["target"] == "new"
    assert by_file["Đơn đổi tên_0001 (1).pdf"]["slotKey"] == "doi_ten_confirmed_name_change_application"
    assert by_file["Đơn đổi tên_0001 (1).pdf"]["slotIndex"] == 1
    assert by_file["GĐK KD_0001.pdf"]["slotKey"] == "doi_ten_business_registration_or_establishment"
    assert by_file["GĐK KD_0001.pdf"]["slotIndex"] == 3


async def test_doi_ten_nuoc_sach_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "don.pdf",
                "text": "ĐƠN XIN ĐỔI TÊN TRONG HỢP ĐỒNG DỊCH VỤ CẤP NƯỚC\nBÊN GIAO\nBÊN NHẬN",
            },
            {
                "name": "gdk.pdf",
                "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\nMã số doanh nghiệp: 6200123497",
            },
            {
                "name": "hop-dong.pdf",
                "text": "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(doi_ten_attach, "_ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(doi_ten_attach.client, "chat", fake_chat)

    res = await doi_ten_attach.plan([_file("don.pdf"), _file("gdk.pdf"), _file("hop-dong.pdf")], {}, None)
    by_file = {item["fileName"]: item for item in res["attachments"]}

    assert by_file["don.pdf"]["slotKey"] == "doi_ten_confirmed_name_change_application"
    assert by_file["gdk.pdf"]["slotKey"] == "doi_ten_business_registration_or_establishment"
    assert by_file["hop-dong.pdf"]["slotKey"] == "doi_ten_transfer_contract"
    assert any("attachment_agent" in err for err in res["errors"])


def test_registry_uses_doi_ten_nuoc_sach_attachment_pipeline():
    procedure = get_procedure("chuyen-doi-ten-hop-dong-nuoc-sach")
    assert procedure["hasAttachmentStep"] is True
    assert get_attach_pipeline("chuyen-doi-ten-hop-dong-nuoc-sach") is not None
