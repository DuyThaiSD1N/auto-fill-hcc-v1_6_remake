"""Metadata trình bày thủ tục trong báo cáo Excel.

Registry hiện chưa lưu cấp thẩm quyền và một số mã TTHC, nên giữ bảng bù tập trung tại đây
để API và các script export cũ không tự phát sinh hai cách diễn giải khác nhau.
"""
import re

from app.procedures.registry import _ATTACH_PIPELINE


_CAP_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^chung-thuc|^cap-ban-sao-so-goc"), "Cấp xã"),
    (re.compile(r"khai-sinh|ket-hon|khai-tu|trich-luc|ho-tich|hon-nhan|giam-ho|nhan-cha-me-con|nuoi-con-nuoi"), "Cấp xã"),
    (re.compile(r"ho-kinh-doanh|^dang-ky-kinh-doanh"), "Cấp xã"),
    (re.compile(r"mai-tang|huu-tri-xa-hoi|tro-cap-xa-hoi"), "Cấp xã"),
    (re.compile(r"tro-choi-dien-tu"), "Cấp xã"),
    (re.compile(r"dat-dai|gcn|dinh-chinh|thua-dat|giao-thue|quy-hoach|thu-hoi"), "Cấp tỉnh"),
    (re.compile(r"liet-si|to-quoc-ghi-cong|nguoi-co-cong|khang-chien|tu-tran|di-chuyen-ho-so"), "Cấp tỉnh"),
    (re.compile(r"thi-tuyen|xet-tuyen"), "Cấp tỉnh"),
    (re.compile(r"attp|an-toan-thuc-pham|lien-van|tau-ca"), "Cấp tỉnh"),
]
_CAP_MAC_DINH = "Cấp xã"
_MA_TT_BO_SUNG = {
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": "1.013792",
    "giai-quyet-che-do-khang-chien": "2.009383",
    "xet-tuyen-vien-chuc-lai-chau": "3.000601",
}
_MA_TT_RE = re.compile(r"(?:mathutuc|matthc)=(\d+\.\d+)", re.IGNORECASE)


def ma_thu_tuc(entry: dict | None) -> str:
    if not entry:
        return "—"
    for url in (entry.get("detect") or {}).get("urlIncludes") or []:
        match = _MA_TT_RE.search(url)
        if match:
            return match.group(1)
    return _MA_TT_BO_SUNG.get(entry["key"], "—")


def cap_thu_tuc(key: str) -> str:
    for pattern, label in _CAP_RULES:
        if pattern.search(key):
            return label
    return _CAP_MAC_DINH


def pham_vi_ho_tro(entry: dict | None, key: str) -> str:
    mode = (entry or {}).get("mode") or ""
    has_attach = key in _ATTACH_PIPELINE
    if mode == "attach":
        return "Đính kèm hồ sơ tự động"
    if has_attach:
        return "Điền biểu mẫu + đính kèm hồ sơ tự động"
    return "Điền biểu mẫu tự động"
