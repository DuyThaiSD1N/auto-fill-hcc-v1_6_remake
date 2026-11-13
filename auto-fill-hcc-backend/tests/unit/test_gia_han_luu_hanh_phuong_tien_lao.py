"""[Bộ Xây dựng] Gia hạn thời gian lưu hành cho phương tiện của Lào (1.002063) — mapper + tách trang không bỏ trang."""

import base64
import re
from pathlib import Path

import fitz
import pytest

from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.attach import planner as dieu_phoi
from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.attach.dinh_kem_tach import planner
from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.process import mapper
from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.process.schema import UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import public_list

_KEY = "gia-han-luu-hanh-phuong-tien-lao"
_ROOT = Path(__file__).resolve().parents[2].parent
_FACTS = {
    "NguoiNop_HoTen": "NGUYEN VAN A",
    "NguoiNop_ThuongTru": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Mẫu", "diaChi": "Tổ 1"},
    "NguoiNop_DienThoai": "0900000001",
    "DeNghi_KinhGui": "Sở Xây dựng thành phố Đà Nẵng",
    "DeNghi_LyDo": "Xe bị hỏng",
    "DeNghi_ThoiGianNhapCanh": "11/08/2026",
    "DeNghi_SoNgayGiaHan": "10 ngày",
    "DeNghi_TuNgay": "10/09/2026",
    "DeNghi_DenNgay": "20/09/2026",
    "DeNghi_BienSo": "ກທ 5889",
    "DeNghi_Tai": "Đà Nẵng",
}


def _run(values):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {})
    return {f["name"]: f for f in fields}, warnings


def test_registry_detect_theo_ten_va_host():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["detect"]["urlScope"] == ["dvc.moc.gov.vn"] and entry["hasAttachmentStep"] is True


def test_ca_nhan_va_cac_o_de_nghi_key_phang():
    ui, _ = _run(_FACTS)
    assert ui["data[chonDoiTuong]"]["value"] == "Cá nhân"
    assert ui["data[T_CoQuan]"]["value"] == "Sở Xây dựng TP Đà Nẵng"
    assert ui["data[tenDiaPhuong]"]["value"] == "Thành phố Đà Nẵng"
    assert ui["data[ThoiGianGiaHan]"]["value"] == "10"
    assert ui["data[BienSoXeGiaHan]"]["value"] == "ກທ 5889", "giữ nguyên chữ Lào"
    assert ui["data[kyTenDongDau]"]["value"] == "NGUYEN VAN A"
    assert "data[tenHoSo]" not in UI_COMP_BY_NAME, "ô Ghi chú để trống"
    assert all(k.count("[") == 1 for k in ui), "form này dùng key phẳng"


def test_khong_co_cccd_thi_xoa_trang_o_tai_khoan_do_san():
    ui, warnings = _run(_FACTS)
    assert ui["data[birthday]"].get("clear") and ui["data[identityNumber]"].get("clear")
    assert any("không có CCCD" in w for w in warnings)


def _pdf(pages: int) -> FileItem:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    return FileItem(name="hoso.pdf", type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}",
                    role="attachment")


@pytest.mark.asyncio
async def test_bao_gia_va_giay_phep_trong_mot_file_tach_dung_dong(monkeypatch):
    text = "\n".join(f"───── Trang {i}/6 ─────\nx" for i in range(1, 7))

    async def fake_ocr(files):
        return [{"name": f["name"], "text": text} for f in files]

    async def fake_classify(documents):
        return [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "giay_to_chung_minh", "documentName": "Báo giá sửa chữa xe"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 6, "type": "giay_phep_lien_van", "documentName": "Giấy phép liên vận"},
        ]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)
    res = await planner.plan([_pdf(6)], {}, None)
    items = {i["detectedType"]: i for i in res["attachments"]}
    assert items["giay_phep_lien_van"]["componentIndex"] == 2
    assert items["giay_phep_lien_van"]["sourceSegments"][0]["pageIndexes"] == [1, 2, 3, 4, 5]
    assert items["giay_to_chung_minh"]["componentIndex"] == 1, "giấy ngoài bảng đính chung dòng 1"
    assert items["giay_to_chung_minh"]["documentName"] == "Báo giá sửa chữa xe"


def _fe_fold(text: str) -> str:
    import unicodedata

    text = str(text or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s*[-‐-―]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def test_component_khop_dong_that_tren_snapshot():
    pages = [f.read_text(encoding="utf-8", errors="replace") for d in (_ROOT / "thongtin").glob("142*")
             for f in d.glob("*.html")]
    html = next((p for p in pages if "rdo_File" in p), None)
    if html is None:
        return
    rows = [_fe_fold(re.sub(r"(?s)<[^>]+>", " ", r))
            for r in re.findall(r'(?s)<tr[^>]*class="[^"]*table-row[^"]*"[^>]*>(.*?)</tr>', html)]
    assert len(rows) == 2, len(rows)
    for doc_type, row in planner._ROWS.items():
        assert _fe_fold(row["componentName"]) in rows[row["componentIndex"] - 1], doc_type


def test_day_so_dai_ma_tem_khong_dien_vao_bien_so():
    ui, warnings = _run({**_FACTS, "DeNghi_BienSo": "52049819840752795"})
    assert "data[BienSoXeGiaHan]" not in ui
    assert any("mã tem" in w for w in warnings)
    ui, _ = _run({**_FACTS, "DeNghi_BienSo": "NN-5889"})
    assert ui["data[BienSoXeGiaHan]"]["value"] == "NN-5889"


# ---------------- Hai chế độ đính kèm theo cài đặt "Tách giấy tờ" ----------------
def _named_pdf(name: str, pages: int) -> FileItem:
    return _pdf(pages).model_copy(update={"name": name})


_HAI_CHE_DO_TEXTS = {
    "hoso.pdf": "\n".join(f"───── Trang {i}/6 ─────\nx" for i in range(1, 7)),
    "de_nghi.pdf": "GIẤY ĐỀ NGHỊ GIA HẠN thời gian lưu hành của phương tiện tại Việt Nam",
}
_HAI_CHE_DO_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "giay_to_chung_minh", "documentName": "Báo giá sửa chữa xe"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 6, "type": "giay_phep_lien_van", "documentName": "Giấy phép liên vận"},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "giay_de_nghi", "documentName": ""},
]
_HAI_CHE_DO_TYPES = {0: ["giay_to_chung_minh", "giay_phep_lien_van"], 1: ["giay_de_nghi"]}


