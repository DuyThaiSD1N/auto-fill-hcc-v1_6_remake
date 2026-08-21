import json

from app.pipelines.cap_giay_phep_xay_dung.attach import planner
from app.pipelines.cap_giay_phep_xay_dung.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, file_type="application/pdf"):
    return FileItem(name=name, type=file_type, dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_cap_giay_phep_xay_dung_routes_sample_house_documents_to_fixed_slots(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "Căn cươc CD Chinh.pdf": (
                "CĂN CƯỚC CÔNG DÂN\n"
                "Số / No.: 027077015515\n"
                "Họ và tên / Full name: NGUYỄN TRUNG CHÍNH\n"
                "IDVNM027077015515"
            ),
            "Đơn đề nghị cấp phép xây nhà 2026.pdf": (
                "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG\n"
                "Sử dụng cho công trình: Không theo tuyến/Nhà ở riêng lẻ/sửa chữa, cải tạo\n"
                "Tên chủ đầu tư (tên chủ hộ): Ông NGUYỄN TRUNG CHÍNH\n"
                "Gửi kèm theo Đơn này các tài liệu: Bản sao giấy tờ chứng minh quyền sử dụng đất."
            ),
            "Bản cam ket xây nhà 2026.pdf": (
                "BẢN CAM KẾT\n"
                "V/v Đảm bảo an toàn đối với công trình liền kề\n"
                "Ông: NGUYỄN TRUNG CHÍNH xin cam kết khi xây nhà."
            ),
            "Bản kê khai kinh nghiệm thiết kế.pdf": (
                "BẢN KÊ KHAI KINH NGHIỆM CỦA TỔ CHỨC, CÁ NHÂN THIẾT KẾ\n"
                "Tổ chức thiết kế: Công ty cổ phần tư vấn đầu tư xây dựng ARECO\n"
                "Chủ trì thiết kế các bộ môn: Kiến trúc: Nguyễn Văn Lục."
            ),
            "Bản vẽ xin cấp phép xây dựng.pdf": (
                "HỒ SƠ XIN CẤP PHÉP XÂY DỰNG\n"
                "CÔNG TRÌNH: NHÀ Ở GIA ĐÌNH\n"
                "MẶT BẰNG TẦNG 1\n"
                "MẶT ĐỨNG TRỤC 1-4\n"
                "MẶT BẰNG MÓNG\n"
                "TỔNG MẶT BẰNG CẤP NƯỚC, THOÁT NƯỚC, CẤP ĐIỆN"
            ),
            "Chứng chỉ năng lực HĐXD ARECO 2025.pdf": (
                "CHỨNG CHỈ NĂNG LỰC HOẠT ĐỘNG XÂY DỰNG\n"
                "Tên tổ chức: CÔNG TY CỔ PHẦN TƯ VẤN ĐẦU TƯ XÂY DỰNG ARECO\n"
                "Giấy chứng nhận đăng ký doanh nghiệp số: 2301199858"
            ),
            "Nguyễn Văn Lục KT.pdf": (
                "CHỨNG CHỈ HÀNH NGHỀ KIẾN TRÚC\n"
                "Số: BAN-00000047\n"
                "Cấp cho: Ông Nguyễn Văn Lục\n"
                "Nội dung được phép hành nghề kiến trúc: Thiết kế kiến trúc công trình"
            ),
            "Sổ đỏ 1.jpg": (
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\n"
                "Ông NGUYỄN TRUNG CHÍNH\n"
                "Thửa đất số 604, tờ bản đồ số 3."
            ),
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "other", "title": "Tài liệu khác"},
                {"index": 1, "type": "land_legal_document", "title": "Giấy chứng nhận quyền sử dụng đất"},
                {"index": 2, "type": "building_permit_application", "title": "Đơn đề nghị cấp phép xây dựng"},
                {"index": 3, "type": "design_experience_declaration", "title": "Bản kê khai kinh nghiệm thiết kế"},
                {"index": 4, "type": "construction_design_drawings", "title": "Bản vẽ xin cấp phép xây dựng"},
                {"index": 5, "type": "construction_capacity_certificate", "title": "Chứng chỉ năng lực"},
                {"index": 6, "type": "architect_practice_certificate", "title": "Chứng chỉ hành nghề"},
                {"index": 7, "type": "land_legal_document", "title": "Giấy chứng nhận quyền sử dụng đất"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [
            _file("Căn cươc CD Chinh.pdf"),
            _file("Đơn đề nghị cấp phép xây nhà 2026.pdf"),
            _file("Bản cam ket xây nhà 2026.pdf"),
            _file("Bản kê khai kinh nghiệm thiết kế.pdf"),
            _file("Bản vẽ xin cấp phép xây dựng.pdf"),
            _file("Chứng chỉ năng lực HĐXD ARECO 2025.pdf"),
            _file("Nguyễn Văn Lục KT.pdf"),
            _file("Sổ đỏ 1.jpg", "image/jpeg"),
        ],
        {},
        {"request_id": "req_gpxd"},
    )
    items = res["attachments"]

    assert len(items) == 8
    assert all(item["target"] == "fixed-slot" for item in items)
    assert all(item["needsAddComponent"] is False for item in items)
    assert all("sourceFileIndexes" not in item for item in items)

    by_slot = {}
    for item in items:
        by_slot.setdefault(item["slotKey"], []).append(item)

    app_items = by_slot["gpxd_application"]
    assert [item["fileIndex"] for item in app_items] == [1, 0, 2]
    assert {item["componentIndex"] for item in app_items} == {1}
    assert {item["slotIndex"] for item in app_items} == {0}
    assert "Đơn đề nghị cấp giấy phép xây dựng" in app_items[0]["componentName"]

    land_items = by_slot["gpxd_land_document"]
    assert [item["fileIndex"] for item in land_items] == [7]
    assert land_items[0]["componentIndex"] == 11
    assert land_items[0]["slotIndex"] == 10
    assert "giấy tờ hợp pháp về đất đai" in land_items[0]["componentName"].lower()

    design_items = by_slot["gpxd_design_dossier"]
    assert [item["fileIndex"] for item in design_items] == [4, 3, 5, 6]
    assert {item["componentIndex"] for item in design_items} == {27}
    assert {item["slotIndex"] for item in design_items} == {26}
    assert "Hồ sơ thiết kế xây dựng" in design_items[0]["componentName"]
    assert not res["errors"]

    by_name = {entry["fileName"]: entry for entry in res["extracted"]["classified"]}
    assert by_name["Đơn đề nghị cấp phép xây nhà 2026.pdf"]["docType"] == "building_permit_application"
    assert by_name["Căn cươc CD Chinh.pdf"]["docType"] == "identity_document"
    assert by_name["Bản cam ket xây nhà 2026.pdf"]["docType"] == "safety_commitment"
    assert by_name["Sổ đỏ 1.jpg"]["componentIndex"] == 11
    assert by_name["Bản vẽ xin cấp phép xây dựng.pdf"]["componentIndex"] == 27


async def test_cap_giay_phep_xay_dung_filename_fallback_when_ocr_empty(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": "", "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": ""}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("Sổ đỏ 1.jpg", "image/jpeg")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "fixed-slot"
    assert item["componentIndex"] == 11
    assert item["slotKey"] == "gpxd_land_document"
    assert item["slotIndex"] == 10
    assert item["documentName"] == "Giấy chứng nhận quyền sử dụng đất"


def test_cap_giay_phep_xay_dung_registry_has_process_and_attach():
    key = "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"
    proc = get_procedure(key)

    assert proc is not None
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert "đính từng file vào các hàng có sẵn" in proc["uploadHint"]
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None


def test_cap_giay_phep_xay_dung_prompt_uses_ocr_text_only():
    assert "building_permit_application" in SYSTEM_PROMPT
    assert "construction_design_drawings" in SYSTEM_PROMPT
    assert "land_legal_document" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT
    assert "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG" in SYSTEM_PROMPT
    assert "Dòng 27" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "don-de-nghi.pdf",
            "text": "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG",
        }
    ])

    assert "ocrText" in user_prompt
    assert "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG" in user_prompt
    assert "don-de-nghi.pdf" not in user_prompt
    assert "fileName" not in user_prompt
