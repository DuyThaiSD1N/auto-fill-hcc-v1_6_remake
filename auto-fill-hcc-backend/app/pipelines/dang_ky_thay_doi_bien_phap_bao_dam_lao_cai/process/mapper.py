"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.011442.H38).

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (cài đặt "Lấy người nộp theo tờ khai" của extension → `options.submitterMode`):
  · Mặc định — THEO TÀI KHOẢN: mốc là Họ tên + Số Căn cước cổng đổ sẵn từ tài khoản định danh, gửi lên
    trong `options.formContext`. Chỉ bù nhân thân người nộp bằng giấy tờ CỦA CHÍNH người đó; không có
    mốc, hoặc hồ sơ không có giấy tờ của người đó → bỏ trống nhân thân + cảnh báo.
  · `submitterMode="owner_as_submitter"` — THEO TỜ KHAI: người được giới thiệu/ủy quyền → người liên hệ
    trên Phiếu 02a (`NguoiNop_*`) → chủ hồ sơ cá nhân.
Cổng gửi Họ tên + Số Căn cước + Ngày sinh của khối người nộp sang CSDL quốc gia dân cư để xác thực trước
khi cho nộp → cả khối phải là MỘT người. Bước chốt (không ghi/ghi hai ô readonly, xoá nhân thân tài khoản
mà hồ sơ không có) đi qua `_shared/lao_cai_nguoi_nop.chot_khoi_nguoi_nop`.

⚑ Gộp nhân thân CHẶT: khớp số định danh trước; một phía thiếu số mới khớp họ tên bỏ dấu khi ngày sinh
không mâu thuẫn; cùng họ tên mà mang nhiều số định danh khác nhau → không gộp theo tên (hai người trùng
tên). Hồ sơ thế chấp hay có nhiều cá nhân (người đại diện hai bên, người sử dụng đất, người liên hệ).

⚑ "Đối tượng nộp hồ sơ" (`ChuHoSo_maDoiTuongNopHS`) phát VALUE (CN/DN) — nhãn "Tổ chức" khớp lỏng được cả
"Doanh nghiệp/ Tổ chức" lẫn "Tổ chức khác". Ô này đứng ĐẦU khối chủ hồ sơ vì đổi đối tượng làm cổng xoá
trắng nhánh ô còn lại; ô đang ẩn theo đối tượng thì không phát (engine báo "không điền được" vô cớ).

⚑ Checkbox "Người nộp là chủ hồ sơ" chỉ copy tới Nơi cấp/Ngày cấp, không copy địa chỉ → không phát
checkbox, luôn phát đủ khối chủ hồ sơ. `HoSoOnline_veViec` cổng điền sẵn đúng tên thủ tục → không đụng.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.lao_cai_nguoi_nop import chot_khoi_nguoi_nop

from .schema import INDIVIDUAL_ONLY_FIELDS, ORG_ONLY_FIELDS, UI_ALIASES, UI_COMP_BY_NAME

_DOI_TUONG_FIELD = "ChuHoSo_maDoiTuongNopHS"
_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_DOANH_NGHIEP = "DN"

# Textarea "Ghi chú" của cổng giới hạn 500 ký tự.
_MAX_GHI_CHU = 500

