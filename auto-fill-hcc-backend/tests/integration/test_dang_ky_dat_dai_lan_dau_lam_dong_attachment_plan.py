"""Đính kèm [Lâm Đồng] Đăng ký đất đai cấp GCN lần đầu (1.116360).

Bảng thành phần hồ sơ đổi theo Quyết định 40/2026/QĐ-UBND: 20 dòng, Đơn Mẫu 15 xuống STT 19.
Khoá lại slotIndex từng nhóm + luật "thuần LLM, không bỏ sót file nào".
"""

import inspect

from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.attach import planner

# STT (1-based) từng dòng của bảng trên cổng mà planner dùng tới — slotIndex = STT − 1.
_STT = {
    "g_origin": 1,
    "g_household": 8,
    "g_survey": 14,
    "g_finance": 16,
    "g_representation": 18,
    "g_application": 19,
}


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _llm(*types):
    return {i: {"type": t, "documentName": ""} for i, t in enumerate(types)}


def test_slot_index_dung_bang_20_dong_cua_cong():
    for group_key, stt in _STT.items():
        assert planner._GROUPS[group_key]["slotIndex"] == stt - 1, group_key
    assert set(planner._GROUPS) == set(_STT)


def test_don_mau_15_vao_stt_19_khong_con_dong_dau_bang():
    items, _, _ = planner.build_plan_items(_files(["don.pdf"]), [], _llm("application"))

    assert len(items) == 1
    assert items[0]["slotIndex"] == 18
    assert items[0]["target"] == "fixed-slot"
    assert "Mẫu số 15" in items[0]["componentName"]


def test_uy_quyen_vao_o_van_ban_dai_dien_stt_18():
    """Ủy quyền có dòng riêng trên cổng ("Văn bản về việc đại diện…"), không dùng chung ô với Đơn."""
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf", "uy-quyen.pdf"]), [], _llm("application", "authorization")
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file == {"don.pdf": 18, "uy-quyen.pdf": 17}
    uy_quyen = next(i for i in items if i["fileName"] == "uy-quyen.pdf")
    assert uy_quyen["slotKey"] == "g_representation"
    assert "thông qua người đại diện" in uy_quyen["componentName"]
    # Mỗi file 1 attachment riêng → FE KHÔNG gộp PDF.
    assert all(i["sourceFileIndexes"] == [i["fileIndex"]] for i in items)


def test_cccd_va_tai_lieu_la_van_o_don_khong_theo_uy_quyen():
    items, _, _ = planner.build_plan_items(
        _files(["cccd.pdf", "la.pdf"]), [], _llm("identity", "other")
    )

    assert {i["slotIndex"] for i in items} == {18}


