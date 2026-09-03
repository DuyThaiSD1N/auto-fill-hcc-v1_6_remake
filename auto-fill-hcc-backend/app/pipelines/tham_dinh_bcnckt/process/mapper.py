"""Map compact facts → Form.io data[...] fields cho "Thẩm định BCNCKT đầu tư xây dựng" (cổng Bộ Xây dựng).

- Phần I  người nộp (occ0): từ CCCD người nộp; xác định qua VNeID (formContext tên + CCCD).
- Phần II doanh nghiệp (province1/district1/address1) + Phần III chủ đầu tư: từ Tờ trình I.4-I.5.
- Phần IV dự án (địa điểm xây dựng = province/district/address occ1) + thông tin chung.
- Phần VI containers quy hoạch/phê duyệt (container6/container1/container[G17-KQ...]).
- Phần VII năng lực nhà thầu + 2 datagrid bộ môn (khaoSatXayDung[]/thamTraThietKe[]).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.tham_dinh_bcnckt.process.schema import UI_COMP_BY_NAME, _MAX_BO_MON


@dataclass
class Person:
    name: str | None = None
    identity: str | None = None
    birthday: str | None = None
    issue_date: str | None = None
    issuer: str | None = None
    residence: Any = None
    phone: str | None = None
    email: str | None = None


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
            value.get("diaChi") or value.get("chiTiet"),
            value.get("xa") or value.get("phuong"),
            value.get("tinh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _strip_admin_prefix(text)
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


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
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        out = out if any(out.values()) else None
    else:
        return None
    return out


def _full_address(value: Any) -> str | None:
    area = _area(value)
    if not area:
        return _text(value)
    parts = [area.get("diaChi"), area.get("xa"), area.get("tinh")]
    joined = ", ".join(str(p).strip() for p in parts if str(p or "").strip())
    return joined or _text(value)


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
    if 9 <= len(digits) <= 12:
        return digits
    return None


def _digits(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    d = re.sub(r"\D+", "", text)
    return d or None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _norm_identity(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _same_person(a_id: Any, a_name: Any, b_id: Any, b_name: Any) -> bool:
    ai, bi = _norm_identity(a_id), _norm_identity(b_id)
    if ai and bi:
        if ai == bi:
            return True
        if len(ai) >= 9 and len(bi) >= 9:
            return False
    an, bn = _fold(a_name), _fold(b_name)
    return bool(an and bn and an == bn)


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _nguoi_nop(values: dict) -> Person | None:
    name = values.get("NguoiNop_HoTen")
    identity = values.get("NguoiNop_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = _date(values.get("NguoiNop_NgayCap"))
    return Person(
        name=_text(name),
        identity=_identity(identity),
        birthday=_date(values.get("NguoiNop_NgaySinh")),
        issue_date=issue_date,
        issuer=_issuer(values.get("NguoiNop_NoiCap")),
        residence=values.get("NguoiNop_NoiCuTru"),
        phone=_phone(values.get("NguoiNop_DienThoai")),
        email=_text(values.get("NguoiNop_Email")),
    )


def _item(row: Any, *keys: str) -> str | None:
    if not isinstance(row, dict):
        return _text(row)
    for k in keys:
        if row.get(k) not in (None, "", {}, []):
            return _text(row.get(k))
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _fold(value) in {"true", "1", "co", "có", "x", "yes", "dieu chinh"}


def _loai_du_an(loai_cong_trinh: Any) -> str | None:
    """Suy 'Loại dự án' từ 'Loại công trình chính' — option form KHỚP theo nhóm công trình
    (Dân dụng/Công nghiệp/Hạ tầng kỹ thuật/Giao thông/Nông nghiệp phát triển nông thôn/Hỗn hợp)."""
    text = _text(loai_cong_trinh)
    if not text:
        return None
    bare = re.sub(r"^\s*công\s*trình\s+", "", text, flags=re.IGNORECASE).strip()
    if not bare:
        return None
    return bare[:1].upper() + bare[1:]


# Nguồn vốn (Tờ trình mô tả tự do) → 1 trong 5 option select trên form.
def _nguon_von(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    h = _fold(text)
    if "ppp" in h or "doi tac cong tu" in h:
        return "Thực hiện theo phương thức PPP"
    if "nha nuoc ngoai dau tu cong" in h:
        return "Vốn nhà nước ngoài đầu tư công"
    if "dau tu cong" in h and "ngoai" not in h:
        return "Vốn đầu tư công"
    if "hon hop" in h:
        return "Vốn hỗn hợp"
    # tự có / vay ngân hàng / tư nhân / hợp pháp khác → "Vốn khác".
    return "Vốn khác"


# Loại hình BĐS: LLM trả "1"/"2"/"3"; map sang value checkbox tương ứng (giữ nguyên).
def _loai_hinh_bds(value: Any) -> str | None:
    d = re.sub(r"\D+", "", str(value or ""))
    return d if d in {"1", "2", "3"} else None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None, str | None]] = set()

    def add(name: str, value, *, occurrence: int | None = None, default: bool = False,
            option_value: str | None = None) -> None:
        seen_key = (name, occurrence, option_value)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        if option_value is not None:
            item["optionValue"] = option_value
        if default:
            item["default"] = True
        out.append(item)
        seen.add(seen_key)

    def add_area(province_name, ward_name, address_name, area, *, occurrence=None) -> None:
        if not area:
            return
        # ⚠ CẢ 3 cấp (province/district/address) đều TRÙNG 2× trong DOM (Phần I occ0 / dự án occ1) → ward
        # cũng phải mang occurrence, nếu không occ1 bị chặn bởi occ0 (cùng key+None). Với Phần II doanh
        # nghiệp (province1/district1/address1 — key riêng) thì occurrence=None, không ảnh hưởng.
        add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
        add(ward_name, _commune_label(area.get("xa")), occurrence=occurrence)
        add(address_name, _text(area.get("diaChi")), occurrence=occurrence)

    # ===== Phần I: NGƯỜI NỘP (occurrence 0) — từ CCCD, xác định qua VNeID =====
    nguoi_nop = _nguoi_nop(values)
    ctx = _form_context(options)
    if nguoi_nop:
        # Nếu formContext (VNeID) có và KHÁC người trong CCCD → vẫn điền (người nộp = chủ CCCD tải lên);
        # match chỉ để yên tâm. KHÔNG bỏ trống như tài khoản-gate.
        if ctx.get("applicant_identity") or ctx.get("applicant_name"):
            if not _same_person(nguoi_nop.identity, nguoi_nop.name,
                                 ctx.get("applicant_identity"), ctx.get("applicant_name")):
                warnings.append("CCCD người nộp không khớp tài khoản VNeID — vẫn điền theo CCCD tải lên.")
        add("data[chonDoiTuong]", "Tổ chức", default=True)  # đại diện chủ đầu tư (tổ chức).
        add("data[fullname]", nguoi_nop.name)
        add("data[birthday]", nguoi_nop.birthday)
        add("data[identityNumber]", nguoi_nop.identity)
        add("data[identityDate]", nguoi_nop.issue_date)
        add("data[identityAgency]", nguoi_nop.issuer)
        add("data[phoneNumber]", nguoi_nop.phone)
        add("data[email]", nguoi_nop.email)
        add("data[nation]", "Việt Nam", default=True)
        add_area("data[province]", "data[district]", "data[address]", _area(nguoi_nop.residence), occurrence=0)
    else:
        add("data[chonDoiTuong]", "Tổ chức", default=True)
        warnings.append("Không có CCCD người nộp — Phần I nhân thân để VNeID tự điền.")

    # ===== Chủ đầu tư (Tờ trình I.4-I.5) =====
    cdt_ten = _text(values.get("ChuDauTu_Ten"))
    cdt_mst = _digits(values.get("ChuDauTu_MaSoThue"))
    cdt_phone = _phone(values.get("ChuDauTu_DienThoai"))
    cdt_area = _area(values.get("ChuDauTu_DiaChi"))
    cdt_diachi_full = _full_address(values.get("ChuDauTu_DiaChi"))

    if not cdt_ten:
        warnings.append("Không đọc được tên chủ đầu tư từ Tờ trình (mục I.5).")

    # Phần II: doanh nghiệp (hiện khi Tổ chức).
    add("data[organization]", cdt_ten)
    add("data[taxCode]", cdt_mst)
    add("data[nation1]", "Việt Nam", default=True)
    add("data[organizationPhoneNumber]", cdt_phone)
    add_area("data[province1]", "data[district1]", "data[address1]", cdt_area)

    # Phần III: chủ đầu tư.
    add("data[nguoiQuyetDinhDauTu]", _text(values.get("ChuDauTu_NguoiQuyetDinhDauTu")))
    add("data[chuDauTu]", cdt_ten)
    add("data[maChuDauTu]", cdt_mst)
    add("data[diaChiChuDauTu]", cdt_diachi_full)
    add("data[soDienThoaiChuDauTu]", cdt_phone)

    # ===== Phần IV: THÔNG TIN CHUNG DỰ ÁN (địa điểm = occurrence 1) =====
    if _truthy(values.get("DuAn_LaDieuChinh")):
        add("data[thBCNCKTDieuChinh]", True)
    add("data[tenDuAn]", _text(values.get("DuAn_Ten")))
    add_area("data[province]", "data[district]", "data[address]", _area(values.get("DuAn_DiaDiem")), occurrence=1)
    add("data[nhomDuAn]", _text(values.get("DuAn_Nhom")))
    loai_ct = _text(values.get("DuAn_LoaiCongTrinh"))
    add("data[loaiCongTrinh]", loai_ct)
    # Loại dự án: Tờ trình không nêu riêng → suy từ loại công trình chính (mặc định vàng để cán bộ soát).
    add("data[loaiDuAn]", _loai_du_an(loai_ct), default=True)
    add("data[capCongTrinh]", _text(values.get("DuAn_CapCongTrinh")))
    add("data[thoiHanSuDungCongTrinhChinh]", _digits(values.get("DuAn_ThoiHanSuDung")))
    add("data[tongMucDauTu]", _digits(values.get("DuAn_TongMucDauTu")))
    # Nguồn vốn: chuẩn hóa mô tả tự do → đúng 1 option select (vd "Vốn tự có, vay NH…" → "Vốn khác").
    add("data[nguonVonDauTu]", _nguon_von(values.get("DuAn_NguonVon")), default=True)
    add("data[quyMoDauTu]", _text(values.get("DuAn_QuyMo")))
    add("data[tuNgay]", _date(values.get("DuAn_TienDoTuNgay")))
    add("data[denNgay]", _date(values.get("DuAn_TienDoDenNgay")))
    # Loại hình bất động sản (checkbox group value 1/2/3) — tích đúng nhóm công năng.
    _bds = _loai_hinh_bds(values.get("DuAn_LoaiHinhBDS"))
    if _bds:
        add("data[loaiHinhBatDongSan][]", True, option_value=_bds, default=True)

    # ===== Phần VI: QUY HOẠCH / PHÊ DUYỆT (containers) =====
    add("data[container6][tenQuyHoachCanCuLapDuAn]", _text(values.get("QHDuAn_Ten")))
    add("data[container6][G17-KQ002914_soQuyetDinh]", _text(values.get("QHDuAn_So")))
    add("data[container6][G17-KQ002914_ngay]", _date(values.get("QHDuAn_Ngay")))
    add("data[container6][G17-KQ002914_coQuan]", _text(values.get("QHDuAn_CoQuan")))
    add("data[container1][tenQuyHoachCanCuLapQuyHoach]", _text(values.get("QHQuyHoach_Ten")))
    add("data[container1][G17-KQ002915_soQuyetDinh]", _text(values.get("QHQuyHoach_So")))
    add("data[container1][G17-KQ002915_ngay]", _date(values.get("QHQuyHoach_Ngay")))
    add("data[container1][G17-KQ002915_coQuan]", _text(values.get("QHQuyHoach_CoQuan")))
    add("data[container][G17-KQ002911_soQuyetDinh]", _text(values.get("ChuTruong_So")))
    add("data[container][G17-KQ002911_ngay]", _date(values.get("ChuTruong_Ngay")))
    add("data[container][G17-KQ002911_coQuan]", _text(values.get("ChuTruong_CoQuan")))
    add("data[container][G17-KQ002916_soQuyetDinh]", _text(values.get("MoiTruong_So")))
    add("data[container][G17-KQ002916_ngay]", _date(values.get("MoiTruong_Ngay")))
    add("data[container][G17-KQ002916_coQuan]", _text(values.get("MoiTruong_CoQuan")))

    # ===== Phần VII: NĂNG LỰC NHÀ THẦU =====
    # ⚠ Ô "Mã số doanh nghiệp" của ĐƠN VỊ yêu cầu MST 10 số / mã chi nhánh (10-3) — KHÁC "chứng chỉ năng
    # lực số" (BXD-xxx/SOL-xxx) mà Tờ trình cung cấp. Tờ trình KHÔNG có MST nhà thầu → BỎ TRỐNG ô này
    # (điền chứng chỉ số vào đây gây lỗi validation). Cán bộ tra MST / dùng tính năng tìm kiếm theo tên.
    add("data[tenDoanhNghiepKhaoSat]", _text(values.get("KhaoSat_TenDN")))
    add("data[tenChuNhiemKhaoSatXayDung]", _text(values.get("KhaoSat_ChuNhiem")))
    add("data[maSoChungChiChuNhiemKhaoSat]", _text(values.get("KhaoSat_MaCC")))
    add("data[tenDoanhNghiepTuVanThietKe]", _text(values.get("ThietKe_TenDN")))
    add("data[tenChuNhiemThietKe]", _text(values.get("ThietKe_ChuNhiem")))
    add("data[maSoChungChiChuNhiemThietKe]", _text(values.get("ThietKe_MaCC")))
    add("data[tenDoanhNghiepThamTra]", _text(values.get("ThamTra_TenDN")))
    add("data[tenChuNhiemKhaoSatXayDung1]", _text(values.get("ThamTra_ChuNhiem")))       # ⚠ chủ nhiệm THẨM TRA.
    add("data[maSoChungChiChuNhiemKhaoSat1]", _text(values.get("ThamTra_MaCC")))          # ⚠ mã CC thẩm tra.

    # Datagrid bộ môn thiết kế (khaoSatXayDung[i]) — key DOM là "khaoSatXayDung" nhưng nội dung THIẾT KẾ.
    bo_mon_tk = values.get("BoMonThietKe")
    if isinstance(bo_mon_tk, list):
        for idx, row in enumerate(bo_mon_tk[:_MAX_BO_MON]):
            base = f"data[khaoSatXayDung][{idx}]"
            add(f"{base}[boMonThietKe]", _item(row, "boMon", "boMonThietKe", "bomon"))
            add(f"{base}[hoVaTenThietKe]", _item(row, "hoTen", "hoVaTen", "ten"))
            add(f"{base}[maSoChungChiHanhNgheThietKe]", _item(row, "maCC", "maSoChungChi", "maChungChi"))

    # Datagrid bộ môn thẩm tra (thamTraThietKe[i]).
    bo_mon_tt = values.get("BoMonThamTra")
    if isinstance(bo_mon_tt, list):
        for idx, row in enumerate(bo_mon_tt[:_MAX_BO_MON]):
            base = f"data[thamTraThietKe][{idx}]"
            add(f"{base}[boMonThamTra]", _item(row, "boMon", "boMonThamTra", "bomon"))
            add(f"{base}[hoVaTenThamTra]", _item(row, "hoTen", "hoVaTen", "ten"))
            add(f"{base}[maSoChungChiHanhNgheThamTra]", _item(row, "maCC", "maSoChungChi", "maChungChi"))

    return out, warnings
