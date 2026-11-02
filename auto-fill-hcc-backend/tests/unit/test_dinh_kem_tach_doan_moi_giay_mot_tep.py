"""Planner tách đoạn (attp-row): nhiều giấy cùng dòng → mỗi giấy một item riêng, KHÔNG gộp thành một PDF.

Đoạn phủ trọn tệp → đính nguyên tệp (không sourceSegments); đoạn là một phần tệp → sourceSegments đúng 1 đoạn của
chính tệp đó. Dữ liệu giả.
"""

import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.attach import planner as bao_cao_dai_hoi
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach import planner as moi_gioi
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach import planner as chia_tach_hoi
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach import planner as dang_ky_lai
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach import planner as thong_bao_dai_hoi

_TEXT = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nNGUYEN VAN A"

# (module, hai loại khác nhau cùng vào một dòng, dòng đó)
_CASES = [
    (bao_cao_dai_hoi, ("bao_cao_tong_ket", "bao_cao_kiem_diem"), 11),
    (chia_tach_hoi, ("so_yeu_ly_lich", "ly_lich_tu_phap"), 6),
    (thong_bao_dai_hoi, ("bien_ban", "danh_sach"), 3),
    (moi_gioi, ("cccd", "cccd"), 2),
    (dang_ky_lai, ("hop_dong", "hoa_don"), 3),
]
_IDS = [c[0].__name__.split(".")[2] for c in _CASES]


def _plan(mod, layout):
    """layout: danh sách tệp, mỗi tệp là danh sách (pageFrom, pageTo, type)."""
    raw_files = [{"name": f"tep{i}.pdf", "type": "application/pdf"} for i in range(len(layout))]
    segments, file_meta, pages = [], {}, {}
    for i, parts in enumerate(layout):
        page_count = max(p[1] for p in parts)
        file_meta[i] = {"pageCount": page_count, "pageBoundariesAvailable": True}
        pages[i] = {p: _TEXT for p in range(1, page_count + 1)}
        segments += [{"fileIndex": i, "pageFrom": a, "pageTo": b, "type": t, "documentName": ""} for a, b, t in parts]
    out = mod.build_plan_items(raw_files, segments, file_meta, pages)
    AttachmentPlanResp.model_validate({"attachments": out[0]})
    return out[0]


@pytest.mark.parametrize(("mod", "types", "row"), _CASES, ids=_IDS)
def test_hai_tep_cung_dong_thanh_hai_item_nguyen_tep(mod, types, row):
    items = [i for i in _plan(mod, [[(1, 1, types[0])], [(1, 2, types[1])]]) if i["componentIndex"] == row]
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert not any(i.get("sourceFileIndexes") or i.get("sourceSegments") for i in items)
    assert len({i["documentName"] for i in items}) == 2


@pytest.mark.parametrize(("mod", "types", "row"), _CASES, ids=_IDS)
def test_hai_giay_trong_mot_pdf_thanh_hai_item_cat_trang(mod, types, row):
    items = [i for i in _plan(mod, [[(1, 1, types[0]), (2, 3, types[1])]]) if i["componentIndex"] == row]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1, 2]}],
    ]
    assert [i["detectedType"] for i in items] == list(types)
    assert not any(i.get("sourceFileIndexes") for i in items)
