"""Cấp mới GPHN giai đoạn chuyển tiếp — đính kèm (trace req_95e5a60db2b9).

Lỗi gốc: "Ảnh thẻ.pdf" có OCR chỉ là watermark "Scanned with CS CamScanner" → rơi vào other → bị BỎ,
chỉ còn 5/6 tệp được đính. Phân loại nay thuần LLM (mọi dấu hiệu ảnh chân dung nằm trong prompt), và
tệp không xếp được loại thì dồn vào dòng Đơn chứ không bỏ.
"""

import asyncio

from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.attach import planner, prompt

_TRACE_FILES = [
    "Ảnh thẻ.pdf", "Bằng cử nhân.pdf", "Đơn đề nghị.pdf", "Gksk.pdf", "GXN BV đa khoa.pdf", "SYLL.pdf",
]


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_ho_so_trong_trace_du_6_tep_vao_dung_6_dong():
    llm_types = {0: "anh_chan_dung", 1: "van_bang", 2: "don_de_nghi", 3: "suc_khoe",
                 4: "thuc_hanh", 5: "so_yeu_ly_lich"}
    items, warnings, _ = planner.build_plan_items(_files(_TRACE_FILES), llm_types)

    assert len(items) == 6, "tuyệt đối không bỏ tệp nào"
    by_file = {i["fileName"]: i["componentName"] for i in items}
    assert by_file["Ảnh thẻ.pdf"] == "02 ảnh chân dung cỡ 04 cm"
    assert by_file["GXN BV đa khoa.pdf"] == "giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07"
    assert all(i["target"] == "attp-row" for i in items)
    assert not warnings


def test_nhan_thuc_hanh_khong_bi_doi_thanh_anh():
    """Bản cũ dò chuỗi con "anh" trong nhãn → "thuc_hanh" bị đổi thành anh_chan_dung."""
    assert planner._normalize_doc_type("thuc_hanh") == "thuc_hanh"
    assert planner._normalize_doc_type("thuc hanh") == "thuc_hanh"
    assert planner._normalize_doc_type("anh_chan_dung") == "anh_chan_dung"
    assert planner._normalize_doc_type("anh the") == "other", "nhãn lạ không được đoán"
    assert planner._normalize_doc_type("") == "other"


def test_tep_khong_xep_duoc_loai_don_vao_dong_don_giu_ten_goc():
    items, warnings, classified = planner.build_plan_items(
        _files(["Đơn đề nghị.pdf", "giay_to_la.pdf"]), {0: "don_de_nghi", 1: "other"},
    )

    assert len(items) == 2
    la = items[1]
    assert la["componentName"] == "Đơn theo Mẫu 08 Phụ lục I"
    assert la["documentName"] == "giay_to_la.pdf", "attp-row đặt tên tệp theo documentName"
    assert la["detectedType"] == "other"
    assert classified[1]["fallbackRow"] == "don_de_nghi"
    assert any("giay_to_la.pdf" in w for w in warnings)


def test_llm_loi_hoan_toan_van_dinh_du_moi_tep():
    items, warnings, classified = planner.build_plan_items(_files(_TRACE_FILES), {})

    assert len(items) == len(_TRACE_FILES)
    assert all(i["componentName"] == "Đơn theo Mẫu 08 Phụ lục I" for i in items)
    assert all(c["source"] == "fallback" for c in classified)
    assert warnings


def test_cccd_don_vao_dong_don_khong_bo():
    """Trace req_8328e84774f7: bản sao CCCD công chứng bị bỏ → chỉ đính 5/6 tệp."""
    items, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "scan-cccd.pdf"]), {0: "don_de_nghi", 1: "cccd"},
    )

    assert len(items) == 2, "tuyệt đối không bỏ tệp nào"
    cccd = items[1]
    assert cccd["componentName"] == "Đơn theo Mẫu 08 Phụ lục I"
    assert cccd["documentName"] == "Bản sao Căn cước công dân"
    assert cccd["detectedType"] == "cccd"
    assert classified[1]["fallbackRow"] == "don_de_nghi"
    assert "skipped" not in classified[1]
    assert not warnings, "CCCD đã nhận đúng loại, không cảnh báo như tệp other"


def test_moi_tep_mot_luot_goi_va_tep_ocr_rong_van_duoc_gui(monkeypatch):
    """Ảnh chân dung hay có OCR rỗng — bản cũ không gửi tệp rỗng cho LLM nên ảnh không bao giờ được xếp."""
    seen = []

    async def _chat(messages, **_kw):
        seen.append(messages[-1]["content"])
        return '{"documents":[{"index":0,"docType":"anh_chan_dung"}]}'

    monkeypatch.setattr(planner.client, "chat", _chat)
    monkeypatch.setattr(planner.client, "extract_json_block", lambda raw: __import__("json").loads(raw))

    docs = [{"index": 0, "name": "Ảnh thẻ.pdf", "text": ""},
            {"index": 1, "name": "x.pdf", "text": "Scanned with CS CamScanner"}]
    result = asyncio.run(planner._classify_with_llm(docs))

    assert result == {0: "anh_chan_dung", 1: "anh_chan_dung"}
    assert len(seen) == 2, "mỗi tệp một lượt gọi"
    assert '"fileName": "Ảnh thẻ.pdf"' in seen[0]


