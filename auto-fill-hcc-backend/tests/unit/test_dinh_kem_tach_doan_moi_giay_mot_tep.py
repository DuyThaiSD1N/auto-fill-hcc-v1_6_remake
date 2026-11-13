"""Planner tách đoạn (attp-row): nhiều giấy cùng dòng → mỗi giấy một item riêng, KHÔNG gộp thành một PDF.

Đoạn phủ trọn tệp → đính nguyên tệp (không sourceSegments); đoạn là một phần tệp → sourceSegments đúng 1 đoạn của
chính tệp đó. Dữ liệu giả.
"""

import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.attach import planner as bao_cao_dai_hoi
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_tach import planner as moi_gioi
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_tach import planner as chia_tach_hoi
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach.dinh_kem_tach import planner as dang_ky_lai
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach.dinh_kem_tach import planner as thong_bao_dai_hoi

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


# ---------------- 5 thủ tục đất đai Đà Nẵng (attp-row): tách / không tách theo cài đặt "Tách giấy tờ" ----------------
# (thủ tục, đoạn của PDF gộp 4 trang khi tách: (từ trang, đến trang, loại, dòng),
#  tệp khi không tách: (docTypes LLM trả, dòng của giấy chính) — tệp đầu luôn gộp giấy của hai dòng, dòng dự phòng)
_DN_CASES = [
    ("dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua",
     [(1, 1, "don_mau_18", 1), (2, 3, "gcn_da_cap", 2), (4, 4, "gcn_dang_ky_doanh_nghiep", 7)],
     [(["gcn_da_cap", "don_mau_18"], 1), (["van_ban_dai_dien"], 3), (["qd_to_chuc_lai", "cccd"], 8)], 1),
    ("dinh_chinh_gcn_da_cap_da_nang",
     [(1, 1, "don_mau_18", 4), (2, 3, "gcn_da_cap", 1), (4, 4, "giay_to_chung_minh", 2)],
     [(["gcn_da_cap", "giay_to_chung_minh"], 1), (["van_ban_uy_quyen"], 3), (["giay_to_chung_minh"], 2)], 4),
    ("xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004",
     [(1, 1, "don_bien_dong", 3), (2, 3, "gcn_da_cap", 1), (4, 4, "van_ban_dai_dien", 2)],
     [(["gcn_da_cap", "don_bien_dong"], 3), (["gcn_da_cap"], 1), (["van_ban_dai_dien"], 2)], 3),
    ("dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn",
     [(1, 1, "don_mau_18", 1), (2, 3, "gcn_da_cap", 2), (4, 4, "ho_so_thiet_ke", 5)],
     [(["gcn_da_cap", "don_mau_18"], 1), (["so_do_cong_trinh"], 4), (["van_ban_dai_dien"], 8)], 1),
    ("dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly",
     [(1, 1, "don_mau_15", 1), (2, 3, "bao_cao_ra_soat", 2), (4, 4, "quyet_dinh", 1)],
     [(["bao_cao_ra_soat", "don_mau_15"], 1), (["bao_cao_ra_soat", "trich_luc_ban_do"], 2), (["quyet_dinh"], 1)], 1),
]
_DN_IDS = [c[0] for c in _DN_CASES]
_DN_PAGE = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY TỜ MẪU SỐ {p}\nNGUYEN VAN A, thửa đất số 99, tờ bản đồ số 9"


def _dn_pdf(name: str, pages: int):
    import base64

    import fitz

    from app.process.schemas import FileItem

    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name=name, type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


def _dn_image(name: str):
    from app.process.schemas import FileItem

    return FileItem(name=name, type="image/jpeg", role="doc", dataUrl="data:image/jpeg;base64,")


def _dn_pdf_text(pages: int) -> str:
    return "\n".join(f"───── Trang {p}/{pages} ─────\n{_DN_PAGE.format(p=p)}" for p in range(1, pages + 1))


def _dn_plan(monkeypatch, pkg, files, texts, chat, options):
    """Gọi qua bộ điều phối attach/planner.py; OCR + LLM giả."""
    import asyncio
    import importlib

    from app.services import ocr as ocr_service
    from app.services.llm import client as llm_client

    async def fake_ocr(batch, **_kwargs):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in batch]

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", chat)
    dispatcher = importlib.import_module(f"app.pipelines.{pkg}.attach.planner")
    out = asyncio.run(dispatcher.plan(files, options))
    AttachmentPlanResp.model_validate({"attachments": out["attachments"]})
    return out


