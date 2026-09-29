"""Cấp, cấp lại Giấy phép khai thác thủy sản — đính kèm không được bỏ tệp nào (bảng chỉ có 2 dòng Đơn)."""

import json

from app.pipelines.cap_giay_phep_khai_thac_thuy_san.attach import planner, prompt


def _files(*names):
    return [{"name": n} for n in names]


def test_tep_gop_co_don_cap_lai_vao_dong_mau_05():
    items, warnings, _ = planner.build_plan_items(_files("gop.pdf"), [], {0: "don_cap_lai"})
    assert [i["componentName"] for i in items] == ["Đơn đề nghị cấp lại theo Mẫu số 05"]
    assert not warnings


def test_giay_phep_cu_va_cccd_di_kem_dong_don_giu_ten_goc():
    llm = {0: "giay_phep_cu", 1: "don_cap_lai", 2: "cccd", 3: "other"}
    items, warnings, classified = planner.build_plan_items(
        _files("gp.pdf", "don.pdf", "cccd.jpg", "tau.pdf"), [], llm
    )
    assert [i["fileIndex"] for i in items] == [0, 1, 2, 3], "không bỏ tệp nào"
    assert {i["componentName"] for i in items} == {"Đơn đề nghị cấp lại theo Mẫu số 05"}
    assert items[0]["documentName"] == "gp.pdf" and items[0]["detectedType"] == "giay_phep_cu"
    assert items[1]["documentName"].startswith("Đơn đề nghị cấp lại")
    assert all(c.get("routedTo") == "don_cap_lai" for c in classified if c["fileName"] != "don.pdf")
    assert not warnings


def test_khong_co_don_thi_canh_bao_chu_khong_im_lang():
    items, warnings, _ = planner.build_plan_items(_files("gp.pdf", "cccd.jpg"), [], {0: "giay_phep_cu", 1: "cccd"})
    assert items == []
    assert warnings and "gp.pdf" in warnings[0] and "cccd.jpg" in warnings[0]


async def test_llm_tra_thua_phan_tu_theo_trang_chi_lay_phan_tu_dau_cua_index(monkeypatch):
    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "don_cap_lai"},
            {"index": 0, "docType": "giay_phep_cu"},
            {"index": 1, "docType": "cccd"},
        ]})

    monkeypatch.setattr(planner.client, "chat", fake_chat)
    assert await planner._classify_with_llm([{"index": 0, "text": "x"}]) == {0: "don_cap_lai"}


def test_prompt_neu_ro_mot_tep_mot_phan_tu_va_tep_gop():
    assert "ĐÚNG MỘT phần tử cho index đó" in prompt.SYSTEM_PROMPT
    assert "Tệp GỘP nhiều giấy" in prompt.SYSTEM_PROMPT
