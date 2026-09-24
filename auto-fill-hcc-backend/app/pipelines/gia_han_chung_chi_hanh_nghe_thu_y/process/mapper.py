"""Map compact source facts → Form.io data[...] fields cho thủ tục "Gia hạn Chứng chỉ hành nghề thú y".

Form cùng họ với "Cấp lại Chứng chỉ hành nghề thú y" nên dùng lại toàn bộ helper chuẩn hoá của
cap_lai_CCHN_thu_y.process.mapper. Nguyên tắc giữ nguyên:

NGƯỜI TRONG HỒ SƠ ĐI XUỐNG PHẦN II, KHÔNG LÊN PHẦN I. Phần I "Thông tin người nộp hồ sơ" là nhân thân
TÀI KHOẢN ĐANG ĐĂNG NHẬP do cổng đổ vào (ô số căn cước bị khoá). Mapper KHÔNG phát ô nhân thân nào của
Phần I; nó bỏ tích "Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II rồi đổ người đề nghị vào
data[owner*] và khối "Thông tin chung" của tờ đơn 02.HNTY (gắn scope vì field-key trùng Phần I).

Mục "Đã được cấp Chứng chỉ hành nghề thú y" là selectboxes 12 option dùng chung name data[deNghi][];
mapper khớp phạm vi đọc trong Đơn với nhãn chuẩn rồi gửi optionLabel cho FE tự tick.
"""

from __future__ import annotations

