import json

from app.pipelines.khai_sinh_lien_thong.attach import planner as khai_sinh
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {"request_id": "req_khai_sinh_test", "procedure": "khai-sinh-dang-ky", "fields": []}


async def test_khai_sinh_attach_picks_birth_proof_into_single_slot(monkeypatch):
    """Giấy chứng sinh + CCCD cha/mẹ: tất cả vào STT1 dưới dạng NHIỀU TỆP RỜI (không gộp PDF)."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 040203015844"},
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "cccd-me.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012193000851"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "other"},
            {"index": 1, "docType": "birth_proof"},
            {"index": 2, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("cccd-bo.pdf"), _file("chung-sinh.pdf"), _file("cccd-me.pdf")], {}, _session()
    )
    items = res["attachments"]

    # Trang cho nhiều tệp/hàng → chứng sinh + 2 CCCD là 3 item RỜI cùng ô STT1, KHÔNG gộp PDF.
    assert len(items) == 3
    assert all(it["target"] == "fixed-slot" and it["slotIndex"] == 0 for it in items)
    assert all(it["repeatUpload"] is True for it in items)
    assert all("sourceFileIndexes" not in it for it in items)
    # Thủ tục này giữ nguyên tên file gốc; nhãn loại giấy chỉ nằm ở slotName/componentName.
    assert [it["documentName"] for it in items] == ["chung-sinh", "cccd-bo", "cccd-me"]
    # Chứng sinh trước, rồi các "other" (CCCD cha/mẹ) theo thứ tự file.
    assert [it["fileIndex"] for it in items] == [1, 0, 2]
    assert [it["fileName"] for it in items] == ["chung-sinh.pdf", "cccd-bo.pdf", "cccd-me.pdf"]
    assert res["extracted"]["birthProof"] == "chung-sinh.pdf"
    assert res["extracted"]["residenceForm"] is None
    assert res["extracted"]["skipped"] == []


async def test_khai_sinh_attach_two_slots_with_residence_form(monkeypatch):
    """Có cả giấy chứng sinh + tờ khai thay đổi thông tin cư trú → đính 2 ô đúng vị trí."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "cu-tru.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
            {"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "birth_proof"},
            {"index": 1, "docType": "residence_form"},
            {"index": 2, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("chung-sinh.pdf"), _file("cu-tru.pdf"), _file("cccd-bo.pdf")], {}, _session()
    )
    items = res["attachments"]

    # STT1 nhận chứng sinh + CCCD bố (2 tệp RỜI, repeatUpload); STT2 tách riêng tờ khai cư trú.
    assert len(items) == 3
    stt1 = [it for it in items if it["slotIndex"] == 0]
    stt2 = [it for it in items if it["slotIndex"] == 1]
    assert [it["fileIndex"] for it in stt1] == [0, 2]   # chứng sinh trước, rồi CCCD bố
    assert all(it["repeatUpload"] is True and "sourceFileIndexes" not in it for it in stt1)
    assert [it["documentName"] for it in stt1] == ["chung-sinh", "cccd-bo"]
    assert len(stt2) == 1
    assert stt2[0]["fileName"] == "cu-tru.pdf"
    assert stt2[0]["documentName"] == "cu-tru"
    assert "repeatUpload" not in stt2[0]   # STT2 chỉ 1 tệp, không cần lặp menu
    assert all(it["target"] == "fixed-slot" for it in items)
    assert res["extracted"]["birthProof"] == "chung-sinh.pdf"
    assert res["extracted"]["residenceForm"] == "cu-tru.pdf"
    assert res["extracted"]["skipped"] == []


