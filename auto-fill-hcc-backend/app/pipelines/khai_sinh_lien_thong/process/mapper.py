"""Map compact OCR-derived birth registration facts to Angular UI fields."""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.ethnic_normalize import normalize_ethnic
from app.pipelines._shared.hospital_lookup import lookup_hospital
from app.pipelines.khai_sinh_lien_thong.process.schema import STATIC_DEFAULTS, UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value) -> str:
    """Bỏ dấu + lowercase để so khớp bất chấp OCR hoa/thường/dấu (kể cả đ→d)."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower().strip()


def _first_token(full_name) -> str:
    parts = [p for p in str(full_name or "").split() if p]
    return parts[0] if parts else ""


def _norm_birth_place(area):
    """Nơi sinh là cơ sở y tế tuyến tỉnh (vd "Bệnh viện đa khoa TỈNH") mà OCR ghi tắt, thiếu tên
    tỉnh → nối tên tỉnh vào chi tiết để ra "Bệnh viện đa khoa tỉnh <Tỉnh>"."""
    if not isinstance(area, dict):
        return area
    tinh = area.get("tinh") or area.get("tỉnh")
    dia = str(area.get("diaChi") or area.get("dia_chi") or area.get("diachi") or "").strip()
    xa = area.get("xa") or area.get("xã")
    if not (tinh and dia):
        return area
    out = dict(area)
    low = _fold(dia)
    is_facility = any(k in low for k in ("benh vien", "trung tam y te", "tram y te", "phong kham", "nha ho sinh"))
    if is_facility and _fold(tinh) not in low and re.search(r"(tinh|thanh pho)$", low):
        dia = f"{dia} {tinh}"
        out["diaChi"] = dia
    # Bệnh viện đa khoa TỈNH LAI CHÂU đặt trụ sở tại phường/xã Tân Phong → điền xã khi OCR thiếu
    # (few-shot prompt hay bỏ sót). Chỉ áp cho bệnh viện tuyến tỉnh của Lai Châu.
    combined = _fold(f"{dia} {tinh}")
    if not xa and "benh vien da khoa tinh" in combined and "lai chau" in combined:
        out["xa"] = "Tân Phong"
    return out


def _is_birth_cert_serial(value) -> bool:
    """Số giấy chứng sinh (vd "01327.GCS.12096.25") — KHÔNG phải số giấy CN kết hôn."""
    text = str(value or "").upper()
    return "GCS" in text or "CHUNG SINH" in text or "CHỨNG SINH" in text


def _clean_phone(value) -> str:
    """Chuẩn hóa SĐT VN: sửa lỗi OCR, khôi phục số 0 đứng đầu cho di động."""
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    text = text.translate(str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "I": "1", "l": "1"}))
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8:
        return ""
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    elif len(digits) == 9 and digits[0] in "35789":
        digits = "0" + digits
    # Chỉ điền khi là SĐT VN hợp lệ (10-11 số, bắt đầu bằng 0); tránh điền số rác do OCR mờ.
    return digits if len(digits) in (10, 11) and digits.startswith("0") else ""


def _positive_copy_quantity(value) -> str:
    """Chỉ nhận số lượng bản sao thật, dương; không có số thì để trống."""
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return ""
    quantity = int(match.group())
    return str(quantity) if quantity > 0 else ""


def _split_name(full_name: str | None) -> tuple[str, str, str]:
    parts = [p for p in str(full_name or "").split() if p]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return "", "", parts[0]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _clean_child_name(value, mother_name) -> str:
    """Chặn placeholder và lỗi LLM copy tên mẹ khi giấy chứng sinh chưa đặt tên trẻ."""
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if re.fullmatch(r"[/\\|._\-\s]+", text):
        return ""
    folded = re.sub(r"\s+", " ", _fold(text))
    if folded in {
        "chua dat ten",
        "chua co ten",
        "chua dat",
        "khong co ten",
    }:
        return ""
    mother_folded = re.sub(r"\s+", " ", _fold(mother_name))
    if mother_folded and folded == mother_folded:
        return ""
    return text


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


# Đổi tên tỉnh/thành theo sắp xếp đơn vị hành chính 2025: giấy tờ cũ ghi tên CŨ → chuẩn hóa tên MỚI.
_TINH_RENAME = {
    "thua thien hue": "Huế",
}


def _norm_tinh(value):
    """Chuẩn hóa tên tỉnh về đơn vị hành chính hiện hành (vd 'Thừa Thiên Huế' → 'Huế')."""
    if not value:
        return value
    return _TINH_RENAME.get(_fold(value), value)


def _area(value):
    if not isinstance(value, dict):
        return None
    xa = _strip_admin_prefix(value.get("xa") or value.get("xã"))
    dia = value.get("diaChi") or value.get("dia_chi") or value.get("diachi")
    # diaChi chỉ là phần CHI TIẾT (bản/tổ/thôn/số nhà). Nếu nó chính là tên xã/phường
    # (vd "Phường Tân Phong" trong khi xa="Tân Phong") → trùng lặp vô nghĩa, bỏ đi.
    if dia and _strip_admin_prefix(dia).strip().lower() == (xa or "").strip().lower():
        dia = None
    out = {"tinh": _norm_tinh(value.get("tinh") or value.get("tỉnh")), "xa": xa, "diaChi": dia}
    out = {k: v for k, v in out.items() if v not in (None, "", {}, [])}
    # Áp dụng remap địa chỉ để chuẩn hóa xã/phường theo sáp nhập đơn vị hành chính
    return remap_area(out) if out else None


def enrich(fields: list[dict]) -> list[dict]:
    """Derive deterministic Angular form fields from compact source facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
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

    def add_name(prefix: str, full_name: str | None) -> None:
        ho, chu_dem, ten = _split_name(full_name)
        add(f"{prefix}Ho" if prefix else "Ho", ho)
        add(f"{prefix}ChuDem" if prefix else "ChuDem", chu_dem)
        add(f"{prefix}Ten" if prefix else "Ten", ten)

    child_name = _clean_child_name(
        values.get("Gcs_HoTenCon"),
        values.get("CccdNu_HoTen"),
    )
    has_child = bool(child_name) or any(
        name in values
        for name in (
            "Gcs_NgaySinhCon",
            "Gcs_GioiTinhCon",
            "Gcs_DanTocCon",
            "Gcs_NoiSinh",
        )
    )
    has_father = bool(values.get("CccdNam_SoDinhDanh") or values.get("CccdNam_HoTen"))
    has_mother = bool(values.get("CccdNu_SoDinhDanh") or values.get("CccdNu_HoTen"))

    if has_child:
        add_name("", child_name)
        add("NgaySinh", values.get("Gcs_NgaySinhCon"))
        add("GioiTinh", values.get("Gcs_GioiTinhCon"))
        # Dân tộc con: ưu tiên giấy chứng sinh; nếu không có thì SUY LUẬN theo cha/mẹ (bôi vàng):
        #  1) Cha và mẹ CÙNG dân tộc → con theo dân tộc đó (chắc chắn nhất).
        #  2) Con mang họ cha → theo dân tộc cha; con mang họ mẹ → theo dân tộc mẹ.
        dan_toc_con = values.get("Gcs_DanTocCon")
        dan_toc_suy_luan = False
        if not dan_toc_con:
            dt_cha = values.get("CccdNam_DanToc")
            dt_me = values.get("CccdNu_DanToc")
            ho_con = _fold(_first_token(child_name))
            ho_cha = _fold(_first_token(values.get("CccdNam_HoTen")))
            ho_me = _fold(_first_token(values.get("CccdNu_HoTen")))
            if dt_cha and dt_me and _fold(dt_cha) == _fold(dt_me):
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif ho_con and ho_con == ho_cha:
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif ho_con and ho_con == ho_me:
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
        add("MaDanToc", normalize_ethnic(dan_toc_con), default=dan_toc_suy_luan)
        add("MaQuocTich", "Việt Nam")
        add("NsMaQuocGia", "Việt Nam")
        # Nơi sinh: ưu tiên tờ khai đăng ký khai sinh, sau đó mới tới giấy chứng sinh.
        # Nếu LLM không suy ra được xa → tra bảng bệnh viện để bổ sung xa + tinh.
        ns_raw = values.get("Tk_NoiSinh") or values.get("Gcs_NoiSinh")
        ns_area = _area(_norm_birth_place(ns_raw))
        if ns_area and not ns_area.get("xa"):
            dia_chi = ns_area.get("diaChi") or ""
            bv_info = lookup_hospital(dia_chi)
            if bv_info:
                ns_area = {**ns_area, "xa": bv_info["xa"]}
                # Bổ sung tinh nếu LLM cũng bỏ trống
                if not ns_area.get("tinh"):
                    ns_area["tinh"] = bv_info["tinh"]
        add("NsDiaChi", ns_area)

    if has_mother:
        add_name("Me", values.get("CccdNu_HoTen"))
        add("MeNgaySinh", values.get("CccdNu_NgaySinh"))
        add("MeSoGiayTo", values.get("CccdNu_SoDinhDanh"))
        add("MeMaDanToc", normalize_ethnic(values.get("CccdNu_DanToc")))
        add("MeMaQuocTich", values.get("CccdNu_QuocTich") or "Việt Nam")
        add("MeLoaiCuTru", "Thường trú")
        add("MeMaQuocGia", "Việt Nam")
        add("MeDiaChi", _area(values.get("CccdNu_NoiCuTru")))

    if has_father:
        add_name("Cha", values.get("CccdNam_HoTen"))
        # Form liên thông dùng 1 ô họ tên gộp (ChaHoTen); form cũ dùng 3 ô tách ở trên.
        add("ChaHoTen", values.get("CccdNam_HoTen"))
        add("ChaNgaySinh", values.get("CccdNam_NgaySinh"))
        add("ChaSoGiayTo", values.get("CccdNam_SoDinhDanh"))
        add("ChaMaDanToc", normalize_ethnic(values.get("CccdNam_DanToc")))
        add("ChaMaQuocTich", values.get("CccdNam_QuocTich") or "Việt Nam")
        add("ChaLoaiCuTru", "Thường trú")
        add("ChaMaQuocGia", "Việt Nam")
        add("ChaDiaChi", _area(values.get("CccdNam_NoiCuTru")))

    # Quê quán CON (QqDiaChi) — lấy theo CCCD cha:
    #  1) TỜ KHAI có ghi quê quán con riêng → ưu tiên (chính xác nhất).
    #  2) Quê quán trên CCCD cha (CccdNam_QueQuan).
    #  Không có nguồn nào → để trống (không bịa).
    tk_que_quan = _area(values.get("Tk_QueQuanCon"))
    if tk_que_quan:
        add("QqMaQuocGia", "Việt Nam")
        add("QqDiaChi", tk_que_quan)
    else:
        que_quan_cha = _area(values.get("CccdNam_QueQuan"))
        if que_quan_cha:
            add("QqMaQuocGia", "Việt Nam")
            add("QqDiaChi", que_quan_cha)

    # Giấy chứng nhận kết hôn của cha mẹ (nếu có) → mục "Thông tin về Giấy CN kết hôn".
    # Chặn cứng: số giấy chứng sinh (chứa "GCS", vd "01327.GCS.12096.25") KHÔNG phải số kết hôn.
    gcn_so = values.get("GcnKetHon_So")
    if gcn_so and _is_birth_cert_serial(gcn_so):
        gcn_so = None
    if any([gcn_so, values.get("GcnKetHon_QuyenSo"), values.get("GcnKetHon_NgayCap"), values.get("GcnKetHon_NoiCap")]):
        add("GiayCNKHSo", gcn_so)
        add("GiayCNKHQuyenSo", values.get("GcnKetHon_QuyenSo"))
        add("GiayCNKHNgayCap", values.get("GcnKetHon_NgayCap"))
        add("GiayCNKHNoiCap", values.get("GcnKetHon_NoiCap"))

    # Quan hệ người yêu cầu với người được khai sinh. Danh tính người yêu cầu (tên + CCCD) do
    # cổng tự đổ từ tài khoản đăng nhập vào ô readonly trên form → chỉ extension đọc được. Ta
    # gửi kèm danh tính cha/mẹ để extension so khớp: trùng CCCD/tên cha → "Cha", mẹ → "Mẹ",
    # khác cả hai → mặc định "Người giám hộ/đại diện hợp pháp".
    if has_father or has_mother:
        add("NycQuanHe", {
            "chaCccd": values.get("CccdNam_SoDinhDanh"),
            "chaTen": values.get("CccdNam_HoTen"),
            "meCccd": values.get("CccdNu_SoDinhDanh"),
            "meTen": values.get("CccdNu_HoTen"),
        })

    # Đăng ký thường trú: nếu hồ sơ có TỜ KHAI CT01 (thay đổi thông tin cư trú) → chọn xác nhận
    # bằng VĂN BẢN GIẤY (LoaiXacNhanVNeID="1") thay cho VNeID, rồi điền "Thông tin chủ hộ" theo CT01.
    # Xác định chủ hộ là bố/mẹ theo SỐ ĐỊNH DANH (chắc chắn), fallback TÊN; khác cả hai → điền tay 3 ô.
    ct01_ten = values.get("Ct01_ChuHoHoTen")
    ct01_sdd = values.get("Ct01_ChuHoSoDinhDanh")
    if ct01_ten or ct01_sdd:
        add("LoaiXacNhanVNeID", "1")

        ct01_sdd_d = re.sub(r"\D", "", str(ct01_sdd or ""))
        cha_sdd_d = re.sub(r"\D", "", str(values.get("CccdNam_SoDinhDanh") or ""))
        me_sdd_d = re.sub(r"\D", "", str(values.get("CccdNu_SoDinhDanh") or ""))
        ct01_ten_f = _fold(ct01_ten)

        is_bo = (ct01_sdd_d and ct01_sdd_d == cha_sdd_d) or (
            not ct01_sdd_d and ct01_ten_f and has_father and ct01_ten_f == _fold(values.get("CccdNam_HoTen"))
        )
        is_me = (ct01_sdd_d and ct01_sdd_d == me_sdd_d) or (
            not ct01_sdd_d and ct01_ten_f and has_mother and ct01_ten_f == _fold(values.get("CccdNu_HoTen"))
        )

        if is_bo:
            add("DkttIsTtBo", True)
            add("DkttMaQuanHe", "Con đẻ")
            seen.add("DkttIsTtMe")
        elif is_me:
            add("DkttIsTtMe", True)
            add("DkttMaQuanHe", "Con đẻ")
            seen.add("DkttIsTtBo")
        else:  # chủ hộ là người khác → điền tay 3 ô
            seen.update({"DkttIsTtBo", "DkttIsTtMe"})
            add("DkttChuHo", ct01_ten)
            add("DkttChuhoSoGiayTo", ct01_sdd)
            add("DkttMaQuanHe", values.get("Ct01_QuanHeVoiChuHo"))
            seen.add("DkttMaQuanHe")  # quan hệ trống cũng KHÔNG để default "Con đẻ" (sai cho người khác)

    # Bản sao: chỉ khi tờ khai có số lượng thật mới điền số lượng.
    # CapBanSao="1" để Angular hiện ô BanSaoSoLuong trước khi extension điền số.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "1")
        add("BanSaoSoLuong", copy_quantity)

    for default in STATIC_DEFAULTS:
        if default["name"] not in seen:
            out.append(dict(default))
            seen.add(default["name"])

    return out