@pytest.mark.parametrize(("pkg", "layout", "_whole", "_fallback"), _DN_CASES, ids=_DN_IDS)
def test_dat_dai_da_nang_bat_tach_cat_dung_dong_khong_sot_trang(monkeypatch, pkg, layout, _whole, _fallback):
    import json

    async def fake_chat(*_args, **_kwargs):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": a, "pageTo": b, "type": t, "documentName": ""} for a, b, t, _ in layout
        ]})

    out = _dn_plan(monkeypatch, pkg, [_dn_pdf("ho-so-gop.pdf", 4)], {"ho-so-gop.pdf": _dn_pdf_text(4)}, fake_chat,
                   {"splitDocuments": True})
    page_rows: list[tuple[int, int]] = []
    for item in out["attachments"]:
        assert item["fileIndex"] == 0 and item["target"] == "attp-row"
        segments = item.get("sourceSegments") or [{"fileIndex": 0, "pageIndexes": None}]
        assert len(segments) == 1
        pages = segments[0]["pageIndexes"]
        page_rows += [(p, item["componentIndex"]) for p in (range(4) if pages is None else pages)]
    # Mỗi trang đúng một lần (không sót, không lặp), đúng dòng của giấy chứa nó.
    assert sorted(page_rows) == [(p - 1, row) for a, b, _, row in layout for p in range(a, b + 1)]
    assert all(item.get("sourceSegments") for item in out["attachments"])
    assert not any("attachment_agent" in e for e in out["errors"])


@pytest.mark.parametrize("options", [None, {}, {"splitDocuments": False}], ids=["none", "rong", "false"])
@pytest.mark.parametrize(("pkg", "_layout", "whole", "fallback"), _DN_CASES, ids=_DN_IDS)
def test_dat_dai_da_nang_tat_tach_moi_tep_mot_muc_nguyen_tep(monkeypatch, pkg, _layout, whole, fallback, options):
    import json

    names = ["ho-so-gop.pdf", "giay-thu-hai.jpg", "giay-thu-ba.jpg", "anh-mo.jpg"]
    files = [_dn_pdf(names[0], 2), _dn_image(names[1]), _dn_image(names[2]), _dn_image(names[3])]
    texts = {names[0]: _dn_pdf_text(2), names[1]: _DN_PAGE.format(p=1), names[2]: _DN_PAGE.format(p=1)}  # tệp 4: OCR rỗng
    calls: list[str] = []

    async def fake_chat(messages, **_kwargs):
        calls.append(messages[-1]["content"])
        return json.dumps({"documents": [{"index": i, "docTypes": types} for i, (types, _) in enumerate(whole)]})

    out = _dn_plan(monkeypatch, pkg, files, texts, fake_chat, options)
    items = out["attachments"]
    assert len(calls) == 1  # MỘT lượt LLM cho cả hồ sơ
    assert sorted(item["fileIndex"] for item in items) == [0, 1, 2, 3]
    assert not any(item.get("sourceSegments") or item.get("sourceFileIndexes") for item in items)
    rows = {item["fileIndex"]: item["componentIndex"] for item in items}
    assert rows == {0: whole[0][1], 1: whole[1][1], 2: whole[2][1], 3: fallback}
    by_index = {item["fileIndex"]: item for item in items}
    assert "anh-mo" in by_index[3]["documentName"] and by_index[3]["detectedType"] == "other"
    assert "ho-so-gop" in by_index[0]["documentName"]  # tệp gộp giữ tên gốc
    assert any("gộp nhiều giấy tờ" in e and "ho-so-gop.pdf" in e and f"dòng {whole[0][1]}" in e for e in out["errors"])
    assert out["extracted"]["attachmentMode"] == "preserve_files"


@pytest.mark.parametrize(("pkg", "_layout", "_whole", "fallback"), _DN_CASES, ids=_DN_IDS)
def test_dat_dai_da_nang_tach_loi_quay_ve_dinh_nguyen_tep(monkeypatch, pkg, _layout, _whole, fallback):
    async def broken_chat(*_args, **_kwargs):
        raise RuntimeError("LLM hết hạn mức")

    files = [_dn_pdf("ho-so-gop.pdf", 4), _dn_image("giay-le.jpg")]
    texts = {"ho-so-gop.pdf": _dn_pdf_text(4), "giay-le.jpg": _DN_PAGE.format(p=1)}
    out = _dn_plan(monkeypatch, pkg, files, texts, broken_chat, {"splitDocuments": True})
    items = out["attachments"]
    assert sorted(item["fileIndex"] for item in items) == [0, 1]
    assert not any(item.get("sourceSegments") for item in items)
    assert {item["componentIndex"] for item in items} == {fallback}
    assert out["errors"][0].startswith("attachment_agent (tách): LLM hết hạn mức")
    assert out["extracted"]["attachmentMode"] == "preserve_files"
