"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.115678).

BA QUYẾT ĐỊNH CHỦ CHỐT, đều rút từ `mapping_giao_dat_trung_dau_gia_Lao_Cai.xlsx` (2 bản DOM thật:
cá nhân + tổ chức) và 2 hồ sơ mẫu HS1/HS2:

1. LUÔN PHÁT ĐỦ KHỐI CHỦ HỒ SƠ, kể cả khi người nộp trùng chủ hồ sơ. Checkbox "Người nộp là chủ hồ
   sơ" của cổng CHỈ sao chép tới Nơi cấp/Ngày cấp căn cước, KHÔNG sao chép Tỉnh/Phường-Xã/Địa chỉ.
   Cũng KHÔNG tự bấm checkbox đó: đổi trạng thái có thể làm cổng xoá dữ liệu vừa điền.

2. HAI MODE NGƯỜI NỘP được chốt bằng ĐỐI CHIẾU THẬT, không tin cờ LLM:
   • Mode A "nộp thay" — hai khối là hai người khác nhau (hồ sơ có hợp đồng ủy quyền).
   • Mode B "tự nộp"  — hai khối cùng một người.
   Mode quyết định việc BỔ KHUYẾT: ở mode B, ô nào của khối người nộp mà hồ sơ không ghi riêng thì
   lấy từ khối chủ hồ sơ (và ngược lại) — đúng một người nên chép là an toàn. Ở mode A thì TUYỆT ĐỐI
   không chép chéo: chép là gán nhân thân người này cho người kia.

   ⚑ MỐC CHỐT MODE là TÀI KHOẢN ĐỊNH DANH ĐANG ĐĂNG NHẬP, không phải suy đoán từ giấy tờ. Cổng
   prefill tài khoản vào hai ô readonly `CongDan_tenCongDan` / `CongDan_soCmnd`; extension đọc rồi
   gửi lên trong `options.formContext`. Người đang đăng nhập CHÍNH LÀ người đi nộp — đó là sự thật
   của phiên làm việc, trong khi giấy tờ chỉ cho biết hồ sơ DỰ ĐỊNH ai nộp. Thiếu mốc (popup chưa
   bật thu thập cho key này, hoặc trang chưa đăng nhập) thì quay về đối chiếu hai khối trong giấy tờ
   và nói rõ trong cảnh báo rằng mode chỉ là suy đoán.

3. KHÔNG PHÁT `CongDan_tenCongDan` / `CongDan_soCmnd`. Hai ô readonly đó mà bị ghi thì script cổng
   XOÁ TRẮNG "Di động" + "Số Căn cước" — điền vào chính là làm hỏng ô bắt buộc vừa điền xong.

4. LỌC Ô THEO ĐỐI TƯỢNG. Khối chủ hồ sơ có 2 nhóm ô loại trừ nhau (`ORG_ONLY_FIELDS` /
   `INDIVIDUAL_ONLY_FIELDS`): chọn "Cá nhân" thì nhóm tổ chức bị display:none và ngược lại. Phát ô
   đang ẩn chỉ làm engine báo "không điền được" một cách vô cớ.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cho_thue_dat_thue_rung.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_DOI_TUONG_TO_CHUC = "Tổ chức"
