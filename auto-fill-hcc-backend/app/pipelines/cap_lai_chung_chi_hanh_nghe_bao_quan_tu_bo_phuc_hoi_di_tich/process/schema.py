"""Compact schema cho "Thủ tục cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích" (1.002003, QT-10).

Cùng cổng, cùng trang `/nop-ho-so` dựng bằng liz-* như bản cấp mới 1.001822 (engine `fill-liz.js`, khớp ô theo
section = `.group-header` + nhãn `<mat-label>`). Theo bản mapping QT-10, trang hiện CÙNG LÚC nhiều khối đơn:
  - "Thông tin người nộp hồ sơ" / "Thông tin người ủy quyền" — y hệt bản cấp mới (dùng lại khuôn ở đó);
  - đơn giám định cổ vật (thủ tục khác) — KHÔNG điền;
  - "ĐƠN ĐỀ NGHỊ CẤP CHỨNG CHỈ HÀNH NGHỀ BẢO QUẢN…" (khối cấp mới) — khối DUY NHẤT có ô Trình độ chuyên môn /
    Kinh nghiệm, mapping lấy giá trị từ Đơn cấp lại vì cùng nội dung → điền;
  - "ĐƠN ĐỀ NGHỊ CẤP LẠI GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN HÀNH NGHỀ … (HOẶC CHỨNG CHỈ HÀNH NGHỀ …)" — khối chính:
    mục 1 người đề nghị, mục 2 số + ngày cấp chứng chỉ cũ và 3 ô lý do (bổ sung nội dung / bị hỏng / bị mất);
  - đơn cấp GCN của tổ chức + "Thông tin biên lai" — KHÔNG điền.
Lý do "hết hạn" không có ô riêng → ghi vào "Ghi chú" (textarea name="description") như mapping đề xuất.

⚑ CHƯA CÓ DOM GỐC: tiêu đề khối lấy theo bản mapping. Khối cấp mới dùng cùng cụm ngắn với bản 1.001822 ("chứng
chỉ hành nghề bảo quản"); tiêu đề khối cấp lại cũng chứa cụm này (trong ngoặc) nhưng đứng SAU trên trang nên
engine gặp ô của khối cấp mới trước. Khối cấp lại dùng cụm riêng "cấp lại giấy chứng nhận đủ điều kiện hành nghề"
— không khối nào khác chứa.
"""

from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    LABEL_DIA_CHI_LIEN_HE,
    LABEL_HO_TEN,
    LABEL_KINH_NGHIEM,
    LABEL_NGAY_SINH,
    LABEL_SO_DINH_DANH,
    LABEL_TRINH_DO,
    S_DON,
    S_NOP,
    S_UQ,
    UI_FIELDS as _UI_FIELDS_CAP_MOI,
    UY_QUYEN_CHECKBOX,
)

