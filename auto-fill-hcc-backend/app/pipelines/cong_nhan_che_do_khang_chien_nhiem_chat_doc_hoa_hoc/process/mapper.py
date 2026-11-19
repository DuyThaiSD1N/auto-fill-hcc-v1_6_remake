"""Map chủ hồ sơ (người hoạt động kháng chiến), người nộp và Bản khai Mẫu 09 sang Form.io cổng Bộ Nội vụ (1.010816).

Bước 1 có HAI form Form.io trên cùng trang: form Người nộp / Chủ hồ sơ và eForm Bản khai. eForm dùng lại key của khối
Người nộp (data[fullname], data[birthday], data[gender], data[identityNumber], data[identityDate], data[province],
data[address], data[phoneNumber]) → khối Người nộp phát occurrence 0, Bản khai occurrence 1. Ô riêng của Bản khai:
data[identityAgency] (danh mục nơi cấp), data[village] (xã quê quán), data[province1]/[village1]/[address1] (thường trú),
data[tinhTrang], datagrid data[quaTrinh][i][thoiGian|coQuan|diaBan], data[conDe][i][hoTen|namSinh|giayTo|tinhTrang].

Người nộp theo formContext (tài khoản): khớp người hoạt động kháng chiến → tự nộp (tích "Người nộp hồ sơ là chủ hồ sơ");
khác → chỉ lấy CCCD khớp tài khoản (NguoiNop_*). ⚑ Cài đặt "Lấy người nộp theo tờ khai"
(`options.submitterMode="owner_as_submitter"`, Auto Fill + trợ lý): bỏ mốc tài khoản, người nộp = người hoạt động kháng
chiến; khác tài khoản thì Họ tên + CCCD khối Người nộp phát kèm enableInput (cổng khoá theo VNeID), Bản khai không có
ngày sinh thì xoá ngày sinh của tài khoản.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared import fold as _fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import ISSUER_CUC
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import _person_matches
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process.schema import (
    MAX_CON_DE_ROWS,
    MAX_HO_SO_ROWS,
    MAX_QUA_TRINH_ROWS,
    UI_COMP_BY_NAME,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _phone,
    _text,
)

BAN_KHAI = "Bản khai theo Mẫu số 09 Phụ lục I Nghị định số 131/2021/NĐ-CP"
OWNER_AS_SUBMITTER = "owner_as_submitter"
_ADMIN_PREFIX_RE = re.compile(r"^(?:phường|xã|thị trấn|đặc khu|p\.|x\.)\s*", re.IGNORECASE)
# Dòng in sẵn của bảng quá trình ("Từ tháng ... năm ... đến tháng ... năm ...") không phải dữ liệu.
_PLACEHOLDER_RE = re.compile(r"^[\s.…]*(?:từ\s+tháng[\s.…]*năm[\s.…]*đến\s+tháng[\s.…]*năm[\s.…]*)?[\s.…]*$",
                             re.IGNORECASE)


def _issuer_name(value: Any) -> str | None:
    """normalize_issuer + chữ viết tay rơi chữ "quản lý" ("Cục Csát QLý trật tự xã hội Bộ CA")."""
    text = _issuer(value)
    if text and _fold(text).startswith("cuc") and re.search(r"\b(trat|trai|chat) tu xa hoi\b", _fold(text)):
        return ISSUER_CUC
    return text


def _bare_commune(value: Any) -> str:
    return _fold(_ADMIN_PREFIX_RE.sub("", _text(value) or ""))


def _place(value: Any, *, keep_old_commune: bool = False) -> dict | None:
    """Địa chỉ đã remap sang đơn vị hiện hành. ``keep_old_commune``: quê quán chỉ ghi tới xã cũ đã sáp nhập (vd "Hòa X,
    quận Y") → ô số nhà, đường (bắt buộc) giữ tên xã cũ để không mất thông tin."""
    area = _area(value)
    if not area:
        return None
    if keep_old_commune and not _text(area.get("diaChi")) and isinstance(value, dict):
        old = _text(value.get("xa") or value.get("phuong"))
        if old and area.get("xa") and _bare_commune(old) != _bare_commune(area.get("xa")):
            area = {**area, "diaChi": _ADMIN_PREFIX_RE.sub("", old).strip()}
    return area


def _person(values: dict, prefix: str) -> dict:
    identity = _identity(values.get(f"{prefix}SoDinhDanh"))
    return {
        "name": _text(values.get(f"{prefix}HoTen")),
        "identity": identity,
        "birthday": _date(values.get(f"{prefix}NgaySinh")),
        "gender": _gender(values.get(f"{prefix}GioiTinh")) or _gender_from_identity(identity),
        "id_date": _date(values.get(f"{prefix}NgayCap")),
        "issuer": _issuer_name(values.get(f"{prefix}NoiCap")),
        "phone": _phone(values.get(f"{prefix}DienThoai")),
    }


def _rows(value: Any) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _cell(item: dict, *keys: str) -> str | None:
    for key in keys:
        text = _text(item.get(key))
        if text:
            return text
    return None


def _qua_trinh(value: Any) -> list[dict]:
    out = []
    for item in _rows(value):
        row = {"thoiGian": _cell(item, "thoiGian", "thoi_gian", "time"),
               "coQuan": _cell(item, "coQuan", "coQuanDonVi", "donVi"),
               "diaBan": _cell(item, "diaBan", "diaBanHoatDong")}
        if row["thoiGian"] and _PLACEHOLDER_RE.match(row["thoiGian"]) and not row["coQuan"] and not row["diaBan"]:
            continue
        if any(row.values()):
            out.append(row)
    return out


def _con_de(value: Any) -> list[dict]:
    out = []
    for item in _rows(value):
        row = {"hoTen": _cell(item, "hoTen", "hoVaTen"), "namSinh": _cell(item, "namSinh", "ngaySinh"),
               "giayTo": _cell(item, "giayTo", "soGiayTo", "soCccd"), "tinhTrang": _cell(item, "tinhTrang")}
        if row["hoTen"]:
            out.append(row)
    return out


def _papers(value: Any) -> list[tuple[str, str]]:
    """(tên giấy, loại bản) — Bản khai Mẫu 09 luôn đứng đầu, không lặp."""
    out: list[tuple[str, str]] = [(BAN_KHAI, "Bản chính")]
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            name, kind = _cell(item, "tenGiayTo", "ten", "name"), _cell(item, "loaiBan", "loai")
        else:
            name, kind = _text(item), None
        if not name or ("ban khai" in _fold(name) and ("09" in name or "mau" in _fold(name))):
            continue
        kind = "Bản sao" if kind and "sao" in _fold(kind) else "Bản chính"
        if all(_fold(name) != _fold(n) for n, _ in out):
            out.append((name, kind))
    return out


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence: int | None = None, extra: dict | None = None) -> None:
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []) or name not in UI_COMP_BY_NAME:
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value, **(extra or {})}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(key)

    def clear(name: str, *, occurrence: int | None = None) -> None:
        # Cổng đổ sẵn giá trị của tài khoản VNeID, không phải của người theo tờ khai → xoá trắng + tô đỏ.
        key = (name, occurrence)
        if key in seen or name not in UI_COMP_BY_NAME:
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True, "markEmpty": True}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(key)

    def add_area(province: str, commune: str, detail: str, area: dict | None, *, occurrence: int | None = None):
        if not area:
            return
        add(province, province_label(area.get("tinh")), occurrence=occurrence)
        add(commune, _text(area.get("xa")), occurrence=occurrence)
        add(detail, _text(area.get("diaChi")), occurrence=occurrence)

    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)
    theo_to_khai = str((options or {}).get("submitterMode") or "") == OWNER_AS_SUBMITTER

    owner = _person(values, "ChuHoSo_")
    owner_home = _place(values.get("ChuHoSo_NoiThuongTru"))
    owner_origin = _place(values.get("ChuHoSo_QueQuan"), keep_old_commune=True)
    submitter = _person(values, "NguoiNop_")

    def matches_account(person: dict) -> bool:
        return has_ctx and bool(person["name"] or person["identity"]) and _person_matches(
            person["name"], person["identity"], ctx_name, ctx_identity)

    owner_matches_account = matches_account(owner)
    # Theo tờ khai: người nộp luôn là người hoạt động kháng chiến (cần đọc được người đó), không xét CCCD khác.
    owner_submits = owner_matches_account or (theo_to_khai and bool(owner["name"] or owner["identity"]))
    nop, nop_home = (owner, owner_home) if owner_submits else (
        (submitter, _place(values.get("NguoiNop_NoiCuTru"))) if not theo_to_khai and matches_account(submitter)
        else (None, None))

    # --- Phần I: người nộp (cổng khoá họ tên / ngày sinh / CCCD theo tài khoản) ---
    # Ô tích đứng trước (FE sắp lên đầu): tích khi người hoạt động kháng chiến tự nộp.
    if has_ctx or theo_to_khai:
        add("data[isOwnerDossierCheck]", owner_submits)
    if owner_submits and not owner_matches_account:
        # Theo tờ khai, người khai khác tài khoản → mở khoá Họ tên + CCCD và ghi đè; ngày sinh tài khoản thì xoá nếu
        # Bản khai không có.
        unlock = {"enableInput": True}
        add("data[fullname]", owner["name"], occurrence=0, extra=unlock)
        add("data[identityNumber]", owner["identity"], occurrence=0, extra=unlock)
        if owner["birthday"]:
            add("data[birthday]", owner["birthday"], occurrence=0, extra=unlock)
        else:
            clear("data[birthday]", occurrence=0)
        if has_ctx:
            warnings.append(f"Đang bật \"Lấy người nộp theo tờ khai\": phần người nộp ghi theo người hoạt động kháng "
                            f"chiến ({owner['name'] or owner['identity']}), khác tài khoản đăng nhập "
                            f"({ctx_name or ctx_identity}) — kiểm tra lại trước khi nộp.")
    if nop:
        add("data[gender]", nop["gender"], occurrence=0)
        add("data[identityDate]", nop["id_date"], occurrence=0)
        add("data[idIssuePlace]", nop["issuer"])
        add_area("data[province]", "data[district]", "data[address]", nop_home, occurrence=0)
        add("data[phoneNumber]", nop["phone"], occurrence=0)
    if not theo_to_khai:
        add("data[gender]", _gender_from_identity(ctx_identity), occurrence=0)

    # --- Phần II: chủ hồ sơ = người hoạt động kháng chiến ---
    add("data[chonDoiTuong1]", "Cá nhân")
    add("data[ownerFullname]", owner["name"])
    add("data[ownerBirthday]", owner["birthday"])
    add("data[ownerGender]", owner["gender"])
    add("data[ownerIdentityNumber]", owner["identity"])
    add("data[ownerIdentityDate]", owner["id_date"])
    add("data[ownerIdIssuePlace]", owner["issuer"])
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", owner_home)
    add("data[ownerPhoneNumber]", owner["phone"])
    add("data[ownerNation]", "Việt Nam")

    # --- Phần III: Hồ sơ kèm theo gồm ---
    papers = _papers(values.get("HoSoDinhKem"))
    for index, (name, kind) in enumerate(papers[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{index}][textField1]", name)
        add(f"data[hoSoDinhKem][{index}][textField2]", kind)

    # --- Phần IV: Bản khai Mẫu 09 Mục 1 (occurrence 1 cho key trùng khối Người nộp) ---
    add("data[fullname]", owner["name"], occurrence=1)
    add("data[identityNumber]", owner["identity"], occurrence=1)
    add("data[birthday]", owner["birthday"], occurrence=1)
    add("data[identityDate]", owner["id_date"], occurrence=1)
    add("data[gender]", owner["gender"], occurrence=1)
    add("data[identityAgency]", owner["issuer"])
    # Quê quán: Tỉnh / số nhà trùng key khối Người nộp (occurrence 1), ô xã data[village] chỉ có ở Bản khai.
    if owner_origin:
        add("data[province]", province_label(owner_origin.get("tinh")), occurrence=1)
        add("data[village]", _text(owner_origin.get("xa")))
        add("data[address]", _text(owner_origin.get("diaChi")), occurrence=1)
    add_area("data[province1]", "data[village1]", "data[address1]", owner_home)
    add("data[phoneNumber]", owner["phone"], occurrence=1)
    tinh_trang = _text(values.get("HDKC_TinhTrangSucKhoe"))
    add("data[tinhTrang]", tinh_trang)
    qua_trinh = _qua_trinh(values.get("HDKC_QuaTrinh"))
    for index, row in enumerate(qua_trinh[:MAX_QUA_TRINH_ROWS]):
        for col, value in row.items():
            add(f"data[quaTrinh][{index}][{col}]", value)
    con_de = _con_de(values.get("HDKC_ConDe"))
    for index, row in enumerate(con_de[:MAX_CON_DE_ROWS]):
        for col, value in row.items():
            add(f"data[conDe][{index}][{col}]", value)

    # --- Cảnh báo ---
    if not owner["name"] or not owner["identity"]:
        warnings.append("Chưa đọc được họ tên / số CCCD người hoạt động kháng chiến ở Mục 1 Bản khai Mẫu 09 — vui lòng "
                        "nhập tay Phần chủ hồ sơ và Bản khai.")
    if not owner_home:
        warnings.append("Chưa đọc được nơi thường trú của người hoạt động kháng chiến — vui lòng chọn Tỉnh/TP, Phường/Xã "
                        "và nhập địa chỉ ở Phần chủ hồ sơ và Bản khai.")
    if not owner_origin or not owner_origin.get("xa"):
        warnings.append("Chưa đọc đủ quê quán (tới cấp xã) của người hoạt động kháng chiến — vui lòng chọn ở Bản khai.")
    if not owner["phone"]:
        warnings.append("Bản khai không ghi số điện thoại — ô Điện thoại (bắt buộc) vui lòng nhập tay.")
    if not tinh_trang:
        warnings.append("Chưa đọc được \"Tình trạng bệnh tật, sức khỏe hiện nay\" ở Bản khai — vui lòng nhập tay.")
    if not qua_trinh:
        warnings.append("Chưa đọc được bảng quá trình hoạt động kháng chiến ở vùng quân đội Mỹ sử dụng chất độc hóa học "
                        "— vui lòng nhập tay.")
    elif len(qua_trinh) > MAX_QUA_TRINH_ROWS:
        warnings.append(f"Bảng quá trình hoạt động có {len(qua_trinh)} dòng, chỉ điền {MAX_QUA_TRINH_ROWS} dòng đầu.")
    if theo_to_khai:
        if not nop:
            warnings.append("Bật \"Lấy người nộp theo tờ khai\" nhưng chưa đọc được người hoạt động kháng chiến ở Bản khai "
                            "— chưa điền phần người nộp, vui lòng nhập tay.")
    elif not has_ctx:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — chưa điền phần người nộp, vui lòng kiểm tra.")
    elif not nop:
        warnings.append("Người nộp khác người hoạt động kháng chiến và hồ sơ không có CCCD của người nộp — vui lòng tự "
                        "nhập ngày cấp, nơi cấp, địa chỉ, số điện thoại của người nộp.")
    return out, warnings
