"""Đăng ký khai sinh liên thông, bật "tách giấy tờ": một tệp scan gộp cả bộ hồ sơ phải được cắt theo trang — giấy
chứng sinh vào STT1, tờ khai thay đổi thông tin cư trú vào STT2, giấy khác vào STT1 thành tệp rời. Tắt tách thì giữ
nguyên planner cũ."""

import base64

import fitz

from app.pipelines.khai_sinh_lien_thong.attach import planner as ks
from app.pipelines.khai_sinh_lien_thong.attach.dinh_kem_tach import planner as tach
from app.process.schemas import FileItem

PAGES = [
    "SỞ Y TẾ GIẤY CHỨNG SINH Mã số GCS Đã sinh con vào lúc giờ ngày Cân nặng\nTrang 1/1",  # chân trang in sẵn
    "GIẤY CHỨNG NHẬN KẾT HÔN Số",
    "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Họ và tên",
    "Đặc điểm nhận dạng Ngày cấp",
    "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Họ và tên",
    "Đặc điểm nhận dạng Ngày cấp",
    "Mẫu CT01 TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ Kính gửi",
    "Ý kiến của chủ hộ chữ ký",
]
LLM_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "birth_proof", "documentName": "Giấy chứng sinh"},
    {"fileIndex": 0, "pages": [2], "docType": "other", "documentName": "Giấy chứng nhận kết hôn"},
    {"fileIndex": 0, "pages": [3, 4], "docType": "other", "documentName": "Căn cước công dân"},
    {"fileIndex": 0, "pages": [5, 6], "docType": "other", "documentName": "Căn cước công dân"},
    {"fileIndex": 0, "pages": [7, 8], "docType": "residence_form", "documentName": "Tờ khai thay đổi thông tin cư trú"},
]


def _pdf(pages: int) -> str:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def _ocr_text(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{p}" for i, p in enumerate(pages, 1))


def _patch(monkeypatch, documents=None, error=None, pages=PAGES):
    calls = {"split": 0}

    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": _ocr_text(pages)} for f in files]

    async def fake_segment(pages_by_file):
        calls["split"] += 1
        calls["pages"] = {i: len(p) for i, p in pages_by_file.items()}
        if error:
            raise error
        return documents if documents is not None else LLM_DOCS

    monkeypatch.setattr(tach.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach, "_segment_all", fake_segment)
    return calls


def _scan(pages: int = len(PAGES)) -> list[FileItem]:
    return [FileItem(name="ho so scan.pdf", type="application/pdf", dataUrl=_pdf(pages), role="")]


async def test_tep_scan_gop_cat_trang_vao_dung_dong(monkeypatch):
    calls = _patch(monkeypatch)
    out = await ks.plan(_scan(), {"splitDocuments": True}, None)

    # Chân trang "Trang 1/1" của giấy chứng sinh không được coi là mốc trang của OCR.
    assert calls["pages"] == {0: 8}
    items = out["attachments"]
    assert [(i["slotIndex"], i["documentName"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        (0, "Giấy chứng sinh", [0]),
        (0, "Giấy chứng nhận kết hôn", [1]),
        (0, "Căn cước công dân", [2, 3]),
        (0, "Căn cước công dân 2", [4, 5]),
        (1, "Tờ khai thay đổi thông tin cư trú", [6, 7]),
    ]
    assert all(i["target"] == "fixed-slot" for i in items)
    assert items[0]["slotKey"] == "birth_proof" and items[0]["repeatUpload"] is True
    assert "fallbackSlotIndex" not in items[0]  # giấy chứng sinh không bao giờ dời dòng
    assert all(i["fallbackSlotIndex"] == 1 for i in items[1:4])
    assert items[4]["slotKey"] == "residence_form"
    assert out["errors"] == []


async def test_tat_tach_giu_planner_cu(monkeypatch):
    calls = _patch(monkeypatch)

    async def old_planner(files, options=None, session=None):
        return {"attachments": [], "errors": ["planner cũ"]}

    monkeypatch.setattr(ks, "plan_khai_sinh_attachments", old_planner)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}, None):
        assert (await ks.plan(_scan(), options, None))["errors"] == ["planner cũ"]
    assert calls["split"] == 0


async def test_song_lieu_chi_dinh_chung_sinh_va_to_khai_cu_tru(monkeypatch):
    _patch(monkeypatch)
    out = await ks.plan(_scan(), {"splitDocuments": True, ks.ONLY_BIRTH_PROOF_OPTION: True}, None)

    assert [(i["slotIndex"], i["documentName"]) for i in out["attachments"]] == [
        (0, "Giấy chứng sinh"), (1, "Tờ khai thay đổi thông tin cư trú")]
    assert any(e.startswith(ks.ONLY_BIRTH_PROOF_NOTE) for e in out["errors"])


async def test_nghia_lo_bo_to_khai_dang_ky_khai_sinh(monkeypatch):
    docs = [*LLM_DOCS[:1], {"fileIndex": 0, "pages": [2], "docType": "birth_declaration",
                            "documentName": "Tờ khai đăng ký khai sinh"}, *LLM_DOCS[2:]]
    _patch(monkeypatch, documents=docs)
    out = await ks.plan(_scan(), {"splitDocuments": True, ks.OMIT_BIRTH_DECLARATION_OPTION: True}, None)

    assert "Tờ khai đăng ký khai sinh" not in [i["documentName"] for i in out["attachments"]]
    assert any(e.startswith(ks.OMITTED_DECLARATION_NOTE) for e in out["errors"])


async def test_trang_llm_bo_sot_gop_vao_giay_lien_truoc(monkeypatch):
    docs = [d for d in LLM_DOCS if d["pages"] != [2]]  # LLM quên trang 2
    _patch(monkeypatch, documents=docs)
    out = await ks.plan(_scan(), {"splitDocuments": True}, None)

    birth = out["attachments"][0]
    assert birth["documentName"] == "Giấy chứng sinh" and birth["sourceSegments"][0]["pageIndexes"] == [0, 1]


async def test_llm_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, error=RuntimeError("llm down"))

    async def old_planner(files, options=None, session=None):
        return {"attachments": [{"fileIndex": 0}], "errors": []}

    monkeypatch.setattr(ks, "plan_khai_sinh_attachments", old_planner)
    out = await ks.plan(_scan(), {"splitDocuments": True}, None)

    assert out["attachments"] == [{"fileIndex": 0}]
    assert out["errors"][0].startswith("attachment_agent (tách)")


