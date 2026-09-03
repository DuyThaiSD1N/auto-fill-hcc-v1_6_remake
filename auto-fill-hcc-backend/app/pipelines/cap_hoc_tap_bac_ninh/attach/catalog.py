"""Danh mục thành phần hồ sơ eForm Bắc Ninh 1.014581 (hỗ trợ chi phí học tập).

4 nhóm TPHS chuẩn có mã KQ (khớp componentName theo mã KQ nằm trong dòng checkbox `thanhPhanHoSo<id>`);
CCCD / Đơn ủy quyền / Lời chứng không thuộc 4 nhóm → nộp qua ô "File đính kèm khác" (fileDinhKem).
"""

# (label, mã KQ hoặc None, slot, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("don_de_nghi", "KQ001000", "banChinh",
     "Đơn đề nghị hỗ trợ chi phí học tập (Mẫu số 01) — có tiêu đề 'ĐƠN ĐỀ NGHỊ HỖ TRỢ CHI PHÍ HỌC TẬP', do HSSV làm và ký."),
    ("xac_nhan_dao_tao", "KQ001001", "banChinh",
     "Giấy xác nhận của cơ sở đào tạo (Mẫu số 02) — có 'GIẤY XÁC NHẬN CỦA CƠ SỞ ĐÀO TẠO', do trường cấp."),
    ("bang_tot_nghiep", "KQ001002", "banChinh",
     "Bằng tốt nghiệp THCS hoặc THPT — có 'BẰNG TỐT NGHIỆP TRUNG HỌC CƠ SỞ'/'TRUNG HỌC PHỔ THÔNG'."),
    ("giay_uu_tien", "KQ001003", "banChinh",
     "Giấy tờ đối tượng ưu tiên: Giấy chứng nhận hộ nghèo/hộ cận nghèo/người khuyết tật hoặc QĐ trợ cấp xã hội."),
    ("cccd", None, "banChinh",
     "Căn cước công dân/CMND/thẻ căn cước/hộ chiếu."),
    ("don_uy_quyen", None, "banChinh",
     "Đơn/Văn bản xin xác nhận ủy quyền nộp hồ sơ trực tuyến (cha/mẹ nộp thay con)."),
    ("loi_chung", None, "banChinh",
     "Lời chứng chứng thực chữ ký tại Trung tâm phục vụ hành chính công."),
    ("khac", None, "banChinh",
     "Giấy tờ khác/trang không xác định được loại."),
]

_BY_LABEL = {label: (kq, slot, desc) for label, kq, slot, desc in CATALOG}
LABELS = [label for label, _, _, _ in CATALOG]

_DISPLAY = {
    "don_de_nghi": "Đơn đề nghị hỗ trợ chi phí học tập (Mẫu 01)",
    "xac_nhan_dao_tao": "Giấy xác nhận của cơ sở đào tạo (Mẫu 02)",
    "bang_tot_nghiep": "Bằng tốt nghiệp THCS/THPT",
    "giay_uu_tien": "Giấy tờ đối tượng ưu tiên",
    "cccd": "Căn cước công dân",
    "don_uy_quyen": "Đơn xin xác nhận ủy quyền nộp hồ sơ",
    "loi_chung": "Lời chứng chứng thực chữ ký",
    "khac": "Giấy tờ kèm theo hồ sơ",
}


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def resolve(label: str) -> tuple[str, str, str]:
    """→ (target, componentName, slotKey). componentName là mã KQ để FE khớp dòng thành phần."""
    kq, slot, _ = _BY_LABEL.get(label, (None, "banChinh", ""))
    if kq:
        return "existing", kq, slot
    return "supplementary", "", slot


def display_name(label: str) -> str:
    return _DISPLAY.get(label, _DISPLAY["khac"])


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
