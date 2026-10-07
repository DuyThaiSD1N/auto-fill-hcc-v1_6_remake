"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.011441.H38).

Mapper tự chứa (không mượn mapper thủ tục khác) vì vai ở thủ tục này khác: chủ hồ sơ là NGƯỜI YÊU CẦU
ĐĂNG KÝ ở mục 1 Phiếu 01a, người nộp có thể là cán bộ tổ chức tín dụng được giới thiệu/ủy quyền.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (cài đặt "Lấy người nộp theo tờ khai" của extension → `options.submitterMode`):
  · Mặc định — THEO TÀI KHOẢN: mốc là Họ tên + Số Căn cước cổng đổ sẵn từ tài khoản định danh
    (`options.formContext`). Thiếu formContext (bản extension cũ, hoặc trang cổng chưa F5 sau khi reload
    extension) = chưa có mốc. Chỉ điền nhân thân lấy từ giấy tờ của CHÍNH người khớp mốc; không có mốc
    hoặc không thấy người đó trong hồ sơ → bỏ trống nhân thân + cảnh báo.
  · `submitterMode="owner_as_submitter"` — THEO TỜ KHAI: người được giới thiệu/ủy quyền → khối phẳng
    NguoiNop_* → chủ hồ sơ cá nhân; ghi cả Họ tên + Số Căn cước (readonly) theo người đó.
  Bước chốt chung `_shared/lao_cai_nguoi_nop.chot_khoi_nguoi_nop`: tài khoản không ghi hai ô readonly;
  tờ khai đưa hai ô đó lên đầu và xoá nhân thân tài khoản mà hồ sơ không có.

⚑ GỘP NHÂN THÂN CHẶT: ứng viên từ nhiều giấy tờ chỉ gộp khi khớp SỐ ĐỊNH DANH; thiếu số ở một phía mới
khớp họ tên (bỏ dấu) với ngày sinh không mâu thuẫn; một họ tên ứng với nhiều số định danh → không gộp.
Hồ sơ thế chấp hay có người vay cùng họ với bên thế chấp — gộp lỏng là ghép chéo nhân thân.

⚑ Khối chủ hồ sơ:
  1. `ChuHoSo_maDoiTuongNopHS` phát VALUE (CN/DN) và phát TRƯỚC mọi ô ChuHoSo_* khác: đổi đối tượng làm
     cổng xoá trắng nhánh ô còn lại. Nhãn "Tổ chức" khớp lỏng được cả "Doanh nghiệp/ Tổ chức" lẫn "Tổ chức
     khác", value thì engine khớp chính xác.
  2. CN ẩn tên tổ chức/MST; DN ẩn các ô cá nhân → chỉ phát ô đang hiện.
  3. Không dùng checkbox `chkbox_nguoinoplachuhs` (JS cổng lỗi ở thủ tục này) → luôn phát đủ khối.

⚑ Ô "Ghi chú" (`HoSoOnline_ghiChu`, bước thành phần hồ sơ, tối đa 500 ký tự): mô tả tệp gộp nhiều giấy
tờ để cán bộ tiếp nhận biết giấy nào nằm ở trang nào. Ô "Về việc" giữ chữ cổng điền sẵn.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date, upper_person_name
from app.pipelines._shared.lao_cai_nguoi_nop import chot_khoi_nguoi_nop

from .schema import INDIVIDUAL_ONLY_FIELDS, ORG_ONLY_FIELDS, UI_ALIASES, UI_COMP_BY_NAME

_EMPTY = (None, "", {}, [])

# Option value thật của <select name="ChuHoSo_maDoiTuongNopHS">.
_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_DOANH_NGHIEP = "DN"

_GHI_CHU_MAX = 500

# Thứ tự nguồn địa chỉ của MỘT người: khối phẳng/giấy ủy quyền lấy theo Phiếu 01a (địa giới mới) đứng
# trước CCCD/GCN cấp trước sắp xếp đơn vị hành chính (địa giới cũ).
_NGUON_DIA_CHI_CHU_HO_SO = ("ChuHoSo", "NguoiNop", "UyQuyen", "NguoiTrongGiayTo", "Cccd")
_NGUON_DIA_CHI_NGUOI_NOP = ("NguoiNop", "UyQuyen", "ChuHoSo", "NguoiTrongGiayTo", "Cccd")

