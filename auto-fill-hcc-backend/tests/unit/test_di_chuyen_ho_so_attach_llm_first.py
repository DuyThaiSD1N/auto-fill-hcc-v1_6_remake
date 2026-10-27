"""Đính kèm di chuyển hồ sơ người hưởng trợ cấp ưu đãi: LLM quyết định loại giấy, luật dò chữ chỉ dự phòng khi LLM không
trả lời cho tệp đó — không bao giờ đè LLM."""
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import build_plan_items


def _plan(texts, llm_types):
    files = [{"name": f"f{i}.pdf"} for i in range(len(texts))]
    ocr = [{"name": f"f{i}.pdf", "text": t} for i, t in enumerate(texts)]
    return build_plan_items(files, ocr, llm_types)


def test_llm_thang_luat_do_chu():
    # Luật dò chữ thấy "mẫu số 27" → đơn; LLM đọc cả tệp nói là CCCD → theo LLM.
    items, _, classified = _plan(["CĂN CƯỚC CÔNG DÂN ... ghi chú mẫu số 27"], {0: "cccd"})
    assert [(i["slotKey"], i["slotIndex"]) for i in items] == [("cccd", 0)]
    assert classified[0]["source"] == "llm"


def test_mat_sau_cccd_luat_bo_sot_thi_llm_van_dinh():
    items, _, _ = _plan(["Đặc điểm nhận dạng / Personal identification ... IDVNM"], {0: "cccd"})
    assert [i["slotKey"] for i in items] == ["cccd"]


def test_llm_noi_giay_nguon_khac_thi_bo_qua():
    items, warnings, classified = _plan(["PHIẾU BÁO DI CHUYỂN HỒ SƠ"], {0: "phieu_bao_di_chuyen"})
    assert items == [] and classified[0].get("skipped") and not warnings


def test_llm_khong_tra_loi_thi_moi_dung_luat_du_phong():
    items, _, classified = _plan(["ĐƠN ĐỀ NGHỊ di chuyển hồ sơ Mẫu số 27"], {})
    assert [(i["slotKey"], i["slotIndex"]) for i in items] == [("don_mau_27", 1)]
    assert classified[0]["source"] == "rule"