__all__ = [
    "LABEL_DIA_CHI_LIEN_HE", "LABEL_HO_TEN", "LABEL_KINH_NGHIEM", "LABEL_NGAY_SINH", "LABEL_SO_DINH_DANH",
    "LABEL_TRINH_DO", "S_DON", "S_NOP", "S_UQ", "UY_QUYEN_CHECKBOX",
]

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ (Đơn cấp lại Mẫu 51; đối chiếu CCCD, chứng chỉ đã cấp, văn bằng, CCHN xây dựng) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp lại — dòng '1. Họ và tên (viết chữ in hoa)' của Đơn; đối chiếu 'Cấp cho "
                "ông/bà' trên chứng chỉ đã cấp, 'Họ và tên' trên CCCD. Viết có dấu.",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy (Đơn: 'Ngày, tháng, năm sinh'; CCCD; chứng chỉ). Chỉ trả khi đọc "
                "được ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số CCCD/định danh của người đề nghị (CCCD hoặc dòng 'Căn cước công dân: số …' của Đơn). Chỉ chữ số. "
                "Số CMND cũ 9 số in trên chứng chỉ chỉ dùng khi không có số nào khác.",
    },
    {
        "name": "NguoiDeNghi_NgayCap",
        "desc": "Ngày cấp CÙNG giấy tờ với số định danh đã chọn (Đơn: '… cấp ngày dd/mm/yyyy tại …'), dd/mm/yyyy.",
    },
    {
        "name": "NguoiDeNghi_NoiCap",
        "desc": "Nơi cấp CÙNG giấy tờ với số định danh đã chọn — Đơn: phần sau 'tại'/'do' (vd 'Cục QLHC về TTXH').",
    },
    {
        "name": "NguoiDeNghi_DiaChiLienHe",
        "desc": "Dòng 'Địa chỉ liên hệ' của Đơn, chép NGUYÊN VĂN (giữ cả '(Nay là: …)' nếu có).",
    },
    {
        "name": "NguoiDeNghi_DiaChiHienNay",
        "desc": "Địa chỉ HIỆN HÀNH tách từ 'Địa chỉ liên hệ' của Đơn (phần sau 'Nay là' nếu có); Đơn không ghi thì "
                "nơi thường trú trên CCCD. KHÔNG lấy địa chỉ cũ in trên chứng chỉ đã cấp. Object "
                "{tinh,xa,chiTietDuoiXa}.",
    },
    {"name": "NguoiDeNghi_DienThoai", "desc": "Dòng 'Điện thoại' của Đơn, chỉ chữ số."},
    {"name": "NguoiDeNghi_Email", "desc": "Email của người đề nghị nếu giấy tờ có ghi, nguyên văn."},
    {
        "name": "NguoiDeNghi_TrinhDoChuyenMon",
        "desc": "Mục '2. Trình độ chuyên môn' của Đơn: MẢNG, mỗi dòng '+ …' một phần tử, chép NGUYÊN VĂN cả dấu '+'.",
    },
    {
        "name": "NguoiDeNghi_KinhNghiem",
        "desc": "Mục '3. Kinh nghiệm chuyên môn…' của Đơn: MẢNG theo thứ tự trên đơn — mỗi dòng '- …' một phần tử "
                "nguyên văn; mỗi HÀNG bảng quá trình công tác một phần tử dạng '<STT>. <cột 2> | <cột 3> | <cột 4> | "
                "<cột 5>'; mục a., b.… mỗi mục một phần tử.",
    },
    {
        "name": "Don_HoatDongDeNghi",
        "desc": "Các hoạt động đề nghị cấp lại, liệt kê sau '…cho các hoạt động sau:' của Đơn: MẢNG, mỗi phần tử một "
                "hoạt động, bỏ dấu '+'/'-' đầu dòng.",
    },
    {
        "name": "Don_LyDoCapLai",
        "desc": "Đoạn sau 'Lý do cấp lại' của Đơn, chép NGUYÊN VĂN, bỏ dấu '+'/'-' đầu dòng (vd 'Chứng chỉ hành nghề … "
                "số 12/SVHTT-QLDT cấp ngày 01/02/2020 đã hết hạn sử dụng ngày 31/01/2025.').",
    },
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn (vd 'Giám đốc Sở Văn hóa, Thể thao và Du lịch tỉnh …')."},

    # ---- CHỨNG CHỈ ĐÃ CẤP (chứng chỉ cũ đề nghị cấp lại) ----
    {
        "name": "ChungChiCu_So",
        "desc": "'Số chứng chỉ' trên chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích ĐÃ CẤP (vd '12/SVHTT-QLDT'); "
                "không có giấy thì số nêu trong 'Lý do cấp lại' của Đơn. Nguyên văn.",
    },
    {
        "name": "ChungChiCu_NgayCap",
        "desc": "Ngày cấp chứng chỉ ĐÃ CẤP — dòng '<Tỉnh>, ngày dd/mm/yyyy' trên chứng chỉ (hoặc 'cấp ngày' trong Lý do "
                "cấp lại của Đơn), dd/mm/yyyy. KHÔNG phải ngày cấp CMND/CCCD.",
    },
    {
        "name": "ChungChiCu_DenNgay",
        "desc": "Hạn của chứng chỉ ĐÃ CẤP — 'Chứng chỉ có giá trị … đến ngày dd/mm/yyyy' (hoặc 'hết hạn … ngày' trong "
                "Đơn), dd/mm/yyyy.",
    },

    # ---- VĂN BẰNG (bù trình độ chuyên môn khi đơn để trống) ----
    {
        "name": "VanBang_CoSoDaoTao",
        "desc": "Trường cấp bằng tốt nghiệp đại học (dòng 'Hiệu trưởng trường … cấp'), hoặc 'Cơ sở đào tạo' trên CCHN.",
    },
    {"name": "VanBang_Nganh", "desc": "Ngành ghi trên bằng tốt nghiệp đại học (vd 'Kiến trúc', 'Xây dựng dân dụng')."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "ChungChiCu_NgayCap", "ChungChiCu_DenNgay"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChiHienNay"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
S_CAP_LAI = "cấp lại giấy chứng nhận đủ điều kiện hành nghề"
# "Ghi chú" (textarea name="description") ở phần thông tin chung, không thuộc khối nào → section rỗng, engine chỉ
# nhận khi nhãn là DUY NHẤT trên trang.
S_CHUNG = ""
LABEL_GHI_CHU = "Ghi chú"

LABEL_TEN_CAP_LAI = (
    "Tên tổ chức, cá nhân đề nghị cấp lại Giấy chứng nhận đủ điều kiện hành nghề (hoặc Chứng chỉ hành nghề) (viết "
    "bằng chữ in hoa)"
)
LABEL_DIEN_THOAI = "Điện thoại"
LABEL_SO_CC_CU = "Số Giấy chứng nhận hành nghề (hoặc Chứng chỉ hành nghề đã cấp)"
LABEL_NGAY_CAP_CC_CU = "Ngày, tháng, năm cấp"
LABEL_BO_SUNG = "Bổ sung nội dung hành nghề (nêu rõ những thông tin đề nghị bổ sung nội dung hành nghề)"
LABEL_BI_HONG = (
    "Giấy chứng nhận đủ điều kiện hành nghề hoặc Chứng chỉ hành nghề đã được cấp bị hỏng (nêu rõ lý do bị hỏng)"
)
LABEL_BI_MAT = (
    "Giấy chứng nhận đủ điều kiện hành nghề hoặc Chứng chỉ hành nghề đã được cấp bị mất (nêu rõ lý do bị mất)"
)

_CAP_MOI_DON = {LABEL_HO_TEN, LABEL_SO_DINH_DANH, LABEL_NGAY_SINH, LABEL_DIA_CHI_LIEN_HE, LABEL_TRINH_DO, LABEL_KINH_NGHIEM}

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    # Khối người nộp / ủy quyền + 6 ô Mẫu 51 của khối cấp mới: y hệt bản 1.001822 (bỏ ô "hoạt động" — trang cấp lại
    # không có).
    *(row for row in _UI_FIELDS_CAP_MOI if row[0] in (S_NOP, S_UQ) or (row[0] == S_DON and row[1] in _CAP_MOI_DON)),

    (S_CHUNG, LABEL_GHI_CHU, "liz-input", ()),

    (S_CAP_LAI, LABEL_TEN_CAP_LAI, "liz-input", ("Tên tổ chức, cá nhân đề nghị cấp lại",)),
    (S_CAP_LAI, LABEL_SO_DINH_DANH, "liz-input", ("Số định danh cá nhân",)),
    (S_CAP_LAI, LABEL_NGAY_SINH, "liz-date", ("Ngày, tháng, năm sinh",)),
    (S_CAP_LAI, LABEL_DIA_CHI_LIEN_HE, "liz-input", ()),
    (S_CAP_LAI, LABEL_DIEN_THOAI, "liz-input", ("Số điện thoại",)),
    (S_CAP_LAI, LABEL_SO_CC_CU, "liz-input", ("Số Giấy chứng nhận hành nghề",)),
    (S_CAP_LAI, LABEL_NGAY_CAP_CC_CU, "liz-date", ()),
    (S_CAP_LAI, LABEL_BO_SUNG, "liz-input", ("Bổ sung nội dung hành nghề",)),
    (S_CAP_LAI, LABEL_BI_HONG, "liz-input", ()),
    (S_CAP_LAI, LABEL_BI_MAT, "liz-input", ()),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}
