import json

from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import planner
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_dieu_chinh_huu_tri_attach_maps_van_ban_and_skips_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "van-ban.pdf",
                "text": (
                    "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
                    "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
                ),
            },
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố: 031071000001",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps(
            {
                "documents": [
                    {"index": 0, "type": "van_ban_de_nghi_huu_tri", "title": "Văn bản đề nghị trợ cấp hưu trí xã hội"},
                    {"index": 1, "type": "giay_to_tuy_than", "title": "Căn cước công dân"},
                ]
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("van-ban.pdf"), _file("cccd.pdf")], {}, None)

    # Bảng chỉ còn MỘT dòng → mọi file đều vào dòng 1, không bỏ sót.
    assert len(res["attachments"]) == 2
    assert all(item["slotIndex"] == 0 for item in res["attachments"])
    item = res["attachments"][0]
    assert item["fileName"] == "van-ban.pdf"
    assert item["target"] == "fixed-slot"
    assert item["slotIndex"] == 0
    assert item["slotKey"] == "van_ban_de_nghi_huu_tri"
    assert "Văn bản đề nghị" in item["slotName"]
    assert res["attachments"][1]["fileName"] == "cccd.pdf"
    assert any("giấy tờ tùy thân" in err for err in res["errors"])


async def test_dieu_chinh_huu_tri_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "van-ban.pdf",
                "text": (
                    "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
                    "Mẫu số 01\n"
                    "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
                ),
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("van-ban.pdf")], {}, None)

    assert len(res["attachments"]) == 1
    assert res["attachments"][0]["slotKey"] == "van_ban_de_nghi_huu_tri"
    assert any("attachment_agent" in err for err in res["errors"])


def test_dieu_chinh_huu_tri_rule_rejects_explicit_mau_02():
    text = (
        "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
        "Mẫu số 02\n"
        "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
    )

    assert planner.detect_slot_key(text) == ""


# ---------------------------------------------------------------------------
# Hồ sơ thật req_1d66e02a4271: nộp TRÍCH LỤC KHAI TỬ, bị xếp nhầm thành giấy tờ tùy thân và đính vào
# dòng "Một trong các giấy tờ có ảnh…" (add-document-dialog).
# ---------------------------------------------------------------------------
_TRICH_LUC_KHAI_TU = (
    "TỈNH LÂM ĐỒNG UBND PHƯỜNG L. Số: 104/2026/TLKT\n"
    "TRÍCH LỤC KHAI TỬ\n"
    "Họ, chữ đệm, tên: ĐÀO THỊ T.  Ngày, tháng, năm sinh: 12/04/1938\n"
    "Số định danh cá nhân: 0681xxxxxxx\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 0681xxxxxxx, Cục cảnh sát quản lý hành chính về "
    "trật tự xã hội cấp ngày 28/06/2021\n"
    "Đã chết vào lúc 09 giờ 00 phút, ngày 03/09/2026\n"
    "Họ, chữ đệm, tên người đi khai tử: VƯƠNG ĐÌNH P.\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 0680xxxxxxx"
)


def _files_one(name="SKM_550i.pdf"):
    return [{"name": name, "type": "application/pdf"}], [{"name": name, "text": _TRICH_LUC_KHAI_TU}]


def test_trich_luc_khai_tu_khong_bi_xep_thanh_giay_to_tuy_than():
    """Trích lục khai tử NHẮC "Thẻ căn cước công dân số …" trong phần thông tin, nhưng bản thân nó
    KHÔNG phải giấy tờ tùy thân → không được đính vào dòng "Một trong các giấy tờ có ảnh…".
    Vẫn phải được đính (không bỏ sót) vào dòng duy nhất của thủ tục, kèm cảnh báo."""
    files, ocr = _files_one()

    items, warnings = planner.build_plan_items(files, ocr, {0: ""})

    assert len(items) == 1
    assert items[0]["target"] == "fixed-slot"
    assert items[0]["slotIndex"] == 0
    assert all(item.get("target") != "add-document-dialog" for item in items)
    assert any("SKM_550i.pdf" in w for w in warnings)


def test_luoi_keyword_cu_da_bi_go_khoi_luong_quyet_dinh():
    """`is_excluded_document` vẫn khớp nhầm (giữ lại để đối chứng) nhưng KHÔNG còn được dùng để định
    tuyến — nếu ai đó nối lại vào build_plan_items thì test trên sẽ vỡ."""
    assert planner.is_excluded_document(_TRICH_LUC_KHAI_TU) is True
    assert "KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH" in planner.is_excluded_document.__doc__


