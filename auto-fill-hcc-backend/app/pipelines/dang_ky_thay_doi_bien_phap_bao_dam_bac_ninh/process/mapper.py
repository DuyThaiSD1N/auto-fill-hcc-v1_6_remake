"""Map fact nguồn → ô eForm Bắc Ninh 1.011442 (Phiếu 02a) và khối doiTuongKhac* (bên ủy quyền).

- ``enrich``: thân Phiếu theo class eform-element-<Key> (Mapping_Don_dang_ky.xlsx 12/11/2026).
- ``enrich_authorized``: khối "Thông tin trong trường hợp được ủy quyền" theo loại bên ủy quyền
  (Mapping_Nguoi_uy_quyen.xlsx: Doanh nghiệp / Tổ chức / Cá nhân khác — mỗi loại cổng nạp bộ ô riêng).
"""

import re
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer

from . import schema as S


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("chiTietDuoiXa", "diaChi", "chiTiet", "xa", "phuong", "huyen", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return " ".join(str(value).split()).strip(" ,;") or None


def _lines(value: Any) -> str | None:
    """Giữ xuống dòng (mục 3, mục 5 chép nguyên văn nhiều dòng); bỏ dòng chỉ có dấu chấm giữ chỗ."""
    if value in (None, "", {}, []):
        return None
    rows = [" ".join(line.split()) for line in str(value).replace("\\n", "\n").splitlines()]
    rows = [r for r in rows if r and not re.fullmatch(r"[.…\s:]*", r)]
    return "\n".join(rows) or None


def _digits(value: Any) -> str | None:
    return re.sub(r"\D+", "", str(value or "")) or None


def _truthy(value: Any) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "co", "có", "1"}


