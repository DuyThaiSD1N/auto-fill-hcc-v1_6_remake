"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp lại thẻ HDV du lịch (Đà Nẵng).

Cùng cổng, cùng khối người nộp với thẻ nội địa và cùng khối "thẻ đã được cấp" (Mẫu 05) với cấp đổi nên dùng
lại các hàm chuẩn hoá của hai pipeline đó. Mỗi field emit {name=<mat-label>, comp, value, section=<cụm
group-header>, aliases=[nhãn thay thế]}; nhãn LẶP giữa các section (Ngày cấp/Nơi cấp/Email…) nên `section`
là bắt buộc — khối cấp lại cũng có "Ngày cấp"/"Nơi cấp" nhưng là của THẺ HDV cũ, không phải của CCCD.

Khối "Thông tin người nộp hồ sơ" là của TÀI KHOẢN đang đăng nhập (tên + số định danh cổng tự điền). Chỉ đổ
nhân thân người đề nghị vào đó khi số CCCD tài khoản (formContext) TRÙNG ĐỦ số CCCD trên hồ sơ. Không trùng /
không đọc đủ số / không có formContext → bỏ hẳn khối đó, chỉ điền khối cấp lại. Không điền khối "Thông tin
ủy quyền" (ẩn tới khi tick ô; tick hộ thì dễ đổ nhầm nhân thân chủ hồ sơ sang người nộp thay).

