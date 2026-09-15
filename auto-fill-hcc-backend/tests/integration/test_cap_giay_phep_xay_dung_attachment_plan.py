import json

from app.pipelines.cap_giay_phep_xay_dung.attach import planner
from app.pipelines.cap_giay_phep_xay_dung.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, file_type="application/pdf"):
    return FileItem(name=name, type=file_type, dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_cap_giay_phep_xay_dung_routes_sample_house_documents_to_fixed_slots(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "Căn cươc CD Chinh.pdf": (
                "CĂN CƯỚC CÔNG DÂN\n"
                "Số / No.: 027077015515\n"
                "Họ và tên / Full name: NGUYỄN TRUNG CHÍNH\n"
                "IDVNM027077015515"
            ),
            "Đơn đề nghị cấp phép xây nhà 2026.pdf": (
                "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG\n"
                "Sử dụng cho công trình: Không theo tuyến/Nhà ở riêng lẻ/sửa chữa, cải tạo\n"
                "Tên chủ đầu tư (tên chủ hộ): Ông NGUYỄN TRUNG CHÍNH\n"
                "Gửi kèm theo Đơn này các tài liệu: Bản sao giấy tờ chứng minh quyền sử dụng đất."
            ),
            "Bản cam ket xây nhà 2026.pdf": (
                "BẢN CAM KẾT\n"
                "V/v Đảm bảo an toàn đối với công trình liền kề\n"
                "Ông: NGUYỄN TRUNG CHÍNH xin cam kết khi xây nhà."
            ),
            "Bản kê khai kinh nghiệm thiết kế.pdf": (
                "BẢN KÊ KHAI KINH NGHIỆM CỦA TỔ CHỨC, CÁ NHÂN THIẾT KẾ\n"
                "Tổ chức thiết kế: Công ty cổ phần tư vấn đầu tư xây dựng ARECO\n"
                "Chủ trì thiết kế các bộ môn: Kiến trúc: Nguyễn Văn Lục."
            ),
            "Bản vẽ xin cấp phép xây dựng.pdf": (
                "HỒ SƠ XIN CẤP PHÉP XÂY DỰNG\n"
                "CÔNG TRÌNH: NHÀ Ở GIA ĐÌNH\n"
                "MẶT BẰNG TẦNG 1\n"
                "MẶT ĐỨNG TRỤC 1-4\n"
                "MẶT BẰNG MÓNG\n"
                "TỔNG MẶT BẰNG CẤP NƯỚC, THOÁT NƯỚC, CẤP ĐIỆN"
            ),
            "Chứng chỉ năng lực HĐXD ARECO 2025.pdf": (
                "CHỨNG CHỈ NĂNG LỰC HOẠT ĐỘNG XÂY DỰNG\n"
                "Tên tổ chức: CÔNG TY CỔ PHẦN TƯ VẤN ĐẦU TƯ XÂY DỰNG ARECO\n"
                "Giấy chứng nhận đăng ký doanh nghiệp số: 2301199858"
            ),
            "Nguyễn Văn Lục KT.pdf": (
                "CHỨNG CHỈ HÀNH NGHỀ KIẾN TRÚC\n"
                "Số: BAN-00000047\n"
                "Cấp cho: Ông Nguyễn Văn Lục\n"
                "Nội dung được phép hành nghề kiến trúc: Thiết kế kiến trúc công trình"
            ),
            "Sổ đỏ 1.jpg": (
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\n"
                "Ông NGUYỄN TRUNG CHÍNH\n"
                "Thửa đất số 604, tờ bản đồ số 3."
            ),
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            # index PHẢI khớp đúng thứ tự file gửi vào plan() bên dưới (0-based). Fixture cũ bị lệch
            # một nhịp (0="other", 1=land cho chính tệp Đơn) nên test fail vĩnh viễn.
            "congTrinhNhanh": "nha_o_rieng_le",
            "documents": [
                {"index": 0, "type": "identity_document", "title": "Căn cước công dân"},
                {"index": 1, "type": "building_permit_application", "title": "Đơn đề nghị cấp phép xây dựng"},
                {"index": 2, "type": "safety_commitment", "title": "Bản cam kết xây nhà"},
                {"index": 3, "type": "design_experience_declaration", "title": "Bản kê khai kinh nghiệm thiết kế"},
                {"index": 4, "type": "construction_design_drawings", "title": "Bản vẽ xin cấp phép xây dựng"},
                {"index": 5, "type": "construction_capacity_certificate", "title": "Chứng chỉ năng lực"},
                {"index": 6, "type": "architect_practice_certificate", "title": "Chứng chỉ hành nghề"},
                {"index": 7, "type": "land_legal_document", "title": "Giấy chứng nhận quyền sử dụng đất"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [
            _file("Căn cươc CD Chinh.pdf"),
            _file("Đơn đề nghị cấp phép xây nhà 2026.pdf"),
            _file("Bản cam ket xây nhà 2026.pdf"),
            _file("Bản kê khai kinh nghiệm thiết kế.pdf"),
            _file("Bản vẽ xin cấp phép xây dựng.pdf"),
            _file("Chứng chỉ năng lực HĐXD ARECO 2025.pdf"),
            _file("Nguyễn Văn Lục KT.pdf"),
            _file("Sổ đỏ 1.jpg", "image/jpeg"),
        ],
        {},
        {"request_id": "req_gpxd"},
    )
    items = res["attachments"]

    assert len(items) == 8
    assert all(item["target"] == "fixed-slot" for item in items)
    assert all(item["needsAddComponent"] is False for item in items)
    assert all("sourceFileIndexes" not in item for item in items)

    by_slot = {}
    for item in items:
        by_slot.setdefault(item["slotKey"], []).append(item)

    # Bảng NĐ 217/2026 chia 5 khối theo loại công trình; hồ sơ nhà ở riêng lẻ phải vào 12, 13, 16
    # (chốt BA 2026-09-14). Trước đây rơi vào 1, 2, 27 = khối "không theo tuyến"/BIM → sai hoàn toàn.
    assert res["extracted"]["congTrinhNhanh"] == "nha_o_rieng_le"

    app_items = by_slot["gpxd_nrl_don"]
    assert [item["fileIndex"] for item in app_items] == [1, 0, 2]
    assert {item["componentIndex"] for item in app_items} == {12}
    assert {item["slotIndex"] for item in app_items} == {11}
    assert "Đơn đề nghị cấp giấy phép xây dựng" in app_items[0]["componentName"]

    land_items = by_slot["gpxd_nrl_dat"]
    assert [item["fileIndex"] for item in land_items] == [7]
    assert land_items[0]["componentIndex"] == 13
    assert land_items[0]["slotIndex"] == 12
    assert "giấy tờ hợp pháp về đất đai" in land_items[0]["componentName"].lower()

    design_items = by_slot["gpxd_nrl_banve"]
    assert [item["fileIndex"] for item in design_items] == [4, 3, 5, 6]
    assert {item["componentIndex"] for item in design_items} == {16}
    assert {item["slotIndex"] for item in design_items} == {15}
    assert "Bộ bản vẽ thiết kế xây dựng kèm theo" in design_items[0]["componentName"]
    assert not res["errors"]

    # slotKey phải KHÁC các key cũ: extension khớp keyword theo slotKey TRƯỚC slotIndex, mà text đơn/
    # đất của 5 khối gần như trùng nhau nên keyword luôn bắt nhầm dòng 1/2. Key mới không có trong
    # FIXED_SLOT_KEYWORDS → FE rơi về slotIndex và vào đúng khối.
    assert not {"gpxd_application", "gpxd_land_document", "gpxd_design_dossier"} & set(by_slot)

    by_name = {entry["fileName"]: entry for entry in res["extracted"]["classified"]}
    assert by_name["Đơn đề nghị cấp phép xây nhà 2026.pdf"]["docType"] == "building_permit_application"
    assert by_name["Căn cươc CD Chinh.pdf"]["docType"] == "identity_document"
    assert by_name["Bản cam ket xây nhà 2026.pdf"]["docType"] == "safety_commitment"
    assert by_name["Sổ đỏ 1.jpg"]["componentIndex"] == 13
    assert by_name["Bản vẽ xin cấp phép xây dựng.pdf"]["componentIndex"] == 16


async def test_cap_giay_phep_xay_dung_khong_doan_theo_ten_file_khi_ocr_rong(monkeypatch):
    """OCR rỗng + LLM trả "other" → BỎ QUA kèm cảnh báo, KHÔNG suy loại giấy tờ từ TÊN FILE.
    (Test này trước đây kỳ vọng có fallback theo tên file — cơ chế đó đã bỏ vì đoán theo tên rất dễ
    sai; giữ nguyên kỳ vọng cũ thì test fail vĩnh viễn.)"""
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": "", "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": ""}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("Sổ đỏ 1.jpg", "image/jpeg")], {}, None)

    assert res["attachments"] == []
    assert any("Sổ đỏ 1.jpg" in err for err in res["errors"])


def test_cap_giay_phep_xay_dung_registry_has_process_and_attach():
    key = "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"
    proc = get_procedure(key)

    assert proc is not None
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    # uploadHint phải nêu ĐÚNG dòng của từng khối loại công trình (chốt BA 2026-09-14).
    assert "STT 12" in proc["uploadHint"] and "STT 13" in proc["uploadHint"] and "STT 16" in proc["uploadHint"]
    assert "STT 6, 7, 10" in proc["uploadHint"]
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None


def test_cap_giay_phep_xay_dung_prompt_uses_ocr_text_only():
    assert "building_permit_application" in SYSTEM_PROMPT
    assert "construction_design_drawings" in SYSTEM_PROMPT
    assert "land_legal_document" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT
    assert "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG" in SYSTEM_PROMPT
    # Prompt nói theo NHÓM (Đơn / Đất đai / Thiết kế), KHÔNG bám số dòng: bảng của cổng đã đổi sang
    # NĐ 217/2026 và số dòng còn phụ thuộc khối loại công trình — hardcode số dòng vào prompt là sai.
    assert "Nhóm THIẾT KẾ" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "don-de-nghi.pdf",
            "text": "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG",
        }
    ])

    assert "ocrText" in user_prompt
    assert "ĐƠN ĐỀ NGHỊ CẤP PHÉP XÂY DỰNG" in user_prompt
    assert "don-de-nghi.pdf" not in user_prompt
    assert "fileName" not in user_prompt


