"""Map compact facts → Form.io data[...] cho mai táng phí dân công hỏa tuyến (cổng MOHA).

Hai vai: CHỦ HỒ SƠ (ChuHoSo_*, người đứng khai) và NGƯỜI NỘP (NguoiNop_*, người có thẻ CCCD khác). Người
nộp trên cổng = TÀI KHOẢN UI (formContext) — mapper lấy đó làm CHUẨN, KHÔNG để LLM tự quyết:
- Tự nộp (tài khoản UI = chủ hồ sơ, hoặc UI không có anchor) → tick True, Phần I = chủ hồ sơ (cổng tự đổ
  Phần II).
- Nộp thay (tài khoản UI ≠ chủ hồ sơ) → tick False, Phần I = người nộp (dữ liệu từ NguoiNop_* nếu khớp UI,
  không thì lấy tên/số theo tài khoản UI), Phần II owner_* = chủ hồ sơ.
Không làm rỗng chủ hồ sơ khi không xác minh được người nộp.
"""

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.mai_tang_dan_cong.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    return " ".join(str(value).replace("\n", " ").split()).strip() or None


def _fold(value: Any) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z]+", " ", text)).strip().lower()


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits or None


def _strip_admin_prefix(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s+", "", text,
                  flags=re.IGNORECASE).strip()


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        parts = [p.strip(" .") for p in re.split(r"[,;\n]+", value) if p.strip(" .")]
        if not parts:
            return None
        out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
        district = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
        if len(parts) >= 4 and district.match(parts[-2]):
            out["tinh"], out["xa"], out["diaChi"] = _strip_admin_prefix(parts[-1]), _strip_admin_prefix(parts[-3]), ", ".join(parts[:-3])
        elif len(parts) >= 3:
            out["tinh"], out["xa"], out["diaChi"] = _strip_admin_prefix(parts[-1]), _strip_admin_prefix(parts[-2]), ", ".join(parts[:-2])
        elif len(parts) == 2:
            out["tinh"], out["diaChi"] = _strip_admin_prefix(parts[-1]), parts[0]
        else:
            out["diaChi"] = parts[0]
        return out if any((out["tinh"], out["xa"], out["diaChi"])) else None
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    return out if any((out["tinh"], out["xa"], out["diaChi"])) else None


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ")):
        return text
    cities = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in cities else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _same_person(a_id, a_name, b_id, b_name) -> bool:
    ai, bi = _identity(a_id), _identity(b_id)
    if ai and bi:
        if ai == bi:
            return True
        if len(ai) >= 9 and len(bi) >= 9:
            return False
    an, bn = _fold(a_name), _fold(b_name)
    return bool(an and bn and an == bn)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    v = _by_name(fields)
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

    # --- CHỦ HỒ SƠ (người đứng khai, mục 1) ---
    name = _text(v.get("ChuHoSo_HoTen"))
    identity = _identity(v.get("ChuHoSo_SoDinhDanh"))
    if not name and not identity:
        return out, ["Không đọc được chủ hồ sơ (người đứng khai) từ Bản khai Mẫu 02-MTP."]
    birthday = _text(v.get("ChuHoSo_NgaySinh"))
    gender = _text(v.get("ChuHoSo_GioiTinh"))
    id_date = _text(v.get("ChuHoSo_NgayCap"))
    issuer = _text(v.get("ChuHoSo_NoiCap")) or (default_issuer(id_date) if id_date else None)
    residence = _area(v.get("ChuHoSo_ThuongTru"))
    phone = _text(v.get("ChuHoSo_DienThoai"))
    nation = _text(v.get("ChuHoSo_QuocTich")) or "Việt Nam"

    def add_phan_i(*, p_name, p_bd, p_gender, p_id, p_iddate, p_issuer, p_res, p_phone):
        """Phần I — NGƯỜI NỘP HỒ SƠ."""
        add("data[fullname]", p_name)
        add("data[birthday]", p_bd)
        add("data[gender]", p_gender)
        add("data[identityNumber]", p_id)
        add("data[identityDate]", p_iddate)
        add("data[idIssuePlace]", p_issuer)
        if p_res:
            add("data[province]", _province_label(p_res.get("tinh")))
            add("data[district]", _text(p_res.get("xa")))
            add("data[address]", _text(p_res.get("diaChi")))
        add("data[phoneNumber]", p_phone)

    # --- NGƯỜI NỘP theo TÀI KHOẢN UI (formContext là CHUẨN) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("ownerFullname") or ctx.get("fullname"))
    ctx_id = _identity(ctx.get("applicantIdentityNumber") or ctx.get("ownerIdentityNumber") or ctx.get("identityNumber"))
    ui_has_anchor = bool(ctx_name or ctx_id)

    # UI không có anchor → không tự xác nhận người nộp → mặc định tự nộp, giữ chủ hồ sơ.
    is_nop_thay = ui_has_anchor and not _same_person(ctx_id, ctx_name, identity, name)

    if not is_nop_thay:
        # === TỰ NỘP: Phần I = chủ hồ sơ; TICH → cổng tự đổ Phần II. ===
        add("data[isOwnerDossierCheck]", True)
        add_phan_i(p_name=name, p_bd=birthday, p_gender=gender, p_id=identity, p_iddate=id_date,
                   p_issuer=issuer, p_res=residence, p_phone=phone)
        add("data[nation]", nation)
        return out, warnings

    # === NỘP THAY: Phần I = NGƯỜI NỘP (tài khoản UI); BỎ TÍCH; Phần II owner_* = chủ hồ sơ. ===
    add("data[isOwnerDossierCheck]", False)

    # Dữ liệu người nộp: chỉ dùng NguoiNop_* KHI khớp tài khoản UI (cả hai anchor). Nếu không khớp/thiếu
    # → chỉ đặt tên+số theo tài khoản UI (Phần I fullname/id khóa theo tài khoản).
    nop_name = _text(v.get("NguoiNop_HoTen"))
    nop_id = _identity(v.get("NguoiNop_SoDinhDanh"))
    nop_matches_ui = (nop_name or nop_id) and _same_person(nop_id, nop_name, ctx_id, ctx_name)

    if nop_matches_ui:
        nop_iddate = _text(v.get("NguoiNop_NgayCap"))
        add_phan_i(
            p_name=nop_name or ctx_name,
            p_bd=_text(v.get("NguoiNop_NgaySinh")),
            p_gender=_text(v.get("NguoiNop_GioiTinh")),
            p_id=nop_id or ctx_id,
            p_iddate=nop_iddate,
            p_issuer=_text(v.get("NguoiNop_NoiCap")) or (default_issuer(nop_iddate) if nop_iddate else None),
            p_res=_area(v.get("NguoiNop_ThuongTru")),
            p_phone=None,
        )
        add("data[nation]", _text(v.get("NguoiNop_QuocTich")) or "Việt Nam")
    else:
        add("data[fullname]", ctx_name)
        add("data[identityNumber]", ctx_id)
        warnings.append(
            "Nộp thay nhưng không có thẻ CCCD của người nộp khớp tài khoản UI — chỉ điền tên/số người nộp "
            "theo tài khoản; các ô còn lại của Phần I vui lòng bổ sung."
        )

    # Phần II — CHỦ HỒ SƠ (điền tường minh, không dựa vào cổng mirror khi đã bỏ tích).
    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", gender)
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", id_date)
    add("data[ownerIdIssuePlace]", issuer)
    if residence:
        add("data[ownerProvince]", _province_label(residence.get("tinh")))
        add("data[ownerDistrict]", _text(residence.get("xa")))
        add("data[ownerAddress]", _text(residence.get("diaChi")))
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerNation]", nation)
    return out, warnings
