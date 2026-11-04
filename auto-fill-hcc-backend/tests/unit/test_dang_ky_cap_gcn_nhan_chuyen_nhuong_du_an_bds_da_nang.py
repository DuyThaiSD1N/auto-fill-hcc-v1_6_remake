"""[Đà Nẵng] Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án BĐS — detect khoá host + hai mode đính kèm
(tách / không tách theo cài đặt "Có tách hồ sơ khi đính kèm"). Dữ liệu trong test đều là placeholder."""

import json

import pytest

from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.attach import planner as P
from app.process.schemas import FileItem
from app.procedures.registry import public_list

_KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san"


def test_registry_detect_khoa_host_da_nang_khong_de_ban_lao_cai():
    entries = {p["key"]: p for p in public_list()}
    assert entries[_KEY]["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    lao_cai = entries["dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai"]
    assert "dichvucong.danang.gov.vn" not in lao_cai["detect"].get("urlScope", [])


def test_registry_khai_supports_split_documents_de_extension_gui_cai_dat():
    entries = {p["key"]: p for p in public_list()}
    assert entries[_KEY]["supportsSplitDocuments"] is True


# Tệp 0 gộp cả bộ, mở đầu bằng CCCD; tệp 1 chỉ có biên bản bàn giao.
_PAGES = {
    0: {1: "CĂN CƯỚC CÔNG DÂN", 2: "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG", 3: "HỢP ĐỒNG MUA BÁN", 4: "tiếp", 5: "BIÊN BẢN BÀN GIAO",
        6: "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", 7: "HÓA ĐƠN GIÁ TRỊ GIA TĂNG"},
    1: {1: "BIÊN BẢN BÀN GIAO", 2: ""},
}
_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "giay_to_nhan_than", "documentName": "Căn cước công dân"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "don_mau_18", "documentName": "Đơn đăng ký biến động"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 4, "type": "hop_dong_chuyen_nhuong", "documentName": "Hợp đồng mua bán"},
    {"fileIndex": 0, "pageFrom": 5, "pageTo": 5, "type": "bien_ban_ban_giao", "documentName": ""},
    {"fileIndex": 0, "pageFrom": 6, "pageTo": 6, "type": "gcn_chu_dau_tu", "documentName": ""},
    {"fileIndex": 0, "pageFrom": 7, "pageTo": 7, "type": "chung_tu_tai_chinh", "documentName": ""},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "bien_ban_ban_giao", "documentName": "Biên bản bàn giao"},
    {"fileIndex": 1, "pageFrom": 2, "pageTo": 2, "type": "trang_trang", "documentName": ""},
]
_RAW_FILES = [{"name": "ho-so-gop.pdf"}, {"name": "ban-giao.pdf"}]


def _meta():
    return {i: {"pageCount": len(p), "pageBoundariesAvailable": True} for i, p in _PAGES.items()}


def test_khong_tach_moi_tep_dinh_nguyen_vao_dong_giay_chinh_dau_tien():
    items, classified, errors = P.build_attachments(
        _SEGMENTS, _RAW_FILES, _meta(), _PAGES, {0: "x", 1: "x"}, split=False
    )

    assert all("sourceSegments" not in it for it in items)
    # Tệp gộp mở đầu bằng CCCD vẫn vào dòng Đơn (giấy có dòng riêng đầu tiên), không về dòng 7.
    assert [(it["fileIndex"], it["componentIndex"]) for it in items] == [(0, 2), (1, 4), (1, 8)]
    assert [c["componentIndex"] for c in classified] == [2, 4]
    # Giấy nằm trong tệp gộp vẫn tính là đã nhận ra → không cảnh báo thiếu.
    assert errors == []


def test_tach_cat_trang_tung_giay_nhu_cu():
    items, _, _ = P.build_attachments(_SEGMENTS, _RAW_FILES, _meta(), _PAGES, {0: "x", 1: "x"})

    assert [(it["fileIndex"], it["componentIndex"]) for it in items] == [
        (0, 2), (0, 3), (0, 4), (1, 4), (0, 8), (1, 8), (0, 5), (0, 7), (0, 7), (0, 11), (0, 11),
    ]
    assert all(it.get("sourceSegments") for it in items if it["fileIndex"] == 0)
    assert all("sourceSegments" not in it for it in items if it["fileIndex"] == 1)


def _ocr_text(pages: dict[int, str]) -> str:
    total = len(pages)
    return "\n".join(f"───── Trang {n}/{total} ─────\n{text}" for n, text in pages.items())


@pytest.mark.parametrize(
    ("options", "split"),
    [({"splitDocuments": True}, True), ({"splitDocuments": False}, False), ({}, False), (None, False)],
)
async def test_plan_theo_cai_dat_split_documents(monkeypatch, options, split):
    async def fake_ocr(files):
        return [{"text": _ocr_text(_PAGES[i])} for i in range(len(files))]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": _SEGMENTS}, ensure_ascii=False)

    monkeypatch.setattr(P.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(P.client, "chat", fake_chat)
    files = [FileItem(name=f["name"], type="application/pdf", role="attachment",
                      dataUrl="data:application/pdf;base64,") for f in _RAW_FILES]

    result = await P.plan(files, options)

    cut = [it for it in result["attachments"] if it.get("sourceSegments")]
    assert bool(cut) is split
    assert result["extracted"]["attachmentMode"] == ("split_documents" if split else "preserve_files")
    if not split:
        assert len(result["attachments"]) == 3