Loại thẻ đã được cấp là NHÓM 3 checkbox (Nội địa / Quốc tế / Tại điểm) → emit một `liz-checkbox` kèm
`option` = nhãn ô cần tích. Chỉ lấy từ Đơn Mẫu 05 hoặc thẻ cũ: tiêu đề đơn cấp MỚI và tên chứng chỉ nghiệp
vụ là loại thẻ ĐỀ NGHỊ cấp, không phải loại đã được cấp — chỉ nêu trong cảnh báo để cán bộ tự quyết.
"""

from __future__ import annotations

from app.pipelines.cap_doi_the_huong_dan_vien_du_lich_da_nang.process.mapper import _loai_the, _so_the
from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.process.schema import (
    AFTER_BY_UI,
    ALIASES_BY_UI,
    COMP_BY_UI,
    LABEL_LOAI_THE,
    LABEL_LY_DO,
    LOAI_THE_OPTIONS,
    S_NOP,
    S_THE,
)
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
    _text,
)


def _loai_de_nghi(value) -> str | None:
    """Tiêu đề in sẵn 'cấp đổi/cấp lại' (không gạch bên nào) là đơn của thủ tục đang chọn → 'cấp lại'."""
    folded = _fold(value)
    if "lai" in folded:
        return "cấp lại"
    if "doi" in folded:
        return "cấp đổi"
    if "moi" in folded or folded in {"cap", "cap the"}:
        return "cấp mới"
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value, hint: str | None = None, option: str | None = None) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        item = {"name": label, "comp": comp, "value": value, "section": section}
        if option:
            item["option"] = option
        aliases = ALIASES_BY_UI.get((section, label))
        if aliases:
            item["aliases"] = aliases
        after = AFTER_BY_UI.get((section, label))
        if after:
            item["after"] = after
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

    # ---- Khối người nộp chỉ điền khi CCCD tài khoản đăng nhập TRÙNG CCCD trên hồ sơ ----
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

    # ---- Khối cấp lại: thẻ HDV đã được cấp (Đơn Mẫu 05 + thẻ cũ nếu còn) ----
    loai_cu = _loai_the(values.get("TheCu_Loai"))
    so_the, so_bi_loai = _so_the(values.get("TheCu_SoThe"))
    ly_do = _text(values.get("Don_LyDo"))
    loai_de_nghi = _loai_de_nghi(values.get("Don_LoaiDeNghi"))
    loai_moi = _loai_the(values.get("Don_LoaiTheDeNghi")) if loai_de_nghi == "cấp mới" else None
    # Không có loại thẻ cũ mà hồ sơ là đơn cấp mới → tích tạm theo loại thẻ ĐỀ NGHỊ (kèm cảnh báo bên dưới)
    # để cán bộ khỏi bỏ trống mục bắt buộc; cán bộ đổi ô nếu loại thẻ đã cấp khác.
    loai_tich = loai_cu or loai_moi
    # Tích loại thẻ TRƯỚC các ô chữ: engine dựng lại chỉ mục sau khi tích, ô phụ thuộc (nếu có) mới hiện.
    if loai_tich:
        put(S_THE, LABEL_LOAI_THE, True, option=LOAI_THE_OPTIONS[loai_tich])
    put(S_THE, "Giới tính", _gender(values.get("NguoiDeNghi_GioiTinh"), identity))
    put(S_THE, "Email", email)
    put(S_THE, "Số thẻ", so_the)
    put(S_THE, "Ngày cấp", _date(values.get("TheCu_NgayCap")))
    put(S_THE, "Nơi cấp", _text(values.get("TheCu_NoiCap")))
    put(S_THE, LABEL_LY_DO, ly_do)

    # ---- Cảnh báo ----
    if not tu_nop:
        if not ctx_identity:
            ly_do_bo = "chưa đọc được số CCCD của tài khoản đang đăng nhập"
        elif not identity:
            ly_do_bo = "chưa đọc được đủ số CCCD của người đề nghị trên hồ sơ"
        else:
            ly_do_bo = (
                f"số CCCD tài khoản đang đăng nhập ({ctx_name or ctx_identity}) KHÁC số CCCD của người "
                f"đề nghị cấp lại thẻ ({ho_ten or 'theo Đơn đề nghị'})"
            )
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" vì {ly_do_bo} — khối này giữ thông tin tài khoản, "
            "cán bộ tự kiểm tra Ngày sinh, Số điện thoại, Email, Địa chỉ. Chỉ điền phần thông tin cấp lại "
            "thẻ hướng dẫn viên du lịch theo đơn."
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

    if loai_de_nghi == "cấp mới":
        warnings.append(
            "LỆCH THỦ TỤC: Đơn trong hồ sơ là đơn CẤP MỚI thẻ hướng dẫn viên du lịch"
            + (f" {loai_moi.upper()}" if loai_moi else "")
            + " (Mẫu số 04/06) nhưng thủ tục đang chọn là CẤP LẠI thẻ (Đơn Mẫu số 05). Nếu người đề nghị "
            "chưa từng có thẻ thì chọn lại thủ tục cấp thẻ; nếu đúng là cấp lại thì lập lại Đơn Mẫu số 05 "
            "(số thẻ, nơi cấp, ngày cấp, loại thẻ đã được cấp, lý do cấp lại)."
        )
    elif loai_de_nghi == "cấp đổi" or (ly_do and "het han" in _fold(ly_do)):
        warnings.append(
            "Đơn ghi đề nghị CẤP ĐỔI thẻ (thẻ hết hạn) — thủ tục đang chọn là CẤP LẠI (thẻ bị mất, hư hỏng "
            "hoặc thay đổi thông tin). Cấp đổi là thủ tục riêng (1.001432), kiểm tra lại với người đề nghị "
            "trước khi nộp."
        )
    if so_bi_loai:
        warnings.append(
            f"\"{so_bi_loai}\" trông như số hiệu chứng chỉ/văn bằng, không phải số thẻ hướng dẫn viên du lịch — "
            "không điền ô Số thẻ, cán bộ đối chiếu mục 'Đã được cấp thẻ' của Đơn Mẫu 05."
        )
    elif not so_the:
        warnings.append(
            "Chưa có SỐ THẺ hướng dẫn viên du lịch đã được cấp — Đơn Mẫu 05 không ghi số thẻ và hồ sơ không có "
            "ảnh thẻ cũ; cán bộ bổ sung (tra cứu trên hệ thống quản lý hướng dẫn viên) trước khi nộp."
        )
    if not loai_cu and loai_moi:
        warnings.append(
            f"Chưa xác định được LOẠI THẺ đã được cấp từ Đơn Mẫu 05 hoặc thẻ cũ — đã tích TẠM ô "
            f"{LOAI_THE_OPTIONS[loai_moi].upper()} theo loại thẻ đề nghị trên đơn cấp mới. Cán bộ đối chiếu thẻ "
            "đã được cấp và đổi ô ở mục 'Đã được cấp thẻ hướng dẫn viên du lịch loại' nếu khác."
        )
    elif not loai_cu:
        warnings.append(
            "Chưa xác định được LOẠI THẺ đã được cấp (Nội địa / Quốc tế / Tại điểm) từ Đơn Mẫu 05 hoặc thẻ cũ — "
            "cán bộ tự tích ô tương ứng ở mục 'Đã được cấp thẻ hướng dẫn viên du lịch loại'."
        )
    if not ly_do and loai_de_nghi != "cấp mới":
        warnings.append(
            "Đơn chưa ghi LÝ DO đề nghị cấp lại thẻ (bị mất / hư hỏng / thay đổi thông tin) — cán bộ hỏi lại "
            "người đề nghị và nhập tay."
        )
    co_quan = _text(values.get("Don_CoQuanNhan"))
    # Dòng in sẵn "Sở Du lịch/Sở VHTTDL tỉnh/thành phố …." chưa ghi tỉnh không phải nơi gửi khác.
    if co_quan and "da nang" not in _fold(co_quan) and "tinh/thanh pho" not in _fold(co_quan):
        warnings.append(
            f"Đơn gửi \"{co_quan}\" — thủ tục này nộp về Sở Văn hóa, Thể thao và Du lịch TP Đà Nẵng. Kiểm tra "
            "lại nơi tiếp nhận."
        )
    return out, warnings