async def test_khai_sinh_attach_residence_form_rule_fallback(monkeypatch):
    """LLM lỗi → rule nhận ra tờ khai cư trú qua nội dung OCR và vẫn đính ô STT2."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "f1.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "f2.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("f1.pdf"), _file("f2.pdf")], {}, _session()
    )
    by_slot = {it["slotIndex"]: it for it in res["attachments"]}

    assert by_slot[0]["fileName"] == "f1.pdf"
    assert by_slot[1]["fileName"] == "f2.pdf"
    assert by_slot[1]["documentName"] == "f2"


async def test_khai_sinh_attach_rule_fallback_when_llm_fails(monkeypatch):
    """LLM lỗi → rule theo nội dung OCR vẫn nhận ra văn bản người làm chứng về việc sinh."""
    async def fake_ocr_per_file(files):
        return [{"name": "lam-chung.pdf", "text": "VĂN BẢN NGƯỜI LÀM CHỨNG XÁC NHẬN VỀ VIỆC SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments([_file("lam-chung.pdf")], {}, _session())
    items = res["attachments"]

    assert len(items) == 1
    assert items[0]["fileName"] == "lam-chung.pdf"
    assert items[0]["target"] == "fixed-slot"


async def test_khai_sinh_attach_no_birth_proof(monkeypatch):
    """Không có giấy chứng sinh → VẪN đính giấy tờ khác vào ô STT1, kèm lời nhắc bổ sung chứng sinh."""
    async def fake_ocr_per_file(files):
        return [{"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "other"}]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments([_file("cccd-bo.pdf")], {}, _session())

    items = res["attachments"]
    assert [(it["fileName"], it["slotIndex"], it["detectedType"]) for it in items] == [("cccd-bo.pdf", 0, "other")]
    assert items[0]["repeatUpload"] is True and items[0]["fallbackSlotIndex"] == 1
    assert res["extracted"]["birthProof"] is None and res["extracted"]["skipped"] == []
    assert any("Không tìm thấy giấy chứng sinh" in e and "cần bổ sung" in e for e in res["errors"])


async def test_khai_sinh_attach_keeps_identity_and_marriage_as_other(monkeypatch):
    """LLM chạy trước, nhưng CCCD/giấy kết hôn không được chiếm 2 ô cố định."""
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "cccd-kiet.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card\nHọ và tên / Full name: VÕ TUẤN KIỆT",
            },
            {
                "name": "cccd-vi.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card\nHọ và tên / Full name: KIỀU THỊ THÙY VI",
            },
            {
                "name": "ket-hon.pdf",
                "text": "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên vợ: KIỀU THỊ THÙY VI",
            },
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH\nĐã sinh con vào lúc 03 giờ 15"},
            {"name": "ct01.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # Cố tình mô phỏng LLM trả sai để chứng minh validation sau LLM không ép
        # CCCD/giấy kết hôn vào hai ô và rule vẫn cứu giấy tờ đích rõ ràng.
        return json.dumps({"documents": [
            {"index": 0, "docType": "birth_proof"},
            {"index": 1, "docType": "residence_form"},
            {"index": 2, "docType": "birth_proof"},
            {"index": 3, "docType": "other"},
            {"index": 4, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [
            _file("cccd-kiet.pdf"),
            _file("cccd-vi.pdf"),
            _file("ket-hon.pdf"),
            _file("chung-sinh.pdf"),
            _file("ct01.pdf"),
        ],
        {},
        _session(),
    )

    items = res["attachments"]
    stt1 = [it for it in items if it["slotIndex"] == 0]
    stt2 = [it for it in items if it["slotIndex"] == 1]
    # chứng sinh (idx3) trước, rồi CCCD×2 + kết hôn (idx0,1,2 = "other") — mỗi tệp RỜI vào STT1.
    assert [it["fileIndex"] for it in stt1] == [3, 0, 1, 2]
    assert all(it["repeatUpload"] is True and "sourceFileIndexes" not in it for it in stt1)
    assert stt1[0]["fileName"] == "chung-sinh.pdf"
    assert len(stt2) == 1 and stt2[0]["fileName"] == "ct01.pdf"
    assert res["extracted"]["skipped"] == []
    by_name = {item["fileName"]: item["docType"] for item in res["extracted"]["classified"]}
    assert by_name["cccd-kiet.pdf"] == "other"
    assert by_name["cccd-vi.pdf"] == "other"
    assert by_name["ket-hon.pdf"] == "other"
    assert res["extracted"]["llmDocuments"] == [
        "cccd-kiet.pdf", "cccd-vi.pdf", "ket-hon.pdf", "chung-sinh.pdf", "ct01.pdf"
    ]


async def test_khai_sinh_llm_result_uses_explicit_index_not_output_order(monkeypatch):
    """LLM được phép trả đảo thứ tự; nhãn vẫn phải theo index gốc, không theo vị trí mảng."""
    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 3, "docType": "birth_proof"},
            {"index": 5, "docType": "residence_form"},
            {"index": 0, "docType": "other"},
            {"index": 1, "docType": "other"},
            {"index": 2, "docType": "other"},
            {"index": 4, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    docs = [{"index": idx, "fileName": f"f{idx}.pdf", "text": "không rõ"} for idx in range(6)]

    classified = await khai_sinh._classify_with_llm(docs)

    assert classified[3] == "birth_proof"
    assert classified[5] == "residence_form"
    assert classified[0] == "other"


async def test_khai_sinh_attach_keeps_original_names_and_numbers_duplicates(monkeypatch):
    """Nhiều tệp cùng ô STT1 phải khác tên (cổng chặn trùng tên); tên gốc trùng thì tệp sau thêm số."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "đk kết hôn.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "birth_proof"},
            {"index": 1, "docType": "other"},
            {"index": 2, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("image.pdf"), _file("image.pdf"), _file("đk kết hôn.pdf")], {}, _session()
    )
    items = res["attachments"]

    assert [it["documentName"] for it in items] == ["image", "image 2", "đk kết hôn"]
    assert all(it["slotName"] == "Giấy chứng sinh" for it in items)