def test_bon_tuyen_duong_dung_o():
    """Bộ 4 giấy tờ điển hình: đơn → 19, ủy quyền → 18, trích đo → 14, tài sản riêng → 8."""
    names = ["uy-quyen.pdf", "manh-trich-do.pdf", "don-mau-15.pdf", "tai-san-rieng.pdf"]
    items, _, _ = planner.build_plan_items(
        _files(names), [], _llm("authorization", "survey_adjust", "application", "household_rights")
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file == {
        "don-mau-15.pdf": 18,
        "uy-quyen.pdf": 17,
        "manh-trich-do.pdf": 13,
        "tai-san-rieng.pdf": 7,
    }
    assert len(items) == len(names)
    # 4 file → 4 ô khác nhau, không dồn chung dòng nào.
    assert len({i["slotIndex"] for i in items}) == 4


def test_tai_san_rieng_khong_roi_vao_o_nguon_goc():
    items, _, _ = planner.build_plan_items(_files(["tai-san-rieng.pdf"]), [], _llm("household_rights"))

    assert items[0]["slotIndex"] == 7
    assert "thành viên có chung quyền sử dụng đất" in items[0]["componentName"]


def test_nguon_goc_va_bien_lai_dung_o():
    items, _, _ = planner.build_plan_items(
        _files(["nguon-goc.pdf", "bien-lai.pdf"]), [], _llm("origin_doc", "tax_receipt")
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file == {"nguon-goc.pdf": 0, "bien-lai.pdf": 15}


def test_ba_loai_ban_ve_chung_o_manh_trich_do():
    items, _, _ = planner.build_plan_items(
        _files(["a.pdf", "b.pdf", "c.pdf"]), [], _llm("survey_adjust", "map_extract", "boundary_desc")
    )

    assert {i["slotIndex"] for i in items} == {13}


def test_khong_ro_loai_van_dinh_vao_o_don_khong_bo_sot():
    names = ["la-1.pdf", "don.pdf", "la-2.pdf"]
    items, warnings, _ = planner.build_plan_items(_files(names), [], _llm("other", "application", "other"))

    assert sorted(i["fileIndex"] for i in items) == [0, 1, 2]
    assert {i["slotIndex"] for i in items} == {18}
    assert any("không bỏ sót" in w or "Chưa nhận ra loại" in w for w in warnings)
    # Tên hiển thị phải nêu rõ là tài liệu chưa nhận ra loại để cán bộ soát.
    unknown = [i for i in items if i["fileName"].startswith("la-")]
    assert all(i["documentName"].startswith("Tài liệu khác") for i in unknown)


def test_llm_chet_van_dinh_du_file():
    names = ["a.pdf", "b.pdf", "c.pdf"]
    items, warnings, _ = planner.build_plan_items(_files(names), [], {})

    assert sorted(i["fileIndex"] for i in items) == [0, 1, 2]
    assert {i["slotIndex"] for i in items} == {18}
    assert warnings


def test_thuan_llm_khong_con_luoi_keyword():
    """Planner không được đọc OCR để tự đoán loại — phân loại là việc của LLM."""
    for name in ("_rule_doc_type", "_looks_like_identity", "_has_any"):
        assert not hasattr(planner, name), f"{name} phải bị gỡ khỏi planner"
    src = inspect.getsource(planner.build_plan_items)
    assert "ocr_results" in src and "_ = ocr_results" in src
    # OCR có nội dung dễ gây nhầm nhưng LLM đã xác định loại → planner phải nghe LLM.
    ocr = [{"name": "uy-quyen.pdf", "text": "GIẤY ỦY QUYỀN ... theo Mảnh trích đo địa chính số 497-2019"}]
    items, _, _ = planner.build_plan_items(_files(["uy-quyen.pdf"]), ocr, _llm("authorization"))
    assert items[0]["slotIndex"] == 17


def test_slot_key_khong_trung_keyword_extension():
    """slotKey cố ý KHÔNG nằm trong FIXED_SLOT_KEYWORDS (content.js) → FE dùng thẳng slotIndex."""
    from pathlib import Path

    content = Path(__file__).resolve().parents[3] / "auto-fill-hcc-extension" / "content.js"
    if not content.exists():  # repo backend đứng một mình
        return
    text = content.read_text(encoding="utf-8")
    block = text.split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    for group_key in planner._GROUPS:
        assert f"{group_key}:" not in block, group_key


def test_prompt_co_bay_va_rang_buoc_khong_bo_sot():
    from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.attach.prompt import (
        SYSTEM_PROMPT,
        build_user_prompt,
    )

    assert "household_rights" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT
    assert "KHÔNG BỊA" in SYSTEM_PROMPT
    # Hai bẫy gây phân loại sai trên bộ giấy tờ đất đai.
    assert "NHẮC TỚI MẢNH TRÍCH ĐO ≠ LÀ MẢNH TRÍCH ĐO" in SYSTEM_PROMPT
    assert "TÀI SẢN RIÊNG ≠ NGUỒN GỐC ĐẤT" in SYSTEM_PROMPT
    # Prompt mô tả theo TÊN Ô, không hardcode số dòng (bảng đã đổi một lần rồi).
    assert "STT 19" not in SYSTEM_PROMPT
    assert "3 phần tử" in build_user_prompt([{"index": i, "text": ""} for i in range(3)])
