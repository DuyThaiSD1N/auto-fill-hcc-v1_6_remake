"""Ánh xạ facts → ô eForm của thủ tục [Lào Cai] ĐIỀU CHỈNH quyết định giao đất/cho thuê đất (1.115652).

⚑ ĐIỂM KHÁC BIỆT QUAN TRỌNG so với các cổng Form.io: checkbox "Người nộp là chủ hồ sơ"
(`chkbox_nguoinoplachuhs`) của cổng CHỈ sao chép sang khối chủ hồ sơ tới Nơi cấp / Ngày cấp căn cước —
KHÔNG sao chép tỉnh/xã/địa chỉ. Vì vậy mapper LUÔN phát ĐẦY ĐỦ khối chủ hồ sơ (gồm cả 3 ô địa chỉ), kể
cả khi người nộp trùng chủ hồ sơ, thay vì trông vào checkbox đó. Cũng không phát chính checkbox: để cán
bộ tự quyết, tránh cổng tự xoá dữ liệu đã điền khi trạng thái checkbox đổi.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (cài đặt "Người nộp = chủ hồ sơ" của extension → `options.submitterMode`):
  · Mặc định — THEO TÀI KHOẢN: mốc là Họ tên + Số Căn cước cổng đổ sẵn từ tài khoản định danh, gửi lên
    trong `options.formContext`. Chỉ điền nhân thân người nộp lấy từ giấy tờ CỦA CHÍNH người đó; không
    có mốc, hoặc hồ sơ không có giấy tờ của người đó → BỎ TRỐNG cả khối + cảnh báo.
  · `submitterMode="owner_as_submitter"` — THEO TỜ KHAI: bỏ mốc, lấy bên được ủy quyền → người ký đơn
    → chủ hồ sơ.
Hai ô `CongDan_tenCongDan` / `CongDan_soCmnd` readonly (cổng đổ từ tài khoản) nhưng VẪN ĐƯỢC PHÁT để
cả khối là MỘT người — bỏ trống chúng thì khối thành nửa của tài khoản nửa của người trong hồ sơ. Chế
độ theo tài khoản ghi lại đúng chuỗi mốc; chế độ theo tờ khai ghi theo người trong hồ sơ và CẢNH BÁO
khi lệch tài khoản, vì cổng gửi chính hai ô đó (kèm ngày sinh) sang CSDL quốc gia dân cư để xác thực
trước khi cho nộp — lệch là chặn nộp ("Thông tin người nộp hồ sơ không đúng với tài khoản đăng nhập!").

⚑ Trang "Thành phần hồ sơ" có thêm 2 textarea `HoSoOnline_veViec` (BẮT BUỘC) và `HoSoOnline_ghiChu`.
Bản CẤP XÃ này KHÔNG đụng vào cả hai: cơ quan tiếp nhận yêu cầu giữ nguyên chuỗi cổng điền sẵn theo
tên thủ tục (ngược với bản ở Sở 1.115652 — xem cuối hàm `enrich`).
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dieu_chinh_giao_dat_cap_xa_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

# Phát OPTION VALUE chứ không phát nhãn: nhãn tổ chức của cổng là "Doanh nghiệp/ Tổ chức", mà danh
# sách còn có "Tổ chức khác" → khớp lỏng theo chữ "Tổ chức" có thể trúng nhầm option.
# `fillStandardSelect` (content.js) thử `option.value === raw` TRƯỚC nên "CN"/"DN" là khớp chắc chắn.
# Chủ hồ sơ là CƠ QUAN NHÀ NƯỚC (CQ) / TỔ CHỨC KHÁC (TC) thì cán bộ tự chọn lại: schema chỉ có cờ nhị
# phân `ChuHoSo_LaToChuc`, không đủ căn cứ tách bốn nhóm mà không đoán.
_DOI_TUONG_TO_CHUC = "DN"
_DOI_TUONG_CA_NHAN = "CN"


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
    """Trích yếu ô "Về việc". Ưu tiên câu LLM đọc từ Đơn; không có thì ghép tất định từ số/ngày QĐ gốc.

    Cổng tự điền sẵn TÊN THỦ TỤC vào ô này — cán bộ tiếp nhận cần trích yếu THẬT của hồ sơ nên phải
    ghi đè. Thiếu số/ngày quyết định thì ghép phần đọc được, KHÔNG bịa số.
    """
    san_co = _plain(values.get("Don_TrichYeu"))
    if san_co:
        return san_co
    so = _plain(values.get("QuyetDinhGoc_So"))
    if not so:
        return None
    parts = [f"Đề nghị điều chỉnh Quyết định giao đất, cho thuê đất số {so}"]
    ngay = _date(values.get("QuyetDinhGoc_NgayKy"))
    if ngay:
        parts.append(f"ngày {ngay}")
    co_quan = _plain(values.get("QuyetDinhGoc_CoQuanBanHanh"))
    if co_quan:
        parts.append(f"của {co_quan}")
    text = " ".join(parts)
    du_an = _plain(values.get("DuAn_TenDuAn"))
    return f"{text} - {du_an}" if du_an else text


def _people(values: dict, key: str) -> list[dict]:
    raw = values.get(key)
    if isinstance(raw, dict):
        raw = [raw]
    return [p for p in raw if isinstance(p, dict)] if isinstance(raw, list) else []


def _get(person: dict | None, *keys):
    """Ứng viên đến từ nhiều nguồn nên tên khoá khác nhau (HoTen ↔ hoTen)."""
    for key in keys:
        value = (person or {}).get(key)
        if value not in (None, "", {}, []):
            return value
    return None


def _match_anchor(person: dict | None, anchor_id: str, anchor_name: str) -> bool:
    """Khớp theo SỐ ĐỊNH DANH trước; giấy tờ cũ hay in CMND 9 số nên mới cho khớp theo HỌ TÊN."""
    if not person:
        return False
    person_id = _digits(_get(person, "SoDinhDanh", "soDinhDanh"))
    person_name = _fold(_get(person, "HoTen", "hoTen"))
    if anchor_id and person_id:
        return person_id == anchor_id
    return bool(anchor_name and person_name and person_name == anchor_name)


def _person_block(values: dict, prefix: str) -> dict | None:
    """Gom khối phẳng ChuHoSo_*/NguoiNop_* thành một ứng viên cùng dạng với danh sách."""
    block = {
        "HoTen": values.get(f"{prefix}_HoTen"),
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
    return block if any(v not in (None, "", {}, []) for v in block.values()) else None


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


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "có", "1"):
        return True
    return bool(values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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
    # Cổng gửi Họ tên + Số Căn cước + Ngày sinh của khối này sang CSDL quốc gia dân cư để xác thực
    # trước khi cho nộp → cả khối phải là nhân thân của CHÍNH người đang đăng nhập, không ghép người.
    ctx = (options or {}).get("formContext") or {}
    anchor_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_name = _fold(ctx.get("applicantFullname") or ctx.get("fullname"))
    has_anchor = bool(anchor_id or anchor_name)

    proxy = _proxy_person(values)
    # Thứ tự nguồn: CCCD rời (đầy đủ nhất) → người ghi trong giấy tờ → giấy ủy quyền → khối phẳng.
    candidates = _merge_candidates(
        _people(values, "DanhSachCccd"),
        _people(values, "NguoiTrongGiayTo"),
        [proxy] if proxy else [],
        [_person_block(values, "NguoiNop")] if _person_block(values, "NguoiNop") else [],
        [_person_block(values, "ChuHoSo")] if not is_org and _person_block(values, "ChuHoSo") else [],
    )

    # Chế độ TỜ KHAI (cài đặt "Người nộp = chủ hồ sơ"): bỏ mốc tài khoản, lấy người nộp theo hồ sơ —
    # bên được ủy quyền trước, rồi người ký đơn/đại diện, cuối cùng là chủ hồ sơ.
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    if theo_to_khai:
        base = proxy or _person_block(values, "NguoiNop") or (
            None if is_org else _person_block(values, "ChuHoSo")
        )
        # Khối phẳng thường chỉ có tên + số định danh; nhân thân đầy đủ (ngày sinh, ngày/nơi cấp, địa
        # chỉ) nằm ở CCCD hoặc giấy tờ khác của cùng người đó → gộp thêm, ưu tiên khối phẳng.
        nguoi_nop = next(iter(_merge_candidates([base], candidates)), None) if base else None
    else:
        nguoi_nop = next(
            (p for p in candidates if _match_anchor(p, anchor_id, anchor_name)), None
        ) if has_anchor else None

    if is_org:
        # Người nộp đại diện cho tổ chức → ô tên cơ quan/MST của khối người nộp cũng là của tổ chức đó.
        # Đây là thông tin của TỔ CHỨC nên phát được cả khi chưa xác định người đi nộp.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)

    nop_area = _area(_get(nguoi_nop, "NoiCuTru")) if nguoi_nop else None
    if nguoi_nop:
        nop_identity = _digits(_get(nguoi_nop, "SoDinhDanh"))
        # Chế độ theo tài khoản ghi lại ĐÚNG chuỗi mốc (không lấy biến thể viết hoa/CMND 9 số trong
        # giấy tờ) để không phá lệnh xác thực CSDLQG.
        if theo_to_khai:
            add("CongDan_tenCongDan", _plain(_get(nguoi_nop, "HoTen")))
            add("CongDan_soCmnd", nop_identity)
        else:
            add("CongDan_tenCongDan", _plain(ctx.get("applicantFullname") or ctx.get("fullname")))
            add("CongDan_soCmnd", anchor_id)
        nop_ngay_cap = _date(_get(nguoi_nop, "NgayCap"))
        # Nơi cấp mặc định CHỈ khi hồ sơ thật sự có giấy tờ định danh của người đó — không thì là bịa.
        nop_noi_cap = normalize_issuer(_plain(_get(nguoi_nop, "NoiCap")))
        if not nop_noi_cap and nop_identity:
            nop_noi_cap = default_issuer(nop_ngay_cap)
        add("CongDan_ngaySinhCongDan", _date(_get(nguoi_nop, "NgaySinh")))
        add("CongDan_gioiTinhCongDan", _plain(_get(nguoi_nop, "GioiTinh")))
        add("CongDan_danTocCongDan", _plain(_get(nguoi_nop, "DanToc")))
        add("CongDan_ngayCapCmnd", nop_ngay_cap)
        add("CongDan_noiCapCmnd", nop_noi_cap)
        add("CongDan_diDong", _phone(_get(nguoi_nop, "DienThoai")))
        add("CongDan_email", _plain(_get(nguoi_nop, "Email")))
        add("CongDan_fax", _plain(_get(nguoi_nop, "Fax")))
        if theo_to_khai and has_anchor and not _match_anchor(nguoi_nop, anchor_id, anchor_name):
            warnings.append(
                "Khối \"Thông tin người nộp\" đang điền theo TỜ KHAI ("
                + (_plain(_get(nguoi_nop, "HoTen")) or "người trong hồ sơ")
                + ") nhưng tài khoản đang đăng nhập là "
                + (_plain(ctx.get("applicantFullname")) or "người khác")
                + ". Cổng xác thực Họ tên/Số Căn cước/Ngày sinh với CSDL quốc gia dân cư trước khi cho "
                "nộp — lệch tài khoản sẽ bị chặn với thông báo \"Thông tin người nộp hồ sơ không đúng "
                "với tài khoản đăng nhập!\". Đăng nhập đúng tài khoản người đi nộp, hoặc tắt cài đặt "
                "\"Người nộp = chủ hồ sơ\"."
            )
        if nop_area:
            add("CongDan_maTinhThanh", _province_label(nop_area.get("tinh")))
            add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
            add("CongDan_diaChi", _plain(nop_area.get("diaChi")))
    elif not has_anchor and not theo_to_khai:
        warnings.append(
            "Không xác định được NGƯỜI ĐANG ĐI NỘP: cổng chưa đổ sẵn Họ tên/Số Căn cước từ tài khoản "
            "định danh (hoặc trang chưa đăng nhập). Trợ lý bỏ trống nhân thân khối \"Thông tin người "
            "nộp\" để khỏi điền nhầm người — đăng nhập đúng tài khoản của người đi nộp rồi quét lại."
        )
    else:
        warnings.append(
            "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
            + (f" ({_plain(ctx.get('applicantFullname'))})" if ctx.get("applicantFullname") else "")
            + " nên khối \"Thông tin người nộp\" để trống — cán bộ nhập tay, KHÔNG lấy thông tin của "
            "người khác trong hồ sơ vì cổng xác thực với CSDL quốc gia dân cư trước khi cho nộp."
        )

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
    # KHÔNG phát `HoSoOnline_veViec`: cơ quan tiếp nhận cấp xã yêu cầu GIỮ NGUYÊN chuỗi cổng điền sẵn
    # theo tên thủ tục ("Điều chỉnh quyết định giao đất… (cấp xã)."). Đây là điểm NGƯỢC với bản nộp ở
    # Sở (1.115652) — ở đó ô này phải ghi đè bằng trích yếu thật của Đơn. `_trich_yeu` giữ lại để bật
    # lại chỉ bằng một dòng `add(...)` nếu cơ quan đổi yêu cầu.

    return out, warnings
