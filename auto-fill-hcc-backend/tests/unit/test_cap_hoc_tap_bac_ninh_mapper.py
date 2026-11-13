"""Unit test mapper hỗ trợ chi phí học tập Bắc Ninh: HocSinh_* → doiTuongKhac* (khối được ủy quyền)."""

import asyncio
import json

from app.pipelines.cap_hoc_tap_bac_ninh.attach import planner as attach
from app.pipelines.cap_hoc_tap_bac_ninh.process import mapper
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client as llm_client


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict):
    fields, warnings = mapper.enrich(_flds(vals), {"purpose": "authorized_person"})
    return {f["name"]: f for f in fields}, warnings


_HSSV = {
    "HocSinh_HoTen": "NGUYỄN VĂN HIỆP",
    "HocSinh_GioiTinh": "Nam",
    "HocSinh_SoDinhDanh": "024209011449",
    "HocSinh_NgayCap": "06/12/2023",
    "HocSinh_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "HocSinh_NgaySinh": "30/10/2009",
    "HocSinh_SoDienThoai": "0358487622",
    "HocSinh_ThuongTru": {"tinh": "Bắc Ninh", "xa": "Phường Bắc Giang", "diaChi": "Số nhà 10, ngõ 77, Tổ dân phố Hà Vị"},
}


def test_map_day_du_khoi_uy_quyen_la_hoc_sinh():
    d, w = _run(_HSSV)
    assert not w
    assert d["doiTuongKhachoTen"]["value"] == "NGUYỄN VĂN HIỆP"
    assert d["doiTuongKhacsoDinhDanh"]["value"] == "024209011449"
    assert d["doiTuongKhacngaySinh"]["value"] == "30/10/2009"
    assert d["doiTuongKhacngayCap"]["value"] == "06/12/2023"
    assert d["doiTuongKhacsoDienThoai"]["value"] == "0358487622"
    # Giới tính là select native, option đầy đủ.
    assert d["doiTuongKhacgioiTinhId"]["value"] == "Giới tính Nam"
    assert d["doiTuongKhacgioiTinhId"]["comp"] == "bn-select"
    # Địa chỉ tách 3 cấp; tỉnh/xã là bn-select (select2), chi tiết là input.
    assert d["doiTuongKhactinhThanhId"]["value"] == "Bắc Ninh"
    assert d["doiTuongKhactinhThanhId"]["comp"] == "bn-select"
    assert d["doiTuongKhacphuongXaId"]["value"] == "Phường Bắc Giang"
    assert d["doiTuongKhacdiaChiChiTiet"]["value"].startswith("Số nhà 10")
    assert d["doiTuongKhacdiaChiChiTiet"]["comp"] == "bn-input"


def test_gioi_tinh_nu_map_dung_option():
    d, _ = _run({**_HSSV, "HocSinh_GioiTinh": "Nữ"})
    assert d["doiTuongKhacgioiTinhId"]["value"] == "Giới tính Nữ"


def test_thieu_ho_ten_hoac_cccd_tra_canh_bao_khong_crash():
    d, w = _run({"HocSinh_HoTen": "NGUYỄN VĂN HIỆP"})
    assert "doiTuongKhachoTen" in d
    assert w and "định danh" in w[0].lower()

    d2, w2 = _run({"HocSinh_SoDinhDanh": "024209011449"})
    assert w2 and ("họ tên" in w2[0].lower() or "sinh viên" in w2[0].lower())


def test_email_trong_khong_phat():
    d, _ = _run({**_HSSV, "HocSinh_Email": ""})
    assert "doiTuongKhacemail" not in d


# ── Đính kèm: hai chế độ theo cài đặt "Tách giấy tờ" (gọi qua bộ điều phối attach/planner.py) ──

_DON = "ĐƠN ĐỀ NGHỊ HỖ TRỢ CHI PHÍ HỌC TẬP Kính gửi: UBND xã. Họ và tên học sinh: TRAN VAN B"
_XAC_NHAN = "GIẤY XÁC NHẬN CỦA CƠ SỞ ĐÀO TẠO (Mẫu số 02) Trường THPT Thử Nghiệm xác nhận"
_BANG = "BẰNG TỐT NGHIỆP TRUNG HỌC CƠ SỞ cấp cho: TRAN VAN B"
_CCCD_HS = "CĂN CƯỚC CÔNG DÂN số 027000000002 Họ và tên TRAN VAN B"
_UY_QUYEN = "ĐƠN XIN XÁC NHẬN ỦY QUYỀN NỘP HỒ SƠ TRỰC TUYẾN"
_LOI_CHUNG = "LỜI CHỨNG CHỨNG THỰC CHỮ KÝ"


def _gop(*pages):
    return "\n".join(f"───── Trang {i + 1}/{len(pages)} ─────\n{t}" for i, t in enumerate(pages))