def test_khoi_ton_giao_va_nha_o_rieng_le_dung_dong_theo_chot_ba():
    """Bảng NĐ 217/2026 lặp gần như y hệt bộ giấy tờ ở 5 khối → chọn sai khối là đính sai chỗ.
    Chốt BA 2026-09-14: nhà ở riêng lẻ = 12/13/16, tín ngưỡng tôn giáo = 6/7/10."""
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "so-do.pdf", "type": "application/pdf"},
        {"name": "ban-ve.pdf", "type": "application/pdf"},
    ]
    llm = {
        0: {"type": "building_permit_application", "title": "Đơn đề nghị cấp GPXD"},
        1: {"type": "land_legal_document", "title": "Giấy chứng nhận quyền sử dụng đất"},
        2: {"type": "construction_design_drawings", "title": "Bản vẽ"},
    }

    for nhanh, expected in (("nha_o_rieng_le", [12, 13, 16]), ("tin_nguong_ton_giao", [6, 7, 10])):
        items, warnings, _ = planner.build_plan_items(files, None, llm, nhanh)
        assert [item["componentIndex"] for item in items] == expected, nhanh
        # slotIndex là vị trí 0-based FE dùng để tìm ô upload → luôn phải là STT - 1.
        assert [item["slotIndex"] for item in items] == [stt - 1 for stt in expected], nhanh
        assert warnings == []