def _hai_che_do(monkeypatch, segments, doc_types):
    """OCR + LLM chia giấy (chế độ tách) + LLM liệt kê loại (chế độ không tách) giả; Exception = raise."""
    calls = {"tach": 0, "khong_tach": 0}

    async def fake_ocr(files):
        return [{"name": f["name"], "text": _HAI_CHE_DO_TEXTS[f["name"]]} for f in files]

    async def fake_tach(documents):
        calls["tach"] += 1
        if isinstance(segments, Exception):
            raise segments
        return segments

    async def fake_khong_tach(documents):
        calls["khong_tach"] += 1
        if isinstance(doc_types, Exception):
            raise doc_types
        return {d["index"]: doc_types[d["index"]] for d in documents}

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_tach)
    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_khong_tach)
    return calls, [_named_pdf("hoso.pdf", 6), _named_pdf("de_nghi.pdf", 1)]


def _assert_nguyen_tep(items):
    assert sorted(i["fileIndex"] for i in items) == [0, 1]
    assert not any(i.get("sourceSegments") or i.get("sourceFileIndexes") for i in items)
    assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True and i["loaiBan"] == "Bản chính"
               for i in items)


@pytest.mark.asyncio
async def test_bat_tach_pdf_gop_tach_dung_dong_khong_sot_trang(monkeypatch):
    calls, files = _hai_che_do(monkeypatch, _HAI_CHE_DO_SEGMENTS, AssertionError("không gọi"))
    res = await dieu_phoi.plan(files, {"splitDocuments": True}, None)
    assert calls == {"tach": 1, "khong_tach": 0}
    hoso = [i for i in res["attachments"] if i["fileIndex"] == 0]
    pages = [(i["componentIndex"], i["sourceSegments"][0]["pageIndexes"]) for i in hoso]
    assert pages == [(1, [0]), (2, [1, 2, 3, 4, 5])]
    de_nghi = next(i for i in res["attachments"] if i["fileIndex"] == 1)
    assert de_nghi["componentIndex"] == 1 and "sourceSegments" not in de_nghi


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
async def test_tat_tach_moi_tep_mot_muc_dung_dong_giay_chinh(monkeypatch, options):
    calls, files = _hai_che_do(monkeypatch, AssertionError("không gọi"), _HAI_CHE_DO_TYPES)
    res = await dieu_phoi.plan(files, options, None)
    assert calls == {"tach": 0, "khong_tach": 1}
    _assert_nguyen_tep(res["attachments"])
    by = {i["fileIndex"]: i for i in res["attachments"]}
    # Báo giá + giấy phép liên vận cùng tệp → giấy có dòng riêng (liên vận, dòng 2) thắng; giữ tên gốc.
    assert by[0]["componentIndex"] == 2 and by[0]["detectedType"] == "giay_phep_lien_van"
    assert by[0]["documentName"] == "hoso"
    assert by[1]["componentIndex"] == 1 and by[1]["documentName"] == planner._ROWS["giay_de_nghi"]["documentName"]
    assert not any("Chưa nhận ra" in e for e in res["errors"])


@pytest.mark.asyncio
async def test_bat_tach_ma_llm_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    calls, files = _hai_che_do(monkeypatch, RuntimeError("LLM sập"), _HAI_CHE_DO_TYPES)
    res = await dieu_phoi.plan(files, {"splitDocuments": True}, None)
    assert calls == {"tach": 1, "khong_tach": 1}
    _assert_nguyen_tep(res["attachments"])
    assert {i["fileIndex"]: i["componentIndex"] for i in res["attachments"]} == {0: 2, 1: 1}
    assert res["errors"][0] == "attachment_agent (tách): LLM sập"


@pytest.mark.asyncio
async def test_khong_tach_llm_loi_moi_tep_ve_dong_1_giu_ten_goc(monkeypatch):
    _, files = _hai_che_do(monkeypatch, AssertionError("không gọi"), RuntimeError("hết hạn"))
    res = await dieu_phoi.plan(files, {}, None)
    _assert_nguyen_tep(res["attachments"])
    assert [(i["componentIndex"], i["documentName"]) for i in res["attachments"]] == [(1, "hoso"), (1, "de_nghi")]
    assert "attachment_agent: hết hạn" in res["errors"]
    assert any("Chưa nhận ra loại giấy tờ" in e and "hoso.pdf" in e and "de_nghi.pdf" in e for e in res["errors"])