import re

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.cap_lai_CCHN_thu_y.process.mapper import (
    _area,
    _by_name,
    _commune_label,
    _date,
    _identity,
    _match_pham_vi,
    _phone,
    _province_label,
    _so_dang_ky,
    _strip_admin_prefix,
    _text,
    _yes,
)
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.process.schema import (
    DON_SCOPE,
    DON_SCOPE_NEAR,
    DON_SCOPED_FIELDS,
    NGUOI_NOP_MARKERS,
    PHAM_VI_FIELD_KEY,
    UI_COMP_BY_NAME,
)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    # Không cần formContext: người trong hồ sơ luôn xuống khối chủ hồ sơ, khối người nộp không đụng tới
    # dù tự nộp hay nộp thay.
    _ = options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()

    def add(name: str, value, *, option_label: str | None = None) -> None:
        seen_key = (name, option_label or "")
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in DON_SCOPED_FIELDS:
            # scope = panel tờ đơn; scopeNear/scopeAway để extension tự thu hẹp khi panel đó bọc cả
            # hai khối nhân thân, và BỎ ô nếu vẫn không tách được — thà trống còn hơn ghi đè Phần I.
            field["scope"] = DON_SCOPE
            field["scopeNear"] = DON_SCOPE_NEAR
            field["scopeAway"] = list(NGUOI_NOP_MARKERS)
        if option_label is not None:
            field["optionLabel"] = option_label
        out.append(field)
        seen.add(seen_key)

    # --- NGƯỜI ĐỀ NGHỊ = CHỦ HỒ SƠ (Phần II), KHÔNG phải người nộp hồ sơ (Phần I) ---
    name = _text(values.get("NguoiDeNghi_HoTen"))
    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    residence = _area(values.get("NguoiDeNghi_ThuongTru"))
    birthday = _date(values.get("NguoiDeNghi_NgaySinh"))
    identity_date = _date(values.get("NguoiDeNghi_NgayCapCCCD"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    province = _province_label(residence.get("tinh")) if residence else None
    commune = _commune_label(residence.get("xa")) if residence else None
    address = _text(residence.get("diaChi")) if residence else None

    if not name:
        warnings.append("Thiếu họ tên người đề nghị từ CCCD/Đơn 02.HNTY/Giấy khám sức khỏe.")

    add("data[kinhGui]", _text(values.get("Don_KinhGui")))

    # Bỏ tích "Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II — không đọc được ô số căn cước bị khoá
    # của Phần I để đối chiếu, bỏ tích rồi khai đủ Phần II thì đúng cả khi tự nộp lẫn nộp thay.
    add("data[isOwnerDossierCheck]", False)

    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", _text(values.get("NguoiDeNghi_GioiTinh")))
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", identity_date)
    add("data[ownerIdIssuePlace]", normalize_issuer(values.get("NguoiDeNghi_NoiCapCCCD")) or None)
    add("data[ownerProvince]", province)
    add("data[ownerDistrict]", commune)
    add("data[ownerAddress]", address)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerNation]", "Việt Nam" if name or identity else None)

    # --- Mục "Thông tin chung" của TỜ ĐƠN: cũng là NGƯỜI ĐỀ NGHỊ, không phải người nộp ---
    add("data[fullname]", name)
    add("data[birthday]", birthday)
    add("data[identityNumber]", identity)
    add("data[identityDate]", identity_date)
    add("data[province]", province)
    add("data[district]", commune)
    add("data[address]", address)
    add("data[phoneNumber]", phone)

    # Ô "Tôi là người nước ngoài" cổng để sẵn CHƯA tick; chỉ TICK khi giấy tờ nói rõ là người nước ngoài.
    if _yes(values.get("Don_LaNguoiNuocNgoai")):
        add("data[toiLaNguoiNuocNgoai]", True)
    add("data[bangCapChuyenMon]", _text(values.get("Don_BangCapChuyenMon")))

    if not identity:
        warnings.append(
            "Không đọc được số căn cước của người đề nghị (hồ sơ không có CCCD và Giấy khám sức khỏe không "
            "ghi) — ô số căn cước ở mục Thông tin chủ hồ sơ còn trống, vui lòng điền tay."
        )
    if residence and not address:
        # "Địa chỉ chi tiết" của chủ hồ sơ là ô BẮT BUỘC; đơn giấy hay chỉ ghi tới phường/xã.
        warnings.append(
            "Giấy tờ chỉ ghi nơi cư trú tới phường/xã — ô 'Địa chỉ chi tiết' (bắt buộc) ở mục Thông tin chủ "
            "hồ sơ còn trống, vui lòng bổ sung số nhà/thôn/tổ."
        )

    # --- Nội dung đơn đăng ký ---
    # Phạm vi hành nghề: mỗi dòng được tích trong Đơn → 1 checkbox, FE khớp theo nhãn chuẩn.
    matched: list[str] = []
    unmatched: list[str] = []
    for line in re.split(r"\s*[;\n]\s*", _text(values.get("Don_PhamViHanhNghe")) or ""):
        line = line.strip(" .;")
        if not line:
            continue
        option = _match_pham_vi(line)
        if option:
            matched.append(option)
        else:
            unmatched.append(line)
    for option in matched:
        add(PHAM_VI_FIELD_KEY, True, option_label=option)
    if unmatched:
        warnings.append(
            "Chưa tự tích được phạm vi hành nghề sau (không khớp dòng nào trên form, vui lòng tích "
            f"tay): {'; '.join(unmatched)}."
        )
    elif not matched:
        warnings.append(
            "Chưa đọc được phạm vi hành nghề trong Đơn — vui lòng tích tay mục 'Đã được cấp Chứng chỉ "
            "hành nghề thú y'."
        )

    so_dk = _so_dang_ky(values.get("CCHNCu_SoDangKy"))
    ngay_het_han = _date(values.get("CCHNCu_NgayHetHan"))
    add("data[soDK]", so_dk)
    add("data[ngayCC]", ngay_het_han)
    if not so_dk or not ngay_het_han:
        warnings.append(
            "Hồ sơ không có Chứng chỉ hành nghề thú y đã cấp — ô 'Số đăng ký' / 'Chứng chỉ có giá trị đến' "
            "còn trống, vui lòng nhập tay theo chứng chỉ cần gia hạn."
        )
    # Ô "Địa điểm" là input text tự do → ghi TÊN ĐỊA DANH trần (vd "Lai Châu"), bỏ tiền tố hành chính.
    dia_diem = _text(values.get("Don_DiaDiem")) or (_text(residence.get("tinh")) if residence else None)
    add("data[diaDiem]", _strip_admin_prefix(dia_diem) if dia_diem else None)
    add("data[thoiGian]", _date(values.get("Don_NgayLamDon")))
    add("data[nguoiLD]", _text(values.get("Don_NguoiLamDon")) or name)

    return out, warnings
