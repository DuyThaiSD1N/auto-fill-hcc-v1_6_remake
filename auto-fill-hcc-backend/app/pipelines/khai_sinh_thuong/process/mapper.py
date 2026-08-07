"""Map compact OCR-derived facts to regular birth registration legacy fields."""

import re

from app.pipelines._shared.legacy_fields.dang_ky_lai import ALLOWED as LEGACY_COMP_BY_NAME
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.hospital_lookup import lookup_hospital

# Đổi tên tỉnh/thành theo sắp xếp đơn vị hành chính 2025 (giấy tờ cũ ghi tên cũ → chuẩn hóa tên mới).
_TINH_RENAME = {"thua thien hue": "Huế"}


def _fold_tinh(value: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower().strip()


def _norm_tinh(value):
    if not value:
        return value
    return _TINH_RENAME.get(_fold_tinh(value), value)


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()

_COMP_BY_NAME = {
    **LEGACY_COMP_BY_NAME,
    "LoaiDangKy": "x-radio",
    "nksLoaiKhaiSinh": "x-select-default",
    "QuanHe": "x-radio",
    # Nhánh "Khác" của mục Nơi cư trú — ô nhập tự do (dùng cho cha/mẹ đã chết).
    # x-select-area nhận value là CHUỖI thì extension điền thẳng vào ô text.
    "ChaNoiCuTru_NuocNgoai": "x-select-area",
    "MeNoiCuTru_NuocNgoai": "x-select-area",
    "nycNoiCuTru_NuocNgoai": "x-select-area",
}

_STRUCTURAL_DEFAULTS = [
    {"name": "LoaiDangKy", "comp": "x-radio", "value": "1"},
    {"name": "nksLoaiKhaiSinh", "comp": "x-select-default", "value": "Đã xác định được cả cha lẫn mẹ"},
]

_TAIL_DEFAULTS = [
    {"name": "QuanHe", "comp": "x-radio", "value": "ChaDe"},
]


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _area(value):
    if not isinstance(value, dict):
        return None
    xa = _strip_admin_prefix(value.get("xa") or value.get("xã"))
    dia = value.get("diaChi") or value.get("dia_chi") or value.get("diachi")
    # diaChi chỉ là phần CHI TIẾT; nếu chính là tên xã/phường (vd "Phường Tân Phong" trong khi
    # xa="Tân Phong") → trùng lặp vô nghĩa, bỏ đi.
    if dia and _strip_admin_prefix(dia).strip().lower() == (xa or "").strip().lower():
        dia = None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": _norm_tinh(value.get("tinh") or value.get("tỉnh")),
        "xa": xa,
        "diaChi": dia,
    }
    return {k: v for k, v in out.items() if v not in (None, "", {}, [])}


def _birth_year(ngay_sinh) -> int | None:
    """Trích năm sinh từ chuỗi dd/mm/yyyy hoặc yyyy."""
    text = str(ngay_sinh or "").strip()
    # dd/mm/yyyy
    m = re.match(r"^\d{1,2}/\d{1,2}/(\d{4})$", text)
    if m:
        return int(m.group(1))
    # yyyy alone
    if re.match(r"^\d{4}$", text):
        return int(text)
    return None


def _is_deceased_area(value) -> bool:
    """Kiểm tra area có phải marker 'đã chết' không (không có tinh/xa thật)."""
    if not isinstance(value, dict):
        return False
    tinh = str(value.get("tinh") or "").strip()
    xa = str(value.get("xa") or "").strip()
    if tinh or xa:
        return False
    import unicodedata as _ud
    dia = str(value.get("diaChi") or "").strip()
    folded = _ud.normalize("NFD", dia)
    folded = "".join(c for c in folded if _ud.category(c) != "Mn")
    folded = folded.replace("Đ", "D").replace("đ", "d").lower().strip()
    return bool(folded) and any(kw in folded for kw in ("da chet", "dachet", "chet", "da mat"))


