"""Fixture chung: test không được ăn theo cờ thí nghiệm trong .env local.

OCR_BY_TIENGNOI=true trong .env từng làm 9 test compact "vỡ oan" (mock nhắm endpoint
raw/gemini nhưng runtime rẽ sang tiengnoi) — ghim cờ về False cho MỌI test.
"""
import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _pin_ocr_engine(monkeypatch):
    monkeypatch.setattr(settings, "ocr_by_tiengnoi", False)
