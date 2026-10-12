"""Map compact source facts → Form.io data[...] fields cho thủ tục "Gia hạn Chứng chỉ hành nghề thú y".

Form cùng họ với "Cấp lại Chứng chỉ hành nghề thú y" nên dùng lại toàn bộ helper chuẩn hoá của
cap_lai_CCHN_thu_y.process.mapper. Nguyên tắc giữ nguyên:

NGƯỜI ĐỀ NGHỊ ĐI XUỐNG PHẦN II. Mapper bỏ tích "Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II rồi đổ
người đề nghị vào data[owner*] và khối "Thông tin chung" của tờ đơn 02.HNTY (gắn scope vì field-key trùng
Phần I). Phần I "Thông tin người nộp hồ sơ" = NGƯỜI NỘP: nộp thay (có CCCD riêng của người nộp) → nhân
thân trên CCCD đó; tự nộp (formContext tài khoản khớp người đề nghị) → người đề nghị; không rõ → không
đụng, chỉ cảnh báo (ô số căn cước Phần I bị khoá theo tài khoản, đoán sai là ghép hai người).

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
    _fold,
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


def _is_tu_nop(options: dict | None, name: str | None, identity: str | None) -> bool:
    """Tài khoản đăng nhập (formContext Phần I) có phải chính người đứng đơn không."""
    context = (options or {}).get("formContext") or {}
    ctx_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    if ctx_identity and identity:
        return ctx_identity == identity
    ctx_name = _text(context.get("applicantFullname") or context.get("fullname"))
    return bool(ctx_name and name and _fold(ctx_name) == _fold(name))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()

    def add(name: str, value, *, option_label: str | None = None, nguoi_nop: bool = False) -> None:
        seen_key = (name, option_label or ("nguoi_nop" if nguoi_nop else ""))
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if nguoi_nop:
            # Phần I nằm ĐẦU trang → ô đầu tiên trùng key; không gắn scope để extension không coi là
            # khối cấm ghi và trả lại giá trị cũ.
            if name in DON_SCOPED_FIELDS:
                field["occurrence"] = 0
        elif name in DON_SCOPED_FIELDS:
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

    # --- Phần I "Thông tin người nộp hồ sơ" ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_identity = _identity(values.get("NguoiNop_SoDinhDanh"))
    # LLM đôi khi chép lại chính người đứng đơn vào NguoiNop_* → coi là tự nộp.
    if (nop_identity and nop_identity == identity) or (
        not nop_identity and nop_name and name and _fold(nop_name) == _fold(name)
    ):
        nop_name = nop_identity = None
    if nop_name or nop_identity:
        # NỘP THAY: người trên CCCD riêng của người nộp.
        nop_residence = _area(values.get("NguoiNop_ThuongTru"))
        add("data[fullname]", nop_name, nguoi_nop=True)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")), nguoi_nop=True)
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")), nguoi_nop=True)
        add("data[identityNumber]", nop_identity, nguoi_nop=True)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCapCCCD")), nguoi_nop=True)
        add("data[idIssuePlace]", normalize_issuer(values.get("NguoiNop_NoiCapCCCD")) or None, nguoi_nop=True)
        if nop_residence:
            add("data[province]", _province_label(nop_residence.get("tinh")), nguoi_nop=True)
            add("data[district]", _commune_label(nop_residence.get("xa")), nguoi_nop=True)
            add("data[address]", _text(nop_residence.get("diaChi")), nguoi_nop=True)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")), nguoi_nop=True)
    elif _is_tu_nop(options, name, identity):
        # TỰ NỘP (tài khoản đăng nhập = người đứng đơn): Phần I cũng là người đứng đơn.
        add("data[fullname]", name, nguoi_nop=True)
        add("data[birthday]", birthday, nguoi_nop=True)
        add("data[gender]", _text(values.get("NguoiDeNghi_GioiTinh")), nguoi_nop=True)
        add("data[identityNumber]", identity, nguoi_nop=True)
        add("data[identityDate]", identity_date, nguoi_nop=True)
        add("data[idIssuePlace]", normalize_issuer(values.get("NguoiDeNghi_NoiCapCCCD")) or None, nguoi_nop=True)
        add("data[province]", province, nguoi_nop=True)
        add("data[district]", commune, nguoi_nop=True)
        add("data[address]", address, nguoi_nop=True)
        add("data[phoneNumber]", phone, nguoi_nop=True)
    else:
        # Không có CCCD người nộp và không biết tài khoản là ai → không đoán, tránh ghép họ tên người
        # đứng đơn vào số căn cước (bị khoá) của tài khoản.
        warnings.append(
            "Hồ sơ không có CCCD của người nộp — mục 'Thông tin người nộp hồ sơ' giữ theo tài khoản đăng "
            "nhập, vui lòng kiểm tra/bổ sung tay (hoặc tải kèm CCCD người nộp)."
        )

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