def test_cccd_cung_vao_dong_1_vi_cong_da_bo_nut_them_giay_to():
    """Cổng đã bỏ thành phần phụ + nút "Thêm giấy tờ" (chốt user 2026-09-15) → CCCD cũng vào dòng 1,
    KHÔNG còn target add-document-dialog. Tên hiển thị vẫn phân biệt để cán bộ soát."""
    files = [{"name": "cccd.pdf", "type": "application/pdf"}]
    ocr = [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN / CITIZEN IDENTITY CARD ..."}]

    items, warnings = planner.build_plan_items(files, ocr, {0: "giay_to_tuy_than"})

    assert len(items) == 1
    assert items[0]["target"] == "fixed-slot"
    assert items[0]["slotIndex"] == 0
    assert "tùy thân" in items[0]["documentName"]
    assert any("giấy tờ tùy thân" in w for w in warnings)


def test_khong_con_bat_ky_target_add_document_dialog_nao():
    files = [{"name": f"{n}.pdf", "type": "application/pdf"} for n in ("a", "b", "c")]
    for llm in ({}, {0: "van_ban_de_nghi_huu_tri", 1: "giay_to_tuy_than", 2: "other"}):
        items, _ = planner.build_plan_items(files, [], llm)
        assert len(items) == 3
        assert all(item["target"] == "fixed-slot" and item["slotIndex"] == 0 for item in items)
        assert all(item["needsAddComponent"] is False for item in items)


def test_tuyet_doi_khong_bo_sot_file_ke_ca_khi_llm_chet():
    """Chốt user: KHÔNG lưới keyword nào (kể cả làm phao) và KHÔNG được bỏ sót file. LLM im lặng →
    mọi file về dòng Văn bản đề nghị kèm cảnh báo, chứ không đoán mò bằng keyword."""
    names = ["khai-tu.pdf", "don.pdf", "cccd.pdf"]
    files = [{"name": n, "type": "application/pdf"} for n in names]
    ocr = [
        {"name": "khai-tu.pdf", "text": _TRICH_LUC_KHAI_TU},
        {"name": "don.pdf", "text": "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI (Mẫu số 01)"},
        {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN / CITIZEN IDENTITY CARD"},
    ]

    items, warnings = planner.build_plan_items(files, ocr, {})

    assert [item["fileIndex"] for item in items] == [0, 1, 2]
    assert all(item["target"] == "fixed-slot" for item in items)
    assert len(warnings) == 3
    # detect_slot_key VẪN nhận ra "don.pdf" nếu bị gọi → chứng minh nó đã bị gỡ khỏi luồng.
    assert planner.detect_slot_key(ocr[1]["text"]) == planner.SLOT["slotKey"]


def test_khong_con_luoi_keyword_nao_trong_luong_quyet_dinh():
    for fn in (planner.is_excluded_document, planner.detect_slot_key):
        assert "KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH" in (fn.__doc__ or ""), fn.__name__


def test_prompt_co_type_rieng_va_chan_bay_trich_luc_khai_tu():
    from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach.prompt import SYSTEM_PROMPT

    assert "giay_to_tuy_than" in SYSTEM_PROMPT
    assert "TRÍCH LỤC KHAI TỬ" in SYSTEM_PROMPT
    assert "KHÔNG biến tài liệu thành giấy tờ" in SYSTEM_PROMPT


def test_slot_name_khop_text_that_cua_cong():
    assert "Mẫu số 01 ban hành kèm theo Nghị định số 176/2025/NĐ-CP" in planner.SLOT["slotName"]


# ---------------------------------------------------------------------------
# Cài đặt "Có tách hồ sơ khi đính kèm" — mẫu theo hồ sơ thật req_e466442af788 (dữ liệu bịa): một PDF 6 trang gồm
# Giấy ủy quyền (trang 1 + trang xác nhận), Văn bản đề nghị Mẫu 01 (2 trang), CCCD bên ủy quyền, CCCD bên được ủy quyền.
# ---------------------------------------------------------------------------
_BO_GOP_TRANG = [
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY ỦY QUYỀN\nI. BÊN ỦY QUYỀN: Ông TRẦN VĂN MẪU sinh năm 1950\n"
    "Căn cước công dân số: 001050000001\nII. BÊN ĐƯỢC ỦY QUYỀN: Bà LÊ THỊ THỬ sinh năm 1980",
    "XÁC NHẬN CỦA CƠ QUAN NHÀ NƯỚC CÓ THẨM QUYỀN\nGIÁM ĐỐC",
    "Mẫu số 01\nVĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\nI. Thông tin người đề nghị trợ cấp hưu trí xã hội\n"
    "1. Họ, chữ đệm, tên: TRẦN VĂN MẪU\n3. Thẻ Căn cước hoặc số định danh cá nhân: 001050000001",
    "10. Tài khoản ngân hàng:\n- Tên tài khoản: Trần Văn Mẫu\nII. Thông tin người giám hộ, người được uỷ quyền (nếu có)\n"
    "7. Tôi xin cam đoan những lời khai trên là đúng sự thật",
    "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: 001050000001\nHọ và tên / Full name: TRẦN VĂN MẪU",
    "CĂN CƯỚC\nIDENTITY CARD\nSố định danh cá nhân: 001080000002\nHọ, chữ đệm và tên khai sinh: LÊ THỊ THỬ",
]
_PAGE_TYPES = [
    "giay_uy_quyen", "giay_uy_quyen", "van_ban_de_nghi_huu_tri", "van_ban_de_nghi_huu_tri",
    "giay_to_tuy_than", "giay_to_tuy_than",
]


def _pdf_file(name: str, pages: int) -> FileItem:
    import base64

    import fitz

    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="doc")


def _ocr_text(pages: list[str]) -> str:
    return "\n\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{p}" for n, p in enumerate(pages))


