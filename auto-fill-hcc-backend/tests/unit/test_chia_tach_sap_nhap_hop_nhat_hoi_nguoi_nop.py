"""Chia, tách, sáp nhập, hợp nhất hội (cấp tỉnh) — hai chế độ người nộp. Chủ hồ sơ = Chủ tịch dự kiến. Dữ liệu giả.

Đính kèm: hai chế độ theo cài đặt "Tách giấy tờ" (bật → cắt trang; tắt / client cũ / chia giấy lỗi → đính nguyên tệp).
"""

import asyncio
import base64
import json

import fitz
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach import planner as attach_planner
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process import mapper
from app.process.schemas import FileItem

_OWNER = {
    "ChuHoSo_HoTen": "NGUYỄN VĂN A",
    "ChuHoSo_SoDinhDanh": "001071000001",
    "ChuHoSo_NgaySinh": "01/12/1971",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_NgayCap": "28/09/2021",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_DiaChi": {"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Phường Giả", "diaChi": "Số 1"},
    "NguoiLienHe_HoTen": "Nguyễn Văn A",
    "NguoiLienHe_DienThoai": "0900000001",
    "LoaiThuTuc": "sáp nhập",
    "HoiThamGia": ["Hội X", "Hội Y"],
    "HoiMoi": ["Hội X"],
}
_TK_KHAC = {"formContext": {"applicantFullname": "Trần Văn B", "applicantIdentityNumber": "001099000002"}}


def _run(options, extra=None):
    values = dict(_OWNER, **(extra or {}))
    out, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return out, {(f["name"], f.get("occurrence")): f for f in out}, warnings


def test_to_khai_nguoi_nop_la_chu_ho_so_bo_khoa_3_o_va_ghim_phan_i():
    out, d, _ = _run({"submitterMode": "owner_as_submitter", **_TK_KHAC})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    for name, value in (("data[fullname]", "NGUYỄN VĂN A"), ("data[identityNumber]", "001071000001"),
                        ("data[birthday]", "01/12/1971")):
        assert d[(name, 0)]["value"] == value and d[(name, 0)]["enableInput"] is True
    assert d[("data[district]", None)]["value"] == "Phường Giả"
    assert d[("data[phoneNumber]", None)]["value"] == "0900000001"
    assert d[("data[ownerFullname]", None)]["value"] == "NGUYỄN VĂN A"


def test_tai_khoan_khong_co_moc_khong_tich_khong_dien_phan_i():
    out, d, warnings = _run({})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert not any(name in ("data[gender]", "data[district]", "data[phoneNumber]") for name, _ in d)
    assert not any(f.get("enableInput") for f in out)
    assert d[("data[ownerDistrict]", None)]["value"] == "Phường Giả"
    assert any("F5" in w for w in warnings)


def test_tai_khoan_la_chu_ho_so_thi_tich_khong_ghi_o_khoa():
    out, d, _ = _run({"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001071000001"}})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    assert ("data[fullname]", 0) not in d and ("data[identityNumber]", 0) not in d
    assert d[("data[gender]", None)]["value"] == "Nam"
    assert d[("data[phoneNumber]", None)]["value"] == "0900000001"


def test_tai_khoan_khop_cccd_nguoi_khac_bo_tich_phan_i_la_nguoi_do():
    _, d, _ = _run(_TK_KHAC, {"NguoiNop_HoTen": "TRẦN VĂN B", "NguoiNop_SoDinhDanh": "001099000002",
                              "NguoiNop_GioiTinh": "Nam", "NguoiNop_NgayCap": "02/03/2022"})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert d[("data[identityDate]", None)]["value"] == "02/03/2022"
    # SĐT trên Đơn là của người liên hệ (chủ hồ sơ), không gán cho người nộp khác.
    assert ("data[phoneNumber]", None) not in d


def test_tai_khoan_khong_khop_ai_thi_de_trong_va_canh_bao():
    _, d, warnings = _run(_TK_KHAC)
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert ("data[gender]", None) not in d
    assert any("không có giấy tờ của tài khoản" in w for w in warnings)


