"""Map dữ kiện nguồn → field UI bước 2 cho thủ tục 1.115651 (Lào Cai).

Chọn nguồn theo sheet "Ma trận đa nguồn" của file mapping:
  Người nộp : họ tên/số căn cước/địa chỉ do TK định danh điền sẵn → chế độ tài khoản KHÔNG phát.
              Ngày sinh, giới tính, dân tộc, ngày/nơi cấp → CCCD CỦA CHÍNH người nộp (khớp số, không có số thì
              khớp họ tên tài khoản); ngày/nơi cấp còn bù từ đơn/giấy ủy quyền ghi đúng số CCCD đó.
              Tên cơ quan/MST → tổ chức chủ hồ sơ (người nộp đại diện tổ chức đó).
              Di động/Email/Fax → KHÔNG phát: số liên hệ trên Đơn/GCN ĐKDN là của chủ hồ sơ.
  Chủ hồ sơ : người sử dụng đất đứng tên Đơn. Cá nhân → CCCD rồi Đơn; tổ chức → tên + MST (GCN ĐKDN > Đơn > bản đồ).
              Địa chỉ: tổ chức → GCN ĐKDN → Đơn → vị trí khu đất; cá nhân → CCCD → Đơn → vị trí khu đất
              (mapping dùng vị trí khu đất trên bản đồ khi hồ sơ không có giấy tờ nào ghi trụ sở).
              Di động/Email → Đơn → GCN ĐKDN.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (cài đặt "Người nộp = chủ hồ sơ" của extension → `options.submitterMode`):
  · Mặc định — THEO TÀI KHOẢN: như trên, mốc là `options.formContext`.
  · `submitterMode="owner_as_submitter"` — THEO TỜ KHAI: bỏ mốc, người nộp là chủ hồ sơ CÁ NHÂN, nhân thân
    bù từ CCCD/giấy tờ khác của CHÍNH người đó (`_merge_person`). Schema không có vai bên được uỷ quyền /
    người đại diện của tổ chức (NguoiTrongGiayTo không ghi vai) → hồ sơ TỔ CHỨC thì để trống nhân thân +
    cảnh báo, không đoán ai trong danh sách. Hai ô Họ tên/Số căn cước ghi theo người đó, đứng TRƯỚC các ô
    khác của khối (sửa họ tên làm script cổng xoá Di động/Số Căn cước), ô nhân thân tài khoản mà hồ sơ không
    có thì XOÁ (`_shared/lao_cai_nguoi_nop.chot_khoi_nguoi_nop`); người theo tờ khai lệch tài khoản thì
    cảnh báo: cổng đối chiếu Họ tên/Số Căn cước/Ngày sinh với tài khoản trước khi cho nộp.

`enrich` trả list field như cũ (runner chưa đọc cảnh báo); `enrich_with_warnings` trả thêm cảnh báo.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines._shared.lao_cai_nguoi_nop import chot_khoi_nguoi_nop
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_FULL_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


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
    """Chỉ nhận ngày đủ dd/mm/yyyy. "Sinh năm 1970" không đủ cho ô DD/MM/YYYY → bỏ, không bịa."""
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
    for key in keys:
        value = (person or {}).get(key)
        if value not in (None, "", {}, []):
            return value
    return None


def _owner_person(values: dict) -> dict | None:
    """Chủ hồ sơ cá nhân dạng ứng viên — khối này nằm rải ở ChuHoSo_* chứ không thành một object như CCCD."""
    block = {
        "HoTen": values.get("ChuHoSo_HoTen"),
        "SoDinhDanh": values.get("ChuHoSo_SoDinhDanh"),
        "NgaySinh": values.get("ChuHoSo_NgaySinh"),
        "NgayCap": values.get("ChuHoSo_NgayCap"),
        "NoiCap": values.get("ChuHoSo_NoiCap"),
    }
    return block if (block["HoTen"] or block["SoDinhDanh"]) else None


def _same_person_by_name(left: dict, right: dict) -> bool:
    """Hai bản ghi cùng họ tên nhưng KHÁC ngày sinh là hai người (cha/con trùng tên) — không gộp.

    Đơn hay chỉ ghi "Sinh năm 1970" trong khi CCCD ghi đủ ngày → phía nào chỉ có năm thì so theo năm.
    """
    left_dob = _plain(_get(left, "NgaySinh")) or ""
    right_dob = _plain(_get(right, "NgaySinh")) or ""
    if _full_date(left_dob) and _full_date(right_dob):
        return _full_date(left_dob) == _full_date(right_dob)
    left_year = re.search(r"\d{4}", left_dob)
    right_year = re.search(r"\d{4}", right_dob)
    return not (left_year and right_year and left_year.group() != right_year.group())


def _merge_person(base: dict | None, *groups: list[dict]) -> dict | None:
    """Bù các mục còn thiếu của `base` bằng giấy tờ khác CỦA CHÍNH người đó.

    Chỉ gộp khi chắc chắn cùng người: khớp SỐ ĐỊNH DANH, hoặc (khi một trong hai phía không đọc được số)
    khớp HỌ TÊN mà ngày sinh không mâu thuẫn.
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
                if value in (None, "", {}, []):
                    continue
                current = merged.get(field)
                # Ngày chỉ có năm (Đơn) không điền được ô dd/mm/yyyy → nhường ngày đủ của giấy khác cùng người.
                partial_date = (field in ("NgaySinh", "NgayCap") and current not in (None, "")
                                and not _full_date(current) and _full_date(value))
                if current in (None, "", {}, []) or partial_date:
                    merged[field] = value
    return merged


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    return enrich_with_warnings(fields, options)[0]


