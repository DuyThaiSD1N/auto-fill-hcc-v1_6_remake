import json
import re

from app.pipelines._shared import fold
from app.pipelines.an_toan_thuc_pham.attach import planner as attp_attach
from app.pipelines.an_toan_thuc_pham.attach.prompt import SYSTEM_PROMPT
from app.process.schemas import FileItem

# Tên dòng cột "Tên giấy tờ" trên cổng thật (5 dòng a–e).
_ROW_TEXTS = [
    "a) Đơn đề nghị cấp Giấy chứng nhận (Mẫu số 1 Phụ lục I kèm theo Nghị định số 155/2018/NĐ-CP ngày 13/11/2018);",
    "b) Bản sao Giấy chứng nhận đăng ký kinh doanh hoặc Giấy chứng nhận đăng ký doanh nghiệp có ngành nghề phù hợp "
    "với loại thực phẩm của cơ sở sản xuất (có xác nhận của cơ sở);",
    "c) Bản thuyết minh về cơ sở vật chất, trang thiết bị dụng cụ bảo đảm điều kiện vệ sinh an toàn thực phẩm.",
    "d) Giấy xác nhận đủ sức khỏe của chủ cơ sở và người trực tiếp sản xuất, kinh doanh thực phẩm do cơ sở y tế "
    "tuyến huyện trở lên cấp.",
    "e) Danh sách người sản xuất thực phẩm, kinh doanh dịch vụ ăn uống đã được tập huấn kiến thức an toàn thực "
    "phẩm có xác nhận của chủ cơ sở.",
]
_ROW_TAIL = " 1 Bản chính 1 Bản sao Scan tệp tin Chọn tệp tin"


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _fake_ocr(texts):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": texts.get(f["name"], ""), "provider": "tiengnoi"} for f in files]
    return fake_ocr_per_file


def _fe_fold(value: str) -> str:
    # foldChoiceText của extension: bỏ dấu + chữ thường + gộp khoảng trắng, gạch nối thành dấu cách.
    return re.sub(r"\s*[-–—‐‑]+\s*", " ", fold(value))


def _fe_row_for(item, row_texts):
    """Mô phỏng findFixedSlotInput: dòng ĐẦU (thứ tự DOM) chứa một slotKeyword, không có thì slotIndex."""
    keywords = [_fe_fold(k) for k in item.get("slotKeywords") or []]
    for idx, text in enumerate(row_texts):
        if any(k in _fe_fold(text) for k in keywords):
            return idx
    return item["slotIndex"] if item["slotIndex"] < len(row_texts) else None


async def test_an_toan_thuc_pham_attach_moi_loai_giay_vao_dung_dong(monkeypatch):
    names = ["thuyet-minh.pdf", "don.pdf", "tap-huan.pdf", "dkkd.pdf", "suc-khoe.pdf"]
    texts = {name: "nội dung OCR" for name in names}

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "thuyet_minh", "title": ""},
            {"index": 1, "docType": "don_de_nghi", "title": ""},
            {"index": 2, "docType": "tap_huan", "title": ""},
            {"index": 3, "docType": "gcn_dkkd", "title": ""},
            {"index": 4, "docType": "suc_khoe", "title": ""},
        ]})

    monkeypatch.setattr(attp_attach.ocr, "ocr_per_file", _fake_ocr(texts))
    monkeypatch.setattr(attp_attach.client, "chat", fake_chat)

    res = await attp_attach.plan([_file(n) for n in names], {}, None)
    items = res["attachments"]

    assert [(i["fileName"], i["componentIndex"], i["slotIndex"]) for i in items] == [
        ("thuyet-minh.pdf", 3, 2),
        ("don.pdf", 1, 0),
        ("tap-huan.pdf", 5, 4),
        ("dkkd.pdf", 2, 1),
        ("suc-khoe.pdf", 4, 3),
    ]
    assert {i["target"] for i in items} == {"fixed-slot"}
    assert all(i["repeatUpload"] is True and i["slotKeywords"] for i in items)
    # slotKey cũ "attp_dossier" có sẵn từ khoá trong extension bắt dòng a) → không được dùng lại.
    assert len({i["slotKey"] for i in items}) == 5 and "attp_dossier" not in {i["slotKey"] for i in items}
    assert not res["errors"]

    # FE trên bảng 5 dòng: mỗi tệp vào đúng dòng của nó.
    rows = [text + _ROW_TAIL for text in _ROW_TEXTS]
    assert [_fe_row_for(i, rows) for i in items] == [2, 0, 4, 1, 3]
    # Đính lại sau lần lỗi (cả 5 tệp đang nằm ở dòng a) với tên theo loại giấy): tên tệp không kéo nhầm về dòng a).
    rows_sau_lan_loi = [rows[0] + " " + " ".join(f"{i['documentName']}.pdf" for i in items)] + rows[1:]
    assert [_fe_row_for(i, rows_sau_lan_loi) for i in items] == [2, 0, 4, 1, 3]
    # Cổng gom năm loại vào MỘT dòng "A. Thành phần hồ sơ: a)…e)" → mọi tệp vào dòng đó như trước.
    one_row = ["A. Thành phần hồ sơ: " + " ".join(_ROW_TEXTS) + _ROW_TAIL]
    assert [_fe_row_for(i, one_row) for i in items] == [0] * 5


