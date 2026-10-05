import json

from app.pipelines.an_toan_thuc_pham.attach import planner as attp_attach
from app.pipelines.an_toan_thuc_pham.attach.prompt import SYSTEM_PROMPT
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _fake_ocr(texts):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": texts.get(f["name"], ""), "provider": "tiengnoi"} for f in files]
    return fake_ocr_per_file


async def test_an_toan_thuc_pham_attach_dat_ten_theo_loai_giay_va_van_mot_dong(monkeypatch):
    names = ["scan-1.pdf", "scan-2.pdf", "scan-3.pdf", "scan-4.pdf", "scan-5.pdf", "scan-6.pdf"]
    texts = {name: "nội dung OCR" for name in names[:5]}  # scan-6: OCR rỗng → không gửi LLM

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "don_de_nghi", "title": ""},
            {"index": 1, "docType": "suc_khoe", "title": ""},
            {"index": 2, "docType": "suc_khoe", "title": ""},
            {"index": 3, "docType": "other", "title": "Căn cước công dân"},
            {"index": 4, "docType": "other", "title": ""},
        ]})

    monkeypatch.setattr(attp_attach.ocr, "ocr_per_file", _fake_ocr(texts))
    monkeypatch.setattr(attp_attach.client, "chat", fake_chat)

    res = await attp_attach.plan([_file(n) for n in names], {}, None)
    items = res["attachments"]

    # Không bỏ file nào, tất cả vẫn vào MỘT dòng lặp upload như cũ.
    assert [item["fileIndex"] for item in items] == [0, 1, 2, 3, 4, 5]
    assert {item["slotKey"] for item in items} == {"attp_dossier"}
    assert {item["slotIndex"] for item in items} == {0}
    assert {item["target"] for item in items} == {"fixed-slot"}
    assert all(item["repeatUpload"] is True for item in items)
    assert "Đơn đề nghị cấp Giấy chứng nhận" in items[0]["componentName"]

    assert [item["documentName"] for item in items] == [
        "Đơn đề nghị cấp Giấy chứng nhận ATTP",
        "Giấy xác nhận đủ sức khỏe",
        "Giấy xác nhận đủ sức khỏe 2",
        "Căn cước công dân",
        "scan-5",  # other không có tiêu đề → giữ tên gốc, không bịa tên chung
        "scan-6",
    ]
    assert all(len(item["documentName"]) <= 50 for item in items)
    assert res["extracted"]["llmDocuments"] == names[:5]
    assert not res["errors"]


async def test_an_toan_thuc_pham_attach_llm_loi_van_dinh_du_file_ten_goc(monkeypatch):
    async def broken_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(attp_attach.ocr, "ocr_per_file", _fake_ocr({"a.pdf": "x", "b.pdf": "y"}))
    monkeypatch.setattr(attp_attach.client, "chat", broken_chat)

    res = await attp_attach.plan([_file("a.pdf"), _file("b.pdf")], {}, None)

    assert [item["documentName"] for item in res["attachments"]] == ["a", "b"]
    assert any("attachment_agent" in err for err in res["errors"])


def test_an_toan_thuc_pham_prompt_chi_theo_ocr_va_du_loai():
    assert "Không dùng tên file" in SYSTEM_PROMPT
    for doc_type in ("don_de_nghi", "gcn_dkkd", "thuyet_minh", "suc_khoe", "tap_huan", "other"):
        assert doc_type in SYSTEM_PROMPT
    assert set(attp_attach._LABELS) | {"other"} == attp_attach._ALLOWED_DOC_TYPES


async def test_an_toan_thuc_pham_attach_hai_tep_trung_ten_khong_lay_nham_ocr(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": text} for f, text in zip(files, ["", "nội dung"])]

    seen = []

    async def fake_chat(messages, max_tokens, enable_thinking):
        payload = json.loads(messages[1]["content"].split("\n")[1])
        seen.extend(item["index"] for item in payload)
        return json.dumps({"documents": [{"index": 1, "docType": "tap_huan", "title": ""}]})

    monkeypatch.setattr(attp_attach.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(attp_attach.client, "chat", fake_chat)

    res = await attp_attach.plan([_file("image.pdf"), _file("image.pdf")], {}, None)

    assert seen == [1], "chỉ tệp có OCR mới gửi LLM, theo vị trí chứ không theo tên"
    assert [item["documentName"] for item in res["attachments"]] == [
        "image", "Danh sách người đã tập huấn kiến thức ATTP",
    ]

