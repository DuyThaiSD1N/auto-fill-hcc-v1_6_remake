"""Map source facts → Form.io data[...] cho "Đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục…" (mã
1.014335, cổng DVC Bộ GD&ĐT dvc.moet.gov.vn).

Cùng cổng/cùng bộ field người nộp + chủ hồ sơ với cap_ban_sao_van_bang_so_goc → dùng lại helper chuẩn hoá ở đó.

- Phần I  Người nộp LUÔN là người đăng nhập VNeID (họ tên/số định danh/ngày sinh khoá theo tài khoản). Chỉ điền ô
  sửa được khi giấy tờ ĐÚNG là của người đăng nhập (formContext trùng số định danh, không có số thì trùng họ tên):
  trùng sinh viên → nhân thân sinh viên; trùng người nộp trong giấy tờ (CCCD cha/mẹ, Giấy tiếp nhận) → người đó;
  LLM lấy nhầm người nộp nhưng hồ sơ có thẻ CCCD mang số tài khoản → đọc thẳng thẻ đó trong OCR.
  Không đối chiếu được → BỎ QUA cả Phần I (không điền, không tô đỏ), giữ dữ liệu cổng đổ từ tài khoản.
- Phần II data[ChuHS] = "Cá nhân", data[owner...] = sinh viên.
- Phần III panel Đơn PL IV: nơi sinh ưu tiên Giấy khai sinh; nơi thường trú ưu tiên địa danh HIỆN HÀNH (Đơn/Giấy
  xác nhận), CCCD (địa danh cũ) quy đổi làm dự phòng.
Ô bắt buộc thiếu dữ liệu → "dom-expect" (extension tô đỏ); giá trị phỏng đoán → default=True (tô vàng).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines.cap_ban_sao_van_bang_so_goc.process.mapper import (
    _OCR_FILE_SPLIT,
    _area,
    _current_ward,
    _date,
    _fold,
    _gender,
    _identity,
    _issue_place,
    _ngay_cap_by_mrz,
    _phone,
    _province_label,
    _remap,
    _same_name,
    _strip_admin_prefix,
    _text,
)
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process.mapper import _extract_info_from_cccd
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.schema import UI_COMP_BY_NAME

# Ô bắt buộc (dấu *) mà extension chịu trách nhiệm điền; thiếu dữ liệu → tô đỏ để cán bộ nhập tay.
_EXPECT_NGUOI_NOP = ("data[phoneNumber]", "data[province]", "data[district]", "data[address]")
_EXPECT_CHU_HO_SO = ("data[ownerPhoneNumber]", "data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]")
_EXPECT_DON = (
    "data[TinhThanhPho]", "data[QuanHuyen]", "data[SoNhaDuong]",
    "data[TinhThanhPho1]", "data[QuanHuyen1]", "data[SoNhaDuong1]",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _verbatim(value: Any) -> str | None:
    """Câu chép nguyên văn ('Thuộc đối tượng'): giữ dấu chấm cuối câu, chỉ bỏ dòng dấu chấm chỗ trống ('……')."""
    if value in (None, "", {}, []) or isinstance(value, dict):
        return _text(value)
    text = " ".join(re.sub(r"[.…]{2,}", " ", str(value)).split()).strip(" :;,-")
    return text or None


_ID_CARD_MARKERS = ("can cuoc", "chung minh nhan dan", "identity card", "citizen identity", "personal identification")
# Số định danh đứng riêng (cho phép dấu cách/chấm giữa chữ số); dãy MRZ dính chữ số khác nên không khớp.
_ID_RUN = re.compile(r"(?<!\d)(?:\d[ .]?){8,11}\d(?!\d)")
_CARD_GIOI_TINH = re.compile(r"giới\s*tính[^:\n]*:\s*(nam|nữ)", re.IGNORECASE)
_CARD_THUONG_TRU = re.compile(r"nơi\s+thường\s+trú[^:\n]*:[ \t]*([^\n]*)", re.IGNORECASE)


def card_of_account(text: str, ctx_id: str | None, ctx_name: str | None) -> bool:
    """Đoạn OCR có phải THẺ CCCD của người đăng nhập? So số định danh; thẻ không đọc được số 12 chữ số nào thì
    mới so họ tên (thẻ mang số KHÁC là của người khác dù trùng tên)."""
    folded = _fold(text)
    if not any(marker in folded for marker in _ID_CARD_MARKERS):
        return False
    ids = {re.sub(r"\D+", "", m) for m in _ID_RUN.findall(unicodedata.normalize("NFC", text or ""))}
    if ctx_id and ctx_id in ids:
        return True
    if any(len(i) == 12 for i in ids):
        return False
    name = _fold(ctx_name)
    return bool(name and name in re.sub(r"\s+", " ", folded))


def _account_card(ocr_text: str, ctx_id: str | None, ctx_name: str | None) -> dict:
    """Nhân thân đọc THẲNG từ thẻ CCCD của người đăng nhập trong OCR — dự phòng khi LLM lấy người nộp từ giấy khác
    (vd Giấy tiếp nhận ghi mẹ sinh viên). Trả {gender, tt, ngaycap} hoặc {} nếu hồ sơ không có thẻ đó."""
    if not (ctx_id or ctx_name) or not ocr_text:
        return {}
    for seg in _OCR_FILE_SPLIT.split(unicodedata.normalize("NFC", ocr_text)):
        if not card_of_account(seg, ctx_id, ctx_name):
            continue
        g = _CARD_GIOI_TINH.search(seg)
        tt: dict = {}
        m = _CARD_THUONG_TRU.search(seg)
        if m:
            # Thẻ in địa chỉ xuống dòng: gom dòng tiếp theo tới khi gặp nhãn khác ("Có giá trị đến: …").
            parts = [m.group(1)]
            for line in seg[m.end():].split("\n")[1:3]:
                if not line.strip() or ":" in line or _fold(line).startswith(("co gia tri", "date of")):
                    break
                parts.append(line)
            pieces = [p.strip(" .;") for p in ", ".join(parts).split(",") if p.strip(" .;")]
            # Thẻ ghi "chi tiết, xã, huyện, tỉnh" (cũ) hoặc "chi tiết, xã, tỉnh" (sau sáp nhập).
            if len(pieces) >= 4:
                tt = {"tinh": pieces[-1], "huyen": pieces[-2], "xa": pieces[-3], "diaChi": ", ".join(pieces[:-3])}
            elif len(pieces) == 3:
                tt = {"tinh": pieces[2], "xa": pieces[1], "diaChi": pieces[0]}
        return {
            "gender": _gender(g.group(1)) if g else None,
            "tt": tt,
            "ngaycap": _ngay_cap_by_mrz(ocr_text, ctx_id),
        }
    return {}


def _residence(areas: list[Any], ocr_text: str = "") -> dict:
    """Chọn địa chỉ để điền 3 cấp. Ưu tiên nguồn đầu tiên quy được về phường/xã HIỆN HÀNH; số nhà/đường lấy theo
    chính nguồn đó, nguồn đó không ghi thì lấy nguồn còn lại. Trả {} khi không nguồn nào có tỉnh."""
    picked: list[dict] = []
    for raw in areas:
        area = _area(raw)
        if not area:
            continue
        r = _remap(area, ocr_text)
        tinh = _province_label(r.get("tinh"))
        if not tinh:
            continue
        xa, guess = _current_ward(tinh, _text(r.get("xa")), ocr_text)
        picked.append({"tinh": tinh, "xa": xa, "xa_guess": guess, "diaChi": _text(r.get("diaChi"))})
    if not picked:
        return {}
    best = next((p for p in picked if p["xa"]), picked[0])
    if not best["diaChi"]:
        best = {**best, "diaChi": next((p["diaChi"] for p in picked if p["diaChi"]), None)}
    return best


def _birthplace(raw: Any, ocr_text: str = "") -> dict:
    """Nơi sinh 3 cấp. Giấy khai sinh hay chỉ ghi cơ sở y tế + tỉnh ('Bệnh viện Đa khoa, tỉnh X') → ô Số nhà,
    đường nhận tên cơ sở, ô Phường/Xã để trống cho cán bộ chọn."""
    area = _area(raw)
    if not area:
        text = _text(raw)
        return {"diaChi": text} if text else {}
    r = _remap(area, ocr_text)
    tinh = _province_label(r.get("tinh"))
    xa, guess = _current_ward(tinh, _text(r.get("xa")), ocr_text) if tinh else (None, False)
    dia_chi = _text(r.get("diaChi")) or _text(area.get("diaChi")) or _text(area.get("fullText"))
    return {"tinh": tinh, "xa": xa, "xa_guess": guess, "diaChi": dia_chi}


def enrich(fields: list[dict], options: dict | None = None, ocr_text: str = "") -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:  # giá trị PHỎNG ĐOÁN → extension tô vàng cho cán bộ soát.
            field["default"] = True
        out.append(field)
        seen.add(name)

    def expect(names: tuple[str, ...]) -> None:
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    def add_area(prefix: tuple[str, str, str], res: dict, default: bool = False) -> None:
        tinh_name, xa_name, dia_chi_name = prefix
        add(tinh_name, res.get("tinh"), default=default)
        add(xa_name, res.get("xa"), default=default or res.get("xa_guess", False))
        add(dia_chi_name, res.get("diaChi"), default=default)

    # ===== SINH VIÊN = chủ hồ sơ =====
    sv_name = _text(values.get("SinhVien_HoTen"))
    sv_id = _identity(values.get("SinhVien_SoDinhDanh"))
    sv_dob = _date(values.get("SinhVien_NgaySinh"))
    sv_gender = _gender(values.get("SinhVien_GioiTinh")) or _extract_info_from_cccd(sv_id).get("gender")
    sv_ngaycap = _date(values.get("SinhVien_NgayCap")) or _ngay_cap_by_mrz(ocr_text, sv_id)
    sv_noicap = _issue_place(values.get("SinhVien_NoiCap"), "", sv_ngaycap)
    sv_phone = _phone(values.get("SinhVien_DienThoai"))
    sv_email = _text(values.get("SinhVien_Email"))
    sv_res = _residence([values.get("SinhVien_ThuongTru"), values.get("SinhVien_ThuongTruCCCD")], ocr_text)

    ks_cha = _text(values.get("KhaiSinh_HoTenCha"))
    ks_me = _text(values.get("KhaiSinh_HoTenMe"))

    def _parent_gender(name: str | None) -> str | None:
        if name and _same_name(name, ks_me):
            return "Nữ"
        if name and _same_name(name, ks_cha):
            return "Nam"
        return None

    # ===== NGƯỜI NỘP = LUÔN là người đăng nhập VNeID (formContext) =====
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_is_sv = bool((nop_name and sv_name and _same_name(nop_name, sv_name)) or (nop_id and sv_id and nop_id == sv_id))
    has_nop = bool(nop_name or nop_id) and not nop_is_sv
    nop_phone = _phone(values.get("NguoiNop_DienThoai"))

    ctx = (options or {}).get("formContext") or {}
    ctx_id = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))

    def _is_account(pid: str | None, name: str | None) -> bool:
        """Giấy tờ có phải của người đăng nhập? Có số định danh hai bên thì so số; không thì so họ tên."""
        if ctx_id and pid:
            return ctx_id == pid
        return bool(ctx_name and name and _same_name(ctx_name, name))

    # Thẻ CCCD của người đăng nhập đọc thẳng từ OCR — dự phòng khi LLM lấy NguoiNop_* từ giấy khác.
    card = _account_card(ocr_text, ctx_id, ctx_name) if not _is_account(sv_id, sv_name) else {}
    if _is_account(sv_id, sv_name):
        submitter = "sv"
    elif has_nop and _is_account(nop_id, nop_name):
        submitter = "nop"
    elif card:
        submitter = "card"
    else:
        # Không đối chiếu được (thiếu formContext, hoặc giấy tờ không có người đăng nhập — vd Giấy tiếp nhận ghi
        # mẹ sinh viên nhưng cán bộ đăng nhập): KHÔNG điền Phần I, giữ nguyên dữ liệu cổng đổ từ tài khoản.
        submitter = None

    # ===== Phần I: ô sửa được của người nộp — chỉ khi giấy tờ đúng là của người đăng nhập =====
    if submitter == "sv":
        add("data[gender]", sv_gender)
        add("data[identityDate]", sv_ngaycap)
        add("data[idIssuePlace]", sv_noicap)
        add("data[email]", sv_email)
        add_area(("data[province]", "data[district]", "data[address]"), sv_res)
        add("data[phoneNumber]", sv_phone)
        expect(_EXPECT_NGUOI_NOP)
    elif submitter == "nop":
        nop_ngaycap = _date(values.get("NguoiNop_NgayCap")) or _ngay_cap_by_mrz(ocr_text, nop_id)
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")) or _parent_gender(nop_name)
            or _extract_info_from_cccd(nop_id).get("gender"))
        add("data[identityDate]", nop_ngaycap)
        add("data[idIssuePlace]", _issue_place(values.get("NguoiNop_NoiCap"), "", nop_ngaycap))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add_area(("data[province]", "data[district]", "data[address]"),
                 _residence([values.get("NguoiNop_ThuongTru")], ocr_text))
        add("data[phoneNumber]", nop_phone)
        expect(_EXPECT_NGUOI_NOP)
    elif submitter == "card":
        # SĐT trên Giấy tiếp nhận/đơn là của người khác → không dùng; ô bắt buộc thiếu thì tô đỏ.
        add("data[gender]", card.get("gender") or _extract_info_from_cccd(ctx_id).get("gender"))
        add("data[identityDate]", card.get("ngaycap"))
        add("data[idIssuePlace]", _issue_place(None, "", card.get("ngaycap")))
        add_area(("data[province]", "data[district]", "data[address]"), _residence([card.get("tt")], ocr_text))
        expect(_EXPECT_NGUOI_NOP)
    # SĐT liên hệ của hồ sơ (sinh viên, hoặc người nộp ghi trên Giấy tiếp nhận) — dự phòng cho SĐT chủ hồ sơ.
    submitter_phone = sv_phone or nop_phone

    # ===== Phần II: CHỦ HỒ SƠ = sinh viên =====
    add("data[ChuHS]", "Cá nhân")
    add("data[ownerFullname]", sv_name.upper() if sv_name else None)
    add("data[ownerGender]", sv_gender)
    add("data[ownerIdentityNumber]", sv_id)
    add("data[ownerIdentityDate]", sv_ngaycap)
    add("data[ownerBirthday]", sv_dob)
    add("data[ownerIdentityAgency22]", sv_noicap)
    add("data[ownerNation]", _text(values.get("SinhVien_QuocTich")) or "Việt Nam")
    add("data[ownerEmail]", sv_email)
    # Giấy tờ hiếm khi ghi SĐT sinh viên → dùng SĐT liên hệ của người nộp (tô vàng).
    add("data[ownerPhoneNumber]", sv_phone or submitter_phone, default=not sv_phone)
    add_area(("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]"), sv_res)
    if sv_name:
        add("data[tenHoSo]", f"Đề nghị chi trả tiền miễn, giảm học phí cho học sinh, sinh viên {sv_name.upper()}")
    expect(_EXPECT_CHU_HO_SO)

    # ===== Phần III: Đơn đề nghị chi trả tiền miễn, giảm học phí (Phụ lục IV) =====
    # Tỉnh xử lý = tỉnh nơi sinh viên thường trú (UBND cấp xã nơi thường trú giải quyết). Option không có tiền tố.
    xu_ly = sv_res.get("tinh")
    add("data[province2]", _strip_admin_prefix(xu_ly) if xu_ly else None)
    add("data[d]", _date(values.get("Don_NgayLam")))
    add("data[KinhGui]", _text(values.get("Don_KinhGui")) or _text(values.get("Truong_Ten")))
    add("data[TenChaMe]", _text(values.get("Don_HoTenChaMe")) or ks_cha or ks_me)
    add("data[Lop]", _text(values.get("Don_Lop")))
    add("data[Khoa1]", _text(values.get("Don_NienKhoa")))
    add("data[DoiTuong]", _verbatim(values.get("Don_DoiTuong")) or _verbatim(values.get("GiayXacNhan_DoiTuong")))
    add("data[Khoa2]", _text(values.get("Don_Khoa")))
    noi_sinh = _birthplace(values.get("SinhVien_NoiSinh"), ocr_text)
    add_area(("data[TinhThanhPho]", "data[QuanHuyen]", "data[SoNhaDuong]"), noi_sinh)
    add_area(("data[TinhThanhPho1]", "data[QuanHuyen1]", "data[SoNhaDuong1]"), sv_res)
    expect(_EXPECT_DON)

    if not sv_name:
        warnings.append("Thiếu họ tên học sinh, sinh viên (chủ hồ sơ) — kiểm tra Đơn Phụ lục IV/Giấy xác nhận.")
    if sv_id and len(sv_id) != 12:
        warnings.append(f"Số định danh sinh viên đọc được '{sv_id}' không đủ 12 chữ số — vui lòng kiểm tra CCCD.")
    if noi_sinh.get("tinh") and not noi_sinh.get("xa"):
        warnings.append("Nơi sinh chưa có phường/xã (giấy khai sinh chỉ ghi cơ sở y tế/tỉnh) — vui lòng chọn tay.")
    if not sv_res:
        warnings.append("Chưa đọc được nơi thường trú của sinh viên — vui lòng nhập tay.")
    if _fold(values.get("Don_DoiTuong")) == "" and _fold(values.get("GiayXacNhan_DoiTuong")) == "":
        warnings.append("Chưa đọc được dòng 'Thuộc đối tượng' trên Đơn/Giấy xác nhận.")

    return out, warnings
