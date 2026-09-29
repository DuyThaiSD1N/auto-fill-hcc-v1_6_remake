"""Ánh xạ facts → ô eForm của thủ tục [Lào Cai] đăng ký biến động do chia/tách/sáp nhập tổ chức.

⚑ ĐIỂM KHÁC BIỆT QUAN TRỌNG so với các cổng Form.io: checkbox "Người nộp là chủ hồ sơ"
(`chkbox_nguoinoplachuhs`) của cổng CHỈ sao chép sang khối chủ hồ sơ tới Nơi cấp / Ngày cấp căn cước —
KHÔNG sao chép tỉnh/xã/địa chỉ. Vì vậy mapper LUÔN phát ĐẦY ĐỦ khối chủ hồ sơ (gồm cả 3 ô địa chỉ), kể
cả khi người nộp trùng chủ hồ sơ, thay vì trông vào checkbox đó. Cũng không phát chính checkbox: để cán
bộ tự quyết, tránh cổng tự xoá dữ liệu đã điền khi trạng thái checkbox đổi.

⚑ Trang "Thành phần hồ sơ" có thêm 2 textarea: `HoSoOnline_veViec` (BẮT BUỘC — trích yếu hồ sơ, cổng tự
điền sẵn TÊN THỦ TỤC nên phải ghi đè bằng trích yếu thật của Đơn) và `HoSoOnline_ghiChu`.

⚑ HAI CHẾ ĐỘ KHỐI NGƯỜI NỘP (cổng đối chiếu Họ tên + Số Căn cước + Ngày sinh với CSDL quốc gia dân cư và
tài khoản đăng nhập → cả khối phải là MỘT người):
  · THEO TÀI KHOẢN (mặc định; thiếu `options.formContext` — bản extension cũ, hoặc popup không đọc được
    trang — coi là chưa có mốc): chọn ứng viên khớp mốc (số định danh trước, thiếu số mới theo
    họ tên), bù nhân thân chỉ từ bản ghi của chính người đó; KHÔNG ghi hai ô readonly Họ tên/Số Căn cước
    (cổng đã đổ đúng tài khoản). Không có mốc / không tìm thấy → bỏ trống cả khối + cảnh báo.
  · THEO TỜ KHAI (`submitterMode="owner_as_submitter"`): bên được ủy quyền → người ký đơn (NguoiNop_*)
    → chủ hồ sơ cá nhân; ghi hai ô readonly theo người đó (đi trước), XOÁ ô nhân thân tài khoản mà hồ sơ
    không có (`_shared/lao_cai_nguoi_nop.chot_khoi_nguoi_nop`); lệch tài khoản thì cảnh báo cổng sẽ chặn
    nộp.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.lao_cai_nguoi_nop import chot_khoi_nguoi_nop
from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process.schema import (
    UI_ALIASES,
    UI_CHU_HO_SO_CA_NHAN,
    UI_COMP_BY_NAME,
)

_DOI_TUONG_TO_CHUC = "Tổ chức"
_DOI_TUONG_CA_NHAN = "Cá nhân"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _area(value) -> dict | None:
    """Địa chỉ thường là object {quocGia,tinh,xa,diaChi}; chuỗi trần thì dồn vào diaChi."""
    if isinstance(value, str):
        text = _plain(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _digits(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    return re.sub(r"\D", "", text) or None


def _tax_code(value) -> str | None:
    """Mã số thuế giữ được dấu '-' của mã đơn vị phụ thuộc (vd 5300xxxxxx-001)."""
    text = _plain(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9-]", "", text).strip("-")
    return cleaned or None


def _phone(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _date(value) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1980") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _trich_yeu(values: dict) -> str | None:
    """Trích yếu ô "Về việc". Cổng tự điền sẵn TÊN THỦ TỤC nên phải ghi đè bằng nội dung thật của Đơn.

    Ưu tiên câu LLM đọc từ Đơn Mẫu 24; không có thì ghép tất định từ nội dung biến động + thửa đất.
    Không đọc được số thửa → không phát field (không bịa).
    """
    san_co = _plain(values.get("Don_TrichYeu"))
    if san_co:
        return san_co
    so_thua = _plain(values.get("ThuaDat_SoThua"))
    if not so_thua:
        return None
    noi_dung = _plain(values.get("Don_NoiDungBienDong"))
    parts = [f"Đăng ký biến động - {noi_dung}, thửa {so_thua}" if noi_dung
             else f"Đăng ký biến động đất đai, tài sản gắn liền với đất thửa {so_thua}"]
    to_ban_do = _plain(values.get("ThuaDat_ToBanDo"))
    if to_ban_do:
        parts.append(f"tờ bản đồ {to_ban_do}")
    thua_dat = _area(values.get("ThuaDat_DiaChi"))
    if thua_dat:
        dia_chi = ", ".join(
            x for x in (_plain(thua_dat.get("diaChi")), _plain(thua_dat.get("xa")),
                        _province_label(thua_dat.get("tinh"))) if x
        )
        if dia_chi:
            parts.append(dia_chi)
    return ", ".join(parts)


# ----- Người nộp: ứng viên + chọn người (chế độ TÀI KHOẢN / TỜ KHAI) -----
# Mọi ứng viên quy về cùng một bộ khoá để so khớp và bù nhân thân.
_PERSON_KEYS = ("HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "DanToc", "NgayCap", "NoiCap",
                "NoiCuTru", "DienThoai", "Email", "Fax")
_DATE_KEYS = ("NgaySinh", "NgayCap")


def _empty(value) -> bool:
    return value in (None, "", {}, [])


def _get(person: dict | None, key: str):
    value = (person or {}).get(key)
    return None if _empty(value) else value


def _text(value) -> str | None:
    """Ứng viên là dữ liệu tự do của LLM — năm sinh có thể về dạng số nguyên."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(int(value))
    return _plain(value)


