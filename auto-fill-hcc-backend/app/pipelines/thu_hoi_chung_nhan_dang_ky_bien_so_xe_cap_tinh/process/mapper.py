"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 2.001485 (Cổng DVC Bộ Công an).

Theo file mapping "Mapping_Thu_hoi_CNDK_BSX" (màn kê khai "Nộp hồ sơ trực tuyến"):
- Chủ xe = người đứng tên trên Giấy chứng nhận đăng ký xe (thẻ căn cước → Giấy ĐKX → HĐMB bên bán → Giấy khai thu hồi).
  Thông tin bên bán trong hợp đồng chỉ dùng cho chủ xe khi bên bán đúng là người đứng tên Giấy ĐKX.
- Chủ xe mới (Phần V) = bên mua: thẻ căn cước của bên mua → HĐMB bên mua.
- Ô tra cứu + Phần VI (thông tin xe): Giấy ĐKX trước, HĐMB sau; Giấy ĐKX chụp mất một phần số khung / số máy mà hợp
  đồng ghi đủ (phần đọc được khớp) thì lấy bản đủ. Biển số nhập liền ("25A-039.07" → "25A03907") vì ô tra cứu tự xoá
  dấu chấm, khoảng trắng, gạch ngang.
- Lý do thu hồi: Giấy khai thu hồi ghi lý do → option tương ứng; không có mà hồ sơ có hợp đồng mua bán / tặng cho →
  "Chuyển quyền sở hữu" (cổng bắt buộc khối chủ xe mới).
- Số điện thoại / email in ở trang bìa hợp đồng là của văn phòng công chứng — không dùng.

Hai kịch bản theo tài khoản VNeID đang đăng nhập (``options.formContext``: Auto Fill / trợ lý đọc ô khoá
``CongDan_tenCongDan`` / ``CongDan_soCmnd`` — cổng tích sẵn "Người nộp hồ sơ là chủ xe" và đổ thông tin tài khoản):
- Tài khoản là chủ xe (hoặc không đọc được tài khoản, hồ sơ không có giấy ủy quyền): tích "Người nộp hồ sơ là chủ xe";
  Mã định danh / Họ tên / Ngày sinh cổng khoá theo tài khoản nên không phát; SĐT / email giữ giá trị cổng đổ sẵn.
- Tài khoản là người KHÁC chủ xe (bên mua, người được ủy quyền): tích "Người nộp hồ sơ là người khai hộ" — cổng mở ô
  chủ xe để nhập theo giấy và đổ khối "Người được ủy quyền làm thủ tục" theo tài khoản; mapper bổ sung loại giấy tờ,
  ngày cấp, cơ quan cấp, liên hệ từ hợp đồng (bên mua) / giấy ủy quyền / thẻ của đúng người đó.

Mã bảo mật, nút Tra cứu, điểm đăng ký, ô ẩn không phát.
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.formatting import clean_email as _email
from app.pipelines._shared.formatting import keep_portal_values
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _full_address,
    _id_number,
    _issuer,
    _plain,
    _same_person,
)
from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process.mapper import (
    _account,
    _id_type,
    _person,
    _plate_color,
    _same_holder,
)
from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process.schema import MAU_BIEN
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.mapper import _phone, _vehicle_kind
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.mapper import (
    _first,
    _nationality,
    _number,
    _result_method,
    _text,
)
from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_cap_tinh.process.schema import (
    LY_DO_CAN_CHU_MOI,
    LY_DO_THU_HOI,
    UI_COMP_BY_NAME,
    WAIT_MS,
)

TRA_CUU_WARNING = (
    "Nhập Mã bảo mật rồi bấm \"Tra cứu\" để cổng lấy thông tin xe từ CSDL đăng ký xe và mở khoá các phần bên dưới; "
    "kiểm tra lại các ô đã điền sau khi tra cứu."
)
NO_ACCOUNT_WARNING = (
    "Chưa đối chiếu được giấy tờ với tài khoản VNeID đang đăng nhập (không đọc được ô Họ và tên chủ xe / Mã định danh "
    "trên form) — đã điền theo trường hợp chủ xe tự nộp; nếu người đăng nhập không phải chủ xe thì tích \"Người nộp hồ "
    "sơ là người khai hộ\" và nhập thông tin chủ xe."
)