def _mock_split(monkeypatch, page_types, calls):
    async def fake_ocr_per_file(files):
        return [{"name": "bo-gop.pdf", "text": _ocr_text(_BO_GOP_TRANG)}]

    async def fake_chat(messages, max_tokens, enable_thinking, temperature=None):
        calls.append(messages[0]["content"])
        if messages[0]["content"] == planner.prompt.SPLIT_SYSTEM_PROMPT:
            return json.dumps({"tep": [{"fileIndex": 0, "trang": page_types}]})
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": "Giấy ủy quyền"}]})

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)


async def test_bat_tach_ho_so_cat_bo_gop_thanh_tung_giay(monkeypatch):
    calls: list[str] = []
    _mock_split(monkeypatch, _PAGE_TYPES, calls)

    res = await planner.plan([_pdf_file("bo-gop.pdf", 6)], {"splitDocuments": True}, None)

    items = res["attachments"]
    assert [i["documentName"] for i in items] == [
        "Văn bản đề nghị trợ cấp hưu trí xã hội", "Giấy ủy quyền", "Căn cước công dân",
    ]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [2, 3]}],
        [{"fileIndex": 0, "pageIndexes": [0, 1]}],
        [{"fileIndex": 0, "pageIndexes": [4, 5]}],
    ]
    assert all(i["target"] == "fixed-slot" and i["slotIndex"] == 0 for i in items)
    assert all("/" not in i["documentName"] for i in items)
    # Có Văn bản đề nghị trong bộ → không cảnh báo; chỉ một lượt LLM (xếp loại trang).
    assert res["errors"] == []
    assert calls == [planner.prompt.SPLIT_SYSTEM_PROMPT]
    assert res["extracted"]["splitDocuments"] is True
    assert res["extracted"]["tachGiayTo"][0]["tachGiayTo"] == [
        {"docType": "giay_uy_quyen", "pages": [1, 2]},
        {"docType": "van_ban_de_nghi_huu_tri", "pages": [3, 4]},
        {"docType": "giay_to_tuy_than", "pages": [5, 6]},
    ]


async def test_tat_tach_ho_so_giu_nguyen_tep_nhu_cu(monkeypatch):
    calls: list[str] = []
    _mock_split(monkeypatch, _PAGE_TYPES, calls)

    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        calls.clear()
        res = await planner.plan([_pdf_file("bo-gop.pdf", 6)], options, None)
        assert len(res["attachments"]) == 1
        assert "sourceSegments" not in res["attachments"][0]
        assert planner.prompt.SPLIT_SYSTEM_PROMPT not in calls
        assert res["extracted"]["splitDocuments"] is False


async def test_tach_loi_so_trang_lech_thi_dinh_nguyen_tep(monkeypatch):
    calls: list[str] = []
    _mock_split(monkeypatch, _PAGE_TYPES[:4], calls)

    res = await planner.plan([_pdf_file("bo-gop.pdf", 6)], {"splitDocuments": True}, None)

    assert len(res["attachments"]) == 1
    assert "sourceSegments" not in res["attachments"][0]
    assert res["extracted"]["tachGiayTo"] == []


async def test_tach_pdf_lech_so_trang_ocr_khong_goi_llm_chia_trang(monkeypatch):
    calls: list[str] = []
    _mock_split(monkeypatch, _PAGE_TYPES, calls)

    res = await planner.plan([_pdf_file("bo-gop.pdf", 5)], {"splitDocuments": True}, None)

    assert len(res["attachments"]) == 1
    assert planner.prompt.SPLIT_SYSTEM_PROMPT not in calls


def test_tach_trang_other_ngan_nhap_giay_truoc_va_canh_bao_khi_khong_co_van_ban():
    files = [{"name": "bo-gop.pdf", "type": "application/pdf"}]
    pages = [_BO_GOP_TRANG[0], _BO_GOP_TRANG[1], _BO_GOP_TRANG[4]]
    ocr = [{"name": "bo-gop.pdf", "text": _ocr_text(pages)}]

    items, warnings = planner.build_plan_items(
        files, ocr, {}, {0: ["giay_uy_quyen", "other", "giay_to_tuy_than"]}
    )

    assert [i["sourceSegments"][0]["pageIndexes"] for i in items] == [[0, 1], [2]]
    assert any("không có trang nào là Văn bản đề nghị" in w for w in warnings)


def test_registry_bat_cai_dat_tach_ho_so():
    from app.procedures.registry import PROCEDURES

    cfg = next(p for p in PROCEDURES if p["key"] == "dieu-chinh-huu-tri-xa-hoi")
    assert cfg["supportsSplitDocuments"] is True
