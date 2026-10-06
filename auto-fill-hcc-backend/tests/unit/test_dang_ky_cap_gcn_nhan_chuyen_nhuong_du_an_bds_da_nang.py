"""[Đà Nẵng] Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án BĐS — mapper 2 vai + tách trang không bỏ trang."""

import re
from pathlib import Path

import pytest

from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bds_da_nang.attach import planner
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bds_da_nang.process import mapper
from app.process.schemas import FileItem
from app.procedures.registry import public_list

# Entry registry đã đổi key theo ke_khai_links.json và trỏ sang pipeline dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.
_KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san"
_ROOT = Path(__file__).resolve().parents[2].parent
_OWNER = {
    "ChuHoSo_LoaiChuThe": "Cá nhân",
    "ChuHoSo_HoTen": "NGUYEN VAN A",
    "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Xã Mẫu", "diaChi": "Thôn 1"},
    "NguoiNop_HoTen": "NGUYEN VAN A",
    "NguoiNop_SoDinhDanh": "001000000001",
    "NguoiNop_NgaySinh": "01/02/1984",
}


def _run(values):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {})
    return {f["name"]: f["value"] for f in fields}, warnings


def test_registry_detect_khoa_host_da_nang_khong_de_ban_lao_cai():
    entries = {p["key"]: p for p in public_list()}
    assert entries[_KEY]["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    lao_cai = entries["dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai"]
    assert "dichvucong.danang.gov.vn" not in lao_cai["detect"].get("urlScope", [])


def test_tu_nop_tich_va_noi_dung_yeu_cau_lay_tu_don():
    ui, _ = _run({**_OWNER, "NoiDungBienDong": "Thay đổi chủ sử dụng do nhận chuyển nhượng"})
    assert ui["data[noidungyeucaugiaiquyet]"] == "Thay đổi chủ sử dụng do nhận chuyển nhượng"
    ui, _ = _run(_OWNER)
    assert ui["data[ownerFullname]"] == "NGUYEN VAN A" and ui["data[isOwnerDossier]"] is True
    assert ui["data[identityNumber]"] == "001000000001" and ui["data[birthday]"] == "01/02/1984"
    assert "data[noidungyeucaugiaiquyet]" not in ui, "Đơn không ghi thì giữ câu khung của cổng"
    assert ui["data[province]"] == "Thành phố Đà Nẵng"


def test_uy_quyen_bo_tich_dien_ca_hai_vai():
    values = {**_OWNER, "NguoiNop_HoTen": "TRAN THI B", "NguoiNop_SoDinhDanh": "001000000002"}
    ui, _ = _run(values)
    assert ui["data[isOwnerDossier]"] is False
    assert ui["data[ownerFullname]"] == "NGUYEN VAN A" and ui["data[fullname]"] == "TRAN THI B"


def _pdf_file(pages: int) -> FileItem:
    import base64

    import fitz

    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    return FileItem(name="hoso.pdf", type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}",
                    role="attachment")


def _patch(monkeypatch, pages: int, segments: list[dict] | Exception):
    text = "\n".join(f"───── Trang {i}/{pages} ─────\nnội dung {i}" for i in range(1, pages + 1))

    async def fake_ocr(files):
        return [{"name": f["name"], "text": text} for f in files]

    async def fake_classify(documents):
        if isinstance(segments, Exception):
            raise segments
        return segments

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)


@pytest.mark.asyncio
async def test_tach_trang_moi_doan_vao_dung_dong_va_khong_mat_trang(monkeypatch):
    _patch(monkeypatch, 6, [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_mau_18", "documentName": "Đơn đăng ký biến động"},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "hop_dong_chuyen_nhuong", "documentName": "Hợp đồng (bản sao)"},
        {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "chung_tu_tai_chinh", "documentName": "Tờ khai lệ phí trước bạ"},
        {"fileIndex": 0, "pageFrom": 5, "pageTo": 5, "type": "cccd", "documentName": ""},
    ])
    res = await planner.plan([_pdf_file(6)], {}, None)
    items = res["attachments"]
    pages = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2, 3, 4, 5], "trang 6 LLM bỏ sót vẫn được đính"
    by_type = {i["detectedType"]: i for i in items}
    assert by_type["don_mau_18"]["componentIndex"] == 2
    assert by_type["hop_dong_chuyen_nhuong"]["componentIndex"] == 3
    assert by_type["hop_dong_chuyen_nhuong"]["documentName"] == "Hợp đồng bản sao", "tên không ngoặc"
    assert by_type["chung_tu_tai_chinh"]["componentIndex"] == 7
    assert by_type["cccd"]["componentIndex"] == 2 and by_type["cccd"]["documentName"] == "Căn cước công dân"
    assert by_type["other"]["componentIndex"] == 2
    assert any("Chưa nhận ra loại giấy tờ" in e for e in res["errors"])


@pytest.mark.asyncio
async def test_llm_loi_van_dinh_ca_file_vao_dong_don(monkeypatch):
    _patch(monkeypatch, 3, RuntimeError("LLM down"))
    res = await planner.plan([_pdf_file(3)], {}, None)
    assert len(res["attachments"]) == 1 and res["attachments"][0]["componentIndex"] == 2


def test_nhan_la_cua_llm_khong_do_chuoi_con():
    assert planner._normalize_type("hop_dong") == "other"
    assert planner._normalize_type("don_mau_18") == "don_mau_18"


def _fe_fold(text: str) -> str:
    import unicodedata

    text = str(text or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s*[-‐-―]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def test_component_index_tro_dung_dong_chua_component_tren_snapshot():
    pages = [f.read_text(encoding="utf-8", errors="replace") for d in (_ROOT / "thongtin").glob("138_*")
             for f in d.glob("*.html")]
    html = next((p for p in pages if "rdo_File" in p), None)
    if html is None:
        return
    rows = [_fe_fold(re.sub(r"(?s)<[^>]+>", " ", r))
            for r in re.findall(r'(?s)<tr[^>]*mat-column-code[^>]*>(.*?)</tr>', html)]
    rows = rows or [_fe_fold(re.sub(r"(?s)<[^>]+>", " ", r))
                    for r in re.findall(r'(?s)<tr[^>]*class="[^"]*mat-row[^"]*"[^>]*>(.*?)</tr>', html)]
    assert len(rows) == 11, len(rows)
    for doc_type, row in planner._ROWS.items():
        assert _fe_fold(row["componentName"]) in rows[row["componentIndex"] - 1], doc_type
