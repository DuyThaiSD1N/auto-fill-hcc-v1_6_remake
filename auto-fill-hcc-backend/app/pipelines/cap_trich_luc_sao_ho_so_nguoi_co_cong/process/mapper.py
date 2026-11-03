"""Map fact Đơn đề nghị + CCCD sang field Form.io của thủ tục 1.010828.

Theo "Mapping - Cấp trích lục hồ sơ NCC - Bộ Nội vụ.xlsx":
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] / data[chonDoiTuong] cổng khoá theo tài
  khoản VNeID. Hai chế độ (cài đặt "Lấy người nộp theo tờ khai" → `options.submitterMode`):
  * BẬT (`owner_as_submitter`): người nộp = người làm đơn, bỏ mốc tài khoản; ghi cả ô khoá (họ tên, số CCCD kèm
    enableInput; thiếu ngày sinh đủ thì xoá ngày sinh tài khoản cổng đổ sẵn), tích "Người nộp hồ sơ là chủ hồ sơ".
  * TẮT: mốc tài khoản (formContext) quyết định. Khớp người làm đơn → tự nộp, điền phần sửa được + tích. Khác →
    nộp thay, bỏ tích; ô khoá giữ theo tài khoản, phần sửa được lấy từ CCCD của người đăng nhập (NguoiNop_*) nếu
    hồ sơ có, không thì để trống. Thiếu mốc → coi như tự nộp.
- Phần II chủ hồ sơ = người làm đơn.
- Nguồn nhân thân: CCCD → Đơn (ngày cấp, nơi cấp CCCD và Đơn hay lệch nhau — lấy CCCD). SĐT chỉ có trên Đơn.
- Bảng "Hồ sơ kèm theo gồm": mỗi giấy tờ một dòng (Đơn — Bản chính, CCCD — Bản sao).
"""

from __future__ import annotations

from app.pipelines._shared.area_remap import province_label
from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process.schema import (
    MAX_HO_SO_ROWS,
    UI_COMP_BY_NAME,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _person_matches,
    _phone,
    _same_name,
    _text,
)

DON_TITLE = "Đơn đề nghị cấp trích lục hoặc sao hồ sơ người có công"
CCCD_TITLE = "Căn cước công dân"


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _don_title(value) -> str | None:
    """"ĐƠN ĐỀ NGHỊ Di chuyển hồ sơ …" → "Đơn đề nghị di chuyển hồ sơ …" cho ô Tên giấy tờ."""
    text = _text(value)
    if not text:
        return None
    if text == text.upper():
        text = text.lower()
    if _fold(text).startswith("don de nghi"):
        rest = text[len("đơn đề nghị"):].strip()
        text = f"Đơn đề nghị {rest[:1].lower()}{rest[1:]}".strip()
    return text[0].upper() + text[1:]


def _is_di_chuyen(title: str | None) -> bool:
    folded = _fold(title)
    return "di chuyen" in folded and "trich luc" not in folded and " sao " not in f" {folded} "


def _submitter_facts(values: dict, ctx_name: str | None, ctx_identity: str | None, cccd_same: bool) -> dict | None:
    """Nhân thân NGƯỜI NỘP (nộp thay) từ giấy tờ của chính người đăng nhập: NguoiNop_*, hoặc thẻ LLM lỡ xếp vào
    Person1_* (khác người làm đơn). Chỉ nhận khi khớp tài khoản — không khớp thì không đoán."""
    prefixes = ["NguoiNop_"] + ([] if cccd_same else ["Person1_"])
    for prefix in prefixes:
        name = _text(values.get(f"{prefix}HoTen"))
        identity = _identity(values.get(f"{prefix}SoDinhDanh"))
        if not (name or identity) or not _person_matches(name, identity, ctx_name, ctx_identity):
            continue
        issuer = values.get(f"{prefix}NoiCap")
        area = _area(values.get(f"{prefix}NoiCuTru"))
        return {
            "gender": _gender(values.get(f"{prefix}GioiTinh")),
            "issue_date": _date(values.get(f"{prefix}NgayCap")),
            "issuer": _issuer(issuer) or _text(issuer),
            "residence": area if area and (area.get("tinh") or area.get("xa")) else None,
        }
    return None


