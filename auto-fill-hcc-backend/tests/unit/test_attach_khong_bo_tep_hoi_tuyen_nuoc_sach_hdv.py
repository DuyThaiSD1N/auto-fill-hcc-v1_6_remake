"""Đính kèm không bỏ sót tệp: giấy lạ (other) và CCCD đều phải có item ở dòng cố định của planner.

Phủ các planner: 3 thủ tục hội cấp tỉnh (tách/gộp theo đoạn), 4 thủ tục thi/xét tuyển (một ô Phiếu), cấp nước
sạch, đổi tên nước sạch, cấp lại thẻ HDV du lịch Đà Nẵng.
"""

import asyncio
import base64
import json

import fitz
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.attach import planner as bao_cao_dai_hoi
from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.attach import planner as hdv_dieu_phoi
from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.attach.dinh_kem_tach import planner as hdv_da_nang
from app.pipelines.cap_nuoc_sach.attach import planner as cap_nuoc_sach
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_tach import planner as chia_tach_hoi
from app.pipelines.doi_ten_nuoc_sach.attach import planner as doi_ten_nuoc_sach
from app.pipelines.thi_tuyen_cong_chuc.attach import planner as thi_tuyen
from app.pipelines.thi_tuyen_cong_chuc_mot_cua_moha.attach import planner as thi_tuyen_moha
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach import planner as thong_bao_dieu_phoi
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach.dinh_kem_tach import planner as thong_bao_dai_hoi
from app.pipelines.xet_tuyen_cong_chuc.attach import planner as xet_tuyen_cc
from app.pipelines.xet_tuyen_vien_chuc.attach import planner as xet_tuyen_vc
from app.process.schemas import FileItem

_CCCD = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001000000001\nHọ và tên: NGUYEN VAN A"
_LA = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY XÁC NHẬN\nXác nhận ông NGUYEN VAN A"


def _files(n: int) -> list[dict]:
    return [{"name": f"f{i}.pdf", "type": "application/pdf"} for i in range(n)]


# ---------------- Hội cấp tỉnh (attp-row, tách/gộp theo đoạn) ----------------
def _hoi_inputs(main_type: str, main_text: str):
    texts = [main_text, _LA, _CCCD]
    types = [main_type, "other", "cccd"]
    segments = [
        {"fileIndex": i, "pageFrom": 1, "pageTo": 1, "type": t, "documentName": ""} for i, t in enumerate(types)
    ]
    file_meta = {i: {"pageCount": 1, "pageBoundariesAvailable": True} for i in range(3)}
    pages_by_file = {i: {1: text} for i, text in enumerate(texts)}
    return _files(3), segments, file_meta, pages_by_file


