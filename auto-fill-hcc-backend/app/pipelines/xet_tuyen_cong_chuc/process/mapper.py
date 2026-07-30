"""Map civil-servant recruitment facts to Form.io fields."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.xet_tuyen_cong_chuc.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.area_remap import remap_area


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
    city_markers = {
        "ha noi",
        "hai phong",
        "da nang",
        "can tho",
        "ho chi minh",
        "tp ho chi minh",
        "hue",
    }
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("xa ", "phuong ", "thi tran ", "tt ")):
        return text
    return text


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
    return remap_area(out if any(out.values()) else None)


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


def _number(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:[,.]\d+)?", text)
    if not m:
        return None
    num = m.group(0).replace("+", "").replace(",", ".")
    if "." in num:
        num = num.rstrip("0").rstrip(".")
    elif re.fullmatch(r"-?\d+", num):
        num = str(int(num))
    return num or None


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
    if isinstance(value, list):
        return value
    return []


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    return _text(_pick(*(item.get(k) for k in keys)))


def _nguyen_vong(value: Any, default_index: int | None = None) -> str | None:
    text = _text(value)
    if not text and default_index is not None:
        text = str(default_index + 1)
    if not text:
        return None
    if re.fullmatch(r"\d+", text):
        return f"Nguyện vọng {int(text)}"
    return text


def _add_area(add, province_name: str, district_name: str, address_name: str, value: Any, *, occurrence=None) -> None:
    area = _area(value)
    if not area:
        return
    add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
    add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
    add(address_name, _text(area.get("diaChi")), occurrence=occurrence)


def _add_person_block(
    add,
    prefix: str,
    *,
    name: Any,
    birthday: Any,
    gender: Any,
    identity: Any,
    issue_date: Any,
    issue_place: Any,
    residence: Any,
    phone: Any,
    email: Any,
    occurrence=None,
) -> None:
    add(f"data[{prefix}Fullname]" if prefix == "owner" else "data[fullname]", _text(name), occurrence=occurrence)
    add(f"data[{prefix}Birthday]" if prefix == "owner" else "data[birthday]", _date(birthday), occurrence=occurrence)
    add(f"data[{prefix}Gender]" if prefix == "owner" else "data[gender]", _text(gender), occurrence=occurrence)
    add(f"data[{prefix}IdentityNumber]" if prefix == "owner" else "data[identityNumber]", _identity(identity), occurrence=occurrence)
    add(f"data[{prefix}IdentityDate]" if prefix == "owner" else "data[identityDate]", _date(issue_date), occurrence=occurrence)
    add(
        f"data[{prefix}IdIssuePlace]" if prefix == "owner" else "data[idIssuePlace]",
        _issuer(issue_place) or _text(issue_place),
        occurrence=occurrence,
    )
    if prefix == "owner":
        _add_area(add, "data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
        add("data[ownerPhoneNumber]", _phone(phone))
        add("data[ownerEmail]", _text(email))
        add("data[ownerNation]", "Việt Nam")
    else:
        _add_area(add, "data[province]", "data[district]", "data[address]", residence, occurrence=occurrence)
        add("data[phoneNumber]", _phone(phone), occurrence=occurrence)
        add("data[email]", _text(email), occurrence=occurrence)


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

    candidate_name = _text(values.get("Phieu_HoTen"))
    candidate_identity = _identity(values.get("Phieu_SoDinhDanh"))
    candidate_residence = _area(values.get("Phieu_NoiThuongTru")) or _area(values.get("Person1_NoiCuTru"))
    candidate_issue_date = _date(_pick(values.get("Phieu_NgayCap"), values.get("Person1_NgayCap")))
    candidate_issue_place = _pick(values.get("Phieu_NoiCap"), values.get("Person1_NoiCap"))

    if not candidate_name or not candidate_identity:
        warnings.append("Thiếu họ tên hoặc số định danh người dự tuyển từ Phiếu đăng ký dự tuyển.")

    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(candidate_identity, candidate_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    if can_fill_applicant:
        add("data[chonDoiTuong]", "Cá nhân")
        _add_person_block(
            add,
            "",
            name=candidate_name,
            birthday=_pick(values.get("Phieu_NgaySinh"), values.get("Person1_NgaySinh")),
            gender=_pick(values.get("Phieu_GioiTinh"), values.get("Person1_GioiTinh")),
            identity=candidate_identity,
            issue_date=candidate_issue_date,
            issue_place=candidate_issue_place,
            residence=candidate_residence,
            phone=values.get("Phieu_DienThoai"),
            email=values.get("Phieu_Email"),
            occurrence=0,
        )
        add("data[isOwnerDossierCheck]", True)
    else:
        add("data[isOwnerDossierCheck]", False)

    if not can_fill_applicant:
        add("data[chonDoiTuong1]", "Cá nhân")
    _add_person_block(
        add,
        "owner",
        name=candidate_name,
        birthday=_pick(values.get("Phieu_NgaySinh"), values.get("Person1_NgaySinh")),
        gender=_pick(values.get("Phieu_GioiTinh"), values.get("Person1_GioiTinh")),
        identity=candidate_identity,
        issue_date=candidate_issue_date,
        issue_place=candidate_issue_place,
        residence=candidate_residence,
        phone=values.get("Phieu_DienThoai"),
        email=values.get("Phieu_Email"),
    )

    add("data[hoSoDinhKem][0][textField1]", "Phiếu đăng ký dự tuyển (Mẫu 01, NĐ 170/2025/NĐ-CP)")
    add("data[hoSoDinhKem][0][textField2]", "Bản chính")

    add("data[VtVlDt]", _text(values.get("Phieu_ViTriViecLam")))
    add("data[CqTcDt]", _text(values.get("Phieu_CoQuanDuTuyen")))
    add("data[fullname]", candidate_name, occurrence=1)
    add("data[birthday]", _date(values.get("Phieu_NgaySinh")), occurrence=1)
    add("data[gender]", _text(values.get("Phieu_GioiTinh")), occurrence=1)
    add("data[identityNumber]", candidate_identity, occurrence=1)
    add("data[identityDate]", candidate_issue_date, occurrence=1)
    add("data[identityAgency]", _issuer(candidate_issue_place) or _text(candidate_issue_place))
    add("data[TonGiao]", _text(values.get("Phieu_TonGiao")))
    add("data[DanToc]", _text(values.get("Phieu_DanToc")))
    add("data[phoneNumber]", _phone(values.get("Phieu_DienThoai")), occurrence=1)
    add("data[email]", _text(values.get("Phieu_Email")), occurrence=1)
    _add_area(add, "data[province1]", "data[district1]", "data[address1]", values.get("Phieu_QueQuan"))
    _add_area(add, "data[province2]", "data[district2]", "data[address2]", values.get("Phieu_NoiThuongTru"))
    _add_area(add, "data[province]", "data[district]", "data[address]", values.get("Phieu_NoiOHienTai"), occurrence=1)
    add("data[TtSk]", _text(values.get("Phieu_TinhTrangSucKhoe")))
    add("data[ChieuCao]", _number(values.get("Phieu_ChieuCao")))
    add("data[CanNang]", _number(values.get("Phieu_CanNang")))
    add("data[TdVh]", _text(values.get("Phieu_TrinhDoVanHoa")))
    add("data[TdCm]", _text(values.get("Phieu_TrinhDoChuyenMon")))

    for idx, item in enumerate(_list(values.get("Phieu_VanBangChungChi"))[:6]):
        add(f"data[DataGrid][{idx}][TenTruong]", _item_text(item, "tenTruong", "truong", "coSoDaoTao"))
        add(f"data[DataGrid][{idx}][NgayCap1]", _date(_item_text(item, "ngayCap", "ngay")))
        add(f"data[DataGrid][{idx}][TdVh1]", _item_text(item, "trinhDo"))
        add(f"data[DataGrid][{idx}][ShVbCc]", _item_text(item, "soHieu", "soVanBang", "soChungChi"))
        add(f"data[DataGrid][{idx}][CnDt]", _item_text(item, "chuyenNganh"))
        add(f"data[DataGrid][{idx}][Ndt]", _item_text(item, "nganh"))
        add(f"data[DataGrid][{idx}][HtDt]", _item_text(item, "hinhThuc"))
        add(f"data[DataGrid][{idx}][XhVbCc]", _item_text(item, "xepLoai"))

    for idx, item in enumerate(_list(values.get("Phieu_QuaTrinhCongTac"))[:5]):
        add(f"data[DataGrid1][{idx}][TnDn]", _item_text(item, "thoiGian"))
        add(f"data[DataGrid1][{idx}][CqTcDv]", _item_text(item, "coQuan", "donVi"))

    add("data[NgoaiNgu]", _text(values.get("Phieu_NgoaiNgu")))
    add("data[CoKhong]", _text(values.get("Phieu_CoDoiTuongUuTien")))
    add("data[DtUt]", _text(values.get("Phieu_DoiTuongUuTien")))
    add("data[Dut]", _number(values.get("Phieu_DiemUuTien")))
    add("data[XacNhan]", True)

    for idx, item in enumerate(_list(values.get("Phieu_ThuTuUuTien"))[:5]):
        add(f"data[DataGrid2][{idx}][stt]", str(idx + 1))
        add(f"data[DataGrid2][{idx}][textField1]", _item_text(item, "tenCoQuan", "coQuan", "donVi"))
        add(f"data[DataGrid2][{idx}][textField2]", _nguyen_vong(_item_text(item, "nguyenVong", "thuTu"), idx))

    add("data[NdYc]", _text(values.get("Phieu_NoiDungKhac")))

    if not values.get("Phieu_VanBangChungChi"):
        warnings.append("Chưa đọc được bảng văn bằng, chứng chỉ trong Phiếu đăng ký dự tuyển.")
    if not values.get("Phieu_ThuTuUuTien"):
        warnings.append("Chưa đọc được thứ tự ưu tiên/nguyện vọng trong Phiếu đăng ký dự tuyển.")
    return out, warnings