def _cccd_nu_is_subject(values: dict) -> bool:
    """Phát hiện trường hợp LLM nhầm: CccdNu_* thực ra là người được đăng ký khai sinh,
    không phải mẹ. Điều kiện:

    A) CccdNu_ có SoDinhDanh (CCCD thật) VÀ năm sinh CccdNu_ gần với năm sinh Gcs_/TkKs_
       (chênh ≤ 2 năm → cùng người).

    B) CccdNu_ có SoDinhDanh VÀ CccdNam_ không có SoDinhDanh (chỉ tên/năm từ tờ khai)
       VÀ năm sinh CccdNam_ già hơn CccdNu_ ít nhất 18 năm.
    """
    nu_sdd = str(values.get("CccdNu_SoDinhDanh") or "").strip()
    if not nu_sdd:
        return False  # Không có CCCD Nữ thật → không áp dụng

    nu_year = _birth_year(values.get("CccdNu_NgaySinh"))
    if not nu_year:
        return False

    # Trường hợp A: năm sinh CccdNu_ trùng/gần với Gcs_ hoặc TkKs_
    gcs_year = _birth_year(values.get("Gcs_NgaySinhCon"))
    tk_year = _birth_year(values.get("TkKs_NgaySinhCon"))
    subject_year = gcs_year or tk_year
    if subject_year and abs(nu_year - subject_year) <= 2:
        return True

    # Trường hợp B: CccdNam_ không có SoDinhDanh (chỉ từ tờ khai) VÀ già hơn nhiều
    nam_sdd = str(values.get("CccdNam_SoDinhDanh") or "").strip()
    if not nam_sdd:
        nam_year = _birth_year(values.get("CccdNam_NgaySinh"))
        if nam_year and (nu_year - nam_year) >= 18:
            # CccdNam_ già hơn CccdNu_ ít nhất 18 tuổi → CccdNu_ là con, CccdNam_ là cha
            return True

    return False


