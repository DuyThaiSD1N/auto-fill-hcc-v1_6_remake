"""Kế hoạch đính kèm bước 3 của "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân"."""

from app.pipelines.khai_sinh_co_ho_so.attach import planner
from app.process.schemas import FileItem
from app.services import ocr


def _file(name: str) -> FileItem:
    return FileItem(
        name=name,
        type="application/pdf",
        dataUrl="data:application/pdf;base64,AAA",
        role="doc",
    )


def _session():
    return {"request_id": "req_khai_sinh_co_ho_so"}


async def test_routes_cam_doan_giay_to_ca_nhan_uy_quyen(monkeypatch):
    """Cam đoan → STT 2; mọi giấy tờ cá nhân dồn chung STT 3; ủy quyền → STT 5; STT 1 không đụng."""

    async def fake_ocr_per_file(_files):
        return [
            {"name": "cam-doan.pdf",
             "text": "BẢN CAM ĐOAN về việc chưa được đăng ký khai sinh"},
            {"name": "cccd.pdf",
             "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: SÙNG A TỦA\nNgày sinh: 09/11/1973"},
            {"name": "bhyt.pdf", "text": "THẺ BẢO HIỂM Y TẾ\nMã số BHXH: 0123456789"},
            {"name": "ket-hon.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_classify(_documents):
        return {
            0: {"type": "commitment", "title": "Bản cam đoan"},
            1: {"type": "personal_document", "title": "Căn cước công dân"},
            2: {"type": "personal_document", "title": "Thẻ bảo hiểm y tế"},
            3: {"type": "personal_document", "title": "Giấy chứng nhận kết hôn"},
            4: {"type": "authorization", "title": "Văn bản ủy quyền"},
        }

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_co_ho_so_attachments(
        [_file("cam-doan.pdf"), _file("cccd.pdf"), _file("bhyt.pdf"),
         _file("ket-hon.pdf"), _file("uy-quyen.pdf")],
        {},
        _session(),
    )
    by_file = {item["fileName"]: item for item in result["attachments"]}

    assert by_file["cam-doan.pdf"]["componentIndex"] == 2
    assert by_file["cam-doan.pdf"]["target"] == "existing"

    # Ô gom: ba giấy tờ khác nhau cùng vào STT 3, mỗi file giữ tên tài liệu riêng để phân biệt.
    for name in ("cccd.pdf", "bhyt.pdf", "ket-hon.pdf"):
        assert by_file[name]["componentIndex"] == 3, name
        assert by_file[name]["target"] == "existing", name
        assert by_file[name]["needsAddComponent"] is False, name
    # Tên tài liệu trong cùng một dòng phải khác nhau; CCCD kèm tên chủ thẻ để cán bộ phân biệt.
    assert by_file["cccd.pdf"]["documentName"] == "Căn cước công dân Sùng A Tủa"
    assert by_file["bhyt.pdf"]["documentName"] == "Thẻ bảo hiểm y tế"
    assert by_file["ket-hon.pdf"]["documentName"] == "Giấy chứng nhận kết hôn"

    assert by_file["uy-quyen.pdf"]["componentIndex"] == 5

    # Không file nào được đính vào STT 1 (mẫu hộ tịch điện tử do cổng tự sinh ở bước Kê khai).
    assert all(item["componentIndex"] != 1 for item in result["attachments"])


async def test_civil_servant_document_goes_to_slot_4(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{"name": "xac-nhan-co-quan.pdf", "text": "VĂN BẢN XÁC NHẬN CỦA THỦ TRƯỞNG CƠ QUAN"}]

    async def fake_classify(_documents):
        return {0: {"type": "civil_servant_doc", "title": "Văn bản xác nhận của cơ quan"}}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_co_ho_so_attachments(
        [_file("xac-nhan-co-quan.pdf")], {}, _session()
    )
    item = result["attachments"][0]
    assert item["componentIndex"] == 4
    assert "cán bộ, công chức" in item["componentName"]


async def test_second_commitment_falls_back_to_shared_slot_3(monkeypatch):
    """Ô một-file đã có chủ thì file sau dồn xuống ô gom, không đẻ thành phần mới."""

    async def fake_ocr_per_file(_files):
        return [
            {"name": "cam-doan-1.pdf", "text": "BẢN CAM ĐOAN về việc chưa được đăng ký khai sinh"},
            {"name": "cam-doan-2.pdf", "text": "BẢN CAM ĐOAN về việc chưa được đăng ký khai sinh"},
        ]

    async def fake_classify(_documents):
        return {
            0: {"type": "commitment", "title": "Bản cam đoan"},
            1: {"type": "commitment", "title": "Bản cam đoan"},
        }

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_co_ho_so_attachments(
        [_file("cam-doan-1.pdf"), _file("cam-doan-2.pdf")], {}, _session()
    )
    by_file = {item["fileName"]: item for item in result["attachments"]}
    assert by_file["cam-doan-1.pdf"]["componentIndex"] == 2
    assert by_file["cam-doan-2.pdf"]["componentIndex"] == 3
    # Tên tài liệu phải khác nhau, nếu trùng form coi như "đã có" và bỏ qua file thứ hai.
    assert by_file["cam-doan-1.pdf"]["documentName"] != by_file["cam-doan-2.pdf"]["documentName"]


async def test_paper_declaration_becomes_new_component(monkeypatch):
    """Tờ khai bản giấy chỉ dùng để OCR — không được đính đè lên mẫu điện tử ở STT 1."""

    async def fake_ocr_per_file(_files):
        return [{"name": "to-khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI SINH"}]

    async def fake_classify(_documents):
        return {0: {"type": "paper_declaration", "title": "Tờ khai đăng ký khai sinh"}}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_co_ho_so_attachments(
        [_file("to-khai.pdf")], {}, _session()
    )
    item = result["attachments"][0]
    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["needsAddComponent"] is True


async def test_unclassified_file_defaults_to_shared_slot_3(monkeypatch):
    """OCR mờ/LLM bỏ cuộc: giấy tờ có dấu hiệu nhân thân vẫn phải vào ô gom, không bị bỏ rơi."""

    async def fake_ocr_per_file(_files):
        return [
            {"name": "hoc-ba.pdf", "text": "HỌC BẠ TRUNG HỌC CƠ SỞ"},
            {"name": "mo.pdf", "text": ""},
        ]

    async def fake_classify(_documents):
        return {
            0: {"type": "other", "title": ""},
            1: {"type": "other", "title": ""},
        }

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_co_ho_so_attachments(
        [_file("hoc-ba.pdf"), _file("mo.pdf")], {}, _session()
    )
    by_file = {item["fileName"]: item for item in result["attachments"]}
    assert by_file["hoc-ba.pdf"]["componentIndex"] == 3
    # Không đọc được gì thì vẫn giữ file bằng một thành phần mới, không im lặng bỏ qua.
    assert by_file["mo.pdf"]["target"] == "new"