# ---------------- Đính kèm: hai chế độ theo cài đặt "Tách giấy tờ" ----------------
# Tệp 0 gộp Đơn (tr.1) + Biên bản họp (tr.2) + Nghị quyết (tr.3–4); tệp 1 là Đề án; tệp 2 là ảnh CCCD.
_HOI_GOP = [
    ("don_de_nghi", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ chia, tách hội\nKính gửi: Sở Nội vụ"),
    ("bien_ban_hop", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBIÊN BẢN HỌP Ban chấp hành\nHôm nay vào lúc 8 giờ"),
    ("nghi_quyet", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nNGHỊ QUYẾT Ban chấp hành\nQUYẾT NGHỊ: Điều 1"),
    ("nghi_quyet", "Điều 2. Nghị quyết có hiệu lực kể từ ngày ký. Nơi nhận: như trên"),
]
_HOI_TEXTS = {
    "ho-so-gop.pdf": "\n".join(f"───── Trang {p}/4 ─────\n{t}" for p, (_, t) in enumerate(_HOI_GOP, start=1)),
    "de-an.pdf": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐỀ ÁN chia, tách hội\nPHẦN I. Cơ sở và lý do",
    "cccd.png": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001000000001\nHọ và tên: NGUYỄN VĂN A",
}
_HOI_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_de_nghi"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "bien_ban_hop"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 4, "type": "nghi_quyet"},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "de_an"},
    {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "cccd"},
]
_HOI_TYPES = [
    {"index": 0, "docTypes": ["don_de_nghi", "bien_ban_hop", "nghi_quyet"]},
    {"index": 1, "docTypes": ["de_an"]},
    {"index": 2, "docTypes": ["cccd"]},
]


def _pdf(name: str, pages: int) -> FileItem:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name=name, type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


def _hoi_files() -> list[FileItem]:
    return [_pdf("ho-so-gop.pdf", 4), _pdf("de-an.pdf", 1),
            FileItem(name="cccd.png", type="image/png", role="doc", dataUrl="data:image/png;base64,AAAA")]


def _plan_hoi(monkeypatch, options, *, split_fails=False, classify_fails=False):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": _HOI_TEXTS[f["name"]]} for f in files]

    async def fake_chat(messages, **_kwargs):
        if "docTypes" in messages[0]["content"]:  # prompt chế độ không tách
            if classify_fails:
                raise RuntimeError("LLM hết giờ")
            return json.dumps({"documents": _HOI_TYPES})
        if split_fails:
            raise RuntimeError("LLM hết giờ")
        return json.dumps({"documents": _HOI_SEGMENTS})

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    out = asyncio.run(attach_planner.plan(_hoi_files(), options))
    AttachmentPlanResp.model_validate(out)
    return out


def test_dinh_kem_bat_tach_cat_pdf_gop_dung_dong_khong_sot_trang(monkeypatch):
    out = _plan_hoi(monkeypatch, {"splitDocuments": True})
    gop = [a for a in out["attachments"] if a["fileIndex"] == 0]
    assert [(a["componentIndex"], a["detectedType"], a["sourceSegments"][0]["pageIndexes"]) for a in gop] == [
        (2, "don_de_nghi", [0]), (4, "nghi_quyet", [2, 3]), (4, "bien_ban_hop", [1]),
    ]
    assert sorted(p for a in gop for s in a["sourceSegments"] for p in s["pageIndexes"]) == [0, 1, 2, 3]
    rest = {a["fileIndex"]: a for a in out["attachments"] if a["fileIndex"] != 0}
    assert {i: a["componentIndex"] for i, a in rest.items()} == {1: 3, 2: 2}
    assert not any(a.get("sourceSegments") for a in rest.values())


@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
def test_dinh_kem_tat_tach_moi_tep_nguyen_mot_lan_dung_dong_giay_chinh(monkeypatch, options):
    out = _plan_hoi(monkeypatch, options)
    attachments = out["attachments"]
    assert out["extracted"]["attachmentMode"] == "preserve_files"
    assert sorted(a["fileIndex"] for a in attachments) == [0, 1, 2]
    assert not any(a.get("sourceSegments") or a.get("sourceFileIndexes") for a in attachments)
    by_file = {a["fileIndex"]: a for a in attachments}
    assert {i: a["componentIndex"] for i, a in by_file.items()} == {0: 2, 1: 3, 2: 2}
    assert by_file[0]["includedTypes"] == ["don_de_nghi", "bien_ban_hop", "nghi_quyet"]
    assert by_file[0]["documentName"] == "ho-so-gop", "tệp gộp giữ tên gốc"
    assert by_file[1]["documentName"].startswith("Đề án chia"), "tệp một giấy mang tên giấy"
    assert all(a["target"] == "attp-row" and a["loaiBan"] == "Bản chính" for a in attachments)
    assert any("ho-so-gop.pdf" in w and "dòng 4" in w for w in out["errors"])
    assert any("đã đính chung dòng" in w and "cccd.png" in w for w in out["errors"])


@pytest.mark.parametrize("classify_fails", [False, True])
def test_dinh_kem_bat_tach_ma_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch, classify_fails):
    out = _plan_hoi(monkeypatch, {"splitDocuments": True}, split_fails=True, classify_fails=classify_fails)
    attachments = out["attachments"]
    assert out["errors"][0].startswith("attachment_agent (tách)")
    assert sorted(a["fileIndex"] for a in attachments) == [0, 1, 2]
    assert not any(a.get("sourceSegments") for a in attachments)
    rows = {a["fileIndex"]: a["componentIndex"] for a in attachments}
    if classify_fails:
        # Cả lượt phân loại cũng lỗi → mọi tệp về dòng Đơn đề nghị, giữ tên gốc.
        assert rows == {0: 2, 1: 2, 2: 2}
        assert [a["documentName"] for a in sorted(attachments, key=lambda a: a["fileIndex"])] == [
            "ho-so-gop", "de-an", "cccd"]
    else:
        assert rows == {0: 2, 1: 3, 2: 2}