@pytest.mark.parametrize(
    ("mod", "main_type", "main_text", "main_row"),
    [
        (bao_cao_dai_hoi, "bao_cao_to_chuc_dai_hoi",
         "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBÁO CÁO tổ chức đại hội nhiệm kỳ\nKính gửi: Sở Nội vụ", 15),
        (chia_tach_hoi, "don_de_nghi", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ chia, tách hội", 2),
        (thong_bao_dai_hoi, "bao_cao_ket_qua",
         "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBÁO CÁO kết quả đại hội\nKính gửi: Sở Nội vụ", 1),
    ],
)
def test_hoi_cap_tinh_doan_la_va_cccd_thanh_item_rieng_o_dong_chinh(mod, main_type, main_text, main_row):
    out = mod.build_plan_items(*_hoi_inputs(main_type, main_text))
    attachments, classified, warnings = out[0], out[1], out[2]
    assert [(a["fileIndex"], a["componentIndex"]) for a in attachments if a["fileIndex"] == 0] == [(0, main_row)]
    shared = [a for a in attachments if a["fileIndex"] in (1, 2)]
    assert [(a["fileIndex"], a["componentIndex"], a["target"], a["detectedType"]) for a in shared] == [
        (1, main_row, "attp-row", "other"),
        (2, main_row, "attp-row", "cccd"),
    ]
    # Mỗi đoạn một item; đoạn phủ trọn tệp thì đính nguyên tệp (không cắt trang).
    assert not any(a.get("sourceSegments") or a.get("sourceFileIndexes") for a in attachments)
    assert [a["documentName"] for a in shared] == ["f1", "f2"]
    assert not any(c.get("target") == "skip" for c in classified)
    assert any("đã đính chung dòng" in w and "f1.pdf" in w and "f2.pdf" in w for w in warnings)


# ---------------- Thi/xét tuyển (fixed-slot, một ô Phiếu) ----------------
@pytest.mark.parametrize("mod", [thi_tuyen, thi_tuyen_moha, xet_tuyen_cc, xet_tuyen_vc])
def test_tuyen_giay_la_va_cccd_dinh_chung_o_phieu(mod):
    files = _files(3)
    ocr = [{"name": "f0.pdf", "text": "PHIẾU ĐĂNG KÝ DỰ TUYỂN"}, {"name": "f1.pdf", "text": _LA},
           {"name": "f2.pdf", "text": _CCCD}]
    items, warnings = mod.build_plan_items(files, ocr, {0: "phieu_dang_ky_du_tuyen"})
    assert [(i["fileIndex"], i["slotIndex"], i["target"]) for i in items] == [
        (0, 0, "fixed-slot"), (1, 0, "fixed-slot"), (2, 0, "fixed-slot")
    ]
    assert [i["documentName"] for i in items[1:]] == ["f1.pdf", "f2.pdf"]
    assert [i["detectedType"] for i in items[1:]] == ["other", "other"]
    assert len(warnings) == 1 and "f1.pdf, f2.pdf" in warnings[0]


# ---------------- Nước sạch (fixed-slot) ----------------
def test_cap_nuoc_sach_giay_la_vao_o_don_ho_gia_dinh_cccd_giu_dong_moi():
    files = _files(3)
    items, warnings, classified = cap_nuoc_sach.build_plan_items(
        files, [], {0: "household_application", 1: "other", 2: "identity_document"}
    )
    assert [(i["fileIndex"], i["target"], i.get("slotIndex")) for i in items] == [
        (0, "fixed-slot", 0), (1, "fixed-slot", 0), (2, "new", None)
    ]
    assert items[1]["documentName"] == "f1.pdf" and items[1]["detectedType"] == "other"
    assert classified[1]["routedTo"] == "household_application"
    assert "f1.pdf" in warnings[0]


def test_cap_nuoc_sach_lo_to_chuc_thi_giay_la_vao_o_don_to_chuc():
    items, _, _ = cap_nuoc_sach.build_plan_items(_files(2), [], {0: "organization_application", 1: "other"})
    assert [i["slotIndex"] for i in items] == [1, 1]


def test_doi_ten_nuoc_sach_giay_la_vao_o_don_cccd_giu_dong_moi():
    items, warnings, _ = doi_ten_nuoc_sach.build_plan_items(
        _files(3), [], {0: "template_name_change_application", 1: "other", 2: "identity_document"}
    )
    assert [(i["fileIndex"], i["target"], i.get("slotIndex")) for i in items] == [
        (0, "fixed-slot", 4), (1, "fixed-slot", 4), (2, "new", None)
    ]
    assert "f1.pdf" in warnings[0]


def test_doi_ten_nuoc_sach_chua_co_don_thi_vao_o_don_co_xac_nhan():
    items, _, _ = doi_ten_nuoc_sach.build_plan_items(_files(1), [], {0: "other"})
    assert [(i["slotIndex"], i["documentName"]) for i in items] == [(1, "f0.pdf")]


# ---------------- Cấp lại thẻ HDV du lịch Đà Nẵng (fixed-slot) ----------------
def test_hdv_da_nang_giay_la_va_cccd_dinh_chung_dong_giay_to():
    items, warnings, classified = hdv_da_nang.build_plan_items(
        _files(3), {0: ("don_cap_lai", []), 1: ("other", []), 2: ("cccd", [])}
    )
    assert [(i["fileIndex"], i["slotIndex"], i["target"]) for i in items] == [
        (0, 1, "fixed-slot"), (1, 0, "fixed-slot"), (2, 0, "fixed-slot")
    ]
    assert [i["documentName"] for i in items[1:]] == ["f1.pdf", "f2.pdf"]
    assert items[2]["detectedType"] == "cccd"
    assert not any(c.get("target") == "skip" for c in classified)
    assert any("đã đính chung dòng" in w and "f1.pdf" in w and "f2.pdf" in w for w in warnings)


def test_hdv_da_nang_trang_cccd_trong_pdf_gop_thanh_item_rieng():
    items, _, _ = hdv_da_nang.build_plan_items(
        _files(1), {}, {0: ["don_cap_lai", "cccd", "chung_chi_nghiep_vu"]}
    )
    assert [(i["slotIndex"], i["detectedType"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        (1, "don_cap_lai", [0]), (0, "cccd", [1]), (0, "chung_chi_nghiep_vu", [2])
    ]


# ---------------- Hai chế độ theo cài đặt "Tách giấy tờ" (gọi qua bộ điều phối attach/planner.py) ----------------
def _pdf(name: str, pages: int) -> FileItem:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name=name, type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


def _paged(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {p}/{len(pages)} ─────\n{t}" for p, t in enumerate(pages, start=1))


def _run_plan(monkeypatch, mod, files, texts, options, fake_chat):
    async def fake_ocr(items):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in items]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    out = asyncio.run(mod.plan(files, options))
    AttachmentPlanResp.model_validate(out)
    return out


# Thông báo kết quả đại hội: tệp 0 gộp Tờ trình (tr.1) + Danh sách kèm theo tờ trình (tr.2) + Nghị quyết (tr.3–4).
_TB_TEXTS = {
    "bao-cao-gop.pdf": _paged([
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ TRÌNH V/v báo cáo kết quả Đại hội\nKính gửi: Sở Nội vụ",
        "DANH SÁCH Ban chấp hành (Kèm theo tờ trình số 01/TTr-HMX)\nSTT Họ và tên Chức vụ\n1 Nguyễn Văn A Chủ tịch",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nNGHỊ QUYẾT ĐẠI HỘI\nĐại hội QUYẾT NGHỊ",
        "Nghị quyết này đã được Đại hội biểu quyết thông qua. Nơi nhận: như trên",
    ]),
    "bien-ban.pdf": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBIÊN BẢN ĐẠI HỘI\nHôm nay vào lúc 8 giờ",
}
_TB_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "bao_cao_ket_qua"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "danh_sach"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 4, "type": "nghi_quyet_dai_hoi"},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "bien_ban"},
]
_TB_TYPES = [
    {"index": 0, "docTypes": ["bao_cao_ket_qua", "danh_sach", "nghi_quyet_dai_hoi"]},
    {"index": 1, "docTypes": ["bien_ban"]},
]


