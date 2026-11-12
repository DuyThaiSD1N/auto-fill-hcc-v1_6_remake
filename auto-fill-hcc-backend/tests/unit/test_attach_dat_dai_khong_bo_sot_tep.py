"""Attach planner đất đai (Đà Nẵng / Lâm Đồng): CCCD, giấy chưa rõ loại, tệp không đọc được chữ đều phải có item ở
dòng Đơn / Phiếu yêu cầu (dòng chính) — không bỏ sót tệp. Dữ liệu trong test đều là placeholder."""

import importlib

import pytest

from app.process.schemas import FileItem

_UNKNOWN = "TÀI LIỆU KHÔNG XÁC ĐỊNH"
_CCCD = "CĂN CƯỚC CÔNG DÂN\nNGUYEN VAN A\n001000000001"

# package → hằng dòng chính trong planner.
_SIMPLE = [
    ("cap_gcn_so_nha_da_nang", "_DON"),
    ("chuyen_muc_dich_su_dung_dat_da_nang", "_DON"),
    ("dang_ky_bien_dong_dat_dai_da_nang", "_DON"),
    ("dang_ky_bien_phap_bao_dam_qsdd", "_PHIEU"),
    ("dang_ky_dat_dai_lan_dau_da_nang", "_DON_M15"),
    ("tach_hop_thua_dat_da_nang", "_DON"),
    ("xac_nhan_ho_so_so_nha_da_nang", "_DON"),
    ("xoa_dang_ky_bien_phap_bao_dam_da_nang", "_PHIEU_03A"),
    ("dang_ky_thay_doi_bien_phap_bao_dam_qsdd", "_PHIEU_02A"),
]


def _planner(pkg: str):
    return importlib.import_module(f"app.pipelines.{pkg}.attach.planner")


@pytest.mark.parametrize("pkg,main", _SIMPLE)
def test_cccd_va_giay_la_dinh_chung_dong_chinh(pkg, main):
    P = _planner(pkg)
    files = [{"name": "la.pdf"}, {"name": "cccd.jpg"}, {"name": "khong-chu.pdf"}]
    ocr = [{"name": "la.pdf", "text": _UNKNOWN}, {"name": "cccd.jpg", "text": _CCCD}]
    items, warnings, classified = P.build_plan_items(files, ocr, {0: "other", 1: "cccd"})

    main_type = getattr(P, main)
    row = P._ROWS[main_type]
    assert [it["fileIndex"] for it in items] == [0, 1, 2]
    assert all(it["componentName"] == row["componentName"] and it["target"] == "attp-row" for it in items)
    assert [it["detectedType"] for it in items] == ["other", "cccd", "other"]
    assert [it["documentName"] for it in items] == ["la.pdf", "cccd.jpg", "khong-chu.pdf"]
    assert all(c["routedTo"] == main_type for c in classified)
    shared = [w for w in warnings if "đã đính chung dòng" in w]
    assert len(shared) == 1 and all(n in shared[0] for n in ("la.pdf", "cccd.jpg", "khong-chu.pdf"))
    assert not any("thủ công" in w for w in warnings)


def _segments_fixture(full_texts: dict[int, str], pages: dict[int, dict[int, str]]):
    file_meta = {i: {"pageCount": len(p), "pageBoundariesAvailable": True} for i, p in pages.items()}
    return file_meta, pages, full_texts


def test_chia_tach_cccd_va_doan_la_thanh_file_rieng_o_dong_1():
    P = _planner("dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua")
    raw_files = [{"name": "ho-so.pdf"}, {"name": "anh.jpg"}]
    pages = {0: {1: "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI Mẫu số 18", 2: _CCCD, 3: _UNKNOWN, 4: ""}, 1: {1: ""}}
    file_meta, page_text, full_text = _segments_fixture({0: "x" * 50, 1: ""}, pages)
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_mau_18", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "cccd", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "other", "documentName": "Bảng kê tài liệu"},
        {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "other", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "other", "documentName": ""},
    ]
    items, classified, warnings = P.build_plan_items(raw_files, segments, file_meta, page_text, full_text)

    assert [it["componentIndex"] for it in items] == [1, 1, 1, 1]
    don, cccd, la, anh = items
    assert don["detectedType"] == "don_mau_18" and len(don["sourceSegments"]) == 1
    assert cccd["detectedType"] == "cccd" and cccd["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    assert la["documentName"] == "Bảng kê tài liệu" and la["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2]}]
    assert anh["fileIndex"] == 1 and anh["documentName"] == "anh" and "sourceSegments" not in anh
    assert any("trang trắng" in w and "trang 4-4" in w for w in warnings)
    assert any("đã đính chung dòng" in w and "anh.jpg" in w for w in warnings)


