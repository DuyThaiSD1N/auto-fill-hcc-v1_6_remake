"""Catalog thành phần hồ sơ (Đăng ký đất đai, cấp GCN lần đầu — Bắc Ninh).

LLM phân loại tài liệu → NHÃN RÚT GỌN → BE map sang componentName chi tiết (mã KQ) hoặc ô bổ sung.
Danh mục form có ~20 thành phần; gom về nhãn phân biệt được. Cá nhân chủ yếu dùng:
don_mau_15 / danh_sach_15a / chung_tu_tai_chinh / uy_quyen / giay_to_nguon_goc, và
cccd / gcn_ket_hon → ô bổ sung.
"""

# (label, componentName = mã KQ hoặc None → ô bổ sung, mô tả ngắn cho LLM)
CATALOG: list[tuple[str, str | None, str]] = [
    ("don_mau_15", "KQ005747", "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) — bản kê khai"),
    ("danh_sach_15a", "KQ006106",
     "Danh sách/văn bản xác định các thành viên có chung quyền sử dụng đất (Mẫu 15a)"),
    ("chung_tu_tai_chinh", "KQ006110",
     "Chứng từ thực hiện nghĩa vụ tài chính; phiếu thu tiền; giấy tờ miễn/giảm nghĩa vụ tài chính"),
    ("uy_quyen", "KQ005910",
     "Văn bản về việc đại diện/ủy quyền theo pháp luật dân sự (hợp đồng ủy quyền)"),
    ("giay_to_nguon_goc", "KQ006114",
     "Giấy tờ về quyền sử dụng đất theo Điều 137/148/... hoặc quyết định giao/thuê/chuyển mục đích đất"),
    ("thua_ke", "KQ006115", "Giấy tờ về việc nhận thừa kế quyền sử dụng đất"),
    ("chuyen_quyen", "KQ006111",
     "Giấy tờ về việc chuyển quyền sử dụng đất/tài sản gắn liền với đất có chữ ký các bên"),
    ("trich_do_dia_chinh", "KQ006107", "Mảnh trích đo bản đồ địa chính thửa đất"),
    ("van_ban_cap_chung_gcn", "KQ006116",
     "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận (nhiều người chung quyền)"),
    ("xu_phat", "KQ006104", "Giấy tờ/quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai"),
    ("giay_to_xay_dung", "KQ006112",
     "Giấy xác nhận của cơ quan quản lý xây dựng / hồ sơ thiết kế xây dựng công trình"),
    # --- không có ô riêng → ô đính kèm BỔ SUNG ---
    ("cccd", None, "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu"),
    ("gcn_ket_hon", None, "Giấy chứng nhận kết hôn/đăng ký kết hôn (chứng minh quan hệ vợ chồng)"),
    ("khac", None, "Giấy tờ khác hoặc không xác định được loại"),
]

_BY_LABEL = {label: (kq, desc) for label, kq, desc in CATALOG}
LABELS = [label for label, _, _ in CATALOG]

_DISPLAY = {
    "don_mau_15": "Đơn đăng ký đất đai (Mẫu 15)",
    "danh_sach_15a": "Danh sách người đồng sử dụng (Mẫu 15a)",
    "chung_tu_tai_chinh": "Chứng từ nghĩa vụ tài chính",
    "uy_quyen": "Hợp đồng ủy quyền",
    "giay_to_nguon_goc": "Giấy tờ nguồn gốc sử dụng đất",
    "thua_ke": "Giấy tờ thừa kế",
    "chuyen_quyen": "Giấy tờ chuyển quyền",
    "trich_do_dia_chinh": "Mảnh trích đo địa chính",
    "van_ban_cap_chung_gcn": "Văn bản cấp chung Giấy chứng nhận",
    "xu_phat": "Giấy tờ xử phạt đất đai",
    "giay_to_xay_dung": "Giấy tờ xây dựng",
    "cccd": "Căn cước công dân",
    "gcn_ket_hon": "Giấy chứng nhận kết hôn",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str]:
    kq, _ = _BY_LABEL.get(label, (None, ""))
    return ("existing", kq) if kq else ("supplementary", "")


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in CATALOG)