def _attach_patch(monkeypatch, texts, pages=None, doc_types=None, llm_raises=False):
    """OCR theo tên tệp; LLM trả `pages` cho lượt phân loại trang (tách), `doc_types` cho lượt không tách."""
    calls = []

    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, **_):
        mode = "tach" if "TỪNG TRANG" in messages[0]["content"] else "khong_tach"
        calls.append(mode)
        if llm_raises:
            raise RuntimeError("llm hỏng")
        if mode == "tach":
            return json.dumps({"pages": pages or []})
        return json.dumps({"documents": [{"index": i, "docTypes": t} for i, t in (doc_types or {}).items()]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)
    return calls


def _pdfs(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="", role="") for n in names]


def test_dinh_kem_bat_tach_pdf_gop_tach_dung_ma_kq_khong_sot_trang(monkeypatch):
    calls = _attach_patch(monkeypatch, {"hoso.pdf": _gop(_DON, "Trang 2 của đơn", _XAC_NHAN, _BANG, _CCCD_HS)}, pages=[
        {"fileIndex": 0, "pageNumber": 1, "docType": "don_de_nghi"},
        {"fileIndex": 0, "pageNumber": 2, "docType": "don_de_nghi"},
        {"fileIndex": 0, "pageNumber": 3, "docType": "xac_nhan_dao_tao"},
        {"fileIndex": 0, "pageNumber": 4, "docType": "bang_tot_nghiep"},
        # trang 5 (CCCD) LLM bỏ sót → rule keyword nhận CCCD → ô File đính kèm khác.
    ])
    res = asyncio.run(attach.plan(_pdfs("hoso.pdf"), {"splitDocuments": True}))
    got = [(i["target"], i["componentName"], i["sourceSegments"][0]["pageIndexes"]) for i in res["attachments"]]
    assert got == [("existing", "KQ001000", [0, 1]), ("existing", "KQ001001", [2]),
                   ("existing", "KQ001002", [3]), ("supplementary", "", [4])]
    pages = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2, 3, 4]
    assert calls == ["tach"]


def test_dinh_kem_tat_tach_moi_tep_mot_muc_dung_ma_kq_giay_chinh(monkeypatch):
    texts = {"don.pdf": _DON, "gop.pdf": _gop(_XAC_NHAN, _BANG), "uq.pdf": _gop(_UY_QUYEN, _LOI_CHUNG),
             "la.pdf": "Noi dung khong ro loai giay"}
    doc_types = {0: ["don_de_nghi"], 1: ["xac_nhan_dao_tao", "bang_tot_nghiep"], 2: ["don_uy_quyen", "loi_chung"]}
    for options in ({}, None, {"splitDocuments": False}, {"splitDocuments": "true"}):
        calls = _attach_patch(monkeypatch, texts, doc_types=doc_types)  # la.pdf LLM bỏ sót → rule → khac
        res = asyncio.run(attach.plan(_pdfs("don.pdf", "gop.pdf", "uq.pdf", "la.pdf"), options))
        items = res["attachments"]
        assert [i["fileIndex"] for i in items] == [0, 1, 2, 3]
        assert all("sourceSegments" not in i and i["slotKey"] == "banChinh" and i["needsAddComponent"] is False
                   for i in items)
        assert [(i["target"], i["componentName"], i["detectedType"]) for i in items] == [
            ("existing", "KQ001000", "don_de_nghi"), ("existing", "KQ001001", "xac_nhan_dao_tao"),
            ("supplementary", "", "don_uy_quyen"), ("supplementary", "", "khac")]
        assert items[0]["documentName"] == "Đơn đề nghị hỗ trợ chi phí học tập (Mẫu 01)"
        assert items[1]["documentName"] == "gop.pdf" and items[3]["documentName"] == "la.pdf"
        assert any("gop.pdf" in e and "KQ001002" in e for e in res["errors"])
        assert calls == ["khong_tach"]


def test_dinh_kem_tach_loi_quay_ve_dinh_nguyen_tep(monkeypatch):
    # LLM hỏng cả hai lượt → chế độ không tách dùng rule keyword theo trang, vẫn đính nguyên tệp.
    calls = _attach_patch(monkeypatch, {"hoso.pdf": _gop(_BANG, _DON, _CCCD_HS)}, llm_raises=True)
    res = asyncio.run(attach.plan(_pdfs("hoso.pdf"), {"splitDocuments": True}))
    assert [(i["fileName"], i["componentName"], i["detectedType"]) for i in res["attachments"]] == [
        ("hoso.pdf", "KQ001000", "don_de_nghi")]
    assert "sourceSegments" not in res["attachments"][0]
    assert any("(tách)" in e for e in res["errors"])
    assert calls == ["tach", "khong_tach"]
