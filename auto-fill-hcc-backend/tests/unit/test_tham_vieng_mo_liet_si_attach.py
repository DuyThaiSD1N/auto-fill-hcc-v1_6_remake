"""Thăm viếng mộ liệt sĩ: cổng không phải lúc nào cũng có "Thêm giấy tờ" → CCCD, Bằng TQGC, giấy chưa rõ loại
đính chung ô Đơn (fixed-slot), không dùng target "new". Dữ liệu giả."""

from app.pipelines.tham_vieng_mo_liet_si.attach import planner

_FILES = [{"name": f"tep{i}.pdf", "type": "application/pdf"} for i in range(4)]


def test_giay_kem_theo_vao_o_don():
    llm = {0: "don_gioi_thieu", 1: "cccd", 2: "bang_tqgc", 3: "other"}
    items, warnings, _ = planner.build_plan_items(_FILES, [], llm)
    assert [it["fileIndex"] for it in items] == [0, 1, 2, 3]
    assert all(it["target"] == "fixed-slot" and it["slotKey"] == "don_gioi_thieu" for it in items)
    assert all(it["needsAddComponent"] is False for it in items)
    assert items[1]["documentName"] == "Căn cước công dân người nộp"
    # Giấy chưa rõ loại vẫn đính (không miss file) nhưng báo cán bộ kiểm.
    assert len(warnings) == 1 and "tep3.pdf" in warnings[0]


def test_giay_dung_dong_giu_nguyen_o_rieng():
    llm = {0: "ho_so_liet_si", 1: "giay_chung_nhan_than_nhan"}
    items, warnings, _ = planner.build_plan_items(_FILES[:2], [], llm)
    assert [it["slotKey"] for it in items] == ["ho_so_liet_si", "giay_chung_nhan_than_nhan"]
    assert warnings == []


def test_tu_khoa_dong_di_qua_response_model():
    from app.attachments.schemas import AttachmentPlanResp

    items, _, _ = planner.build_plan_items(_FILES[:1], [], {0: "cccd"})
    assert items[0]["slotKeywords"] == ["don de nghi theo mau so 31", "mau so 31 phu luc i"]
    dumped = AttachmentPlanResp.model_validate({"attachments": items}).model_dump(mode="json")
    assert dumped["attachments"][0]["slotKeywords"] == items[0]["slotKeywords"]


def test_ba_thu_tuc_nguoi_co_cong_cung_dinh_giay_kem_theo_vao_o_don():
    from app.pipelines.bo_sung_than_nhan_liet_si.attach import planner as bo_sung
    from app.pipelines.tro_cap_tho_cung_liet_si.attach import planner as tho_cung
    from app.pipelines.uu_dai_ncc_tu_tran.attach import planner as tu_tran

    for mod, extra, dest in (
        (bo_sung, "bang_tqgc", bo_sung._DON),
        (tho_cung, "cccd", tho_cung._DON),
        (tu_tran, "cccd", tu_tran._BAN_KHAI),
    ):
        assert extra in mod._NEW_DOCS, mod.__name__
        items, warnings, _ = mod.build_plan_items(_FILES[:2], [], {0: extra, 1: "other"})
        assert [it["target"] for it in items] == ["fixed-slot", "fixed-slot"], mod.__name__
        assert {it["slotKey"] for it in items} == {dest}, mod.__name__
        assert all(it["slotKeywords"] for it in items), mod.__name__
        assert len(warnings) == 1, mod.__name__


def test_slot_index_theo_thu_tu_cong_hien_tai():
    # Bản extension cũ không đọc slotKeywords, chỉ dò theo thứ tự ô: STT1 hồ sơ LS, STT2 Đơn, STT3 chứng nhận.
    order = {s["slotKey"]: s["slotIndex"] for s in planner.SLOTS}
    assert order == {"ho_so_liet_si": 0, "don_gioi_thieu": 1, "giay_chung_nhan_than_nhan": 2}
