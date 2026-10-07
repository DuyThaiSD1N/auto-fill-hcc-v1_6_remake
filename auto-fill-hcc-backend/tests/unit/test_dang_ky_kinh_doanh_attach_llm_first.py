"""Đính kèm đăng ký hộ kinh doanh: LLM quyết loại, marker OCR chỉ dự phòng khi LLM không trả gì. Dữ liệu giả."""

import asyncio

from app.pipelines.dang_ky_kinh_doanh.attach import planner
from app.process.schemas import FileItem
from app.services import ocr

_UY_QUYEN = (
    "GIẤY ỦY QUYỀN I. BÊN ỦY QUYỀN Họ tên: NGUYỄN THỊ A II. BÊN ĐƯỢC ỦY QUYỀN Họ tên: TRẦN THỊ B "
    "III. NỘI DUNG ỦY QUYỀN Ủy quyền nộp và nhận hồ sơ đề nghị đăng ký thành lập hộ kinh doanh."
)
_DE_NGHI = "GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH Kính gửi: Phòng Kinh tế Tôi là NGUYỄN THỊ A"


def _plan(monkeypatch, llm_result):
    texts = [_DE_NGHI, _UY_QUYEN]

    async def fake_ocr(files):
        return [{"name": f["name"], "text": t} for f, t in zip(files, texts)]

    async def fake_llm(_docs):
        return llm_result

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_llm)
    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="attachment")
             for n in ("kd.pdf", "uy-quyen.pdf")]
    return asyncio.run(planner.plan(files))["attachments"]


def test_giay_uy_quyen_llm_other_vao_loai_khac_khong_de_bang_marker(monkeypatch):
    items = _plan(monkeypatch, {
        0: {"type": "business_form", "documentName": "Giấy đề nghị đăng ký hộ kinh doanh"},
        1: {"type": "other", "documentName": "Giấy ủy quyền"},
    })
    assert [i["category"] for i in items] == ["BUSREGFRM", "OTHERS"]
    assert items[1]["documentName"] == "Giấy ủy quyền"


def test_llm_khong_tra_thi_marker_ocr_du_phong(monkeypatch):
    items = _plan(monkeypatch, {})
    assert items[0]["category"] == "BUSREGFRM"
