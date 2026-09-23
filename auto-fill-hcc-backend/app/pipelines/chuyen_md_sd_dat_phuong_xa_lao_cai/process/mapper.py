"""Map dữ kiện nguồn → field UI bước 2 cho thủ tục 1.115679 (Lào Cai — nộp tại phường/xã).

Chọn nguồn theo sheet "Ma trận đa nguồn" của "Mapping_CMDSDD_1.115679_LaoCai_CaNhan_ToChuc.xlsx"
(ưu tiên: CCCD → Đơn đề nghị → Giấy uỷ quyền → Giấy chứng nhận/giấy tờ chuyên ngành → các văn bản còn lại):
  Người nộp : xem hai chế độ bên dưới. Tên cơ quan/MSDN → tổ chức chủ hồ sơ (người nộp đứng ra đại diện
              cho tổ chức đó), phát được cả khi chưa biết ai đi nộp.
  Chủ hồ sơ : người sử dụng đất ở mục 1 của Đơn, 4 nhánh CN/DN/CQ/TC.
              Cá nhân → CCCD rồi Đơn rồi Giấy uỷ quyền; tổ chức → tên + MST theo giấy tờ pháp nhân.
              Địa chỉ → CCCD → Đơn → Giấy uỷ quyền → Giấy chứng nhận/hồ sơ đo đạc → vị trí thửa đất.
              Di động/Email → Đơn → Phiếu chuyển thông tin.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (cài đặt "Người nộp = chủ hồ sơ" của extension → `options.submitterMode`):
  · Mặc định — THEO TÀI KHOẢN: mốc là Họ tên + Số Căn cước cổng đổ sẵn từ tài khoản định danh
    (`options.formContext`). Ngày sinh/giới tính/dân tộc/ngày cấp/nơi cấp/ĐỊA CHỈ lấy từ giấy tờ của
    CHÍNH người đó: CCCD đã upload (khớp số định danh, không có số thì khớp họ tên) rồi đến người được ghi
    kèm số CCCD trong Đơn/Giấy uỷ quyền — hồ sơ nộp thay thì đó là BÊN ĐƯỢC UỶ QUYỀN. Không nhận ra người
    đăng nhập trong hồ sơ → bỏ trống hết + cảnh báo, KHÔNG gán bừa. Di động/Email chỉ chép lại số trên Đơn
    khi người đăng nhập CHÍNH LÀ chủ hồ sơ. Hai ô "Họ và tên"/"Số Căn cước" KHÔNG phát lại (cổng đã đổ sẵn
    đúng người đó rồi).
  · `submitterMode="owner_as_submitter"` — THEO TỜ KHAI: bỏ mốc, lấy BÊN ĐƯỢC UỶ QUYỀN, không có văn bản
    uỷ quyền thì lấy chủ hồ sơ (chủ hồ sơ là TỔ CHỨC thì chỉ nhận bên được uỷ quyền — tổ chức không tự đi
    nộp). Chế độ này PHẢI ghi đè cả "Họ và tên" + "Số Căn cước" vì người nộp khác người cổng đổ sẵn; để
    nguyên là khối thành nửa của tài khoản nửa của người trong hồ sơ. Lệch tài khoản thì cảnh báo.

⚠ Ô "Giới tính" của cổng không có option trống nên luôn hiển thị "Nữ": hồ sơ nam giới mà thiếu giới tính là
nộp sai mà form vẫn trông như đã chọn → cố gắng suy từ xưng hô Ông/Bà khi không có ảnh thẻ.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_FULL_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

# Option value thật của <select name="ChuHoSo_maDoiTuongNopHS"> trên cổng.
_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_DOANH_NGHIEP = "DN"
_DOI_TUONG_CO_QUAN = "CQ"
_DOI_TUONG_TO_CHUC_KHAC = "TC"

# LLM trả nhãn tiếng Việt (schema ChuHoSo_LoaiDoiTuong) → option value của cổng.
_DOI_TUONG_BY_LABEL = {
    "ca nhan": _DOI_TUONG_CA_NHAN,
    "doanh nghiep": _DOI_TUONG_DOANH_NGHIEP,
    "co quan nha nuoc": _DOI_TUONG_CO_QUAN,
    "to chuc khac": _DOI_TUONG_TO_CHUC_KHAC,
}

# LLM trả nhãn lạ (hay gặp: "Tổ chức" chung chung) → đoán lại theo CHÍNH tên tổ chức, vì chọn sai ô này là
# cổng hiện nhầm nhóm trường bắt buộc. Thứ tự kiểm quan trọng: tên vừa có "ban quan ly" vừa có "so " thì
# nhánh tổ chức chính trị - xã hội/tôn giáo phải xét TRƯỚC.
_TO_CHUC_KHAC_HINTS = (
    "mat tran to quoc", "mttq", "hoi nong dan", "hoi lien hiep", "hoi cuu chien binh", "doan thanh nien",
    "cong doan", "lien doan lao dong", "hoi phu nu", "to chuc chinh tri", "giao xu", "giao ho", "nha tho",
    "giao phan", "chua ", "thien vien", "tinh that", "cong dong dan cu", "dong ho",
)
_CO_QUAN_HINTS = (
    "uy ban nhan dan", "ubnd", "so ", "chi cuc", "cuc ", "ban quan ly", "trung tam", "van phong dang ky",
    "phong giao duc", "truong tieu hoc", "truong trung hoc", "truong mam non", "benh vien", "tram y te",
    "bo chi huy", "cong an", "vien kiem sat", "toa an", "kho bac", "tinh uy", "huyen uy", "dang uy",
    "hat kiem lam", "don vi su nghiep",
)
_DOANH_NGHIEP_HINTS = (
    "cong ty", "doanh nghiep", "tap doan", "tong cong ty", "ngan hang", "hop tac xa", "chi nhanh",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.split()).strip(" :;,-") or None


def _full_date(value) -> str | None:
    """Chỉ nhận ngày đủ dd/mm/yyyy. "Sinh: 1985" không đủ cho ô DD/MM/YYYY → bỏ, không bịa."""
    match = _FULL_DATE_RE.match(_plain(value) or "")
    if not match:
        return None
    return f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{match.group(3)}"


def _id_number(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _tax_code(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (10, 13) else None


def _phone(value) -> str | None:
    text = str(value or "").strip()
    digits = _digits(text)
    if text.startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _email(value) -> str | None:
    text = (_plain(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text) else None


def _issuer(value) -> str | None:
    return normalize_issuer(value) or _plain(value)


def _gender(person: dict | None, xung_ho=None) -> str | None:
    text = _fold((person or {}).get("GioiTinh"))
    if text in ("nam", "male"):
        return "Nam"
    if text in ("nu", "female"):
        return "Nữ"
    salutation = _fold(xung_ho)
    if salutation == "ong":
        return "Nam"
    if salutation == "ba":
        return "Nữ"
    return None


def org_option(loai_doi_tuong, org_name) -> str:
    """Option "Đối tượng nộp hồ sơ" cho chủ hồ sơ là TỔ CHỨC.

    Ưu tiên nhãn LLM đọc được; nhãn lạ (trả trống hoặc "Tổ chức" chung chung) thì đoán theo tên tổ chức.
    Không đoán ra được thì "Tổ chức khác" — lựa chọn rộng nhất, không ô nào bị ép bắt buộc thêm.
    """
    mapped = _DOI_TUONG_BY_LABEL.get(_fold(loai_doi_tuong))
    if mapped and mapped != _DOI_TUONG_CA_NHAN:
        return mapped
    name = _fold(org_name)
    if any(hint in name for hint in _TO_CHUC_KHAC_HINTS):
        return _DOI_TUONG_TO_CHUC_KHAC
    if any(hint in name for hint in _CO_QUAN_HINTS):
        return _DOI_TUONG_CO_QUAN
    if any(hint in name for hint in _DOANH_NGHIEP_HINTS):
        return _DOI_TUONG_DOANH_NGHIEP
    return _DOI_TUONG_TO_CHUC_KHAC


def _area(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or "",
        "diaChi": value.get("diaChi") or "",
    }
    # Thiếu tỉnh hoặc xã thì không chọn được cặp select → bỏ nguồn này, thử nguồn sau.
    if not (area["tinh"] and area["xa"]):
        return None
    hint = value.get("huyen") or value.get("quanHuyen") or ""
    return remap_area(area, huyen_hint=hint) or area


def _people(values: dict, name: str) -> list[dict]:
    items = values.get(name)
    return [p for p in items if isinstance(p, dict)] if isinstance(items, list) else []


def _match_by_id(people: list[dict], wanted) -> dict | None:
    wanted = _digits(wanted)
    if not wanted:
        return None
    matches = [p for p in people if _digits(p.get("SoDinhDanh")) == wanted]
    return matches[0] if len(matches) == 1 else None


def _match_by_name(people: list[dict], name) -> dict | None:
    wanted = _fold(name)
    if not wanted:
        return None
    matches = [p for p in people if _fold(p.get("HoTen")) == wanted]
    # Nhiều người trùng tên → không đoán.
    return matches[0] if len(matches) == 1 else None


def _find_person(people: list[dict], id_number, name) -> dict | None:
    return _match_by_id(people, id_number) if _digits(id_number) else _match_by_name(people, name)


def _get(person: dict | None, *keys):
    """Ứng viên đến từ nhiều nguồn nên tên khoá khác nhau (HoTen ↔ hoTen)."""
    for key in keys:
        value = (person or {}).get(key)
        if value not in (None, "", {}, []):
            return value
    return None


def _proxy_person(values: dict) -> dict | None:
    proxy = values.get("NguoiDuocUyQuyen")
    if not isinstance(proxy, dict) or not any(proxy.values()):
        return None
    return {
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


def _owner_person(values: dict, owner_card: dict | None, owner_named: dict | None) -> dict | None:
    """Chủ hồ sơ dạng ứng viên — khối này nằm rải ở ChuHoSo_* chứ không thành một object như CCCD.

    Chỉ dùng cho chế độ THEO TỜ KHAI khi hồ sơ không có văn bản uỷ quyền: người nộp chính là chủ hồ sơ,
    nên Di động/Email ở mục 3 của Đơn cũng là số của người đó.
    """
    block = {
        "HoTen": values.get("ChuHoSo_HoTen"),
        "SoDinhDanh": values.get("ChuHoSo_SoDinhDanh"),
        "NgaySinh": values.get("ChuHoSo_NgaySinh"),
        "GioiTinh": _gender(owner_card) or _gender(owner_named, values.get("ChuHoSo_XungHo")),
        "DanToc": (owner_card or {}).get("DanToc"),
        "NgayCap": values.get("ChuHoSo_NgayCap"),
        "NoiCap": values.get("ChuHoSo_NoiCap"),
        "DienThoai": values.get("Don_DienThoai"),
        "Email": values.get("Don_Email"),
        "NoiCuTru": values.get("ChuHoSo_DiaChiDon") or values.get("ChuHoSo_DiaChiUyQuyen"),
    }
    return block if any(v not in (None, "", {}, []) for v in block.values()) else None


def _same_person_by_name(left: dict, right: dict) -> bool:
    """Hai bản ghi cùng họ tên nhưng KHÁC ngày sinh là hai người (cha/con trùng tên) — không gộp."""
    left_dob = _plain(_get(left, "NgaySinh", "ngaySinh"))
    right_dob = _plain(_get(right, "NgaySinh", "ngaySinh"))
    return not (left_dob and right_dob and left_dob != right_dob)


def _merge_person(base: dict | None, *groups: list[dict]) -> dict | None:
    """Bù các mục còn thiếu của `base` bằng giấy tờ khác CỦA CHÍNH người đó.

    Khối phẳng/giấy uỷ quyền thường chỉ có tên + số định danh + ngày cấp; dân tộc và nơi thường trú
    nằm ở ảnh thẻ căn cước. Chỉ gộp khi chắc chắn cùng người: khớp SỐ ĐỊNH DANH, hoặc (khi một trong
    hai phía không đọc được số) khớp HỌ TÊN mà ngày sinh không mâu thuẫn.
    """
    if not base:
        return None
    merged = dict(base)
    base_id = _digits(_get(merged, "SoDinhDanh"))
    base_name = _fold(_get(merged, "HoTen"))
    for group in groups:
        for person in group:
            person_id = _digits(_get(person, "SoDinhDanh"))
            person_name = _fold(_get(person, "HoTen"))
            same = (
                (base_id and person_id and base_id == person_id)
                or (not (base_id and person_id) and base_name and base_name == person_name
                    and _same_person_by_name(merged, person))
            )
            if not same:
                continue
            for field, value in person.items():
                if merged.get(field) in (None, "", {}, []) and value not in (None, "", {}, []):
                    merged[field] = value
    return merged


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    ctx = (options or {}).get("formContext") or {}
    # Cài đặt "Người nộp = chủ hồ sơ" của extension: bỏ mốc tài khoản, lấy người nộp theo tờ khai.
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
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

    cards = _people(values, "DanhSachCccd")
    named = _people(values, "NguoiTrongGiayTo")

    # ----- Chủ hồ sơ: xác định loại TRƯỚC (người nộp cần biết có đại diện tổ chức không). -----
    org_name = _plain(values.get("ChuHoSo_TenToChuc"))
    org_tax = _tax_code(values.get("ChuHoSo_MaSoThue"))
    is_ca_nhan_label = _fold(values.get("ChuHoSo_LoaiDoiTuong")) == "ca nhan"
    is_org = bool(org_name) and not is_ca_nhan_label

    owner_id = _id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = None if is_org else _find_person(cards, owner_id, values.get("ChuHoSo_HoTen"))
    owner_named = None if is_org else _find_person(named, owner_id, values.get("ChuHoSo_HoTen"))
    person_name = _plain((owner_card or {}).get("HoTen")) or _plain(values.get("ChuHoSo_HoTen"))
    person_id = _id_number((owner_card or {}).get("SoDinhDanh")) or owner_id
    is_person = not is_org and bool(person_name and person_id)

    # ----- Phần I: người nộp. -----
    applicant_id = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    applicant_name = ctx.get("applicantFullname")
    applicant_card = _find_person(cards, applicant_id, applicant_name)
    applicant_named = _find_person(named, applicant_id, applicant_name)
    if is_org:
        # Người nộp đứng ra cho tổ chức chủ hồ sơ (mapping: ô Tên cơ quan/MSDN của khối người nộp).
        # Đây là dữ liệu của TỔ CHỨC nên phát được cả khi chưa xác định được người đi nộp.
        add("CongDan_tenCoQuanToChuc", org_name)
        add("CongDan_maSoThueNguoiNop", org_tax)

    if theo_to_khai:
        # Bên được uỷ quyền đi nộp thay; không có văn bản uỷ quyền thì người nộp chính là chủ hồ sơ.
        base = _proxy_person(values) or (
            None if is_org else _owner_person(values, owner_card, owner_named)
        )
        nguoi_nop = _merge_person(base, cards, named)
        if nguoi_nop:
            # Người nộp theo tờ khai KHÁC người cổng đổ sẵn nên phải ghi đè cả khối. Họ tên + Số Căn
            # cước đi TRƯỚC để phần nhân thân bên dưới thuộc về đúng người ở hai ô đầu.
            add("CongDan_tenCongDan", upper_person_name(_plain(_get(nguoi_nop, "HoTen"))))
            add("CongDan_soCmnd", _id_number(_get(nguoi_nop, "SoDinhDanh")))
            add("CongDan_ngaySinhCongDan", _full_date(_get(nguoi_nop, "NgaySinh")))
            add("CongDan_gioiTinhCongDan", _gender(nguoi_nop))
            add("CongDan_danTocCongDan", _plain(_get(nguoi_nop, "DanToc")))
            add("CongDan_ngayCapCmnd", _full_date(_get(nguoi_nop, "NgayCap")))
            add("CongDan_noiCapCmnd", _issuer(_get(nguoi_nop, "NoiCap")))
            nop_area = _area(_get(nguoi_nop, "NoiCuTru"))
            if nop_area:
                # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp AJAX sau khi chọn tỉnh.
                add("CongDan_maTinhThanh", province_label(nop_area.get("tinh")))
                add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
                add("CongDan_diaChi", _plain(nop_area.get("diaChi")))
            add("CongDan_diDong", _phone(_get(nguoi_nop, "DienThoai")))
            add("CongDan_email", _email(_get(nguoi_nop, "Email")))
            if applicant_id or applicant_name:
                nop_id = _digits(_get(nguoi_nop, "SoDinhDanh"))
                nop_name = _fold(_get(nguoi_nop, "HoTen"))
                lech = (
                    (_digits(applicant_id) and nop_id and _digits(applicant_id) != nop_id)
                    or (not (_digits(applicant_id) and nop_id)
                        and _fold(applicant_name) and nop_name and _fold(applicant_name) != nop_name)
                )
                if lech:
                    warnings.append(
                        "Khối \"Thông tin người nộp hồ sơ\" đang điền theo TỜ KHAI ("
                        + (_plain(_get(nguoi_nop, "HoTen")) or "người trong hồ sơ")
                        + ") nhưng tài khoản đang đăng nhập là "
                        + (_plain(applicant_name) or "người khác")
                        + ". Cổng đối chiếu Họ tên/Số Căn cước với tài khoản trước khi cho nộp — lệch "
                        "là bị chặn. Đăng nhập đúng tài khoản người đi nộp, hoặc tắt cài đặt \"Người "
                        "nộp = chủ hồ sơ\"."
                    )
        else:
            warnings.append(
                "Bật cài đặt \"Người nộp = chủ hồ sơ\" nhưng hồ sơ không có văn bản uỷ quyền và cũng "
                "không đọc được người sử dụng đất ở mục 1 của Đơn, nên trợ lý để trống khối \"Thông tin "
                "người nộp hồ sơ\" — cán bộ nhập tay."
            )
    else:
        if applicant_card:
            add("CongDan_ngaySinhCongDan", _full_date(applicant_card.get("NgaySinh")))
            add("CongDan_gioiTinhCongDan", _gender(applicant_card))
            add("CongDan_danTocCongDan", _plain(applicant_card.get("DanToc")))
        # Hồ sơ mẫu của thủ tục này KHÔNG có bản scan CCCD; Đơn và Giấy uỷ quyền vẫn ghi đủ số + ngày cấp
        # + nơi cấp + nơi thường trú của cả hai bên uỷ quyền.
        add("CongDan_ngaySinhCongDan", _full_date((applicant_named or {}).get("NgaySinh")))
        # Ô Giới tính không có option trống (cổng luôn hiện "Nữ") → suy từ xưng hô nếu chỉ có giấy tờ chữ.
        add("CongDan_gioiTinhCongDan", _gender(applicant_named))
        add("CongDan_ngayCapCmnd",
            _full_date((applicant_card or {}).get("NgayCap"))
            or _full_date((applicant_named or {}).get("NgayCap")))
        add("CongDan_noiCapCmnd",
            _issuer((applicant_card or {}).get("NoiCap")) or _issuer((applicant_named or {}).get("NoiCap")))
        # Tỉnh/Phường-Xã/Số nhà của khối người nộp đều là (*). Cổng đổ sẵn theo tài khoản nhưng vẫn phát lại
        # theo giấy tờ của CHÍNH người đăng nhập để ba ô là một địa chỉ nhất quán — chắp nửa tài khoản nửa
        # giấy tờ là ra địa chỉ không có thật. Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp AJAX sau khi chọn
        # tỉnh, và cổng đang nạp sẵn danh sách xã của tỉnh theo tài khoản.
        applicant_area = (
            _area((applicant_card or {}).get("NoiCuTru"))
            or _area((applicant_named or {}).get("NoiCuTru"))
        )
        if applicant_area:
            add("CongDan_maTinhThanh", province_label(applicant_area.get("tinh")))
            add("CongDan_maPhuongXa", _plain(applicant_area.get("xa")))
            add("CongDan_diaChi", _plain(applicant_area.get("diaChi")))
        # Di động/Email trên Đơn là của NGƯỜI SỬ DỤNG ĐẤT → chỉ dùng lại cho khối người nộp khi người đăng
        # nhập chính là chủ hồ sơ. Nộp thay mà chép số của chủ hồ sơ sang là cổng gửi thông báo về sai người.
        self_submit = bool(person_id and applicant_id and _digits(person_id) == _digits(applicant_id))
        if self_submit:
            add("CongDan_diDong", _phone(values.get("Don_DienThoai")))
            add("CongDan_email", _email(values.get("Don_Email")))
        if not (applicant_card or applicant_named):
            warnings.append(
                "Không nhận ra người đang đăng nhập"
                + (f" ({_plain(applicant_name)})" if applicant_name else "")
                + " trong giấy tờ của hồ sơ nên trợ lý để trống nhân thân khối \"Thông tin người nộp hồ "
                "sơ\" — sáu ô có dấu (*) ở khối này cán bộ nhập tay, KHÔNG lấy thông tin của người khác."
            )

    # ----- Phần II: chủ hồ sơ. -----
    if is_org:
        # Đối tượng là driver: phát TRƯỚC để cổng hiện nhóm ô tổ chức (tên cơ quan + MST).
        add("ChuHoSo_maDoiTuongNopHS", org_option(values.get("ChuHoSo_LoaiDoiTuong"), org_name))
        add("ChuHoSo_tenCoQuanToChucCHS", org_name)
        add("ChuHoSo_maSoThueChuHoSo", org_tax)
    elif is_person:
        add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_CA_NHAN)
        add("ChuHoSo_tenChuHoSo", upper_person_name(person_name))
        add("ChuHoSo_ngaySinhChuHoSo",
            _full_date((owner_card or {}).get("NgaySinh"))
            or _full_date(values.get("ChuHoSo_NgaySinh"))
            or _full_date((owner_named or {}).get("NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo",
            _gender(owner_card) or _gender(owner_named, values.get("ChuHoSo_XungHo")))
        add("ChuHoSo_danTocChuHoSo", _plain((owner_card or {}).get("DanToc")))
        add("ChuHoSo_soCMNDChuHoSo", person_id)
        add("ChuHoSo_noiCapCMNDCHS",
            _issuer((owner_card or {}).get("NoiCap"))
            or _issuer(values.get("ChuHoSo_NoiCap"))
            or _issuer((owner_named or {}).get("NoiCap")))
        add("ChuHoSo_ngayCapCMNDCHS",
            _full_date((owner_card or {}).get("NgayCap"))
            or _full_date(values.get("ChuHoSo_NgayCap"))
            or _full_date((owner_named or {}).get("NgayCap")))

    if is_org or is_person:
        # CCCD đứng đầu theo ma trận đa nguồn (địa chỉ lệch nhau ở cả hai hồ sơ mẫu: Đơn ghi "Tổ 39", Giấy uỷ
        # quyền ghi "Tổ dân phố số 9 Xuân Tăng", GCN 2018 còn địa danh cũ "Tổ 24, phường Bình Minh").
        residence = (
            _area((owner_card or {}).get("NoiCuTru"))
            or _area(values.get("ChuHoSo_DiaChiDon"))
            or _area(values.get("ChuHoSo_DiaChiUyQuyen"))
            or _area((owner_named or {}).get("NoiCuTru"))
            or _area(values.get("ChuHoSo_DiaChiGcn"))
            or _area(values.get("ThuaDat_DiaChi"))
        )
        if residence:
            add("ChuHoSo_maTinhThanhCHS", province_label(residence.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(residence.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(residence.get("diaChi")))
        add("ChuHoSo_diDongLienLacCHS",
            _phone(values.get("Don_DienThoai")) or _phone(values.get("PhieuChuyen_DienThoai")))
        add("ChuHoSo_emailChuHoSo", _email(values.get("Don_Email")))

    return out, warnings
