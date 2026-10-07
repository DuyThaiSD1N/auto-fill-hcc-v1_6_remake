"""Đính kèm nhóm thủ tục kinh doanh: LLM quyết loại, marker OCR chỉ dự phòng khi LLM không trả gì.

Giấy ủy quyền thường NHẮC tên thành phần chính (vd "nộp hồ sơ đề nghị đăng ký doanh nghiệp") nên marker
trúng nhầm; LLM đã trả authorization/other thì marker không được đè. Dữ liệu giả.
"""

import asyncio

import pytest

from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.attach import planner as cap_lai
from app.pipelines.cham_dut_hoat_dong_ho_kinh_doanh.attach import planner as cham_dut
from app.pipelines.dang_ky_thay_doi_kinh_doanh.attach import planner as thay_doi
from app.pipelines.tam_ngung_kinh_doanh.attach import planner as tam_ngung
from app.pipelines.thanh_lap_ctcp.attach import planner as ctcp
from app.pipelines.thanh_lap_ctythnn_2_nguoi.attach import planner as tnhh2
from app.process.schemas import FileItem
from app.services import ocr

_UQ = "GIẤY ỦY QUYỀN BÊN ỦY QUYỀN: NGUYỄN VĂN A BÊN ĐƯỢC ỦY QUYỀN: TRẦN VĂN B NỘI DUNG: ủy quyền nộp và nhận {}"

# (module, tên hàm LLM, văn bản thành phần chính, category chính, nội dung ủy quyền, loại LLM của ủy quyền,
#  category ủy quyền)
CASES = [
    (ctcp, "_classify_with_llm", "GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP CÔNG TY CỔ PHẦN", "ENTREGFRM",
     "hồ sơ đề nghị đăng ký doanh nghiệp", "authorization", "AUTHORIZATION"),
    (tnhh2, "_classify_with_llm", "GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP CÔNG TY TNHH HAI THÀNH VIÊN", "ENTREGFRM",
     "hồ sơ đề nghị đăng ký doanh nghiệp", "authorization", "AUTHORIZATION"),
    (thay_doi, "_classify", "THÔNG BÁO THAY ĐỔI NỘI DUNG ĐĂNG KÝ HỘ KINH DOANH", "BUSCHANGEFRM",
     "thông báo thay đổi nội dung đăng ký hộ kinh doanh", "other", "OTHERS"),
    (cham_dut, "_classify", "THÔNG BÁO VỀ VIỆC CHẤM DỨT HOẠT ĐỘNG HỘ KINH DOANH", "DISSOLUTION_NOTICE",
     "thông báo về việc chấm dứt hoạt động hộ kinh doanh", "other", "OTHERS"),
    (tam_ngung, "_classify", "GIẤY ĐỀ NGHỊ ĐĂNG KÝ TẠM NGỪNG KINH DOANH", "SUSPENSION_NOTICE",
     "giấy đề nghị đăng ký tạm ngừng kinh doanh", "other", "OTHERS"),
    (cap_lai, "_classify", "GIẤY ĐỀ NGHỊ CẤP LẠI GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH", "BUSREISSUEFRM",
     "giấy đề nghị cấp lại giấy chứng nhận đăng ký hộ kinh doanh", "other", "OTHERS"),
]
_IDS = ["ctcp", "tnhh2", "thay_doi", "cham_dut", "tam_ngung", "cap_lai"]


def _plan(monkeypatch, module, llm_fn, texts, llm_result):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": t} for f, t in zip(files, texts)]

    async def fake_llm(_docs):
        return llm_result

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(module, llm_fn, fake_llm)
    files = [FileItem(name=f"f{i}.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AAA",
                      role="attachment") for i in range(len(texts))]
    return asyncio.run(module.plan(files))["attachments"]


@pytest.mark.parametrize("module,llm_fn,main_text,main_cat,uq_scope,uq_type,uq_cat", CASES, ids=_IDS)
def test_llm_tra_uy_quyen_thi_marker_khong_de(monkeypatch, module, llm_fn, main_text, main_cat, uq_scope,
                                              uq_type, uq_cat):
    items = _plan(monkeypatch, module, llm_fn, [_UQ.format(uq_scope)], {0: {"type": uq_type, "documentName": "Giấy ủy quyền"}})
    assert items[0]["category"] == uq_cat


@pytest.mark.parametrize("module,llm_fn,main_text,main_cat,uq_scope,uq_type,uq_cat", CASES, ids=_IDS)
def test_llm_khong_tra_thi_marker_ocr_du_phong(monkeypatch, module, llm_fn, main_text, main_cat, uq_scope,
                                               uq_type, uq_cat):
    items = _plan(monkeypatch, module, llm_fn, [main_text], {})
    assert items[0]["category"] == main_cat


def test_cap_lai_chu_mau_so_2_khong_con_la_marker(monkeypatch):
    items = _plan(monkeypatch, cap_lai, "_classify", ["Mẫu số 2 BẢN KÊ KHAI"], {})
    assert items[0]["category"] == "OTHERS"
