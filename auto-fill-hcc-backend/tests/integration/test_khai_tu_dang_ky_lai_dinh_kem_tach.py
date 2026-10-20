"""Đăng ký lại khai tử — chế độ TÁCH giấy tờ: chia trang bằng một lượt LLM, xếp dòng đúng luật chế độ không tách."""
import json

from app.pipelines.khai_tu_dang_ky_lai.attach import planner as dispatcher
from app.pipelines.khai_tu_dang_ky_lai.attach.dinh_kem_tach import planner as split
from app.process.schemas import FileItem

_FRONT = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000001\nHọ và tên: NGUYỄN VĂN A"
_BACK = "Đặc điểm nhận dạng\nIDVNM0900000011001090000001<<<<\nNGUYEN<<VAN<A"


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


async def test_tep_gop_tach_tung_giay_dung_dong_va_bo_trang_trang(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(
        "TỜ KHAI ĐĂNG KÝ LẠI KHAI TỬ\nGiấy chứng tử/Trích lục khai tử số:",
        "TRÍCH LỤC KHAI TỬ (Bản sao)",
        _FRONT, _BACK, "",
    )}, [
        {"fileIndex": 0, "pages": [1], "docType": "paper_declaration", "documentName": "Tờ khai"},
        {"fileIndex": 0, "pages": [2], "docType": "death_proof", "documentName": "Trích lục khai tử"},
        {"fileIndex": 0, "pages": [3, 4], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [5], "docType": "blank_page", "documentName": ""},
    ])

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})
    items = result["attachments"]

    assert [(i["target"], i["componentIndex"]) for i in items] == [("new", None), ("existing", 2), ("new", None)]
    assert items[0]["componentName"] == "Tờ khai bản giấy"
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1]}],
        [{"fileIndex": 0, "pageIndexes": [2, 3]}],
    ]
    assert all(i["fileName"] == "hoso.pdf" and i["fileIndex"] == 0 for i in items)
    assert result["extracted"]["attachmentMode"] == "split_documents"


async def test_luoi_rule_van_chan_to_khai_vao_stt2_khi_llm_xep_nham(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged("TỜ KHAI ĐĂNG KÝ LẠI KHAI TỬ\nĐã chết vào lúc", "GIẤY ỦY QUYỀN")}, [
        {"fileIndex": 0, "pages": [1], "docType": "death_proof", "documentName": "Trích lục khai tử"},
        {"fileIndex": 0, "pages": [2], "docType": "authorization", "documentName": "Giấy ủy quyền"},
    ])

    items = (await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {}))["attachments"]

    assert (items[0]["target"], items[0]["componentName"]) == ("new", "Tờ khai bản giấy")
    assert (items[1]["target"], items[1]["componentIndex"]) == ("existing", 3)


async def test_hai_mat_cccd_o_hai_tep_gop_mot_muc_va_trang_lac_theo_giay_truoc(monkeypatch):
    _patch(monkeypatch, {
        "truoc.jpg": _FRONT, "sau.jpg": _BACK,
        "chung-tu.pdf": _paged("GIẤY CHỨNG TỬ", "Trang tiếp theo của giấy chứng tử"),
    }, [
        {"fileIndex": 0, "pages": [1], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 1, "pages": [1], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 2, "pages": [1], "docType": "death_proof", "documentName": "Giấy chứng tử"},
    ])

    items = (await dispatcher.plan(
        [_file("truoc.jpg", "image/jpeg"), _file("sau.jpg", "image/jpeg"), _file("chung-tu.pdf")],
        {"splitDocuments": True}, {},
    ))["attachments"]

    assert len(items) == 2
    assert items[0]["sourceFileIndexes"] == [0, 1] and "sourceSegments" not in items[0]
    # Trang 2 LLM không nhắc tới → thuộc giấy chứng tử → giấy chiếm trọn tệp, đính nguyên tệp.
    assert (items[1]["fileIndex"], items[1]["componentIndex"]) == (2, 2) and "sourceSegments" not in items[1]


async def test_llm_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged("GIẤY CHỨNG TỬ", _FRONT)}, RuntimeError("llm down"))

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
