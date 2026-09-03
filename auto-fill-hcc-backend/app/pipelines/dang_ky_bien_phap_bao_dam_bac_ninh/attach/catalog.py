"""Danh mục thành phần hồ sơ eForm Bắc Ninh 1.011441 (đăng ký biện pháp bảo đảm).

3 thành phần bắt buộc thường dùng: Phiếu yêu cầu Mẫu 01a (KQ003675), Hợp đồng bảo đảm (KQ003676),
Giấy chứng nhận bản gốc (KQ003684). CCCD/GCN ĐKDN/Giấy giới thiệu → ô đính kèm bổ sung (supplementary).
"""

# (label, mã KQ hoặc None, slot, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("phieu_01a", "KQ003675", "banChinh",
     "Phiếu yêu cầu đăng ký biện pháp bảo đảm theo Mẫu số 01a (NĐ 99/2022) — đơn đã kê khai, ký."),
    ("hop_dong_bao_dam", "KQ003676", "banChinh",
     "Hợp đồng bảo đảm/hợp đồng thế chấp (có thể kèm lời chứng công chứng)."),
    ("gcn_qsdd", "KQ003684", "banChinh",
     "Giấy chứng nhận quyền sử dụng đất (bản gốc)."),
    ("gcn_dkdn", None, "banChinh",
     "Giấy chứng nhận đăng ký doanh nghiệp/hộ kinh doanh (giấy tờ tư cách pháp lý của tổ chức)."),
    ("giay_gioi_thieu", None, "banChinh",
     "Giấy giới thiệu/Văn bản ủy quyền cử người đi nộp hồ sơ."),
    ("cccd", None, "banChinh",
     "Căn cước công dân/CMND/hộ chiếu của người liên quan."),
    ("khac", None, "banChinh",
     "Giấy tờ khác liên quan trực tiếp đến hồ sơ đăng ký biện pháp bảo đảm."),
]

_BY_LABEL = {label: (kq, slot, desc) for label, kq, slot, desc in CATALOG}
_DISPLAY = {
    "phieu_01a": "Phiếu yêu cầu đăng ký biện pháp bảo đảm (Mẫu 01a)",
    "hop_dong_bao_dam": "Hợp đồng bảo đảm",
    "gcn_qsdd": "Giấy chứng nhận quyền sử dụng đất",
    "gcn_dkdn": "Giấy chứng nhận đăng ký doanh nghiệp",
    "giay_gioi_thieu": "Giấy giới thiệu",
    "cccd": "Căn cước công dân",
    "khac": "Giấy tờ kèm theo hồ sơ đăng ký biện pháp bảo đảm",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str, str]:
    kq, slot, _ = _BY_LABEL.get(label, (None, "banChinh", ""))
    if kq:
        return "existing", kq, slot
    return "supplementary", "", slot


def display_name(label: str) -> str:
    return _DISPLAY.get(label, _DISPLAY["khac"])


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