async def test_so_trang_ocr_lech_pdf_thi_khong_cat(monkeypatch):
    _patch(monkeypatch)

    async def old_planner(files, options=None, session=None):
        return {"attachments": [], "errors": []}

    monkeypatch.setattr(ks, "plan_khai_sinh_attachments", old_planner)
    out = await ks.plan(_scan(pages=7), {"splitDocuments": True}, None)

    # Cắt theo 8 trang OCR trên PDF 7 trang là đính nhầm trang → không tách, đính nguyên tệp.
    assert any("OCR đọc 8 trang, tệp có 7 trang" in e for e in out["errors"])
    assert all(not item.get("sourceSegments") for item in out["attachments"])


def test_registry_bat_tach_cho_lien_thong_khai_sinh():
    from app.channels.handfree.procedure_registry import get_procedure as handfree_procedure
    from app.procedures.registry import get_procedure

    assert get_procedure("khai-sinh-dang-ky").get("supportsSplitDocuments") is True
    assert handfree_procedure("khai-sinh-dang-ky").get("supportsSplitDocuments") is True


def test_moc_trang_chi_nhan_moc_cua_dich_vu_ocr_o_moi_planner_tach():
    """Chân trang "Trang 1/1" in sẵn trên giấy không được chia đôi trang ở BẤT KỲ planner tách nào."""
    import glob
    import importlib

    text = _ocr_text(["GIẤY CHỨNG SINH nội dung\nTrang 1/1\ncòn tiếp", "TỜ KHAI"])
    paths = glob.glob("app/pipelines/*/attach/dinh_kem_tach/planner.py")
    assert len(paths) >= 11
    for path in paths:
        module = importlib.import_module(path[:-3].replace("/", "."))
        if hasattr(module, "_pages"):
            assert len(module._pages(text)) == 2, path
