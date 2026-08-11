"""Map compact source facts → Form.io data[...] fields cho "Cấp giấy phép chặt hạ, dịch chuyển cây xanh".

- Phần I  Người nộp (flat data[...]): từ CCCD người nộp (nếu có) hoặc tài khoản (formContext).
- Phần II Chủ hồ sơ + đơn (nested data[panel][...]): kinhGui/organization/nguoiDaiDien/chucVu/identityNumber/
  address/phoneNumber.
- Phần III Bảng kê cây: datagrid data[panel][tbantest][i][stt/loaiCay/viTri/chieuCao/duongKinh/motaTinhTrang].
- Phần IV-V: data[panel][lyDoChat/viTriMoi/TinTTTe/TDTTK/kyTen].
Nút "Sao chép" là BUTTON → bỏ qua, điền Phần II trực tiếp (không có isOwnerDossier).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.process.schema import UI_COMP_BY_NAME, _MAX_CAY


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
    # Bỏ chuỗi dấu chấm điền chỗ trống trên mẫu giấy (vd "......") — đó là DẤU HIỆU Ô TRỐNG, không phải
    # dữ liệu. Cũng cắt dấu chấm/gạch thừa ở đầu-cuối. Nếu chỉ còn rỗng → None (coi như để trống).
    text = " ".join(re.sub(r"[.…]{2,}", " ", text).split()).strip(" .…:;,-")
    return text or None


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return _text(item)
    for k in keys:
        v = _text(item.get(k))
        if v:
            return v
    return None


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


def _commune_label(value: Any) -> str | None:
    return _text(value)


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


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


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


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

    # ===== Phần I: NGƯỜI NỘP HỒ SƠ (flat) =====
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    owner_name = _text(values.get("ChuHoSo_Ten"))
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner_phone = _phone(values.get("ChuHoSo_DienThoai")) or _phone(values.get("ChuHoSo_Fax"))
    # Người nộp CHÍNH LÀ chủ hồ sơ? (cùng số định danh hoặc cùng họ tên) → mượn SĐT chủ hồ sơ cho Phần I
    # (CCCD không in SĐT nhưng đơn có → tránh để trống ô SĐT bắt buộc).
    same_person = bool((nop_id and owner_id and nop_id == owner_id)
                       or (nop_name and owner_name and _fold(nop_name) == _fold(owner_name)))
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname") or ctx.get("ownerFullname"))
    ctx_id = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or ctx.get("ownerIdentityNumber"))

    add("data[chonDoiTuong]", "Cá nhân")
    if nop_name or nop_id:
        # Có CCCD người nộp riêng.
        add("data[fullname]", nop_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        nop_area = _area(values.get("NguoiNop_ThuongTru"))
        if nop_area:
            add("data[province]", _province_label(nop_area.get("tinh")))
            add("data[district]", _commune_label(nop_area.get("xa")))
            add("data[address]", _text(nop_area.get("diaChi")))
        # SĐT người nộp: CCCD không có → nếu người nộp = chủ hồ sơ, mượn SĐT chủ hồ sơ (đơn).
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")) or (owner_phone if same_person else None))
        add("data[email]", _text(values.get("NguoiNop_Email")))
    else:
        # Tự nộp: tối thiểu từ tài khoản (cổng tự đổ VNeID).
        add("data[fullname]", ctx_name)
        add("data[identityNumber]", ctx_id)

    # ===== Phần II: CHỦ HỒ SƠ + nội dung đơn (nested data[panel][...]) =====
    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người đề nghị cấp phép).")

    add("data[panel][kinhGui]", _text(values.get("ToKhai_KinhGui")))
    add("data[panel][organization]", owner_name)
    add("data[panel][nguoiDaiDien]", _text(values.get("ChuHoSo_NguoiDaiDien")))
    add("data[panel][chucVu]", _text(values.get("ChuHoSo_ChucVu")))
    add("data[panel][identityNumber]", owner_id)
    add("data[panel][address]", _text(values.get("ChuHoSo_DiaChi")))
    # SĐT chủ hồ sơ: ưu tiên 'Điện thoại'; thiếu/không đủ 10-11 số → dùng Fax (nếu Fax đạt tiêu chí SĐT).
    add("data[panel][phoneNumber]", owner_phone)

    # ===== Phần III: DATAGRID bảng kê cây xanh =====
    cay_list = values.get("BangKeCay")
    if isinstance(cay_list, dict):
        cay_list = [cay_list]
    if isinstance(cay_list, list):
        for idx, item in enumerate(cay_list[:_MAX_CAY]):
            base = f"data[panel][tbantest][{idx}]"
            add(f"{base}[stt]", _item_text(item, "stt") or f"{idx + 1:02d}")
            add(f"{base}[loaiCay]", _item_text(item, "loaiCay", "loai", "tenCay"))
            add(f"{base}[viTri]", _item_text(item, "viTri", "vitri"))
            add(f"{base}[chieuCao]", _item_text(item, "chieuCao", "cao"))
            add(f"{base}[duongKinh]", _item_text(item, "duongKinh", "dk"))
            add(f"{base}[motaTinhTrang]", _item_text(item, "moTa", "motaTinhTrang", "tinhTrang"))

    # ===== Phần IV-V: lý do / phương án / ký =====
    add("data[panel][lyDoChat]", _text(values.get("Don_LyDo")))
    # viTriMoi BẮT BUỘC trên form; đơn để trống (chỉ dấu chấm) → mặc định "Không có".
    add("data[panel][viTriMoi]", _text(values.get("Don_ViTriMoi")) or "Không có")
    dia_danh = _text(values.get("Don_DiaDanh"))
    add("data[panel][TinTTTe]", _province_label(dia_danh) if dia_danh else None)
    add("data[panel][TDTTK]", _date(values.get("Don_NgayLap")))
    add("data[panel][kyTen]", _text(values.get("Don_NguoiKy")) or owner_name)

    return out, warnings
