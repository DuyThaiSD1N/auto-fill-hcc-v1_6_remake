"""Metadata trình bày thủ tục trong báo cáo Excel.

Registry hiện chưa lưu cấp thẩm quyền và một số mã TTHC, nên giữ bảng bù tập trung tại đây
để API và các script export cũ không tự phát sinh hai cách diễn giải khác nhau.
"""
import re

from app.procedures.registry import _ATTACH_PIPELINE


_CAP_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^chung-thuc|^cap-ban-sao-so-goc"), "Cấp xã"),
    (re.compile(r"khai-sinh|ket-hon|khai-tu|trich-luc|ho-tich|hon-nhan|giam-ho|nhan-cha-me-con"), "Cấp xã"),
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
    "giai-quyet-che-do-khang-chien": "1.010819",
    "xet-tuyen-vien-chuc-lai-chau": "3.000601",
    # Hộ tịch trên Cổng DVC quốc gia mới: URL chỉ có formalityId, không có maThuTuc để đọc mã.
    "khai-sinh-dang-ky-thuong": "1.001193",
    "khai-sinh-nuoc-ngoai": "2.000528",
    "trich-luc-ks": "2.000635",
    "trich-luc-ks-eform": "2.000635",
    "khai-tu": "1.000656",
    "thay-doi-cai-chinh-ho-tich": "1.004859",
    "xac-nhan-tinh-trang-hon-nhan": "1.004873",
    # Form cũ eForm Bộ Tư pháp của cùng thủ tục (URL có maThuTuc nhưng khai sẵn cho chắc).
    "xac-nhan-tinh-trang-hon-nhan-eform": "1.004873",
    # Biến thể theo tỉnh / theo quy trình không mang mã riêng → mã của thủ tục gốc: cùng tỉnh bỏ hậu tố quy
    # trình (iLis, vbdlis, miền núi hải đảo, cổng mới), hoặc mã quốc gia của đúng tên thủ tục ở ke_khai_links.
    "dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang-ilis": "1.012796",
    "giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang-vbdlis": "1.013949",
    "dang-ky-dat-dai-lan-dau-tuyen-quang-ilis": "1.013978",
    "dang-ky-dat-dai-lan-dau-tuyen-quang-vbdlis": "1.013978",
    "giao-thue-chuyen-muc-dich-dat-ninh-binh": "1.013949",
    "dinh-chinh-gcn-da-cap-ninh-binh": "1.012796",
    "dinh-chinh-da-cap-ninh-binh": "1.012790",
    "cap-doi-gcn-ninh-binh": "1.012783",
    "dang-ky-bien-dong-dat-dai-ninh-binh": "1.013831",
    "giao-thue-chuyen-muc-dich-dat-quang-ngai": "1.013949",
    "dang-ky-dat-dai-lan-dau-quang-ngai": "1.013978",
    "dinh-chinh-sai-sot-quang-ngai": "1.012796",
    "xac-dinh-lai-dien-tich-dat-o-quang-ngai": "1.012817",
    "ho-tro-chi-phi-hoa-tang-quang-ngai": "1.012749",
    "dang-ky-dat-dai-lan-dau-da-nang": "1.013978",
    "cap-doi-gcn-da-nang": "1.012783",
    "dinh-chinh-gcn-da-cap-da-nang": "1.012796",
    "tach-hop-thua-dat-da-nang": "1.012784",
    "chuyen-muc-dich-su-dung-dat-da-nang": "1.013992",
    "giao-thue-dat-lao-cai": "1.115650",
    "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao": "1.115820",
    "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao": "1.115835",
    "cap-doi-gcn-quang-ninh-mien-nui-hai-dao": "1.115848",
    "cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao": "1.115848",
    "tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao": "1.115832",
    "dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao": "1.115840",
    "dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao": "1.115837",
    "sua-chua-cai-tao-gpxd-nha-o-rieng-le": "1.013229",
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": "1.013855",
    "mai-tang-dan-cong-hoa-tuyen": "1.014359",
    "thi-tuyen-cong-chuc-mot-cua-moha": "1.014111",
    "tro-cap-tho-cung-liet-si": "1.010803",
    "tro-cap-xa-hoi-hang-thang": "1.001776",
    "cap-lai-giay-phep-hanh-nghe-truoc-2024": "1.012290",
    "dieu-chinh-giay-phep-hoat-dong-kcb": "1.012280",
    "gia-han-luu-hanh-phuong-tien-lao": "1.002063",
}
# Một mã TTHC trên DVC mà registry tách theo quy trình (nhãn mang hậu tố quy trình): dòng báo cáo gộp theo mã
# hiện tên đầy đủ của thủ tục, không phụ thuộc quy trình nào có hồ sơ trước.
TEN_THEO_MA = {
    "1.013229": "Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV và nhà ở riêng lẻ",
}
# Key đã đổi tên / gộp vào key khác: hồ sơ cũ vẫn mang key cũ → tra entry hiện tại để báo cáo ra đúng mã, tên
# và gộp chung một dòng với hồ sơ mới.
KEY_CU = {
    "ho-tro-mai-tang": "ho-tro-mai-tang-1116910",
    "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bds-da-nang": "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san",
}
_MA_TT_RE = re.compile(r"(?:mathutuc|matthc)=(\d+\.\d+)", re.IGNORECASE)


def ma_thu_tuc(entry: dict | None) -> str:
    if not entry:
        return "—"
    for url in (entry.get("detect") or {}).get("urlIncludes") or []:
        match = _MA_TT_RE.search(url)
        if match:
            return match.group(1)
    if entry["key"] in _MA_TT_BO_SUNG:
        return _MA_TT_BO_SUNG[entry["key"]]
    # Phần lớn thủ tục không mang mã trên URL nhận diện; đọc thêm trường code / URL kê khai / ke_khai_links
    # cùng cách trang danh mục thủ tục. Import trong hàm: app.dashboard.procedures import app.reports.integration,
    # mà integration import module này → import ở đầu file là vòng import.
    from app.dashboard.procedures import _codes

    return ", ".join(_codes(entry)) or "—"


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
