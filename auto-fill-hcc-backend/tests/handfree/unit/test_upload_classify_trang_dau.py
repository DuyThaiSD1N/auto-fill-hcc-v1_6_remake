"""Phân loại lúc tải lên: OCR đọc hết tệp (vào cache cho bước điền), LLM chỉ xem 3 trang đầu."""
import pytest

from app.pipelines._shared.documents import first_ocr_pages
from app.upload_session import llm_classifier


def _ocr(pages: int, *, lead_mark: bool = True) -> str:
    parts = [f"───── Trang {i}/{pages} ─────\nnoi dung trang {i}" for i in range(1, pages + 1)]
    if not lead_mark:
        parts[0] = "noi dung trang 1"
    return "\n".join(parts)


def test_cat_dung_ba_trang_dau():
    cut = first_ocr_pages(_ocr(10), 3)
    assert "trang 3" in cut and "trang 4" not in cut


def test_trang_dau_khong_co_vach_van_cat_dung():
    cut = first_ocr_pages(_ocr(10, lead_mark=False), 3)
    assert "trang 1" in cut and "trang 3" in cut and "trang 4" not in cut


def test_it_trang_hon_hoac_khong_co_vach_thi_giu_nguyen():
    assert first_ocr_pages(_ocr(2), 3) == _ocr(2)
    assert first_ocr_pages("anh mot trang", 3) == "anh mot trang"


@pytest.mark.asyncio
async def test_llm_phan_loai_chi_nhan_ba_trang_dau(monkeypatch):
    seen: list[str] = []

    async def fake_chat(messages, **_kw):
        seen.append(messages[-1]["content"])
        return '{"doc_key": "ban_ve"}'

    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)
    spec = llm_classifier.ClassificationSpec(
        system_prompt="x", allowed_keys=frozenset({"ban_ve"}), build_user_prompt=lambda _n, text: text)
    key = await llm_classifier._classify_one({"name": "ban-ve.pdf"}, {"text": _ocr(24)}, spec)
    assert key == "ban_ve"
    assert "trang 3" in seen[0] and "trang 4" not in seen[0]