def test_tai_san_cccd_va_doan_la_dinh_dong_don():
    P = _planner("dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn")
    raw_files = [{"name": "ho-so.pdf"}, {"name": "anh.jpg"}]
    pages = {0: {1: "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI Mẫu số 18", 2: _CCCD, 3: _UNKNOWN, 4: ""}, 1: {1: ""}}
    file_meta, page_text, full_text = _segments_fixture({0: "x" * 50, 1: ""}, pages)
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_mau_18", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "cccd", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "other", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "other", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "other", "documentName": ""},
    ]
    items, classified, warnings = P.build_plan_items(raw_files, segments, file_meta, page_text, full_text)

    don_row = P._ROWS[P._DON18]
    assert [it["detectedType"] for it in items] == ["don_mau_18", "cccd", "other", "other"]
    assert all(it["componentIndex"] == don_row["componentIndex"] for it in items)
    assert [it.get("sourceSegments") for it in items[1:3]] == [
        [{"fileIndex": 0, "pageIndexes": [1]}], [{"fileIndex": 0, "pageIndexes": [2]}]
    ]
    assert len({it["documentName"] for it in items}) == 4
    assert sum(1 for c in classified if c.get("routedTo") == P._DON18) == 3
    assert any("trang trắng" in w for w in warnings)


def test_nha_nuoc_giao_cccd_va_giay_la_vao_dong_1():
    P = _planner("dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly")
    raw_files = [{"name": "ho-so.pdf"}, {"name": "anh.jpg"}]
    pages = {
        0: {1: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐĂNG KÝ ĐẤT ĐAI", 2: _CCCD,
            3: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n" + _UNKNOWN},
        1: {1: ""},
    }
    file_meta, page_text, full_text = _segments_fixture({0: "x" * 50, 1: ""}, pages)
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_mau_15", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "cccd", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "other", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "other", "documentName": ""},
    ]
    items, classified, warnings = P.build_plan_items(raw_files, segments, file_meta, page_text, full_text)

    assert [it["componentIndex"] for it in items] == [1, 1, 1, 1]
    assert [it["detectedType"] for it in items] == ["don_mau_15", "cccd", "other", "other"]
    assert items[3]["fileIndex"] == 1 and items[3]["documentName"].startswith("D1-04 ")
    assert all(len(it["sourceSegments"]) == 1 for it in items)
    assert any("đã đính chung dòng" in w and "anh.jpg" in w for w in warnings)