async def test_khai_sinh_attach_renames_messy_file_names(monkeypatch):
    """Tên gốc có ký tự đặc biệt / chuỗi ngẫu nhiên cổng không nhận → đặt lại theo loại giấy, vẫn khác tên nhau."""
    names = [
        "att.x9Kq2LmZ_Pw7Rt3Vb8YnQ4.pdf",  # dấu chấm giữa tên + "_" (tên tệp tải từ Zalo)
        "IMG_20261112_101010.pdf",
        "Scan (1).pdf",
        "image-5.pdf",                    # tên sạch → giữ nguyên
        "Abc9xYz8Qw7Er6Ty5.pdf",          # chuỗi ngẫu nhiên không ký tự đặc biệt
    ]

    async def fake_ocr_per_file(files):
        return [{"name": n, "text": ""} for n in names]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "other"},
            {"index": 1, "docType": "birth_proof"},
            {"index": 2, "docType": "other"},
            {"index": 3, "docType": "other"},
            {"index": 4, "docType": "residence_form"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments([_file(n) for n in names], {}, _session())
    by_index = {it["fileIndex"]: it["documentName"] for it in res["attachments"]}

    assert by_index == {
        0: "Giấy tờ khác",
        1: "Giấy chứng sinh",
        2: "Giấy tờ khác 2",
        3: "image-5",
        4: "Tờ khai thay đổi thông tin cư trú",
    }
    # fileName vẫn là tên gốc để extension tìm đúng tệp người dùng tải lên.
    assert {it["fileName"] for it in res["attachments"]} == set(names)


def _noisy_pdf(seed: int, side: int = 1100) -> str:
    """PDF một trang ảnh nhiễu màu (nén JPEG rất kém) ~1 MB — giống ảnh chụp điện thoại."""
    import base64
    import random

    import pymupdf

    samples = random.Random(seed).randbytes(side * side * 3)
    pix = pymupdf.Pixmap(pymupdf.csRGB, side, side, samples, False)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=pix.tobytes("jpeg", jpg_quality=90))
    return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def test_chia_ngan_sach_dong_tep_nho_giu_nguyen_phan_du_cho_tep_lon():
    # Tệp 1 nhỏ giữ nguyên; 2 tệp lớn chia phần còn lại, giấy chứng sinh (trọng số 2) gấp đôi.
    shares = khai_sinh._slot_shares({0: 300, 1: 2_000, 2: 2_000}, {0: 1, 1: 2, 2: 1}, 1_500)
    assert shares == {1: 800, 2: 400}
    assert khai_sinh._slot_shares({0: 500, 1: 600}, {0: 1, 1: 1}, 2_000) == {}


