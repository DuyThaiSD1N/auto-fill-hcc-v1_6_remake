"""[Bộ Xây dựng] Gia hạn thời gian lưu hành cho phương tiện của Lào (1.002063) — mapper + tách trang không bỏ trang."""

import base64
import re
from pathlib import Path

import fitz
import pytest

from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.attach import planner
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