def _resolve_subject(values: dict, nu_is_subject: bool = False) -> dict:
    """Xác định thông tin người được đăng ký khai sinh theo thứ tự ưu tiên:

    1. CccdChuThe_* — CCCD của chính người được đăng ký (đăng ký muộn, còn sống).
    2. CccdNu_*     — khi phát hiện LLM nhầm CccdNu_ là người được đăng ký (nu_is_subject=True).
    3. Gcs_*        — Giấy chứng sinh (trẻ sơ sinh).
    4. TkKs_*       — Tờ khai bản giấy (fallback).
    """
    # Ưu tiên 1: CCCD chủ thể (LLM dùng đúng field mới)
    if values.get("CccdChuThe_HoTen") or values.get("CccdChuThe_NgaySinh"):
        return {
            "ho_ten": values.get("CccdChuThe_HoTen"),
            "ngay_sinh": values.get("CccdChuThe_NgaySinh"),
            "gioi_tinh": values.get("CccdChuThe_GioiTinh"),
            "dan_toc": values.get("CccdChuThe_DanToc"),
            "noi_sinh": None,
            "que_quan": _area(values.get("CccdChuThe_QueQuan")),
            "source": "cccd_chu_the",
        }
    # Ưu tiên 2: LLM nhầm CccdNu_ là mẹ nhưng thực ra là người được đăng ký.
    # Họ tên / ngày sinh lấy theo GIẤY CHỨNG SINH (rồi tờ khai) — đó mới là nội dung được
    # đăng ký; CCCD chỉ dùng bổ khuyết khi hai nguồn kia không có.
    if nu_is_subject:
        return {
            "ho_ten": values.get("Gcs_HoTenCon") or values.get("TkKs_HoTenCon") or values.get("CccdNu_HoTen"),
            "ngay_sinh": (
                values.get("Gcs_NgaySinhCon")
                or values.get("TkKs_NgaySinhCon")
                or values.get("CccdNu_NgaySinh")
            ),
            "gioi_tinh": "Nữ",
            "dan_toc": values.get("Gcs_DanTocCon") or values.get("CccdNu_DanToc"),
            "noi_sinh": _area(values.get("Gcs_NoiSinh")) or _area(values.get("TkKs_NoiSinh")),
            "que_quan": _area(values.get("CccdNu_QueQuan") or values.get("CccdNam_QueQuan")),
            "source": "cccd_nu_is_subject",
        }
    # Ưu tiên 3: Giấy chứng sinh
    if values.get("Gcs_HoTenCon") or values.get("Gcs_NgaySinhCon"):
        # Quê quán con = quê quán cha
        # Ưu tiên: QueQuan (CCCD cũ) > NoiDangKyKhaiSinh (căn cước mới) > NoiCuTru (fallback)
        que_quan_raw = (
            _area(values.get("CccdNam_QueQuan"))
            or _area(values.get("CccdNam_NoiDangKyKhaiSinh"))  
            or _area(values.get("CccdNam_NoiCuTru_TrongNuoc"))
        )
        que_quan = remap_area(que_quan_raw) if que_quan_raw else None
        
        # Nơi sinh: áp dụng lookup_hospital để bổ sung xã/phường cho bệnh viện
        noi_sinh_raw = _area(values.get("Gcs_NoiSinh"))
        noi_sinh = noi_sinh_raw
        if noi_sinh_raw and not noi_sinh_raw.get("xa"):
            dia_chi = noi_sinh_raw.get("diaChi") or ""
            bv_info = lookup_hospital(dia_chi)
            if bv_info:
                noi_sinh = {**noi_sinh_raw, "xa": bv_info["xa"]}
                if not noi_sinh_raw.get("tinh"):
                    noi_sinh["tinh"] = bv_info["tinh"]
        
        return {
            "ho_ten": values.get("Gcs_HoTenCon"),
            "ngay_sinh": values.get("Gcs_NgaySinhCon"),
            "gioi_tinh": values.get("Gcs_GioiTinhCon"),
            "dan_toc": values.get("Gcs_DanTocCon"),
            "noi_sinh": noi_sinh,
            "que_quan": que_quan,
            "source": "gcs",
        }
    # Ưu tiên 4: Tờ khai
    if values.get("TkKs_HoTenCon") or values.get("TkKs_NgaySinhCon"):
        return {
            "ho_ten": values.get("TkKs_HoTenCon"),
            "ngay_sinh": values.get("TkKs_NgaySinhCon"),
            "gioi_tinh": values.get("TkKs_GioiTinhCon"),
            "dan_toc": values.get("TkKs_DanTocCon"),
            "noi_sinh": _area(values.get("TkKs_NoiSinh")),
            "que_quan": _area(values.get("TkKs_QueQuan")),
            "source": "tk",
        }
    return {}


def _parent_residence(values: dict, cccd_key: str, tk_key: str, allow_cccd: bool) -> tuple:
    """Nơi cư trú cha/mẹ, trả (area, deceased).

    Nguồn theo thứ tự: CCCD (bản in, OCR chắc hơn) → dòng "Nơi cư trú" ở mục cha/mẹ trên
    tờ khai. Tờ khai lấp chỗ trống cho cha/mẹ không nộp CCCD — trước đây nhóm này không có
    địa chỉ nào nên hai ô trên form bị bỏ trắng.

    Marker "Đã chết"/"Đã mất" là hạng bét: chỉ dùng khi KHÔNG nguồn nào có địa chỉ thật.
    """
    keys = ([cccd_key] if allow_cccd else []) + [tk_key]
    found = []
    for key in keys:
        raw = values.get(key)
        area = _area(raw)
        if area:
            found.append((area, _is_deceased_area(raw)))
    for area, deceased in found:
        if not deceased:
            return area, False
    return found[0] if found else (None, False)


