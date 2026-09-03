"""Catalog thành phần hồ sơ "[Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ" (1.011443).

LLM phân loại mỗi tài liệu → NHÃN RÚT GỌN. BE map nhãn → componentName (mã KQ in trong dòng tiêu đề mỗi
thành phần) + slotKey (banChinh/banSao) hoặc ô đính kèm BỔ SUNG. FE khớp thành phần theo mã KQ.

9 TPHS; hồ sơ mẫu (cá nhân, chính chủ ký) chỉ dùng TPHS 1 (Phiếu 03a) + TPHS 2 (GCN bản gốc).
"""

# (label rút gọn, mã KQ | None nếu ô bổ sung, slotKey, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("phieu_yc_03a", "KQ003715", "banChinh",
     "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm theo Mẫu số 03a — bản đã ký, đóng dấu bên nhận bảo đảm "
     "(ngân hàng). Tiêu đề 'PHIẾU YÊU CẦU XÓA ĐĂNG KÝ…' / 'Mẫu số 03a'."),
    ("gcn", "KQ003716", "banChinh",
     "Giấy chứng nhận (bản gốc) — Giấy chứng nhận QSDĐ/QSH nhà ở (sổ đỏ/sổ hồng), có 'số vào sổ cấp GCN', "
     "số thửa, tờ bản đồ, số phát hành; GỒM cả trang mục IV 'Những thay đổi sau khi cấp GCN'."),
    ("van_ban_dai_dien", "KQ003718", "banSao",
     "Văn bản có nội dung về ĐẠI DIỆN (giám hộ/ủy quyền/người đại diện) — chỉ khi thực hiện qua người đại diện."),
    ("giay_to_chi_nhanh", "KQ003719", "banSao",
     "Giấy tờ về chi nhánh của pháp nhân được giao thực hiện chức năng (khi người yêu cầu là chi nhánh pháp nhân)."),
    ("vb_dong_y_ben_nhan", "KQ003717", "banChinh",
     "Giấy tờ/văn bản khi người yêu cầu xóa KHÔNG phải bên nhận bảo đảm và phiếu chưa có chữ ký/con dấu bên "
     "nhận bảo đảm — vd văn bản đồng ý xóa đăng ký của bên nhận bảo đảm (ngân hàng)."),
    ("giay_to_mien_phi", "KQ003720", "banSao",
     "Giấy tờ chứng minh thuộc đối tượng được miễn phí/giá dịch vụ (điểm đ khoản 1 Điều 9 NĐ 99/2022)."),
    ("giay_to_nhieu_nguoi", "KQ003721", "banSao",
     "Giấy tờ khi bên bảo đảm/bên nhận bảo đảm gồm NHIỀU người (đủ chữ ký các đồng bảo đảm hoặc văn bản cử đại diện)."),
    ("ban_an_toa_an", "KQ003722", "banSao",
     "Bản án, quyết định có hiệu lực pháp luật của Tòa án (khi xóa đăng ký theo điểm m khoản 1 Điều 20)."),
    ("danh_muc_nhieu_bpbd", "KQ003723", "banSao",
     "Danh mục văn bản kê khai khi xóa đăng ký NHIỀU biện pháp bảo đảm cùng một bên nhận bảo đảm."),
    # --- không có ô riêng trong danh mục → ô đính kèm BỔ SUNG ---
    ("hop_dong_the_chap", None, "banChinh",
     "Hợp đồng thế chấp quyền sử dụng đất/tài sản (không có ô riêng trong danh mục → đính kèm bổ sung)."),
    ("cccd", None, "banChinh", "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu của các bên."),
    ("khac", None, "banChinh", "Giấy tờ khác hoặc không xác định được loại."),
]

_BY_LABEL = {label: (kq, slot, desc) for label, kq, slot, desc in CATALOG}
LABELS = [label for label, _, _, _ in CATALOG]

_DISPLAY = {
    "phieu_yc_03a": "Phiếu yêu cầu xóa đăng ký (Mẫu 03a)",
    "gcn": "Giấy chứng nhận QSDĐ (bản gốc)",
    "van_ban_dai_dien": "Văn bản về đại diện",
    "giay_to_chi_nhanh": "Giấy tờ chi nhánh pháp nhân",
    "vb_dong_y_ben_nhan": "Văn bản đồng ý xóa của bên nhận bảo đảm",
    "giay_to_mien_phi": "Giấy tờ miễn phí/giá dịch vụ",
    "giay_to_nhieu_nguoi": "Giấy tờ đồng bảo đảm nhiều người",
    "ban_an_toa_an": "Bản án/quyết định của Tòa án",
    "danh_muc_nhieu_bpbd": "Danh mục xóa nhiều biện pháp bảo đảm",
    "hop_dong_the_chap": "Hợp đồng thế chấp",
    "cccd": "Căn cước công dân",
    "khac": "Tài liệu kèm theo",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str, str]:
    """Nhãn rút gọn → (target, componentName, slotKey). componentName = mã KQ khi có ô riêng, "" nếu bổ sung."""
    kq, slot, _ = _BY_LABEL.get(label, (None, "banChinh", ""))
    if kq:
        return ("existing", kq, slot)
    return ("supplementary", "", slot)


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