def _fold(text: str) -> str:
    import unicodedata

    t = str(text or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").lower().split())


# ── Vá từ OCR (compact_field_fallback) ──
# Mục 1 Phiếu thường viết tay → OCR méo số nhà / mất "Phường" (bộ mẫu 12/11: Phiếu đọc "282 đường Hoà Cường", HĐ sửa
# đổi đánh máy "228 đường 2/9, Phường Hòa Cường, Thành phố Đà Nẵng"). Hợp đồng sửa đổi ghi lại trụ sở của CÙNG chủ thể
# → lấy bản đánh máy. Chỉ đọc trong HĐ SỬA ĐỔI (HĐ thế chấp gốc ghi trụ sở CŨ của bên nhận trước khi đổi tên).
# Tiêu đề / đầu khối các bên viết IN HOA ở đầu dòng — thân Phiếu cũng nhắc "Hợp đồng Sửa đổi…", "Bên nhận thế chấp".
_SUA_DOI_RE = re.compile(r"(?m)^[\s*#]*HỢP\s+ĐỒNG\s+SỬA\s+ĐỔI")
_PARTY_RE = {
    "nhan": re.compile(r"(?m)^[\s\d.*#-]*BÊN\s+NHẬN\s+THẾ\s+CHẤP[^\n]*\n"),
    "the_chap": re.compile(r"(?m)^[\s\d.*#-]*BÊN\s+THẾ\s+CHẤP[^\n]*\n"),
}
_TRU_SO_RE = re.compile(r"Địa\s*chỉ(?:\s*trụ\s*sở(?:\s*chính)?)?\s*:\s*([^\n]+)", re.IGNORECASE)


def _as_dict(raw_fields) -> dict:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {f.get("name"): f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    return {}


def _name_core(name: str) -> str:
    """Phần đuôi đặc trưng của tên chủ thể (vd "chi nhanh kinh bac"); bỏ ngoặc như "(AGRIBANK)"."""
    words = _fold(re.sub(r"\([^)]*\)", " ", name or "")).replace("-", " ").replace("–", " ").split()
    return " ".join(words[-4:])


def contract_address(text: str, requester: str, party: str) -> str | None:
    """Địa chỉ trụ sở của bên ``party`` ("nhan" | "the_chap") trong Hợp đồng sửa đổi, khi tên bên đó khớp người yêu
    cầu; không chắc → None."""
    title = _SUA_DOI_RE.search(text or "")
    core = _name_core(requester)
    if not title or len(core.split()) < 3:
        return None
    window = text[title.end(): title.end() + 6000]
    stop = re.search(r"LỜI\s+CHỨNG", window, re.IGNORECASE)
    window = window[: stop.start()] if stop else window
    header = _PARTY_RE[party].search(window)
    if not header:
        return None
    block = window[header.end(): header.end() + 700]
    name_line = block.strip().split("\n", 1)[0]
    if core not in _fold(name_line).replace("-", " ").replace("–", " "):
        return None
    found = _TRU_SO_RE.search(block)
    value = " ".join(found.group(1).split()).strip(" .;,") if found else ""
    return value or None


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(str(d.get("text") or "") for d in documents or [])
    requester = str(fields.get("NguoiYeuCau_TenDayDu") or "")
    party = "the_chap" if _tu_cach(fields.get("NguoiYeuCau_TuCach")) == "Bên bảo đảm" else "nhan"
    address = contract_address(text, requester, party)
    if address:
        fields["NguoiYeuCau_DiaChi"] = address
    return fields


# Mục 1 — nhãn radio trên eForm (mapping: "Bên nhận bảo đảm (1) | Bên bảo đảm (2) | Bên kế thừa … (3) | Quản tài
# viên/Doanh nghiệp quản lý, thanh lý tài sản (4) | Chi nhánh của pháp nhân, người đại diện (5)"). "Bên bảo đảm" là chuỗi
# con của "Bên kế thừa bên bảo đảm…" → xét các lựa chọn dài trước.
def _tu_cach(raw: Any) -> str | None:
    h = _fold(raw)
    if not h:
        return None
    if "ke thua" in h:
        return "Bên kế thừa bên bảo đảm, bên nhận bảo đảm"
    if "quan tai vien" in h or "thanh ly tai san" in h:
        return "Quản tài viên"
    if "chi nhanh" in h or "dai dien" in h:
        return "Chi nhánh của pháp nhân, người đại diện"
    if "nhan bao dam" in h or "nhan the chap" in h:
        return "Bên nhận bảo đảm"
    if "bao dam" in h or "the chap" in h:
        return "Bên bảo đảm"
    return None


# Mục 6 — nhãn 4 checkbox trên eForm.
_CACH_NHAN = (
    ("buu chinh", "Nhận qua dịch vụ bưu chính"),
    ("dien tu", "Cách thức điện tử"),
    ("cach thuc khac", "Cách thức khác"),
    ("truc tiep", "Nhận trực tiếp tại cơ quan đăng ký"),
)


def _cach_nhan(raw: Any) -> str:
    h = _fold(raw)
    return next((label for key, label in _CACH_NHAN if key in h), "Nhận trực tiếp tại cơ quan đăng ký")


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    v = _by_name(fields)
    out: list[dict] = []

    def add(name: str, value) -> None:
        if value in (None, "", {}, []):
            return
        out.append({"name": name, "comp": S.UI_COMP_BY_NAME[name], "value": value})

    add(S.K_NOIKHAI, _text(v.get("Don_NoiKhai")))
    add(S.K_NGAYKHAI, _text(v.get("Don_NgayKhai")))
    kinh_gui = _text(v.get("Don_KinhGui"))
    add(S.K_KINHGUI, re.sub(r"\(\s*\d+\s*\)\s*$", "", kinh_gui).strip() if kinh_gui else None)

    tu_cach = _tu_cach(v.get("NguoiYeuCau_TuCach"))
    add(S.K_TUCACH, [tu_cach] if tu_cach else None)
    ten = _text(v.get("NguoiYeuCau_TenDayDu"))
    add(S.K_TENDAYDU, ten.upper() if ten else None)
    add(S.K_DIACHI, _text(v.get("NguoiYeuCau_DiaChi")))
    add(S.K_HOTEN, _text(v.get("NguoiYeuCau_HoTenLienHe")))
    add(S.K_SDT, _digits(v.get("NguoiYeuCau_DienThoai")))
    add(S.K_FAX, _digits(v.get("NguoiYeuCau_Fax")))
    add(S.K_EMAIL, _text(v.get("NguoiYeuCau_Email")))

    add(S.K_TENVANBAN, _text(v.get("VanBan_Ten")))
    # Ô "Số: (nếu có)" là input number số nguyên: số hợp đồng có chữ / "/" (vd "12/2026/HĐ") gõ vào thành dãy số
    # sai → chỉ điền khi số toàn chữ số; số đầy đủ đã nằm ở ô "Tên văn bản".
    so = re.sub(r"\s+", "", str(v.get("VanBan_So") or ""))
    add(S.K_SO, so if so.isdigit() else None)
    add(S.K_THOIDIEM, _text(v.get("VanBan_ThoiDiem")))

    add(S.K_NOIDUNG, _lines(v.get("NoiDungThayDoi")))
    # Radio đơn: tick rồi không bỏ được trên giao diện → chỉ phát khi Phiếu đánh dấu rõ.
    add(S.K_KHONGPHI, ["Thuộc đối tượng không phải nộp phí đăng ký"] if _truthy(v.get("KhongNopPhi")) else None)
    add(S.K_KEMTHEO, _lines(v.get("GiayToKemTheo")))

    cach_nhan = _cach_nhan(v.get("CachThucNhan"))
    add(S.K_CACHNHAN, [cach_nhan])
    if cach_nhan != "Nhận trực tiếp tại cơ quan đăng ký":
        add(S.K_CACHNHAN_GHIRO, _lines(v.get("CachThucNhan_GhiRo")))
    else:
        # Tab "Thông tin đăng ký nhận kết quả": nhận trực tiếp ⇔ "Tại nơi nộp hồ sơ (theo giấy hẹn trả)".
        add(S.K_NOINHAN, ["Tại nơi nộp hồ sơ"])
    return out


# ── Khối người ủy quyền ──

AUTHORIZED_SUBJECTS = (
    "Doanh nghiệp", "Tổ chức", "Cá nhân khác là Công dân Việt Nam", "Người nước ngoài", "Hộ kinh doanh cá thể",
)
DEFAULT_SUBJECT = "Doanh nghiệp"  # bên ủy quyền thường là ngân hàng cấp Giấy giới thiệu
_PERSON_SUBJECTS = {"Cá nhân khác là Công dân Việt Nam", "Người nước ngoài"}


def _subject(v: dict) -> str | None:
    text = _fold(v.get("NguoiUyQuyen_Loai"))
    return next((s for s in AUTHORIZED_SUBJECTS if text and text == _fold(s)), None)


def authorized_subject(fields: list[dict]) -> str | None:
    """Loại "Người ủy quyền là:" đọc được từ hồ sơ; None → lời gọi dùng loại mặc định của thủ tục."""
    v = _by_name(fields)
    return _subject(v) if _truthy(v.get("UyQuyen_CoVanBan")) else None


def enrich_authorized(fields: list[dict]) -> tuple[list[dict], list[str]]:
    """Ô doiTuongKhac* của bên ủy quyền. Ô cá nhân (giới tính, ngày sinh, nơi cấp) chỉ có ở loại cá nhân."""
    v = _by_name(fields)
    if not _truthy(v.get("UyQuyen_CoVanBan")):
        return [], ["Không thấy Giấy giới thiệu / văn bản ủy quyền trong hồ sơ — không điền khối người ủy quyền."]
    name = _text(v.get("NguoiUyQuyen_Ten"))
    identity = re.sub(r"[^0-9A-Za-z-]+", "", str(v.get("NguoiUyQuyen_SoDinhDanh") or "")).strip("-")
    warnings: list[str] = []
    if not name:
        return [], ["Không đọc được tên bên ủy quyền."]
    if not identity:
        warnings.append("Không đọc được số định danh / số đăng ký của bên ủy quyền — nhập tay ô này.")
    person = (_subject(v) or DEFAULT_SUBJECT) in _PERSON_SUBJECTS

    out: list[dict] = []

    def add(key: str, value, comp: str = "bn-input") -> None:
        value = value if isinstance(value, dict) else _text(value)
        if value in (None, "", {}, []):
            return
        out.append({"name": key, "comp": comp, "value": value})

    add("doiTuongKhachoTen", name.upper() if not person else name)
    if person:
        add("doiTuongKhacgioiTinhId", v.get("NguoiUyQuyen_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", identity)
    add("doiTuongKhacngayCap", v.get("NguoiUyQuyen_NgayCap"))
    if person:
        add("doiTuongKhacnoiCap", normalize_issuer(_text(v.get("NguoiUyQuyen_NoiCap")) or "") or None)
        add("doiTuongKhacngaySinh", v.get("NguoiUyQuyen_NgaySinh"))
    add("doiTuongKhacemail", v.get("NguoiUyQuyen_Email"))
    add("doiTuongKhacsoDienThoai", _digits(v.get("NguoiUyQuyen_SoDienThoai")))
    address = v.get("NguoiUyQuyen_DiaChi")
    if isinstance(address, dict):
        # Tỉnh trước Xã: select2 Xã nạp theo Tỉnh.
        add("doiTuongKhactinhThanhId", address.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", address.get("xa"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", address.get("chiTietDuoiXa") or address.get("diaChi"))
    elif address:
        add("doiTuongKhacdiaChiChiTiet", address)
    return out, warnings