def _add_residence(add, prefix: str, residence, deceased: bool) -> None:
    """Phát mục "Nơi cư trú" của một người (prefix = Cha / Me / nyc).

    Bình thường: tick "Trong nước" (id ...-1) + ô địa danh Tỉnh/Xã có cascade.

    Cha/mẹ ĐÃ CHẾT: tờ khai ghi "Đã chết"/"Đã mất" thay cho địa chỉ. Nhánh "Trong nước"
    chỉ có dropdown tỉnh/xã nên KHÔNG gõ được chữ này — phải tick "Khác" để form hiện ô
    nhập tự do, rồi mới điền chữ vào đó. Thứ tự add quyết định thứ tự extension điền:
    radio trước, ô text sau (engine legacy chờ 200ms sau radio cho ô kia render).

    Cũng không chọn "Thường trú" vì người đã mất không còn loại cư trú.
    """
    if not residence:
        return
    if deceased:
        add(f"{prefix}NoiCuTru", "Khác")
        add(f"{prefix}NoiCuTru_NuocNgoai", residence.get("diaChi"))
        return
    add(f"{prefix}LoaiCuTru", "Thường trú")
    add(f"{prefix}NoiCuTru", "1")
    add(f"{prefix}NoiCuTru_TrongNuoc", residence)


def _resolve_requester(
    values: dict,
    *,
    nu_is_subject: bool,
    has_father_cccd: bool,
    has_mother_cccd: bool,
    father_residence,
    mother_residence,
    father_deceased: bool = False,
    mother_deceased: bool = False,
) -> dict:
    """Xác định NGƯỜI YÊU CẦU (khối HoVaTenC/SoDinhDanhC...) hoàn toàn từ dữ liệu OCR.

    Cổng dịch vụ công tự đổ sẵn người yêu cầu theo tài khoản VNeID đang đăng nhập — thường
    KHÔNG phải người trên hồ sơ giấy. Mapper phải phát field để đè lên dữ liệu đó.

    Thứ tự ưu tiên:
      1. Tờ khai (TkKs_Nyc*) — dòng "Họ, chữ đệm, tên người yêu cầu"; đây là nguồn khai báo
         trực tiếp nên thắng mọi suy luận khác.
      2. CCCD chủ thể (CccdChuThe_*, hoặc CccdNu_* khi nu_is_subject) — đăng ký muộn, người
         được đăng ký khai sinh tự đi làm thủ tục.
      3. CCCD cha (CccdNam_*) — trường hợp thông thường.
      4. CCCD mẹ (CccdNu_*) — khi hồ sơ chỉ có CCCD mẹ.

    Không suy ra được → trả {} để giữ nguyên dữ liệu cổng điền sẵn.
    """
    # 1. Người yêu cầu khai trên tờ khai (vd chị dâu, anh, em, chú, bác...).
    if values.get("TkKs_NycHoTen"):
        return {
            "ho_ten": values.get("TkKs_NycHoTen"),
            "so_dinh_danh": values.get("TkKs_NycSoDinhDanh"),
            "ngay_cap": values.get("TkKs_NycNgayCapCccd"),
            "noi_cap": default_issuer(values.get("TkKs_NycNgayCapCccd")),
            "noi_cu_tru": _area(values.get("TkKs_NycNoiCuTru")),
            "quan_he": "Khac",
            "source": "to_khai",
        }

    # 2. Chính người được đăng ký khai sinh (đăng ký muộn, đã có CCCD).
    if values.get("CccdChuThe_HoTen"):
        return {
            "ho_ten": values.get("CccdChuThe_HoTen"),
            "so_dinh_danh": values.get("CccdChuThe_SoDinhDanh"),
            "ngay_cap": values.get("CccdChuThe_NgayCap"),
            "noi_cap": values.get("CccdChuThe_NoiCap") or default_issuer(values.get("CccdChuThe_NgayCap")),
            "noi_cu_tru": _area(values.get("CccdChuThe_NoiCuTru")),
            "quan_he": "Khac",
            "source": "cccd_chu_the",
        }
    if nu_is_subject and values.get("CccdNu_HoTen"):
        # LLM nhầm CCCD chủ thể thành CCCD mẹ — vẫn là người được đăng ký tự đi làm.
        return {
            "ho_ten": values.get("CccdNu_HoTen"),
            "so_dinh_danh": values.get("CccdNu_SoDinhDanh"),
            "ngay_cap": values.get("CccdNu_NgayCap"),
            "noi_cap": values.get("CccdNu_NoiCap") or default_issuer(values.get("CccdNu_NgayCap")),
            "noi_cu_tru": _area(values.get("CccdNu_NoiCuTru_TrongNuoc")),
            "quan_he": "Khac",
            "source": "cccd_nu_is_subject",
        }

    # 3. Cha — mặc định của trường hợp thông thường.
    if has_father_cccd:
        return {
            "ho_ten": values.get("CccdNam_HoTen"),
            "so_dinh_danh": values.get("CccdNam_SoDinhDanh"),
            "ngay_cap": values.get("CccdNam_NgayCap"),
            "noi_cap": values.get("CccdNam_NoiCap") or default_issuer(values.get("CccdNam_NgayCap")),
            "noi_cu_tru": father_residence,
            "deceased": father_deceased,
            "quan_he": "ChaDe",
            "source": "cccd_cha",
        }

    # 4. Mẹ — hồ sơ chỉ có CCCD mẹ.
    if has_mother_cccd:
        return {
            "ho_ten": values.get("CccdNu_HoTen"),
            "so_dinh_danh": values.get("CccdNu_SoDinhDanh"),
            "ngay_cap": values.get("CccdNu_NgayCap"),
            "noi_cap": values.get("CccdNu_NoiCap") or default_issuer(values.get("CccdNu_NgayCap")),
            "noi_cu_tru": mother_residence,
            "deceased": mother_deceased,
            "quan_he": "MeDe",
            "source": "cccd_me",
        }

    return {}