def _plan_thong_bao(monkeypatch, options, split_fails=False):
    async def fake_chat(messages, **_kwargs):
        if "docTypes" in messages[0]["content"]:  # prompt chế độ không tách
            return json.dumps({"documents": _TB_TYPES})
        if split_fails:
            raise RuntimeError("LLM hết giờ")
        return json.dumps({"documents": _TB_SEGMENTS})

    files = [_pdf("bao-cao-gop.pdf", 4), _pdf("bien-ban.pdf", 1)]
    return _run_plan(monkeypatch, thong_bao_dieu_phoi, files, _TB_TEXTS, options, fake_chat)


def test_thong_bao_dai_hoi_bat_tach_cat_pdf_gop_dung_dong_khong_sot_trang(monkeypatch):
    attachments = _plan_thong_bao(monkeypatch, {"splitDocuments": True})["attachments"]
    gop = [a for a in attachments if a["fileIndex"] == 0]
    assert [(a["componentIndex"], a["detectedType"], a["sourceSegments"][0]["pageIndexes"]) for a in gop] == [
        (1, "bao_cao_ket_qua", [0]), (1, "danh_sach", [1]), (5, "nghi_quyet_dai_hoi", [2, 3]),
    ]
    assert sorted(p for a in gop for s in a["sourceSegments"] for p in s["pageIndexes"]) == [0, 1, 2, 3]
    bien_ban = next(a for a in attachments if a["fileIndex"] == 1)
    assert bien_ban["componentIndex"] == 3 and not bien_ban.get("sourceSegments")


@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
def test_thong_bao_dai_hoi_tat_tach_moi_tep_nguyen_mot_lan(monkeypatch, options):
    out = _plan_thong_bao(monkeypatch, options)
    attachments = out["attachments"]
    assert [(a["fileIndex"], a["componentIndex"]) for a in attachments] == [(0, 1), (1, 3)]
    assert not any(a.get("sourceSegments") or a.get("sourceFileIndexes") for a in attachments)
    assert attachments[0]["includedTypes"] == ["bao_cao_ket_qua", "danh_sach", "nghi_quyet_dai_hoi"]
    assert attachments[0]["documentName"] == "bao-cao-gop", "tệp gộp giữ tên gốc"
    # Dòng điều kiện không có tệp → bỏ tick như chế độ tách.
    assert len(attachments[0]["untickRows"]) == 3
    gop = [w for w in out["errors"] if "bao-cao-gop.pdf" in w and "gộp nhiều giấy" in w]
    assert len(gop) == 1 and "dòng 5" in gop[0] and "dòng 3" not in gop[0]
    assert not any("Chưa có Nghị quyết đại hội" in w for w in out["errors"]), "giấy trong tệp gộp không báo thiếu"


