"""Dịch dữ kiện đã trích sang ô eForm khai tử (mẫu 2053) cho thủ tục khai tử có yếu tố nước ngoài (1.001766).

Nền là mapper đăng ký lại khai tử (cùng engine x-*, cùng tên ô mục I / mục II), khác ở các chỗ yếu tố nước ngoài:
- Quốc tịch không mặc định "Việt Nam"; người mang quốc tịch nước ngoài chọn dân tộc "Người nước ngoài" (danh mục của cổng
  không có "Hán") và ghi dân tộc trên giấy vào ô "Khác" đi kèm (nktDanTocKhac).
- Giấy tờ tùy thân: hộ chiếu → "Hộ chiếu"; giấy tờ nước ngoài khác → "Các loại giấy tờ tùy thân khác" + tên giấy. Số định
  danh cá nhân chỉ điền số 12 chữ số của Việt Nam; cơ quan cấp giấy nước ngoài giữ nguyên chữ trên tờ khai.
- Nơi cư trú cuối cùng / nơi chết ở nước ngoài: radio "Khác" (mã "2") + khối {quocGia, diaChi}, không đẩy qua bảng remap
  tỉnh / xã Việt Nam.
- Loại đăng ký: giấy ghi rõ thì theo giấy; không thì tính theo hạn 15 ngày kể từ ngày chết (đúng hạn "1" / quá hạn "4").
- Mục I cổng đổ sẵn theo TÀI KHOẢN: người yêu cầu trên hồ sơ khác tài khoản (nộp thay) thì ghi đè theo hồ sơ, ô hồ sơ không
  có (ngày sinh, ngày cấp, cơ quan cấp) thì xoá để không giữ nhân thân của chủ tài khoản.
"""

import re
from datetime import date

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.formatting import normalize_date, parse_death_time, upper_person_name
from app.pipelines._shared.nationality import normalize_nationality
from app.pipelines.khai_tu_dang_ky_lai.process.mapper import (
    _area,
    _by_name,
    _copy_value,
    _date_or_year,
    _declaration_wins_on_mismatch,
    _digits,
    _fold,
)

from .schema import UI_COMP_BY_NAME

VIET_NAM = "Việt Nam"
TRONG_NUOC, KHAC = "1", "2"
NGUOI_NUOC_NGOAI = "Người nước ngoài"
HO_CHIEU = "Hộ chiếu"
GIAY_TO_KHAC = "Các loại giấy tờ tùy thân khác"
THUONG_TRU, TAM_TRU = "Thường trú", "Tạm trú"
# Radio "Loại đăng ký" của mẫu 2053: mã option.
DUNG_HAN, QUA_HAN, CHET_DA_LAU = "1", "4", "5"
# Luật Hộ tịch: người thân đi khai tử trong 15 ngày kể từ ngày có người chết.
HAN_KHAI_TU_NGAY = 15
_VN_CARDS = {"Căn cước công dân", "Thẻ căn cước", "Chứng minh nhân dân", "Giấy chứng nhận căn cước"}
_ORDER = {name: index for index, name in enumerate(UI_COMP_BY_NAME)}
# Ô mục I cổng đổ theo tài khoản mà hồ sơ người nộp thay có thể không có → xoá. Ô chọn không xoá: engine chưa có
# nhánh xoá x-select, giá trị rỗng sẽ khớp nhầm option đầu danh sách.
_ACCOUNT_PREFILLED = ("NgaySinhC", "SoDinhDanhC", "SoGiayToDinhDanhC", "NgayCapDDC", "NoiCapDDC")


def _nation(value) -> str:
    # exact_only: khoá ngắn của bảng không được nuốt tên nước khác; tên lạ giữ nguyên cho extension khớp danh mục.
    return normalize_nationality(value, default="", exact_only=True) if str(value or "").strip() else ""


def is_foreign(nation: str) -> bool:
    return bool(nation) and _fold(nation) not in {"viet nam", "vietnam", "vn"}