_DOI_TUONG_CA_NHAN = "Cá nhân"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _area(value) -> dict | None:
    """Địa chỉ thường là object {quocGia,tinh,xa,diaChi}; chuỗi trần thì dồn vào diaChi."""
    if isinstance(value, str):
        text = _plain(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _digits(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    return re.sub(r"\D", "", text) or None


def _tax_code(value) -> str | None:
    """Mã số thuế giữ được dấu '-' của mã đơn vị phụ thuộc (vd 5300xxxxxx-001)."""
    text = _plain(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9-]", "", text).strip("-")
    return cleaned or None


def _phone(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _date(value) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1974") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "có", "1"):
        return True
    return bool(values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"))


def _account_anchor(options: dict | None) -> tuple[str | None, str]:
    """Nhân thân TÀI KHOẢN ĐANG ĐĂNG NHẬP, do extension đọc từ 2 ô readonly của cổng."""
    ctx = (options or {}).get("formContext") or {}
    ctx_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    ctx_name = _fold(_plain(ctx.get("applicantFullname")) or "")
    return ctx_id, ctx_name


def _match(left_id, left_name, right_id, right_name) -> bool | None:
    """So hai người: số định danh trước, rồi tới họ tên đã bỏ dấu. None = không đủ căn cứ.

    Số định danh là bằng chứng mạnh nhất nên được xét TRƯỚC: hai người có thể trùng họ tên nhưng
    không bao giờ trùng CCCD. Họ tên so bản đã bỏ dấu vì OCR hay rơi dấu.
    """
    if left_id and right_id:
        return left_id == right_id
    if left_name and right_name:
        return left_name == right_name
    return None


def _same_person(values: dict, ctx_id: str | None, ctx_name: str) -> bool:
    """Người nộp có TRÙNG chủ hồ sơ không (mode B) — chốt bằng dữ liệu, không bằng cờ LLM.

    Ưu tiên MỐC TÀI KHOẢN: người đang đăng nhập chính là người đi nộp, nên chỉ cần đối chiếu mốc đó
    với CHỦ HỒ SƠ là ra mode. Giấy tờ chỉ nói hồ sơ DỰ ĐỊNH ai nộp, còn mốc nói ai ĐANG nộp thật.

    Không có mốc thì quay về đối chiếu hai khối trong giấy tờ. Hai ca không đối chiếu được ngả về
    hai phía khác nhau, đều có lý do:
      • Khối người nộp TRỐNG HẲN (không số, không tên) → TRÙNG. Đó đúng là hồ sơ tự nộp: người dân
        chỉ khai một lần ở khối chủ hồ sơ, không có giấy ủy quyền nào để trích ra người thứ hai.
      • Khối người nộp CÓ khai nhưng thiếu vế kia để so → coi là NGƯỜI KHÁC. Ngả về "khác" là phía
        an toàn: mode khác nhau thì mapper không chép nhân thân chéo, cùng lắm là bỏ trống vài ô cho
        cán bộ nhập tay; ngả nhầm sang "trùng" thì gán luôn nhân thân người này cho người kia.
    """
    chs_id = _digits(values.get("ChuHoSo_SoDinhDanh"))
    chs_name = _fold(_plain(values.get("ChuHoSo_HoTen")) or "")

    if ctx_id or ctx_name:
        matched = _match(ctx_id, ctx_name, chs_id, chs_name)
        # Có mốc mà chủ hồ sơ không có gì để so → không dám coi là trùng (xem lý do ở trên).
        return bool(matched)

    nop_id = _digits(values.get("NguoiNop_SoDinhDanh"))
    nop_name = _fold(_plain(values.get("NguoiNop_HoTen")) or "")
    matched = _match(nop_id, nop_name, chs_id, chs_name)
    if matched is not None:
        return matched
    return not (nop_id or nop_name)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    is_org = _is_org(values)
    ctx_id, ctx_name = _account_anchor(options)
    same_person = _same_person(values, ctx_id, ctx_name)

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        # Ô đang bị cổng ẩn theo "Đối tượng nộp hồ sơ" thì không phát (xem docstring, điểm 3).
        if is_org and name in INDIVIDUAL_ONLY_FIELDS:
            return
        if not is_org and name in ORG_ONLY_FIELDS:
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    ten_to_chuc = _plain(values.get("ChuHoSo_TenToChuc"))
    ma_so_thue = _tax_code(values.get("ChuHoSo_MaSoThue"))

    # --- Nhân thân hai khối, đã tính cả việc bổ khuyết chéo khi CÙNG MỘT NGƯỜI ---
    def pick(nop_key: str, chs_key: str) -> tuple[object, object]:
        """Trả (giá trị khối người nộp, giá trị khối chủ hồ sơ) sau khi bổ khuyết theo mode."""
        nop_raw = values.get(nop_key)
        chs_raw = values.get(chs_key)
        if not same_person:
            return nop_raw, chs_raw
        return (nop_raw or chs_raw), (chs_raw or nop_raw)

    nop_ten, chs_ten = pick("NguoiNop_HoTen", "ChuHoSo_HoTen")
    nop_ngay_sinh, chs_ngay_sinh = pick("NguoiNop_NgaySinh", "ChuHoSo_NgaySinh")
    nop_gioi_tinh, chs_gioi_tinh = pick("NguoiNop_GioiTinh", "ChuHoSo_GioiTinh")
    nop_dan_toc, chs_dan_toc = pick("NguoiNop_DanToc", "ChuHoSo_DanToc")
    nop_so_raw, chs_so_raw = pick("NguoiNop_SoDinhDanh", "ChuHoSo_SoDinhDanh")
    nop_ngay_cap_raw, chs_ngay_cap_raw = pick("NguoiNop_NgayCap", "ChuHoSo_NgayCap")
    nop_noi_cap_raw, chs_noi_cap_raw = pick("NguoiNop_NoiCap", "ChuHoSo_NoiCap")
    nop_dien_thoai, chs_dien_thoai = pick("NguoiNop_DienThoai", "ChuHoSo_DienThoai")
    nop_email, chs_email = pick("NguoiNop_Email", "ChuHoSo_Email")
    nop_fax, chs_fax = pick("NguoiNop_Fax", "ChuHoSo_Fax")

    # --- Khối NGƯỜI NỘP ---
    nop_identity = _digits(nop_so_raw)
    nop_ngay_cap = _date(nop_ngay_cap_raw)
    # Nơi cấp mặc định CHỈ khi hồ sơ thật sự có giấy tờ định danh của người đó — không thì là bịa.
    nop_noi_cap = normalize_issuer(_plain(nop_noi_cap_raw))
    if not nop_noi_cap and nop_identity:
        nop_noi_cap = default_issuer(nop_ngay_cap)
    add("CongDan_tenCongDan", _plain(nop_ten))
    add("CongDan_ngaySinhCongDan", _date(nop_ngay_sinh))
    add("CongDan_gioiTinhCongDan", _plain(nop_gioi_tinh))
    add("CongDan_danTocCongDan", _plain(nop_dan_toc))
    add("CongDan_soCmnd", nop_identity)
    add("CongDan_ngayCapCmnd", nop_ngay_cap)
    add("CongDan_noiCapCmnd", nop_noi_cap)
    add("CongDan_diDong", _phone(nop_dien_thoai))
    add("CongDan_email", _plain(nop_email))
    add("CongDan_fax", _plain(nop_fax))
    if is_org and same_person:
        # Chỉ khi chính người của tổ chức đi nộp thì khối người nộp mới mang tên/MST tổ chức đó.
        # Nộp thay theo ủy quyền thì bên được ủy quyền là CÁ NHÂN — điền tên công ty vào đây là sai.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)

    nop_area = _area(values.get("NguoiNop_NoiCuTru"))
    if not nop_area and same_person:
        nop_area = _area(values.get("ChuHoSo_NoiCuTru"))
    if nop_area:
        add("CongDan_maTinhThanh", _province_label(nop_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
        add("CongDan_diaChi", _plain(nop_area.get("diaChi")))

    # --- Khối CHỦ HỒ SƠ: phát ĐỦ, KHÔNG dựa vào checkbox "Người nộp là chủ hồ sơ" ---
    add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_TO_CHUC if is_org else _DOI_TUONG_CA_NHAN)
    add("ChuHoSo_tenChuHoSo", _plain(chs_ten))
    add("ChuHoSo_ngaySinhChuHoSo", _date(chs_ngay_sinh))
    add("ChuHoSo_gioiTinhChuHoSo", _plain(chs_gioi_tinh))
    add("ChuHoSo_danTocChuHoSo", _plain(chs_dan_toc))
    chs_ngay_cap = _date(chs_ngay_cap_raw)
    chs_identity = _digits(chs_so_raw)
    chs_noi_cap = normalize_issuer(_plain(chs_noi_cap_raw))
    if not chs_noi_cap and chs_identity:
        chs_noi_cap = default_issuer(chs_ngay_cap)
    add("ChuHoSo_soCMNDChuHoSo", chs_identity)
    add("ChuHoSo_ngayCapCMNDCHS", chs_ngay_cap)
    add("ChuHoSo_noiCapCMNDCHS", chs_noi_cap)
    add("ChuHoSo_diDongLienLacCHS", _phone(chs_dien_thoai))
    add("ChuHoSo_emailChuHoSo", _plain(chs_email))
    add("ChuHoSo_faxChuHoSo", _plain(chs_fax))
    if is_org:
        add("ChuHoSo_tenCoQuanToChucCHS", ten_to_chuc)
        add("ChuHoSo_maSoThueChuHoSo", ma_so_thue)

    # 3 ô địa chỉ này là thứ checkbox của cổng KHÔNG copy → luôn phát từ dữ liệu trích được.
    chs_area = _area(values.get("ChuHoSo_NoiCuTru"))
    if not chs_area and same_person:
        chs_area = nop_area
    if chs_area:
        add("ChuHoSo_maTinhThanhCHS", _province_label(chs_area.get("tinh")))
        add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
        add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
    else:
        warnings.append(
            "Không đọc được địa chỉ chủ hồ sơ. Nút \"Người nộp là chủ hồ sơ\" của cổng KHÔNG sao chép "
            "địa chỉ, cán bộ cần nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ."
        )

    warnings.extend(_mode_warnings(values, same_person, nop_area, ctx_id, ctx_name))
    return out, warnings


def _mode_warnings(
    values: dict,
    same_person: bool,
    nop_area: dict | None,
    ctx_id: str | None,
    ctx_name: str,
) -> list[str]:
    """Cảnh báo riêng cho từng mode người nộp — thứ cán bộ không thể tự thấy trên màn hình."""
    warnings: list[str] = []
    ho_ten_nop = _plain(values.get("NguoiNop_HoTen"))
    has_anchor = bool(ctx_id or ctx_name)

    if not has_anchor:
        warnings.append(
            "Chưa đọc được tài khoản định danh đang đăng nhập trên cổng, nên vai người nộp chỉ là suy "
            "đoán từ giấy tờ. Cán bộ kiểm tra lại khối \"Thông tin người nộp\" trước khi nộp."
        )

    if same_person:
        # Mode B: cổng vẫn để trống khối chủ hồ sơ, cán bộ hay tưởng chỉ cần tick checkbox là xong.
        warnings.append(
            "Người nộp trùng chủ hồ sơ (hồ sơ không có ủy quyền): hệ thống đã điền ĐỦ cả hai khối. "
            "Nếu cán bộ tự tick \"Người nộp là chủ hồ sơ\", cổng có thể ghi đè phần đã điền — nên "
            "kiểm tra lại khối chủ hồ sơ sau khi tick."
        )
        return warnings

    # Mode A: hai người khác nhau. Các rủi ro thật, đều lấy từ hồ sơ mẫu HS1.
    warnings.append(
        f"Hồ sơ nộp thay: người đi nộp khác chủ hồ sơ"
        + (f" (giấy tờ ghi người được ủy quyền là {ho_ten_nop})" if ho_ten_nop else "")
        + ". Hai ô \"Họ và tên\" và \"Số Căn cước\" của khối người nộp là ô READONLY do cổng đổ từ "
        "tài khoản đang đăng nhập nên hệ thống KHÔNG điền (ghi vào đó là cổng xoá trắng Di động và "
        "Số Căn cước). TUYỆT ĐỐI không tick \"Người nộp là chủ hồ sơ\"."
    )

    # Rủi ro thật hay gặp: cán bộ/người thân đăng nhập bằng tài khoản CỦA MÌNH rồi nộp hộ. Khi đó hồ
    # sơ mang tên người đăng nhập chứ không phải người được ủy quyền ghi trong hợp đồng.
    nop_id = _digits(values.get("NguoiNop_SoDinhDanh"))
    nop_name = _fold(ho_ten_nop or "")
    if has_anchor and (nop_id or nop_name):
        matched = _match(ctx_id, ctx_name, nop_id, nop_name)
        if matched is False:
            warnings.append(
                "⚠ Tài khoản đang đăng nhập KHÔNG phải người được ủy quyền ghi trong hồ sơ"
                + (f" ({ho_ten_nop})" if ho_ten_nop else "")
                + ". Cổng sẽ ghi người nộp theo tài khoản đăng nhập — đăng nhập đúng tài khoản của "
                "người được ủy quyền, hoặc bổ sung giấy ủy quyền cho chính người đang đăng nhập."
            )

    if not _phone(values.get("NguoiNop_DienThoai")):
        warnings.append(
            "Không đọc được số điện thoại của người được ủy quyền (hợp đồng ủy quyền thường không "
            "ghi). Ô \"Di động\" của khối người nộp là ô bắt buộc — cán bộ hỏi trực tiếp người nộp, "
            "KHÔNG lấy số của chủ hồ sơ."
        )
    if not nop_area:
        warnings.append(
            "Không đọc được địa chỉ của người được ủy quyền. Ba ô Tỉnh/Phường-Xã/Địa chỉ của khối "
            "người nộp là bắt buộc — cán bộ nhập tay theo nơi thường trú ghi trong hợp đồng ủy quyền."
        )
    return warnings
