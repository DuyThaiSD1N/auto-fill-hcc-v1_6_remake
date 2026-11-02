"""Planner đính kèm đất đai Lào Cai: CCCD và giấy chưa rõ loại không được rơi khỏi kế hoạch.

Cổng có danh sách "Giấy tờ khác" → target "new"; cổng không có → chung dòng Đơn của nhánh/nhóm (giữ target của dòng).
"""

import pytest

from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach import planner as cap_gcn
from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.attach import planner as cap_gcn_igate
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.attach import planner as chuyen_doi_igate
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.attach import planner as chuyen_doi
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.attach import planner as phuong_xa
from app.pipelines.dang_ky_bien_dong_lao_cai.attach import planner as bien_dong
from app.pipelines.dang_ky_bien_dong_thoa_thuan_igate_lao_cai.attach import planner as bien_dong_igate
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach import planner as quyen_sdd
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.attach import planner as dk_dat_dai
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.attach import planner as thu_hoi
from app.pipelines.thu_hoi_gcn_igate_lao_cai.attach import planner as thu_hoi_igate


def _files(n):
    return [{"name": f"t{i}.pdf", "_index": i} for i in range(n)]


def _llm(*labels):
    return {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}


def _by_file(items):
    return {item["fileIndex"]: item for item in items}


@pytest.mark.parametrize("planner, don, call", [
    (chuyen_doi, "don_mau_02", lambda p, f, t: p.build_plan_items(f, t, "")),
    (phuong_xa, "don_mau_02", lambda p, f, t: p.build_plan_items(f, t)),
    (bien_dong, "don_dang_ky", lambda p, f, t: p.build_plan_items(f, t, "")),
    (quyen_sdd, "don_dang_ky", lambda p, f, t: p.build_plan_items(f, t)),
    (dk_dat_dai, "don_dang_ky", lambda p, f, t: p.build_plan_items(f, t)),
    (thu_hoi, "don_kien_nghi", lambda p, f, t: p.build_plan_items(f, t)),
])
def test_cong_cu_co_giay_to_khac_cccd_va_tep_la_vao_giay_to_khac(planner, don, call):
    items, warnings, classified, *_ = call(planner, _files(3), _llm(don, "khac", "cccd"))
    by_file = _by_file(items)
    assert sorted(by_file) == [0, 1, 2]
    assert by_file[0]["target"] == "fixed-slot"
    for idx, kind in ((1, "khac"), (2, "cccd")):
        assert by_file[idx]["target"] == "new" and by_file[idx]["detectedType"] == kind
    assert by_file[2]["documentName"] == "Căn cước công dân"
    assert any("t1.pdf" in w and "t2.pdf" in w and "Giấy tờ khác" in w for w in warnings)
    assert not any("bỏ qua" in w for w in warnings)
    assert all(c["target"] != "skip" for c in classified)


def test_cap_gcn_cong_cu_cccd_va_tep_la_vao_o_don_cua_nhanh():
    items, warnings, classified, branch = cap_gcn.build_plan_items(_files(3), [], _llm("hop_dong", "khac", "cccd"), "a")
    by_file = _by_file(items)
    assert branch == "a" and sorted(by_file) == [0, 1, 2]
    don_slot = cap_gcn.catalog.slot("a", "don_dang_ky")
    for idx, kind in ((1, "khac"), (2, "cccd")):
        assert by_file[idx]["target"] == "fixed-slot"
        assert by_file[idx]["slotKey"] == don_slot["slotKey"]
        assert by_file[idx]["detectedType"] == kind
    assert any("t1.pdf" in w and "t2.pdf" in w and don_slot["slotName"] in w for w in warnings)
    assert [c.get("routedTo") for c in classified] == [None, "don_dang_ky", "don_dang_ky"]


def test_cap_gcn_igate_cccd_va_tep_la_vao_dong_don_nhanh():
    items, warnings, _, _ = cap_gcn_igate.build_plan_items(_files(3), [], _llm("hop_dong", "khac", "cccd"), "b", None)
    by_file = _by_file(items)
    assert sorted(by_file) == [0, 1, 2]
    assert [by_file[i]["componentIndex"] for i in range(3)] == [10, 9, 9]
    assert all(i["target"] == "attp-row" for i in items)
    assert any("t1.pdf" in w and "t2.pdf" in w for w in warnings)


def test_chuyen_doi_igate_cccd_va_tep_la_vao_dong_don_nhom():
    items, warnings, _, _ = chuyen_doi_igate.build_plan_items(_files(3), _llm("don_mau_17", "khac", "cccd"), "", None)
    assert [i["componentIndex"] for i in items] == [6, 6, 6]
    assert [i["detectedType"] for i in items] == ["don_mau_17", "khac", "cccd"]
    assert any("t1.pdf" in w and "t2.pdf" in w for w in warnings)


def test_bien_dong_igate_cccd_va_tep_la_vao_dong_don_nhom():
    items, warnings, _, _, _ = bien_dong_igate.build_plan_items(_files(3), _llm("don_dang_ky", "khac", "cccd"), "1", None)
    assert [i["componentIndex"] for i in items] == [1, 1, 1]
    assert any("t1.pdf" in w and "t2.pdf" in w for w in warnings)
    assert not any("bỏ qua" in w for w in warnings)


def test_thu_hoi_igate_cccd_va_tep_la_vao_dong_kien_nghi():
    items, warnings, classified = thu_hoi_igate.build_plan_items(_files(3), _llm("gcn", "khac", "cccd"), None)
    assert [i["componentIndex"] for i in items] == [2, 1, 1]
    assert [c.get("routedTo") for c in classified] == [None, "kien_nghi", "kien_nghi"]
    assert any("t1.pdf" in w and "t2.pdf" in w for w in warnings)