_EMPTY = (None, "", {}, [])


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in _EMPTY}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_honorific(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    return re.sub(r"^(ông|bà|anh|chị)\s*[:.]?\s+", "", text, flags=re.IGNORECASE).strip() or None


def _name_key(value) -> str:
    return _fold(_strip_honorific(value))


def _digits(value) -> str | None:
    text = _plain(value) if isinstance(value, str) else (str(value) if value not in _EMPTY else None)
    if not text:
        return None
    return re.sub(r"\D", "", text) or None


def _tax_code(value) -> str | None:
    """Mã số thuế giữ dấu '-' của mã đơn vị phụ thuộc (chi nhánh dạng 0100000000-001)."""
    text = _plain(value) if isinstance(value, str) else _digits(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9-]", "", text).strip("-")
    base = cleaned.split("-", 1)[0]
    return cleaned if len(base) in (10, 13) else None


def _phone(value) -> str | None:
    text = _plain(value) if isinstance(value, str) else _digits(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _email(value) -> str | None:
    text = (_plain(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text) else None


def _date(value) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1980") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _gender(value) -> str | None:
    text = _fold(value)
    if text in ("nam", "male"):
        return "Nam"
    if text in ("nu", "female"):
        return "Nữ"
    return None


def _area(value) -> dict | None:
    """Địa chỉ object {quocGia,tinh,xa,diaChi[,huyen]}; chuỗi trần thì dồn vào diaChi."""
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
    hint = value.get("huyen") or value.get("quanHuyen") or None
    return remap_area(out, allow_diachi_fallback=True, huyen_hint=hint) or out


def _get(person: dict | None, *keys):
    """Ứng viên đến từ nhiều nguồn nên tên khoá khác nhau (HoTen ↔ hoTen)."""
    for key in keys:
        value = (person or {}).get(key)
        if value not in _EMPTY:
            return value
    return None


def _people(values: dict, key: str) -> list[dict]:
    raw = values.get(key)
    if isinstance(raw, dict):
        raw = [raw]
    return [p for p in raw if isinstance(p, dict)] if isinstance(raw, list) else []


def _person_block(values: dict, prefix: str) -> dict | None:
    """Gom khối phẳng ChuHoSo_*/NguoiNop_* thành một ứng viên cùng dạng với danh sách."""
    block = {
        "HoTen": _strip_honorific(values.get(f"{prefix}_HoTen")),
        "SoDinhDanh": values.get(f"{prefix}_SoDinhDanh"),
        "NgaySinh": values.get(f"{prefix}_NgaySinh"),
        "GioiTinh": values.get(f"{prefix}_GioiTinh"),
        "DanToc": values.get(f"{prefix}_DanToc"),
        "NgayCap": values.get(f"{prefix}_NgayCap"),
        "NoiCap": values.get(f"{prefix}_NoiCap"),
        "DienThoai": values.get(f"{prefix}_DienThoai"),
        "Email": values.get(f"{prefix}_Email"),
        "Fax": values.get(f"{prefix}_Fax"),
        "NoiCuTru": values.get(f"{prefix}_NoiCuTru"),
    }
    block = {k: v for k, v in block.items() if v not in _EMPTY}
    # Chỉ có điện thoại/địa chỉ mà không có tên hay số thì không biết là của ai.
    return block if (block.get("HoTen") or block.get("SoDinhDanh")) else None


def _proxy_person(values: dict) -> dict | None:
    proxy = values.get("NguoiDuocUyQuyen")
    if isinstance(proxy, list):
        proxy = next((p for p in proxy if isinstance(p, dict)), None)
    if not isinstance(proxy, dict):
        return None
    person = {
        "HoTen": _strip_honorific(_get(proxy, "hoTen", "HoTen")),
        "SoDinhDanh": _get(proxy, "soDinhDanh", "SoDinhDanh"),
        "NgaySinh": _get(proxy, "ngaySinh", "NgaySinh"),
        "GioiTinh": _get(proxy, "gioiTinh", "GioiTinh"),
        "DanToc": _get(proxy, "danToc", "DanToc"),
        "NgayCap": _get(proxy, "ngayCapCccd", "NgayCap"),
        "NoiCap": _get(proxy, "noiCapCccd", "NoiCap"),
        "DienThoai": _get(proxy, "dienThoai", "DienThoai"),
        "Email": _get(proxy, "email", "Email"),
        "NoiCuTru": _get(proxy, "thuongTru", "NoiCuTru"),
        "DonVi": _plain(_get(proxy, "donVi", "DonVi")),
        "MaSoThueDonVi": _get(proxy, "maSoThueDonVi", "MaSoThueDonVi"),
    }
    person = {k: v for k, v in person.items() if v not in _EMPTY}
    return person if (person.get("HoTen") or person.get("SoDinhDanh")) else None


def _dob_conflict(left: dict, right: dict) -> bool:
    """Cùng họ tên nhưng KHÁC ngày sinh là hai người (cha/con trùng tên)."""
    a = _plain(_get(left, "NgaySinh"))
    b = _plain(_get(right, "NgaySinh"))
    if not (a and b):
        return False
    # "1990" với "15/06/1990" không mâu thuẫn: so theo phần năm khi một bên chỉ có năm.
    if re.fullmatch(r"\d{4}", a) or re.fullmatch(r"\d{4}", b):
        return a[-4:] != b[-4:]
    return (_date(a) or a) != (_date(b) or b)


def _merge_person(base: dict | None, *groups: list[dict], known_id: str | None = None) -> dict | None:
    """Bù mục còn thiếu của `base` bằng giấy tờ khác CỦA CHÍNH người đó (gộp chặt).

    - Hai phía cùng có số định danh: chỉ gộp khi trùng số.
    - Một phía thiếu số: gộp khi trùng họ tên bỏ dấu, ngày sinh không mâu thuẫn, VÀ họ tên đó không gắn
      với nhiều số định danh khác nhau trong hồ sơ (trùng tên hai người → không đoán).
    `known_id`: số định danh chắc chắn của người này (mốc tài khoản) khi `base` chưa có số.
    """
    if not base:
        return None
    merged = dict(base)
    base_id = _digits(_get(merged, "SoDinhDanh")) or _digits(known_id)
    base_name = _name_key(_get(merged, "HoTen"))
    people = [p for group in groups for p in group if isinstance(p, dict)]
    ids_same_name = {
        _digits(_get(p, "SoDinhDanh"))
        for p in people
        if base_name and _name_key(_get(p, "HoTen")) == base_name and _digits(_get(p, "SoDinhDanh"))
    }
    for person in people:
        if person is base:
            continue
        person_id = _digits(_get(person, "SoDinhDanh"))
        if base_id and person_id:
            same = base_id == person_id
        else:
            same = (
                bool(base_name)
                and _name_key(_get(person, "HoTen")) == base_name
                and not _dob_conflict(merged, person)
                and (base_id or len(ids_same_name) <= 1)
            )
        if not same:
            continue
        for field, value in person.items():
            if merged.get(field) in _EMPTY and value not in _EMPTY:
                merged[field] = value
    return merged


def _find_anchor(groups: list[list[dict]], anchor_id: str, anchor_name: str) -> dict | None:
    """Ứng viên khớp mốc tài khoản: số định danh trước; thiếu số mới theo họ tên và phải DUY NHẤT."""
    people = [p for group in groups for p in group if isinstance(p, dict)]
    if anchor_id:
        by_id = [p for p in people if _digits(_get(p, "SoDinhDanh")) == anchor_id]
        if by_id:
            return by_id[0]
    if not anchor_name:
        return None
    by_name = [
        p for p in people
        if _name_key(_get(p, "HoTen")) == anchor_name
        # Mốc có số mà người này mang số KHÁC → người trùng tên, không phải tài khoản.
        and not (anchor_id and _digits(_get(p, "SoDinhDanh")))
    ]
    if not by_name:
        return None
    ids = {_digits(_get(p, "SoDinhDanh")) for p in by_name if _digits(_get(p, "SoDinhDanh"))}
    if len(ids) > 1:
        return None
    for left in by_name:
        if any(_dob_conflict(left, right) for right in by_name):
            return None
    return by_name[0]


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "1", "yes"):
        return True
    if isinstance(flag, str) and _fold(flag) in ("false", "khong", "0", "no"):
        return False
    return bool(values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"))


def _ghi_chu(values: dict) -> str | None:
    text = _plain(values.get("GhiChu_TepDinhChung"))
    if not text:
        return None
    if len(text) <= _MAX_GHI_CHU:
        return text
    cut = text[: _MAX_GHI_CHU - 1]
    # Cắt ở ranh giới từ để không để lại nửa chữ.
    cut = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return cut.rstrip(" ;,") + "…"


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    options = options or {}
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    def add(name: str, value, **extra) -> None:
        if name in seen or value in _EMPTY:
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value, **extra}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    is_org = _is_org(values)
    ten_to_chuc = _plain(values.get("ChuHoSo_TenToChuc")) if is_org else None
    ma_so_thue = _tax_code(values.get("ChuHoSo_MaSoThue")) if is_org else None

    ctx = options.get("formContext") or {}
    anchor_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")) or ""
    anchor_name = _name_key(ctx.get("applicantFullname") or ctx.get("fullname"))
    has_anchor = bool(anchor_id or anchor_name)
    theo_to_khai = str(options.get("submitterMode") or "") == "owner_as_submitter"

    proxy = _proxy_person(values)
    nop_flat = _person_block(values, "NguoiNop")
    chs_flat = None if is_org else _person_block(values, "ChuHoSo")
    cards = _people(values, "DanhSachCccd")
    named = _people(values, "NguoiTrongGiayTo")
    # Thứ tự nguồn khi khớp/bù: CCCD rời (đầy đủ nhất) → người trong giấy tờ → giấy giới thiệu/ủy quyền
    # → khối phẳng người nộp → chủ hồ sơ cá nhân.
    groups = [cards, named, [proxy] if proxy else [], [nop_flat] if nop_flat else [],
              [chs_flat] if chs_flat else []]

    # --- Khối NGƯỜI NỘP ---
    if theo_to_khai:
        base = proxy or nop_flat or chs_flat
        nguoi_nop = _merge_person(base, *groups)
    elif has_anchor:
        base = _find_anchor(groups, anchor_id, anchor_name)
        nguoi_nop = _merge_person(base, *groups, known_id=anchor_id or None)
    else:
        nguoi_nop = None

    # Ô tên cơ quan/MST của người nộp: đơn vị cử người đó đi (giấy giới thiệu/ủy quyền), không có thì tổ
    # chức chủ hồ sơ — đều là dữ liệu TỔ CHỨC nên phát được cả khi chưa xác định người đi nộp.
    don_vi = _plain(_get(nguoi_nop, "DonVi"))
    if don_vi:
        mst_don_vi = _tax_code(_get(nguoi_nop, "MaSoThueDonVi"))
        if not mst_don_vi and ten_to_chuc and _fold(don_vi) == _fold(ten_to_chuc):
            mst_don_vi = ma_so_thue
        add("CongDan_tenCoQuanToChuc", don_vi)
        add("CongDan_maSoThueNguoiNop", mst_don_vi)
    elif is_org:
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)

    nop_area = _area(_get(nguoi_nop, "NoiCuTru")) if nguoi_nop else None
    if nguoi_nop:
        nop_identity = _digits(_get(nguoi_nop, "SoDinhDanh"))
        if theo_to_khai:
            add("CongDan_tenCongDan", _plain(_get(nguoi_nop, "HoTen")))
            add("CongDan_soCmnd", nop_identity)
        nop_ngay_cap = _date(_get(nguoi_nop, "NgayCap"))
        # Nơi cấp mặc định CHỈ khi hồ sơ thật sự có số giấy tờ của chính người đó — không thì là bịa.
        nop_noi_cap = normalize_issuer(_plain(_get(nguoi_nop, "NoiCap")))
        nop_default_issuer = False
        if not nop_noi_cap and nop_identity:
            nop_noi_cap = default_issuer(nop_ngay_cap)
            nop_default_issuer = bool(nop_noi_cap)
        add("CongDan_ngaySinhCongDan", _date(_get(nguoi_nop, "NgaySinh")))
        add("CongDan_gioiTinhCongDan", _gender(_get(nguoi_nop, "GioiTinh")))
        add("CongDan_danTocCongDan", _plain(_get(nguoi_nop, "DanToc")))
        add("CongDan_ngayCapCmnd", nop_ngay_cap)
        add("CongDan_noiCapCmnd", nop_noi_cap, **({"default": True} if nop_default_issuer else {}))
        if nop_area:
            # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh.
            add("CongDan_maTinhThanh", province_label(nop_area.get("tinh")))
            add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
            add("CongDan_diaChi", _plain(nop_area.get("diaChi")))
        add("CongDan_diDong", _phone(_get(nguoi_nop, "DienThoai")))
        add("CongDan_email", _email(_get(nguoi_nop, "Email")))
        add("CongDan_fax", _plain(_get(nguoi_nop, "Fax")))
        if theo_to_khai and has_anchor:
            nop_id = _digits(_get(nguoi_nop, "SoDinhDanh"))
            nop_name = _name_key(_get(nguoi_nop, "HoTen"))
            lech = (anchor_id and nop_id and anchor_id != nop_id) or (
                not (anchor_id and nop_id) and anchor_name and nop_name and anchor_name != nop_name
            )
            if lech:
                warnings.append(
                    "Khối \"Thông tin người nộp\" đang điền theo TỜ KHAI ("
                    + (_plain(_get(nguoi_nop, "HoTen")) or "người trong hồ sơ")
                    + ") nhưng tài khoản đang đăng nhập là "
                    + (_plain(ctx.get("applicantFullname")) or "người khác")
                    + ". Cổng xác thực Họ tên/Số Căn cước/Ngày sinh với CSDL quốc gia dân cư trước khi cho "
                    "nộp — lệch tài khoản sẽ bị chặn với thông báo \"Thông tin người nộp hồ sơ không đúng "
                    "với tài khoản đăng nhập!\". Đăng nhập đúng tài khoản người đi nộp, hoặc tắt cài đặt "
                    "\"Lấy người nộp theo tờ khai\"."
                )
    elif theo_to_khai:
        warnings.append(
            "Bật cài đặt \"Lấy người nộp theo tờ khai\" nhưng hồ sơ không có giấy giới thiệu/văn bản ủy quyền, "
            "Phiếu 02a không ghi người liên hệ và không đọc được người yêu cầu là cá nhân, nên trợ lý không "
            "xác định được người đi nộp theo tờ khai — khối \"Thông tin người nộp\" để trống nhân thân, cán "
            "bộ nhập tay."
        )
    elif not has_anchor:
        warnings.append(
            "Không xác định được NGƯỜI ĐANG ĐI NỘP: trợ lý chưa đọc được Họ tên/Số Căn cước cổng đổ sẵn từ "
            "tài khoản định danh (trang chưa đăng nhập, hoặc vừa cập nhật extension mà chưa F5 trang cổng). "
            "Khối \"Thông tin người nộp\" để trống nhân thân để khỏi điền nhầm người — F5 trang cổng rồi "
            "quét lại, hoặc bật cài đặt \"Lấy người nộp theo tờ khai\" để điền theo tờ khai."
        )
    else:
        warnings.append(
            "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
            + (f" ({_plain(ctx.get('applicantFullname'))})" if ctx.get("applicantFullname") else "")
            + " nên khối \"Thông tin người nộp\" để trống nhân thân — cán bộ nhập tay, KHÔNG lấy thông tin "
            "của người khác trong hồ sơ vì cổng xác thực với CSDL quốc gia dân cư trước khi cho nộp. Muốn "
            "điền theo người trong tờ khai thì bật cài đặt \"Lấy người nộp theo tờ khai\"."
        )

    # --- Khối CHỦ HỒ SƠ: đối tượng đứng đầu, rồi đủ các ô đang hiện theo đối tượng ---
    add(_DOI_TUONG_FIELD, _DOI_TUONG_DOANH_NGHIEP if is_org else _DOI_TUONG_CA_NHAN)
    if is_org:
        add("ChuHoSo_tenCoQuanToChucCHS", ten_to_chuc)
        add("ChuHoSo_maSoThueChuHoSo", ma_so_thue)
        if not ma_so_thue:
            warnings.append(
                "Không đọc được đủ mã số thuế/mã số chi nhánh của tổ chức yêu cầu đăng ký — cổng bắt buộc "
                "ô \"Mã số thuế\" của chủ hồ sơ tổ chức, cán bộ nhập tay."
            )
        chs = {}
    else:
        chs = _merge_person(chs_flat, cards, named) or {}
        chs_identity = _digits(_get(chs, "SoDinhDanh"))
        chs_ngay_cap = _date(_get(chs, "NgayCap"))
        chs_noi_cap = normalize_issuer(_plain(_get(chs, "NoiCap")))
        chs_default_issuer = False
        if not chs_noi_cap and chs_identity:
            chs_noi_cap = default_issuer(chs_ngay_cap)
            chs_default_issuer = bool(chs_noi_cap)
        add("ChuHoSo_tenChuHoSo", _plain(_get(chs, "HoTen")))
        add("ChuHoSo_ngaySinhChuHoSo", _date(_get(chs, "NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo", _gender(_get(chs, "GioiTinh")))
        add("ChuHoSo_danTocChuHoSo", _plain(_get(chs, "DanToc")))
        add("ChuHoSo_soCMNDChuHoSo", chs_identity)
        add("ChuHoSo_noiCapCMNDCHS", chs_noi_cap, **({"default": True} if chs_default_issuer else {}))
        add("ChuHoSo_ngayCapCMNDCHS", chs_ngay_cap)
    add("ChuHoSo_faxChuHoSo", _plain(values.get("ChuHoSo_Fax")))
    add("ChuHoSo_emailChuHoSo", _email(values.get("ChuHoSo_Email")) or _email(_get(chs, "Email")))
    add("ChuHoSo_diDongLienLacCHS", _phone(values.get("ChuHoSo_DienThoai")) or _phone(_get(chs, "DienThoai")))

    chs_area = _area(values.get("ChuHoSo_NoiCuTru")) or _area(_get(chs, "NoiCuTru"))
    if chs_area:
        add("ChuHoSo_maTinhThanhCHS", province_label(chs_area.get("tinh")))
        add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
        add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
        if _plain(chs_area.get("tinh")) and not _plain(chs_area.get("xa")):
            warnings.append(
                "Địa chỉ chủ hồ sơ ghi theo đơn vị hành chính CŨ (trước sáp nhập) nên không khớp danh mục "
                "hiện hành — cán bộ chọn tay ô Phường/Xã của khối chủ hồ sơ."
            )
    else:
        warnings.append(
            "Không đọc được địa chỉ chủ hồ sơ — cán bộ nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ."
        )

    # --- Bước "Thành phần hồ sơ" ---
    add("HoSoOnline_ghiChu", _ghi_chu(values))

    # Ô đang ẩn theo đối tượng: không phát (phòng khi dữ liệu LLM lẫn hai nhánh).
    hidden = INDIVIDUAL_ONLY_FIELDS if is_org else ORG_ONLY_FIELDS
    out = [f for f in out if f["name"] not in hidden]

    out = chot_khoi_nguoi_nop(
        out, theo_to_khai=theo_to_khai, comp_by_name=UI_COMP_BY_NAME, warnings=warnings
    )
    return out, warnings
