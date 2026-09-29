"""Ba thủ tục biện pháp bảo đảm cổng Lào Cai (1.011441 / 1.011442 / 1.011443) không cướp trang của nhau.

Tên "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất" là chuỗi con của tiêu đề thủ tục xóa, và cả ba
dùng chung cổng → mỗi entry phải khóa bằng mã. Popup so `textIncludes` (AND) trên innerText đã bỏ dấu.
"""

import unicodedata

import pytest

from app.procedures.registry import PROCEDURES

_TIEU_DE = {
    "dang-ky-bien-phap-bao-dam-lao-cai": (
        "Một phần 1.011441.000.00.00.H38 - Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn "
        "liền với đất"
    ),
    "dang-ky-thay-doi-bien-phap-bao-dam-lao-cai": (
        "Một phần 1.011442.000.00.00.H38 - Đăng ký thay đổi nội dung biện pháp bảo đảm bằng quyền sử dụng "
        "đất, tài sản gắn liền với đất đã đăng ký"
    ),
    "xoa-dang-ky-bien-phap-bao-dam-lao-cai": (
        "Một phần 1.011443.000.00.00.H38 - Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản "
        "gắn liền với đất"
    ),
}


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.replace("Đ", "D").replace("đ", "d"))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


def _entries_lao_cai():
    for entry in PROCEDURES:
        scope = " ".join((entry.get("detect") or {}).get("urlScope") or [])
        if "laocai.gov.vn" in scope:
            yield entry


@pytest.mark.parametrize("key", sorted(_TIEU_DE))
def test_moi_trang_chi_khop_dung_mot_thu_tuc(key):
    trang = _fold(_TIEU_DE[key])
    khop = [
        e["key"] for e in _entries_lao_cai()
        if (e["detect"].get("textIncludes") or [])
        and all(_fold(t) in trang for t in e["detect"]["textIncludes"])
    ]
    assert khop == [key]


def test_hai_thu_tuc_moi_co_du_pipeline():
    from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE

    for key in ("dang-ky-bien-phap-bao-dam-lao-cai", "dang-ky-thay-doi-bien-phap-bao-dam-lao-cai"):
        assert key in _PIPELINE and key in _ATTACH_PIPELINE
