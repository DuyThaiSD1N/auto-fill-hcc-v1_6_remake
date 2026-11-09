"""Map compact source facts → Form.io data[...] fields cho "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở
trợ giúp xã hội" (1.116908, NĐ 335/2026/NĐ-CP).

Form và hai chế độ người nộp GIỐNG 1.116909 (dùng lại helper của mapper đó):
  Phần 1 (data[fullname...])   — NGƯỜI NỘP:
      · THEO TÀI KHOẢN (FE gửi họ tên/CCCD tài khoản trong formContext): chọn người giám hộ hoặc đối tượng khớp
        tài khoản; họ tên + CCCD LUÔN lấy của tài khoản vì cổng đã điền sẵn theo định danh điện tử.
      · THEO TỜ KHAI (submitterMode="owner_as_submitter" — cài đặt "Lấy người nộp theo tờ khai" của Auto Fill /
        submitterFromDeclaration của tài khoản trợ lý —, hoặc FE không gửi mốc): người giám hộ (Mẫu 04 mục II);
        không có → dùng đối tượng. Bật cài đặt thì ô ngày sinh/ngày cấp/nơi cấp Phần I mà tờ khai không có bị
        xoá (cổng đổ sẵn theo tài khoản), runner mở khoá họ tên + CCCD để ghi đè.
  Phần 2 (data[owner*])        — CHỦ HỒ SƠ = ĐỐI TƯỢNG (mục I). LUÔN bỏ tích isOwnerDossierCheck + điền tường
                                 minh. Cổng KHÔNG xoá dữ liệu đã chép từ Phần I khi bỏ tích → ô định danh/ngày của
                                 chủ hồ sơ mà hồ sơ không có (trẻ chưa có thẻ, người lang thang) phát clear. SĐT đối
                                 tượng trống → dùng SĐT người giám hộ vì ô SĐT chủ hồ sơ là bắt buộc.
  data[ghiChu]                 — nhóm đối tượng (mục I.7, luôn có "Đối tượng cần bảo vệ khẩn cấp" vì đó là điều
                                 kiện của thủ tục) + nơi ở hiện nay (mục I.3) khi khác nơi cư trú (theo file mapping).
1.116907 (tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn) dùng lại mapper này với
required_group=None: Ghi chú chỉ ghi nhóm đọc được ở mục I.7.
Ngày sinh chỉ có năm (Biên bản tiếp nhận) → KHÔNG điền 01/01, cảnh báo để cán bộ xác minh.
Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
from typing import Any

from app.locations.catalog import find_province
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.mapper import (
    _account_anchor,
    _account_submitter,
    _area,
    _by_name,
    _complete_missing_provinces,
    _fold,
    _identity,
    _issuer,
    _phone,
    _province_label as _fallback_province_label,
    _text,
    _validated_submitter_identity,
)
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.schema import (
    UI_COMP_BY_NAME,
)

PROCEDURE_KEY = "tiep-nhan-doi-tuong-can-bao-ve-khan-cap-vao-co-so-tro-giup-xa-hoi"

EMERGENCY_GROUP = "Đối tượng cần bảo vệ khẩn cấp"
# Ô tích mục I.7 Tờ khai Mẫu số 04: (dấu hiệu sau khi fold, nhãn ghi vào Ghi chú) — theo thứ tự in trên tờ khai.
_GROUPS: tuple[tuple[str, str], ...] = (
    ("duoi 16 tuoi", "trẻ em dưới 16 tuổi không có nguồn nuôi dưỡng"),
    ("du 16 tuoi", "người từ đủ 16 tuổi không có nguồn nuôi dưỡng đang đi học"),
    ("khuyet tat", "người khuyết tật nặng, đặc biệt nặng"),
    ("hiv", "người nhiễm HIV/AIDS"),
    ("cao tuoi", "người cao tuổi không có điều kiện sống tại cộng đồng"),
    ("khan cap", "đối tượng cần bảo vệ khẩn cấp"),
)
_DISABILITY_LEVELS = {"nang": "nặng", "dac biet nang": "đặc biệt nặng"}


def _province_label(value: Any) -> str | None:
    """Nhãn tỉnh đúng danh mục ("Thành phố Đồng Nai"); option cổng Bộ Y tế theo địa giới mới — "Tỉnh Đồng Nai"
    sẽ trượt option "Thành Phố Đồng Nai"."""
    text = _text(value)
    if not text:
        return None
    province = find_province(text)
    return province["text"] if province else _fallback_province_label(text)


def _full_date(value: Any) -> str | None:
    """Chỉ nhận ngày đủ dd/mm/yyyy; chỉ có năm/tháng thì None (không tự điền 01/01)."""
    text = _text(value)
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text or "")
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), m.group(3)
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None
    return f"{day:02d}/{month:02d}/{year}"


def _plain(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _fold(value)).strip()


def _groups_note(groups_value: Any, disability_value: Any, required_group: str | None = EMERGENCY_GROUP) -> str:
    """'Đối tượng cần bảo vệ khẩn cấp; người khuyết tật nặng'. ``required_group`` là điều kiện của thủ tục, luôn
    đứng đầu (1.116908: nhóm khẩn cấp); None (1.116907) thì chỉ ghi các nhóm đọc được ở mục I.7, viết hoa chữ đầu.
    "du 16 tuoi" không nằm trong "duoi 16 tuoi"."""
    folded = _plain(" ".join(map(str, groups_value)) if isinstance(groups_value, list) else _text(groups_value) or "")
    labels = [required_group] if required_group else []
    for marker, label in _GROUPS:
        if marker not in folded:
            continue
        if marker == "khuyet tat":
            level = _DISABILITY_LEVELS.get(_plain(disability_value))
            label = f"người khuyết tật {level}" if level else label
        if _plain(label) not in {_plain(item) for item in labels}:
            labels.append(label)
    note = "; ".join(labels)
    return note[:1].upper() + note[1:]


def _same_place(current: str, residence: dict | None) -> bool:
    """Nơi ở hiện nay trùng nơi cư trú? So phần chi tiết (số nhà/tổ/khu phố) của nơi cư trú trong chuỗi nơi ở."""
    now = _plain(current)
    if not now or now in {"nhu tren", "nhu noi cu tru", "nhu muc 2"}:
        return True
    if not residence:
        return False
    detail = _plain(residence.get("diaChi"))
    ward = _plain(re.sub(r"^(phường|xã|đặc khu|thị trấn)\s+", "", str(residence.get("xa") or ""), flags=re.I))
    if detail:
        return detail in now and (not ward or ward in now)
    return bool(ward) and now.startswith(ward)


def enrich(
    fields: list[dict], options: dict | None = None, required_group: str | None = EMERGENCY_GROUP,
) -> tuple[list[dict], list[str]]:
    """``required_group``: nhóm đối tượng là điều kiện của thủ tục, luôn mở đầu Ghi chú — 1.116908 mặc định nhóm
    khẩn cấp; 1.116907 (cùng form, cùng Tờ khai Mẫu số 04) truyền None."""
    anchor = _account_anchor(options)
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def clear(name: str) -> None:
        if name in seen:
            return
        out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True})
        seen.add(name)

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _text(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    # --- ĐỐI TƯỢNG cần bảo vệ khẩn cấp = chủ hồ sơ (mục I) ---
    subject = {
        "name": _text(values.get("DoiTuong_HoTen")),
        "identity": _identity(values.get("DoiTuong_SoDinhDanh")),
        "birthday": _full_date(values.get("DoiTuong_NgaySinh")),
        "gender": _text(values.get("DoiTuong_GioiTinh")),
        "id_date": _full_date(values.get("DoiTuong_NgayCap")),
        "issuer": None,
        "residence": _area(values.get("DoiTuong_NoiCuTru")),
        "phone": _phone(values.get("DoiTuong_DienThoai")),
        "email": _text(values.get("DoiTuong_Email")),
    }
    has_subject = bool(subject["name"] or subject["identity"])
    if not subject["name"]:
        warnings.append("Thiếu họ tên đối tượng cần bảo vệ khẩn cấp từ Tờ khai Mẫu số 04/CCCD/Biên bản tiếp nhận.")
    raw_birthday = _text(values.get("DoiTuong_NgaySinh"))
    if raw_birthday and not subject["birthday"]:
        warnings.append(
            f"Ngày sinh đối tượng trên giấy tờ chỉ ghi '{raw_birthday}' — không tự điền ngày/tháng; cán bộ xác minh "
            "rồi nhập ô Ngày sinh của chủ hồ sơ."
        )

    # --- NGƯỜI GIÁM HỘ (mục II) ---
    guardian = {
        "name": _text(values.get("NguoiNop_HoTen")),
        "identity": _validated_submitter_identity(values.get("NguoiNop_SoDinhDanh")),
        "birthday": _full_date(values.get("NguoiNop_NgaySinh")),
        "gender": _text(values.get("NguoiNop_GioiTinh")),
        "id_date": _full_date(values.get("NguoiNop_NgayCap")),
        "issuer": None,
        "residence": _area(values.get("NguoiNop_NoiCuTru")),
        "phone": _phone(values.get("NguoiNop_DienThoai")),
        "email": _text(values.get("NguoiNop_Email")),
    }
    subject["issuer"] = _issuer(values.get("DoiTuong_NoiCap"), subject["id_date"], subject["identity"])
    guardian["issuer"] = _issuer(values.get("NguoiNop_NoiCap"), guardian["id_date"], guardian["identity"])
    has_guardian = bool(guardian["name"] or guardian["identity"])

    if anchor:
        candidates = [guardian, subject] if has_guardian else [subject]
        matched = _account_submitter(candidates, anchor)
        if matched is None:
            # Người đăng nhập không có trong hồ sơ: chỉ họ tên + CCCD tài khoản là chắc chắn của họ.
            submitter = {"name": anchor["name"], "identity": anchor["identity"]}
            warnings.append(
                "Không tìm thấy người nộp khớp tài khoản "
                f"({anchor['identity'] or anchor['name']}) trong tờ khai/giấy tờ; "
                "chỉ điền họ tên và số định danh của tài khoản."
            )
        else:
            submitter = {
                **matched,
                "name": anchor["name"] or matched.get("name"),
                "identity": anchor["identity"] or matched.get("identity"),
            }
    else:
        submitter = guardian if has_guardian else subject

    residence = subject["residence"]
    nop_residence = submitter.get("residence")
    _complete_missing_provinces(residence, nop_residence, guardian["residence"])

    # Remap phường/xã theo bảng sáp nhập; chạy SAU _complete_missing_provinces vì lookup cần có tỉnh.
    residence = remap_area(residence)
    nop_residence = remap_area(nop_residence)

    add("data[chonDoiTuong]", "Cá nhân")
    add("data[fullname]", submitter.get("name"))
    add("data[birthday]", submitter.get("birthday"))
    add("data[gender]", submitter.get("gender"))
    add("data[identityNumber]", submitter.get("identity"))
    add("data[identityDate]", submitter.get("id_date"))
    add("data[idIssuePlace]", submitter.get("issuer"))
    add_area("data[province]", "data[district]", "data[address]", nop_residence)
    add("data[phoneNumber]", submitter.get("phone"))
    add("data[email]", submitter.get("email"))
    if "data[email]" not in seen:
        # Cổng nhớ email của lượt nộp trước và tự điền lại → hồ sơ không có email người nộp thì XOÁ ô.
        clear("data[email]")
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter" and submitter.get("name"):
        # Người nộp lấy theo tờ khai: cổng đổ sẵn nhân thân TÀI KHOẢN vào Phần I → ô tờ khai không có phải xoá,
        # không để ngày sinh/ngày cấp của tài khoản đứng cạnh họ tên người giám hộ.
        for name in ("data[birthday]", "data[identityDate]", "data[idIssuePlace]"):
            clear(name)
        if not submitter.get("identity"):
            warnings.append(
                f"Không đọc được số định danh của người nộp theo tờ khai ({submitter['name']}) — ô CC/CCCD Phần I "
                "vẫn là số của tài khoản đăng nhập; cán bộ kiểm tra."
            )

    # --- Mở khoá Phần II: BỎ TÍCH "Người nộp là chủ hồ sơ" ---
    add("data[isOwnerDossierCheck]", False)

    # --- Phần II: chủ hồ sơ = ĐỐI TƯỢNG ---
    add("data[ownerFullname]", subject["name"])
    add("data[ownerBirthday]", subject["birthday"])
    add("data[ownerGender]", subject["gender"])
    add("data[ownerIdentityNumber]", subject["identity"])
    add("data[ownerIdentityDate]", subject["id_date"])
    add("data[ownerIdIssuePlace]", subject["issuer"])
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
    # Ô SĐT chủ hồ sơ bắt buộc; đối tượng (trẻ em, nạn nhân) thường không có SĐT → dùng SĐT người giám hộ.
    add("data[ownerPhoneNumber]", subject["phone"] or guardian["phone"])
    add("data[ownerEmail]", subject["email"])
    add("data[ownerNation]", "Việt Nam" if has_subject else None)
    if has_subject:
        # Bỏ tích không xoá dữ liệu cổng đã chép từ Phần I → ô của chủ hồ sơ mà hồ sơ không có phải xoá trống,
        # không để lại số định danh/ngày sinh của người nộp.
        for name in ("data[ownerBirthday]", "data[ownerIdentityNumber]", "data[ownerIdentityDate]",
                     "data[ownerIdIssuePlace]", "data[ownerEmail]"):
            clear(name)

        groups = values.get("DoiTuong_NhomDoiTuong")
        parts = []
        group_note = _groups_note(groups, values.get("DoiTuong_MucDoKhuyetTat"), required_group)
        if group_note:
            # Chỉ dẫn nguồn khi thật sự đọc được mục I.7; không có tờ khai thì chỉ ghi điều kiện của thủ tục.
            parts.append(group_note + (" (Tờ khai Mẫu số 04 mục I.7)." if groups else "."))
        current = _text(values.get("DoiTuong_NoiOHienNay"))
        if current and not _same_place(current, residence):
            parts.append(f"Nơi ở hiện nay: {current.rstrip('.')}.")
        add("data[ghiChu]", " ".join(parts))

    return out, warnings
