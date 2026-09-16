"""Map dữ kiện nguồn → field UI bước 2 cho thủ tục 1.115667 (Lào Cai).

Chọn nguồn theo cột "Nguồn ưu tiên" (sheet 2 file mapping):
  Người nộp : họ tên/số căn cước/địa chỉ do TK định danh điền sẵn → KHÔNG phát
              (sửa "Họ và tên" là cổng xoá trắng ô Di động và Số căn cước).
              Ngày sinh, giới tính, dân tộc, ngày cấp, nơi cấp → CCCD của CHÍNH người nộp (khớp số, không có
              số thì khớp họ tên tài khoản). Di động/Fax → không phát (SĐT trên Đơn là của chủ hồ sơ).
  Chủ hồ sơ : họ tên, ngày sinh, giới tính, dân tộc, số căn cước → CCCD (bù bằng HĐ/Đơn);
              ngày cấp, nơi cấp → HĐ chuyển nhượng (bù bằng CCCD);
              địa chỉ → Đơn (bù bằng HĐ rồi CCCD); di động, email → Đơn.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_FULL_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.split()).strip(" :;,-") or None


def _full_date(value) -> str | None:
    """Chỉ nhận ngày đủ dd/mm/yyyy. "Sinh năm 1957" không đủ cho ô DD/MM/YYYY → bỏ, không bịa."""
    match = _FULL_DATE_RE.match(_plain(value) or "")
    if not match:
        return None
    return f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{match.group(3)}"


def _id_number(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _phone(value) -> str | None:
    text = str(value or "").strip()
    digits = _digits(text)
    if text.startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _email(value) -> str | None:
    text = (_plain(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text) else None


def _issuer(value) -> str | None:
    return normalize_issuer(value) or _plain(value)


def _gender(card: dict | None, xung_ho) -> str | None:
    text = _fold((card or {}).get("GioiTinh"))
    if text in ("nam", "male"):
        return "Nam"
    if text in ("nu", "female"):
        return "Nữ"
    # Giấy tờ đất đai không ghi giới tính, chỉ có xưng hô "Ông"/"Bà" trước tên.
    salutation = _fold(xung_ho)
    if salutation == "ong":
        return "Nam"
    if salutation == "ba":
        return "Nữ"
    return None


def _area(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or "",
        "diaChi": value.get("diaChi") or "",
    }
    if not (area["tinh"] or area["xa"] or area["diaChi"]):
        return None
    hint = value.get("huyen") or value.get("quanHuyen") or ""
    return remap_area(area, huyen_hint=hint) or area


def _cards(values: dict) -> list[dict]:
    cards = values.get("DanhSachCccd")
    return [c for c in cards if isinstance(c, dict)] if isinstance(cards, list) else []


def _card_by_id(cards: list[dict], wanted) -> dict | None:
    wanted = _digits(wanted)
    if not wanted:
        return None
    matches = [c for c in cards if _digits(c.get("SoDinhDanh")) == wanted]
    return matches[0] if len(matches) == 1 else None


def _card_by_name(cards: list[dict], name) -> dict | None:
    wanted = _fold(name)
    if not wanted:
        return None
    matches = [c for c in cards if _fold(c.get("HoTen")) == wanted]
    # Nhiều thẻ trùng tên → không đoán.
    return matches[0] if len(matches) == 1 else None


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    ctx = (options or {}).get("formContext") or {}
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    cards = _cards(values)

    # ----- Phần I: người nộp (tài khoản đăng nhập). -----
    # Chỉ nhận thẻ khớp SỐ định danh của tài khoản: hồ sơ nộp thay chứa thẻ của chủ hồ sơ, lấy nhầm là
    # điền ngày/nơi cấp của người khác vào ô người nộp.
    applicant_id = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    applicant_card = (
        _card_by_id(cards, applicant_id) if _digits(applicant_id)
        else _card_by_name(cards, ctx.get("applicantFullname"))
    )
    if applicant_card:
        add("CongDan_ngaySinhCongDan", _full_date(applicant_card.get("NgaySinh")))
        add("CongDan_gioiTinhCongDan", _gender(applicant_card, None))
        add("CongDan_danTocCongDan", _plain(applicant_card.get("DanToc")))
        add("CongDan_ngayCapCmnd", _full_date(applicant_card.get("NgayCap")))
        add("CongDan_noiCapCmnd", _issuer(applicant_card.get("NoiCap")))
    # SĐT trên Đơn là của chủ hồ sơ → chỉ điền Di động khối chủ hồ sơ, không đụng Di động/Fax người nộp.

    # ----- Phần II: chủ hồ sơ = bên nhận chuyển nhượng. -----
    owner_id = _id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = _card_by_id(cards, owner_id) if owner_id else _card_by_name(cards, values.get("ChuHoSo_HoTen"))

    org_name = _plain(values.get("ChuHoSo_TenToChuc"))
    is_org = _fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(org_name)
    person_name = _plain((owner_card or {}).get("HoTen")) or _plain(values.get("ChuHoSo_HoTen"))
    person_id = _id_number((owner_card or {}).get("SoDinhDanh")) or owner_id
    is_person = not is_org and bool(person_name and person_id)

    if is_org:
        # Đối tượng là driver: phát TRƯỚC để cổng hiện nhóm ô tổ chức.
        add("ChuHoSo_maDoiTuongNopHS", "DN")
        add("ChuHoSo_tenCoQuanToChucCHS", org_name.upper())
        tax = _digits(values.get("ChuHoSo_MaSoThue"))
        add("ChuHoSo_maSoThueChuHoSo", tax if len(tax) in (10, 13) else None)
    elif is_person:
        # Chỉ tự chọn "Cá nhân" khi có đủ họ tên + số căn cước — hai ô cổng bắt buộc ở nhánh này.
        add("ChuHoSo_maDoiTuongNopHS", "CN")
        add("ChuHoSo_tenChuHoSo", upper_person_name(person_name))
        add("ChuHoSo_ngaySinhChuHoSo",
            _full_date((owner_card or {}).get("NgaySinh")) or _full_date(values.get("ChuHoSo_NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo", _gender(owner_card, values.get("ChuHoSo_XungHo")))
        # Dân tộc: không giấy tờ đất đai nào ghi → chỉ lấy từ thẻ.
        add("ChuHoSo_danTocChuHoSo", _plain((owner_card or {}).get("DanToc")))
        add("ChuHoSo_soCMNDChuHoSo", person_id)
        add("ChuHoSo_noiCapCMNDCHS",
            _issuer(values.get("ChuHoSo_NoiCap")) or _issuer((owner_card or {}).get("NoiCap")))
        add("ChuHoSo_ngayCapCMNDCHS",
            _full_date(values.get("ChuHoSo_NgayCap")) or _full_date((owner_card or {}).get("NgayCap")))

    if is_org or is_person:
        residence = (
            _area(values.get("ChuHoSo_DiaChiDon"))
            or _area(values.get("ChuHoSo_DiaChiHopDong"))
            or _area((owner_card or {}).get("NoiCuTru"))
        )
        if residence:
            # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh.
            add("ChuHoSo_maTinhThanhCHS", province_label(residence.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(residence.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(residence.get("diaChi")))
        add("ChuHoSo_diDongLienLacCHS", _phone(values.get("Don_DienThoai")))
        add("ChuHoSo_emailChuHoSo", _email(values.get("Don_Email")))

    return out
