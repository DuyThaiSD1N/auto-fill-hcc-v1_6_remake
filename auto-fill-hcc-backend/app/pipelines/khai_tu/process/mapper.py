"""Map compact death registration facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.khai_tu.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.formatting import parse_death_time

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import remap_area


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _requester_trusted(values: dict, options: dict | None) -> bool:
    """CCCD (Cccd_*) có TRÙNG người yêu cầu cổng đã điền sẵn (VNeID) không?

    Không có mỏ neo từ cổng → tin như cũ. Có mỏ neo nhưng Cccd_* khác/thiếu → KHÔNG tin
    (CCCD đó là của người mất, không phải người yêu cầu)."""
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    applicant_name = _fold(ctx.get("applicantFullname"))
    if not applicant_id and not applicant_name:
        return True
    cccd_id = _digits(values.get("Cccd_SoDinhDanh"))
    if applicant_id and cccd_id:
        return applicant_id == cccd_id
    cccd_name = _fold(values.get("Cccd_HoTen"))
    if applicant_name and cccd_name:
        return applicant_name == cccd_name
    return False


def _ngay_sinh_nguoi_mat(value) -> str:
    """Ô 'Ngày, tháng, năm sinh' của người mất (input text): nếu nguồn có ĐỦ ngày/tháng/năm
    → điền đủ 'dd/mm/yyyy'; chỉ có năm → điền 'yyyy'."""
    text = str(value or "").strip()
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", text)
    if m:
        d, mo, y = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{y}"
    y = re.search(r"\b(\d{4})\b", text)
    return y.group(1) if y else ""


def _doc_type(so_dinh_danh, issuer: str = "") -> str:
    """Suy loại giấy tờ từ độ dài số định danh và nơi cấp.

    - 9 chữ số → CMND (Chứng minh nhân dân)
    - 12 chữ số → CCCD/Căn cước (dùng id_doc_type phân biệt Bộ Công an vs Cục Cảnh sát)
    - Khác → mặc định Căn cước công dân
    """
    digits = _digits(so_dinh_danh)
    if len(digits) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type("Thẻ căn cước công dân", issuer)


def _copy_value(value) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _positive_copy_quantity(value) -> str:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return ""
    quantity = int(match.group())
    return str(quantity) if quantity > 0 else ""


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        # xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT).
        "xa": re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", str(value.get("xa") or value.get("xã") or "").strip(), flags=re.IGNORECASE).strip(),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)



def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        out.append(field)
        seen.add(name)

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))
    has_gbt = any(
        name in values
        for name in (
            "Gbt_HoTenNguoiMat",
            "Gbt_NgayMat",
            "Gbt_GioMat",
            "Gbt_So",
            "Gbt_CoQuanCap",
        )
    )

    add("loaiDangKy", "1")

    # Người yêu cầu chỉ điền từ Cccd_* khi CCCD TRÙNG người đăng nhập (hoặc không có mỏ neo formContext).
    # Nếu CCCD upload KHÔNG trùng → đó là CCCD của NGƯỜI MẤT (dù LLM có lỡ nhét vào Cccd_*): không điền
    # danh tính người yêu cầu, chỉ đặt MẶC ĐỊNH cư trú (viền vàng), giữ tên/CCCD cổng đã điền.
    requester_trusted = _requester_trusted(values, options)
    if has_cccd and requester_trusted:
        add("HoVaTenC", values.get("Cccd_HoTen"))
        add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
        add("SoGiayToDinhDanhC", values.get("Cccd_SoDinhDanh"))
        _issuer_c = values.get("Cccd_NoiCap") or default_issuer(values.get("Cccd_NgayCap"))
        add("LoaiGiayToDinhDanhC", _doc_type(values.get("Cccd_SoDinhDanh"), _issuer_c))
        add("NgayCapDDC", values.get("Cccd_NgayCap"))
        add("NoiCapDDC", _issuer_c)
        add("nycLoaiCuTru", "Thường trú")
        area = _area(values.get("Cccd_NoiCuTru"))
        if area:
            add("nycNoiCuTru", "1")
            add("nycNoiCuTru_TrongNuoc", area)
    else:
        # Không xác định được người yêu cầu từ giấy tờ → mặc định cư trú trong nước/Việt Nam (viền vàng).
        add("nycLoaiCuTru", "Thường trú", default=True)
        add("nycNoiCuTru", "1", default=True)
        add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
    add("QuanHe", values.get("ToKhai_QuanHeNguoiYeuCau"))

    # CCCD đầu vào KHÔNG trùng người đăng nhập = CCCD của người mất → cứu danh tính sang mục II
    # (kể cả khi LLM lỡ route vào Cccd_*). Ưu tiên Gbt_* (từ giấy báo tử/tờ khai), thiếu thì lấy Cccd_*.
    cccd_is_deceased = has_cccd and not requester_trusted

    def deceased(gbt_key: str, cccd_key: str | None = None):
        val = values.get(gbt_key)
        if val in (None, "", {}, []) and cccd_is_deceased and cccd_key:
            return values.get(cccd_key)
        return val

    if has_gbt or cccd_is_deceased:
        add("HoTen", deceased("Gbt_HoTenNguoiMat", "Cccd_HoTen"))
        add("NgaySinh", _ngay_sinh_nguoi_mat(deceased("Gbt_NgaySinhNguoiMat", "Cccd_NgaySinh")))
        add("GioiTinh", deceased("Gbt_GioiTinhNguoiMat", "Cccd_GioiTinh"))
        add("nktDanToc", deceased("Gbt_DanTocNguoiMat", "Cccd_DanToc"))
        add("nktQuocTich", deceased("Gbt_QuocTichNguoiMat", "Cccd_QuocTich") or "Việt Nam")
        so_dinh_danh = deceased("Gbt_SoDinhDanhNguoiMat", "Cccd_SoDinhDanh")
        add("SoDinhDanh", so_dinh_danh)
        add("SoGiayToDinhDanh", so_dinh_danh)
        if so_dinh_danh:
            _issuer_mat = deceased("Gbt_NoiCapDDNguoiMat", "Cccd_NoiCap") or default_issuer(deceased("Gbt_NgayCapDDNguoiMat", "Cccd_NgayCap"))
            add("LoaiGiayToDinhDanh", _doc_type(so_dinh_danh, _issuer_mat))
        add("NgayCapDD", deceased("Gbt_NgayCapDDNguoiMat", "Cccd_NgayCap"))
        add("NoiCapDD", deceased("Gbt_NoiCapDDNguoiMat", "Cccd_NoiCap"))
        add("nktLoaiCuTru", "Thường trú")
        residence = _area(deceased("Gbt_NoiCuTruNguoiMat", "Cccd_NoiCuTru"))
        if residence:
            add("nktNoiCuTru", "1")
            add("nktNoiCuTru_TrongNuoc", residence)
        else:
            # Mặc định cư trú trong nước nếu không đọc được địa chỉ
            add("nktNoiCuTru", "1", default=True)
            add("nktNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

        add("NgayMat", values.get("Gbt_NgayMat"))
        death_time = parse_death_time(values.get("Gbt_GioMat"))
        add("GioMat", death_time.get("hour"))
        add("PhutMat", death_time.get("minute"))
        add("NguyenNhanMat", values.get("Gbt_NguyenNhanMat"))

        death_place = _area(values.get("Gbt_NoiChet")) or _area({
            "quocGia": "Việt Nam",
            "diaChi": values.get("Gbt_CoQuanCap"),
        })
        if death_place:
            add("nktNoiChet", "1")
            add("nktNoiChet_TrongNuoc", death_place)
        else:
            add("nktNoiChet", "1", default=True)
            add("nktNoiChet_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

        has_death_notice_metadata = bool(
            values.get("Gbt_So") or values.get("Gbt_CoQuanCap") or values.get("Gbt_NgayCap")
        )
        if has_death_notice_metadata:
            add("gbtLoai", "Giấy báo tử")
            add("gbtSo", values.get("Gbt_So"))
            add("gbtCoQuanCap", values.get("Gbt_CoQuanCap"))
            add("gbtNgay", values.get("Gbt_NgayCap"))

    # Số lượng dương vừa là bằng chứng chọn "Có", vừa được điền vào input raw SoLuong.
    # Không có số lượng thật thì không tự mặc định.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "Có")
        add("SoLuong", copy_quantity)
    else:
        add("CapBanSao", _copy_value(values.get("CopyRequest_WantsCopy")))

    return out
