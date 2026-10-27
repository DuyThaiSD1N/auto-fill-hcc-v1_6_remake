"""Đính kèm mai táng bảo trợ xã hội (ho-tro-mai-tang, ho-tro-mai-tang-1116910): LLM quyết định loại giấy, luật dò chữ chỉ
dự phòng khi LLM không trả lời cho file đó — không bao giờ đè LLM."""
from app.pipelines.ho_tro_mai_tang.attach.planner import build_plan_items


def _plan(texts, llm_slots):
    files = [{"name": f"f{i}.pdf"} for i in range(len(texts))]
    ocr = [{"name": f"f{i}.pdf", "text": t} for i, t in enumerate(texts)]
    return build_plan_items(files, ocr, llm_slots)


def test_quyet_dinh_co_dong_so_can_cuoc_van_dinh_theo_llm():
    items, _ = _plan(["QUYẾT ĐỊNH về việc dừng hưởng chế độ. Ông A, Căn cước công dân số 0000"],
                     {0: "quyet_dinh_thoi_huong"})
    assert [i["slotKey"] for i in items] == ["quyet_dinh_thoi_huong"]


def test_trich_luc_khai_tu_co_mau_so_04_vao_dong_chung_tu_theo_llm():
    items, _ = _plan(["Mẫu số 04 TRÍCH LỤC KHAI TỬ (Bản sao)"], {0: "giay_chung_tu"})
    assert [i["slotKey"] for i in items] == ["giay_chung_tu"]


def test_llm_noi_giay_khac_thi_khong_dinh_va_canh_bao():
    items, warnings = _plan(["CĂN CƯỚC CÔNG DÂN"], {0: ""})
    assert items == [] and "không thuộc 3 thành phần" in warnings[0]


def test_llm_khong_tra_loi_thi_moi_dung_luat_du_phong():
    items, _ = _plan(["TRÍCH LỤC KHAI TỬ"], {})
    assert [i["slotKey"] for i in items] == ["giay_chung_tu"]
