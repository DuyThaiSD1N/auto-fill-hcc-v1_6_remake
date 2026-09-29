"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp thẻ HDV du lịch tại điểm (Đà Nẵng).

Cùng cổng, cùng bộ ô với thẻ nội địa nên dùng lại các hàm chuẩn hoá của pipeline đó. Mỗi field emit
{name=<mat-label>, comp, value, section=<cụm group-header>, aliases=[nhãn thay thế]}; nhãn LẶP giữa các
section (Ngày sinh/Ngày cấp/Nơi cấp/Email/Địa chỉ…) nên `section` là bắt buộc.

Phần II "Thông tin người nộp hồ sơ" là của TÀI KHOẢN đang đăng nhập (tên + số định danh cổng tự điền).
Chỉ đổ nhân thân người đề nghị vào đó khi số CCCD tài khoản (formContext) TRÙNG ĐỦ số CCCD trên hồ sơ.
Không trùng / không đọc đủ số / không có formContext → bỏ hẳn Phần II, chỉ điền phần "Cấp thẻ…" bên
dưới. Không điền khối "Thông tin ủy quyền": khối này ẩn tới khi tick ô, engine không thấy ô sẽ bỏ qua,
còn tick hộ thì dễ đổ nhầm nhân thân chủ hồ sơ sang người nộp thay.