_PLATE_PREFIX_RE = re.compile(r"^bi[eể]n\s*s[oố]\s*(?:đăng\s*ký|dang\s*ky)?\s*(?:xe)?\s*[:.]?\s*", re.IGNORECASE)
# Giấy ĐKX in ký hiệu màu biển trong ngoặc ngay sau nhãn "Biển số đăng ký (N°Plate)": (T) trắng, (X) xanh, (V) vàng.
_PLATE_LETTER = {"t": MAU_BIEN["trang"], "x": MAU_BIEN["xanh"], "v": MAU_BIEN["vang_den"]}
_YEAR_RE = re.compile(r"\b(19[5-9]\d|20\d\d)\b")
# Lý do ghi tự do trên Giấy khai thu hồi → option cổng. Xét theo thứ tự (đấu giá trước "sang tên", "chuyển quyền").
_REASON_RULES = (
    ("sang_ten_dau_gia", r"sang ten\b.*\bdau gia|trung dau gia"),
    ("cap_bien_dau_gia", r"cap bien dau gia|bien dau gia"),
    ("mien_thue", r"mien thue|tam nhap|tai xuat"),
    ("chuyen_quyen", r"chuyen quyen|sang ten|mua ban|ban xe|tang cho|cho tang|thua ke|chuyen nhuong"),
    ("di_chuyen", r"di chuyen|chuyen (?:di |ve |sang )?tinh"),
    ("mat_cap", r"mat cap|trom|chiem doat"),
    ("hong", r"\bhong\b|pha huy|tai nan"),
    ("nien_han", r"nien han|khong duoc phep luu hanh"),
    ("thao_may", r"thao (?:may|khung)|thay the cho xe"),
    ("tich_thu", r"tich thu|sung quy"),
    ("sai_he_bien", r"he bien"),
    ("ho_so_gia", r"ho so gia|giay to gia"),
    ("nghiep_vu", r"nghiep vu"),
)


def _words(value) -> str:
    """Chữ không dấu, bỏ dấu câu — để so cụm từ."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", fold(_plain(value) or "")).split())


def _plate(value) -> str | None:
    """Biển số nhập liền như mapping ("25A-039.07" → "25A03907"; "(T)" ký hiệu màu biển bỏ đi)."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\(.*?\)", " ", _PLATE_PREFIX_RE.sub("", text))
    text = re.sub(r"[\s.\-–_/]", "", text).upper()
    return text if re.search(r"\d", text) else None


def _plate_color_dkx(*values) -> str | None:
    """Option "Màu biển": ký hiệu một chữ của Giấy ĐKX ("T", "(T)") hoặc chữ mô tả màu nền."""
    for value in values:
        letter = _words(value)
        if letter in _PLATE_LETTER:
            return _PLATE_LETTER[letter]
        color = _plate_color(value)
        if color:
            return color
    return None


def _vin(primary, fallback) -> tuple[str | None, bool]:
    """(số khung / số máy viết liền IN HOA, lấy theo giấy ưu tiên?). Giấy ĐKX chụp mất đầu/đuôi mà hợp đồng ghi đủ, phần
    đọc được khớp → lấy bản đủ của hợp đồng (mapping: "…41BBLN035039" → "RLUA341BBLN035039")."""
    first, second = (
        (re.sub(r"[\s…]", "", _text(value) or "").strip(".").upper() or None) for value in (primary, fallback)
    )
    if first and second and len(second) > len(first) and (second.endswith(first) or second.startswith(first)):
        return second, False
    return first or second, bool(first)


def _reason(value) -> str | None:
    words = _words(value)
    if not words:
        return None
    for option in LY_DO_THU_HOI.values():
        if _words(option) in words:
            return option
    for key, pattern in _REASON_RULES:
        if re.search(pattern, words):
            return LY_DO_THU_HOI[key]
    return None


def _year(value) -> str | None:
    match = _YEAR_RE.search(_plain(value) or "")
    return match.group(1) if match else None


def _upper(value) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _residence(*values) -> dict | None:
    """Địa chỉ đầu tiên có Tỉnh/Xã; không có thì địa chỉ đầu tiên chỉ có phần chi tiết."""
    fallback = None
    for value in values:
        area = _area(value)
        if area and (area.get("tinh") or area.get("xa")):
            return area
        fallback = fallback or area
    return fallback


