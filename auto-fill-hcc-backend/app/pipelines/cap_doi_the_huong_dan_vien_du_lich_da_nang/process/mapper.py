"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp đổi thẻ HDV du lịch (Đà Nẵng).

Cùng cổng, cùng Phần II với thẻ nội địa nên dùng lại các hàm chuẩn hoá của pipeline đó. Mỗi field emit
{name=<mat-label>, comp, value, section=<cụm group-header>, aliases=[nhãn thay thế]}; nhãn LẶP giữa các
section (Ngày cấp/Nơi cấp/Email…) nên `section` là bắt buộc — Phần IV cũng có "Ngày cấp"/"Nơi cấp" nhưng
là của THẺ HDV cũ, không phải của CCCD.

Phần II "Thông tin người nộp hồ sơ" là của TÀI KHOẢN đang đăng nhập (tên + số định danh cổng tự điền).
Chỉ đổ nhân thân người đề nghị vào đó khi số CCCD tài khoản (formContext) TRÙNG ĐỦ số CCCD trên hồ sơ.
Không trùng / không đọc đủ số / không có formContext → bỏ hẳn Phần II, chỉ điền Phần IV. Không điền khối
"Thông tin ủy quyền" (ẩn tới khi tick ô; tick hộ thì dễ đổ nhầm nhân thân chủ hồ sơ sang người nộp thay).

