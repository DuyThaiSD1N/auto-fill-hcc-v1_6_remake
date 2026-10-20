"""Đăng ký lại kết hôn — STT2 nhận một giấy (GCN kết hôn cũ → giấy tờ liên quan → bản cam đoan), CCCD đặt tên theo
bên nam / bên nữ, gộp hai mặt cùng người; chế độ TÁCH chia trang rồi xếp đúng luật đó."""
import json

from app.pipelines.ket_hon_lai.attach import planner as dispatcher
from app.pipelines.ket_hon_lai.attach.dinh_kem_tach import planner as split
from app.process.schemas import FileItem

_MALE_FRONT = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000001\nGiới tính / Sex: Nam"
_MALE_BACK = "Đặc điểm nhận dạng\nIDVNM0900000011001090000001<<<<"
_FEMALE = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001190000002\nGiới tính / Sex: Nữ"


def _file(name: str, mime: str = "application/pdf") -> FileItem:
    return FileItem(name=name, type=mime, dataUrl=f"data:{mime};base64,AAA", role="doc")


def _paged(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def _session():
    return {"fields": [{"name": "SoDinhDanh_BenNam", "value": "001090000001"},
                       {"name": "SoDinhDanh_BenNu", "value": "001190000002"}]}


def _patch(monkeypatch, texts: dict[str, str], documents):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        if isinstance(documents, Exception):
            raise documents
        return json.dumps({"documents": documents})

    monkeypatch.setattr(split.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(split.client, "chat", fake_chat)


async def test_khong_tach_stt2_uu_tien_giay_lien_quan_hon_cam_doan_va_cccd_theo_ben(monkeypatch):
    _patch(monkeypatch, {
        "camdoan.pdf": "BẢN CAM ĐOAN", "khaisinh.pdf": "GIẤY KHAI SINH",
        "nam1.jpg": _MALE_FRONT, "nam2.jpg": _MALE_BACK, "nu.jpg": _FEMALE,
    }, [
        {"index": 0, "type": "commitment", "documentName": "Bản cam đoan"},
        {"index": 1, "type": "other", "documentName": "Giấy khai sinh"},
        {"index": 2, "type": "identity", "side": "nam", "face": "truoc"},
        {"index": 3, "type": "identity", "side": "", "face": "sau"},
        {"index": 4, "type": "identity", "side": "nu", "face": "truoc"},
    ])

    items = (await dispatcher.plan([
        _file("camdoan.pdf"), _file("khaisinh.pdf"), _file("nam1.jpg", "image/jpeg"),
        _file("nam2.jpg", "image/jpeg"), _file("nu.jpg", "image/jpeg"),
    ], {}, _session()))["attachments"]

    assert [(i["documentName"], i["target"], i["componentIndex"]) for i in items] == [
        ("Bản cam đoan", "new", None),
        ("Giấy tờ liên quan đến nội dung đăng ký kết hôn", "existing", 2),
        ("CCCD bên nam", "new", None),
        ("CCCD bên nữ - mặt trước", "new", None),
    ]
    assert items[2]["sourceFileIndexes"] == [2, 3]


async def test_tach_bo_cam_doan_va_khai_sinh_khai_sinh_vao_stt2_cam_doan_dong_moi(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged("BẢN CAM ĐOAN", "GIẤY KHAI SINH", _MALE_FRONT, _MALE_BACK, _FEMALE, "")}, [
        {"fileIndex": 0, "pages": [1], "docType": "commitment", "documentName": "Bản cam đoan"},
        {"fileIndex": 0, "pages": [2], "docType": "other", "documentName": "Giấy khai sinh"},
        {"fileIndex": 0, "pages": [3, 4], "docType": "identity", "side": "nam", "face": "ca_hai"},
        {"fileIndex": 0, "pages": [5], "docType": "identity", "side": "nu", "face": "truoc"},
        {"fileIndex": 0, "pages": [6], "docType": "blank_page"},
    ])

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, _session())
    items = result["attachments"]

    assert [(i["documentName"], i["target"], i["componentIndex"]) for i in items] == [
        ("Bản cam đoan", "new", None),
        ("Giấy tờ liên quan đến nội dung đăng ký kết hôn", "existing", 2),
        ("CCCD bên nam", "new", None),
        ("CCCD bên nữ - mặt trước", "new", None),
    ]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1]}],
        [{"fileIndex": 0, "pageIndexes": [2, 3]}],
        [{"fileIndex": 0, "pageIndexes": [4]}],
    ]
    assert result["extracted"]["attachmentMode"] == "split_documents"


async def test_tach_gcn_ket_hon_cu_duoc_uu_tien_vao_stt2(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged("GIẤY KHAI SINH", "GIẤY CHỨNG NHẬN KẾT HÔN")}, [
        {"fileIndex": 0, "pages": [1], "docType": "other", "documentName": "Giấy khai sinh"},
        {"fileIndex": 0, "pages": [2], "docType": "marriage_certificate", "documentName": "Giấy chứng nhận kết hôn"},
    ])

    items = (await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, _session()))["attachments"]

    assert [(i["documentName"], i["componentIndex"]) for i in items] == [
        ("Giấy khai sinh", None), ("Bản sao Giấy chứng nhận kết hôn", 2),
    ]


async def test_tach_llm_loi_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged("BẢN CAM ĐOAN", "GIẤY KHAI SINH")}, RuntimeError("llm down"))

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, _session())

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