Khác thẻ nội địa: thẻ tại điểm KHÔNG đòi văn bằng/chứng chỉ, nhưng ô "Tên điểm du lịch" là cốt lõi — thiếu
thì cảnh báo; đơn/chứng chỉ ghi thẻ NỘI ĐỊA/QUỐC TẾ thì cảnh báo lệch thủ tục.
"""

from __future__ import annotations

from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.process.mapper import (
    _area,
    _by_name,
    _date,
    _digits,
    _email,
    _fold,
    _gender,
    _identity,
    _issuer,
    _phone,
    _province_label,
    _ten_diem,
    _text,
)
from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.process.schema import (
    ALIASES_BY_UI,
    COMP_BY_UI,
    S_NOP,
    S_THE,
)

_LABEL_NGOAI_NGU = "Trình độ ngoại ngữ (đối với người đề nghị cấp thẻ HDV du lịch quốc tế)"
_LABEL_DIEM_DU_LICH = "Tên điểm du lịch đối với trường hợp cấp thẻ hướng dẫn viên du lịch tại điểm"


def _loai_the(value) -> str | None:
    """'tại điểm' / 'nội địa' / 'quốc tế' theo chữ trên đơn hoặc tên chứng chỉ; không rõ thì None."""
    folded = _fold(value)
    if "tai diem" in folded:
        return "tại điểm"
    if "noi dia" in folded:
        return "nội địa"
    if "quoc te" in folded:
        return "quốc tế"
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value, hint: str | None = None) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        item = {"name": label, "comp": comp, "value": value, "section": section}
        aliases = ALIASES_BY_UI.get((section, label))
        if aliases:
            item["aliases"] = aliases
        if hint:
            item["hint"] = hint
        out.append(item)

    ho_ten = _text(values.get("NguoiDeNghi_HoTen"))
    raw_identity = _digits(values.get("NguoiDeNghi_SoDinhDanh"))
    identity = _identity(raw_identity)
    ngay_sinh = _date(values.get("NguoiDeNghi_NgaySinh"))
    ngay_cap = _date(values.get("NguoiDeNghi_NgayCap"))
    noi_cap = _issuer(values.get("NguoiDeNghi_NoiCap"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    email = _email(values.get("NguoiDeNghi_Email"))
    area = _area(values.get("NguoiDeNghi_DiaChi"))
    xa = _text(area.get("xa")) if area else None
    tinh = _province_label(area.get("tinh")) if area else None
    dia_chi_chi_tiet = _text(area.get("diaChi")) if area else None

    # ---- Phần II chỉ điền khi CCCD tài khoản đăng nhập TRÙNG CCCD trên hồ sơ ----
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    tu_nop = bool(ctx_identity and identity and ctx_identity == identity)

    if tu_nop:
        put(S_NOP, "Ngày sinh", ngay_sinh)
        put(S_NOP, "Ngày cấp", ngay_cap)
        put(S_NOP, "Nơi cấp", noi_cap)
        put(S_NOP, "Số điện thoại", phone)
        put(S_NOP, "Email", email)
        # Ô hành chính là MỘT mat-select gộp Tỉnh–Xã; gửi tên xã, kèm tỉnh làm gợi ý để engine chọn đúng
        # dòng khi tên xã trùng ở nhiều tỉnh.
        put(S_NOP, "Địa chỉ hành chính", xa or tinh, hint=tinh if xa else None)
        put(S_NOP, "Địa chỉ chi tiết", dia_chi_chi_tiet)

    # ---- Phần IV: nội dung Đơn ----
    trinh_do = _text(values.get("NguoiDeNghi_TrinhDoChuyenMon")) or _text(values.get("VanBang_TrinhDo"))
    ten_diem = _ten_diem(values.get("NguoiDeNghi_TenDiemDuLich"))
    put(S_THE, "Giới tính", _gender(values.get("NguoiDeNghi_GioiTinh"), identity))
    put(S_THE, "Trình độ chuyên môn nghiệp vụ", trinh_do)
    put(S_THE, _LABEL_NGOAI_NGU, _text(values.get("NguoiDeNghi_TrinhDoNgoaiNgu")))
    put(S_THE, "Email", email)
    put(S_THE, _LABEL_DIEM_DU_LICH, ten_diem)

    # ---- Cảnh báo ----
    if not tu_nop:
        if not ctx_identity:
            ly_do = "chưa đọc được số CCCD của tài khoản đang đăng nhập"
        elif not identity:
            ly_do = "chưa đọc được đủ số CCCD của người đề nghị trên hồ sơ"
        else:
            ly_do = (
                f"số CCCD tài khoản đang đăng nhập ({ctx_name or ctx_identity}) KHÁC số CCCD của người "
                f"đề nghị cấp thẻ ({ho_ten or 'theo Đơn đề nghị'})"
            )
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" vì {ly_do} — khối này giữ thông tin tài khoản, "
            "cán bộ tự kiểm tra Ngày sinh, Số điện thoại, Email, Địa chỉ. Chỉ điền phần \"Cấp thẻ hướng "
            "dẫn viên du lịch tại điểm\" theo đơn."
        )
    else:
        thieu = [
            label for label, value in (
                ("Số điện thoại", phone), ("E-mail", email),
                ("Địa chỉ hành chính", xa or tinh), ("Địa chỉ chi tiết", dia_chi_chi_tiet),
            ) if not value
        ]
        if thieu:
            warnings.append(
                "Chưa đọc được đầy đủ các ô bắt buộc của khối \"Thông tin người nộp hồ sơ\": "
                f"{', '.join(thieu)} — bản scan có thể bị che/mờ, cán bộ nhập tay theo Đơn đề nghị hoặc CCCD."
            )
    if raw_identity and not identity:
        warnings.append(
            f"Số định danh trên giấy tờ chỉ đọc được \"{raw_identity}\" (không đủ 12 số) — không điền, cán "
            "bộ đối chiếu CCCD/VNeID của người đề nghị."
        )

    loai_don = _loai_the(values.get("Don_LoaiThe"))
    loai_chung_chi = _loai_the(values.get("ChungChi_Ten"))
    if loai_don in ("nội địa", "quốc tế"):
        warnings.append(
            f"LỆCH THỦ TỤC: Đơn đề nghị ghi cấp thẻ hướng dẫn viên du lịch {loai_don.upper()} nhưng thủ tục "
            "đang chọn là thẻ TẠI ĐIỂM (Đơn Mẫu số 06). Xác nhận lại với người đề nghị; nếu đúng là thẻ "
            f"{loai_don} thì chọn lại thủ tục — danh mục thành phần hồ sơ sẽ khác."
        )
    elif not loai_don and loai_chung_chi in ("nội địa", "quốc tế"):
        warnings.append(
            f"Hồ sơ kèm chứng chỉ nghiệp vụ hướng dẫn du lịch {loai_chung_chi} — kiểm tra lại người đề nghị "
            "cần thẻ TẠI ĐIỂM hay thẻ " + loai_chung_chi + " trước khi nộp."
        )
    if not ten_diem:
        warnings.append(
            "Chưa có TÊN ĐIỂM DU LỊCH — ô cốt lõi của thẻ hướng dẫn viên tại điểm. Đơn không ghi tên điểm cụ "
            "thể (dòng 'Hướng dẫn ghi' in sẵn không tính); cán bộ hỏi người đề nghị rồi nhập tay."
        )
    co_quan = _text(values.get("Don_CoQuanNhan"))
    if co_quan and "da nang" not in _fold(co_quan):
        warnings.append(
            f"Đơn gửi \"{co_quan}\" — thủ tục này nộp về Sở Văn hóa, Thể thao và Du lịch TP Đà Nẵng. Kiểm tra "
            "lại nơi tiếp nhận."
        )
    return out, warnings