def enrich_with_warnings(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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

    # ----- Chủ hồ sơ: xác định loại trước (người nộp cần biết có đại diện tổ chức không). -----
    org_name = _plain(values.get("ChuHoSo_TenToChuc"))
    org_tax = _tax_code(values.get("ChuHoSo_MaSoThue"))
    is_org = _fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(org_name)

    owner_id = _id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = None if is_org else _find_person(cards, owner_id, values.get("ChuHoSo_HoTen"))
    owner_named = None if is_org else _find_person(named, owner_id, values.get("ChuHoSo_HoTen"))
    person_name = _plain((owner_card or {}).get("HoTen")) or _plain(values.get("ChuHoSo_HoTen"))
    person_id = _id_number((owner_card or {}).get("SoDinhDanh")) or owner_id
    is_person = not is_org and bool(person_name and person_id)

    # ----- Phần II: người nộp (tài khoản đăng nhập). -----
    applicant_id = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    applicant_name = ctx.get("applicantFullname")
    applicant_card = _find_person(cards, applicant_id, applicant_name)
    applicant_named = _match_by_id(named, applicant_id)
    if is_org:
        # Người nộp đứng ra cho tổ chức chủ hồ sơ (mapping: ô Tên cơ quan/MSDN người nộp = bên mua).
        add("CongDan_tenCoQuanToChuc", org_name.upper())
        add("CongDan_maSoThueNguoiNop", org_tax)
    if theo_to_khai:
        nguoi_nop = None if is_org else _merge_person(_owner_person(values), cards, named)
        if nguoi_nop:
            ten_nop = upper_person_name(_plain(_get(nguoi_nop, "HoTen")))
            if ten_nop:
                # Chỉ ghi Số Căn cước khi đã có họ tên: đổi riêng số mà giữ họ tên tài khoản là khối người nộp
                # thành nửa người này nửa người kia.
                add("CongDan_tenCongDan", ten_nop)
                add("CongDan_soCmnd", _id_number(_get(nguoi_nop, "SoDinhDanh")))
            add("CongDan_ngaySinhCongDan", _full_date(_get(nguoi_nop, "NgaySinh")))
            # Người nộp chính là chủ hồ sơ → xưng hô trên Đơn cũng là của người đó.
            add("CongDan_gioiTinhCongDan",
                _gender(nguoi_nop) or _gender(None, values.get("ChuHoSo_XungHo")))
            add("CongDan_danTocCongDan", _plain(_get(nguoi_nop, "DanToc")))
            add("CongDan_ngayCapCmnd", _full_date(_get(nguoi_nop, "NgayCap")))
            add("CongDan_noiCapCmnd", _issuer(_get(nguoi_nop, "NoiCap")))
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
                    + (_plain(_get(nguoi_nop, "HoTen")) or "chủ hồ sơ")
                    + ") nhưng tài khoản đang đăng nhập là "
                    + (_plain(applicant_name) or "người khác")
                    + ". Cổng đối chiếu Họ tên/Số Căn cước/Ngày sinh với tài khoản trước khi cho nộp — lệch "
                    "là bị chặn. Đăng nhập đúng tài khoản người đi nộp, hoặc tắt cài đặt \"Người nộp = chủ "
                    "hồ sơ\"."
                )
        else:
            warnings.append(
                "Bật cài đặt \"Người nộp = chủ hồ sơ\" nhưng "
                + ("chủ hồ sơ là tổ chức (trợ lý không xác định được người đại diện/bên được uỷ quyền đi nộp)"
                   if is_org else "không đọc được họ tên/số định danh của chủ hồ sơ")
                + ", nên trợ lý để trống nhân thân khối \"Thông tin người nộp hồ sơ\" — cán bộ nhập tay."
            )
    else:
        if applicant_card:
            add("CongDan_ngaySinhCongDan", _full_date(applicant_card.get("NgaySinh")))
            add("CongDan_gioiTinhCongDan", _gender(applicant_card))
            add("CongDan_danTocCongDan", _plain(applicant_card.get("DanToc")))
        add("CongDan_ngayCapCmnd",
            _full_date((applicant_card or {}).get("NgayCap")) or _full_date((applicant_named or {}).get("NgayCap")))
        add("CongDan_noiCapCmnd",
            _issuer((applicant_card or {}).get("NoiCap")) or _issuer((applicant_named or {}).get("NoiCap")))

    # ----- Phần III: chủ hồ sơ. -----
    if is_org:
        # Đối tượng là driver: phát TRƯỚC để cổng hiện nhóm ô tổ chức. MST là ô bắt buộc cùng tên tổ chức.
        add("ChuHoSo_maDoiTuongNopHS", "DN")
        add("ChuHoSo_tenCoQuanToChucCHS", org_name.upper())
        add("ChuHoSo_maSoThueChuHoSo", org_tax)
    elif is_person:
        add("ChuHoSo_maDoiTuongNopHS", "CN")
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
        if is_org:
            residence = _area(values.get("ChuHoSo_DiaChiDkdn")) or _area(values.get("ChuHoSo_DiaChiDon"))
        else:
            residence = _area((owner_card or {}).get("NoiCuTru")) or _area(values.get("ChuHoSo_DiaChiDon"))
        residence = residence or _area(values.get("ThuaDat_DiaChi"))
        if residence:
            # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh (mặc định cổng là Lào Cai).
            add("ChuHoSo_maTinhThanhCHS", province_label(residence.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(residence.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(residence.get("diaChi")))
        add("ChuHoSo_diDongLienLacCHS",
            _phone(values.get("Don_DienThoai"))
            or (_phone(values.get("Dkdn_DienThoai")) if is_org else None))
        add("ChuHoSo_emailChuHoSo",
            _email(values.get("Don_Email")) or (_email(values.get("Dkdn_Email")) if is_org else None))

    out = chot_khoi_nguoi_nop(
        out, theo_to_khai=theo_to_khai, comp_by_name=UI_COMP_BY_NAME, warnings=warnings
    )
    return out, warnings
