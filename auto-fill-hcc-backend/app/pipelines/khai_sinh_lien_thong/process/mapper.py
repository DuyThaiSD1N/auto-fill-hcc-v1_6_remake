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


def _upper_name(value) -> str:
    """Tên chủ thể trên form hộ tịch phải viết IN HOA, đồng thời gom khoảng trắng OCR."""
    return " ".join(str(value or "").split()).upper()


def _ethnicity_for_form(value) -> tuple[str, str]:
    """Cil/Cill không có option riêng: chọn Khác và giữ nguyên cách ghi vào ô nhập tay."""
    raw = str(value or "").strip()
    if not raw:
        return "", ""
    if _fold(raw) in {"cil", "cill"}:
        return "Khác", raw
    return normalize_ethnic(raw), ""


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


def _upper_name(full_name: str | None) -> str:
    """Họ tên con/cha/mẹ trên biểu mẫu liên thông LUÔN viết HOA toàn bộ.

    Cổng không tự chuẩn hoá nên giấy tờ ghi kiểu gì extension điền y hệt kiểu đó; hồ sơ có ba ô
    tên viết ba kiểu khác nhau ("Nguyễn Văn A" / "NGUYỄN VĂN B") trông như dữ liệu lấy sai nguồn.
    str.upper() nhận biết Unicode nên giữ nguyên dấu tiếng Việt ("Nguyễn" -> "NGUYỄN").
    """
    return " ".join(str(full_name or "").split()).upper()


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
    for name_field in (
        "Gcs_HoTenCon",
        "Tk_HoTenCon",
        "ThongTinBo_HoTen",
        "ThongTinMe_HoTen",
        "CccdNam_HoTen",
        "CccdNu_HoTen",
        "Ct01_ChuHoHoTen",
    ):
        if name_field in values:
            values[name_field] = _upper_name(values[name_field])
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
        ho, chu_dem, ten = _split_name(_upper_name(full_name))
        add(f"{prefix}Ho" if prefix else "Ho", ho)
        add(f"{prefix}ChuDem" if prefix else "ChuDem", chu_dem)
        add(f"{prefix}Ten" if prefix else "Ten", ten)

    child_name = _clean_child_name(
        values.get("Tk_HoTenCon") or values.get("Gcs_HoTenCon"),
        values.get("ThongTinMe_HoTen"),
    )
    has_child = bool(child_name) or any(
        name in values
        for name in (
            "Tk_NgaySinhCon",
            "Tk_GioiTinhCon",
            "Tk_DanTocCon",
            "Gcs_NgaySinhCon",
            "Gcs_GioiTinhCon",
            "Gcs_DanTocCon",
            "Gcs_NoiSinh",
        )
    )
    has_father = bool(values.get("ThongTinBo_SoDinhDanh") or values.get("ThongTinBo_HoTen"))
    has_mother = bool(values.get("ThongTinMe_SoDinhDanh") or values.get("ThongTinMe_HoTen"))

    # Ngoại lệ Lâm Đồng dùng ở HAI nơi: dân tộc con (trong khối has_child) và quê quán con
    # (ngoài khối). Trước đây tính bên trong `if has_child:` nên hồ sơ KHÔNG có giấy chứng sinh
    # lẫn tờ khai — has_child = False — chạy tới phần quê quán là nổ UnboundLocalError
    # "cannot access local variable 'is_lam_dong'", công dân chỉ thấy "Xử lý giấy tờ chưa xong".
    ns_raw = values.get("Tk_NoiSinh") or values.get("Gcs_NoiSinh")
    ns_area = _area(_norm_birth_place(ns_raw)) if ns_raw else None
    birth_province = _fold(ns_area.get("tinh") or "") if ns_area else ""
    is_lam_dong = "lam dong" in birth_province

    if has_child:
        add_name("", child_name)
        # Thông tin con nói chung ưu tiên TỜ KHAI. RIÊNG NGÀY SINH ưu tiên GIẤY CHỨNG SINH:
        # đó là bản ghi y tế gốc của sự kiện sinh; con số ngày người khai gõ tay ở tờ khai hay
        # lệch/typo so với ngày sinh thực (vd tờ khai ghi số "28" nhưng chữ + chứng sinh là "20").
        add("NgaySinh", values.get("Gcs_NgaySinhCon") or values.get("Tk_NgaySinhCon"))
        add("GioiTinh", values.get("Tk_GioiTinhCon") or values.get("Gcs_GioiTinhCon"))
        
        # ns_area / is_lam_dong đã tính TRƯỚC khối này (xem chú thích ở trên).
        # Dân tộc con: ưu tiên tờ khai, rồi giấy chứng sinh; nếu không có thì SUY LUẬN theo cha/mẹ (bôi vàng):
        #  1) Tờ khai ghi rõ dân tộc con → dùng (chính xác nhất).
        #  2) Giấy chứng sinh ghi rõ dân tộc con → dùng.
        #  3) NGOẠI LỆ LÂM ĐỒNG: nếu con sinh ra ở Lâm Đồng → theo dân tộc MẸ.
        #  4) Cha và mẹ CÙNG dân tộc → con theo dân tộc đó.
        #  5) Con mang họ cha → theo dân tộc cha.
        #  6) Con mang họ mẹ → theo dân tộc mẹ.
        #  7) Chỉ có dân tộc cha (không biết dân tộc mẹ) → theo dân tộc cha.
        #  8) Chỉ có dân tộc mẹ (không biết dân tộc cha) → theo dân tộc mẹ.
        dan_toc_con = values.get("Tk_DanTocCon") or values.get("Gcs_DanTocCon")
        dan_toc_suy_luan = False
        if not dan_toc_con:
            dt_cha = values.get("ThongTinBo_DanToc")
            dt_me = values.get("ThongTinMe_DanToc")
            ho_con = _fold(_first_token(child_name))
            ho_cha = _fold(_first_token(values.get("ThongTinBo_HoTen")))
            ho_me = _fold(_first_token(values.get("ThongTinMe_HoTen")))
            
            if is_lam_dong and dt_me:
                # NGOẠI LỆ LÂM ĐỒNG: theo dân tộc mẹ
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
            elif dt_cha and dt_me and _fold(dt_cha) == _fold(dt_me):
                # Cùng dân tộc
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif ho_con and ho_con == ho_cha and dt_cha:
                # Họ theo cha
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif ho_con and ho_con == ho_me and dt_me:
                # Họ theo mẹ
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
            elif dt_cha:
                # Chỉ biết dân tộc cha → mặc định theo cha
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif dt_me:
                # Chỉ biết dân tộc mẹ
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
        dan_toc_con_select, dan_toc_con_khac = _ethnicity_for_form(dan_toc_con)
        # Dropdown phải đi trước để Angular render ô DantocKhac rồi extension mới điền field kế tiếp.
        add("MaDanToc", dan_toc_con_select, default=dan_toc_suy_luan)
        add("DantocKhac", dan_toc_con_khac, default=dan_toc_suy_luan)
        add("MaQuocTich", "Việt Nam")
        add("NsMaQuocGia", "Việt Nam")
        # Nơi sinh: nếu LLM không suy ra được xa → tra bảng bệnh viện để bổ sung xa + tinh.
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
        add_name("Me", values.get("ThongTinMe_HoTen"))
        add("MeNgaySinh", values.get("ThongTinMe_NgaySinh"))
        add("MeSoGiayTo", values.get("ThongTinMe_SoDinhDanh"))
        dan_toc_me_select, dan_toc_me_khac = _ethnicity_for_form(values.get("ThongTinMe_DanToc"))
        add("MeMaDanToc", dan_toc_me_select)
        add("MeDantocKhac", dan_toc_me_khac)
        add("MeMaQuocTich", values.get("ThongTinMe_QuocTich") or "Việt Nam")
        add("MeLoaiCuTru", "Thường trú")
        add("MeMaQuocGia", "Việt Nam")
        add("MeDiaChi", _area(values.get("ThongTinMe_NoiCuTru")))

    if has_father:
        add_name("Cha", values.get("ThongTinBo_HoTen"))
        # Form liên thông dùng 1 ô họ tên gộp (ChaHoTen); form cũ dùng 3 ô tách ở trên.
        add("ChaHoTen", _upper_name(values.get("ThongTinBo_HoTen")))
        add("ChaNgaySinh", values.get("ThongTinBo_NgaySinh"))
        add("ChaSoGiayTo", values.get("ThongTinBo_SoDinhDanh"))
        dan_toc_cha_select, dan_toc_cha_khac = _ethnicity_for_form(values.get("ThongTinBo_DanToc"))
        add("ChaMaDanToc", dan_toc_cha_select)
        add("ChaDantocKhac", dan_toc_cha_khac)
        add("ChaMaQuocTich", values.get("ThongTinBo_QuocTich") or "Việt Nam")
        add("ChaLoaiCuTru", "Thường trú")
        add("ChaMaQuocGia", "Việt Nam")
        add("ChaDiaChi", _area(values.get("ThongTinBo_NoiCuTru")))

    # Quê quán CON (QqDiaChi) — lấy theo thứ tự ưu tiên:
    #  1) TỜ KHAI có ghi quê quán con riêng → ưu tiên (chính xác nhất).
    #  2) Quê quán trên CCCD cha (ThongTinBo_QueQuan) — CCCD cũ có dòng "Quê quán".
    #  3) Nơi đăng ký khai sinh trên thẻ CĂN CƯỚC mới của cha (ThongTinBo_NoiDangKyKhaiSinh).
    #  4) Nơi cư trú của cha (ThongTinBo_NoiCuTru) — fallback cuối cùng theo tục lệ
    #     quê quán con = quê cha.
    #  NGOẠI LỆ LÂM ĐỒNG: nếu nơi sinh con (NsDiaChi) có tỉnh = "Lâm Đồng", lấy QUÊ QUÁN MẸ
    #     thay vì cha (theo quy định địa phương); tuyệt đối không dùng nơi cư trú mẹ thay thế.
    #  Không có nguồn nào → để trống (không bịa).
    tk_que_quan = _area(values.get("Tk_QueQuanCon"))

    if tk_que_quan:
        add("QqMaQuocGia", "Việt Nam")
        add("QqDiaChi", tk_que_quan)
    else:
        # is_lam_dong tính ở đầu hàm — NGOÀI khối has_child, vì nhánh này chạy cả khi hồ sơ
        # chưa có thông tin con.
        if is_lam_dong and has_mother:
            # Lâm Đồng lấy đúng QUÊ QUÁN MẸ. Không có field này thì để trống; nơi cư trú là một
            # khái niệm khác và không được dùng làm fallback cho quê quán của con.
            que_quan_me = _area(values.get("ThongTinMe_QueQuan"))
            if que_quan_me:
                add("QqMaQuocGia", "Việt Nam")
                add("QqDiaChi", que_quan_me)
        else:
            # Trường hợp thông thường: lấy quê quán từ CHA
            que_quan_cha = (
                _area(values.get("ThongTinBo_QueQuan"))
                or _area(values.get("ThongTinBo_NoiDangKyKhaiSinh"))
                or _area(values.get("ThongTinBo_NoiCuTru"))
            )
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
            "chaCccd": values.get("ThongTinBo_SoDinhDanh"),
            "chaTen": values.get("ThongTinBo_HoTen"),
            "meCccd": values.get("ThongTinMe_SoDinhDanh"),
            "meTen": values.get("ThongTinMe_HoTen"),
        })

    # Số điện thoại: SĐT ghi trên giấy tờ là của NGƯỜI KÝ TỜ KHAI. Khối "Thông tin người yêu cầu"
    # trên cổng lại là người ĐANG ĐĂNG NHẬP (readonly, chỉ extension đọc được) → gửi kèm tên người
    # yêu cầu trên tờ khai để extension so tên; trùng thì mới điền ô SĐT, khác thì bỏ qua vì đó là
    # số của người khác.
    phone = _clean_phone(values.get("LienHe_SoDienThoai"))
    nyc_ten = _upper_name(values.get("Tk_NguoiYeuCau_HoTen"))
    if phone and nyc_ten:
        add("NycSdt", {"sdt": phone, "ten": nyc_ten})

    # Đăng ký thường trú: nếu hồ sơ có TỜ KHAI CT01 (thay đổi thông tin cư trú) → chọn xác nhận
    # bằng VĂN BẢN GIẤY (LoaiXacNhanVNeID="1") thay cho VNeID, rồi điền "Thông tin chủ hộ" theo CT01.
    # Xác định chủ hộ là bố/mẹ theo SỐ ĐỊNH DANH (chắc chắn), fallback TÊN; khác cả hai → điền tay 3 ô.
    ct01_ten = values.get("Ct01_ChuHoHoTen")
    ct01_sdd = values.get("Ct01_ChuHoSoDinhDanh")
    if ct01_ten or ct01_sdd:
        add("LoaiXacNhanVNeID", "1")

        ct01_sdd_d = re.sub(r"\D", "", str(ct01_sdd or ""))
        cha_sdd_d = re.sub(r"\D", "", str(values.get("ThongTinBo_SoDinhDanh") or ""))
        me_sdd_d = re.sub(r"\D", "", str(values.get("ThongTinMe_SoDinhDanh") or ""))
        ct01_ten_f = _fold(ct01_ten)

        is_bo = (ct01_sdd_d and ct01_sdd_d == cha_sdd_d) or (
            not ct01_sdd_d and ct01_ten_f and has_father and ct01_ten_f == _fold(values.get("ThongTinBo_HoTen"))
        )
        is_me = (ct01_sdd_d and ct01_sdd_d == me_sdd_d) or (
            not ct01_sdd_d and ct01_ten_f and has_mother and ct01_ten_f == _fold(values.get("ThongTinMe_HoTen"))
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
