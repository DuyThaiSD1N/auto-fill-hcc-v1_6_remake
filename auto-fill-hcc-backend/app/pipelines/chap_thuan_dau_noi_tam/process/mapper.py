"""Map compact source facts → Form.io data[...] fields cho "Chấp thuận vị trí đấu nối tạm vào đường bộ".

- Phần I  Người nộp (flat): CCCD người nộp / tài khoản (formContext). Cá nhân hoặc Tổ chức (MST).
- Phần II Nội dung đơn (flat): đơn vị đề nghị + nội dung Đơn (đấu nối từ/vào đường, trường hợp, cam kết, ký).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.chap_thuan_dau_noi_tam.process.schema import TRUONG_HOP, UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("chiTiet"),
            value.get("xa") or value.get("phuong"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    text = " ".join(re.sub(r"[.…]{2,}", " ", text).split()).strip(" .…:;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _strip_admin_prefix(text)
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


def _area(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0").replace("S", "5"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    return normalize_date(text)


def _issuer(value: Any, ngay_cap: Any = None) -> str | None:
    text = _text(value)
    if text:
        norm = normalize_issuer(text)
        if norm:
            return norm
    return default_issuer(ngay_cap) if ngay_cap else None


def _truong_hop_case(value: Any) -> str:
    """Trả '1' (làm đường công vụ) hoặc '2' (quốc phòng/an ninh/thiên tai/đê điều). Mặc định '1'."""
    h = _fold(value)
    if "2" in h or "quoc phong" in h or "an ninh" in h or "thien tai" in h or "de dieu" in h:
        return "2"
    return "1"


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    # ===== Phần I: NGƯỜI NỘP HỒ SƠ =====
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_id = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))

    _mst_raw = _identity(values.get("NguoiNop_MaSoThue"))
    _cccd_raw = _identity(values.get("NguoiNop_SoDinhDanh"))
    # Chỉ nhận SỐ ĐỊNH DANH hợp lệ: CMND 9 / CCCD 12 số; MST 10 / 13 số. Loại số 10 chữ số kiểu SĐT (vd
    # 0901777715) mà LLM vớ nhầm từ dòng liên hệ trong Đơn.
    cccd = _cccd_raw if (_cccd_raw and len(_cccd_raw) in (9, 12)) else None
    mst = _mst_raw if (_mst_raw and len(_mst_raw) in (10, 13)) else None
    is_org = "to chuc" in _fold(values.get("NguoiNop_LoaiDoiTuong")) or bool(
        _text(values.get("NguoiNop_TenToChuc")) or mst
    )
    # Chỉ TIN thông tin nhân thân người nộp khi có giấy tờ tùy thân thật (CCCD/MST). Nếu không, người nộp =
    # tài khoản đăng nhập (formContext) — TRÁNH LLM vớ nhầm tên người ký/liên hệ trong Đơn vào Phần I.
    has_id_doc = bool(cccd or mst)
    nop_name = _text(values.get("NguoiNop_TenToChuc")) if is_org else _text(values.get("NguoiNop_HoTen"))
    nop_ngaycap = _date(values.get("NguoiNop_NgayCap"))
    tt = _area(values.get("NguoiNop_ThuongTru")) if has_id_doc else {}

    add("data[chonDoiTuong]", "Tổ chức" if is_org else "Cá nhân")
    add("data[nation]", "Việt Nam")
    add("data[fullname]", (nop_name if has_id_doc else None) or ctx_name)
    add("data[identityNumber]", (mst if is_org else cccd) or ctx_id)
    if not is_org and has_id_doc:
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", nop_ngaycap)
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap"), nop_ngaycap))
    add("data[province]", _province_label(tt.get("tinh") or tt.get("tinhThanh")))
    add("data[district]", _text(tt.get("xa") or tt.get("phuong")))
    add("data[address]", _text(tt.get("diaChi") or tt.get("chiTiet")))
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")) if has_id_doc else None)
    add("data[email]", _text(values.get("NguoiNop_Email")) if has_id_doc else None)

    # ===== Phần II: NỘI DUNG ĐƠN ĐỀ NGHỊ =====
    don_ten = _text(values.get("Don_TenToChuc"))
    if not don_ten:
        warnings.append("Thiếu tên đơn vị/tổ chức đề nghị đấu nối (Đơn đề nghị).")
    add("data[tentochucanhan]", don_ten)
    add("data[nguoidaidien]", _text(values.get("Don_NguoiDaiDien")))
    add("data[veViecDeNghiDauNoiTamTu]", _text(values.get("Don_DauNoiTamTu")))
    vao_duong = _text(values.get("Don_VaoDuong"))
    add("data[vaoDuong]", vao_duong)
    case = _truong_hop_case(values.get("Don_TruongHop"))
    add("data[truongHop]", TRUONG_HOP[case])
    add("data[cacCamKet]", _text(values.get("Don_CamKet")))
    add("data[dauNoiTam]", _text(values.get("Don_PhapLuat")))
    add("data[chuKy]", _text(values.get("Don_NguoiKy")) or _text(values.get("Don_NguoiDaiDien")))

    # ===== Panel điều kiện theo trường hợp (render sau khi chọn truongHop; FE dom-input/date có waitFor) =====
    vitri = _text(values.get("DauNoi_ViTri")) or _text(values.get("Don_DauNoiTamTu"))
    dia_ban = _text(values.get("DauNoi_DiaBan"))
    muc_dich = _text(values.get("DauNoi_MucDich"))
    tu_ngay = _date(values.get("DauNoi_TuNgay"))
    den_ngay = _date(values.get("DauNoi_DenNgay"))
    if case == "2":  # Phục vụ quốc phòng, an ninh… (phucVu) — field-key riêng, KHÔNG có ô mục đích.
        add("data[Duong]", vao_duong)
        add("data[diaBan]", dia_ban)
        add("data[TuNgay]", tu_ngay)
        add("data[DenNgay]", den_ngay)
    else:  # (1) Làm đường công vụ… (lamDuong)
        add("data[viTriDauNoiTam]", vitri)
        add("data[tenDuong]", vao_duong)
        add("data[thuocDiaban]", dia_ban)
        add("data[mucDichViecDauNoiTam]", muc_dich)
        add("data[tuNgay]", tu_ngay)
        add("data[denNgay]", den_ngay)

    return out, warnings