def _id_doc(card: dict, number, date, issuer, birth=None) -> dict:
    """Ngày cấp / cơ quan cấp lấy theo cùng một giấy: thẻ có ngày cấp thì cơ quan theo thẻ (hoặc suy từ ngày cấp thẻ) —
    hợp đồng có thể ghi căn cước cũ."""
    card_date = _date(card.get("NgayCap"))
    issue = card_date or _date(date)
    if card_date:
        noi_cap = _issuer(card.get("NoiCap")) or default_issuer(card_date)
    else:
        noi_cap = _issuer(card.get("NoiCap")) or _issuer(issuer) or (default_issuer(issue) if issue else None)
    return {
        "id": _first(_id_number(card.get("SoDinhDanh")), _id_number(number)),
        "ngayCap": issue,
        "noiCap": noi_cap,
        "ngaySinh": _first(_date(card.get("NgaySinh")), _date(birth)),
    }


def _sort_cards(values: dict, owner_ref: dict, buyer_ref: dict) -> dict:
    """Thẻ căn cước theo vai {owner, buyer, proxy, other}. LLM xếp nhầm vai (thẻ bên mua vào Cccd_*…) thì xếp lại theo họ
    tên / số định danh so với Giấy ĐKX và hợp đồng; thẻ không khớp ai (vợ/chồng bên bán, người làm thủ tục) → other."""
    cards: dict = {"owner": {}, "buyer": {}, "proxy": {}, "other": []}
    for prefix, default, ref in (
        ("Cccd_", "owner", owner_ref), ("CccdChuMoi_", "buyer", buyer_ref), ("CccdNduq_", "proxy", None),
    ):
        card = {key[len(prefix):]: value for key, value in values.items() if key.startswith(prefix)}
        if not card:
            continue
        person = _person(card.get("HoTen"), card.get("SoDinhDanh"))
        if _same_holder(person, owner_ref):
            role = "owner"
        elif _same_holder(person, buyer_ref):
            role = "buyer"
        elif ref is None or _same_holder(person, ref) is None:
            role = default
        else:
            role = "other"
        if role == "other" or cards[role]:
            cards["other"].append(card)
        else:
            cards[role] = card
    return cards


