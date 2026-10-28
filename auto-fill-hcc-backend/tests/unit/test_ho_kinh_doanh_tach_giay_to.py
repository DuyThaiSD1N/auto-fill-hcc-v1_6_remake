"""Nhóm hộ kinh doanh (HkdOnline): bật "Tách tệp có nhiều giấy tờ" thì planner chia PDF theo trang rồi phân loại
từng giấy; không bật / extension không cắt được trang → phân loại nguyên tệp như cũ."""

import asyncio
import importlib

import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.procedure_registry import get_procedure
from app.pipelines._shared import kinh_doanh_tach_giay_to as tach
from app.pipelines._shared.kinh_doanh_tach_giay_to import split_requested
from app.procedures.registry import public_list

_HKD = {
    "dang-ky-kinh-doanh": "dang_ky_kinh_doanh",
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": "dang_ky_thay_doi_kinh_doanh",
    "tam-ngung-kinh-doanh": "tam_ngung_kinh_doanh",
    "cham-dut-hoat-dong-ho-kinh-doanh": "cham_dut_hoat_dong_ho_kinh_doanh",
    "cap-lai-cap-doi-gcn-ho-kinh-doanh": "cap_lai_cap_doi_gcn_ho_kinh_doanh",
}


def test_split_requested():
    assert split_requested({"splitDocuments": True})  # Auto Fill không gửi supportsSourceSegments
    assert split_requested({"splitDocuments": True, "supportsSourceSegments": True})
    assert not split_requested({"splitDocuments": True, "supportsSourceSegments": False})
    assert not split_requested({"splitDocuments": False})
    assert not split_requested({})
    assert not split_requested(None)


def test_ca_hai_registry_bat_co_tach():
    core = {p["key"]: p for p in public_list()}
    for key in _HKD:
        assert core[key].get("supportsSplitDocuments") is True, key
        assert get_procedure(key).get("supportsSplitDocuments") is True, key


@pytest.mark.parametrize("pkg", list(_HKD.values()))
def test_planner_chi_tach_khi_bat(monkeypatch, pkg):
    planner = importlib.import_module(f"app.pipelines.{pkg}.attach.planner")
    calls = []

    async def fake_split(plan_fn, files, options, session, *, doc_hints):
        calls.append(("split", plan_fn))
        assert doc_hints == planner._SPLIT_DOC_HINTS
        return {"attachments": []}

    async def fake_files(files, options, session):
        calls.append(("whole", None))
        return {"attachments": []}

    monkeypatch.setattr(planner, "plan_with_split", fake_split)
    monkeypatch.setattr(planner, "_plan_files", fake_files)
    asyncio.run(planner.plan([], {"splitDocuments": True, "supportsSourceSegments": True}))
    asyncio.run(planner.plan([], {"splitDocuments": True, "supportsSourceSegments": False}))
    asyncio.run(planner.plan([], {}))
    assert [c[0] for c in calls] == ["split", "whole", "whole"]
    assert calls[0][1] is fake_files


def test_handfree_gui_splitdocuments_cho_ho_kinh_doanh():
    conv = {
        "procedure_key": "dang-ky-kinh-doanh",
        "client_capabilities": {"supportsSourceSegments": True},
        "attachment_preferences": {"splitDocuments": True},
    }
    assert flow._attachment_options(conv)["splitDocuments"] is True
    # Extension cũ không có capability → giữ nguyên options rỗng như trước.
    assert "splitDocuments" not in flow._attachment_options({**conv, "client_capabilities": {}})


def test_trang_trang_khong_mo_giay_moi():
    don = "GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH Kính gửi: Phòng Tài chính phường A. Tôi là NGUYỄN VĂN A"
    cccd = "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân 001000000001 Họ và tên NGUYỄN VĂN A Ngày sinh 01/01/1990"
    # Trang trắng / mặt sau hoa văn OCR ra chữ rác hoặc riêng dòng quốc hiệu → không mở giấy mới.
    pages = [don, "Qwen", cccd, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "(1)"]
    data = {"tep": [{"fileIndex": 0, "trangDau": [1, 2, 3, 4, 5, 9]}]}
    assert tach.page_starts(data, {0: pages}) == {0: [0, 2]}


def test_doi_ke_hoach_ve_tep_goc_va_khong_bo_giay():
    segments = [
        {"source": 0, "pages": [0, 1, 2], "file": {"name": "a_trang_1-3.pdf"}},
        {"source": 0, "pages": [3, 4], "file": {"name": "a_trang_4-5.pdf"}},
        {"source": 1, "pages": None, "file": {"name": "b.pdf"}},
    ]
    plan = [
        {"fileIndex": 0, "category": "BUSREGFRM", "target": "new"},
        {"fileIndex": 2, "category": "CPID", "target": "new"},
    ]
    out = tach.remap_plan(plan, segments)
    assert out[0]["fileIndex"] == 0 and out[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1, 2]}]
    assert out[1]["fileIndex"] == 1 and "sourceSegments" not in out[1]
    # Đoạn planner không trả mục → vẫn đính, loại "Khác".
    assert out[2]["category"] == "OTHERS" and out[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [3, 4]}]


def test_prompt_rieng_cho_ho_kinh_doanh_va_goi_y_theo_thu_tuc():
    assert "HỘ KINH DOANH" in tach.SYSTEM_PROMPT and "%DOC_HINTS%" in tach.SYSTEM_PROMPT
    for pkg in _HKD.values():
        planner = importlib.import_module(f"app.pipelines.{pkg}.attach.planner")
        assert planner._SPLIT_DOC_HINTS.strip(), pkg