def _is_candidate(person: dict | None) -> bool:
    return bool(person) and bool(_get(person, "HoTen") or _get(person, "SoDinhDanh"))


def _people(values: dict, name: str) -> list[dict]:
    items = values.get(name)
    if not isinstance(items, list):
        return []
    return [p for p in items if isinstance(p, dict) and _is_candidate(p)]


def _pick(source: dict, *keys):
    for key in keys:
        if not _empty(source.get(key)):
            return source[key]
    return None


def _proxy_person(values: dict) -> dict | None:
    """Bên được ủy quyền — object khoá camelCase theo desc của schema."""
    proxy = values.get("NguoiDuocUyQuyen")
    if isinstance(proxy, list) and len(proxy) == 1:
        proxy = proxy[0]
    if not isinstance(proxy, dict):
        return None
    person = {
        "HoTen": _pick(proxy, "hoTen", "HoTen"),
        "SoDinhDanh": _pick(proxy, "soDinhDanh", "SoDinhDanh"),
        "NgaySinh": _pick(proxy, "ngaySinh", "NgaySinh"),
        "GioiTinh": _pick(proxy, "gioiTinh", "GioiTinh"),
        "DanToc": _pick(proxy, "danToc", "DanToc"),
        "NgayCap": _pick(proxy, "ngayCapCccd", "NgayCap"),
        "NoiCap": _pick(proxy, "noiCapCccd", "NoiCap"),
        "DienThoai": _pick(proxy, "dienThoai", "DienThoai"),
        "Email": _pick(proxy, "email", "Email"),
        "NoiCuTru": _pick(proxy, "thuongTru", "NoiCuTru"),
    }
    return person if _is_candidate(person) else None


def _flat_person(values: dict, prefix: str) -> dict | None:
    """Khối phẳng NguoiNop_*/ChuHoSo_* dạng ứng viên."""
    person = {key: values.get(f"{prefix}_{key}") for key in _PERSON_KEYS}
    return person if _is_candidate(person) else None