_PERSON_KEYS = ("HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "DanToc", "NgayCap", "NoiCap",
                "DienThoai", "Email", "Fax", "NoiCuTru")


# ----------------------------------------------------------------------------- chuẩn hoá giá trị

def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in _EMPTY}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _strip_honorific(value) -> str:
    """Phiếu 01a in sẵn "ÔNG (BÀ):" trước họ tên và hay có dấu phẩy thừa phía sau."""
    text = " ".join(str(value or "").split())
    text = re.sub(r"^(ông|bà|anh|chị)\s*(\(\s*bà\s*\))?\s*[:.]?\s*", "", text, flags=re.IGNORECASE)
    return text.strip(" ,.;:-")


def _name_key(value) -> str:
    return _fold(_strip_honorific(value))


def _person_name(value) -> str | None:
    text = _strip_honorific(value)
    return upper_person_name(text) or None


def _id_number(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _tax_code(value) -> str | None:
    """Mã số thuế giữ dấu '-' của mã đơn vị phụ thuộc (chi nhánh ngân hàng: 01000xxxxx-6xx)."""
    text = _plain(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9-]", "", text).strip("-")
    return cleaned if len(_digits(cleaned)) >= 10 else None


def _phone(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    digits = _digits(text)
    if text.startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _email(value) -> str | None:
    text = (_plain(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text) else None


def _date(value) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. "Sinh năm 1980" không đủ cho ô DD/MM/YYYY → bỏ, không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", normalized)
    return f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{match.group(3)}" if match else None


def _gender(value) -> str | None:
    text = _fold(value)
    if text in ("nam", "male"):
        return "Nam"
    if text in ("nu", "female"):
        return "Nữ"
    return None


def _area(value) -> dict | None:
    """Địa chỉ object {quocGia,tinh,xa,diaChi} → đã quy về địa giới hiện hành. Thiếu tỉnh thì bỏ nguồn."""
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    if not _plain(area["tinh"]):
        return None
    hint = value.get("huyen") or value.get("quanHuyen") or None
    return remap_area(area, allow_diachi_fallback=True, huyen_hint=hint) or area


def _issuer(value, identity: str | None, issue_date: str | None) -> tuple[str | None, bool]:
    """Nơi cấp theo giấy tờ; mặc định theo ngày cấp CHỈ khi hồ sơ có số giấy tờ của chính người đó."""
    issuer = normalize_issuer(_plain(value)) or _plain(value)
    if issuer:
        return issuer, False
    if identity:
        return default_issuer(issue_date), True
    return None, False


# ----------------------------------------------------------------------------- ứng viên & gộp chặt

def _get(person: dict | None, key: str):
    value = (person or {}).get(key)
    return None if value in _EMPTY else value


def _record(raw: dict, kind: str) -> dict | None:
    record = {key: raw.get(key) for key in _PERSON_KEYS if raw.get(key) not in _EMPTY}
    if not record:
        return None
    record["_nguon"] = [(kind, raw.get("NoiCuTru"))]
    return record


def _people(values: dict, name: str, kind: str) -> list[dict]:
    items = values.get(name)
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return []
    return [r for r in (_record(p, kind) for p in items if isinstance(p, dict)) if r]


def _flat_block(values: dict, prefix: str) -> dict | None:
    raw = {key: values.get(f"{prefix}_{key}") for key in _PERSON_KEYS}
    return _record(raw, prefix)


def _proxy(values: dict) -> dict | None:
    proxy = values.get("NguoiDuocUyQuyen")
    if not isinstance(proxy, dict):
        return None
    raw = {
        "HoTen": proxy.get("hoTen"), "SoDinhDanh": proxy.get("soDinhDanh"),
        "NgaySinh": proxy.get("ngaySinh"), "GioiTinh": proxy.get("gioiTinh"),
        "DanToc": proxy.get("danToc"), "NgayCap": proxy.get("ngayCapCccd"),
        "NoiCap": proxy.get("noiCapCccd"), "DienThoai": proxy.get("dienThoai"),
        "Email": proxy.get("email"), "NoiCuTru": proxy.get("thuongTru"),
    }
    record = _record(raw, "UyQuyen")
    if not record or not _get(record, "HoTen"):
        return None
    record["_donVi"] = _plain(proxy.get("donVi"))
    record["_maSoThueDonVi"] = _tax_code(proxy.get("maSoThueDonVi"))
    return record


def _years(value) -> tuple[str | None, str | None]:
    """(ngày đủ, năm) — giấy chỉ ghi "sinh năm" vẫn so được năm."""
    text = _plain(value) or ""
    full = _date(text)
    year = re.search(r"(19|20)\d{2}", text)
    return full, year.group(0) if year else None


def _dob_conflict(left: dict, right: dict) -> bool:
    l_full, l_year = _years(_get(left, "NgaySinh"))
    r_full, r_year = _years(_get(right, "NgaySinh"))
    if l_full and r_full:
        return l_full != r_full
    return bool(l_year and r_year and l_year != r_year)


def _same_person(left: dict | None, right: dict | None) -> bool:
    if not left or not right:
        return False
    left_id, right_id = _digits(_get(left, "SoDinhDanh")), _digits(_get(right, "SoDinhDanh"))
    if left_id and right_id:
        return left_id == right_id
    left_name, right_name = _name_key(_get(left, "HoTen")), _name_key(_get(right, "HoTen"))
    return bool(left_name and left_name == right_name and not _dob_conflict(left, right))


def _absorb(target: dict, person: dict) -> None:
    for key, value in person.items():
        if key == "_nguon":
            target["_nguon"] = [*target.get("_nguon", []), *value]
        elif target.get(key) in _EMPTY and value not in _EMPTY:
            target[key] = value


def _merge_strict(*groups: list[dict]) -> list[dict]:
    """Gộp nhân thân CÙNG một người; nguồn đứng trước được ưu tiên giữ giá trị.

    Gom cụm theo SỐ ĐỊNH DANH trước cho mọi bản ghi, rồi mới gắn bản ghi thiếu số vào cụm DUY NHẤT cùng họ
    tên (ngày sinh không mâu thuẫn). Làm hai lượt để kết quả không phụ thuộc thứ tự: bản ghi thiếu số đứng
    trước hai người trùng tên khác số vẫn bị coi là mơ hồ, không bị hút vào người đầu tiên.
    Phần tử đầu kết quả luôn là cụm chứa bản ghi đầu tiên (dùng để bù nhân thân cho một người đã chọn).
    """
    records = [p for group in groups for p in group if p]
    clusters: list[list[int]] = []
    by_id: dict[str, int] = {}
    for i, person in enumerate(records):
        person_id = _digits(_get(person, "SoDinhDanh"))
        if not person_id:
            continue
        if person_id in by_id:
            clusters[by_id[person_id]].append(i)
        else:
            by_id[person_id] = len(clusters)
            clusters.append([i])

    for i, person in enumerate(records):
        if _digits(_get(person, "SoDinhDanh")):
            continue
        name = _name_key(_get(person, "HoTen"))
        hits = [
            c for c, members in enumerate(clusters)
            if name
            and any(_name_key(_get(records[j], "HoTen")) == name for j in members)
            and not any(_dob_conflict(records[j], person) for j in members)
        ] if name else []
        if len(hits) == 1:
            clusters[hits[0]].append(i)
        else:
            # Không khớp ai, hoặc một họ tên khớp nhiều người khác số → không đoán, để riêng.
            clusters.append([i])

    merged: list[dict] = []
    for members in sorted(clusters, key=min):
        person: dict = {"_nguon": []}
        for j in sorted(members):
            _absorb(person, records[j])
        merged.append(person)
    return merged


def _find_anchor(candidates: list[dict], anchor_id: str, anchor_name: str) -> dict | None:
    """Khớp mốc tài khoản: SỐ ĐỊNH DANH trước; ứng viên không có số mới khớp theo họ tên. Duy nhất 1 người."""
    if anchor_id:
        hits = [p for p in candidates if _digits(_get(p, "SoDinhDanh")) == anchor_id]
        if not hits and anchor_name:
            hits = [p for p in candidates
                    if not _digits(_get(p, "SoDinhDanh")) and _name_key(_get(p, "HoTen")) == anchor_name]
    else:
        hits = [p for p in candidates if anchor_name and _name_key(_get(p, "HoTen")) == anchor_name]
    return hits[0] if len(hits) == 1 else None


def _person_area(person: dict | None, order: tuple[str, ...]) -> dict | None:
    if not person:
        return None
    sources = person.get("_nguon") or []
    fallback = None
    for kind in order:
        for source_kind, raw in sources:
            if source_kind != kind:
                continue
            area = _area(raw)
            if area and _plain(area.get("xa")):
                return area
            fallback = fallback or area
    return fallback or _area(_get(person, "NoiCuTru"))


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "1", "yes"):
        return True
    if isinstance(flag, str) and _fold(flag) in ("false", "khong", "0", "no"):
        return False
    return bool(_plain(values.get("ChuHoSo_TenToChuc")))


def _ghi_chu(values: dict) -> str | None:
    text = _plain(values.get("GhiChu_TepDinhChung"))
    if not text:
        return None
    if len(text) <= _GHI_CHU_MAX:
        return text
    cut = text[: _GHI_CHU_MAX - 1]
    space = cut.rfind(" ")
    if space >= _GHI_CHU_MAX - 80:
        cut = cut[:space]
    return cut.rstrip(" ,;:(") + "…"


# ----------------------------------------------------------------------------- enrich

def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    options = options or {}
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    def add(name: str, value, *, default: bool = False) -> None:
        if name in seen or value in _EMPTY:
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    is_org = _is_org(values)
    org_name = _plain(values.get("ChuHoSo_TenToChuc")) if is_org else None
    org_tax = _tax_code(values.get("ChuHoSo_MaSoThue")) if is_org else None

    cards = _people(values, "DanhSachCccd", "Cccd")
    named = _people(values, "NguoiTrongGiayTo", "NguoiTrongGiayTo")
    proxy = _proxy(values)
    nop_block = _flat_block(values, "NguoiNop")
    owner_block = None if is_org else _flat_block(values, "ChuHoSo")
    candidates = _merge_strict(
        cards, named, [proxy] if proxy else [], [nop_block] if nop_block else [],
        [owner_block] if owner_block else [],
    )

    # ================= Khối NGƯỜI NỘP =================
    # Cổng gửi Họ tên + Số Căn cước + Ngày sinh của khối này sang CSDL quốc gia dân cư trước khi cho nộp
    # → cả khối phải là nhân thân của MỘT người.
    ctx = options.get("formContext") or {}
    anchor_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_name = _name_key(ctx.get("applicantFullname") or ctx.get("fullname"))
    has_anchor = bool(anchor_id or anchor_name)
    theo_to_khai = str(options.get("submitterMode") or "") == "owner_as_submitter"

    if theo_to_khai:
        base = proxy or nop_block or owner_block
        nguoi_nop = _merge_strict([base], candidates)[0] if base else None
    else:
        nguoi_nop = _find_anchor(candidates, anchor_id, anchor_name) if has_anchor else None

    if nguoi_nop:
        identity = _id_number(_get(nguoi_nop, "SoDinhDanh"))
        if theo_to_khai:
            add("CongDan_tenCongDan", _person_name(_get(nguoi_nop, "HoTen")))
            add("CongDan_soCmnd", identity)

    # Ô tổ chức của khối người nộp: người được giới thiệu/ủy quyền đứng ra cho ĐƠN VỊ cử đi; không thì
    # người nộp đại diện cho tổ chức chủ hồ sơ. Hồ sơ cá nhân tự nộp → để trống.
    if nguoi_nop and proxy and _same_person(nguoi_nop, proxy) and proxy.get("_donVi"):
        add("CongDan_tenCoQuanToChuc", proxy.get("_donVi"))
        add("CongDan_maSoThueNguoiNop", proxy.get("_maSoThueDonVi"))
    elif is_org:
        add("CongDan_tenCoQuanToChuc", org_name)
        add("CongDan_maSoThueNguoiNop", org_tax)

    if nguoi_nop:
        identity = _id_number(_get(nguoi_nop, "SoDinhDanh"))
        ngay_cap = _date(_get(nguoi_nop, "NgayCap"))
        noi_cap, noi_cap_mac_dinh = _issuer(_get(nguoi_nop, "NoiCap"), identity, ngay_cap)
        add("CongDan_ngaySinhCongDan", _date(_get(nguoi_nop, "NgaySinh")))
        add("CongDan_gioiTinhCongDan", _gender(_get(nguoi_nop, "GioiTinh")))
        add("CongDan_danTocCongDan", _plain(_get(nguoi_nop, "DanToc")))
        add("CongDan_ngayCapCmnd", ngay_cap)
        add("CongDan_noiCapCmnd", noi_cap, default=noi_cap_mac_dinh)
        nop_area = _person_area(nguoi_nop, _NGUON_DIA_CHI_NGUOI_NOP)
        if nop_area:
            # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp AJAX sau khi chọn tỉnh.
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
                    + (_person_name(_get(nguoi_nop, "HoTen")) or "người trong hồ sơ")
                    + ") nhưng tài khoản đang đăng nhập là "
                    + (_plain(ctx.get("applicantFullname")) or "người khác")
                    + ". Cổng xác thực Họ tên/Số Căn cước/Ngày sinh với CSDL quốc gia dân cư trước khi cho "
                    "nộp — lệch tài khoản sẽ bị chặn với thông báo \"Thông tin người nộp hồ sơ không đúng "
                    "với tài khoản đăng nhập!\". Đăng nhập đúng tài khoản người đi nộp, hoặc tắt cài đặt "
                    "\"Lấy người nộp theo tờ khai\"."
                )
    elif theo_to_khai:
        warnings.append(
            "Bật cài đặt \"Lấy người nộp theo tờ khai\" nhưng hồ sơ không có giấy giới thiệu/văn bản ủy quyền và "
            "không đọc được cá nhân yêu cầu đăng ký ở mục 1 Phiếu 01a, nên khối \"Thông tin người nộp\" để "
            "trống — cán bộ nhập tay."
        )
    elif not has_anchor:
        warnings.append(
            "Không xác định được NGƯỜI ĐANG ĐI NỘP: trợ lý chưa đọc được Họ tên/Số Căn cước tài khoản mà cổng "
            "đổ sẵn (trang cổng chưa đăng nhập, hoặc chưa tải lại trang sau khi cập nhật tiện ích). Nhân thân "
            "khối \"Thông tin người nộp\" để trống cho khỏi điền nhầm người — nhấn F5 trang cổng rồi quét lại, "
            "hoặc bật cài đặt \"Lấy người nộp theo tờ khai\" nếu người trong hồ sơ tự đi nộp."
        )
    else:
        warnings.append(
            "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
            + (f" ({_plain(ctx.get('applicantFullname'))})" if ctx.get("applicantFullname") else "")
            + " nên nhân thân khối \"Thông tin người nộp\" để trống — cán bộ nhập tay, KHÔNG lấy thông tin "
            "của người khác trong hồ sơ vì cổng xác thực với CSDL quốc gia dân cư trước khi cho nộp. Nếu "
            "người trong hồ sơ tự đi nộp thì bật cài đặt \"Lấy người nộp theo tờ khai\"."
        )

    # ================= Khối CHỦ HỒ SƠ = người yêu cầu đăng ký =================
    owner = _merge_strict([owner_block], cards, named)[0] if owner_block else None
    if is_org or owner:
        add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_DOANH_NGHIEP if is_org else _DOI_TUONG_CA_NHAN)

    if is_org:
        add("ChuHoSo_tenCoQuanToChucCHS", org_name)
        add("ChuHoSo_maSoThueChuHoSo", org_tax)
        if not (org_name and org_tax):
            warnings.append(
                "Người yêu cầu đăng ký là tổ chức nhưng chưa đọc đủ Tên cơ quan/tổ chức và Mã số thuế — hai ô "
                "này cổng bắt buộc khi Đối tượng là Doanh nghiệp/Tổ chức, cán bộ nhập tay theo mục 1 Phiếu 01a."
            )
    elif owner:
        owner_id = _id_number(_get(owner, "SoDinhDanh"))
        owner_ngay_cap = _date(_get(owner, "NgayCap"))
        owner_noi_cap, owner_noi_cap_mac_dinh = _issuer(_get(owner, "NoiCap"), owner_id, owner_ngay_cap)
        add("ChuHoSo_tenChuHoSo", _person_name(_get(owner, "HoTen")))
        add("ChuHoSo_ngaySinhChuHoSo", _date(_get(owner, "NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo", _gender(_get(owner, "GioiTinh")))
        add("ChuHoSo_danTocChuHoSo", _plain(_get(owner, "DanToc")))
        add("ChuHoSo_soCMNDChuHoSo", owner_id)
        add("ChuHoSo_noiCapCMNDCHS", owner_noi_cap, default=owner_noi_cap_mac_dinh)
        add("ChuHoSo_ngayCapCMNDCHS", owner_ngay_cap)
        if not ("ChuHoSo_tenChuHoSo" in seen and owner_id):
            warnings.append(
                "Chưa đọc đủ Họ tên và Số Căn cước của người yêu cầu đăng ký (mục 1 Phiếu 01a) — hai ô này cổng "
                "bắt buộc khi Đối tượng là Cá nhân, cán bộ nhập tay."
            )
    else:
        warnings.append(
            "Không đọc được người yêu cầu đăng ký ở mục 1 Phiếu 01a nên khối \"Thông tin chủ hồ sơ\" để trống "
            "— cán bộ chọn Đối tượng nộp hồ sơ rồi nhập tay."
        )

    if is_org or owner:
        add("ChuHoSo_faxChuHoSo", _plain(values.get("ChuHoSo_Fax")))
        add("ChuHoSo_emailChuHoSo", _email(values.get("ChuHoSo_Email")) or _email(_get(owner, "Email")))
        add("ChuHoSo_diDongLienLacCHS",
            _phone(values.get("ChuHoSo_DienThoai")) or _phone(_get(owner, "DienThoai")))
        chs_area = _area(values.get("ChuHoSo_NoiCuTru")) if is_org else _person_area(
            owner, _NGUON_DIA_CHI_CHU_HO_SO
        )
        if chs_area:
            add("ChuHoSo_maTinhThanhCHS", province_label(chs_area.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
            if not _plain(chs_area.get("xa")):
                warnings.append(
                    "Địa chỉ chủ hồ sơ ghi theo đơn vị hành chính CŨ (trước sắp xếp) nên không khớp danh mục "
                    "hiện hành — cán bộ chọn tay ô Phường/Xã của khối chủ hồ sơ."
                )
        else:
            warnings.append(
                "Không đọc được địa chỉ của người yêu cầu đăng ký — cán bộ nhập tay Tỉnh/Phường-Xã/Địa chỉ ở "
                "khối chủ hồ sơ."
            )

    # Chặn lọt ô đang bị cổng ẩn theo đối tượng (vd khối phẳng lẫn dữ liệu của nhánh kia).
    hidden = INDIVIDUAL_ONLY_FIELDS if is_org else ORG_ONLY_FIELDS
    out = [f for f in out if f["name"] not in hidden]

    out = chot_khoi_nguoi_nop(
        out, theo_to_khai=theo_to_khai, comp_by_name=UI_COMP_BY_NAME, warnings=warnings
    )

    # --- Bước "Thành phần hồ sơ": ô Ghi chú mô tả tệp gộp nhiều giấy tờ. ---
    ghi_chu = _ghi_chu(values)
    if ghi_chu and "HoSoOnline_ghiChu" not in seen:
        out.append({"name": "HoSoOnline_ghiChu", "comp": UI_COMP_BY_NAME["HoSoOnline_ghiChu"], "value": ghi_chu})
    return out, warnings
