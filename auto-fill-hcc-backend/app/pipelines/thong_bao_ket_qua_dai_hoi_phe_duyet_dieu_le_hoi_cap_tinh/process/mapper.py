"""Map compact source facts → Form.io data[...] fields cho "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê
duyệt điều lệ hội (cấp tỉnh)" (1.012943, cổng DVCQG).

Theo mapping của thủ tục:
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] / data[chonDoiTuong] cổng khoá theo tài
  khoản → KHÔNG phát. Giới tính, ngày cấp, nơi cấp, địa chỉ chỉ lấy từ CCCD KHỚP tài khoản; không có thẻ thì giới
  tính suy từ số định danh của tài khoản.
- Phần II chủ hồ sơ: cổng tích sẵn "Người nộp hồ sơ là chủ hồ sơ" (Phần II chép từ Phần I). Chỉ khi hồ sơ có CCCD
  của người ký TM. Ban chấp hành và người đó KHÁC tài khoản mới bỏ tích và điền Phần II theo thẻ đó.
- Phần III datagrid "Hồ sơ kèm theo gồm": mỗi giấy tờ gửi kèm một dòng, Loại bản "Bản chính".
- Phần IV mẫu khai: tên hội, số văn bản, ngày đại hội, loại đại hội, "Lần thứ ..., nhiệm kỳ ...", địa điểm, toàn văn
  quyết nghị, datagrid "Hồ sơ gửi kèm theo" (Tên giấy tờ / Loại giấy tờ), TM. Ban chấp hành.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import (
    _multiline,
    _paper_names,
    _person_matches,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date as _date_slash,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _phone,
    _same_name,
    _text,
)
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.process.schema import (
    DAI_HOI_BAT_THUONG,
    DAI_HOI_NHIEM_KY,
    MAX_HO_SO_ROWS,
    UI_COMP_BY_NAME,
)

_VN_DATE_RE = re.compile(r"(\d{1,2})\s*(?:và\s*(?:ngày\s*)?\d{1,2}\s*)?tháng\s*(\d{1,2})\s*năm\s*(\d{4})",
                         re.IGNORECASE)
_ROMAN_RE = re.compile(r"^[IVXLC]+$")

# Tên loại văn bản (đầu tên giấy tờ, đã bỏ dấu) → nhãn cột "Loại giấy tờ" của datagrid mẫu khai.
_LOAI_GIAY_TO = (
    ("du thao dieu le", "Dự thảo Điều lệ"),
    ("dieu le", "Điều lệ"),
    ("danh sach", "Danh sách"),
    ("nghi quyet", "Nghị quyết"),
    ("bien ban", "Biên bản"),
    ("bao cao", "Báo cáo"),
    ("don ", "Đơn"),
    ("so yeu ly lich", "Sơ yếu lý lịch"),
    ("phieu ly lich tu phap", "Phiếu lý lịch tư pháp"),
    ("chuong trinh", "Chương trình"),
    ("quyet dinh", "Quyết định"),
    ("cong van", "Công văn"),
    ("to trinh", "Tờ trình"),
    ("de an", "Đề án"),
    ("thong bao", "Thông báo"),
)


def _date(value: Any) -> str | None:
    """dd/mm/yyyy; văn bản hay ghi "17 và 18 tháng 9 năm 2026" → lấy ngày đầu."""
    m = _VN_DATE_RE.search(_text(value) or "")
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    return _date_slash(value)


def _loai_dai_hoi(value: Any) -> str:
    """"nhiem_ky" / "bat_thuong" / "thanh_lap"; không rõ → nhiệm kỳ (trường hợp phổ biến nhất)."""
    folded = _fold(value)
    if "bat thuong" in folded:
        return "bat_thuong"
    if "thanh lap" in folded:
        return "thanh_lap"
    return "nhiem_ky"


def _nhiem_ky(value: Any) -> str | None:
    m = re.search(r"(\d{4})\D{1,5}(\d{4})", _text(value) or "")
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _lan_thu(value: Any) -> str | None:
    """"Lần thứ I" / "lần thứ 7" / "VII" → "I" / "7" / "VII"."""
    text = _text(value) or ""
    text = re.sub(r"(?i)^\s*(?:đại hội\s*)?(?:lần\s*thứ)\s*", "", text).strip(" .,:")
    if not text:
        return None
    upper = text.upper()
    if _ROMAN_RE.match(upper):
        return upper
    m = re.match(r"\d{1,3}", text)
    return m.group(0) if m else None


def _nhiem_ky_text(values: dict) -> str | None:
    """Ô "Nhiệm kỳ" (placeholder "Lần thứ ...") → "Lần thứ I, nhiệm kỳ 2026-2031"."""
    lan_thu = _lan_thu(values.get("LanThu"))
    nhiem_ky = _nhiem_ky(values.get("NhiemKy"))
    parts = []
    if lan_thu:
        parts.append(f"Lần thứ {lan_thu}")
    if nhiem_ky:
        parts.append(f"nhiệm kỳ {nhiem_ky}" if parts else f"Nhiệm kỳ {nhiem_ky}")
    return ", ".join(parts) or None


def _loai_giay_to(paper: str) -> str:
    folded = _fold(paper).strip() + " "
    for prefix, label in _LOAI_GIAY_TO:
        if folded.startswith(prefix):
            return label
    for prefix, label in _LOAI_GIAY_TO:
        if prefix.strip() in folded[:40]:
            return label
    return "Văn bản"


def _ghi_chu(values: dict) -> str | None:
    """"Báo cáo kết quả Đại hội Hội X lần thứ I, nhiệm kỳ 2026-2031"."""
    ten_hoi = _text(values.get("TenHoi"))
    if not ten_hoi:
        return None
    text = "Báo cáo kết quả Đại hội"
    loai = _loai_dai_hoi(values.get("LoaiDaiHoi"))
    if loai == "bat_thuong":
        text += " bất thường"
    elif loai == "thanh_lap":
        text += " thành lập"
    text += f" {ten_hoi}"
    nhiem_ky = _nhiem_ky_text(values)
    if nhiem_ky:
        text += f" {nhiem_ky[0].lower()}{nhiem_ky[1:]}"
    return text


def _list(value: Any) -> list[str]:
    items = value if isinstance(value, list) else [value] if value not in (None, "") else []
    return [t for t in (_text(i) for i in items) if t]


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    nguoi_ky = _text(values.get("NguoiKy_TMBCH"))
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    # CCCD trích ra phải đúng của người ký TM. BCH; thẻ của người khác thì không dùng làm chủ hồ sơ.
    owner_card = bool(owner_name or owner_id) and (not nguoi_ky or not owner_name or _same_name(owner_name, nguoi_ky))
    owner_is_account = has_ctx and owner_card and _person_matches(owner_name, owner_id, ctx_name, ctx_identity)
    owner_differs = owner_card and has_ctx and not owner_is_account

    # --- Phần I: người nộp — chỉ từ CCCD khớp tài khoản ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_ok = has_ctx and bool(nop_name or nop_id) and _person_matches(nop_name, nop_id, ctx_name, ctx_identity)
    if nop_ok:
        prefix = "NguoiNop"
    elif owner_is_account:
        prefix = "ChuHoSo"
    else:
        prefix = None
    if prefix:
        add("data[gender]", _gender(values.get(f"{prefix}_GioiTinh")))
        add("data[identityDate]", _date(values.get(f"{prefix}_NgayCap")))
        add("data[idIssuePlace]", _issuer(values.get(f"{prefix}_NoiCap")))
        nop_area = _area(values.get(f"{prefix}_DiaChi"))
        if nop_area:
            add("data[province]", province_label(nop_area.get("tinh")))
            add("data[district]", _text(nop_area.get("xa")))
            add("data[address]", _text(nop_area.get("diaChi")))
    add("data[gender]", _gender_from_identity(ctx_identity))
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")) if has_ctx else None)

    # --- Phần II: chủ hồ sơ ---
    # Bỏ tích phải phát TRƯỚC: các ô Phần II chỉ mở khoá sau khi bỏ tích.
    add("data[isOwnerDossierCheck]", not owner_differs)
    if owner_differs:
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", _date(values.get("ChuHoSo_NgaySinh")))
        add("data[ownerGender]", _gender(values.get("ChuHoSo_GioiTinh")) or _gender_from_identity(owner_id))
        add("data[ownerIdentityNumber]", owner_id)
        add("data[ownerIdentityDate]", _date(values.get("ChuHoSo_NgayCap")))
        add("data[ownerIdIssuePlace]", _issuer(values.get("ChuHoSo_NoiCap")))
        owner_area = _area(values.get("ChuHoSo_DiaChi"))
        if owner_area:
            add("data[ownerProvince]", province_label(owner_area.get("tinh")))
            add("data[ownerDistrict]", _text(owner_area.get("xa")))
            add("data[ownerAddress]", _text(owner_area.get("diaChi")))
        nation = _text(values.get("ChuHoSo_QuocTich"))
        add("data[ownerNation]", "Việt Nam" if not nation or "viet nam" in _fold(nation) else nation)
    add("data[ghiChu]", _ghi_chu(values))

    # --- Phần III + datagrid mẫu khai: giấy tờ gửi kèm ---
    papers = _paper_names(values.get("DanhMucHoSo"))
    # Chính văn bản báo cáo là mẫu khai, không phải giấy tờ gửi kèm.
    papers = [p for p in papers if not _fold(p).startswith(("to trinh", "van ban bao cao ket qua"))]
    for i, paper in enumerate(papers[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{i}][textField1]", paper)
        add(f"data[hoSoDinhKem][{i}][textField2]", "Bản chính")
        add(f"data[HoSo][{i}][textField1]", paper)
        add(f"data[HoSo][{i}][textField2]", _loai_giay_to(paper))

    # --- Phần IV: mẫu khai văn bản báo cáo kết quả đại hội ---
    loai = _loai_dai_hoi(values.get("LoaiDaiHoi"))
    add("data[TenHoi]", _text(values.get("TenHoi")))
    add("data[So]", _text(values.get("SoVanBan")))
    add("data[NgayTl]", _date(values.get("NgayDaiHoi")))
    if loai != "thanh_lap":
        add("data[DaiHoiTl]", DAI_HOI_BAT_THUONG if loai == "bat_thuong" else DAI_HOI_NHIEM_KY)
    add("data[NhiemKy]", _nhiem_ky_text(values))
    add("data[ToChucTai]", _text(values.get("DiaDiem")))
    add("data[NoiDung]", _multiline(values.get("NoiDung")))
    add("data[TM.BCH]", nguoi_ky)

    # --- Cảnh báo ---
    for label, name in (
        ("Tên hội", "data[TenHoi]"),
        ("Ngày đại hội", "data[NgayTl]"),
        ("Nhiệm kỳ", "data[NhiemKy]"),
        ("Hội đã được tổ chức tại", "data[ToChucTai]"),
        ("Đại hội đã thảo luận và thông qua nội dung sau", "data[NoiDung]"),
        ("TM. Ban chấp hành", "data[TM.BCH]"),
    ):
        if name not in seen:
            warnings.append(f"Không đọc được '{label}' (bắt buộc) trong hồ sơ — vui lòng nhập tay ở mẫu khai.")
    if loai == "thanh_lap":
        warnings.append("Hồ sơ là đại hội thành lập — ô loại đại hội của mẫu khai chỉ có 'Đại hội nhiệm kỳ' / 'Đại "
                        "hội bất thường', vui lòng tự chọn.")
    so = _text(values.get("SoVanBan"))
    so_number = re.match(r"\s*(\d*)", so or "").group(1)
    if so and (not so_number or int(so_number) == 0):
        warnings.append(f"Số văn bản đọc được '{so}' thiếu phần số (thường viết tay) — đối chiếu Tờ trình và sửa ô "
                        "'Số văn bản'.")
    for note in _list(values.get("SaiLech")):
        warnings.append(f"Giấy tờ ghi lệch nhau: {note} — đối chiếu bản gốc trước khi nộp.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Hồ sơ không ghi số điện thoại của người nộp — ô SĐT Phần I (bắt buộc) vui lòng nhập tay.")
    if not has_ctx:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — chưa điền nhân thân người nộp (Phần I), "
                        "vui lòng nhập tay.")
    elif not prefix:
        warnings.append("Hồ sơ không có CCCD khớp người nộp — vui lòng tự nhập ngày cấp, nơi cấp, địa chỉ của người "
                        "nộp.")
    if owner_differs:
        warnings.append(f"Đã bỏ tích 'Người nộp hồ sơ là chủ hồ sơ' và điền Phần II theo CCCD của người ký TM. Ban "
                        f"chấp hành ({owner_name or owner_id}) — kiểm tra lại số điện thoại, email chủ hồ sơ.")
    if not papers:
        warnings.append("Không lập được danh mục 'Hồ sơ kèm theo gồm' — vui lòng nhập tay từng giấy tờ.")
    elif len(papers) > MAX_HO_SO_ROWS:
        warnings.append(f"Hồ sơ có {len(papers)} giấy tờ, chỉ điền {MAX_HO_SO_ROWS} dòng đầu vào danh mục hồ sơ — "
                        "nhập thêm phần còn lại.")
    return out, warnings