Loại thẻ đã được cấp là NHÓM 3 checkbox (Nội địa / Quốc tế / Tại điểm) → emit một `liz-checkbox` kèm
`option` = nhãn ô cần tích. Chỉ lấy từ thẻ cũ hoặc Đơn Mẫu 05: tiêu đề đơn cấp MỚI và tên chứng chỉ
nghiệp vụ là loại thẻ ĐỀ NGHỊ cấp, không phải loại đã được cấp.
"""

from __future__ import annotations

import re

from app.pipelines.cap_doi_the_huong_dan_vien_du_lich_da_nang.process.schema import (
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

# LLM hay chép cả nhãn in trên thẻ/đơn: "Số/No.: 048123456", "+ Số thẻ: …".
_SO_THE_PREFIX = re.compile(r"^\s*[+\-]?\s*(?:số thẻ|số|no)\s*[./:]*\s*(?:no\.?)?\s*[:.]?\s*", re.IGNORECASE)


def _loai_the(value) -> str | None:
    """'nội địa' / 'quốc tế' / 'tại điểm' theo chữ trên thẻ hoặc đơn; không rõ hoặc nhiều loại thì None."""
    folded = _fold(value)
    if not folded:
        return None
    found = [
        loai for loai, keys in (
            ("nội địa", ("noi dia", "domestic")),
            ("quốc tế", ("quoc te", "international")),
            ("tại điểm", ("tai diem", "on-site", "onsite")),
        ) if any(k in folded for k in keys)
    ]
    return found[0] if len(found) == 1 else None


def _loai_de_nghi(value) -> str | None:
    folded = _fold(value)
    if "doi" in folded:
        return "cấp đổi"
    if "lai" in folded:
        return "cấp lại"
    if "moi" in folded or folded in {"cap", "cap the"}:
        return "cấp mới"
    return None


def _so_the(value) -> tuple[str | None, str | None]:
    """(số thẻ, số bị loại). Số hiệu chứng chỉ ('CMS./HDDLNĐ-…') không phải số thẻ → loại, không điền."""
    text = _text(value)
    if not text:
        return None, None
    text = _SO_THE_PREFIX.sub("", text).strip(" .:;,-")
    if not text:
        return None, None
    folded = _fold(text)
    if "cms" in folded or "hdd" in folded or "/" in text:
        return None, text
    return text, None


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

    # ---- Phần IV: thẻ HDV đã được cấp (Đơn Mẫu 05 + thẻ cũ) ----
    loai_cu = _loai_the(values.get("TheCu_Loai"))
    so_the, so_bi_loai = _so_the(values.get("TheCu_SoThe"))
    # Tích loại thẻ TRƯỚC các ô chữ: engine dựng lại chỉ mục sau khi tích, ô phụ thuộc (nếu có) mới hiện.
    if loai_cu:
        put(S_THE, LABEL_LOAI_THE, True, option=LOAI_THE_OPTIONS[loai_cu])
    put(S_THE, "Giới tính", _gender(values.get("NguoiDeNghi_GioiTinh"), identity))
    put(S_THE, "Email", email)
    put(S_THE, "Số thẻ", so_the)
    put(S_THE, "Ngày cấp", _date(values.get("TheCu_NgayCap")))
    put(S_THE, "Nơi cấp", _text(values.get("TheCu_NoiCap")))
    put(S_THE, LABEL_LY_DO, _text(values.get("Don_LyDo")))

    # ---- Cảnh báo ----
    if not tu_nop:
        if not ctx_identity:
            ly_do = "chưa đọc được số CCCD của tài khoản đang đăng nhập"
        elif not identity:
            ly_do = "chưa đọc được đủ số CCCD của người đề nghị trên hồ sơ"
        else:
            ly_do = (
                f"số CCCD tài khoản đang đăng nhập ({ctx_name or ctx_identity}) KHÁC số CCCD của người "
                f"đề nghị cấp đổi thẻ ({ho_ten or 'theo Đơn đề nghị'})"
            )
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" vì {ly_do} — khối này giữ thông tin tài khoản, "
            "cán bộ tự kiểm tra Ngày sinh, Số điện thoại, Email, Địa chỉ. Chỉ điền phần thẻ hướng dẫn viên "
            "du lịch đã được cấp theo đơn."
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

    loai_de_nghi = _loai_de_nghi(values.get("Don_LoaiDeNghi"))
    if loai_de_nghi == "cấp mới":
        loai_moi = _loai_the(values.get("Don_LoaiTheDeNghi"))
        warnings.append(
            "LỆCH THỦ TỤC: Đơn trong hồ sơ là đơn CẤP MỚI thẻ hướng dẫn viên du lịch"
            + (f" {loai_moi.upper()}" if loai_moi else "")
            + " (Mẫu số 04/06) nhưng thủ tục đang chọn là CẤP ĐỔI thẻ (Đơn Mẫu số 05). Nếu người đề nghị "
            "chưa từng có thẻ thì chọn lại thủ tục cấp thẻ; nếu đúng là cấp đổi thì lập lại Đơn Mẫu số 05 "
            "(số thẻ, nơi cấp, ngày cấp, loại thẻ đã được cấp, lý do cấp đổi)."
        )
    elif loai_de_nghi == "cấp lại":
        warnings.append(
            "Đơn ghi đề nghị CẤP LẠI thẻ (thẻ bị mất/hư hỏng) — thủ tục đang chọn là CẤP ĐỔI. Cấp lại là thủ "
            "tục riêng (1.004614), kiểm tra lại với người đề nghị trước khi nộp."
        )
    if so_bi_loai:
        warnings.append(
            f"\"{so_bi_loai}\" trông như số hiệu chứng chỉ/văn bằng, không phải số thẻ hướng dẫn viên du lịch — "
            "không điền ô Số thẻ, cán bộ đối chiếu thẻ HDV đã được cấp."
        )
    elif not so_the:
        warnings.append(
            "Chưa có SỐ THẺ hướng dẫn viên du lịch đã được cấp — hồ sơ thiếu ảnh thẻ HDV cũ và Đơn Mẫu 05 "
            "không ghi số thẻ; cán bộ bổ sung trước khi nộp."
        )
    if not loai_cu:
        warnings.append(
            "Chưa xác định được LOẠI THẺ đã được cấp (Nội địa / Quốc tế / Tại điểm) từ thẻ cũ hoặc Đơn Mẫu 05 — "
            "cán bộ tự tích ô tương ứng ở mục 'Đã được cấp thẻ hướng dẫn viên du lịch loại'."
        )
    elif loai_cu == "tại điểm":
        warnings.append(
            "Thẻ đã được cấp là thẻ hướng dẫn viên du lịch TẠI ĐIỂM — thủ tục cấp đổi này chỉ áp dụng cho thẻ "
            "QUỐC TẾ và NỘI ĐỊA. Kiểm tra lại thủ tục trước khi nộp."
        )
    co_quan = _text(values.get("Don_CoQuanNhan"))
    # Dòng in sẵn "Sở Du lịch/Sở VHTTDL tỉnh/thành phố …." chưa ghi tỉnh không phải nơi gửi khác.
    if co_quan and "da nang" not in _fold(co_quan) and "tinh/thanh pho" not in _fold(co_quan):
        warnings.append(
            f"Đơn gửi \"{co_quan}\" — thủ tục này nộp về Sở Văn hóa, Thể thao và Du lịch TP Đà Nẵng. Kiểm tra "
            "lại nơi tiếp nhận."
        )
    return out, warnings