def _street_or_area(area: dict | None) -> str | None:
    """Ô "Địa chỉ chi tiết" bắt buộc; giấy tờ chỉ ghi tới xã thì nhập lại "xã, tỉnh"."""
    if not area:
        return None
    detail = _text(area.get("diaChi"))
    if detail:
        return detail
    parts = [_text(area.get("xa")), province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, **extra) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value, **extra})
        seen.add(name)

    def add_area(province: str, commune: str, address: str, area: dict | None) -> None:
        if not area:
            return
        add(province, province_label(area.get("tinh")))
        add(commune, _text(area.get("xa")))
        add(address, _street_or_area(area))

    # --- Mốc tài khoản đăng nhập VNeID ---
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    # --- CCCD chỉ dùng khi đúng người làm đơn ---
    don_name = _text(values.get("Don_HoTen"))
    don_identity = _identity(values.get("Don_SoDinhDanh"))
    cccd_name = _text(values.get("Person1_HoTen"))
    cccd_identity = _identity(values.get("Person1_SoDinhDanh"))
    cccd_same = True
    if cccd_identity and don_identity:
        cccd_same = cccd_identity == don_identity
    elif cccd_name and don_name:
        cccd_same = _same_name(cccd_name, don_name)
    if not cccd_same and not (has_ctx and _person_matches(cccd_name, cccd_identity, ctx_name, ctx_identity)):
        warnings.append(
            f"CCCD trong hồ sơ ({cccd_name or cccd_identity}) không phải của người làm đơn "
            f"({don_name or don_identity}) — đã điền theo Đơn, cần đối chiếu lại."
        )

    def cccd(key: str):
        return values.get(key) if cccd_same else None

    # --- Nhân thân người làm đơn: CCCD → Đơn ---
    name = _text(_pick(cccd("Person1_HoTen"), values.get("Don_HoTen")))
    identity = _identity(_pick(cccd("Person1_SoDinhDanh"), values.get("Don_SoDinhDanh")))
    birthday = _date(_pick(cccd("Person1_NgaySinh"), values.get("Don_NgaySinh")))
    gender = (
        _gender(cccd("Person1_GioiTinh")) or _gender(values.get("Don_GioiTinh"))
        or _gender_from_identity(identity)
    )
    cccd_issue_date = _date(cccd("Person1_NgayCap"))
    don_issue_date = _date(values.get("Don_NgayCap"))
    issue_date = cccd_issue_date or don_issue_date
    # Nơi cấp đi cùng ngày cấp: đã lấy ngày cấp CCCD thì lấy cơ quan in trên thẻ, không thì nơi cấp ghi trên Đơn.
    if cccd_issue_date or not don_issue_date:
        issuer_raw = _pick(cccd("Person1_NoiCap"), values.get("Don_NoiCap"))
    else:
        issuer_raw = _pick(values.get("Don_NoiCap"), cccd("Person1_NoiCap"))
    issuer = _issuer(issuer_raw) or _text(issuer_raw)
    cccd_area = _area(cccd("Person1_NoiCuTru"))
    don_area = _area(values.get("Don_NoiThuongTru"))
    residence = cccd_area if cccd_area and cccd_area.get("tinh") and cccd_area.get("xa") else (don_area or cccd_area)
    if residence is cccd_area and don_area and _fold(don_area.get("xa")) == _fold(cccd_area.get("xa")):
        # Mặt sau thẻ scan hay mất số nhà ("Phước Long" vs Đơn "12 đường Phước Long") → cùng xã thì lấy chi tiết
        # dài hơn của Đơn khi nó chứa chi tiết trên thẻ.
        cccd_detail, don_detail = _fold(cccd_area.get("diaChi")), _fold(don_area.get("diaChi"))
        if cccd_detail in don_detail and len(don_detail) > len(cccd_detail):
            residence = {**cccd_area, "diaChi": don_area.get("diaChi")}
    phone = _phone(values.get("Don_DienThoai"))

    if not name or not identity:
        warnings.append("Thiếu họ tên hoặc số CCCD của người làm đơn (Đơn đề nghị/CCCD).")
    if cccd_issue_date and don_issue_date and cccd_issue_date != don_issue_date:
        warnings.append(
            f"Ngày cấp CCCD trên thẻ ({cccd_issue_date}) khác trên Đơn ({don_issue_date}) — đã lấy theo thẻ, cần "
            "đối chiếu lại."
        )

    self_submit = owner_mode or not has_ctx or _person_matches(name, identity, ctx_name, ctx_identity)

    # --- Phần I: người nộp ---
    if self_submit:
        if owner_mode:
            # Ô khoá theo tài khoản VNeID: người làm đơn có thể là người khác tài khoản nên kèm enableInput để
            # extension bỏ disabled trước khi ghi (cán bộ còn sửa được khi OCR sai).
            add("data[chonDoiTuong]", "Cá nhân")
            add("data[fullname]", name, enableInput=True)
            if birthday:
                add("data[birthday]", birthday)
            else:
                # Cổng đổ sẵn ngày sinh của tài khoản → không có ngày đủ thì xoá + đánh dấu, không để ngày người khác.
                out.append({"name": "data[birthday]", "comp": UI_COMP_BY_NAME["data[birthday]"], "value": "",
                            "clear": True, "markEmpty": True})
                seen.add("data[birthday]")
            add("data[identityNumber]", identity, enableInput=True)
            if has_ctx and not _person_matches(name, identity, ctx_name, ctx_identity):
                warnings.append(
                    f"Đang bật \"Lấy người nộp theo tờ khai\": 'Thông tin người nộp hồ sơ' ghi theo người làm đơn "
                    f"({name or identity}), khác tài khoản đăng nhập ({ctx_name or ctx_identity}) — kiểm tra lại "
                    "trước khi nộp."
                )
        add("data[gender]", gender)
        add("data[identityDate]", issue_date)
        add("data[idIssuePlace]", issuer)
        add_area("data[province]", "data[district]", "data[address]", residence)
        add("data[phoneNumber]", phone)
        add("data[isOwnerDossierCheck]", True)
    else:
        # Nộp thay: ô khoá giữ theo tài khoản; phần sửa được lấy từ giấy tờ của chính người đăng nhập.
        add("data[isOwnerDossierCheck]", False)
        submitter = _submitter_facts(values, ctx_name, ctx_identity, cccd_same)
        if submitter:
            add("data[gender]", submitter["gender"] or _gender_from_identity(ctx_identity))
            add("data[identityDate]", submitter["issue_date"])
            add("data[idIssuePlace]", submitter["issuer"])
            add_area("data[province]", "data[district]", "data[address]", submitter["residence"])
        else:
            add("data[gender]", _gender_from_identity(ctx_identity))
        missing = [label for label, ok in (
            ("ngày cấp", submitter and submitter["issue_date"]),
            ("nơi cấp", submitter and submitter["issuer"]),
            ("địa chỉ", submitter and submitter["residence"]),
        ) if not ok]
        warnings.append(
            f"Người nộp (tài khoản đăng nhập: {ctx_name or ctx_identity}) khác người làm đơn ({name or identity}) — "
            "nộp thay, bỏ tích 'Người nộp hồ sơ là chủ hồ sơ'. "
            + (f"Hồ sơ không có đủ giấy tờ của người nộp: tự nhập {', '.join(missing)} và SĐT ở 'Thông tin người "
               "nộp hồ sơ'." if missing else "Tự nhập SĐT người nộp ở 'Thông tin người nộp hồ sơ'.")
        )

    # --- Phần II: chủ hồ sơ = người làm đơn ---
    add("data[chonDoiTuong1]", "Cá nhân")
    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", gender)
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", issue_date)
    add("data[ownerIdIssuePlace]", issuer)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerNation]", "Việt Nam" if name or identity else None)
    if not phone:
        warnings.append("Chưa đọc được số điện thoại trên Đơn — ô SĐT bắt buộc, vui lòng tự nhập.")

    # --- Bảng "Hồ sơ kèm theo gồm" ---
    title = _don_title(values.get("Don_TieuDe"))
    rows: list[tuple[str, str]] = []
    if title or don_name or don_identity:
        rows.append((title or DON_TITLE, "Bản chính"))
    if cccd_same and (cccd_name or cccd_identity):
        rows.append((CCCD_TITLE, "Bản sao"))
    for idx, (row_title, kind) in enumerate(rows[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{idx}][textField1]", row_title)
        add(f"data[hoSoDinhKem][{idx}][textField2]", kind)

    if _is_di_chuyen(title):
        warnings.append(
            f"Đơn trong hồ sơ là '{title}', không phải đơn đề nghị cấp trích lục hoặc sao hồ sơ người có công — "
            "cần xác nhận đúng thủ tục trước khi nộp."
        )
    return out, warnings