def test_prompt_chua_dau_hieu_anh_chan_dung_thay_cho_rule_code():
    text = prompt.SYSTEM_PROMPT
    assert "Scanned with CamScanner" in text
    assert "RỖNG" in text
    assert "ảnh thẻ" in text
    assert "NGƯỜI LÀM ĐƠN" in text  # bẫy Đơn liệt kê mọi loại
    # Không còn rule nội dung trong code.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_is_image_only")


def _pages(*rows):
    """(docType, giayMoi, tenGiay) từng trang → kết quả LLM theo trang."""
    return [{"trang": n + 1, "docType": t, "giayMoi": new, "tenGiay": name} for n, (t, new, name) in enumerate(rows)]


def test_che_do_tach_moi_giay_mot_tep_ke_ca_cung_loai():
    pages = ["don 1", "don 2", "bang trung cap", "bia", "giay xac nhan", "quyet dinh", "", "kham suc khoe"]
    docs = planner._parse_docs(_pages(
        ("don_de_nghi", True, "Đơn đề nghị"), ("don_de_nghi", False, None),
        ("van_bang", True, "Bằng tốt nghiệp trung cấp"), ("van_bang", False, None),
        ("thuc_hanh", True, "Giấy xác nhận hoàn thành thực hành"), ("thuc_hanh", True, "Quyết định tiếp nhận thực hành"),
        ("other", False, None), ("suc_khoe", True, "Giấy khám sức khỏe"),
    ), len(pages))
    items, warnings, classified = planner.build_plan_items(
        _files(["ho_so_gop.pdf", "Ảnh thẻ.pdf"]), {1: "anh_chan_dung"}, {0: docs}, {0: pages},
    )

    got = [(i["componentName"], i["documentName"], i.get("sourceSegments")) for i in items if i["fileIndex"] == 0]
    assert got == [
        ("Đơn theo Mẫu 08 Phụ lục I", "Đơn đề nghị", [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        ("Văn bằng chuyên môn", "Bằng tốt nghiệp trung cấp", [{"fileIndex": 0, "pageIndexes": [2, 3]}]),
        ("giấy khám sức khỏe do cơ sở khám bệnh", "Giấy khám sức khỏe", [{"fileIndex": 0, "pageIndexes": [7]}]),
        ("giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07", "Giấy xác nhận hoàn thành thực hành",
         [{"fileIndex": 0, "pageIndexes": [4]}]),
        ("giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07", "Quyết định tiếp nhận thực hành",
         [{"fileIndex": 0, "pageIndexes": [5, 6]}]),
    ], "giấy cùng loại tách riêng; trang trắng other nối vào giấy liền trước, không bị bỏ"
    assert items[-1]["componentName"] == "02 ảnh chân dung cỡ 04 cm" and "sourceSegments" not in items[-1]
    assert classified[0]["source"] == "llm-pages"
    assert not warnings


def test_che_do_tach_llm_tra_lech_so_trang_thi_bo_qua():
    assert planner._parse_docs(_pages(("don_de_nghi", True, None)), 2) is None
    assert planner._parse_docs([{"trang": 2, "docType": "don_de_nghi"}, {"trang": 1, "docType": "don_de_nghi"}], 2) is None


def test_che_do_tach_ten_tep_ngan_hon_50_ky_tu_khong_ngoac():
    name = planner._doc_title("", "Đơn đề nghị cấp giấy phép hành nghề (Mẫu 08 PL I NĐ 96/2023)")
    assert name == "Đơn đề nghị cấp giấy phép hành nghề Mẫu 08", "cổng BYT cắt / từ chối tên từ 50 ký tự kể cả .pdf"
    assert len(planner._doc_title("x" * 10 + " " + "y" * 60, "z")) <= 45


def test_che_do_tach_tep_mot_giay_dinh_nguyen_tep():
    docs = planner._parse_docs(_pages(("suc_khoe", True, "Giấy khám sức khỏe"), ("suc_khoe", False, None)), 2)
    items, _, _ = planner.build_plan_items(_files(["gksk.pdf"]), {}, {0: docs}, {0: ["a", "b"]})
    assert len(items) == 1 and "sourceSegments" not in items[0]


def test_tat_tach_khong_goi_xep_loai_theo_trang(monkeypatch):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": "───── Trang 1/2 ─────\nA\n───── Trang 2/2 ─────\nB"} for f in files]

    async def fake_pages(_):
        raise AssertionError("tắt tách thì không xếp loại theo trang")

    async def fake_one(index, name, text):
        return index, "don_de_nghi"

    from app.services import ocr
    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_pages", fake_pages)
    monkeypatch.setattr(planner, "_classify_one", fake_one)

    class F:
        name, type, dataUrl = "don.pdf", "application/pdf", "data:application/pdf;base64,"

    out = asyncio.run(planner.plan([F()], {}))
    assert len(out["attachments"]) == 1 and out["extracted"]["splitDocuments"] is False
