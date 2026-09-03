"""Map compact facts → UI eForm Bắc Ninh (Đăng ký biện pháp bảo đảm, 1.011441).

- purpose='registration_form' (mặc định): điền Đơn Mẫu 01a theo NAME element_478xx.
- purpose='authorized_person': điền khối doiTuongKhac* của người được ủy quyền.
CHECKBOX (tư cách, loại giấy tờ pháp lý, tài sản 5.1) để USER tự tích — nhãn CMND/Mã số thuế trùng giữa
mục 3 & 4 nên không tích đúng bằng nhãn được.
"""

import re
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "chiTiet", "xa", "phuong", "huyen", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return " ".join(str(value).replace("\n", " ").split()).strip() or None


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _truthy(value: Any) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "co", "có", "1"}


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    v = _by_name(fields)
    if str((options or {}).get("purpose") or "registration_form") == "authorized_person":
        return _authorized_fields(v)
    return _registration_fields(v)


def _registration_fields(v: dict) -> list[dict]:
    ben_bao_dam_ten = _text(v.get("BenBaoDam_Ten"))
    gcn_ten = _text(v.get("Gcn_TenGiayChungNhan"))
    # (element id, giá trị). Dùng NAME element để không nhầm semantic trùng giữa các mục 1/3/4/5.
    mapping: list[tuple[str, Any]] = [
        ("element_47786", _text(v.get("Don_KinhGui"))),
        ("element_47772", _text(v.get("Don_NgayKhai"))),
        # Mục 1 — người yêu cầu đăng ký.
        ("element_47783", _text(v.get("NguoiYeuCau_TenDayDu"))),
        ("element_47782", _text(v.get("NguoiYeuCau_HoTenLienHe"))),
        ("element_47781", _text(v.get("NguoiYeuCau_DienThoai"))),
        ("element_47780", _text(v.get("NguoiYeuCau_Fax"))),
        ("element_47779", _text(v.get("NguoiYeuCau_Email"))),
        # Mục 2 — hợp đồng bảo đảm.
        ("element_47778", _text(v.get("HopDong_Ten"))),
        ("element_47777", _text(v.get("HopDong_So"))),
        ("element_47776", _text(v.get("HopDong_ThoiDiemHieuLuc"))),
        # Mục 3 — bên bảo đảm (bên thế chấp). 47775 = ô header '3. Bên bảo đảm', 47774 = ô '3.1'.
        ("element_47775", ben_bao_dam_ten),
        ("element_47774", ben_bao_dam_ten),
        ("element_47808", _text(v.get("BenBaoDam_DiaChi"))),
        ("element_47809", _text(v.get("BenBaoDam_GiayToPhapLy"))),
        ("element_47819", _text(v.get("BenBaoDam_So"))),
        ("element_47814", _issuer(v.get("BenBaoDam_CoQuanCap"))),
        ("element_47798", _text(v.get("BenBaoDam_NgayCap"))),
        ("element_47817", _text(v.get("BenBaoDam_Fax"))),
        ("element_47807", _text(v.get("BenBaoDam_Email"))),
        # Mục 4 — bên nhận bảo đảm (ngân hàng).
        ("element_47793", _text(v.get("BenNhan_Ten"))),
        ("element_47794", _text(v.get("BenNhan_DiaChi"))),
        ("element_47799", _text(v.get("BenNhan_So"))),
        ("element_47800", _text(v.get("BenNhan_CoQuanCap"))),
        ("element_47801", _text(v.get("BenNhan_DienThoai"))),
        ("element_47802", _text(v.get("BenNhan_Fax"))),
        ("element_47803", _text(v.get("BenNhan_Email"))),
        # Mục 5 — mô tả tài sản (GCN QSDĐ). 47826 = ô header '(iii)', 47825 = 'Tên Giấy chứng nhận'.
        ("element_47806", _text(v.get("Gcn_ThuaDatSo"))),
        ("element_47830", _text(v.get("Gcn_ToBanDoSo"))),
        ("element_47829", _text(v.get("Gcn_MucDichSuDung"))),
        ("element_47828", _text(v.get("Gcn_ThoiHanSuDung"))),
        ("element_47827", _text(v.get("Gcn_DiaChiThuaDat"))),
        ("element_47826", gcn_ten),
        ("element_47825", gcn_ten),
        ("element_47824", _text(v.get("Gcn_SoPhatHanh"))),
        ("element_47823", _text(v.get("Gcn_SoVaoSo"))),
        ("element_47822", _text(v.get("Gcn_CoQuanCap"))),
        ("element_47821", _text(v.get("Gcn_NgayCap"))),
    ]
    return [{"name": key, "comp": "bn-input", "value": val} for key, val in mapping if val]


def _authorized_fields(v: dict) -> list[dict]:
    if not _truthy(v.get("UyQuyen_CoVanBan")):
        return []
    name = _text(v.get("NguoiDuocUyQuyen_HoTen"))
    identity = re.sub(r"\D+", "", str(v.get("NguoiDuocUyQuyen_SoDinhDanh") or ""))
    if not name or not identity:
        return []

    out: list[dict] = []

    def add(key: str, value, comp: str = "bn-input") -> None:
        value = value if isinstance(value, dict) else _text(value)
        if value in (None, "", {}, []):
            return
        out.append({"name": key, "comp": comp, "value": value})

    add("doiTuongKhachoTen", name)
    add("doiTuongKhacgioiTinhId", v.get("NguoiDuocUyQuyen_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", identity)
    add("doiTuongKhacngayCap", v.get("NguoiDuocUyQuyen_NgayCap"))
    add("doiTuongKhacnoiCap", _issuer(v.get("NguoiDuocUyQuyen_NoiCap")))
    add("doiTuongKhacngaySinh", v.get("NguoiDuocUyQuyen_NgaySinh"))
    add("doiTuongKhacemail", v.get("NguoiDuocUyQuyen_Email"))
    add("doiTuongKhacsoDienThoai", v.get("NguoiDuocUyQuyen_SoDienThoai"))
    address = v.get("NguoiDuocUyQuyen_ThuongTru")
    if isinstance(address, dict):
        add("doiTuongKhactinhThanhId", address.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", address.get("xa"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", address.get("diaChi"))
    return out
