"""Map dữ kiện nguồn → field UI bước 2 cho thủ tục 1.115668 (Lào Cai).

Chọn nguồn theo sheet "Ma trận đa nguồn" của file mapping:
  Người nộp : xem hai chế độ bên dưới. Tên cơ quan/MST → tổ chức chủ hồ sơ (người nộp đại diện tổ chức đó),
              phát được cả khi chưa biết ai đi nộp.
  Chủ hồ sơ : cá nhân → CCCD rồi hợp đồng/đơn; tổ chức → tên + MST.
              Địa chỉ → hợp đồng → Đơn → GCN ĐKDN → CCCD. Di động → Đơn → hợp đồng → GCN ĐKDN.
              Email → Đơn → GCN ĐKDN.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (cài đặt "Người nộp = chủ hồ sơ" của extension → `options.submitterMode`):
  · Mặc định — THEO TÀI KHOẢN: mốc là Họ tên + Số Căn cước cổng đổ sẵn từ tài khoản định danh
    (`options.formContext`). Chỉ bù ngày sinh/giới tính/dân tộc/ngày cấp/nơi cấp lấy từ giấy tờ CỦA
    CHÍNH người đó; không có mốc hoặc hồ sơ không có giấy tờ của người đó → BỎ TRỐNG + cảnh báo. Họ tên/
    Số căn cước/địa chỉ/Di động KHÔNG phát lại: cổng đã điền sẵn đúng người, mà sửa "Họ và tên" thì cổng
    xoá trắng Di động + CCCD.
  · `submitterMode="owner_as_submitter"` — THEO TỜ KHAI: bỏ mốc, lấy bên được ủy quyền → chủ hồ sơ (chủ
    hồ sơ là TỔ CHỨC thì chỉ nhận bên được ủy quyền). Ở chế độ này người nộp là NGƯỜI KHÁC với tài khoản
    nên PHẢI ghi đè cả Họ tên, Số căn cước, địa chỉ và Di động. Cổng gửi chính Họ tên/Số căn cước/Ngày
    sinh sang CSDL quốc gia dân cư để xác thực trước khi cho nộp → lệch tài khoản là bị chặn, mapper
    cảnh báo thay vì im lặng.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

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
        "NoiCuTru": proxy.get("thuongTru"),
    }


def _owner_person(values: dict) -> dict | None:
    """Chủ hồ sơ dạng ứng viên: khối này nằm rải ở ChuHoSo_* chứ không thành một object như CCCD."""
    block = {
        "HoTen": values.get("ChuHoSo_HoTen"),
        "SoDinhDanh": values.get("ChuHoSo_SoDinhDanh"),
        "NgaySinh": values.get("ChuHoSo_NgaySinh"),
        "GioiTinh": _gender(None, values.get("ChuHoSo_XungHo")),
        "NgayCap": values.get("ChuHoSo_NgayCap"),
        "NoiCap": values.get("ChuHoSo_NoiCap"),
        # SĐT mục 1.d) của Đơn và SĐT bên nhận trên hợp đồng đều là số của chính chủ hồ sơ.
        "DienThoai": values.get("Don_DienThoai") or values.get("HopDong_DienThoai"),
        "NoiCuTru": values.get("ChuHoSo_DiaChiHopDong") or values.get("ChuHoSo_DiaChiDon"),
    }
    return block if any(v not in (None, "", {}, []) for v in block.values()) else None


def _same_person_by_name(left: dict, right: dict) -> bool:
    """Hai bản ghi cùng họ tên nhưng KHÁC ngày sinh là hai người (cha/con trùng tên) — không gộp."""
    left_dob = _plain(_get(left, "NgaySinh", "ngaySinh"))
    right_dob = _plain(_get(right, "NgaySinh", "ngaySinh"))
    return not (left_dob and right_dob and left_dob != right_dob)


def _merge_candidates(*groups: list[dict]) -> list[dict]:
    """Gộp nhân thân của CÙNG một người từ nhiều giấy tờ; nguồn đứng trước được ưu tiên."""
    merged: list[dict] = []
    for group in groups:
        for person in group:
            if not person:
                continue
            key_id = _digits(_get(person, "SoDinhDanh", "soDinhDanh"))
            key_name = _fold(_get(person, "HoTen", "hoTen"))
            found = None
            for other in merged:
                other_id = _digits(_get(other, "SoDinhDanh"))
                other_name = _fold(_get(other, "HoTen"))
                if (key_id and other_id and key_id == other_id) or (
                    not key_id and not other_id and key_name and key_name == other_name
                    and _same_person_by_name(person, other)
                ):
                    found = other
                    break
            if found is None:
                merged.append(dict(person))
            else:
                for field, value in person.items():
                    if found.get(field) in (None, "", {}, []) and value not in (None, "", {}, []):
                        found[field] = value
    return merged


def _match_anchor(person: dict | None, anchor_id: str, anchor_name: str) -> bool:
    """Khớp theo SỐ ĐỊNH DANH trước; giấy tờ cũ hay in CMND 9 số nên mới cho khớp theo HỌ TÊN."""
    if not person:
        return False
    person_id = _digits(_get(person, "SoDinhDanh", "soDinhDanh"))
    person_name = _fold(_get(person, "HoTen", "hoTen"))
    if anchor_id and person_id:
        return person_id == anchor_id
    return bool(anchor_name and person_name and person_name == anchor_name)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    ctx = (options or {}).get("formContext") or {}
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

    # ----- Phần II: người nộp. -----
    anchor_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_name = _fold(ctx.get("applicantFullname") or ctx.get("fullname"))
    has_anchor = bool(anchor_id or anchor_name)
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"

    proxy = _proxy_person(values)
    owner_person = None if is_org else _owner_person(values)
    # Thứ tự nguồn: thẻ CCCD (đầy đủ nhất) → người ghi trong giấy tờ → giấy ủy quyền → chủ hồ sơ.
    candidates = _merge_candidates(
        cards, named, [proxy] if proxy else [], [owner_person] if owner_person else [],
    )

    if theo_to_khai:
        # Chủ hồ sơ là TỔ CHỨC thì tổ chức không thể tự đi nộp — chỉ nhận người được ủy quyền.
        base = proxy or owner_person
        nguoi_nop = next(iter(_merge_candidates([base], candidates)), None) if base else None
    else:
        # Hồ sơ nộp thay luôn có thẻ của chủ hồ sơ: lấy nhầm là điền ngày/nơi cấp của người khác.
        matched = [p for p in candidates if _match_anchor(p, anchor_id, anchor_name)]
        nguoi_nop = matched[0] if has_anchor and len(matched) == 1 else None
        if has_anchor and len(matched) > 1:
            warnings.append(
                "Hồ sơ có nhiều người trùng họ tên với tài khoản đăng nhập mà không đối chiếu được số căn "
                "cước, trợ lý bỏ trống nhân thân khối \"Thông tin người nộp\" để khỏi điền nhầm người — "
                "cán bộ nhập tay."
            )

    if is_org:
        # Người nộp đứng ra cho tổ chức chủ hồ sơ (mapping: ô Tên cơ quan/MSDN người nộp = bên mua).
        # Đây là dữ liệu của TỔ CHỨC nên phát được cả khi chưa xác định người đi nộp.
        add("CongDan_tenCoQuanToChuc", org_name.upper())
        add("CongDan_maSoThueNguoiNop", org_tax)

    if nguoi_nop:
        if theo_to_khai:
            # Người nộp theo tờ khai KHÁC người cổng đổ sẵn nên phải ghi đè cả khối. Ghi Họ tên TRƯỚC:
            # cổng xoá trắng Di động + Số căn cước khi ô này đổi, các ô sau sẽ điền đè lên.
            add("CongDan_tenCongDan", upper_person_name(_plain(_get(nguoi_nop, "HoTen"))))
            add("CongDan_soCmnd", _id_number(_get(nguoi_nop, "SoDinhDanh")))
        add("CongDan_ngaySinhCongDan", _full_date(_get(nguoi_nop, "NgaySinh")))
        add("CongDan_gioiTinhCongDan", _gender(nguoi_nop))
        add("CongDan_danTocCongDan", _plain(_get(nguoi_nop, "DanToc")))
        add("CongDan_ngayCapCmnd", _full_date(_get(nguoi_nop, "NgayCap")))
        add("CongDan_noiCapCmnd", _issuer(_get(nguoi_nop, "NoiCap")))
        if theo_to_khai:
            add("CongDan_diDong", _phone(_get(nguoi_nop, "DienThoai")))
            nop_area = _area(_get(nguoi_nop, "NoiCuTru"))
            if nop_area:
                # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh.
                add("CongDan_maTinhThanh", province_label(nop_area.get("tinh")))
                add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
                add("CongDan_diaChi", _plain(nop_area.get("diaChi")))
            if has_anchor and not _match_anchor(nguoi_nop, anchor_id, anchor_name):
                warnings.append(
                    "Khối \"Thông tin người nộp\" đang điền theo TỜ KHAI ("
                    + (_plain(_get(nguoi_nop, "HoTen")) or "người trong hồ sơ")
                    + ") nhưng tài khoản đang đăng nhập là "
                    + (_plain(ctx.get("applicantFullname")) or "người khác")
                    + ". Cổng xác thực Họ tên/Số Căn cước/Ngày sinh với CSDL quốc gia dân cư trước khi cho "
                    "nộp — lệch tài khoản sẽ bị chặn. Đăng nhập đúng tài khoản người đi nộp, hoặc tắt cài "
                    "đặt \"Người nộp = chủ hồ sơ\"."
                )
    elif theo_to_khai and is_org and not proxy:
        warnings.append(
            "Chủ hồ sơ là TỔ CHỨC nên không suy ra được người đi nộp từ tờ khai, mà hồ sơ cũng không có văn "
            "bản ủy quyền. Trợ lý giữ nguyên khối \"Thông tin người nộp\" cổng đã đổ sẵn từ tài khoản."
        )
    elif not theo_to_khai and not has_anchor:
        warnings.append(
            "Không xác định được NGƯỜI ĐANG ĐI NỘP: cổng chưa đổ sẵn Họ tên/Số Căn cước từ tài khoản định "
            "danh (hoặc trang chưa đăng nhập). Trợ lý bỏ trống Ngày sinh/Giới tính/Dân tộc/Ngày cấp/Nơi cấp "
            "của khối \"Thông tin người nộp\" để khỏi lấy nhân thân người khác trong hồ sơ."
        )
    elif not theo_to_khai and not warnings:
        warnings.append(
            "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
            + (f" ({_plain(ctx.get('applicantFullname'))})" if ctx.get("applicantFullname") else "")
            + " nên các ô Ngày sinh/Giới tính/Dân tộc/Ngày cấp/Nơi cấp của khối \"Thông tin người nộp\" để "
            "trống — cán bộ nhập tay, KHÔNG lấy thông tin của người khác trong hồ sơ."
        )

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
        residence = (
            _area(values.get("ChuHoSo_DiaChiHopDong"))
            or _area(values.get("ChuHoSo_DiaChiDon"))
            or _area(values.get("ChuHoSo_DiaChiDkdn"))
            or _area((owner_card or {}).get("NoiCuTru"))
        )
        if residence:
            # Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh (mặc định cổng là Lào Cai).
            add("ChuHoSo_maTinhThanhCHS", province_label(residence.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(residence.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(residence.get("diaChi")))
        add("ChuHoSo_diDongLienLacCHS",
            _phone(values.get("Don_DienThoai"))
            or _phone(values.get("HopDong_DienThoai"))
            or (_phone(values.get("Dkdn_DienThoai")) if is_org else None))
        add("ChuHoSo_emailChuHoSo",
            _email(values.get("Don_Email")) or (_email(values.get("Dkdn_Email")) if is_org else None))

    return out, warnings