def test_thong_bao_dai_hoi_bat_tach_ma_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    out = _plan_thong_bao(monkeypatch, {"splitDocuments": True}, split_fails=True)
    assert out["errors"][0].startswith("attachment_agent (tách)")
    assert [(a["fileIndex"], a["componentIndex"]) for a in out["attachments"]] == [(0, 1), (1, 3)]
    assert not any(a.get("sourceSegments") for a in out["attachments"])


# Cấp lại thẻ HDV Đà Nẵng: tệp 0 gộp Đơn Mẫu 05 (tr.1 + trang "Hướng dẫn ghi") + chứng chỉ nghiệp vụ (tr.3); tệp 1 là ảnh.
_HDV_TEXTS = {
    "ho-so-hdv.pdf": _paged([
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ CẤP LẠI THẺ HƯỚNG DẪN VIÊN DU LỊCH\nKính gửi: Sở Du lịch",
        "HƯỚNG DẪN GHI: mục 1 ghi đầy đủ họ tên bằng chữ in hoa có dấu theo giấy tờ tùy thân",
        "TRƯỜNG ĐẠI HỌC MẪU\nCHỨNG CHỈ NGHIỆP VỤ HƯỚNG DẪN DU LỊCH NỘI ĐỊA\nĐã đạt kỳ thi nghiệp vụ hướng dẫn du lịch",
    ]),
    "anh-3x4.png": "",
}


def _plan_hdv(monkeypatch, options, split_fails=False):
    async def fake_chat(messages, **_kwargs):
        if "<ho_so_nhieu_tep>" in messages[0]["content"]:  # prompt chế độ không tách
            return json.dumps({"documents": [
                {"index": 0, "docType": "don_cap_lai", "alsoTypes": ["chung_chi_nghiep_vu"]},
            ]})
        if split_fails:
            raise RuntimeError("LLM hết giờ")
        doc_type = "don_cap_lai" if "CẤP LẠI" in messages[1]["content"] else "chung_chi_nghiep_vu"
        return json.dumps({"documents": [{"index": 0, "docType": doc_type, "alsoTypes": []}]})

    files = [_pdf("ho-so-hdv.pdf", 3),
             FileItem(name="anh-3x4.png", type="image/png", role="doc", dataUrl="data:image/png;base64,AAAA")]
    return _run_plan(monkeypatch, hdv_dieu_phoi, files, _HDV_TEXTS, options, fake_chat)


def test_hdv_da_nang_bat_tach_cat_pdf_gop_dung_dong_khong_sot_trang(monkeypatch):
    attachments = _plan_hdv(monkeypatch, {"splitDocuments": True})["attachments"]
    gop = [a for a in attachments if a["fileIndex"] == 0]
    assert [(a["slotIndex"], a["detectedType"], a["sourceSegments"][0]["pageIndexes"]) for a in gop] == [
        (1, "don_cap_lai", [0, 1]), (0, "chung_chi_nghiep_vu", [2]),
    ]
    anh = next(a for a in attachments if a["fileIndex"] == 1)
    assert anh["slotIndex"] == 2 and not anh.get("sourceSegments")


@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
def test_hdv_da_nang_tat_tach_moi_tep_nguyen_mot_lan(monkeypatch, options):
    out = _plan_hdv(monkeypatch, options)
    attachments = out["attachments"]
    assert [(a["fileIndex"], a["slotIndex"], a["target"]) for a in attachments] == [
        (0, 1, "fixed-slot"), (1, 2, "fixed-slot"),
    ]
    assert not any(a.get("sourceSegments") for a in attachments)
    assert attachments[0]["loaiBan"] == "Bản chính" and attachments[0]["slotKey"] == "hdvcl_don_de_nghi"
    assert any("ho-so-hdv.pdf" in w and "không tách sang dòng 1" in w for w in out["errors"])


def test_hdv_da_nang_bat_tach_ma_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    out = _plan_hdv(monkeypatch, {"splitDocuments": True}, split_fails=True)
    assert out["errors"][0].startswith("attachment_agent (tách)")
    assert [(a["fileIndex"], a["slotIndex"]) for a in out["attachments"]] == [(0, 1), (1, 2)]
    assert not any(a.get("sourceSegments") for a in out["attachments"])
