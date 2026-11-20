"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 2.000076 (Cổng DVC Bộ Công an).

Theo file mapping "Mapping_Dang_ky_sang_ten_xe_o_to_BCA" (bước "Nhập thông tin người nộp hồ sơ"):
- Loại đăng ký: có chuyển quyền sở hữu (HĐMB, mục "Sang tên cho chủ xe mới", lý do thu hồi "Chuyển quyền sở hữu", giấy
  lệ phí trước bạ) → "Đăng ký sang tên xe"; lý do thu hồi "Di chuyển" mà không đổi chủ → "Đăng ký di chuyển xe".
- Chủ xe = người đứng tên đăng ký: sang tên là chủ xe MỚI (thẻ căn cước → HĐMB bên mua → GCN thu hồi mục chủ xe mới →
  Giấy khai → giấy LPTB); di chuyển là chính "Chủ xe" trên GCN thu hồi. Thông tin chủ xe cũ / bên bán chỉ để đối chiếu.
- Ô tra cứu (Phần II): biển số, số khung, số máy theo GCN thu hồi → HĐMB → giấy LPTB; mã hồ sơ LPTB theo giấy LPTB.
- Số điện thoại chủ xe: giấy LPTB → GCN thu hồi (GCN hay ghi số giả "00000000000" → bỏ) → Giấy khai. Địa chỉ thường trú:
  giấy ghi theo địa giới 2 cấp mới (Giấy khai, HĐMB, GCN thu hồi) rồi mới tới thẻ (thẻ cũ in quận/huyện cũ).

Hai kịch bản của mapping theo tài khoản VNeID đang đăng nhập (``options.formContext``: Auto Fill / trợ lý đọc ô khoá
``CongDan_tenCongDan`` / ``CongDan_soCmnd`` trước khi điền):
- Tài khoản là chủ xe (hoặc không đọc được tài khoản, hồ sơ không có giấy ủy quyền): tích "Người nộp hồ sơ là chủ xe";
  Mã định danh / Họ tên / Ngày sinh cổng khoá theo tài khoản nên không phát; SĐT / email giữ giá trị cổng đổ sẵn.
- Tài khoản là người KHÁC chủ xe trên giấy (hoặc không đọc được tài khoản mà hồ sơ có giấy ủy quyền làm thủ tục): tích
  "Người nộp hồ sơ là người khai hộ" — cổng mở ô chủ xe để nhập theo giấy và khối "Người được ủy quyền làm thủ tục"; khối
  đó điền theo tài khoản + giấy ủy quyền / thẻ của người được ủy quyền. Người được BÊN BÁN ủy quyền ký hợp đồng mua bán
  KHÔNG phải người làm thủ tục (mapping).

Ô readonly cổng tự điền sau khi người dân nhập mã bảo mật và bấm "Tra cứu" (chứng từ chuyển quyền sở hữu, thông tin xe,
lệ phí trước bạ điện tử) không phát.
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
    _id_number,
    _issuer,
    _plain,
    _same_person,
)
from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process.schema import (
    KINH_DOANH_VAN_TAI,
    LOAI_DANG_KY,
    MAU_BIEN,
    UI_COMP_BY_NAME,
    WAIT_MS,
)
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.mapper import _phone, _vehicle_kind
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.mapper import (
    _code,
    _first,
    _nationality,
    _result_method,
    _text,
)

TRA_CUU_WARNING = (
    "Nhập Mã bảo mật rồi bấm \"Tra cứu\" để cổng lấy thông tin xe, chứng từ chuyển quyền sở hữu và lệ phí trước bạ từ "
    "CSDL; kiểm tra lại các ô đã điền sau khi tra cứu."
)
NO_ACCOUNT_WARNING = (
    "Chưa đối chiếu được giấy tờ với tài khoản VNeID đang đăng nhập (không đọc được ô Họ và tên chủ xe / Mã định danh "
    "trên form) — đã điền theo trường hợp chủ xe tự nộp; nếu người đăng nhập không phải chủ xe thì tích \"Người nộp hồ "
    "sơ là người khai hộ\" và nhập thông tin chủ xe."
)

_TRANSFER_RE = re.compile(r"chuyen quyen|sang ten|mua ban|tang cho|thua ke|chuyen nhuong")
_PLATE_PREFIX_RE = re.compile(r"^bi[eể]n\s*s[oố]\s*(?:xe)?\s*[:.]?\s*", re.IGNORECASE)


