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



# ---------------- Báo cáo tổ chức đại hội hội: tôn trọng cài đặt "Có tách hồ sơ khi đính kèm" ----------------
_BC_LAYOUT = [(1, 2, "bao_cao_to_chuc_dai_hoi"), (3, 3, "de_an_nhan_su"), (4, 5, "bao_cao_tong_ket")]
_BC_TEXTS = {
    "bao_cao_to_chuc_dai_hoi": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBÁO CÁO tổ chức đại hội nhiệm kỳ\nKính gửi: Sở Nội vụ"
                               "\nThời gian, địa điểm: hội trường A",
    "de_an_nhan_su": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐỀ ÁN NHÂN SỰ Ban chấp hành",
    "bao_cao_tong_ket": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBÁO CÁO TỔNG KẾT nhiệm kỳ",
}


def _bc_inputs():
    raw_files = [{"name": "ho-so-gop.pdf", "type": "application/pdf"}]
    segments = [{"fileIndex": 0, "pageFrom": a, "pageTo": b, "type": t, "documentName": ""} for a, b, t in _BC_LAYOUT]
    pages = {0: {p: _BC_TEXTS[t] for a, b, t in _BC_LAYOUT for p in range(a, b + 1)}}
    return raw_files, segments, {0: {"pageCount": 5, "pageBoundariesAvailable": True}}, pages


def test_bao_cao_dai_hoi_tat_tach_dinh_nguyen_tep_mot_lan():
    attachments, classified, warnings, case = bao_cao_dai_hoi.build_plan_items(*_bc_inputs(), split=False)
    AttachmentPlanResp.model_validate({"attachments": attachments})
    assert case == "nhiem_ky"
    assert [(a["fileIndex"], a["componentIndex"]) for a in attachments] == [(0, 15)]
    assert not any(a.get("sourceSegments") or a.get("sourceFileIndexes") for a in attachments)
    assert attachments[0]["includedTypes"] == ["bao_cao_to_chuc_dai_hoi", "de_an_nhan_su", "bao_cao_tong_ket"]
    assert all(c["componentIndex"] == 15 and c["preservedFile"] for c in classified)
    assert any("Đã tắt" in w and "dòng 15" in w for w in warnings)
    # Giấy có trong tệp gộp thì không báo "chưa có"; giấy thật sự thiếu vẫn báo.
    assert not any("Chưa có Đề án nhân sự" in w or "Chưa có Dự thảo báo cáo tổng kết" in w for w in warnings)
    assert not any("Chưa có Dự kiến thời gian" in w for w in warnings)
    assert any("Chưa có Nghị quyết của Ban chấp hành" in w for w in warnings)


def test_bao_cao_dai_hoi_bat_tach_cat_trang_tung_giay():
    attachments, _, warnings, _ = bao_cao_dai_hoi.build_plan_items(*_bc_inputs(), split=True)
    rows = sorted(a["componentIndex"] for a in attachments)
    assert rows == [3, 6, 11, 15]
    assert all(a.get("sourceSegments") for a in attachments)
    assert not any("Đã tắt" in w for w in warnings)


def _bc_pdf_file(pages: int) -> "FileItem":
    import base64

    import fitz

    from app.process.schemas import FileItem

    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name="ho-so-gop.pdf", type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


@pytest.mark.parametrize(("options", "expect_split"), [
    ({}, False),
    ({"splitDocuments": False}, False),
    ({"splitDocuments": True}, True),
    ({"splitDocuments": True, "supportsSourceSegments": False}, False),
])
def test_bao_cao_dai_hoi_plan_doc_co_split_documents(monkeypatch, options, expect_split):
    import asyncio
    import json

    text = "\n".join(
        f"───── Trang {p}/5 ─────\n{_BC_TEXTS[t]}" for a, b, t in _BC_LAYOUT for p in range(a, b + 1)
    )

    async def fake_ocr(files):
        return [{"name": f["name"], "text": text} for f in files]

    async def fake_chat(*_args, **_kwargs):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": a, "pageTo": b, "type": t} for a, b, t in _BC_LAYOUT
        ]})

    monkeypatch.setattr(bao_cao_dai_hoi.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(bao_cao_dai_hoi.client, "chat", fake_chat)
    out = asyncio.run(bao_cao_dai_hoi.plan([_bc_pdf_file(5)], options))
    attachments = out["attachments"]
    assert out["extracted"]["attachmentMode"] == ("split_documents" if expect_split else "preserve_files")
    if expect_split:
        assert len(attachments) > 1 and all(a.get("sourceSegments") for a in attachments)
    else:
        assert len(attachments) == 1 and not attachments[0].get("sourceSegments")


def test_bao_cao_dai_hoi_khai_supports_split_documents():
    from app.channels.handfree.procedure_registry import get_procedure as get_handfree
    from app.procedures.registry import get_procedure

    key = "bao-cao-to-chuc-dai-hoi-hoi-cap-tinh"
    assert get_procedure(key)["supportsSplitDocuments"] is True
    assert get_handfree(key)["supportsSplitDocuments"] is True