def _gender(value) -> str:
    folded = _fold(value)
    if folded in {"nam", "m", "male", "男"} or folded.startswith("nam"):
        return "Nam"
    if folded in {"nu", "f", "female", "女"} or folded.startswith("nu"):
        return "Nữ"
    return ""


def _strip_country(text: str, country: str) -> str:
    """Bỏ tên nước dính ở cuối địa chỉ ("..., tỉnh Quảng Đông Trung Quốc") — quốc gia đã nằm ở ô riêng."""
    words = str(text or "").strip().rstrip(",. ").split()
    size = len(country.split())
    if size and len(words) > size and _fold(" ".join(words[-size:])) == _fold(country):
        return " ".join(words[:-size]).rstrip(",. ")
    return str(text or "").strip()


def place(value, fallback_country: str = "") -> tuple[str, dict] | None:
    """Địa chỉ đã trích → (mã radio, giá trị khối): ("1", khối trong nước) / ("2", {quocGia, diaChi}) / None.

    ``fallback_country`` = quốc tịch nước ngoài của người đó: LLM bỏ trống quocGia nhưng địa chỉ có tên nước này thì vẫn
    là địa chỉ nước ngoài.
    """
    if not isinstance(value, dict):
        return None
    country = _nation(value.get("quocGia"))
    parts = [value.get("chiTietDuoiXa") or value.get("diaChi"), value.get("xa"), value.get("huyen"), value.get("tinh")]
    parts = [str(part).strip() for part in parts if str(part or "").strip()]
    if not country and is_foreign(fallback_country) and _fold(fallback_country) in _fold(" ".join(parts)):
        country = fallback_country
    if is_foreign(country):
        detail = _strip_country(", ".join(parts), country)
        return KHAC, {"quocGia": country, **({"diaChi": detail} if detail else {})}
    area = _area({**value, "quocGia": VIET_NAM,
                  "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa") or ""})
    return (TRONG_NUOC, area) if area else None


_MONTHS = {name: index for index, names in enumerate(
    (("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",), ("jun", "june"),
     ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
     ("dec", "december")), start=1) for name in names}


def _date(value) -> str:
    """dd/mm/yyyy; nhận thêm kiểu hộ chiếu "07 APR 1990" / "07 APR/4月 1990" mà normalize_date không đọc được."""
    text = str(value or "").strip()
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,9})\.?(?:\s*/\s*\S+)?\s+(\d{4})$", text)
    if match and match.group(2).lower() in _MONTHS:
        return f"{int(match.group(1)):02d}/{_MONTHS[match.group(2).lower()]:02d}/{match.group(3)}"
    return normalize_date(text) if text else ""


def _parse_date(value) -> date | None:
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", _date(value))
    if not match:
        return None
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def registration_type(declared, death_date, today: date | None = None) -> tuple[str, bool]:
    """(mã radio Loại đăng ký, default). Giấy ghi rõ thì theo giấy; không thì so ngày chết với hạn 15 ngày."""
    folded = _fold(declared)
    if "da lau" in folded:
        return CHET_DA_LAU, False
    if "qua han" in folded:
        return QUA_HAN, False
    if "dung han" in folded:
        return DUNG_HAN, False
    died = _parse_date(death_date)
    if not died:
        return DUNG_HAN, True
    return (DUNG_HAN if ((today or date.today()) - died).days <= HAN_KHAI_TU_NGAY else QUA_HAN), False


def _doc_type(id_type, number, issuer: str, foreign: bool) -> str:
    """Option "Giấy tờ tùy thân" của eForm (danh mục 1a5e9b7218)."""
    folded = _fold(id_type)
    if "ho chieu" in folded or "passport" in folded:
        return HO_CHIEU
    digits = _digits(number)
    if foreign:
        return GIAY_TO_KHAC if (id_type or number) else ""
    if not number:
        return ""
    if re.search(r"[A-Za-z]", str(number)) and len(digits) not in (9, 12):
        return HO_CHIEU  # số giấy có chữ cái, không phải CMND 9 số / CCCD 12 số
    if len(digits) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type(id_type or "Căn cước công dân", issuer)