async def test_dinh_chinh_gcn_giay_la_va_tep_khong_chu_vao_dong_don(monkeypatch):
    P = _planner("dinh_chinh_gcn_da_cap_da_nang")
    texts = {"don.jpg": "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI Mẫu số 18", "cccd.jpg": _CCCD, "la.jpg": _UNKNOWN}

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_llm(documents):
        return []

    monkeypatch.setattr(P.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(P, "_classify_with_llm", fake_llm)
    files = [
        FileItem(name=n, type=t, dataUrl="data:;base64,", role="")
        for n, t in (("don.jpg", "image/jpeg"), ("cccd.jpg", "image/jpeg"), ("la.jpg", "image/jpeg"),
                     ("anh.png", "image/png"))
    ]
    res = await P.plan(files)

    by_file = {it["fileName"]: it for it in res["attachments"]}
    assert set(by_file) == {"don.jpg", "cccd.jpg", "la.jpg", "anh.png"}
    assert by_file["cccd.jpg"]["componentIndex"] == 2
    assert by_file["la.jpg"]["componentIndex"] == 4 and by_file["la.jpg"]["detectedType"] == "other"
    assert by_file["anh.png"]["componentIndex"] == 4
    assert any("đã đính chung dòng" in e and "la.jpg" in e and "anh.png" in e for e in res["errors"])


def test_dinh_chinh_lam_dong_giay_la_va_cccd_vao_o_don():
    P = _planner("dinh_chinh_sai_sot_lam_dong")
    files = [{"name": "la.pdf"}, {"name": "cccd.jpg"}, {"name": "bo-qua.pdf"}]
    ocr = [{"name": "la.pdf", "text": _UNKNOWN}, {"name": "cccd.jpg", "text": _CCCD}, {"name": "bo-qua.pdf", "text": ""}]
    llm = {0: {"type": "other", "title": "Bảng kê tài liệu"}, 1: {"type": "identity_document", "title": ""},
           2: {"type": "skip", "title": ""}}
    items, warnings, classified = P.build_plan_items(files, ocr, llm)

    assert sorted(it["fileIndex"] for it in items) == [0, 1, 2]
    assert {it["slotKey"] for it in items} == {"dinhchinh_ld_application"}
    assert all(it["target"] == "fixed-slot" for it in items)
    routed = {it["fileName"]: it for it in items if it["detectedType"] in ("other", "skip")}
    assert routed["la.pdf"]["documentName"] == "Bảng kê tài liệu"
    assert routed["bo-qua.pdf"]["documentName"] == "bo-qua"
    assert len(warnings) == 1 and "la.pdf" in warnings[0] and "bo-qua.pdf" in warnings[0]


_GCN = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nThửa đất số 1, tờ bản đồ số 2\nNGƯỜI SỬ DỤNG ĐẤT: NGUYEN VAN A"
_DON_18 = "Mẫu số 18\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\nIV. (2) Giấy ủy quyền"
_BANG_18A = (
    "Bảng 18a: Danh sách những người sử dụng đất, tài sản gắn liền với đất\n"
    "| STT | Tên người sử dụng đất | Địa chỉ |\n| 1 | NGUYEN VAN A | Xã Bất Kỳ |"
)
_KHAI_SINH = "GIẤY KHAI SINH\nHọ tên: NGUYEN VAN A"
_UY_QUYEN = "GIẤY ỦY QUYỀN\nBên ủy quyền: NGUYEN VAN A\nBên được ủy quyền: TRAN THI B"


def test_dinh_chinh_lam_dong_dung_thu_tu_dong_moi_va_gui_tu_khoa():
    """Cổng 1.116358 (12/11/2026): [0] Đơn Mẫu 18, [1] GCN đã cấp, [2] chứng minh sai sót, [3] đại diện."""
    P = _planner("dinh_chinh_sai_sot_lam_dong")
    files = [{"name": n} for n in ("gcn.pdf", "don.pdf", "bang18a.pdf", "ks.pdf", "uq.pdf", "cccd.jpg")]
    ocr = [
        {"name": "gcn.pdf", "text": _GCN}, {"name": "don.pdf", "text": _DON_18},
        {"name": "bang18a.pdf", "text": _BANG_18A}, {"name": "ks.pdf", "text": _KHAI_SINH},
        {"name": "uq.pdf", "text": _UY_QUYEN}, {"name": "cccd.jpg", "text": _CCCD},
    ]
    # LLM trả other cho Bảng 18a → rule phải nhận là phụ lục Đơn, không phải GCN.
    llm = {0: {"type": "land_certificate"}, 1: {"type": "change_application"}, 2: {"type": "other"},
           3: {"type": "birth_certificate"}, 4: {"type": "authorization"}, 5: {"type": "identity_document"}}
    items, warnings, _ = P.build_plan_items(files, ocr, llm)

    row = {it["fileName"]: (it["slotIndex"], it["componentIndex"]) for it in items}
    assert row == {
        "don.pdf": (0, 1), "bang18a.pdf": (0, 1), "cccd.jpg": (0, 1),
        "gcn.pdf": (1, 2), "ks.pdf": (2, 3), "uq.pdf": (3, 4),
    }
    assert [it["fileName"] for it in items if it["slotIndex"] == 0] == ["don.pdf", "bang18a.pdf", "cccd.jpg"]
    assert not warnings
    assert all(it["slotKeywords"] for it in items)


def test_dinh_chinh_lam_dong_tu_khoa_khop_dung_mot_dong_tren_cong():
    """slotKeywords của từng ô chỉ khớp đúng một dòng trên bảng thật (chữ crawl ngày 12/11/2026, đã bỏ dấu)."""
    from app.pipelines._shared import fold

    P = _planner("dinh_chinh_sai_sot_lam_dong")
    rows = [fold(slot["slotName"]) for slot in P.SLOTS]
    for slot in P.SLOTS:
        hits = [i for i, text in enumerate(rows) if any(kw in text for kw in slot["slotKeywords"])]
        assert hits == [slot["slotIndex"]], slot["slotKey"]