async def test_an_toan_thuc_pham_attach_giay_khac_vao_dong_don_giu_ten(monkeypatch):
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

    # Không bỏ file nào; CCCD / giấy chưa rõ loại vào dòng a) Đơn.
    assert [item["fileIndex"] for item in items] == [0, 1, 2, 3, 4, 5]
    assert [item["componentIndex"] for item in items] == [1, 4, 4, 1, 1, 1]
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
    assert [c.get("routedTo") for c in res["extracted"]["classified"]] == [
        None, None, None, "don_de_nghi", "don_de_nghi", "don_de_nghi"]
    assert len(res["errors"]) == 1 and "scan-4.pdf, scan-5.pdf, scan-6.pdf" in res["errors"][0]


async def test_an_toan_thuc_pham_attach_llm_loi_van_chia_dong_theo_ocr(monkeypatch):
    async def broken_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    texts = {
        "a.pdf": "x",
        "b.pdf": "y",
        "don.pdf": "ĐƠN ĐỀ NGHỊ CẤP GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM",
        "tm.pdf": "BẢN THUYẾT MINH Về cơ sở vật chất, trang thiết bị, dụng cụ",
        "sk.pdf": "GIẤY KHÁM SỨC KHỎE ... Kết luận: đủ sức khỏe làm việc",
        "hkd.pdf": "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH Số: 27A8000123",
        "th.pdf": "DANH SÁCH NGƯỜI ĐÃ ĐƯỢC TẬP HUẤN KIẾN THỨC AN TOÀN THỰC PHẨM",
    }
    monkeypatch.setattr(attp_attach.ocr, "ocr_per_file", _fake_ocr(texts))
    monkeypatch.setattr(attp_attach.client, "chat", broken_chat)

    res = await attp_attach.plan([_file(n) for n in texts], {}, None)

    assert [(i["documentName"], i["componentIndex"]) for i in res["attachments"]] == [
        ("a", 1), ("b", 1),
        ("Đơn đề nghị cấp Giấy chứng nhận ATTP", 1),
        ("Bản thuyết minh cơ sở vật chất trang thiết bị", 3),
        ("Giấy xác nhận đủ sức khỏe", 4),
        ("Giấy chứng nhận đăng ký kinh doanh", 2),
        ("Danh sách người đã tập huấn kiến thức ATTP", 5),
    ]
    assert any("attachment_agent" in err for err in res["errors"])


def test_an_toan_thuc_pham_prompt_chi_theo_ocr_va_du_loai():
    assert "Không dùng tên file" in SYSTEM_PROMPT
    for doc_type in ("don_de_nghi", "gcn_dkkd", "thuyet_minh", "suc_khoe", "tap_huan", "other"):
        assert doc_type in SYSTEM_PROMPT
    assert set(attp_attach._LABELS) | {"other"} == attp_attach._ALLOWED_DOC_TYPES
    assert set(attp_attach._ROWS) == set(attp_attach._LABELS)


def test_an_toan_thuc_pham_tu_khoa_dong_khong_nam_trong_ten_tep():
    """Từ khoá dòng khớp trên CẢ dòng (gồm tên tệp đã đính) → không được là chuỗi con của tên tệp planner đặt."""
    labels = [_fe_fold(label) for label in attp_attach._LABELS.values()]
    for row in attp_attach._ROWS.values():
        for keyword in row["slotKeywords"]:
            assert not any(_fe_fold(keyword) in label for label in labels), keyword
            assert _fe_fold(keyword) in _fe_fold(row["slotName"]), keyword


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
    assert [(item["documentName"], item["componentIndex"]) for item in res["attachments"]] == [
        ("image", 1), ("Danh sách người đã tập huấn kiến thức ATTP", 5),
    ]
