"""Map facts nguồn sang Form.io của cổng DVC Quảng Ngãi (đăng ký đất đai, cấp GCN lần đầu)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME

# Bảng thành phần hồ sơ (20 dòng) KHÔNG có dòng riêng cho CCCD/căn cước, giấy xác nhận số định danh
# (CMND 9 số ↔ CCCD là một người) hay tờ khai thuế/lệ phí đứng riêng -> planner gom chúng vào dòng
# "Đơn đăng ký đất đai" (CCCD, giấy xác nhận định danh) và dòng "Chứng từ thực hiện nghĩa vụ tài
# chính" (tờ khai thuế). Ghi chú này để cán bộ tiếp nhận biết chỗ tìm trong file PDF gộp.

def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" ,;:")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", (_text(value) or "").upper().replace("O", "0"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.fullmatch(r"\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*", text)
    return normalize_date(match.group(0).replace("-", "/")) if match else None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    return remap_area(area) if any(area.values()) else None


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    return province_label(bare)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    applicant_name = _text(values.get("NguoiNop_HoTen")) or owner_name
    # Tên chủ hồ sơ khác tên người nộp => hồ sơ có ủy quyền/đại diện (cổng Quảng Ngãi KHÔNG có ô
    # checkbox "người nộp là chủ hồ sơ" nên đây là tín hiệu duy nhất).
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))

    # KHÁC hẳn cổng Ninh Bình cùng tên thủ tục: form Quảng Ngãi KHÔNG có khối riêng cho người nộp.
    # Panel "Thông tin chung" (ngày sinh, giới tính, email, số điện thoại, số định danh, ngày/nơi cấp,
    # địa chỉ) đều là thông tin CHỦ HỒ SƠ — nhãn đầu panel ghi rõ "Thông tin chủ hồ sơ". Về người nộp
    # chỉ có đúng 2 ô: "Họ và tên người nộp hồ sơ" (data[fullname]) và "Số điện thoại ủy quyền"
    # (data[phoneNumber1]). Vì vậy KHÔNG được đổi nguồn khối này sang NguoiNop_* khi có ủy quyền —
    # làm thế là ghi nhân thân người được ủy quyền vào ô của chủ hồ sơ.
    def owner_val(key: str):
        """Fact của CHỦ HỒ SƠ; khi KHÔNG ủy quyền thì hai vai là một người nên NguoiNop_* dùng thay được."""
        value = values.get(f"ChuHoSo_{key}")
        if value in (None, "", {}, []) and not authorized:
            value = values.get(f"NguoiNop_{key}")
        return value

    # ĐỊA CHỈ — ưu tiên TẤT ĐỊNH địa chỉ người dân tự khai trên ĐƠN (field nguồn riêng, LLM chỉ được
    # lấy từ đơn). Không ủy quyền thì NguoiNop_DonDiaChi cũng là của chính chủ hồ sơ nên dùng thay được.
    # Chỉ khi đơn không ghi mới rơi về nơi cư trú suy từ giấy tờ tùy thân: CCCD hay ghi nơi thường trú
    # CŨ/khác tỉnh nên tuyệt đối không để nó ghi đè địa chỉ trên đơn.
    owner_area = (
        _area(values.get("ChuHoSo_DonDiaChi"))
        or (None if authorized else _area(values.get("NguoiNop_DonDiaChi")))
        or _area(owner_val("NoiCuTru"))
    )
    owner_id = _identity(owner_val("SoDinhDanh"))

    add("data[ownerFullname]", owner_name)
    add("data[fullname]", applicant_name)
    add("data[birthday]", _date(owner_val("NgaySinh")))
    add("data[gender]", _text(owner_val("GioiTinh")))
    add("data[identityNumber]", owner_id)
    add("data[identityDate]", _date(owner_val("NgayCap")))
    issuer = _text(owner_val("NoiCap"))
    add("data[identityAgency]", normalize_issuer(issuer) if issuer else None)
    add("data[phoneNumber]", _phone(owner_val("DienThoai")))
    add("data[email]", _text(owner_val("Email")))
    # Ô "Số điện thoại ủy quyền" = số của người trực tiếp đi nộp. Có ủy quyền -> số BÊN ĐƯỢC ỦY QUYỀN;
    # KHÔNG ủy quyền -> người nộp CHÍNH LÀ chủ hồ sơ nên dùng luôn số chủ hồ sơ (đây là suy luận tất
    # định từ chính vai, không phải mượn số của người khác).
    # Ô "Số điện thoại ủy quyền" CHỈ có nghĩa khi NGƯỜI NỘP KHÁC CHỦ HỒ SƠ (hồ sơ có ủy quyền): điền
    # số của người nộp. Hai vai là MỘT người thì để TRỐNG — không fallback số chủ hồ sơ, vì lúc đó
    # không tồn tại việc ủy quyền nào để mà ghi số.
    if authorized:
        add("data[phoneNumber1]", _phone(values.get("NguoiNop_DienThoai")))
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    # Địa chỉ trong panel "Thông tin chung" cũng là nơi cư trú CHỦ HỒ SƠ (xem giải thích ở trên).
    add("data[nation]", owner_area.get("quocGia") if owner_area else "Việt Nam", default=True)
    if owner_area:
        add("data[province]", _province_label(owner_area.get("tinh")))
        # Nhãn form là "Phường/xã" nhưng field-key là district (mô hình hành chính 2 cấp).
        add("data[district]", _text(owner_area.get("xa")))
        add("data[address]", _text(owner_area.get("diaChi")))
    add("data[noidungyeucaugiaiquyet]", _text(values.get("Don_NoiDungDangKy")))

    # KHỐI THỬA ĐẤT (data[diaChiThuaDat]/province2/village2/nation2) là ĐỊA ĐIỂM THỬA ĐẤT đăng ký,
    # tách hẳn khối địa chỉ cư trú ở trên. Chỉ phát khi đọc được nguồn riêng ThuaDat_DiaChi — KHÔNG
    # bao giờ lấy owner_area thay thế, vì nơi ở và thửa đất thường khác nhau.
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    if parcel_area:
        add("data[diaChiThuaDat]", _text(parcel_area.get("diaChi")))
        add("data[province2]", _province_label(parcel_area.get("tinh")))
        add("data[village2]", _text(parcel_area.get("xa")))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam", default=True)


    return out, []
