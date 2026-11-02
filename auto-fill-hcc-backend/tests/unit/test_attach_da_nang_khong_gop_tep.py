"""Attach planner đất đai Đà Nẵng (attp-row, ô upload `multiple`): nhiều tệp / nhiều giấy cùng dòng → mỗi giấy một
item riêng, không `sourceFileIndexes`, không `sourceSegments` xuyên tệp. Dữ liệu trong test đều là placeholder."""

import importlib

from app.attachments.schemas import AttachmentPlanResp


def _planner(pkg: str):
    return importlib.import_module(f"app.pipelines.{pkg}.attach.planner")


def _assert_khong_gop(items: list[dict]) -> None:
    AttachmentPlanResp(attachments=items)
    for it in items:
        assert not it.get("sourceFileIndexes")
        segs = it.get("sourceSegments") or []
        assert len(segs) <= 1
        assert all(s["fileIndex"] == it["fileIndex"] and s["pageIndexes"] is not None for s in segs)


def _meta(pages: dict[int, dict[int, str]]):
    return {i: {"pageCount": len(p), "pageBoundariesAvailable": True} for i, p in pages.items()}


def test_chia_tach_hai_tep_cung_dong_thanh_hai_item():
    P = _planner("dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua")
    raw_files = [{"name": "ho-so.pdf"}, {"name": "to-khai.pdf"}]
    pages = {0: {1: "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG", 2: "GIẤY CHỨNG NHẬN", 3: "GIẤY CHỨNG NHẬN trang bổ sung"},
             1: {1: "TỜ KHAI LỆ PHÍ TRƯỚC BẠ"}}
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_mau_18", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "gcn_da_cap", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "gcn_da_cap", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "to_khai_thue", "documentName": ""},
    ]
    items, _, _ = P.build_plan_items(raw_files, segments, _meta(pages), pages, {0: "x" * 50, 1: "x" * 50})

    _assert_khong_gop(items)
    don, to_khai, gcn = items
    assert (don["componentIndex"], to_khai["componentIndex"], gcn["componentIndex"]) == (1, 1, 2)
    assert don["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert to_khai["fileIndex"] == 1 and "sourceSegments" not in to_khai and to_khai["detectedType"] == "to_khai_thue"
    # Hai trang liền của CÙNG một GCN vẫn là một đoạn.
    assert gcn["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]
    assert len({it["documentName"] for it in items}) == 3


def test_nhan_chuyen_nhuong_hai_tep_cung_dong_thanh_hai_item_va_dong_lap_lai_theo_tung_item():
    P = _planner("dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san")
    raw_files = [{"name": "hop-dong.pdf"}, {"name": "sua-doi.pdf"}, {"name": "ban-giao.pdf"}]
    pages = {0: {1: "HỢP ĐỒNG MUA BÁN", 2: "tiếp"}, 1: {1: "VĂN BẢN SỬA ĐỔI, BỔ SUNG SỐ"},
             2: {1: "BIÊN BẢN BÀN GIAO", 2: "", 3: "CĂN CƯỚC CÔNG DÂN NGUYEN VAN A 001000000001"}}
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "hop_dong_chuyen_nhuong", "documentName": "Hợp đồng"},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "other", "documentName": "", "fallback": True},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "hop_dong_chuyen_nhuong", "documentName": ""},
        {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "bien_ban_ban_giao", "documentName": ""},
        {"fileIndex": 2, "pageFrom": 2, "pageTo": 2, "type": "trang_trang", "documentName": ""},
        {"fileIndex": 2, "pageFrom": 3, "pageTo": 3, "type": "giay_to_nhan_than", "documentName": ""},
    ]
    full = {0: "x", 1: "x", 2: "x"}
    items, _, _ = P.build_attachments(segments, raw_files, _meta(pages), pages, full)

    _assert_khong_gop(items)
    by_row: dict[int, list[dict]] = {}
    for it in items:
        by_row.setdefault(it["componentIndex"], []).append(it)
    hop_dong = by_row[3]
    assert [it["fileIndex"] for it in hop_dong] == [0, 1]
    assert all("sourceSegments" not in it for it in hop_dong)  # trang tiếp của hợp đồng đi cùng đoạn → trọn file
    assert len({it["documentName"] for it in hop_dong}) == 2
    assert by_row[4][0]["sourceSegments"] == [{"fileIndex": 2, "pageIndexes": [0, 1]}]
    assert by_row[8] == [{**by_row[4][0], "componentName": P._ROWS[8]["componentName"], "componentIndex": 8,
                          "loaiBan": P._ROWS[8]["loaiBan"]}]
    assert by_row[7][0]["sourceSegments"] == [{"fileIndex": 2, "pageIndexes": [2]}]
    assert 11 not in by_row  # dòng 7 không có chứng từ tài chính → không đính lại dòng 11


def test_xoa_thue_hai_tep_cung_dong_thanh_hai_item():
    P = _planner("xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang")
    files = [{"name": "cccd.jpg"}, {"name": "don.pdf"}, {"name": "gcn.pdf"}]
    llm = {0: {"docType": "cccd", "containsTypes": {"cccd"}},
           1: {"docType": "don_bien_dong", "containsTypes": {"don_bien_dong"}},
           2: {"docType": "gcn_da_cap", "containsTypes": {"gcn_da_cap"}}}
    items, _, _ = P.build_plan_items(files, {0: "x", 1: "x", 2: "x"}, llm)

    _assert_khong_gop(items)
    assert [(it["componentIndex"], it["fileIndex"]) for it in items] == [(1, 1), (1, 0), (2, 2)]
    assert all("sourceSegments" not in it for it in items)
    assert [it["detectedType"] for it in items] == ["don_bien_dong", "cccd", "gcn_da_cap"]
    assert len({it["documentName"] for it in items}) == 3
