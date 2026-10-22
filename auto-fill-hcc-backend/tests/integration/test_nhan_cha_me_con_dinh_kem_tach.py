"""Đăng ký nhận cha, mẹ, con — chế độ TÁCH giấy tờ: chia trang bằng một lượt LLM, xếp dòng đúng luật chế độ không
tách (STT2 xác nhận quan hệ, STT3 cam đoan chỉ khi không có STT2, còn lại dòng mới, gộp hai mặt CCCD)."""
import json

from app.pipelines.nhan_cha_me_con.attach import planner as dispatcher
from app.pipelines.nhan_cha_me_con.attach.dinh_kem_tach import planner as split
from app.process.schemas import FileItem

_FRONT = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000001\nHọ và tên: NGUYỄN VĂN A"
_BACK = "Đặc điểm nhận dạng\nIDVNM0900000011001090000001<<<<\nNGUYEN<<VAN<A"
_ADN = "KẾT QUẢ XÉT NGHIỆM ADN\nKết luận: có quan hệ huyết thống bố - con; độ tin cậy > 99,99%"
_DECL = "TỜ KHAI ĐĂNG KÝ NHẬN CHA, MẸ, CON\nTôi cam đoan việc nhận cha con nói trên là đúng sự thật"
_COMMIT = "VĂN BẢN CAM ĐOAN việc nhận cha con, có hai người làm chứng"


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


async def test_tep_gop_tach_tung_giay_dung_dong_gop_hai_mat_cccd_bo_trang_trang(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(_DECL, _ADN, "Bảng locus ADN của phiếu kết quả", _FRONT, _BACK, "")}, [
        {"fileIndex": 0, "pages": [1], "docType": "paper_declaration", "documentName": "Tờ khai"},
        {"fileIndex": 0, "pages": [2, 3], "docType": "relationship_proof", "documentName": "Kết quả xét nghiệm ADN"},
        {"fileIndex": 0, "pages": [4], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [5], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [6], "docType": "blank_page", "documentName": ""},
    ])

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})
    items = result["attachments"]

    assert [(i["target"], i["componentIndex"]) for i in items] == [("new", None), ("existing", 2), ("new", None)]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1, 2]}],
        [{"fileIndex": 0, "pageIndexes": [3]}, {"fileIndex": 0, "pageIndexes": [4]}],
    ]
    assert all(i["fileName"] == "hoso.pdf" for i in items)
    assert result["extracted"]["attachmentMode"] == "split_documents"


async def test_co_ket_qua_adn_thi_bo_van_ban_cam_doan(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(_ADN, _COMMIT)}, [
        {"fileIndex": 0, "pages": [1], "docType": "relationship_proof", "documentName": "Kết quả xét nghiệm ADN"},
        {"fileIndex": 0, "pages": [2], "docType": "witness_commitment", "documentName": "Văn bản cam đoan"},
    ])

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})

    assert [(i["componentIndex"], i["sourceSegments"]) for i in result["attachments"]] == [
        (2, [{"fileIndex": 0, "pageIndexes": [0]}])]
    assert any(c["docType"] == "witness_commitment" and c["target"] == "skip" for c in result["extracted"]["classified"])


async def test_khong_co_ket_qua_adn_thi_cam_doan_vao_stt3(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(_DECL, _COMMIT)}, [
        {"fileIndex": 0, "pages": [1], "docType": "paper_declaration", "documentName": "Tờ khai"},
        {"fileIndex": 0, "pages": [2], "docType": "witness_commitment", "documentName": "Văn bản cam đoan"},
    ])

    items = (await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {}))["attachments"]

    assert [(i["target"], i["componentIndex"]) for i in items] == [("new", None), ("existing", 3)]


async def test_llm_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(_ADN, _FRONT)}, RuntimeError("llm down"))

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