async def test_khai_sinh_nhieu_tep_cung_dong_nen_tong_duoi_2_6mb(monkeypatch):
    """Req 12/11: 6 tệp ~1 MB cùng dòng chứng sinh → tổng ~6 MB, cổng chặn 2,6 MB/dòng."""
    names = [f"giay-{i}.pdf" for i in range(6)]
    files = [FileItem(name=n, type="application/pdf", dataUrl=_noisy_pdf(i), role="doc") for i, n in enumerate(names)]

    async def fake_ocr_per_file(files):
        return [{"name": n, "text": ""} for n in names]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": i, "docType": "birth_proof" if i == 0 else "other"}
                                         for i in range(6)]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)

    res = await khai_sinh.plan_khai_sinh_attachments(files, {}, _session())
    replaced = res["replaceFiles"] or {}

    def size(i):
        if str(i) in replaced:
            return replaced[str(i)]["bytes"]
        return len(khai_sinh._decode(files[i].dataUrl))

    assert sum(len(khai_sinh._decode(f.dataUrl)) for f in files) > 2_600_000
    assert all(it["slotIndex"] == 0 for it in res["attachments"])
    assert sum(size(i) for i in range(6)) <= khai_sinh.SLOT_BUDGET_BYTES
    # Giấy chứng sinh giữ nét hơn (được phần lớn hơn) giấy tờ khác.
    assert size(0) >= max(size(i) for i in range(1, 6))
    assert not [e for e in res["errors"] if "vượt giới hạn" in e]


def test_khai_sinh_procedure_has_attachment_step():
    proc = get_procedure("khai-sinh-dang-ky-thuong")

    assert proc["hasAttachmentStep"] is True


_GHEP_KET_HON_CHUNG_SINH = (
    "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên vợ: NGUYỄN THỊ A\nHọ, chữ đệm, tên chồng: TRẦN VĂN B\n"
    "PHẦN GHI CHÚ NHỮNG THÔNG TIN THAY ĐỔI SAU NÀY\n"
    # Trang giấy chứng sinh — OCR mất tiêu đề, chỉ còn các ô của mẫu.
    "SỞ Y TẾ\nBỆNH VIỆN SẢN NHI\nMã số GCS: GCS.00000.GCS.00000.00\nCấp lần đầu: [X]\n"
    "Đã sinh con vào lúc: 10 giờ 30 phút, ngày 01 tháng 01 năm 2026\nSố con trong lần sinh này: 1\n"
    "Giới tính của con: Nữ\nCân nặng: 3000 gam\nNgười đỡ đẻ\nĐại diện cơ sở KBCB"
)


async def test_khai_sinh_scan_ghep_ket_hon_va_chung_sinh_mat_tieu_de_van_vao_o_chung_sinh(monkeypatch):
    """Một PDF ghép: trang đầu giấy kết hôn, trang sau giấy chứng sinh (OCR mất tiêu đề). Trước đây
    cả tệp bị xếp `other` → không có ô chứng sinh → kế hoạch đính kèm rỗng."""
    async def fake_ocr_per_file(files):
        return [{"name": "Scan_0001.pdf", "text": _GHEP_KET_HON_CHUNG_SINH}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "other"}]})  # LLM trượt như trace thật

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    res = await khai_sinh.plan_khai_sinh_attachments([_file("Scan_0001.pdf")], {}, _session())
    assert res["extracted"]["birthProof"] == "Scan_0001.pdf"
    assert [(it["fileName"], it["slotIndex"]) for it in res["attachments"]] == [("Scan_0001.pdf", 0)]


def test_prompt_dan_doc_het_file_ghep_va_nhan_mau_chung_sinh_khi_mat_tieu_de():
    from app.pipelines.khai_sinh_lien_thong.attach import prompt
    assert "BẢN SCAN GHÉP NHIỀU GIẤY" in prompt.SYSTEM_PROMPT
    assert "Mã số GCS" in prompt.SYSTEM_PROMPT
    long_text = "x " * 2000 + "Mã số GCS"
    assert "Mã số GCS" in prompt.build_user_prompt([{"index": 0, "fileName": "a.pdf", "text": long_text}])


