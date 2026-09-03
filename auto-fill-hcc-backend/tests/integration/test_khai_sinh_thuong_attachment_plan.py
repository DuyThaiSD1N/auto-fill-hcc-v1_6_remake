from app.pipelines.khai_sinh_thuong.attach import planner
from app.process.schemas import FileItem
from app.services import ocr


def _file(name: str) -> FileItem:
    return FileItem(
        name=name,
        type="application/pdf",
        dataUrl="data:application/pdf;base64,AAA",
        role="doc",
    )


async def test_commitment_mentioning_cccd_keeps_commitment_file_name(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "giay-uy-quyen.pdf", "text": "GIẤY ỦY QUYỀN"},
            {
                "name": "cccd-nguoi-khai.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: VÀNG A LẤU\nNgày sinh: 01/01/1990",
            },
            {
                "name": "cccd-khai-sinh.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: VÀNG A CHÂNG\nNgày sinh: 02/02/1991",
            },
            {
                "name": "cam-doan-khai-sinh.pdf",
                "text": "BẢN CAM ĐOAN\nTôi mang căn cước công dân số 012345678901 cam đoan nội dung trên đúng.",
            },
        ]

    async def fake_classify(_documents):
        return {
            0: {"type": "authorization", "title": "Văn bản ủy quyền"},
            1: {"type": "identity", "title": "Căn cước công dân"},
            2: {"type": "identity", "title": "Căn cước công dân"},
            3: {"type": "commitment", "title": "Bản cam đoan"},
        }

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_thuong_attachments(
        [
            _file("giay-uy-quyen.pdf"),
            _file("cccd-nguoi-khai.pdf"),
            _file("cccd-khai-sinh.pdf"),
            _file("cam-doan-khai-sinh.pdf"),
        ],
        {},
        {"request_id": "req_commitment_name"},
    )
    by_file = {item["fileName"]: item for item in result["attachments"]}

    commitment = by_file["cam-doan-khai-sinh.pdf"]
    assert commitment["documentName"] == "Bản cam đoan"
    assert commitment["componentName"] == "Bản cam đoan"
    assert commitment["detectedType"] == "Bản cam đoan"
    assert commitment["target"] == "new"

    assert by_file["cccd-nguoi-khai.pdf"]["documentName"] == "cccd_vang_a_lau"
    assert by_file["cccd-khai-sinh.pdf"]["documentName"] == "cccd_vang_a_chang"


async def test_other_with_cccd_markers_still_falls_back_to_identity(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "the-can-cuoc.pdf",
            "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: LÊ MINH AN\nNgày sinh: 03/03/1992",
        }]

    async def fake_classify(_documents):
        return {0: {"type": "other", "title": ""}}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_thuong_attachments(
        [_file("the-can-cuoc.pdf")],
        {},
        {"request_id": "req_identity_fallback"},
    )

    item = result["attachments"][0]
    assert item["documentName"] == "cccd_le_minh_an"
    assert item["componentName"] == "Căn cước công dân Lê Minh An"
    assert result["extracted"]["classified"][0]["type"] == "identity"


async def test_identity_faces_merge_only_for_same_subject(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "a-truoc.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901\nHọ và tên: NGUYỄN VĂN A\nNgày sinh: 01/01/1990"},
            {"name": "a-sau.pdf", "text": "Đặc điểm nhận dạng\nIDVNM3456789010012345678901<<1"},
            {"name": "b-truoc.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 098765432109\nHọ và tên: TRẦN THỊ B\nNgày sinh: 02/02/1992"},
            {"name": "b-sau.pdf", "text": "Đặc điểm nhận dạng\nIDVNM7654321090098765432109<<2"},
        ]

    async def fake_classify(_documents):
        return {
            index: {"type": "identity", "title": "Căn cước công dân"}
            for index in range(4)
        }

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan_khai_sinh_thuong_attachments(
        [_file("a-truoc.pdf"), _file("a-sau.pdf"), _file("b-truoc.pdf"), _file("b-sau.pdf")],
        {},
        {"request_id": "req_identity_subjects"},
    )

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceFileIndexes"] == [0, 1]
    assert result["attachments"][1]["sourceFileIndexes"] == [2, 3]
    assert all(item["target"] == "new" for item in result["attachments"])