def test_slot_key_khong_trung_keyword_cu_cua_extension():
    """FE khớp keyword theo slotKey TRƯỚC slotIndex. Text đơn/đất của 5 khối gần như trùng nhau nên
    keyword luôn bắt dòng 1/2 — đặt lại tên key cũ là lỗi quay lại ngay."""
    stale = {"gpxd_application", "gpxd_land_document", "gpxd_design_dossier"}
    for nhanh in ("nha_o_rieng_le", "tin_nguong_ton_giao"):
        keys = {slot["slotKey"] for slot in planner.slots_for(nhanh).values()}
        assert not (keys & stale), f"{nhanh} dùng lại slotKey cũ: {keys & stale}"


def test_nhanh_la_thi_ve_nha_o_rieng_le():
    assert planner.slots_for("khong_biet_la_gi") == planner.slots_for("nha_o_rieng_le")
    assert planner._normalize_nhanh("Tín ngưỡng, tôn giáo") == "tin_nguong_ton_giao"
    assert planner._normalize_nhanh("chùa") == "tin_nguong_ton_giao"
    assert planner._normalize_nhanh("") == "nha_o_rieng_le"


# ---------------------------------------------------------------------------
# Khoá CẤU TRÚC bảng thành phần hồ sơ thật của cổng (snapshot 'thongtin/xd/đính kèm xây dựng.html',
# dvc.moc.gov.vn, Nghị định 217/2026). 29 dòng = 29 input[type=file], không có input lạ xen giữa nên
# slotIndex (0-based theo DOM) LUÔN bằng STT − 1.
# ---------------------------------------------------------------------------
_ROW_KINDS = [
    "don", "dat", "qd_du_an", "ban_ve_du_an", "bim",                                  # 1-5   không theo tuyến
    "don", "dat", "qd_du_an", "vb_ton_giao", "ban_ve_du_an", "bim",                   # 6-11  tín ngưỡng, tôn giáo
    "don", "dat", "vb_van_hoa_ton_giao", "bim", "ban_ve_nha_o_rieng_le",              # 12-16 NHÀ Ở RIÊNG LẺ
    "don", "dat", "qd_du_an", "ban_ve_du_an", "vb_my_thuat", "bim",                   # 17-22 tượng đài
    "don", "dat", "qd_du_an", "ban_ve_du_an", "bim",                                  # 23-27 theo giai đoạn/dự án
    "don_dieu_chinh", "hiep_dinh",                                                    # 28-29
]


