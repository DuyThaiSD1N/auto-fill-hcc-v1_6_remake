"""Map người nhận trợ cấp, người nộp và cựu chiến binh đã chết sang Form.io cổng Bộ Nội vụ (2.002307).

Bước 1 có HAI form Form.io trên cùng trang: form Người nộp / Chủ hồ sơ và eForm mẫu khai (khung người có công). eForm
dùng lại key của khối Người nộp:
- data[fullname] / data[birthday] / data[gender] → khối "Thông tin về người có công từ trần" (= cựu chiến binh), occ 1;
- data[province] / data[district] / data[address] → trú quán "người nhận mai táng phí", occ 1.
Khối Người nộp luôn occurrence 0. Ô riêng eForm: nguyên quán / trú quán cựu chiến binh (province2-3, district2-3,
address2-3), data[ttncc_*], khối người nhận mai táng phí (fullname1, birthday1, gender1, province1/district1/address1 =
nguyên quán, data[ttnn_QuanHe]). Khối trợ cấp một lần (…2, …4, …5, nntc_QuanHe), bảng thân nhân tnncc_Bang/tnncc_Bang2,
số sổ / tỷ lệ suy giảm / mức trợ cấp không áp dụng cho cựu chiến binh → không phát.

Chủ hồ sơ = cá nhân nhận trợ cấp mai táng (Mục 2a Bản khai). Người nộp theo formContext (tài khoản): khớp người nhận →
tự nộp (tích "Người nộp hồ sơ là chủ hồ sơ"); khác → chỉ lấy CCCD khớp tài khoản (NguoiNop_*). ⚑ Cài đặt "Lấy người nộp
theo tờ khai" (`options.submitterMode="owner_as_submitter"`): người nộp = người nhận trợ cấp; khác tài khoản thì Họ tên +
CCCD khối Người nộp phát kèm enableInput, Bản khai không có ngày sinh thì xoá ngày sinh của tài khoản.

Giới tính: cổng chọn sẵn "Nữ" ở khối Người nộp / Chủ hồ sơ → luôn phát giới tính đọc được (hoặc suy từ số định danh).
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared import fold as _fold
from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import _person_matches
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process.mapper import _issuer_name
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _by_name,
    _commune_label,
    _date,
    _gender,
    _gender_from_identity,
    _identity,
    _phone,
    _text,
)
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.process.schema import (
    MAX_HO_SO_ROWS,
    UI_COMP_BY_NAME,
)

BAN_KHAI = ("Bản khai đề nghị giải quyết chế độ trợ cấp mai táng đối với cựu chiến binh đã chết (Mẫu số 01 Thông tư "
            "số 21/2026/TT-BNV)")
CUU_CHIEN_BINH = "Cựu chiến binh"
OWNER_AS_SUBMITTER = "owner_as_submitter"
_ADMIN_PREFIX_RE = re.compile(r"^(?:phường|xã|thị trấn|đặc khu|p\.|x\.)\s*", re.IGNORECASE)
_UBND_RE = re.compile(r"\bUBND\b", re.IGNORECASE)
_DISTRICT_RE = re.compile(r"^(?:huyện|quận|thị xã|thành phố|tp\.?)\s", re.IGNORECASE)


def _bare_commune(value: Any) -> str:
    return _fold(_ADMIN_PREFIX_RE.sub("", _text(value) or ""))


def _place(value: Any, *, keep_old_commune: bool = False) -> dict | None:
    """Địa chỉ đã remap sang đơn vị hiện hành. Đọc cả khoá huyện cũ (xã trùng tên ở nhiều huyện, vd "Minh Quang" của Thái
    Bình) và chiTietDuoiXa. ``keep_old_commune``: quê quán chỉ ghi tới xã cũ đã sáp nhập → ô "Số nhà, đường" (bắt buộc)
    giữ tên xã cũ để không mất thông tin."""
    if isinstance(value, str):
        # "thôn, xã, [huyện,] tỉnh" — cụm áp chót có tiền tố cấp huyện thì là huyện cũ.
        parts = [p.strip(" .") for p in re.split(r"[,;\n]+", value) if p.strip(" .")]
        if not parts:
            return None
        huyen = parts.pop(-2) if len(parts) >= 3 and _DISTRICT_RE.match(parts[-2]) else ""
        value = {"tinh": parts[-1], "huyen": huyen, "xa": parts[-2] if len(parts) >= 2 else "",
                 "diaChi": ", ".join(parts[:-2])}
    if not isinstance(value, dict):
        return None
    old_commune = _text(value.get("xa") or value.get("phuong"))
    area = {
        "quocGia": _text(value.get("quocGia")) or "Việt Nam",
        "tinh": _text(value.get("tinh") or value.get("tinhThanh")) or "",
        "xa": _commune_label(old_commune) or "",
        "diaChi": _text(value.get("diaChi") or value.get("chiTietDuoiXa") or value.get("chiTiet")) or "",
    }
    if not any(area[k] for k in ("tinh", "xa", "diaChi")):
        return None
    huyen = _text(value.get("huyen") or value.get("quanHuyen"))
    remapped = remap_area({**area, "huyen": huyen} if huyen else dict(area), allow_diachi_fallback=True) or area
    if keep_old_commune and not _text(remapped.get("diaChi")) and old_commune and remapped.get("xa") \
            and _bare_commune(old_commune) != _bare_commune(remapped.get("xa")):
        remapped = {**remapped, "diaChi": _commune_label(old_commune) + " cũ"}
    return remapped


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


def _relation(value: Any) -> str | None:
    """"Cháu nội (con trai của …), là người trực tiếp tổ chức mai táng" → "Cháu nội"."""
    text = _text(value)
    if not text:
        return None
    short = re.split(r"\s*[(,;–-]\s*", text, maxsplit=1)[0].strip()
    return (short[:1].upper() + short[1:]) if short else text


def _agency(value: Any) -> str | None:
    text = _text(value)
    return _UBND_RE.sub("Ủy ban nhân dân", text) if text else None


def _death_paper(kind: Any, number: Any) -> str | None:
    """Ô "Giấy chứng tử": "<loại> số <số>" (vd "Trích lục khai tử số 152/TLKT")."""
    number = _text(number)
    if not number:
        return None
    if _fold(number).startswith(("trich luc", "giay")):  # LLM đã ghi đủ loại giấy
        return number
    number = re.sub(r"^số\s*[:.]?\s*", "", number, flags=re.IGNORECASE).strip()
    kind = _text(kind) or ("Trích lục khai tử" if "tlkt" in _fold(number) else "Giấy chứng tử")
    return f"{kind} số {number}"


def _papers(value: Any) -> list[tuple[str, str]]:
    """(tên giấy, loại bản) — Bản khai Mẫu 01 luôn đứng đầu, không lặp, không đưa CCCD."""
    out: list[tuple[str, str]] = [(BAN_KHAI, "Bản chính")]
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            name = _text(item.get("tenGiayTo") or item.get("ten") or item.get("name"))
            kind = _text(item.get("loaiBan") or item.get("loai"))
        else:
            name, kind = _text(item), None
        folded = _fold(name)
        if not name or folded.startswith("ban khai") or any(k in folded for k in ("can cuoc", "cccd", "cmnd",
                                                                                  "chung minh nhan dan")):
            continue
        kind = "Bản sao" if (kind and "sao" in _fold(kind)) or folded.startswith("ban sao") else "Bản chính"
        if all(folded != _fold(n) for n, _ in out):
            out.append((name, kind))
    return out


def _ghi_chu(ccb: dict, death_day: str | None, recipient: dict, relation: str | None) -> str | None:
    if not ccb["name"]:
        return None
    detail = ", ".join(p for p in (f"sinh {ccb['birthday']}" if ccb["birthday"] else "",
                                   f"chết ngày {death_day}" if death_day else "") if p)
    text = f"Đề nghị giải quyết chế độ trợ cấp mai táng đối với cựu chiến binh {ccb['name']}"
    if detail:
        text += f" ({detail})"
    if recipient["name"]:
        text += f"; người nhận trợ cấp: {recipient['name']}" + (f" – {relation.lower()}" if relation else "")
    return text


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
    relation = _relation(values.get("ChuHoSo_QuanHe"))
    submitter = _person(values, "NguoiNop_")
    ccb = _person(values, "CCB_")
    ccb_origin = _place(values.get("CCB_QueQuan"), keep_old_commune=True)
    ccb_home = _place(values.get("CCB_NoiThuongTru"))
    death_day = _date(values.get("CCB_NgayChet"))
    organization = _text(values.get("ToChucNhan_Ten"))
    if organization and _fold(organization).startswith("khong"):
        organization = None
    has_owner = bool(owner["name"] or owner["identity"])

    def matches_account(person: dict) -> bool:
        return has_ctx and bool(person["name"] or person["identity"]) and _person_matches(
            person["name"], person["identity"], ctx_name, ctx_identity)

    owner_matches_account = matches_account(owner)
    # Theo tờ khai: người nộp luôn là người nhận trợ cấp (cần đọc được người đó), không xét CCCD khác.
    owner_submits = owner_matches_account or (theo_to_khai and has_owner)
    nop, nop_home = (owner, owner_home) if owner_submits else (
        (submitter, _place(values.get("NguoiNop_NoiCuTru"))) if not theo_to_khai and matches_account(submitter)
        else (None, None))

    # --- Phần I: người nộp (occurrence 0; cổng khoá họ tên / CCCD theo tài khoản) ---
    if has_ctx or theo_to_khai:
        add("data[isOwnerDossierCheck]", owner_submits)
    if owner_submits and not owner_matches_account:
        # Theo tờ khai, người nhận trợ cấp khác tài khoản → mở khoá Họ tên + CCCD và ghi đè; ngày sinh tài khoản thì
        # xoá nếu giấy tờ không có.
        unlock = {"enableInput": True}
        add("data[fullname]", owner["name"], occurrence=0, extra=unlock)
        add("data[identityNumber]", owner["identity"], occurrence=0, extra=unlock)
        if owner["birthday"]:
            add("data[birthday]", owner["birthday"], occurrence=0, extra=unlock)
        else:
            clear("data[birthday]", occurrence=0)
        if has_ctx:
            warnings.append(f"Đang bật \"Lấy người nộp theo tờ khai\": phần người nộp ghi theo người nhận trợ cấp mai "
                            f"táng ({owner['name'] or owner['identity']}), khác tài khoản đăng nhập "
                            f"({ctx_name or ctx_identity}) — kiểm tra lại trước khi nộp.")
    if nop:
        add("data[gender]", nop["gender"], occurrence=0)
        add("data[identityDate]", nop["id_date"])
        add("data[idIssuePlace]", nop["issuer"])
        add_area("data[province]", "data[district]", "data[address]", nop_home, occurrence=0)
        add("data[phoneNumber]", nop["phone"])
    if not theo_to_khai:
        # Cổng chọn sẵn "Nữ": không đọc được người nộp vẫn sửa theo chữ số giới tính trong CCCD tài khoản.
        add("data[gender]", _gender_from_identity(ctx_identity), occurrence=0)

    # --- Phần II: chủ hồ sơ = cá nhân nhận trợ cấp mai táng ---
    if has_owner:
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
    add("data[ghiChu]", _ghi_chu(ccb, death_day, owner, relation))

    # --- Hồ sơ kèm theo gồm ---
    for index, (name, kind) in enumerate(_papers(values.get("HoSoDinhKem"))[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{index}][textField1]", name)
        add(f"data[hoSoDinhKem][{index}][textField2]", kind)

    # --- Phần III: người có công từ trần = cựu chiến binh (key trùng khối Người nộp → occurrence 1) ---
    add("data[fullname]", ccb["name"], occurrence=1)
    add("data[birthday]", ccb["birthday"], occurrence=1)
    add("data[gender]", ccb["gender"], occurrence=1)
    add_area("data[province2]", "data[district2]", "data[address2]", ccb_origin)
    add_area("data[province3]", "data[district3]", "data[address3]", ccb_home)
    add("data[ttncc_DoiTuong]", _text(values.get("CCB_DoiTuong")) or CUU_CHIEN_BINH)
    add("data[ttncc_NgayTuTran]", death_day)
    add("data[ttncc_GiayChungTu]", _death_paper(values.get("CCB_LoaiGiayChungTu"), values.get("CCB_SoGiayChungTu")))
    add("data[ttncc_NgayCap]", _date(values.get("CCB_NgayCapGiayChungTu")))
    add("data[ttncc_CoQuanCap]", _agency(values.get("CCB_NoiCapGiayChungTu")))

    # --- Phần IV: người nhận mai táng phí (= chủ hồ sơ); trú quán dùng lại key khối Người nộp (occurrence 1) ---
    if has_owner:
        add("data[fullname1]", owner["name"])
        add("data[birthday1]", owner["birthday"])
        add("data[gender1]", owner["gender"])
        add_area("data[province1]", "data[district1]", "data[address1]", owner_origin)
        add_area("data[province]", "data[district]", "data[address]", owner_home, occurrence=1)
        add("data[ttnn_QuanHe]", relation)

    # --- Cảnh báo ---
    if organization and not owner["name"]:
        warnings.append(f"Bản khai ghi tổ chức nhận trợ cấp ({organization}) — vui lòng chọn \"Tổ chức/Doanh nghiệp\" và "
                        "nhập tay phần chủ hồ sơ, người nhận mai táng phí.")
    elif not owner["name"] or not owner["identity"]:
        warnings.append("Chưa đọc được họ tên / số định danh người nhận trợ cấp ở Mục 2a Bản khai — vui lòng nhập tay "
                        "phần chủ hồ sơ và người nhận mai táng phí.")
    if has_owner and not owner_home:
        warnings.append("Hồ sơ không có CCCD người nhận trợ cấp nên chưa có nơi thường trú — vui lòng chọn Tỉnh/TP, "
                        "Phường/Xã, địa chỉ ở phần chủ hồ sơ và trú quán người nhận mai táng phí.")
    if has_owner and not owner_origin:
        warnings.append("Chưa có quê quán người nhận trợ cấp (CCCD) — vui lòng chọn nguyên quán người nhận mai táng phí.")
    if has_owner and not owner["phone"]:
        warnings.append("Bản khai không ghi số điện thoại người nhận trợ cấp — ô SĐT (bắt buộc) vui lòng nhập tay.")
    if not ccb["name"]:
        warnings.append("Chưa đọc được họ tên cựu chiến binh đã chết (Mục 1 Bản khai / trích lục khai tử) — vui lòng "
                        "nhập tay.")
    if not death_day:
        warnings.append("Chưa đọc được ngày từ trần của cựu chiến binh (trích lục khai tử) — vui lòng nhập tay.")
    if not ccb_origin or not ccb_origin.get("xa"):
        warnings.append("Chưa đọc đủ nguyên quán (tới cấp xã) của cựu chiến binh — vui lòng chọn ở mục người có công từ "
                        "trần.")
    if not ccb_home:
        warnings.append("Chưa đọc được trú quán của cựu chiến binh — vui lòng chọn ở mục người có công từ trần.")
    if theo_to_khai:
        if not nop:
            warnings.append("Bật \"Lấy người nộp theo tờ khai\" nhưng chưa đọc được người nhận trợ cấp ở Bản khai — chưa "
                            "điền phần người nộp, vui lòng nhập tay.")
    elif not has_ctx:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — chưa điền phần người nộp, vui lòng kiểm tra.")
    elif not nop:
        warnings.append("Người nộp khác người nhận trợ cấp và hồ sơ không có CCCD của người nộp — vui lòng tự nhập ngày "
                        "cấp, nơi cấp, địa chỉ, số điện thoại của người nộp.")
    return out, warnings