def _year(value) -> str | None:
    match = re.search(r"(\d{4})$", _text(value) or "")
    return match.group(1) if match else None


def _dob_conflict(left: dict, right: dict) -> bool:
    """Cùng họ tên mà ngày sinh mâu thuẫn là hai người khác nhau (cha/con trùng tên)."""
    a, b = _text(_get(left, "NgaySinh")), _text(_get(right, "NgaySinh"))
    if not a or not b:
        return False
    full_a, full_b = _date(a), _date(b)
    if full_a and full_b:
        return full_a != full_b
    return _year(a) != _year(b)


def _same_person(base: dict, person: dict, base_id: str | None) -> bool:
    """Khớp SỐ ĐỊNH DANH khi cả hai phía có số; chỉ khi một phía thiếu số mới khớp HỌ TÊN bỏ dấu."""
    person_id = _digits(_get(person, "SoDinhDanh"))
    if base_id and person_id:
        return base_id == person_id
    base_name = _fold(_get(base, "HoTen"))
    return bool(base_name) and base_name == _fold(_get(person, "HoTen")) and not _dob_conflict(base, person)


def _merge_person(
    base: dict | None, groups: list[list[dict]], known_id: str | None = None
) -> dict | None:
    """Bù mục còn thiếu của `base` CHỈ từ bản ghi của CHÍNH người đó.

    Khối phẳng/giấy ủy quyền hay thiếu dân tộc, nơi cấp, địa chỉ — những thứ nằm ở ảnh CCCD. Không gộp
    theo "cùng nguồn" vì khối phẳng có thể đã bị LLM ghép chéo hai người. `known_id` là số định danh đã
    biết chắc của người này (mốc tài khoản) khi giấy tờ của họ không ghi số — chặn gộp nhầm người trùng
    tên nhưng khác số.
    """
    if not base:
        return None
    merged = dict(base)
    for group in groups:
        for person in group:
            if person is base:
                continue
            # Tính lại mỗi vòng: vừa bù được số định danh thì các lượt sau phải khớp theo số.
            base_id = _digits(_get(merged, "SoDinhDanh")) or known_id
            if not _same_person(merged, person, base_id):
                continue
            for key in _PERSON_KEYS:
                value = _get(person, key)
                if value is None:
                    continue
                current = _get(merged, key)
                # Ngày chỉ có năm coi như thiếu: bản ghi khác của cùng người có ngày đủ thì lấy ngày đủ.
                if current is None or (key in _DATE_KEYS and not _date(_text(current))
                                       and _date(_text(value))):
                    merged[key] = value
    return merged


def _find_by_anchor(groups: list[list[dict]], anchor_id: str | None, anchor_name: str) -> dict | None:
    """Ứng viên khớp mốc tài khoản — theo SỐ ĐỊNH DANH trước, thiếu số mới theo HỌ TÊN (duy nhất 1 người)."""
    if anchor_id:
        for group in groups:
            for person in group:
                if _digits(_get(person, "SoDinhDanh")) == anchor_id:
                    return person
    if not anchor_name:
        return None
    hits = [
        person for group in groups for person in group
        # Mốc có số mà giấy tờ cũng có số (khác số) → người khác, không xét theo tên.
        if not (anchor_id and _digits(_get(person, "SoDinhDanh")))
        and _fold(_get(person, "HoTen")) == anchor_name
    ]
    if not hits:
        return None
    # Nhiều bản ghi cùng tên chỉ chấp nhận khi chắc là MỘT người (số định danh, ngày sinh không mâu thuẫn).
    first = hits[0]
    ids = {_digits(_get(p, "SoDinhDanh")) for p in hits} - {None}
    if len(ids) > 1 or any(_dob_conflict(first, other) for other in hits[1:]):
        return None
    return first


