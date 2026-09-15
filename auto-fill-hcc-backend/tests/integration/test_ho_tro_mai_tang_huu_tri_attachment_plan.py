"""Đính kèm "Hỗ trợ chi phí mai táng đối với đối tượng hưởng trợ cấp hưu trí xã hội".

Cổng chỉ còn ĐÚNG MỘT dòng (chốt user 2026-09-15) → mọi file vào dòng 1, không bỏ sót, và KHÔNG
lưới keyword nào tham gia phân loại.
"""

from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.attach import planner

_TRICH_LUC_KHAI_TU = (
    "TRÍCH LỤC KHAI TỬ\n"
    "Họ, chữ đệm, tên: ĐÀO THỊ T.\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 0681xxxxxxx, Cục cảnh sát quản lý hành chính về "
    "trật tự xã hội cấp ngày 28/06/2021\n"
    "Đã chết vào lúc 09 giờ 00 phút, ngày 03/09/2026"
)


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_moi_file_deu_vao_dong_1_khong_bo_sot():
    names = ["to-khai.pdf", "khai-tu.pdf", "cccd.pdf", "la.pdf"]
    llm = {0: "to_khai_mai_tang", 1: "giay_chung_tu", 2: "", 3: ""}

    items, warnings = planner.build_plan_items(_files(names), [], llm)

    assert [item["fileIndex"] for item in items] == [0, 1, 2, 3]
    assert all(item["target"] == "fixed-slot" for item in items)
    assert all(item["slotIndex"] == 0 for item in items)
    assert all(item["needsAddComponent"] is False for item in items)
    # Chỉ Tờ khai là đúng dòng → 3 file còn lại phải có cảnh báo cho cán bộ soát.
    assert len(warnings) == 3


def test_ten_hien_thi_phan_biet_de_can_bo_soat():
    items, _ = planner.build_plan_items(
        _files(["to-khai.pdf", "khai-tu.pdf", "la.pdf"]),
        [],
        {0: "to_khai_mai_tang", 1: "giay_chung_tu", 2: ""},
    )

    assert items[0]["documentName"] == "Tờ khai đề nghị hỗ trợ chi phí mai táng"
    assert items[1]["documentName"] == "Giấy chứng tử/Trích lục khai tử"
    assert items[2]["documentName"] == "Tài liệu khác - la.pdf"


def test_llm_chet_van_dinh_du_file_khong_doan_bang_keyword():
    names = ["to-khai.pdf", "khai-tu.pdf"]

    items, warnings = planner.build_plan_items(_files(names), [], {})

    assert len(items) == len(names)
    assert all(item["slotIndex"] == 0 for item in items)
    assert len(warnings) == len(names)
    # detect_slot_key VẪN nhận ra tờ khai nếu bị gọi → chứng minh nó đã bị gỡ khỏi luồng.
    assert planner.detect_slot_key(
        "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG ... trợ cấp hưu trí xã hội"
    ) in ("to_khai_mai_tang", "")


def test_khong_con_luoi_keyword_nao_trong_luong_quyet_dinh():
    for fn in (planner.is_excluded_document, planner.detect_slot_key):
        assert "KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH" in (fn.__doc__ or ""), fn.__name__
    # Lưới cũ vẫn khớp nhầm trích lục khai tử (giữ để đối chứng) — nhưng không còn ảnh hưởng kế hoạch.
    assert planner.is_excluded_document(_TRICH_LUC_KHAI_TU) is True
    items, _ = planner.build_plan_items(_files(["khai-tu.pdf"]), [], {0: "giay_chung_tu"})
    assert len(items) == 1


def test_chi_con_mot_slot_va_slot_name_khop_cong():
    assert len(planner.SLOTS) == 1
    assert planner.SLOT["slotIndex"] == 0
    assert "Mẫu số 02 ban hành kèm theo Nghị định số 176/2025/NĐ-CP" in planner.SLOT["slotName"]


def test_prompt_chan_bay_nhac_so_can_cuoc_trong_trich_luc():
    from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.attach.prompt import SYSTEM_PROMPT

    assert "Mẫu số 02" in SYSTEM_PROMPT
    assert "CHỈ LÀ MỘT DÒNG THÔNG TIN" in SYSTEM_PROMPT