def enrich(fields: list[dict]) -> list[dict]:
    """Derive deterministic legacy UI fields while preserving response shape."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = _COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    for default in _STRUCTURAL_DEFAULTS:
        add(default["name"], default["value"])

    # ── Phát hiện LLM nhầm CccdNu_ là mẹ nhưng thực ra là người được đăng ký ──
    nu_is_subject = _cccd_nu_is_subject(values)

    # ── Xác định thông tin người được đăng ký ──────────────────────────────
    subject = _resolve_subject(values, nu_is_subject=nu_is_subject)
    has_child = bool(subject)

    # ── Xác định cha / mẹ ─────────────────────────────────────────────────
    # nu_is_subject=True → CccdNu_ đã dùng làm con → không dùng làm mẹ nữa
    # CccdNam_ không có SoDinhDanh khi đó → cha chỉ từ tờ khai (tên/năm gcs/tk)
    has_father_cccd = bool(values.get("CccdNam_SoDinhDanh") or values.get("CccdNam_HoTen")) and not nu_is_subject
    has_mother_cccd = bool(values.get("CccdNu_SoDinhDanh") or values.get("CccdNu_HoTen")) and not nu_is_subject

    # Khi CccdNam_ không có SoDinhDanh (lấy từ tờ khai) → coi là cha tờ khai, không phải CCCD cha
    if has_father_cccd and not values.get("CccdNam_SoDinhDanh"):
        has_father_cccd = False
        if not values.get("TkKs_HoTenCha") and values.get("CccdNam_HoTen"):
            values["TkKs_HoTenCha"] = values.get("CccdNam_HoTen")
            values["TkKs_NamSinhCha"] = values.get("CccdNam_NgaySinh")
            values["TkKs_DanTocCha"] = values.get("CccdNam_DanToc")

    # Khi CccdNu_ không có SoDinhDanh (lấy từ tờ khai) → coi là mẹ tờ khai, không phải CCCD mẹ
    if has_mother_cccd and not values.get("CccdNu_SoDinhDanh"):
        has_mother_cccd = False
        if not values.get("TkKs_HoTenMe") and values.get("CccdNu_HoTen"):
            values["TkKs_HoTenMe"] = values.get("CccdNu_HoTen")
            values["TkKs_NamSinhMe"] = values.get("CccdNu_NgaySinh")
            values["TkKs_DanTocMe"] = values.get("CccdNu_DanToc")
    # Cập nhật has_father_tk / has_mother_tk sau khi sync từ CccdNam_/CccdNu_ sang TkKs_
    has_father_tk = bool(values.get("TkKs_HoTenCha"))
    has_mother_tk = bool(values.get("TkKs_HoTenMe"))

    # Khi nu_is_subject: cha lấy từ CccdNam_ (tên/năm trên tờ khai) nếu có
    if nu_is_subject:
        # CccdNam_ chỉ có tên + năm sinh (từ tờ khai, không có SoDinhDanh) → cha tờ khai
        if values.get("CccdNam_HoTen") and not values.get("CccdNam_SoDinhDanh"):
            has_father_tk = True
            # Gán vào TkKs_HoTenCha nếu chưa có
            if not values.get("TkKs_HoTenCha"):
                values["TkKs_HoTenCha"] = values.get("CccdNam_HoTen")
                values["TkKs_NamSinhCha"] = values.get("CccdNam_NgaySinh")
                values["TkKs_DanTocCha"] = values.get("CccdNam_DanToc")
        # Mẹ: lấy từ Gcs_ hoặc TkKs_ nếu có tên mẹ
        if not has_mother_tk and (values.get("Gcs_HoTenCon") or values.get("TkKs_HoTenMe")):
            pass  # mẹ không có thông tin → để trống

    # nu_is_subject → CccdNam_/CccdNu_ không phải cha/mẹ thật, chỉ còn tờ khai làm nguồn.
    father_residence, father_deceased = _parent_residence(
        values, "CccdNam_NoiCuTru_TrongNuoc", "TkKs_NoiCuTruCha", allow_cccd=not nu_is_subject
    )
    mother_residence, mother_deceased = _parent_residence(
        values, "CccdNu_NoiCuTru_TrongNuoc", "TkKs_NoiCuTruMe", allow_cccd=not nu_is_subject
    )

    # Quê quán con KHÔNG được suy từ marker "đã chết" — đó không phải địa danh.
    # Ưu tiên: QueQuan > NoiDangKyKhaiSinh > NoiCuTru (khi không deceased)
    # Tính toán father_origin trong MỌI trường hợp (cả nu_is_subject) để làm fallback cho quê quán con
    father_origin_raw = (
        _area(values.get("CccdNam_QueQuan"))
        or _area(values.get("CccdNam_NoiDangKyKhaiSinh"))
        or (None if father_deceased else father_residence)
    )
    # Áp dụng remap để chuẩn hóa xã/phường
    father_origin = remap_area(father_origin_raw) if father_origin_raw else None

    father_issuer = values.get("CccdNam_NoiCap") or default_issuer(values.get("CccdNam_NgayCap"))
    mother_issuer = values.get("CccdNu_NoiCap") or default_issuer(values.get("CccdNu_NgayCap"))

    # ── Người yêu cầu — suy ra TỪ OCR, không để cổng tự đổ theo tài khoản VNeID ──
    requester = _resolve_requester(
        values,
        nu_is_subject=nu_is_subject,
        has_father_cccd=has_father_cccd,
        has_mother_cccd=has_mother_cccd,
        father_residence=father_residence,
        mother_residence=mother_residence,
        father_deceased=father_deceased,
        mother_deceased=mother_deceased,
    )

    # QuanHe điền SỚM — trước thông tin cha/mẹ để tránh form Angular reset section sau khi
    # chọn radio. Suy theo nguồn người yêu cầu: CCCD cha → ChaDe, CCCD mẹ → MeDe, còn lại → Khac.
    add("QuanHe", requester.get("quan_he") or _TAIL_DEFAULTS[0]["value"])

    if requester:
        add("HoVaTenC", requester.get("ho_ten"))
        add("SoDinhDanhC", requester.get("so_dinh_danh"))
        add("SoGiayToDinhDanhC", requester.get("so_dinh_danh"))
        if requester.get("so_dinh_danh"):
            add("LoaiGiayToDinhDanhC", "Căn cước công dân")
        add("NgayCapDDC", requester.get("ngay_cap"))
        add("NoiCapDDC", requester.get("noi_cap"))
        if not requester.get("deceased"):
            add("nycLoaiCuTru", "Thường trú")
        _add_residence(add, "nyc", requester.get("noi_cu_tru"), bool(requester.get("deceased")))

    # ── Người được khai sinh (con) ─────────────────────────────────────────
    if has_child:
        add("HoTenKS", subject.get("ho_ten"))
        add("NgaySinhChon", subject.get("ngay_sinh"))
        add("GioiTinhKS", subject.get("gioi_tinh"))
        add("DanTocKS", subject.get("dan_toc"))
        add("QuocTichKS", "Việt Nam")

        # Nơi sinh: lấy từ subject nếu có, fallback Gcs_ hoặc TkKs_
        noi_sinh = (
            subject.get("noi_sinh")
            or _area(values.get("Gcs_NoiSinh"))
            or _area(values.get("TkKs_NoiSinh"))
        )
        if noi_sinh:
            add("nksNoiSinh", "1")
            add("nksNoiSinh_TrongNuoc", noi_sinh)

        # Quê quán: ưu tiên subject → tờ khai → fallback theo cha (CCCD cha)
        que_quan = (
            subject.get("que_quan")
            or _area(values.get("TkKs_QueQuan"))
            or father_origin
        )
        if que_quan:
            add("nksQueQuan", "1")
            add("nksQueQuan_TrongNuoc", que_quan)

    # ── Mẹ ────────────────────────────────────────────────────────────────
    if has_mother_cccd:
        add("HoTenMeKS", values.get("CccdNu_HoTen"))
        add("NamSinhMeKS", values.get("CccdNu_NgaySinh"))
        add("SoDinhDanhMe", values.get("CccdNu_SoDinhDanh"))
        add("SoGiayToDinhDanhMe", values.get("CccdNu_SoDinhDanh"))
        add("LoaiGiayToDinhDanhMe", "Căn cước công dân")
        add("NgayCapDDMe", values.get("CccdNu_NgayCap"))
        add("NoiCapDDMe", mother_issuer)
        add("DanTocMeKS", values.get("CccdNu_DanToc"))
        add("QuocTichMeKS", values.get("CccdNu_QuocTich") or "Việt Nam")
        _add_residence(add, "Me", mother_residence, mother_deceased)
    elif has_mother_tk:
        # Mẹ chỉ có tên + năm sinh từ tờ khai (đã mất hoặc không có CCCD)
        add("HoTenMeKS", values.get("TkKs_HoTenMe"))
        add("NamSinhMeKS", values.get("TkKs_NamSinhMe"))
        add("DanTocMeKS", values.get("TkKs_DanTocMe"))
        add("QuocTichMeKS", "Việt Nam")
        _add_residence(add, "Me", mother_residence, mother_deceased)

    # ── Cha ───────────────────────────────────────────────────────────────
    if has_father_cccd:
        add("HoTenChaKS", values.get("CccdNam_HoTen"))
        add("NamSinhChaKS", values.get("CccdNam_NgaySinh"))
        add("SoDinhDanhCha", values.get("CccdNam_SoDinhDanh"))
        add("SoGiayToDinhDanhCha", values.get("CccdNam_SoDinhDanh"))
        add("LoaiGiayToDinhDanhCha", "Căn cước công dân")
        add("NgayCapDDCha", values.get("CccdNam_NgayCap"))
        add("NoiCapDDCha", father_issuer)
        add("DanTocChaKS", values.get("CccdNam_DanToc"))
        add("QuocTichChaKS", values.get("CccdNam_QuocTich") or "Việt Nam")
        _add_residence(add, "Cha", father_residence, father_deceased)
    elif has_father_tk:
        # Cha chỉ có tên + năm sinh từ tờ khai (đã mất hoặc không có CCCD)
        add("HoTenChaKS", values.get("TkKs_HoTenCha"))
        add("NamSinhChaKS", values.get("TkKs_NamSinhCha"))
        add("DanTocChaKS", values.get("TkKs_DanTocCha"))
        add("QuocTichChaKS", "Việt Nam")
        _add_residence(add, "Cha", father_residence, father_deceased)

    # QuanHe đã được điền sớm ở đầu. Các default còn lại (nếu có) điền ở đây.
    for default in _TAIL_DEFAULTS:
        if default["name"] != "QuanHe":
            add(default["name"], default["value"])

    return out

