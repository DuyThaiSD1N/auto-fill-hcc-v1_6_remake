"""Map compact facts sang eForm "ĐƠN YÊU CẦU TRỢ GIÚP PHÁP LÝ" (tokhaidientu.moj.gov.vn, mẫu id 1899).

- Mục I (người được trợ giúp): CCCD > Thông báo > Đơn; địa chỉ liên hệ = nơi đang ở (Thông báo "Nơi cư trú").
  Diện dịch sang ĐÚNG nhãn option x-select-default của cổng (_DIEN_OPTIONS).
- Mục II (người yêu cầu): cổng đổ họ tên + số định danh theo tài khoản. Chỉ ghi khi cổng còn trống; quan hệ
  "Bản thân" khi người yêu cầu trùng người được trợ giúp, còn lại chỉ lấy từ Đơn bản giấy.
- Mục III: tóm tắt ghép từ câu đề nghị + giai đoạn + vụ án của Thông báo (eForm không có ô giai đoạn riêng);
  hình thức suy "Tham gia tố tụng" khi Thông báo đề nghị trợ giúp ở các giai đoạn tố tụng.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.mapper import (
    _area,
    _by_name,
    _clean,
    _date,
    _digits,
    _fold,
    _upper_name,
)
from app.pipelines.yeu_cau_tro_giup_phap_ly.process.schema import (
    DIEN_OPTIONS as _DIEN_OPTIONS,
    HINH_THUC_OPTIONS as _HINH_THUC,
    UI_COMP_BY_NAME,
)

_VN_TZ = timezone(timedelta(hours=7))

# Vai tố tụng của nhóm 16–18 tuổi. "bi buoc toi" đứng trước để "bị buộc tội … bị hại" không lệch vai.
_MINOR_ROLES = (
    ("bi buoc toi", "19"),
    ("kien nghi khoi to", "14"),
    ("pham nhan", "15"),
    ("to giac", "16"),
    ("chuyen huong", "17"),
    ("khan cap", "18"),
    ("bi hai", "20"),
    ("lam chung", "21"),
)
# Diện còn lại, theo thứ tự kiểm tra ("cận nghèo" trước "hộ nghèo", "không thuộc diện" trước tất cả).
_OTHER_DIEN = (
    ("khong thuoc dien", "23"),
    ("can ngheo", "02"),
    ("co cong", "01"),
    ("dan toc thieu so", "03"),
    ("ho ngheo", "04"),
    ("liet si", "05"),
    ("da cam", "06"),
    ("cao tuoi", "07"),
    ("khuyet tat", "08"),
    ("hiv", "09"),
    ("bao luc gia dinh", "10"),
    ("mua ban nguoi", "11"),
    ("nuoc ngoai", "12"),
    ("tre em", "13"),
)

_THAM_GIA_TO_TUNG = "Tham gia tố tụng"
_LITIGATION_STAGES = ("dieu tra", "truy to", "xet xu", "khoi to")
_SELF = "Bản thân"


def _gender(value: Any) -> str:
    text = _fold(value)
    if text in {"nam", "male", "m"}:
        return "Nam"
    if text in {"nu", "female", "f"}:
        return "Nữ"
    return ""


def _parse(value: str) -> date | None:
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _age(birth: str, at: date) -> int | None:
    born = _parse(birth)
    if not born:
        return None
    return at.year - born.year - ((at.month, at.day) < (born.month, born.day))


def _dien(text: Any, *, accused: bool, age: int | None) -> tuple[str, bool]:
    """Dòng 'Thuộc diện …' → (nhãn option, có phải suy đoán không)."""
    folded = _fold(text)
    if folded:
        for label in _DIEN_OPTIONS.values():
            if _fold(label) == folded:
                return label, False
        if "16" in folded and "18" in folded:
            for marker, code in _MINOR_ROLES:
                if marker in folded:
                    return _DIEN_OPTIONS[code], False
        for marker, code in _OTHER_DIEN:
            if marker in folded:
                return _DIEN_OPTIONS[code], False
    # Thông báo không ghi diện: chỉ suy được nhóm tuổi của người bị buộc tội.
    if accused and age is not None and 16 <= age < 18:
        return _DIEN_OPTIONS["19"], True
    if age is not None and age < 16:
        return _DIEN_OPTIONS["13"], True
    return "", False


def _pick(value: Any, options: tuple[str, ...]) -> str:
    folded = _fold(value)
    if not folded:
        return ""
    hits = [o for o in options if _fold(o) == folded or _fold(o) in folded]
    return hits[0] if len(hits) == 1 else ""


def _list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[;,\n]+", value)
    if not isinstance(value, list):
        return []
    return [_clean(v) for v in value if _clean(v)]


def _sentence(text: str) -> str:
    text = _clean(text)
    return text if not text or text.endswith((".", "!", "?")) else text + "."


def _doc_type(hint: Any, issue_date: str, issue_place: Any) -> str:
    """Loại giấy tờ theo option của cổng. Ngày cấp quyết định thẻ cũ/mới: CCCD cấp năm 2023 mà giấy ghi nơi cấp
    "Bộ Công an" vẫn là CCCD (Cục Cảnh sát QLHC), không phải Thẻ căn cước."""
    issuer = default_issuer(issue_date) if issue_date else normalize_issuer(issue_place)
    return id_doc_type(_clean(hint) or "Căn cước công dân", issuer)


def _province_of_org(org: str) -> str:
    """'Trung tâm Trợ giúp pháp lý Nhà nước TP Đà Nẵng' → 'Thành phố Đà Nẵng'."""
    m = re.search(r"\b(tỉnh|thành phố|tp\.?)\s+([^,;(]+)", org or "", flags=re.IGNORECASE)
    name = canonical_province(m.group(2).strip()) if m else None
    return (province_label(name) or "") if name else ""


def _title(value: str) -> str:
    return " ".join(w[:1].upper() + w[1:].lower() for w in value.split())


def _proof_line(values: dict) -> str:
    name = _clean(values.get("TB_TenVanBan"))
    number = _clean(values.get("TB_So"))
    issued = _date(values.get("TB_Ngay"))
    agency = _clean(values.get("TB_CoQuan"))
    if not (name or number):
        return ""
    line = name or "Văn bản"
    if number:
        line += f" số {number}"
    if issued:
        line += f" ngày {issued}"
    if agency:
        line += f" của {agency}"
    return line


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    context = (options or {}).get("formContext") or {}
    today = datetime.now(_VN_TZ).date()
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        out.append(field)
        seen.add(name)

    # ---- I. Người được trợ giúp pháp lý.
    name = _clean(values.get("Ndd_HoTen"))
    birth = _date(values.get("Ndd_NgaySinh"))
    id_number = _digits(values.get("Ndd_SoDinhDanh"))
    issue_date = _date(values.get("Ndd_NgayCap"))
    contact = _area(values.get("Ndd_DiaChiLienHe")) or _area(values.get("Ndd_ThuongTru"))
    phone = _clean(values.get("Ndd_DienThoai"))
    doc_type = _doc_type(values.get("Ndd_LoaiGiayTo"), issue_date, values.get("Ndd_NoiCap")) if id_number else ""

    add("NguoiDuocTGPL_HoVaTen", _upper_name(name))
    add("NguoiDuocTGPL_NgaySinh", birth)
    add("NguoiDuocTGPL_GioiTinh", _gender(values.get("Ndd_GioiTinh")))
    add("NguoiDuocTGPL_LoaiGiayToDinhDanh", doc_type)
    add("NguoiDuocTGPL_SoDinhDanh", id_number)
    if contact:
        add("NguoiDuocTGPL_TinhThanh", contact["tinh"])
        add("NguoiDuocTGPL_PhuongXa", contact["xa"])
        add("NguoiDuocTGPL_DiaChi", contact["diaChi"])
    add("NguoiDuocTGPL_SoDienThoai", phone)

    de_nghi = _clean(values.get("YeuCau_DeNghi"))
    stages = _list(values.get("YeuCau_GiaiDoan"))
    proof_date = _parse(_date(values.get("TB_Ngay"))) or today
    dien, guessed = _dien(
        values.get("Ndd_Dien"),
        accused="buoc toi" in _fold(de_nghi) or "bi can" in _fold(de_nghi),
        age=_age(birth, proof_date),
    )
    add("NguoiDuocTGPL_DienDoiTuong", dien, default=guessed)

    if not name:
        warnings.append("Không đọc được họ tên người được trợ giúp pháp lý từ hồ sơ — vui lòng nhập tay mục I.")
    if not dien:
        warnings.append("Chưa xác định được diện người được trợ giúp pháp lý — vui lòng chọn tay.")
    if not values.get("TheCCCD_SoDinhDanh"):
        warnings.append("Hồ sơ chưa có ảnh CCCD/căn cước của người được trợ giúp pháp lý — nên bổ sung để đính "
                        "kèm cùng giấy tờ chứng minh diện.")

    # ---- II. Người yêu cầu. Cổng đổ họ tên/số theo tài khoản; chỉ ghi khi còn trống.
    account_name = _clean(context.get("applicantFullname"))
    account_id = _digits(context.get("applicantIdentityNumber"))
    paper_name = _clean(values.get("Nyc_HoTen"))
    paper_id = _digits(values.get("Nyc_SoDinhDanh"))
    if not account_name and paper_name:
        add("HoVaTenC", _upper_name(paper_name))
        add("SoDinhDanhC", paper_id)
    requester_name = account_name or paper_name
    requester_id = account_id or paper_id
    same_person = bool(
        requester_name and name and _fold(requester_name) == _fold(name)
        and not (requester_id and id_number and requester_id != id_number)
    )
    # Thông tin liên hệ trên Đơn chỉ thuộc người yêu cầu khi Đơn đúng là của tài khoản đang nộp.
    paper_is_requester = bool(paper_name) and (not account_name or _fold(paper_name) == _fold(account_name))

    relation = _clean(values.get("Nyc_QuanHe")) if paper_is_requester else ""
    if relation:
        add("QuanHe", relation)
    elif same_person:
        add("QuanHe", _SELF)
    elif name:
        warnings.append("Người yêu cầu khác người được trợ giúp pháp lý — vui lòng nhập 'Mối quan hệ với người "
                        "được trợ giúp pháp lý'.")

    paper_area = _area(values.get("Nyc_DiaChi")) if paper_is_requester else None
    if paper_area:
        add("TT_TinhThanhC", paper_area["tinh"])
        add("TT_PhuongXaC", paper_area["xa"])
        add("TT_SoNhaToDanPhoC", paper_area["diaChi"])
    elif same_person and contact:
        add("TT_TinhThanhC", contact["tinh"], default=True)
        add("TT_PhuongXaC", contact["xa"], default=True)
        add("TT_SoNhaToDanPhoC", contact["diaChi"], default=True)
    if paper_is_requester:
        add("SoDienThoai", _clean(values.get("Nyc_DienThoai")))
    elif same_person:
        add("SoDienThoai", phone, default=True)

    # ---- III. Nội dung vụ việc.
    org = _clean(values.get("YeuCau_ToChucTGPL"))
    add("KinhGui", org)
    add("ToChucTGPL_ToChucTiepNhan", org)

    # Tóm tắt trên Đơn chép nguyên văn: chỉ gom khoảng trắng, giữ dấu câu cuối (_clean cắt dấu chấm).
    summary = re.sub(r"\s+", " ", str(values.get("YeuCau_TomTat") or "")).strip()
    if not summary:
        parts = [_sentence(de_nghi)] if de_nghi else []
        if not parts and name and _proof_line(values):
            parts.append(_sentence(f"Theo {_proof_line(values)}, đề nghị trợ giúp pháp lý cho {_upper_name(name)}"))
        if stages:
            parts.append(_sentence("Đề nghị trợ giúp pháp lý ở giai đoạn: " + ", ".join(stages)))
        vu_viec = _clean(values.get("YeuCau_VuViec"))
        if vu_viec:
            parts.append(_sentence(f"Thuộc vụ án: {vu_viec}"))
        summary = " ".join(parts)
    add("VuViec_TomTatYeuCau", summary)

    form = _pick(values.get("YeuCau_HinhThuc"), _HINH_THUC)
    if form:
        add("VuViec_HinhThucTGPL", form)
    elif any(marker in _fold(stage) for stage in stages for marker in _LITIGATION_STAGES):
        # Trợ giúp ở giai đoạn điều tra/truy tố/xét xử là tham gia tố tụng; Thông báo không ghi nhãn hình thức.
        add("VuViec_HinhThucTGPL", _THAM_GIA_TO_TUNG, default=True)

    documents = []
    proof = _proof_line(values)
    if proof:
        documents.append(proof)
    if values.get("TheCCCD_SoDinhDanh") and id_number:
        documents.append(f"Bản chụp {doc_type or 'Căn cước công dân'} số {id_number}"
                         + (f" của {_title(name)}" if name else ""))
    add("VuViec_TaiLieuKemTheo", "; ".join(f"{chr(ord('a') + i)}) {d}" for i, d in enumerate(documents)))

    # Nơi, ngày làm đơn + người làm đơn (người yêu cầu).
    place = _province_of_org(org) or (contact or {}).get("tinh") or ""
    add("LamTai", place, default=True)
    add("Ngay", f"{today.day:02d}")
    add("Thang", f"{today.month:02d}")
    add("Nam", str(today.year))
    add("KyTen", _upper_name(requester_name), default=True)

    return out, warnings