async def test_khai_sinh_moi_chung_sinh_vao_stt1_moi_to_khai_cu_tru_vao_stt2_con_lai_stt1_du_phong_stt2(monkeypatch):
    """Quy tắc ô: giấy chứng sinh + tệp ghép có giấy chứng sinh → STT1 (không bao giờ dời);
    tờ khai cư trú → STT2; giấy khác → STT1, dự phòng STT2. Đúng cho MỌI tệp, kể cả tệp cùng loại thứ hai."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: TRẦN VĂN B"},
            {"name": "chung-sinh-1.pdf", "text": "GIẤY CHỨNG SINH\nĐã sinh con vào lúc 08 giờ"},
            {"name": "ct01-a.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
            {"name": "ghep.pdf", "text": _GHEP_KET_HON_CHUNG_SINH},
            {"name": "ct01-b.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
            {"name": "ket-hon.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên vợ: NGUYỄN THỊ A"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": i, "docType": "other"} for i in range(6)]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file(n) for n in ("cccd.pdf", "chung-sinh-1.pdf", "ct01-a.pdf", "ghep.pdf", "ct01-b.pdf", "ket-hon.pdf")],
        {}, _session())
    by_name = {it["fileName"]: it for it in res["attachments"]}
    for name in ("chung-sinh-1.pdf", "ghep.pdf"):
        assert by_name[name]["slotIndex"] == 0 and "fallbackSlotIndex" not in by_name[name], name
    for name in ("ct01-a.pdf", "ct01-b.pdf"):
        assert by_name[name]["slotIndex"] == 1 and by_name[name]["repeatUpload"] is True, name
    for name in ("cccd.pdf", "ket-hon.pdf"):
        assert by_name[name]["slotIndex"] == 0 and by_name[name]["fallbackSlotIndex"] == 1, name
    # Giấy chứng sinh đứng trước trong STT1.
    assert [it["fileName"] for it in res["attachments"] if it["slotIndex"] == 0][:2] == ["chung-sinh-1.pdf", "ghep.pdf"]
    assert res["extracted"]["skipped"] == []


async def test_khai_sinh_nen_tep_tren_2mb_tra_replace_files(monkeypatch):
    """Tệp trên 2 MB được nén như form DVC quốc gia mới: bản nén ở replaceFiles, fileName theo bản nén."""
    import base64

    from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach import planner as dvc_moi

    async def fake_ocr_per_file(files):
        return [{"name": "chung-sinh.jpg", "text": "GIẤY CHỨNG SINH"}, {"name": "cccd-me.pdf", "text": "CĂN CƯỚC"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "birth_proof"}, {"index": 1, "docType": "other"}]})

    def fake_entry(file, raw, limit):
        return {"name": file["name"].rsplit(".", 1)[0] + ".pdf", "type": "application/pdf", "dataUrl": "data:,",
                "originalBytes": len(raw), "bytes": limit - 1, "level": "test"}

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    monkeypatch.setattr(dvc_moi, "_shrunk_entry", fake_entry)
    big = FileItem(name="chung-sinh.jpg", type="image/jpeg", role="doc",
                   dataUrl="data:image/jpeg;base64," + base64.b64encode(b"x" * 2_100_000).decode())
    small = FileItem(name="cccd-me.pdf", type="application/pdf", role="doc",
                     dataUrl="data:application/pdf;base64," + base64.b64encode(b"x" * 500_000).decode())
    res = await khai_sinh.plan_khai_sinh_attachments([big, small], {}, _session())

    assert set(res["replaceFiles"]) == {"0"}  # tệp nhỏ để nguyên
    assert res["replaceFiles"]["0"]["bytes"] <= dvc_moi.MAX_FILE_BYTES
    by_index = {it["fileIndex"]: it for it in res["attachments"]}
    assert by_index[0]["fileName"] == "chung-sinh.pdf" and by_index[0]["slotIndex"] == 0
    assert by_index[1]["fileName"] == "cccd-me.pdf"
    assert res["extracted"]["shrunk"][0]["originalBytes"] == 2_100_000
    assert not [e for e in res["errors"] if "nén" in e]


_SONG_LIEU = {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Song Liễu"}
_ONLY = khai_sinh.ONLY_BIRTH_PROOF_OPTION


def test_song_lieu_bat_co_chi_dinh_giay_chung_sinh_theo_tai_khoan():
    key = khai_sinh.PROCEDURE_KEY
    assert khai_sinh.with_khai_sinh_attach_options({}, _SONG_LIEU, key) == {_ONLY: True}
    # Viết không dấu / không tiền tố vẫn nhận.
    assert khai_sinh.with_khai_sinh_attach_options({}, {"tinh": "Bac Ninh", "xa": "Song Lieu"}, key)[_ONLY] is True
    # Client không tự bật được; tỉnh khác, xã khác tên gần giống, thủ tục khác → không có cờ.
    assert _ONLY not in khai_sinh.with_khai_sinh_attach_options(
        {_ONLY: True}, {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Hiệp Hòa"}, key)
    assert _ONLY not in khai_sinh.with_khai_sinh_attach_options({}, {"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Song Liễu"}, key)
    assert _ONLY not in khai_sinh.with_khai_sinh_attach_options({}, {"tinh": "Tỉnh Bắc Ninh", "xa": "Xã Song Liễu Mới"}, key)
    assert _ONLY not in khai_sinh.with_khai_sinh_attach_options({}, _SONG_LIEU, "khai-sinh-dang-ky-thuong")
    assert _ONLY not in khai_sinh.with_khai_sinh_attach_options({}, None, key)


def test_nghia_lo_van_chi_bo_to_khai_khong_bat_co_song_lieu():
    opts = khai_sinh.with_khai_sinh_attach_options(
        {}, {"tinh": "Tỉnh Quảng Ngãi", "xa": "Phường Nghĩa Lộ"}, khai_sinh.PROCEDURE_KEY)
    assert opts == {khai_sinh.OMIT_BIRTH_DECLARATION_OPTION: True}


def test_router_va_tro_ly_deu_goi_cau_hinh_khai_sinh_theo_tai_khoan():
    """Auto Fill (router đính kèm) và trợ lý (pipeline_runner) cùng đặt cờ từ tài khoản server."""
    import inspect

    from app.attachments import router as attach_router
    from app.channels.handfree.chat import pipeline_runner

    assert "with_khai_sinh_attach_options(options, user, body.procedure)" in inspect.getsource(attach_router)
    assert "with_khai_sinh_attach_options(attach_options, owner_user, procedure_key)" in inspect.getsource(
        pipeline_runner)


_TO_KHAI_KHAI_SINH = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI ĐĂNG KÝ KHAI SINH\nKính gửi: UBND phường\n"
    "Họ, chữ đệm, tên người yêu cầu: NGUYỄN VĂN A\nĐề nghị cơ quan đăng ký khai sinh cho người dưới đây\n"
    "Tôi cam đoan nội dung đề nghị đăng ký khai sinh trên đây là đúng sự thật"
)


async def test_song_lieu_chi_dinh_giay_chung_sinh_vao_stt1(monkeypatch):
    """Cờ onlyBirthProof: chỉ giấy chứng sinh lên STT1; tờ khai khai sinh, CT01, CCCD, kết hôn không đính,
    không báo "Bỏ qua file" mà ghi chú theo cấu hình."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-me.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: NGUYỄN THỊ B"},
            {"name": "to-khai.pdf", "text": _TO_KHAI_KHAI_SINH},
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH\nĐã sinh con vào lúc 08 giờ"},
            {"name": "ct01.pdf", "text": "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\nMẫu CT01"},
            {"name": "ket-hon.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên vợ: NGUYỄN THỊ B"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # LLM nhận nhầm tờ khai là chứng sinh — rule vẫn phải giữ tờ khai ngoài ô.
        return json.dumps({"documents": [
            {"index": 0, "docType": "other"},
            {"index": 1, "docType": "birth_proof"},
            {"index": 2, "docType": "birth_proof"},
            {"index": 3, "docType": "residence_form"},
            {"index": 4, "docType": "other"},
        ]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    names = ("cccd-me.pdf", "to-khai.pdf", "chung-sinh.pdf", "ct01.pdf", "ket-hon.pdf")
    res = await khai_sinh.plan_khai_sinh_attachments([_file(n) for n in names], {_ONLY: True}, _session())

    items = res["attachments"]
    assert [(it["fileName"], it["slotIndex"]) for it in items] == [("chung-sinh.pdf", 0)]
    assert "fallbackSlotIndex" not in items[0]
    assert res["extracted"]["birthProof"] == "chung-sinh.pdf"
    assert res["extracted"]["onlyBirthProofOmitted"] == ["cccd-me.pdf", "to-khai.pdf", "ct01.pdf", "ket-hon.pdf"]
    assert res["extracted"]["skipped"] == []
    assert [e for e in res["errors"] if e.startswith(khai_sinh.ONLY_BIRTH_PROOF_NOTE)] == [
        f"{khai_sinh.ONLY_BIRTH_PROOF_NOTE}: cccd-me.pdf, to-khai.pdf, ct01.pdf, ket-hon.pdf"
    ]
    assert not [e for e in res["errors"] if e.startswith("Bỏ qua file")]
    # Mọi tệp vẫn có trong classified → extension không báo "chưa vào hồ sơ" vì vượt dung lượng.
    assert [c["fileName"] for c in res["extracted"]["classified"]] == list(names)


async def test_song_lieu_tep_ghep_to_khai_va_chung_sinh_van_dinh(monkeypatch):
    """Tệp ghép tờ khai + trang giấy chứng sinh (còn ô mẫu GCS) → vẫn là giấy chứng sinh, vẫn đính."""
    async def fake_ocr_per_file(files):
        return [{"name": "ghep.pdf", "text": _TO_KHAI_KHAI_SINH + "\n" + _GHEP_KET_HON_CHUNG_SINH}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "other"}]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    res = await khai_sinh.plan_khai_sinh_attachments([_file("ghep.pdf")], {_ONLY: True}, _session())

    assert [(it["fileName"], it["slotIndex"]) for it in res["attachments"]] == [("ghep.pdf", 0)]
    assert res["extracted"]["onlyBirthProofOmitted"] == []


async def test_song_lieu_khong_co_chung_sinh_thi_khong_dinh_gi(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "to-khai.pdf", "text": _TO_KHAI_KHAI_SINH},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "other"}, {"index": 1, "docType": "other"}]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("cccd-bo.pdf"), _file("to-khai.pdf")], {_ONLY: True}, _session())

    assert res["attachments"] == []
    assert res["extracted"]["birthProof"] is None
    assert res["extracted"]["onlyBirthProofOmitted"] == ["cccd-bo.pdf", "to-khai.pdf"]
    assert any(e.startswith("Không tìm thấy giấy chứng sinh") for e in res["errors"])
    assert not any("đã đính các giấy tờ khác" in e for e in res["errors"])


async def test_khong_co_co_thi_to_khai_va_giay_khac_van_dinh_nhu_cu(monkeypatch):
    """Tài khoản khác (không cờ): tờ khai khai sinh + CCCD vẫn lên STT1 như trước."""
    async def fake_ocr_per_file(files):
        return [
            {"name": "chung-sinh.pdf", "text": "GIẤY CHỨNG SINH"},
            {"name": "to-khai.pdf", "text": _TO_KHAI_KHAI_SINH},
            {"name": "cccd-bo.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": i, "docType": "other"} for i in range(3)]})

    monkeypatch.setattr(khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_sinh.client, "chat", fake_chat)
    res = await khai_sinh.plan_khai_sinh_attachments(
        [_file("chung-sinh.pdf"), _file("to-khai.pdf"), _file("cccd-bo.pdf")], {}, _session())

    assert sorted(it["fileName"] for it in res["attachments"]) == ["cccd-bo.pdf", "chung-sinh.pdf", "to-khai.pdf"]
    assert res["extracted"]["onlyBirthProofOmitted"] == []