def _plate(value) -> str | None:
    """Biển số như trên giấy, bỏ khoảng trắng, viết hoa ("25a - 138.20" → "25A-138.20")."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\s", "", _PLATE_PREFIX_RE.sub("", text)).upper()
    return text if re.search(r"\d", text) else None


def _plate_color(value) -> str | None:
    """Option "Màu biển": đọc màu NỀN (sau chữ "nền"), nền vàng thì phân chữ đen / chữ đỏ."""
    folded = fold(_plain(value) or "")
    if not folded:
        return None
    match = re.search(r"nen\s*(?:mau\s*)?(trang|xanh|vang)", folded)
    if match:
        background, tail = match.group(1), folded[match.end():]
    else:
        background = next((c for c in ("trang", "xanh", "vang") if re.search(rf"\b{c}\b", folded)), None)
        tail = folded
    if background == "vang":
        return MAU_BIEN["vang_do"] if re.search(r"\bdo\b", tail) else MAU_BIEN["vang_den"]
    return MAU_BIEN.get(background) if background else None


def _id_type(number: str | None, label=None) -> str | None:
    """Option "Loại giấy tờ" của form sang tên (mapping): "Căn cước công dân" / "Chứng minh thư nhân dân"."""
    folded = fold(_plain(label) or "")
    if "chung minh" in folded or "cmnd" in folded or (number and len(number) == 9 and not folded):
        return "Chứng minh thư nhân dân"
    if "can cuoc" in folded or "cccd" in folded or (number and len(number) == 12):
        return "Căn cước công dân"
    return None


def _registration_kind(values: dict) -> str | None:
    reason = fold(_plain(values.get("GcnThuHoi_LyDo")) or "")
    if any(key.startswith(("Hdmb_", "GcnThuHoi_ChuMoi")) for key in values) or _TRANSFER_RE.search(reason):
        return LOAI_DANG_KY["sang_ten"]
    if "di chuyen" in reason:
        return LOAI_DANG_KY["di_chuyen"]
    # Di chuyển nguyên chủ không nộp lại lệ phí trước bạ; có giấy LPTB là sang tên.
    if any(key.startswith("Lptb_") for key in values):
        return LOAI_DANG_KY["sang_ten"]
    return None


def _owner(values: dict, moving: bool) -> tuple[dict, dict, str | None, str | None]:
    """(values, thẻ của người khác, họ tên, số định danh) của CHỦ XE. Thẻ căn cước của người KHÁC (bên bán, người được ủy
    quyền) thì tách bộ Cccd_* khỏi ``values`` trả về."""
    if moving:
        refs = ("ToKhai_TenChuXe", "GcnThuHoi_ChuXe", "Lptb_TenNguoiNop")
        ids = ("Cccd_SoDinhDanh", "GcnThuHoi_ChuXeMaDinhDanh", "Lptb_MaDinhDanh")
    else:
        refs = ("Hdmb_BenMuaHoTen", "GcnThuHoi_ChuMoiHoTen", "ToKhai_TenChuXe", "Lptb_TenNguoiNop")
        ids = ("Cccd_SoDinhDanh", "Hdmb_BenMuaSoCccd", "GcnThuHoi_ChuMoiMaDinhDanh", "Lptb_MaDinhDanh")
    owner_ref = _first(*(_text(values.get(key)) for key in refs))
    other_card: dict = {}
    if values.get("Cccd_HoTen") and owner_ref and not _same_person(values.get("Cccd_HoTen"), owner_ref):
        other_card = {key: value for key, value in values.items() if key.startswith("Cccd_")}
        values = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
    owner_name = (_text(values.get("Cccd_HoTen")) or owner_ref or "").upper() or None
    owner_id = _first(*(_id_number(values.get(key)) for key in ids))
    return values, other_card, owner_name, owner_id


def _person(name=None, number=None, **extra) -> dict:
    return {"name": _text(name), "id": _id_number(number), **extra}


def _same_holder(left: dict, right: dict) -> bool | None:
    """Cùng một người? So số định danh trước (số lệch mà họ tên trùng → coi là OCR đọc lệch), thiếu số thì so họ tên;
    không có gì để so → None."""
    if left.get("id") and right.get("id") and len(left["id"]) == len(right["id"]):
        return left["id"] == right["id"] or bool(
            left.get("name") and right.get("name") and _same_person(left["name"], right["name"])
        )
    if left.get("name") and right.get("name"):
        return _same_person(left["name"], right["name"])
    return None


def _account(options: dict | None) -> dict:
    """Tài khoản VNeID đang đăng nhập: ô khoá Họ và tên chủ xe / Mã định danh Auto Fill / trợ lý đọc trước khi điền."""
    context = (options or {}).get("formContext") or {}
    return _person(context.get("applicantFullname"), context.get("applicantIdentityNumber") or context.get("identityNumber"))


def _proxy_person(values: dict, other_card: dict, account: dict, owner: dict, seller: dict) -> tuple[dict, list[str]]:
    """Người làm thủ tục (khai hộ): tài khoản VNeID đang đăng nhập, bổ sung ngày cấp / nơi cấp / liên hệ từ giấy ủy quyền
    và thẻ của đúng người đó. Giấy ủy quyền không do chủ xe lập, thẻ của chủ xe / bên bán thì không lấy."""
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
    for card in (
        {key[len("CccdNduq_"):]: value for key, value in values.items() if key.startswith("CccdNduq_")},
        {key[len("Cccd_"):]: value for key, value in other_card.items()},
    ):
        if not card:
            continue
        person = _person(card.get("HoTen"), card.get("SoDinhDanh"), ngayCap=_date(card.get("NgayCap")),
                         noiCap=_issuer(card.get("NoiCap")))
        if _same_holder(person, owner) or _same_holder(person, seller):
            continue
        docs.append(person)

    if account.get("name") or account.get("id"):
        proxy = dict(account)
        if uq and (uq["name"] or uq["id"]) and _same_holder(uq, proxy) is False:
            warnings.append(
                f"Giấy ủy quyền ghi người được ủy quyền là {(uq['name'] or uq['id'])}, khác tài khoản VNeID đang đăng "
                "nhập — người làm thủ tục phải là người được chủ xe ủy quyền."
            )
    else:
        proxy = next((dict(person) for person in docs if person["name"] or person["id"]), _person())
    for person in docs:
        if person is proxy or _same_holder(person, proxy) is False:
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

    kind = _registration_kind(values)
    moving = kind == LOAI_DANG_KY["di_chuyen"]
    values, other_card, owner_name, owner_id = _owner(values, moving)
    owner = _person(owner_name, owner_id)
    seller = (
        _person() if moving
        else _person(_first(_text(values.get("Hdmb_BenBanHoTen")), _text(values.get("GcnThuHoi_ChuXe"))),
                     values.get("GcnThuHoi_ChuXeMaDinhDanh"))
    )

    # Ai đang nộp: tài khoản VNeID là chủ xe → "chủ xe"; là người khác → "người khai hộ".
    account = _account(options)
    has_account = bool(account["name"] or account["id"])
    relation = _same_holder(account, owner)
    proxy_docs = any(key.startswith(("UyQuyen_", "CccdNduq_")) for key in values)
    is_proxy = relation is False or (not has_account and proxy_docs)
    if not has_account and not is_proxy:
        warnings.append(NO_ACCOUNT_WARNING)

    # ── Phần I: đối tượng nộp hồ sơ ──
    add("CongDan__fsLaNguoiKhaiHo" if is_proxy else "CongDan__fsLaChuXe", True)

    # ── Phần II: tra cứu thông tin xe ──
    plate = _first(_plate(values.get("Xe_BienSo")), _plate(values.get("Lptb_BienSo")))
    chassis = _first(_code(values.get("Xe_SoKhung")), _code(values.get("Lptb_SoKhung")))
    engine = _first(_code(values.get("Xe_SoMay")), _code(values.get("Lptb_SoMay")))
    plate_color = _plate_color(values.get("Xe_MauBien"))
    lptb_code = _code(values.get("Lptb_MaHoSo"))
    add("CongDan__fstracuuLoaiDangKy", kind)
    add("CongDan__fsRadioLoaiXe", _vehicle_kind(values.get("Xe_LoaiXe")))
    add("CongDan__fstracuuMauBien", plate_color)
    add("CongDan__fstracuuBienSo", plate)
    add("CongDan__fstracuuSoKhung", chassis.upper() if chassis else None)
    add("CongDan__fstracuuSoMay", engine.upper() if engine else None)
    add("CongDan__fsTraCuMaHsLPTB", lptb_code)

    # ── Phần III: chủ xe. Chủ xe tự nộp: Mã định danh / Họ tên / Ngày sinh cổng khoá theo tài khoản → không phát ──
    if is_proxy:
        add("CongDan_soCmnd", owner_id)
    id_label = "Căn cước công dân" if values.get("Cccd_SoDinhDanh") or (
        not moving and values.get("Hdmb_BenMuaSoCccd")) else None
    add("CongDan__fsLoaiGiayToChuXe", _id_type(owner_id, id_label))
    issue_date = _date(values.get("Cccd_NgayCap")) or _date(
        values.get("GcnThuHoi_ChuXeNgayCap" if moving else "Hdmb_BenMuaNgayCapCccd"))
    add("CongDan__fsngayCapCmnd", issue_date)
    add(
        "CongDan__fsnoiCapCmnd",
        _issuer(values.get("Cccd_NoiCap"))
        or (None if moving else _issuer(values.get("Hdmb_BenMuaNoiCapCccd")))
        or (default_issuer(issue_date) if issue_date else None),
    )
    if is_proxy:
        add("CongDan_tenCongDan", owner_name)
        add("CongDan__fsnamSinh", _date(values.get("Cccd_NgaySinh")) or (
            None if moving else _date(values.get("Hdmb_BenMuaNgaySinh"))))
    # Thẻ căn cước chỉ cấp cho công dân Việt Nam (mapping: giấy tờ khác không ghi quốc tịch).
    add("CongDan__fsQuocTichChuXe", _nationality(values.get("Cccd_QuocTich")) or (
        "Việt Nam" if id_label and owner_id and len(owner_id) == 12 else None))

    residence = None
    address_keys = ("ToKhai_DiaChi", "Cccd_NoiCuTru") if moving else (
        "ToKhai_DiaChi", "Hdmb_BenMuaDiaChi", "GcnThuHoi_ChuMoiDiaChi", "Cccd_NoiCuTru")
    for key in address_keys:
        area = _area(values.get(key))
        if area and (area.get("tinh") or area.get("xa")):
            residence = area
            break
        residence = residence or area
    if residence and residence.get("tinh"):
        add("CongDan__fsBCAHKTTTinh", province_label(residence.get("tinh")))
        add("CongDan__fsBCAHKTTXa", _plain(residence.get("xa")))
    if residence:
        add("CongDan__fsBCAHKTTDCChiTiet", _plain(residence.get("diaChi")))

    phone = _first(
        None if moving else _phone(values.get("Lptb_DienThoai")),
        None if moving else _phone(values.get("GcnThuHoi_ChuMoiDienThoai")),
        _phone(values.get("ToKhai_DienThoai")),
        _phone(values.get("GcnThuHoi_ChuXeDienThoai")) if moving else None,
    )
    add("CongDan_diDong", phone)
    add("CongDan_email", _email(values.get("ToKhai_Email")))

    # ── Phần IV: người được ủy quyền làm thủ tục (chỉ khi khai hộ) ──
    if is_proxy:
        proxy, proxy_warnings = _proxy_person(values, other_card, account, owner, seller)
        warnings += proxy_warnings
        proxy_issue = proxy.get("ngayCap")
        add("CongDan__fsNDUQHoTen", proxy["name"].upper() if proxy.get("name") else None)
        add("CongDan__fsNDUQMaDinhDanh", proxy.get("id"))
        add("CongDan__fsNDUQLoaiGiayTo", _id_type(proxy.get("id")))
        add("CongDan__fsNDUQNgayCap", proxy_issue)
        add("CongDan__fsNDUQCoQuanCap", proxy.get("noiCap") or (default_issuer(proxy_issue) if proxy_issue else None))
        add("CongDan__fsDiDongNDUQ", proxy.get("phone"))
        add("CongDan__fsEmailNDUQ", proxy.get("email"))
        who = owner_name or "trên giấy tờ"
        if relation is False:
            warnings.append(
                f"Tài khoản VNeID đang đăng nhập không phải chủ xe {who} — đã tích \"Người nộp hồ sơ là người khai hộ\", "
                "điền thông tin chủ xe theo giấy tờ và khối Người được ủy quyền làm thủ tục theo tài khoản; cần văn bản "
                "ủy quyền của chủ xe."
            )
            if _same_holder(account, seller):
                warnings.append(
                    "Tài khoản VNeID đang đăng nhập là chủ xe cũ (bên bán) — đăng ký sang tên do chủ xe mới hoặc người "
                    "được chủ xe mới ủy quyền làm; kiểm tra lại tài khoản trước khi nộp."
                )
        missing = [label for label, name in (
            ("Mã định danh", "CongDan__fsNDUQMaDinhDanh"), ("Cấp ngày", "CongDan__fsNDUQNgayCap"),
            ("Cơ quan cấp", "CongDan__fsNDUQCoQuanCap"), ("Số điện thoại", "CongDan__fsDiDongNDUQ"),
        ) if name not in seen]
        if missing:
            warnings.append("Khối Người được ủy quyền làm thủ tục còn thiếu " + ", ".join(missing) + " (*) — nhập tay.")

    # ── Phần V: kinh doanh vận tải — mặc định "Không" khi hồ sơ không có giấy phép (mapping) ──
    license_no = _text(values.get("GpKdvt_SoGiayPhep"))
    add("CongDan__fsCoKinhDoanhvanTai", KINH_DOANH_VAN_TAI["co" if license_no else "khong"])
    if license_no:
        add("CongDan__fsSoGiayPhepKinhDoanh", license_no)
        add("CongDan__fsngayCapGPKD", _date(values.get("GpKdvt_NgayCap")))
        add("CongDan__fsNoiCapGPKD", _text(values.get("GpKdvt_NoiCap")))

    # ── Phần VII: biển số trúng đấu giá (chỉ khi hồ sơ có giấy xác nhận) ──
    auction_plate = _plate(values.get("DauGia_BienSo"))
    auction_no = _code(values.get("DauGia_SoGiay"))
    if auction_plate or auction_no:
        add("CongDan__fs359581_checkbox_1", True)
        add("CongDan__fsBienSoTrungDauGia", auction_plate)
        add("CongDan__fsSoGiayXnTrungDauGia", auction_no)
        add("CongDan__fsNGayCapBienDauGia", _date(values.get("DauGia_NgayCap")))
        add("CongDan__fsCoQuanCapBienDauGia", _text(values.get("DauGia_CoQuanCap")))

    # ── Phần VIII: nhận kết quả — người nhận mặc định là chủ xe, tại địa chỉ thường trú của chủ xe ──
    add("CongDan__fsHinhThucNhanKQ", _result_method(values.get("HoSo_HinhThucNhanKetQua")))
    add("CongDan__fsTenNguoiNhanKQ", owner_name)
    add("CongDan__fsSoDienThoaiNguoiNhan", phone)
    if residence and residence.get("tinh"):
        add("CongDan__fsTinhNhanKQ", province_label(residence.get("tinh")))
        add("CongDan__fsXaNhanKQ", _plain(residence.get("xa")))
    if residence:
        add("CongDan__fsDiaChiChiTietNhanKQ", _plain(residence.get("diaChi")))

    # ── Cảnh báo ──
    if not kind:
        warnings.append("Không xác định được Loại đăng ký (sang tên / di chuyển) từ giấy tờ — chọn tay ô Loại đăng ký (*).")
    lookup = [("Màu biển", plate_color), ("Biển số cũ", plate), ("Số khung", chassis), ("Số máy", engine)]
    if not moving:  # di chuyển nguyên chủ không có giấy lệ phí trước bạ mới
        lookup.append(("Mã hồ sơ lệ phí trước bạ", lptb_code))
    missing = [label for label, value in lookup if not value]
    if missing:
        warnings.append("Không đọc được " + ", ".join(missing) + " — cần nhập tay trước khi bấm Tra cứu.")
    if not phone:
        warnings.append("Giấy tờ không có số điện thoại chủ xe — ô Số điện thoại của chủ xe (*) cần nhập tay.")
    if "CongDan__fsHinhThucNhanKQ" not in seen:
        warnings.append("Giấy tờ không ghi hình thức nhận kết quả — chọn tay ô Hình thức nhận kết quả (*).")
    warnings.append(TRA_CUU_WARNING)
    # Ô liên hệ của chủ xe = chủ tài khoản VNeID khi tự nộp: cổng đổ sẵn thì giữ nguyên (user 20/11/2026). Khai hộ thì
    # các ô này là của chủ xe trên giấy, không phải của tài khoản → ghi theo giấy.
    if not is_proxy:
        keep_portal_values(out, ('CongDan_diDong', 'CongDan_email'))
    return out, warnings
