"""Kết hôn có yếu tố nước ngoài — xếp dòng đính kèm: 5 ô cố định, giấy cùng loại thừa và loại không có ô → dòng mới,
gộp hai mặt CCCD cùng người; chế độ TÁCH chia trang rồi xếp đúng luật đó."""
import json

from app.pipelines.ket_hon_nuoc_ngoai.attach import planner as dispatcher
from app.pipelines.ket_hon_nuoc_ngoai.attach.dinh_kem_tach import planner as split
from app.process.schemas import FileItem

_FRONT = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000001\nHọ và tên: NGUYỄN THỊ B"
_BACK = "Đặc điểm nhận dạng\nIDVNM0900000011001090000001<<<<\nNGUYEN<<THI<B"


def _file(name: str, mime: str = "application/pdf") -> FileItem:
    return FileItem(name=name, type=mime, dataUrl=f"data:{mime};base64,AAA", role="doc")


def _paged(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def _patch(monkeypatch, texts: dict[str, str], documents):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        if isinstance(documents, Exception):
            raise documents
        return json.dumps({"documents": documents})

    monkeypatch.setattr(split.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(split.client, "chat", fake_chat)


async def test_khong_tach_o_co_dinh_giay_thua_va_hai_mat_cccd(monkeypatch):
    _patch(monkeypatch, {
        "yte1.pdf": "GIẤY KHÁM SỨC KHỎE", "yte2.pdf": "GIẤY KHÁM SỨC KHỎE",
        "hochieu.pdf": "PASSPORT", "truoc.jpg": _FRONT, "sau.jpg": _BACK,
    }, [
        {"index": 0, "type": "medical", "documentName": "Giấy khám sức khỏe"},
        {"index": 1, "type": "medical", "documentName": "Giấy khám sức khỏe"},
        {"index": 2, "type": "passport_foreign", "documentName": "Hộ chiếu"},
        {"index": 3, "type": "identity_vn", "documentName": "Căn cước công dân"},
        {"index": 4, "type": "identity_vn", "documentName": "Căn cước công dân"},
    ])

    result = await dispatcher.plan([
        _file("yte1.pdf"), _file("yte2.pdf"), _file("hochieu.pdf"),
        _file("truoc.jpg", "image/jpeg"), _file("sau.jpg", "image/jpeg"),
    ], {}, {})
    items = result["attachments"]

    assert [(i["target"], i["componentIndex"]) for i in items] == [
        ("existing", 2), ("new", None), ("existing", 4), ("new", None),
    ]
    assert items[1]["documentName"] == "Giấy khám sức khỏe 2"
    assert items[3]["sourceFileIndexes"] == [3, 4]


async def test_tach_tep_gop_xep_o_co_dinh_va_gop_hai_mat_cccd(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(
        "GIẤY KHÁM SỨC KHỎE", "PASSPORT", _FRONT, _BACK, "GIẤY KHÁM SỨC KHỎE", "",
    )}, [
        {"fileIndex": 0, "pages": [1], "docType": "medical", "documentName": "Giấy khám sức khỏe"},
        {"fileIndex": 0, "pages": [2], "docType": "passport_foreign", "documentName": "Hộ chiếu"},
        {"fileIndex": 0, "pages": [3], "docType": "identity_vn", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [4], "docType": "identity_vn", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [5], "docType": "medical", "documentName": "Giấy khám sức khỏe"},
        {"fileIndex": 0, "pages": [6], "docType": "blank_page", "documentName": ""},
    ])

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})
    items = result["attachments"]

    assert [(i["target"], i["componentIndex"]) for i in items] == [
        ("existing", 2), ("existing", 4), ("new", None), ("new", None),
    ]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}, {"fileIndex": 0, "pageIndexes": [3]}],
        [{"fileIndex": 0, "pageIndexes": [4]}],
    ]
    assert all(i["fileName"] == "hoso.pdf" for i in items)
    assert result["extracted"]["attachmentMode"] == "split_documents"


async def test_tach_llm_loi_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged("GIẤY KHÁM SỨC KHỎE", "PASSPORT")}, RuntimeError("llm down"))

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})

    assert len(result["attachments"]) == 1 and "sourceSegments" not in result["attachments"][0]
    assert result["errors"][0].startswith("attachment_agent (tách): llm down")


async def test_chi_true_moi_tach(monkeypatch):
    calls = []

    async def fake_split(files, options, session):
        calls.append("split")
        return {}

    async def fake_whole(files, options, session):
        calls.append("whole")
        return {}

    monkeypatch.setattr(split, "plan", fake_split)
    monkeypatch.setattr(dispatcher, "plan_without_split", fake_whole)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}, {"splitDocuments": True}):
        await dispatcher.plan([_file("a.pdf")], options, {})
    assert calls == ["whole", "whole", "whole", "split"]
