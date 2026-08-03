"""Map fact Bản khai Mẫu 12 + CCCD + trích lục khai tử sang field Form.io.

ĐẶC THÙ: occurrence 0 = người khai/nhận trợ cấp (còn sống); occurrence 1 = người có công TỪ TRẦN
(hai người KHÁC nhau). Mục 1 (từ trần): Quê quán = province(occ1)/village/address(occ1);
Nơi thường trú = province1/village1/address1. Mục 3 (người nhận trợ cấp một lần = người khai):
fullname2.../ province5-6. Mục 2 (mai táng phí) là field nạp động → không điền.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.uu_dai_ncc_tu_tran.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    return _text(value)


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"] = parts[-1]
        out["xa"] = parts[-3]
        out["diaChi"] = ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"] = parts[-1]
        out["xa"] = parts[-2]
        out["diaChi"] = ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"] = parts[-1]
        out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0").replace("S", "5"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    return normalize_date(text)


def _year(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", text)
    return m.group(1) if m else text


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _same_person(doc_id: Any, doc_name: Any, ctx_id: Any, ctx_name: Any) -> bool:
    did, cid = _identity(doc_id), _identity(ctx_id)
    if did and cid:
        return did == cid
    dname, cname = _fold(doc_name), _fold(ctx_name)
    return bool(dname and cname and dname == cname)


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    return _text(_pick(*(item.get(k) for k in keys)))


def _add_area(add, province_name, district_name, address_name, value, *, occurrence=None) -> None:
    area = _area(value)
    if not area:
        return
    add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
    add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
    add(address_name, _text(area.get("diaChi")), occurrence=occurrence)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()
    context = _form_context(options)

    def add(name: str, value, *, occurrence=None) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(seen_key)

    # === Người khai/nhận trợ cấp (còn sống) — ưu tiên CCCD cho định danh, tờ khai cho cư trú ===
    kh_name = _text(_pick(values.get("Person1_HoTen"), values.get("ToKhai_HoTen")))
    kh_identity = _identity(_pick(values.get("Person1_SoDinhDanh"), values.get("ToKhai_SoDinhDanh")))
    kh_birthday = _date(_pick(values.get("Person1_NgaySinh"), values.get("ToKhai_NgaySinh")))
    kh_gender = _text(_pick(values.get("Person1_GioiTinh"), values.get("ToKhai_GioiTinh")))
    kh_issue_date = _date(_pick(values.get("Person1_NgayCap"), values.get("ToKhai_NgayCap")))
    kh_issue_place = _pick(values.get("Person1_NoiCap"), values.get("ToKhai_NoiCap"))
    kh_residence = _area(values.get("ToKhai_NoiThuongTru")) or _area(values.get("Person1_NoiCuTru"))
    kh_quequan = _area(values.get("ToKhai_QueQuan"))
    kh_phone = _phone(values.get("ToKhai_DienThoai"))
    kh_issuer = _issuer(kh_issue_place) or _text(kh_issue_place)

    if not kh_name or not kh_identity:
        warnings.append("Thiếu họ tên hoặc số định danh người khai từ Bản khai Mẫu 12/CCCD.")

    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(kh_identity, kh_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    # --- Phần 1: Người nộp (occurrence 0 = người khai) ---
    if can_fill_applicant:
        add("data[chonDoiTuong]", "Cá nhân")
        add("data[fullname]", kh_name, occurrence=0)
        add("data[birthday]", kh_birthday, occurrence=0)
        add("data[gender]", kh_gender, occurrence=0)
        add("data[identityNumber]", kh_identity)
        add("data[identityDate]", kh_issue_date)
        add("data[idIssuePlace]", kh_issuer)
        _add_area(add, "data[province]", "data[district]", "data[address]", kh_residence, occurrence=0)
        add("data[phoneNumber]", kh_phone)
        add("data[isOwnerDossierCheck]", True)
    else:
        add("data[isOwnerDossierCheck]", False)
        add("data[chonDoiTuong1]", "Cá nhân")

    # --- Phần 2: Chủ hồ sơ (= người khai) ---
    add("data[ownerFullname]", kh_name)
    add("data[ownerBirthday]", kh_birthday)
    add("data[ownerGender]", kh_gender)
    add("data[ownerIdentityNumber]", kh_identity)
    add("data[ownerIdentityDate]", kh_issue_date)
    add("data[ownerIdIssuePlace]", kh_issuer)
    _add_area(add, "data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", kh_residence)
    add("data[ownerPhoneNumber]", kh_phone)
    add("data[ownerNation]", "Việt Nam")

    # --- Mục 1: Người có công TỪ TRẦN (occurrence 1) ---
    add("data[fullname]", _text(values.get("TuTran_HoTen")), occurrence=1)
    add("data[birthday]", _date(values.get("TuTran_NgaySinh")), occurrence=1)
    add("data[gender]", _text(values.get("TuTran_GioiTinh")), occurrence=1)
    # Quê quán người từ trần → province(occ1)/village/address(occ1). LƯU Ý: `village` là field DUY NHẤT
    # trên DOM (không occurrence), chỉ province/address mới có occ0/occ1 → village add KHÔNG occurrence.
    _tt_que = _area(values.get("TuTran_QueQuan"))
    if _tt_que:
        add("data[province]", _province_label(_tt_que.get("tinh")), occurrence=1)
        add("data[village]", _commune_label(_tt_que.get("xa")))
        add("data[address]", _text(_tt_que.get("diaChi")), occurrence=1)
    # Nơi thường trú người từ trần → province1/village1/address1.
    _add_area(add, "data[province1]", "data[village1]", "data[address1]", values.get("TuTran_NoiThuongTru"))
    add("data[doiTuong]", _text(values.get("TuTran_DoiTuong")))
    add("data[SoQDTH]", _text(values.get("TuTran_SoQDHuongTroCap")))
    add("data[ncNgayCap]", _date(values.get("TuTran_NgayQDHuongTroCap")))
    add("data[noiCap]", _text(values.get("TuTran_NoiCapQD")))
    add("data[TiLeTonThuong]", _text(values.get("TuTran_TiLeTonThuong")))
    add("data[NgayTuTran]", _date(values.get("TuTran_NgayTuTran")))
    add("data[SoGiayBaoTu]", _text(values.get("TuTran_SoGiayBaoTu")))
    add("data[ncNgayCap1]", _date(values.get("TuTran_NgayCapBaoTu")))
    add("data[noiCap1]", _text(values.get("TuTran_NoiCapBaoTu")))
    add("data[MucTroCap]", _text(values.get("TuTran_MucTroCap")))
    add("data[TroCapPhuCap]", _date(values.get("TuTran_TroCapDaNhanDenHet")))

    # --- Mục 2: Loại nhận mai táng phí + panel "Cá nhân nhận mai táng phí" ---
    # loaiNhan BẮT BUỘC → luôn set. Panel điền từ chính dữ liệu Mục 2a (MaiTang_*), KHÔNG đắp từ Mục 3.
    add("data[loaiNhan]", "Cá nhân")
    mt_name = _text(values.get("MaiTang_HoTen"))
    if mt_name:
        add("data[fullname1]", mt_name)
        add("data[phoneNumber]", _phone(values.get("MaiTang_DienThoai")), occurrence=1)  # reuse tên Phần 1.
        add("data[birthday1]", _date(values.get("MaiTang_NgaySinh")))
        add("data[nnLoaiGiayTo1]", _text(values.get("MaiTang_LoaiGiayTo")) or "Căn cước công dân")
        add("data[gender1]", _text(values.get("MaiTang_GioiTinh")))
        add("data[identityNumber1]", _identity(values.get("MaiTang_SoDinhDanh")))
        add("data[identityDate1]", _date(values.get("MaiTang_NgayCap")))
        add("data[identityAgency1]", _issuer(values.get("MaiTang_NoiCap")) or _text(values.get("MaiTang_NoiCap")))
        _add_area(add, "data[province2]", "data[village2]", "data[address2]", _area(values.get("MaiTang_QueQuan")))
        _add_area(add, "data[province3]", "data[village3]", "data[address3]", _area(values.get("MaiTang_NoiThuongTru")))
        add("data[moiQH]", _text(values.get("MaiTang_MoiQuanHe")))

    # --- Mục 3: Người nhận trợ cấp một lần (= người khai) ---
    add("data[fullname2]", kh_name)
    add("data[phoneNumber2]", kh_phone)
    add("data[birthday2]", kh_birthday)
    add("data[nnLoaiGiayTo2]", _text(values.get("ToKhai_LoaiGiayTo")) or "Căn cước công dân")
    add("data[gender2]", kh_gender)
    add("data[identityNumber2]", kh_identity)
    add("data[identityDate2]", kh_issue_date)
    add("data[identityAgency2]", kh_issuer)
    _add_area(add, "data[province5]", "data[village5]", "data[address5]", kh_quequan)
    _add_area(add, "data[province6]", "data[village6]", "data[address6]", kh_residence)
    add("data[moiQH1]", _text(values.get("ToKhai_MoiQuanHeVoiTuTran")))

    # --- Mục 4a: Danh sách thân nhân (dataGrid) ---
    for idx, item in enumerate(_list(values.get("ToKhai_ThanNhan"))[:8]):
        add(f"data[dataGrid][{idx}][textField]", _item_text(item, "hoTen", "hoVaTen"))
        add(f"data[dataGrid][{idx}][textField1]", _year(_item_text(item, "namSinh", "ngaySinh")))
        add(f"data[dataGrid][{idx}][textField2]", _item_text(item, "noiThuongTru", "diaChi"))
        add(f"data[dataGrid][{idx}][textField3]", _item_text(item, "quanHe", "moiQuanHe", "mqh"))
        add(f"data[dataGrid][{idx}][textField4]", _item_text(item, "ngheNghiep"))
        add(f"data[dataGrid][{idx}][textField5]", _item_text(item, "hoanCanh"))

    # --- Mục 4b: Con NCC đi học/khuyết tật (dataGrid1) ---
    for idx, item in enumerate(_list(values.get("ToKhai_ConNCC"))[:8]):
        add(f"data[dataGrid1][{idx}][textField]", _item_text(item, "hoTen", "hoVaTen"))
        add(f"data[dataGrid1][{idx}][textField1]", _year(_item_text(item, "namSinh", "ngaySinh")))
        add(f"data[dataGrid1][{idx}][textField2]", _item_text(item, "thoiDiemKhuyetTat"))
        add(f"data[dataGrid1][{idx}][textField3]", _item_text(item, "thoiDiemKetThucPhoThong"))
        add(f"data[dataGrid1][{idx}][textField4]", _item_text(item, "tenCoSoGiaoDuc"))
        add(f"data[dataGrid1][{idx}][textField5]", _item_text(item, "thoiGianBatDauHoc"))

    # --- Khai báo hồ sơ đính kèm (dòng đầu) ---
    add("data[hoSoDinhKem][0][textField1]", "Bản khai giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12)")
    add("data[hoSoDinhKem][0][textField2]", "Bản chính")

    if not values.get("TuTran_HoTen"):
        warnings.append("Chưa đọc được họ tên người có công từ trần trong Bản khai Mẫu 12.")
    if not values.get("TuTran_NgayTuTran"):
        warnings.append("Chưa đọc được ngày từ trần (trích lục khai tử/Bản khai Mẫu 12).")
    return out, warnings
