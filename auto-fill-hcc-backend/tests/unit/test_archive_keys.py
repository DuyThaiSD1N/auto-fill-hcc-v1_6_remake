import pytest

from app.archive import keys
from app.archive.config import archive_settings


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setattr(archive_settings, "archive_hmac_key", "khoa-thu")


def test_chuan_hoa_giong_mongo():
    assert keys.mongo_normalized_name("  CCCD   Mặt  Trước.JPG ") == "cccd mặt trước.jpg"
    assert keys.mongo_normalized_name("ĐƠN.pdf") == "ĐƠn.pdf"
    assert keys.mongo_normalized_name("x y.pdf") == "x y.pdf"
    assert keys.mongo_normalized_name(None) == ""


def test_khoa_on_dinh_va_bo_duoi():
    a = keys.attachment_keys("Giấy khai sinh.PDF", "")
    b = keys.attachment_keys("giấy  khai sinh.pdf", "")
    assert a == b and a["nk"].startswith("k:")
    assert keys.attachment_keys("Giấy khai sinh.jpg", "")["sk"] == a["sk"]
    assert keys.attachment_keys("Giấy khai sinh.jpg", "")["nk"] != a["nk"]
    assert keys.attachment_keys(".jpg", "")["sk"] == ""
    assert keys.attachment_keys("", "")["nk"] == ""


def test_co_giay_tuy_than():
    assert keys.attachment_keys("scan.pdf", "Giấy tờ tùy thân")["idd"] is True
    assert keys.attachment_keys("CĂN CƯỚC.pdf", "")["idd"] is True
    assert keys.attachment_keys("Đơn.pdf", "Bản chính")["idd"] is False


def test_khong_co_khoa_thi_giu_nguyen(monkeypatch):
    monkeypatch.setattr(archive_settings, "archive_hmac_key", "")
    items = [{"name": "a.pdf"}]
    assert keys.with_keys(items) == items


def test_doi_khoa_doi_ket_qua(monkeypatch):
    before = keys.attachment_keys("a.pdf", "")["nk"]
    monkeypatch.setattr(archive_settings, "archive_hmac_key", "khoa-khac")
    assert keys.attachment_keys("a.pdf", "")["nk"] != before
