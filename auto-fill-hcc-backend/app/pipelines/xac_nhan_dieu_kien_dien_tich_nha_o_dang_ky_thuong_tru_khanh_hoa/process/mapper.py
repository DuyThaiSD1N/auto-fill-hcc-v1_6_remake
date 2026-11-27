"""Map compact source facts → Form.io data[...] cho Khánh Hòa - xác nhận điều kiện diện tích nhà ở để đăng ký thường trú
(1.013314), theo file mapping "Mapping_XN-cho-o-hop-phap_Mau02_KhanhHoa.xlsx" (27/11/2026).

Form TRÙNG 1.115148 Khánh Hòa nên dùng lại cách dựng hai khối của mapper đó:
  - Chủ hồ sơ = NGƯỜI ĐỀ NGHỊ trên Tờ khai Mẫu 02 (mục I): ownerFullname, ownerIdentityNumber, ownerBirthday,
    ownerPhoneNumber, ownerAddress (MỘT ô chữ: "<chi tiết>, <Phường/Xã>, <Tỉnh>" — nơi cư trú mục I.4 / CCCD).
  - Người nộp: có giấy của người nộp thay (Giấy ủy quyền bên B, hoặc CCCD của người KHÁC chủ hồ sơ) → người đó, BỎ tick
    "Người nộp hồ sơ đồng thời là chủ hồ sơ"; còn lại (tự nộp) → chính chủ hồ sơ, TICK ô đó. Bật "Lấy người nộp theo tờ
    khai" (options.submitterMode) → luôn là người đề nghị.
Ô chữ/ngày giấy tờ không có thì TRẢ VỀ TRỐNG (clear, ô bắt buộc tô đỏ) — cổng đổ sẵn khối người nộp và ngày sinh chủ hồ sơ
theo TÀI KHOẢN đăng nhập; tài khoản chính là người nộp thì giữ khối người nộp của cổng.

"Nội dung yêu cầu giải quyết" ghép tất định theo dữ liệu mẫu của file mapping: mục III.1 của Tờ khai (cụm "địa chỉ nêu
trên" thay bằng địa chỉ chỗ ở hợp pháp mục II.1) + "Tổng số người thuê, mượn, ở nhờ" + "Tổng số diện tích chỗ ở hợp pháp
thuê, mượn, ở nhờ". Không có mục III thì "Đề nghị xác nhận chỗ ở hợp pháp tại địa chỉ <II.1>"; không có gì → tên thủ tục.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_ward
from app.pipelines.cap_doi_gcn_khanh_hoa.process.mapper import PORTAL_PROVINCE, _person_area, _phone_vn, phone_warning
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import (
    _by_name,
    _date,
    _fold,
    _identity,
    _province,
    _text,
    _ward,
    account_is_applicant,
    submitter_is_declarant,
)
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.process.mapper import (
    _BLANK_APPLICANT,
    _BLANK_OWNER,
    _REQUIRED_LABELS,
    _full_address,
)
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.mapper import _cccd_issuer, _gender

from .schema import TEN_THU_TUC, UI_COMP_BY_NAME

# Mục III.1 của Tờ khai hay viết "chỗ ở hợp pháp tại địa chỉ nêu trên" → thay bằng địa chỉ mục II.1 (như dữ liệu mẫu).
_HERE =re.compile(r"(?i)địa chỉ\s+(?:nêu|ghi)\s+(?:trên|ở trên)")
# Tiền tố đơn vị hành chính viết thường khi nằm giữa câu ("tại … phường Nha Trang, tỉnh Khánh Hòa").
_ADMIN_PREFIX = re.compile(r"^(Phường|Xã|Thị trấn|Đặc khu|Tỉnh|Thành phố)\b")


def _lower_prefix(text: str | None) -> str | None:
    return _ADMIN_PREFIX.sub(lambda m: m.group(1).lower(), text) if text else None


def sentence_address(area: dict | None) -> str | None:
    """Địa chỉ chỗ ở trong câu: "Số 25 đường Lê Thánh Tôn, phường Nha Trang, tỉnh Khánh Hòa"."""
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _lower_prefix(_ward(area)), _lower_prefix(_province(area))]
    return ", ".join(part for part in parts if part) or None


def _clause(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"(?i)(\d)\s*m2\b", r"\1 m²", text).rstrip(" .")
    return text or None


def request_text(values: dict, home: dict | None) -> str:
    address = sentence_address(home)
    sentences: list[str] = []
    status = _clause(values.get("ToKhai_TinhTrangChoO"))
    if status:
        if address and _HERE.search(status):
            status = _HERE.sub(lambda _m: f"địa chỉ {address}", status, count=1)
        elif address and _fold(_text(home.get("diaChi")) or address) not in _fold(status):
            sentences.append(f"Địa chỉ chỗ ở hợp pháp: {address}")
        sentences.append(status[0].upper() + status[1:])
    elif address:
        sentences.append(f"Đề nghị xác nhận chỗ ở hợp pháp tại địa chỉ {address}")
    people = _clause(values.get("ToKhai_SoNguoiThueMuon"))
    if people:
        sentences.append(f"Tổng số người thuê, mượn, ở nhờ: {people}")
    area = _clause(values.get("ToKhai_DienTichThueMuon"))
    if area:
        sentences.append(f"Tổng số diện tích chỗ ở hợp pháp thuê, mượn, ở nhờ: {area}")
    return ". ".join(sentences) + "." if sentences else TEN_THU_TUC


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    rejected_phones: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def phone(value: Any) -> str | None:
        number, rejected = _phone_vn(value)
        if rejected:
            rejected_phones.add(rejected)
        return number

    # Chỗ ở hợp pháp đề nghị xác nhận nằm ở Khánh Hòa (UBND phường/xã của cổng tiếp nhận) → thiếu tỉnh thì thử tỉnh cổng.
    home = _person_area(values.get("ChoO_DiaChi"), (PORTAL_PROVINCE,))

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_identity = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner = {
        "name": owner_name,
        "identity": owner_identity,
        "birthday": _date(values.get("ChuHoSo_NgaySinh")),
        "gender": _gender(values.get("ChuHoSo_GioiTinh"), owner_identity),
        "phone": phone(values.get("ChuHoSo_DienThoai")),
        "email": _text(values.get("ChuHoSo_Email")),
        "id_date": _date(values.get("ChuHoSo_NgayCapCccd")),
        "id_agency": _cccd_issuer(values.get("ChuHoSo_NoiCapCccd"), values.get("ChuHoSo_NgayCapCccd")),
        # Nơi cư trú hiện tại (thường ở tỉnh khác) — KHÔNG mượn địa chỉ chỗ ở đề nghị xác nhận.
        "residence": _person_area(values.get("ChuHoSo_ThuongTru"), (PORTAL_PROVINCE,)),
    }

    # Người nộp thay chỉ tính khi thật sự là NGƯỜI KHÁC (LLM có lúc chép lại chính chủ hồ sơ vào object).
    rep = values.get("NguoiNopThay")
    rep = rep if isinstance(rep, dict) else {}
    rep_name = _text(rep.get("hoTen"))
    rep_identity = _identity(rep.get("soDinhDanh"))
    same_as_owner = bool((rep_name and owner_name and _fold(rep_name) == _fold(owner_name))
                         or (rep_identity and owner_identity and rep_identity == owner_identity))
    has_rep = bool(rep_name or rep_identity) and not same_as_owner and not submitter_is_declarant(options, owner_name)

    # ---- Chủ hồ sơ ----
    add("data[ownerFullname]", owner["name"])
    add("data[ownerIdentityNumber]", owner["identity"])
    add("data[ownerBirthday]", owner["birthday"])
    add("data[ownerPhoneNumber]", owner["phone"])
    add("data[ownerAddress]", _full_address(owner["residence"]))
    add("data[isOwnerDossier]", not has_rep)

    # ---- Người nộp ----
    if has_rep:
        # Hai người khác nhau → không mượn SĐT/email/nơi ở của chủ hồ sơ cho người đi nộp thay.
        sub = {
            "name": rep_name,
            "identity": rep_identity,
            "birthday": _date(rep.get("ngaySinh")),
            "gender": _gender(rep.get("gioiTinh"), rep_identity),
            "phone": phone(rep.get("dienThoai")),
            "email": None,
            "id_date": _date(rep.get("ngayCapCccd")),
            "id_agency": _cccd_issuer(rep.get("noiCapCccd"), rep.get("ngayCapCccd")),
            "residence": _person_area(rep.get("thuongTru"), (PORTAL_PROVINCE,)),
        }
    else:
        sub = owner
    add("data[fullname]", sub["name"])
    add("data[birthday]", sub["birthday"])
    add("data[gender]", sub["gender"])
    add("data[email]", sub["email"])
    add("data[phoneNumber]", sub["phone"])
    add("data[identityNumber]", sub["identity"])
    add("data[identityDate]", sub["id_date"])
    add("data[identityAgency]", sub["id_agency"])
    add("data[noidungyeucaugiaiquyet]", request_text(values, home))
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    residence = sub["residence"]
    # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán → bỏ cả cụm.
    if residence and (_text(residence.get("xa")) or _text(residence.get("diaChi"))):
        add("data[nation]", residence.get("quocGia") or "Việt Nam", default=True)
        add("data[province]", _province(residence))
        ward = _ward(residence)
        add("data[district]", ward)
        add("data[address]", _text(residence.get("diaChi")))
        tinh = _text(residence.get("tinh"))
        if ward and tinh and not canonical_ward(tinh, ward):
            warnings.append(f"Phường/xã '{ward}' (người nộp) không có trong danh mục {_province(residence)} — cán bộ "
                            "chọn lại.")

    if not owner_name or not owner_identity:
        warnings.append("Thiếu họ tên/số định danh người đề nghị từ Tờ khai Mẫu 02 hoặc CCCD.")
    if not home:
        warnings.append("Chưa đọc được địa chỉ chỗ ở hợp pháp (Tờ khai mục II.1) — nội dung yêu cầu thiếu địa chỉ, cán "
                        "bộ kiểm tra lại.")
    warnings.extend(phone_warning(rejected_phones))

    # ---- Ô giấy tờ không có → trả về TRỐNG (cổng đổ sẵn theo tài khoản) ----
    keep_applicant = account_is_applicant(options, sub["identity"])
    missing = [label for name, label in _REQUIRED_LABELS.items()
               if name not in seen and not (keep_applicant and name in _BLANK_APPLICANT + ("data[province]",
                                                                                         "data[district]"))]
    if missing:
        warnings.append("Ô bắt buộc chưa có trong giấy tờ: " + "; ".join(missing) + " — đã để trống, cán bộ nhập tay.")
    for name in _BLANK_APPLICANT + _BLANK_OWNER:
        if name in seen or (keep_applicant and name in _BLANK_APPLICANT):
            continue
        item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True}
        if name in _REQUIRED_LABELS:
            item["markEmpty"] = True
        out.append(item)
        seen.add(name)
    return out, warnings