def _identity(values: dict, prefix: str, foreign: bool) -> dict:
    """{loai, ten (giấy khác), soDinhDanh, so, ngayCap, noiCap} của một người."""
    number = str(values.get(f"{prefix}_IdNumber") or "").strip()
    issue_date = _date(values.get(f"{prefix}_IdIssueDate"))
    raw_place = str(values.get(f"{prefix}_IdIssuePlace") or "").strip()
    id_type = str(values.get(f"{prefix}_IdType") or "").strip()
    loai = _doc_type(id_type, number, normalize_issuer(raw_place) or default_issuer(issue_date), foreign)
    vn_card = loai in _VN_CARDS
    if vn_card:
        number = _digits(number)
        issuer = normalize_issuer(raw_place) or (default_issuer(issue_date) if issue_date else "")
    else:
        number = re.sub(r"\s+", "", number).upper()
        issuer = raw_place
    return {
        "loai": loai,
        "ten": id_type if loai == GIAY_TO_KHAC else "",
        "soDinhDanh": number if vn_card and len(number) == 12 else "",
        "so": number,
        "ngayCap": issue_date,
        "noiCap": issuer,
    }


def _account(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return str(ctx.get("applicantFullname") or "").strip(), _digits(ctx.get("applicantIdentityNumber"))


def _is_account(name, number, options: dict | None) -> bool:
    """Người yêu cầu trên hồ sơ chính là chủ tài khoản (hoặc không có mốc tài khoản để so)."""
    account_name, account_id = _account(options)
    if not account_name and not account_id:
        return True
    digits = _digits(number)
    if account_id and len(digits) == len(account_id):
        return digits == account_id
    return bool(name) and _fold(name) == _fold(account_name)


def enrich(fields: list[dict], options: dict | None = None, today: date | None = None) -> list[dict]:
    """Dữ kiện compact → ô eForm 2053, theo thứ tự UI_COMP_BY_NAME (ô tích trước khối nó mở ra)."""
    values = _by_name(fields)
    out: list[dict] = []

    def add(name: str, value, default: bool = False, **extra) -> None:
        if value in (None, "", {}, []) or any(f["name"] == name for f in out):
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value, **extra}
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc từ giấy tờ
        out.append(field)

    # TH1 — nhân thân lệch cả tên lẫn số so với tờ khai: thẻ của người khác → theo tờ khai, viền vàng.
    requester_other = _declaration_wins_on_mismatch(values, "Requester", "ToKhai_NguoiYeuCau")
    deceased_other = _declaration_wins_on_mismatch(values, "Deceased", "ToKhai_NguoiChet")

    # ── I. Người yêu cầu ──
    requester_name = values.get("Requester_FullName") or values.get("ToKhai_NguoiYeuCau_HoTen")
    if requester_name:
        values.setdefault("Requester_IdNumber", values.get("ToKhai_NguoiYeuCau_SoDinhDanh"))
        req = _identity(values, "Requester", foreign=False)
        add("HoVaTenC", upper_person_name(requester_name), requester_other)
        add("NgaySinhC", _date(values.get("Requester_BirthDate")))
        add("SoDinhDanhC", req["soDinhDanh"], requester_other)
        add("LoaiGiayToDinhDanhC", req["loai"])
        add("nycTenGiayTo", req["ten"], otherOf="LoaiGiayToDinhDanhC")
        add("SoGiayToDinhDanhC", req["so"], requester_other)
        add("NgayCapDDC", req["ngayCap"])
        add("NoiCapDDC", req["noiCap"])
        if not _is_account(requester_name, req["so"], options):
            # Nộp thay: ô cổng đổ theo tài khoản mà hồ sơ không có → xoá, không để nhân thân chủ tài khoản.
            emitted = {f["name"] for f in out}
            for name in _ACCOUNT_PREFILLED:
                if name not in emitted:
                    out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True})
    requester_place = place(values.get("Requester_Residence"))
    if requester_place:
        code, area = requester_place
        add("nycLoaiCuTru", THUONG_TRU, True)
        add("nycNoiCuTru", code)
        add("nycNoiCuTru_TrongNuoc" if code == TRONG_NUOC else "nycNoiCuTru_NuocNgoai", area)
    add("QuanHe", str(values.get("Requester_Relationship") or "").strip())

    # ── II. Người được khai tử ──
    nationality = _nation(values.get("Deceased_Nationality"))
    foreign = is_foreign(nationality)
    code, is_default = registration_type(values.get("Registration_Type"), values.get("Deceased_DeathDate"), today)
    add("loaiDangKy", code, is_default)
    add("HoTen", upper_person_name(values.get("Deceased_FullName")), deceased_other)
    birth = values.get("Deceased_BirthDate")
    add("NgaySinh", _date_or_year(_date(birth) or birth), deceased_other)  # ô chữ nhận cả "yyyy"
    add("GioiTinh", _gender(values.get("Deceased_Gender")))
    ethnicity = str(values.get("Deceased_Ethnicity") or "").strip()
    if foreign:
        add("nktDanToc", NGUOI_NUOC_NGOAI, not ethnicity)
        if ethnicity and _fold(ethnicity) != _fold(NGUOI_NUOC_NGOAI):
            add("nktDanTocKhac", ethnicity, otherOf="nktDanToc")
    else:
        add("nktDanToc", ethnicity)
    add("nktQuocTich", nationality)
    dec = _identity(values, "Deceased", foreign)
    add("SoDinhDanh", dec["soDinhDanh"], deceased_other)
    add("LoaiGiayToDinhDanh", dec["loai"])
    add("nktTenGiayTo", dec["ten"], otherOf="LoaiGiayToDinhDanh")
    add("SoGiayToDinhDanh", dec["so"], deceased_other)
    add("NgayCapDD", dec["ngayCap"])
    add("NoiCapDD", dec["noiCap"])
    residence = place(values.get("Deceased_Residence"), nationality)
    if residence:
        code, area = residence
        residence_type = next((label for label in (TAM_TRU, THUONG_TRU)
                               if _fold(label) in _fold(values.get("Deceased_ResidenceType"))), "")
        add("nktLoaiCuTru", residence_type or THUONG_TRU, not residence_type)
        add("nktNoiCuTru", code)
        add("nktNoiCuTru_TrongNuoc" if code == TRONG_NUOC else "nktNoiCuTru_NuocNgoai", area)

    add("NgayMat", _date(values.get("Deceased_DeathDate")))
    death_time = parse_death_time(values.get("Deceased_DeathTime"))
    add("GioMat", death_time.get("hour"))
    add("PhutMat", death_time.get("minute"))
    death_place = place(values.get("Deceased_DeathPlace")) or place(
        {"diaChi": values.get("DeathNotice_IssueAgency")} if values.get("DeathNotice_IssueAgency") else None)
    if death_place:
        code, area = death_place
        add("nktNoiChet", code)
        add("nktNoiChet_TrongNuoc" if code == TRONG_NUOC else "nktNoiChet_NuocNgoai", area)
    add("NguyenNhanMat", str(values.get("Deceased_DeathCause") or "").strip())

    if values.get("DeathNotice_Number") or values.get("DeathNotice_IssueDate") or values.get("DeathNotice_IssueAgency"):
        add("gbtLoai", values.get("DeathNotice_Type") or "Giấy báo tử")
        add("gbtSo", values.get("DeathNotice_Number"))
        add("gbtNgay", _date(values.get("DeathNotice_IssueDate")))
        add("gbtCoQuanCap", values.get("DeathNotice_IssueAgency"))

    quantity = int(_digits(values.get("CopyRequest_Quantity")) or 0)
    copy = "Có" if quantity else _copy_value(values.get("CopyRequest_WantsCopy"))
    if copy in ("Có", "Không"):
        add("CapBanSao", copy)
        if copy == "Có":
            add("SoLuong", str(quantity or 1), not quantity)

    out.sort(key=lambda f: _ORDER[f["name"]])
    return out