def test_cau_truc_bang_29_dong_va_slot_index_khop_snapshot_cong():
    assert len(_ROW_KINDS) == 29

    # Dòng "Đơn" lặp ở 4 khối, dòng "Đất" lặp ở 5 khối → keyword theo TEXT không thể phân biệt khối.
    # Đây chính là lý do phải dùng slotIndex (xem docstring planner).
    don_rows = [i + 1 for i, kind in enumerate(_ROW_KINDS) if kind == "don"]
    dat_rows = [i + 1 for i, kind in enumerate(_ROW_KINDS) if kind == "dat"]
    assert don_rows == [1, 6, 12, 17, 23]
    assert dat_rows == [2, 7, 13, 18, 24]

    # Bản vẽ của NHÀ Ở RIÊNG LẺ là loại RIÊNG ("Bộ bản vẽ… kèm theo"), chỉ xuất hiện ĐÚNG 1 lần.
    assert [i + 1 for i, kind in enumerate(_ROW_KINDS) if kind == "ban_ve_nha_o_rieng_le"] == [16]

    for nhanh, expected in (("nha_o_rieng_le", [12, 13, 16]), ("tin_nguong_ton_giao", [6, 7, 10])):
        slots = planner.slots_for(nhanh)
        stts = [slots[g]["componentIndex"] for g in ("don", "dat", "banve")]
        assert stts == expected, nhanh
        assert [slots[g]["slotIndex"] for g in ("don", "dat", "banve")] == [s - 1 for s in expected]
        # Dòng được chọn phải ĐÚNG LOẠI trên bảng thật.
        assert _ROW_KINDS[expected[0] - 1] == "don", nhanh
        assert _ROW_KINDS[expected[1] - 1] == "dat", nhanh
        assert _ROW_KINDS[expected[2] - 1].startswith("ban_ve"), nhanh


def test_tep_quet_gop_uu_tien_don_va_canh_bao_dong_con_lai_trong():
    """Chốt user 2026-09-14: tệp gộp nhiều giấy tờ mà CÓ TỜ KHAI/ĐƠN thì ưu tiên Đơn. Hệ quả là dòng
    đất/thiết kế có thể trống dù bắt buộc → phải cảnh báo, không im lặng nộp thiếu."""
    files = [{"name": "don-kem-so-do.pdf", "type": "application/pdf"}]
    llm = {0: {"type": "building_permit_application", "title": "Đơn đề nghị cấp GPXD"}}

    items, warnings, _ = planner.build_plan_items(files, None, llm, "nha_o_rieng_le")

    assert [item["componentIndex"] for item in items] == [12]
    assert any("STT 13" in w for w in warnings)
    assert any("STT 16" in w for w in warnings)
    assert all("tách tệp" in w for w in warnings)


def test_du_ca_ba_nhom_thi_khong_canh_bao_thua():
    files = [{"name": f"{n}.pdf", "type": "application/pdf"} for n in ("don", "dat", "banve")]
    llm = {
        0: {"type": "building_permit_application", "title": "Đơn"},
        1: {"type": "land_legal_document", "title": "Sổ đỏ"},
        2: {"type": "construction_design_drawings", "title": "Bản vẽ"},
    }

    _, warnings, _ = planner.build_plan_items(files, None, llm, "nha_o_rieng_le")

    assert warnings == []


def test_prompt_chot_thu_tu_uu_tien_khi_tep_quet_gop():
    from app.pipelines.cap_giay_phep_xay_dung.attach.prompt import SYSTEM_PROMPT

    assert "CÓ ĐƠN/TỜ KHAI trong tệp" in SYSTEM_PROMPT
    assert "dù nó chỉ chiếm 1 trang" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG trả hai type cho một tệp" in SYSTEM_PROMPT
    # Bảng cũ NĐ 175 dùng số dòng 1/11/27 — prompt không được nhắc lại số dòng đã chết.
    assert "Dòng 11" not in SYSTEM_PROMPT and "Dòng 27" not in SYSTEM_PROMPT
