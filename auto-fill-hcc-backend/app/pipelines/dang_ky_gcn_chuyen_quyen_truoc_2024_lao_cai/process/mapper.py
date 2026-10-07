"""Ánh xạ facts → ô eForm của thủ tục [Lào Cai] đăng ký, cấp GCN khi đã chuyển quyền trước 01/8/2024.

⚑ ĐIỂM KHÁC BIỆT QUAN TRỌNG so với các cổng Form.io: checkbox "Người nộp là chủ hồ sơ"
(`chkbox_nguoinoplachuhs`) của cổng CHỈ sao chép sang khối chủ hồ sơ tới Nơi cấp / Ngày cấp căn cước —
KHÔNG sao chép tỉnh/xã/địa chỉ. Vì vậy mapper LUÔN phát ĐẦY ĐỦ khối chủ hồ sơ (gồm cả 3 ô địa chỉ), kể
cả khi người nộp trùng chủ hồ sơ, thay vì trông vào checkbox đó. Cũng không phát chính checkbox: để cán
bộ tự quyết, tránh cổng tự xoá dữ liệu đã điền khi trạng thái checkbox đổi.

⚑ Trang "Thành phần hồ sơ" có thêm 2 textarea: `HoSoOnline_veViec` (BẮT BUỘC — trích yếu hồ sơ, cổng tự
điền sẵn TÊN THỦ TỤC nên phải ghi đè bằng trích yếu thật của Đơn) và `HoSoOnline_ghiChu`.

⚑ HAI CHẾ ĐỘ khối NGƯỜI NỘP (cổng đối chiếu Họ tên + Số Căn cước + Ngày sinh với CSDL quốc gia dân cư và
tài khoản đăng nhập trước khi cho nộp → cả khối phải là MỘT người):
  · THEO TÀI KHOẢN (mặc định; thiếu `options.formContext` — bản extension cũ, hoặc popup không đọc được
    trang — coi là chưa có mốc): mốc = Họ tên + Số Căn cước cổng đổ sẵn. Chọn ứng viên khớp mốc
    (CCCD → người trong giấy tờ → bên được ủy quyền → khối phẳng NguoiNop_* → ChuHoSo_* cá nhân), bù nhân
    thân chỉ từ giấy tờ của CHÍNH người đó; KHÔNG ghi hai ô readonly (cổng đã đổ đúng tài khoản). Không có
    mốc / không tìm thấy → bỏ trống nhân thân khối người nộp + cảnh báo.
  · THEO TỜ KHAI (`submitterMode="owner_as_submitter"`): bên được ủy quyền → khối phẳng NguoiNop_* → chủ
    hồ sơ cá nhân; ghi đè cả hai ô readonly (đi trước), XOÁ ô nhân thân tài khoản mà hồ sơ không có
    (`_shared/lao_cai_nguoi_nop.chot_khoi_nguoi_nop`), lệch tài khoản thì cảnh báo cổng sẽ chặn nộp.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.lao_cai_nguoi_nop import chot_khoi_nguoi_nop
from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

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

    Ưu tiên câu LLM đọc từ Đơn Mẫu 24; không có thì ghép tất định từ thửa đất/tờ bản đồ/địa chỉ.
    Không đọc được số thửa → không phát field (không bịa).
    """
    san_co = _plain(values.get("Don_TrichYeu"))
    if san_co:
        return san_co
    so_thua = _plain(values.get("ThuaDat_SoThua"))
    if not so_thua:
        return None
    parts = [f"Đăng ký biến động - nhận chuyển quyền sử dụng đất thửa {so_thua}"]
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


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "có", "1"):
        return True
    return bool(values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"))


# ----- Người nộp: hai chế độ của bản extension mới -----
# Cổng gửi Họ tên + Số Căn cước + Ngày sinh của khối người nộp sang CSDL quốc gia dân cư và đối chiếu
# với tài khoản đăng nhập trước khi cho nộp → cả khối phải là MỘT người. LLM chỉ liệt kê ứng viên,
# mapper chọn người tất định rồi chỉ BÙ nhân thân từ giấy tờ của CHÍNH người đó.

_THEO_TO_KHAI = "owner_as_submitter"
_PERSON_KEYS = (
    "HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "DanToc", "NgayCap", "NoiCap",
    "NoiCuTru", "DienThoai", "Email", "Fax",
)


def _theo_to_khai(options: dict) -> bool:
    return str(options.get("submitterMode") or "") == _THEO_TO_KHAI



def _empty(value) -> bool:
    return value in (None, "", {}, [])


def _is_person(person: dict) -> bool:
    """Bản ghi không có họ tên lẫn số định danh thì không biết là ai → không làm ứng viên."""
    return not (_empty(person.get("HoTen")) and _empty(person.get("SoDinhDanh")))


def _people(values: dict, name: str) -> list[dict]:
    items = values.get(name)
    if not isinstance(items, list):
        return []
    return [p for p in items if isinstance(p, dict) and _is_person(p)]


def _proxy_person(values: dict) -> dict | None:
    proxy = values.get("NguoiDuocUyQuyen")
    if not isinstance(proxy, dict):
        return None
    person = {
        "HoTen": proxy.get("hoTen"),
        "SoDinhDanh": proxy.get("soDinhDanh"),
        "NgaySinh": proxy.get("ngaySinh"),
        "GioiTinh": proxy.get("gioiTinh"),
        "DanToc": proxy.get("danToc"),
        "NgayCap": proxy.get("ngayCapCccd"),
        "NoiCap": proxy.get("noiCapCccd"),
        "DienThoai": proxy.get("dienThoai"),
        "Email": proxy.get("email"),
        "NoiCuTru": proxy.get("thuongTru"),
    }
    return person if _is_person(person) else None


def _flat_person(values: dict, prefix: str) -> dict | None:
    block = {key: values.get(prefix + key) for key in _PERSON_KEYS}
    return block if _is_person(block) else None


def _id_of(person: dict | None) -> str:
    return re.sub(r"\D", "", str((person or {}).get("SoDinhDanh") or ""))


def _name_of(person: dict | None) -> str:
    return _fold((person or {}).get("HoTen"))


def _dob_conflict(left: dict, right: dict) -> bool:
    """Cùng họ tên mà ngày sinh mâu thuẫn là HAI người (cha/con trùng tên). Giấy chỉ ghi năm thì so năm."""
    a = _plain(str(left.get("NgaySinh") or "")) or ""
    b = _plain(str(right.get("NgaySinh") or "")) or ""
    if not (a and b):
        return False
    full_a, full_b = _date(a), _date(b)
    if full_a and full_b:
        return full_a != full_b
    year_a = re.findall(r"\d{4}", a)
    year_b = re.findall(r"\d{4}", b)
    return bool(year_a and year_b) and year_a[-1] != year_b[-1]


def _one_person(matches: list[dict]) -> dict | None:
    """Nhiều bản ghi cùng khớp chỉ nhận khi chắc là MỘT người: không lệch số định danh, không lệch ngày sinh."""
    if not matches:
        return None
    if len({_id_of(p) for p in matches if _id_of(p)}) > 1:
        return None
    first = matches[0]
    if any(_dob_conflict(first, other) for other in matches[1:]):
        return None
    return first


def _find_by_anchor(group: list[dict], anchor_id: str, anchor_name: str) -> dict | None:
    """Khớp SỐ ĐỊNH DANH trước; chỉ khi một phía thiếu số mới khớp HỌ TÊN bỏ dấu (duy nhất một người)."""
    if anchor_id:
        by_id = [p for p in group if _id_of(p) == anchor_id]
        if by_id:
            return _one_person(by_id)
    if not anchor_name:
        return None
    # Mốc có số mà giấy tờ cũng có số (khác số) → người khác, không xét theo tên.
    by_name = [p for p in group if not (anchor_id and _id_of(p)) and _name_of(p) == anchor_name]
    return _one_person(by_name)


def _merge_person(base: dict, loose: list[dict], strict: list[dict], anchor_id: str = "") -> dict:
    """Bù mục còn thiếu của `base` bằng giấy tờ khác CỦA CHÍNH người đó.

    `loose` = ứng viên theo từng người (CCCD, người trong giấy tờ, bên được ủy quyền): gộp khi khớp số
    định danh, hoặc khi một phía thiếu số thì khớp họ tên mà ngày sinh không mâu thuẫn — trùng tên mà
    mang nhiều số khác nhau là không rõ ai, không gộp theo tên.
    `strict` = khối phẳng (LLM có thể ghép chéo hai người trong một khối) → chỉ gộp khi TRÙNG số định danh.
    `anchor_id` = số mốc tài khoản khi giấy tờ của người này không ghi số — chặn gộp người trùng tên khác số.
    """
    merged = dict(base)
    base_id = anchor_id or _id_of(merged)
    base_name = _name_of(merged)
    name_ids = {_id_of(p) for p in loose if _id_of(p) and base_name and _name_of(p) == base_name}
    ambiguous_name = not base_id and len(name_ids) > 1

    def fill(person: dict) -> None:
        for key, value in person.items():
            if _empty(merged.get(key)) and not _empty(value):
                merged[key] = value

    for person in loose:
        person_id = _id_of(person)
        if base_id and person_id:
            same = base_id == person_id
        else:
            same = (
                not ambiguous_name and bool(base_name) and _name_of(person) == base_name
                and not _dob_conflict(merged, person)
            )
        if same:
            fill(person)
    for person in strict:
        if base_id and _id_of(person) == base_id:
            fill(person)
    return merged


def _person_cells(person: dict) -> list[tuple[str, object]]:
    """Nhân thân khối người nộp (trừ Họ tên/Số Căn cước) — mọi ô từ CÙNG một người đã gộp."""
    ngay_cap = _date(_plain(str(person.get("NgayCap") or "")))
    # Nơi cấp mặc định CHỈ khi giấy tờ của chính người đó có số định danh — không thì là bịa.
    noi_cap = normalize_issuer(_plain(person.get("NoiCap")))
    if not noi_cap and _id_of(person):
        noi_cap = default_issuer(ngay_cap)
    cells: list[tuple[str, object]] = [
        ("CongDan_ngaySinhCongDan", _date(_plain(str(person.get("NgaySinh") or "")))),
        ("CongDan_gioiTinhCongDan", _plain(person.get("GioiTinh"))),
        ("CongDan_danTocCongDan", _plain(person.get("DanToc"))),
        ("CongDan_ngayCapCmnd", ngay_cap),
        ("CongDan_noiCapCmnd", noi_cap),
    ]
    area = _area(person.get("NoiCuTru"))
    if area:
        # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh.
        cells += [
            ("CongDan_maTinhThanh", _province_label(area.get("tinh"))),
            ("CongDan_maPhuongXa", _plain(area.get("xa"))),
            ("CongDan_diaChi", _plain(area.get("diaChi"))),
        ]
    cells += [
        ("CongDan_diDong", _phone(str(person.get("DienThoai") or ""))),
        ("CongDan_email", _plain(person.get("Email"))),
        ("CongDan_fax", _plain(str(person.get("Fax") or ""))),
    ]
    return cells


def _nguoi_nop_moi(values: dict, options: dict, is_org: bool) -> tuple[list[tuple[str, object]], list[str]]:
    """Khối người nộp cho bản extension mới: chế độ TÀI KHOẢN (mặc định) hoặc TỜ KHAI (toggle)."""
    ctx = options.get("formContext")
    ctx = ctx if isinstance(ctx, dict) else {}
    raw_id = _plain(str(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or ""))
    raw_name = _plain(ctx.get("applicantFullname"))
    anchor_id = re.sub(r"\D", "", raw_id or "")
    anchor_name = _fold(raw_name) if raw_name else ""

    cards = _people(values, "DanhSachCccd")
    named = _people(values, "NguoiTrongGiayTo")
    proxy = _proxy_person(values)
    flat_nop = _flat_person(values, "NguoiNop_")
    # Chủ hồ sơ TỔ CHỨC thì ChuHoSo_HoTen là người đại diện của tổ chức chứ không phải cá nhân đứng đơn →
    # không dùng khối đó làm ứng viên người nộp.
    flat_owner = None if is_org else _flat_person(values, "ChuHoSo_")
    loose = cards + named + ([proxy] if proxy else [])
    strict = [p for p in (flat_nop, flat_owner) if p]

    if _theo_to_khai(options):
        base = proxy or flat_nop or flat_owner
        if not base:
            return [], [
                "Bật cài đặt \"Lấy người nộp theo tờ khai\" nhưng hồ sơ không có văn bản ủy quyền và cũng không "
                "đọc được người đứng tên đơn, nên trợ lý để trống khối \"Thông tin người nộp hồ sơ\" — cán "
                "bộ nhập tay."
            ]
        person = _merge_person(base, loose, strict)
        # Người nộp theo tờ khai có thể KHÁC người cổng đổ sẵn → ghi đè cả Họ tên + Số Căn cước (đi TRƯỚC)
        # để cả khối là một người.
        cells = [
            ("CongDan_tenCongDan", _plain(person.get("HoTen"))),
            ("CongDan_soCmnd", _id_of(person) or None),
        ] + _person_cells(person)
        warnings: list[str] = []
        nop_id, nop_name = _id_of(person), _name_of(person)
        if anchor_id and nop_id:
            lech = anchor_id != nop_id
        else:
            lech = bool(anchor_name and nop_name) and anchor_name != nop_name
        if lech:
            warnings.append(
                "Khối \"Thông tin người nộp hồ sơ\" đang điền theo TỜ KHAI ("
                + (_plain(person.get("HoTen")) or "người trong hồ sơ")
                + ") nhưng tài khoản đang đăng nhập là " + (raw_name or raw_id or "người khác")
                + ". Cổng đối chiếu Họ tên/Số Căn cước/Ngày sinh với tài khoản và CSDL quốc gia dân cư "
                "trước khi cho nộp — lệch là bị chặn. Đăng nhập đúng tài khoản người đi nộp, hoặc tắt "
                "cài đặt \"Lấy người nộp theo tờ khai\"."
            )
        return cells, warnings

    if not (anchor_id or anchor_name):
        return [], [
            "Không đọc được Họ tên/Số Căn cước của tài khoản đăng nhập trên trang nên trợ lý để trống khối "
            "\"Thông tin người nộp hồ sơ\" — cán bộ nhập tay nhân thân của CHÍNH người đăng nhập (cổng "
            "đối chiếu với CSDL quốc gia dân cư), không lấy thông tin người khác."
            " Vừa cập nhật/tải lại extension thì F5 trang cổng rồi quét lại; người nộp theo tờ khai thì "
            "bật cài đặt \"Lấy người nộp theo tờ khai\"."
        ]
    base = None
    for group in (cards, named, [proxy] if proxy else [], [flat_nop] if flat_nop else [],
                  [flat_owner] if flat_owner else []):
        base = _find_by_anchor(group, anchor_id, anchor_name)
        if base:
            break
    if not base:
        return [], [
            "Không nhận ra người đang đăng nhập" + (f" ({raw_name})" if raw_name else "")
            + " trong giấy tờ của hồ sơ nên trợ lý để trống khối \"Thông tin người nộp hồ sơ\" — cán bộ "
            "nhập tay nhân thân của CHÍNH người đăng nhập, KHÔNG lấy thông tin của người khác."
        ]
    person = _merge_person(base, loose, strict, anchor_id)
    # Hai ô readonly Họ tên/Số Căn cước cổng đã đổ đúng tài khoản → chỉ bù các ô nhân thân còn lại.
    return _person_cells(person), []


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    options = options if isinstance(options, dict) else {}
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

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

    is_org = _is_org(values)
    ten_to_chuc = _plain(values.get("ChuHoSo_TenToChuc"))
    ma_so_thue = _tax_code(values.get("ChuHoSo_MaSoThue"))

    # --- Khối NGƯỜI NỘP ---
    # Địa chỉ phẳng của khối người nộp vẫn là nguồn dự phòng cho địa chỉ khối chủ hồ sơ ở MỌI chế độ
    # (giữ nguyên logic khối chủ hồ sơ).
    nop_area = _area(values.get("NguoiNop_NoiCuTru")) or _area(values.get("ChuHoSo_NoiCuTru"))
    cells, nop_warnings = _nguoi_nop_moi(values, options, is_org)
    for name, value in cells:
        add(name, value)
    if is_org:
        # Tên cơ quan/MST là dữ liệu của TỔ CHỨC chủ hồ sơ → phát cả khi chưa xác định được người nộp.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)
    warnings.extend(nop_warnings)

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

    # 3 ô địa chỉ này là thứ checkbox của cổng KHÔNG copy → luôn phát từ dữ liệu trích được.
    chs_area = _area(values.get("ChuHoSo_NoiCuTru")) or nop_area
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
        out, theo_to_khai=_theo_to_khai(options), comp_by_name=UI_COMP_BY_NAME, warnings=warnings
    )
    return out, warnings