def _nguoi_nop_hai_che_do(
    values: dict, options: dict, is_org: bool, theo_to_khai: bool, add
) -> tuple[dict | None, list[str]]:
    """Khối người nộp cho extension có gửi mốc tài khoản (hoặc bật chế độ tờ khai).

    Trả (địa chỉ của người nộp đã chọn, cảnh báo). Cổng gửi Họ tên + Số Căn cước + Ngày sinh của khối
    này sang CSDL quốc gia dân cư và đối chiếu tài khoản đăng nhập → cả khối là của MỘT người.
    """
    warnings: list[str] = []
    ctx = options.get("formContext")
    ctx = ctx if isinstance(ctx, dict) else {}
    anchor_id_raw = _text(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_id = _digits(anchor_id_raw)
    anchor_name_raw = _plain(ctx.get("applicantFullname"))
    anchor_name = _fold(anchor_name_raw)
    has_anchor = bool(anchor_id or anchor_name)

    proxy = _proxy_person(values)
    flat_nop = _flat_person(values, "NguoiNop")
    owner = None if is_org else _flat_person(values, "ChuHoSo")
    # Thứ tự ưu tiên nguồn: CCCD rời (đủ nhất) → người ghi kèm số trong giấy tờ → giấy ủy quyền →
    # khối phẳng người nộp → chủ hồ sơ cá nhân.
    groups = [
        _people(values, "DanhSachCccd"),
        _people(values, "NguoiTrongGiayTo"),
        [proxy] if proxy else [],
        [flat_nop] if flat_nop else [],
        [owner] if owner else [],
    ]

    if theo_to_khai:
        # Bên được ủy quyền đi nộp thay; không có thì người ký đơn (khối phẳng), cuối cùng là chủ hồ sơ
        # cá nhân — tổ chức không tự đi nộp.
        base = proxy or flat_nop or owner
        person = _merge_person(base, groups)
        if not person:
            warnings.append(
                "Bật cài đặt \"Người nộp = chủ hồ sơ\" nhưng hồ sơ không có văn bản ủy quyền và cũng không "
                "đọc được người đứng tên đơn, nên trợ lý để trống khối \"Thông tin người nộp hồ sơ\" — cán "
                "bộ nhập tay."
            )
            return None, warnings
        ten = _plain(_get(person, "HoTen"))
        so_cmnd = _digits(_get(person, "SoDinhDanh"))
        if has_anchor:
            if anchor_id and so_cmnd:
                lech = anchor_id != so_cmnd
            else:
                lech = bool(anchor_name and ten) and anchor_name != _fold(ten)
            if lech:
                warnings.append(
                    "Khối \"Thông tin người nộp hồ sơ\" đang điền theo TỜ KHAI ("
                    + (ten or "người trong hồ sơ")
                    + ") nhưng tài khoản đang đăng nhập là "
                    + (anchor_name_raw or anchor_id_raw or "người khác")
                    + ". Cổng xác thực Họ tên/Số Căn cước/Ngày sinh với CSDL quốc gia dân cư và tài khoản "
                    "đăng nhập trước khi cho nộp — lệch là bị chặn. Đăng nhập đúng tài khoản người đi nộp, "
                    "hoặc tắt cài đặt \"Người nộp = chủ hồ sơ\"."
                )
    else:
        if not has_anchor:
            warnings.append(
                "Không xác định được NGƯỜI ĐANG ĐI NỘP: cổng chưa đổ sẵn Họ tên/Số Căn cước từ tài khoản "
                "định danh (hoặc trang chưa đăng nhập). Trợ lý bỏ trống nhân thân khối \"Thông tin người "
                "nộp hồ sơ\" để khỏi điền nhầm người — đăng nhập đúng tài khoản người đi nộp rồi quét lại."
                " Vừa cập nhật/tải lại extension thì F5 trang cổng rồi quét lại; người nộp theo tờ khai thì "
                "bật cài đặt \"Người nộp = chủ hồ sơ\"."
            )
            return None, warnings
        found = _find_by_anchor(groups, anchor_id, anchor_name)
        if not found:
            warnings.append(
                "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
                + (f" ({anchor_name_raw})" if anchor_name_raw else "")
                + " nên trợ lý để trống khối \"Thông tin người nộp hồ sơ\" — cán bộ nhập tay, KHÔNG lấy "
                "thông tin của người khác trong hồ sơ vì cổng xác thực với CSDL quốc gia dân cư trước khi "
                "cho nộp."
            )
            return None, warnings
        person = _merge_person(found, groups, known_id=anchor_id)

    # Theo tài khoản: hai ô readonly Họ tên/Số Căn cước cổng đã đổ đúng → không ghi. Theo tờ khai: đi
    # TRƯỚC để phần nhân thân bên dưới thuộc về đúng người ở hai ô đầu.
    if theo_to_khai:
        add("CongDan_tenCongDan", ten)
        add("CongDan_soCmnd", so_cmnd)
    doc_id = _digits(_get(person, "SoDinhDanh"))
    ngay_cap = _date(_text(_get(person, "NgayCap")))
    # Nơi cấp mặc định CHỈ khi giấy tờ của chính người đó có số định danh — không thì là bịa.
    noi_cap = normalize_issuer(_plain(_get(person, "NoiCap")))
    if not noi_cap and doc_id:
        noi_cap = default_issuer(ngay_cap)
    add("CongDan_ngaySinhCongDan", _date(_text(_get(person, "NgaySinh"))))
    add("CongDan_gioiTinhCongDan", _plain(_get(person, "GioiTinh")))
    add("CongDan_danTocCongDan", _plain(_get(person, "DanToc")))
    add("CongDan_ngayCapCmnd", ngay_cap)
    add("CongDan_noiCapCmnd", noi_cap)
    add("CongDan_diDong", _phone(_text(_get(person, "DienThoai"))))
    add("CongDan_email", _plain(_get(person, "Email")))
    add("CongDan_fax", _text(_get(person, "Fax")))
    return _area(_get(person, "NoiCuTru")), warnings


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "có", "1"):
        return True
    return bool(values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    options = options if isinstance(options, dict) else {}
    # Cài đặt "Người nộp = chủ hồ sơ" của extension: bỏ mốc tài khoản, lấy người nộp theo tờ khai.
    theo_to_khai = str(options.get("submitterMode") or "") == "owner_as_submitter"
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    is_org = _is_org(values)

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        # Chọn đối tượng "Tổ chức" làm cổng display:none 7 ô cá nhân của khối chủ hồ sơ — điền vào ô ẩn
        # là dữ liệu không ai thấy, mà vẫn bị cổng gửi lên.
        if is_org and name in UI_CHU_HO_SO_CA_NHAN:
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    ten_to_chuc = _plain(values.get("ChuHoSo_TenToChuc"))
    ma_so_thue = _tax_code(values.get("ChuHoSo_MaSoThue"))

    # --- Khối NGƯỜI NỘP ---
    nop_area, nop_warnings = _nguoi_nop_hai_che_do(values, options, is_org, theo_to_khai, add)
    warnings.extend(nop_warnings)
    if is_org:
        # Ô tên cơ quan/MST của khối người nộp là dữ liệu của TỔ CHỨC chủ hồ sơ → phát được cả khi
        # chưa xác định được ai đi nộp.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)
    if nop_area:
        add("CongDan_maTinhThanh", _province_label(nop_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
        add("CongDan_diaChi", _plain(nop_area.get("diaChi")))

    # --- Khối CHỦ HỒ SƠ: phát ĐỦ, KHÔNG dựa vào checkbox "Người nộp là chủ hồ sơ" ---
    add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_TO_CHUC if is_org else _DOI_TUONG_CA_NHAN)
    add("ChuHoSo_tenChuHoSo", _plain(values.get("ChuHoSo_HoTen")))
    add("ChuHoSo_ngaySinhChuHoSo", _date(values.get("ChuHoSo_NgaySinh")))
    add("ChuHoSo_gioiTinhChuHoSo", _plain(values.get("ChuHoSo_GioiTinh")))
    add("ChuHoSo_danTocChuHoSo", _plain(values.get("ChuHoSo_DanToc")))
    chs_ngay_cap = _date(values.get("ChuHoSo_NgayCap"))
    chs_identity = _digits(values.get("ChuHoSo_SoDinhDanh"))
    chs_noi_cap = normalize_issuer(_plain(values.get("ChuHoSo_NoiCap")))
    if not chs_noi_cap and chs_identity:
        chs_noi_cap = default_issuer(chs_ngay_cap)
    add("ChuHoSo_soCMNDChuHoSo", chs_identity)
    add("ChuHoSo_ngayCapCMNDCHS", chs_ngay_cap)
    add("ChuHoSo_noiCapCMNDCHS", chs_noi_cap)
    add("ChuHoSo_diDongLienLacCHS", _phone(values.get("ChuHoSo_DienThoai")))
    add("ChuHoSo_emailChuHoSo", _plain(values.get("ChuHoSo_Email")))
    add("ChuHoSo_faxChuHoSo", _plain(values.get("ChuHoSo_Fax")))
    if is_org:
        add("ChuHoSo_tenCoQuanToChucCHS", ten_to_chuc)
        add("ChuHoSo_maSoThueChuHoSo", ma_so_thue)
        if not ten_to_chuc:
            warnings.append(
                "Chủ hồ sơ là TỔ CHỨC nhưng không đọc được tên tổ chức mới — cán bộ nhập tay ô \"Tên cơ "
                "quan/tổ chức\". Tên trên Giấy chứng nhận là tổ chức CŨ, không dùng thay được."
            )

    # 3 ô địa chỉ này là thứ checkbox của cổng KHÔNG copy → luôn phát từ dữ liệu trích được.
    # Nguồn giữ như luồng cũ (khối phẳng) — không phụ thuộc người nộp vừa chọn theo mốc.
    chs_area = _area(values.get("ChuHoSo_NoiCuTru")) or _area(values.get("NguoiNop_NoiCuTru"))
    if chs_area:
        add("ChuHoSo_maTinhThanhCHS", _province_label(chs_area.get("tinh")))
        add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
        add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
    else:
        warnings.append(
            "Không đọc được địa chỉ chủ hồ sơ. Nút \"Người nộp là chủ hồ sơ\" của cổng KHÔNG sao chép "
            "địa chỉ, cán bộ cần nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ."
        )

    # Địa danh SAU SÁP NHẬP: quyết định cũ ghi đơn vị hành chính đã bỏ (vd "xã Minh Bảo, tỉnh Yên Bái"),
    # remap_area đổi được tỉnh nhưng xã cũ không còn trong danh mục → trả rỗng. Báo để cán bộ chọn tay
    # thay vì để trống im lặng.
    if chs_area and _plain(chs_area.get("tinh")) and not _plain(chs_area.get("xa")):
        warnings.append(
            "Địa chỉ chủ hồ sơ ghi theo đơn vị hành chính CŨ (trước sáp nhập) nên không khớp danh mục "
            "hiện hành — cán bộ chọn tay ô Phường/Xã của khối chủ hồ sơ."
        )

    # --- Bước "Thành phần hồ sơ" ---
    add("HoSoOnline_veViec", _trich_yeu(values))

    out = chot_khoi_nguoi_nop(
        out, theo_to_khai=theo_to_khai, comp_by_name=UI_COMP_BY_NAME, warnings=warnings
    )
    return out, warnings