def _proxy_person(values: dict, cards: dict, account: dict, owner: dict, buyer: dict) -> tuple[dict, list[str]]:
    """Người làm thủ tục (khai hộ): tài khoản VNeID đang đăng nhập, bổ sung ngày cấp / nơi cấp / liên hệ từ hợp đồng (khi
    tài khoản là bên mua), giấy ủy quyền và thẻ của đúng người đó. Giấy ủy quyền không do chủ xe lập thì không lấy."""
    warnings: list[str] = []
    docs = []
    uq = None
    grantor = _text(values.get("UyQuyen_BenUyQuyenHoTen"))
    if any(key.startswith("UyQuyen_") for key in values) and not (
        grantor and owner.get("name") and not _same_person(grantor, owner["name"])
    ):
        uq = _person(
            values.get("UyQuyen_HoTen"), values.get("UyQuyen_SoDinhDanh"),
            ngayCap=_date(values.get("UyQuyen_NgayCap")), noiCap=_issuer(values.get("UyQuyen_NoiCap")),
            phone=_phone(values.get("UyQuyen_DienThoai")), email=_email(values.get("UyQuyen_Email")),
        )
        docs.append(uq)
    for card in (cards["proxy"], *cards["other"]):
        if not card:
            continue
        person = _person(card.get("HoTen"), card.get("SoDinhDanh"), **{
            k: v for k, v in _id_doc(card, None, None, None).items() if k in ("ngayCap", "noiCap")})
        if not _same_holder(person, owner):
            docs.append(person)
    if buyer.get("name") or buyer.get("id"):
        docs.append(buyer)

    if account.get("name") or account.get("id"):
        proxy = dict(account)
        if uq and (uq["name"] or uq["id"]) and _same_holder(uq, proxy) is False:
            warnings.append(
                f"Giấy ủy quyền ghi người được ủy quyền là {(uq['name'] or uq['id'])}, khác tài khoản VNeID đang đăng "
                "nhập — người làm thủ tục phải là người được chủ xe ủy quyền."
            )
    else:
        proxy = next((dict(person) for person in docs if (person["name"] or person["id"]) and person is not buyer),
                     _person())
    for person in docs:
        if not _same_holder(person, proxy):
            continue
        for key, value in person.items():
            if value and not proxy.get(key):
                proxy[key] = value
    return proxy, warnings


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    warnings: list[str] = []
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in WAIT_MS:
            field["waitMs"] = WAIT_MS[name]
        out.append(field)
        seen.add(name)

    # ── Ai là chủ xe / chủ xe mới ──
    registered = _first(_text(values.get("Dkx_TenChuXe")), _text(values.get("ToKhai_TenChuXe")))
    seller = _text(values.get("Hdmb_BenBanHoTen"))
    seller_is_owner = bool(seller) and (not registered or _same_person(seller, registered))
    if seller and registered and not seller_is_owner:
        warnings.append(
            f"Bên bán trong hợp đồng ({seller}) khác chủ xe trên Giấy chứng nhận đăng ký xe ({registered}) — đã điền chủ "
            "xe theo Giấy chứng nhận đăng ký xe; kiểm tra lại người đứng tên trước khi nộp."
        )
    seller_get = (lambda key: values.get(key)) if seller_is_owner else (lambda key: None)
    owner_ref = _person(registered or seller, seller_get("Hdmb_BenBanSoCccd"))
    buyer_ref = _person(values.get("Hdmb_BenMuaHoTen"), values.get("Hdmb_BenMuaSoCccd"))
    cards = _sort_cards(values, owner_ref, buyer_ref)

    owner_card = cards["owner"]
    owner_doc = _id_doc(owner_card, seller_get("Hdmb_BenBanSoCccd"), seller_get("Hdmb_BenBanNgayCapCccd"),
                        seller_get("Hdmb_BenBanNoiCapCccd"), seller_get("Hdmb_BenBanNgaySinh"))
    owner_name = _upper(_first(_text(owner_card.get("HoTen")), registered, seller))
    owner_id = owner_doc["id"]
    owner = _person(owner_name, owner_id)

    buyer_card = cards["buyer"]
    buyer_doc = _id_doc(buyer_card, values.get("Hdmb_BenMuaSoCccd"), values.get("Hdmb_BenMuaNgayCapCccd"),
                        values.get("Hdmb_BenMuaNoiCapCccd"))
    buyer_name = _upper(_first(_text(buyer_card.get("HoTen")), _text(values.get("Hdmb_BenMuaHoTen"))))
    buyer = _person(buyer_name, buyer_doc["id"], ngayCap=buyer_doc["ngayCap"], noiCap=buyer_doc["noiCap"])

    reason = _reason(values.get("ToKhai_LyDoThuHoi")) or (
        LY_DO_THU_HOI["chuyen_quyen"] if buyer_name or any(key.startswith("Hdmb_") for key in values) else None
    )

    # Ai đang nộp: tài khoản VNeID là chủ xe → "chủ xe"; là người khác → "người khai hộ".
    account = _account(options)
    has_account = bool(account["name"] or account["id"])
    relation = _same_holder(account, owner)
    proxy_docs = bool(cards["proxy"]) or any(key.startswith("UyQuyen_") for key in values)
    is_proxy = relation is False or (not has_account and proxy_docs)
    if not has_account and not is_proxy:
        warnings.append(NO_ACCOUNT_WARNING)

    # ── Phần I: người nộp hồ sơ ──
    add("CongDan__fsLaNguoiKhaiHo" if is_proxy else "CongDan__fsLaChuXe", True)

    # ── Phần II: tra cứu thông tin xe ──
    kind = _vehicle_kind(values.get("Dkx_LoaiXe"), values.get("Hdmb_LoaiXe"), values.get("Hdmb_TenVanBan"))
    plate = _first(_plate(values.get("Dkx_BienSo")), _plate(values.get("Hdmb_BienSo")))
    plate_color = _plate_color_dkx(values.get("Dkx_MauBien"))
    engine, _ = _vin(values.get("Dkx_SoMay"), values.get("Hdmb_SoMay"))
    chassis, chassis_from_dkx = _vin(values.get("Dkx_SoKhung"), values.get("Hdmb_SoKhung"))
    add("CongDan__fsRadioLoaiXe", kind)
    add("CongDan__fstracuuBienSo", plate)
    add("CongDan__fstracuuMauBien", plate_color)
    add("CongDan__fstracuuSoMay", engine)
    add("CongDan__fstracuuSoKhung", chassis)
    add("CongDan__fslyDoThuHoi", reason)

    # ── Phần III: chủ xe. Chủ xe tự nộp: Mã định danh / Họ tên / Ngày sinh cổng khoá theo tài khoản → không phát ──
    if is_proxy:
        add("CongDan_soCmnd", owner_id)
    id_label = "Căn cước công dân" if owner_card.get("SoDinhDanh") or seller_get("Hdmb_BenBanSoCccd") else None
    add("CongDan__fsLoaiGiayToChuXe", _id_type(owner_id, id_label))
    # Ngày cấp in trên thẻ / hợp đồng, không để ngày cập nhật số định danh cổng đổ sẵn (mapping dòng 13).
    add("CongDan__fsngayCapCmnd", owner_doc["ngayCap"])
    add("CongDan__fsnoiCapCmnd", owner_doc["noiCap"])
    if is_proxy:
        add("CongDan_tenCongDan", owner_name)
        add("CongDan__fsnamSinh", owner_doc["ngaySinh"])
    # Thẻ căn cước chỉ cấp cho công dân Việt Nam (mapping: hợp đồng / Giấy ĐKX không ghi quốc tịch).
    add("CongDan__fsQuocTichChuXe", _nationality(owner_card.get("QuocTich")) or (
        "Việt Nam" if id_label and owner_id and len(owner_id) == 12 else None))

    residence = _residence(values.get("ToKhai_DiaChi"), owner_card.get("NoiCuTru"), seller_get("Hdmb_BenBanDiaChi"))
    if residence and residence.get("tinh"):
        add("CongDan__fsBCAHKTTTinh", province_label(residence.get("tinh")))
        add("CongDan__fsBCAHKTTXa", _plain(residence.get("xa")))
    if residence:
        add("CongDan__fsBCAHKTTDCChiTiet", _plain(residence.get("diaChi")))

    phone = _phone(values.get("ToKhai_DienThoai"))
    add("CongDan_diDong", phone)
    add("CongDan_email", _email(values.get("ToKhai_Email")))

    # ── Phần IV: người được ủy quyền làm thủ tục (chỉ khi khai hộ; cổng đổ sẵn họ tên / mã định danh / ngày cấp) ──
    if is_proxy:
        proxy, proxy_warnings = _proxy_person(values, cards, account, owner, buyer)
        warnings += proxy_warnings
        proxy_issue = proxy.get("ngayCap")
        add("CongDan__fsNDUQHoTen", _upper(proxy.get("name")))
        add("CongDan__fsNDUQMaDinhDanh", proxy.get("id"))
        add("CongDan__fsNDUQLoaiGiayTo", _id_type(proxy.get("id")) or "Căn cước công dân")
        add("CongDan__fsNDUQNgayCap", proxy_issue)
        add("CongDan__fsNDUQCoQuanCap", proxy.get("noiCap") or (default_issuer(proxy_issue) if proxy_issue else None))
        add("CongDan__fsDiDongNDUQ", proxy.get("phone"))
        add("CongDan__fsEmailNDUQ", proxy.get("email"))
        who = owner_name or "trên giấy tờ"
        if relation is False and _same_holder(account, buyer):
            warnings.append(
                f"Tài khoản VNeID đang đăng nhập là bên mua, không phải chủ xe {who} — đã tích \"Người nộp hồ sơ là người "
                "khai hộ\", điền thông tin chủ xe theo giấy tờ và khối Người được ủy quyền làm thủ tục theo tài khoản."
            )
        elif relation is False:
            warnings.append(
                f"Tài khoản VNeID đang đăng nhập không phải chủ xe {who} — đã tích \"Người nộp hồ sơ là người khai hộ\", "
                "điền thông tin chủ xe theo giấy tờ và khối Người được ủy quyền làm thủ tục theo tài khoản; cần văn bản "
                "ủy quyền của chủ xe."
            )
        missing = [label for label, name in (
            ("Cơ quan cấp", "CongDan__fsNDUQCoQuanCap"), ("Số điện thoại", "CongDan__fsDiDongNDUQ"),
        ) if name not in seen]
        if missing:
            warnings.append("Khối Người được ủy quyền làm thủ tục còn thiếu " + ", ".join(missing) + " (*) — nhập tay.")

    # ── Phần V: chủ xe mới (bên mua) ──
    buyer_address = _residence(buyer_card.get("NoiCuTru"), values.get("Hdmb_BenMuaDiaChi"))
    add("CongDan__fsChuMoiHoTen", buyer_name)
    add("CongDan__fsChuMoiDiaChi", _full_address(buyer_address))
    add("CongDan__fsChuMoiMaDinhDanh", buyer_doc["id"])
    if reason in LY_DO_CAN_CHU_MOI:
        missing = [label for label, name in (
            ("Họ và tên", "CongDan__fsChuMoiHoTen"), ("Địa chỉ", "CongDan__fsChuMoiDiaChi"),
            ("Mã định danh", "CongDan__fsChuMoiMaDinhDanh"), ("Số điện thoại", "CongDan__fsChuMoiSDT"),
        ) if name not in seen]
        if missing:
            warnings.append(
                f"Lý do thu hồi \"{reason}\" bắt buộc khối Thông tin chủ xe mới — còn thiếu " + ", ".join(missing)
                + " (*) — nhập tay."
            )

    # ── Phần VI: thông tin xe (cổng ghi đè bằng CSDL sau Tra cứu; ô CSDL không trả thì giữ giá trị theo giấy) ──
    add("CongDan__fsnhanHieu", _upper(_first(_text(values.get("Dkx_NhanHieu")), _text(values.get("Hdmb_NhanHieu")))))
    add("CongDan__fssoLoai", _first(_text(values.get("Dkx_SoLoai")), _text(values.get("Hdmb_SoLoai"))))
    add("CongDan__fsSoMay1", engine)
    add("CongDan__fsSoKhung", chassis)
    year = _year(values.get("Dkx_NamSanXuat"))
    add("CongDan__fsNamSanXuat", year)
    add("CongDan__fsDungTich", _first(_number(values.get("Dkx_DungTich")), _number(values.get("Hdmb_DungTich"))))
    add("CongDan__fscongSuat", _number(values.get("Dkx_CongSuat")))
    add("CongDan__fstrongTai", _number(values.get("Dkx_TaiTrong")))
    add("CongDan__fsSoChoNgoi", _first(_number(values.get("Dkx_SoChoNgoi")), _number(values.get("Hdmb_SoChoNgoi"))))
    add("CongDan__fsSoChoDung", _number(values.get("Dkx_SoChoDung")))
    add("CongDan__fsSoChoNam", _number(values.get("Dkx_SoChoNam")))

    # ── Phần VII: nhận kết quả — người nhận mặc định là chủ xe, tại địa chỉ thường trú của chủ xe ──
    add("CongDan__fsHinhThucNhanKQ", _result_method(values.get("HoSo_HinhThucNhanKetQua")))
    add("CongDan__fsTenNguoiNhanKQ", owner_name)
    add("CongDan__fsSoDienThoaiNguoiNhan", phone)
    if residence and residence.get("tinh"):
        add("CongDan__fsTinhNhanKQ", province_label(residence.get("tinh")))
        add("CongDan__fsXaNhanKQ", _plain(residence.get("xa")))
    if residence:
        add("CongDan__fsDiaChiChiTietNhanKQ", _plain(residence.get("diaChi")))

    # ── Cảnh báo ──
    if not reason:
        warnings.append("Không xác định được Lý do thu hồi từ giấy tờ — chọn tay ô Lý do thu hồi (*).")
    missing = [label for label, value in (
        ("Ô tô / Xe máy", kind), ("Biển số", plate), ("Màu biển", plate_color), ("Số khung", chassis),
    ) if not value]
    if missing:
        warnings.append("Không đọc được " + ", ".join(missing) + " — cần nhập tay trước khi bấm Tra cứu.")
    elif chassis_from_dkx and kind == "Ô tô" and len(chassis) < 17:
        warnings.append(
            f"Số khung chỉ đọc được {len(chassis)} ký tự trên Giấy chứng nhận đăng ký xe — đối chiếu bản gốc, nhập đủ số "
            "khung trước khi bấm Tra cứu."
        )
    if not phone:
        warnings.append("Giấy tờ không có số điện thoại chủ xe — ô Số điện thoại của chủ xe (*) cần nhập tay.")
    if not year:
        warnings.append(
            "Giấy tờ không ghi Năm sản xuất — sau khi Tra cứu, nhập tay ô Năm sản xuất (*) (cổng không lấy từ CSDL)."
        )
    if "CongDan__fsHinhThucNhanKQ" not in seen:
        warnings.append("Giấy tờ không ghi hình thức nhận kết quả — chọn tay ô Hình thức nhận kết quả (*).")
    warnings.append(TRA_CUU_WARNING)
    # Ô liên hệ của chủ tài khoản VNeID: chủ xe tự nộp → Phần III; khai hộ → khối người làm thủ tục. Cổng đổ sẵn thì giữ.
    if is_proxy:
        keep_portal_values(out, ('CongDan__fsDiDongNDUQ', 'CongDan__fsEmailNDUQ'))
    else:
        keep_portal_values(out, ('CongDan_diDong', 'CongDan_email'))
    return out, warnings
