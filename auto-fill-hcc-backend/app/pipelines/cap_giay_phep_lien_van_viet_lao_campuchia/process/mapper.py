"""Map compact facts → Form.io data[...] cho "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877).

Theo Mapping_GP_lien_van_VN-Lao-Campuchia.xlsx:
  Phần I  (data[...] phẳng)               — người nộp: "Chọn đối tượng" theo Giấy đề nghị mục 1 (CÔNG TY… → Tổ chức, khi đó
                                            Họ tên = tên tổ chức, ô CCCD/CMND/MST nhận MST); địa chỉ mục 2 quy đổi địa giới mới.
  Phần II (data[panel_caNhanToChuc][...]) — dịch vụ (8 option mang mã [1.002877.A1..B4]), kính gửi, mục đích chuyến đi
                                            (đúng 1 ô), tại, người ký (khối ký cuối; thiếu thì tên người nộp).
  Datagrid DanhSachPhuongTien             — comp dom-vehicle-add (FE chung với bản Việt – Lào).
Helper chuẩn hoá (định danh, SĐT, ngày, biển số, danh sách xe…) dùng lại của `cap_giay_phep_lien_van_viet_lao`.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process.mapper import (
    _area,
    _date,
    _fold,
    _identity,
    _issuer,
    _phone,
    _strip_admin_prefix,
    _text,
    _vehicles,
)
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.process.schema import UI_COMP_BY_NAME

PANEL = "data[panel_caNhanToChuc]"

# 8 option "Dịch vụ" đúng như cổng (mapping STT 20). LLM chọn 1 mã ngắn → mapper trả nguyên văn option.
DICH_VU: dict[str, str] = {
    "ptm_moi": "Cấp Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện phi thương mại [1.002877.B1]",
    "ptm_huhong": "Cấp lại Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện phi thương mại do hư hỏng "
                  "[1.002877.B2]",
    "ptm_matmat": "Cấp lại Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện phi thương mại do mất mát "
                  "[1.002877.B3]",
    "ptm_hethan": "Cấp lại Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện phi thương mại do hết hạn "
                  "[1.002877.B4]",
    "tm_moi": "Cấp Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện thương mại [1.002877.A1]",
    "tm_hethan": "Cấp lại Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện thương mại do hết hạn "
                 "[1.002877.A2]",
    "tm_huhong": "Cấp lại Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện thương mại do hư hỏng "
                 "[1.002877.A3]",
    "tm_matmat": "Cấp lại Giấy phép liên vận Việt Nam - Campuchia - Lào cho phương tiện thương mại do mất mát "
                 "[1.002877.A4]",
}

# 34 option Tỉnh/TP của cổng: các đơn vị mang chữ "Thành phố" (mapping STT 15/49 — có cả Đồng Nai).
_CITIES = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue", "bac ninh", "quang ninh", "dong nai"}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def province_label(value: Any) -> str | None:
    """Tên tỉnh (có thể là tỉnh cũ) → option cổng "Thành phố X" / "Tỉnh X"."""
    text = _text(value)
    if not text:
        return None
    text = (remap_area({"tinh": text, "xa": "", "diaChi": ""}) or {}).get("tinh") or text
    bare = _strip_admin_prefix(re.sub(r"^\s*(tp\.?\s*|thành phố\s+)", "", text, flags=re.IGNORECASE))
    folded = _fold(bare)
    if folded in ("tp ho chi minh", "thanh pho ho chi minh"):
        bare, folded = "Hồ Chí Minh", "ho chi minh"
    return f"{'Thành phố' if folded in _CITIES else 'Tỉnh'} {bare}"


def residence(value: Any) -> dict:
    """Địa chỉ mục 2 (object hoặc chuỗi) → {tinh, xa, diaChi} địa giới mới. Chuỗi bỏ đuôi ", Việt Nam" trước khi tách."""
    if isinstance(value, str):
        value = re.sub(r"[,\s]*(Việt Nam|Viet Nam)\s*\.?\s*$", "", value, flags=re.IGNORECASE)
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value["chiTietDuoiXa"]}
    return _area(value) or {}


def kinh_gui(value: Any) -> str | None:
    """'Sở Xây dựng thành phố Đà Nẵng' → option 'Sở Xây dựng TP Đà Nẵng'; 'Sở Xây dựng tỉnh X' giữ 'tỉnh'. Đơn mẫu cũ ghi
    'Sở Giao thông vận tải' (nay nhập vào Sở Xây dựng) / tỉnh cũ → đổi theo địa giới mới."""
    text = _text(value)
    if not text:
        return None
    m = re.match(r"^\s*sở\s+(xây dựng|giao thông vận tải|gtvt)\s*(.*)$", text, flags=re.IGNORECASE)
    if not m or not m.group(2).strip():
        return text
    label = province_label(m.group(2)) or ""
    return "Sở Xây dựng " + re.sub(r"^Thành phố\b", "TP", re.sub(r"^Tỉnh\b", "tỉnh", label))


def dich_vu(value: Any) -> str | None:
    """Mã ngắn (ptm_moi…) hoặc mô tả tự do → option cổng; mô tả thì suy theo 'phi thương mại' + lý do cấp lại."""
    raw = _text(value)
    if not raw:
        return None
    folded = _fold(raw)
    code = folded.replace("-", "_").replace(" ", "_")
    if code in DICH_VU:
        return DICH_VU[code]
    for key in DICH_VU:
        if key in code and not (key.startswith("tm_") and f"p{key}" in code):
            return DICH_VU[key]
    match = re.search(r"1\.002877\.?([ab])([1-4])", folded)
    if match:
        return next(v for v in DICH_VU.values() if f"[1.002877.{match.group(1).upper()}{match.group(2)}]" in v)
    prefix = "ptm_" if "phi thuong mai" in folded else "tm_"
    if "het han" in folded:
        reason = "hethan"
    elif "hu hong" in folded or "hu hai" in folded:
        reason = "huhong"
    elif "mat mat" in folded or "bi mat" in folded:
        reason = "matmat"
    else:
        reason = "moi"  # "Cấp, cấp lại" không nêu lý do → cấp mới (mapping STT 20).
    return DICH_VU[prefix + reason]


def muc_dich_key(value: Any) -> str | None:
    """Nhãn mục 6 → checkbox. c) trên đơn ghi "Phục vụ hoạt động của tổ chức/cá nhân" (có chữ "cá nhân") → xét trước b)."""
    folded = _fold(value)
    if not folded:
        return None
    if "cong vu" in folded:
        return "mucdich_01"
    if "phuc vu" in folded or "kinh doanh" in folded or "hoat dong" in folded:
        return "mucdich_03"
    if "ca nhan" in folded:
        return "mucdich_02"
    return "mucdich_04"


def signer(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^(giám đốc|phó giám đốc|tổng giám đốc|chủ tịch( hđqt)?|chủ nhiệm|thủ trưởng)\s*[:\-]?\s*", "", text,
                  flags=re.IGNORECASE).strip()
    return text or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        comp = UI_COMP_BY_NAME.get(name)
        if name in seen or value in (None, "", {}, []) or not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def put(name: str, value) -> None:
        """Ô Phần I cổng đổ sẵn theo chủ tài khoản VNeID: giấy tờ không có thì XÓA TRẮNG ô input/date."""
        if value not in (None, "", {}, []):
            add(name, value)
            return
        comp = UI_COMP_BY_NAME.get(name)
        if name not in seen and comp in ("dom-input", "dom-date"):
            out.append({"name": name, "comp": comp, "value": "", "clear": True})
            seen.add(name)

    # --- Phần I: người nộp ---
    name = _text(values.get("NguoiNop_HoTen"))
    is_org = "to chuc" in _fold(values.get("NguoiNop_LoaiDoiTuong"))
    raw_identity = _text(values.get("NguoiNop_SoDinhDanh"))
    identity = _identity(raw_identity)
    if is_org and identity and len(identity) not in (10, 13):
        identity = None  # tổ chức: ô CCCD/CMND/MST nhận mã số thuế, số CCCD của giám đốc không phải số của đơn vị.
    area = residence(values.get("NguoiNop_ThuongTru"))

    if not name:
        warnings.append("Thiếu tên người nộp (Giấy đề nghị mục 1 / CCCD).")
    if is_org and not identity:
        warnings.append("Người nộp là tổ chức — nhập mã số doanh nghiệp/mã số thuế vào ô CCCD/CMND/MST và kiểm tra khối "
                        "thông tin doanh nghiệp.")
    elif raw_identity and not identity:
        warnings.append(f"Số định danh đọc được '{raw_identity}' không phải số CCCD/CMND/MST hợp lệ — đã để trống.")
    elif not identity:
        warnings.append("Hồ sơ không có CCCD người nộp — đã để trống số CCCD, ngày sinh, ngày cấp; vui lòng nhập tay.")

    add("data[chonDoiTuong]", "Tổ chức" if is_org else "Cá nhân")
    put("data[fullname]", name)
    put("data[birthday]", None if is_org else _date(values.get("NguoiNop_NgaySinh")))
    if not is_org:
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
    put("data[identityNumber]", identity)
    put("data[identityDate]", None if is_org else _date(values.get("NguoiNop_NgayCapCccd")))
    if not is_org:
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCapCccd")))
    add("data[nation]", _text(values.get("NguoiNop_QuocTich")) or ("Việt Nam" if name else None))
    add("data[province]", province_label(area.get("tinh")))
    add("data[district]", _text(area.get("xa")))
    put("data[address]", _text(area.get("diaChi")))
    put("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    put("data[email]", _text(values.get("NguoiNop_Email")))

    # --- Phần II: nội dung Giấy đề nghị ---
    add(f"{PANEL}[dichVu]", dich_vu(values.get("DeNghi_DichVu")))
    add(f"{PANEL}[T_CoQuan]", kinh_gui(values.get("DeNghi_KinhGui")))
    purpose = muc_dich_key(values.get("DeNghi_MucDich"))
    if purpose:
        add(f"{PANEL}[{purpose}]", True)
    elif name:
        warnings.append("Chưa đọc được ô đánh dấu ở mục 6 Mục đích chuyến đi — vui lòng tích tay theo Giấy đề nghị.")
    add(f"{PANEL}[TinTTTe]", province_label(values.get("DeNghi_Tai")))
    add(f"{PANEL}[nguoiLamDon]", signer(values.get("DeNghi_NguoiKy")) or name)

    # --- Danh sách phương tiện: FE chọn biển số có trong tài khoản + "Thêm", không có thì "Thêm mới" rồi điền dòng ---
    vehicles = _vehicles(values.get("DeNghi_PhuongTien"))
    if vehicles:
        out.append({
            "name": f"{PANEL}[BienSoXeData]",
            "comp": "dom-vehicle-add",
            "value": json.dumps(vehicles, ensure_ascii=False),
            "addButtonName": f"{PANEL}[themxe]",
        })
    else:
        warnings.append("Chưa đọc được bảng phương tiện (Giấy đề nghị mục 5) — vui lòng chọn biển số và bấm Thêm mới.")

    return out, warnings
