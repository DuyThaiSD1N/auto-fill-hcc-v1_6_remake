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


def test_cccd_van_bo_qua_vi_khong_co_dong():
    items, _, classified = planner.build_plan_items(_files(["cccd.pdf"]), {0: "cccd"})

    assert items == []
    assert classified[0]["skipped"] is True


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
