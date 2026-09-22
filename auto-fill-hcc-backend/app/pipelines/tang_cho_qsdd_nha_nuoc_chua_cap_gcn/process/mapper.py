"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.115690).

BỐN QUYẾT ĐỊNH CHỦ CHỐT, đều rút từ `Mapping_tang_cho_quyen_su_dung_dat.xlsx` (2 bản DOM thật: cá
nhân + tổ chức) và bộ hồ sơ mẫu Lương Thị Linh / Nguyễn Tiến Quân:

1. LUÔN PHÁT ĐỦ KHỐI CHỦ HỒ SƠ, kể cả khi người nộp trùng chủ hồ sơ. Checkbox "Người nộp là chủ hồ
   sơ" của cổng CHỈ sao chép tới Nơi cấp/Ngày cấp căn cước, KHÔNG sao chép Tỉnh/Phường-Xã/Địa chỉ.
   Cũng KHÔNG tự bấm checkbox đó: đổi trạng thái có thể làm cổng xoá dữ liệu vừa điền.

1b. ⚑ KHỐI "THÔNG TIN NGƯỜI NỘP" CHỈ ĐƯỢC ĐIỀN KHI HỒ SƠ CÓ GIẤY TỜ CỦA CHÍNH NGƯỜI ĐANG ĐĂNG NHẬP.
   Cổng chỉ prefill Họ tên + Số Căn cước từ tài khoản; 11 ô còn lại do mình điền. Điền chúng bằng
   nhân thân của người khác thì hồ sơ gửi đi mang TÊN người đăng nhập nhưng NGÀY SINH/GIỚI TÍNH/
   ĐỊA CHỈ của người khác, mà cán bộ rất khó phát hiện vì hai ô readonly phía trên vẫn đúng tên.
   Vì vậy `_khoi_cua_nguoi_dang_nhap` đối chiếu số căn cước tài khoản với hai khối facts; không
   khớp khối nào (hoặc không đọc được tài khoản) thì KHÔNG phát một ô `CongDan_*` nào, kèm cảnh
   báo chỉ rõ cách gỡ. Khối chủ hồ sơ KHÔNG bị ảnh hưởng — nó là của hồ sơ, không phải của phiên.

2. HAI MODE NGƯỜI NỘP được chốt bằng ĐỐI CHIẾU THẬT, không tin cờ LLM:
   • Mode A "nộp thay" — hai khối là hai người khác nhau (hồ sơ có Giấy uỷ quyền). Hồ sơ mẫu của
     thủ tục này thuộc mode A.
   • Mode B "tự nộp"  — hai khối cùng một người.
   Mode quyết định việc BỔ KHUYẾT: ở mode B, ô nào của khối người nộp mà hồ sơ không ghi riêng thì
   lấy từ khối chủ hồ sơ (và ngược lại) — đúng một người nên chép là an toàn. Ở mode A thì TUYỆT ĐỐI
   không chép chéo: chép là gán nhân thân người này cho người kia.

   ⚑ MỐC CHỐT MODE là TÀI KHOẢN ĐỊNH DANH ĐANG ĐĂNG NHẬP, không phải suy đoán từ giấy tờ. Cổng
   prefill tài khoản vào hai ô readonly `CongDan_tenCongDan` / `CongDan_soCmnd`; extension đọc rồi
   gửi lên trong `options.formContext`. File mapping đã ghi nhận đúng rủi ro này: tên hiển thị ở đầu
   trang cổng là của TÀI KHOẢN ĐĂNG NHẬP, không phải của người trong giấy tờ, "không tự điền" —
   nên phải đối chiếu chứ không chép.

3. KHÔNG PHÁT `CongDan_tenCongDan` / `CongDan_soCmnd`. Hai ô readonly đó mà bị ghi thì script cổng
   XOÁ TRẮNG "Di động" + "Số Căn cước" — điền vào chính là làm hỏng ô bắt buộc vừa điền xong.

4. GIỚI TÍNH SUY TẤT ĐỊNH TỪ CCCD 12 SỐ, KHÔNG suy từ họ tên hay danh xưng "ông/bà". Sheet "Cảnh báo
   và chú thích" của file mapping ghi rõ: "Chưa có giá trị giới tính trên giấy tờ đã gửi; không suy
   từ tên hoặc từ ông/bà." Chữ số thứ 4 của CCCD là mã thế kỷ + giới tính (chẵn = Nam, lẻ = Nữ) nên
   đó là căn cứ DUY NHẤT hợp lệ ở thủ tục này — làm ở mapper để không phụ thuộc LLM có nhớ luật hay
   không. Hồ sơ mẫu: 010164003196 → Nữ (Lương Thị Linh), 010066000177 → Nam (Nguyễn Tiến Quân).

Lọc ô theo đối tượng: khối chủ hồ sơ có 2 nhóm ô loại trừ nhau (`ORG_ONLY_FIELDS` /
`INDIVIDUAL_ONLY_FIELDS`); chọn "Cá nhân" thì nhóm tổ chức bị display:none và ngược lại. Phát ô đang
ẩn chỉ làm engine báo "không điền được" một cách vô cớ.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process.schema import (
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
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1964") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _gender(value, identity: str | None) -> str | None:
    """Nam/Nữ. Nhận giá trị LLM đã trả, nếu không thì suy từ chữ số thứ 4 của CCCD 12 số.

    Chữ số thứ 4 của CCCD là mã "thế kỷ sinh + giới tính": chẵn = Nam, lẻ = Nữ. Đây là căn cứ DUY
    NHẤT được phép ở thủ tục này — file mapping cấm suy từ họ tên và từ danh xưng "ông/bà" (xem
    docstring, điểm 4), mà bộ giấy tờ thì không có ô "Giới tính" nào.
    """
    folded = _fold(_plain(value) or "")
    if folded in ("nam", "male", "m"):
        return "Nam"
    if folded in ("nu", "female", "f"):
        return "Nữ"
    if identity and len(identity) == 12 and identity.isdigit():
        return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"
    return None


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
    không bao giờ trùng CCCD. Họ tên so bản đã bỏ dấu vì bản scan hay rơi dấu và hay VIẾT HOA TOÀN BỘ
    ("LƯƠNG THỊ LINH" ở văn bản tặng cho so với "Lương Thị Linh" ở giấy uỷ quyền).
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
        chỉ khai một lần ở Văn bản tặng cho, không có giấy uỷ quyền nào để trích ra người thứ hai.
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


def _nop_block_is_other_person(values: dict) -> bool:
    """Khối NguoiNop_* trích được có CHẮC CHẮN là người khác chủ hồ sơ không.

    Chỉ True khi đối chiếu được và ra KHÁC; thiếu căn cứ thì False.
    """
    return _match(
        _digits(values.get("NguoiNop_SoDinhDanh")),
        _fold(_plain(values.get("NguoiNop_HoTen")) or ""),
        _digits(values.get("ChuHoSo_SoDinhDanh")),
        _fold(_plain(values.get("ChuHoSo_HoTen")) or ""),
    ) is False


def _khoi_cua_nguoi_dang_nhap(values: dict, ctx_id: str | None, ctx_name: str) -> str | None:
    """Khối facts nào LÀ NHÂN THÂN CỦA CHÍNH TÀI KHOẢN ĐANG ĐĂNG NHẬP.

    Trả "chs" (khối chủ hồ sơ), "nop" (khối người được uỷ quyền), hoặc None = KHÔNG XÁC MINH ĐƯỢC.

    ⚑ ĐÂY LÀ CỬA DUY NHẤT MỞ KHỐI "THÔNG TIN NGƯỜI NỘP". Cổng chỉ prefill Họ tên + Số Căn cước của
    tài khoản; 11 ô còn lại (ngày sinh, giới tính, dân tộc, ngày/nơi cấp, tỉnh, phường-xã, địa chỉ,
    di động, email, fax) do mình điền. Nếu điền chúng bằng nhân thân của một người KHÁC thì hồ sơ
    nộp lên mang tên người đang đăng nhập nhưng ngày sinh/giới tính/địa chỉ của người khác — sai
    lệch nhân thân ngay trên hồ sơ gửi cơ quan nhà nước, và cán bộ rất khó phát hiện vì hai ô
    readonly ở trên vẫn đúng tên mình.

    Vì vậy chỉ điền khi hồ sơ có GIẤY TỜ CỦA CHÍNH NGƯỜI ĐANG ĐĂNG NHẬP (thường là ảnh CCCD người
    dân tải lên) và đối chiếu khớp. Không khớp, hoặc không đọc được tài khoản → trả None và để
    trống cả khối cho cán bộ nhập tay.
    """
    if not (ctx_id or ctx_name):
        return None
    for source, id_key, name_key in (
        ("chs", "ChuHoSo_SoDinhDanh", "ChuHoSo_HoTen"),
        ("nop", "NguoiNop_SoDinhDanh", "NguoiNop_HoTen"),
    ):
        khop = _match(
            ctx_id,
            ctx_name,
            _digits(values.get(id_key)),
            _fold(_plain(values.get(name_key)) or ""),
        )
        if khop is True:
            return source
    return None


def _nop_area(values: dict, nop_source: str | None, cho_phep_bo_khuyet: bool) -> dict | None:
    """Địa chỉ cho khối NGƯỜI NỘP — cùng luật với `pick`, chỉ khác là làm trên object địa chỉ."""
    if nop_source is None:
        return None
    chs_area = _area(values.get("ChuHoSo_NoiCuTru"))
    nop_area = _area(values.get("NguoiNop_NoiCuTru"))
    if nop_source == "chs":
        return chs_area or (nop_area if cho_phep_bo_khuyet else None)
    return nop_area or (chs_area if cho_phep_bo_khuyet else None)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    is_org = _is_org(values)
    ctx_id, ctx_name = _account_anchor(options)
    same_person = _same_person(values, ctx_id, ctx_name)
    # Hai khối facts CHẮC CHẮN là hai người khác nhau → cấm mọi việc chép nhân thân chéo.
    khac_nguoi = _nop_block_is_other_person(values)
    # Khối nào là nhân thân của chính tài khoản đang đăng nhập. None = chưa xác minh được ⇒ KHÔNG
    # phát bất kỳ ô nào của khối "Thông tin người nộp" (xem `_khoi_cua_nguoi_dang_nhap`).
    nop_source = _khoi_cua_nguoi_dang_nhap(values, ctx_id, ctx_name)

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        # Ô đang bị cổng ẩn theo "Đối tượng nộp hồ sơ" thì không phát (xem docstring).
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
        """Trả (giá trị cho khối NGƯỜI NỘP, giá trị cho khối CHỦ HỒ SƠ).

        Khối người nộp CHỈ lấy từ đúng khối facts của người đang đăng nhập; chưa xác minh được thì
        trả None để không ô nào được phát. Bổ khuyết chéo chỉ xảy ra khi hai khối là MỘT người.
        """
        nop_raw = values.get(nop_key)
        chs_raw = values.get(chs_key)
        cho_phep_bo_khuyet = same_person and not khac_nguoi

        chs_out = (chs_raw or nop_raw) if cho_phep_bo_khuyet else chs_raw
        if nop_source == "chs":
            nop_out = chs_out
        elif nop_source == "nop":
            nop_out = (nop_raw or chs_raw) if cho_phep_bo_khuyet else nop_raw
        else:
            nop_out = None
        return nop_out, chs_out

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
    add("CongDan_ngaySinhCongDan", _date(nop_ngay_sinh))
    add("CongDan_gioiTinhCongDan", _gender(nop_gioi_tinh, nop_identity))
    add("CongDan_danTocCongDan", _plain(nop_dan_toc))
    add("CongDan_ngayCapCmnd", nop_ngay_cap)
    add("CongDan_noiCapCmnd", nop_noi_cap)
    add("CongDan_diDong", _phone(nop_dien_thoai))
    add("CongDan_email", _plain(nop_email))
    add("CongDan_fax", _plain(nop_fax))
    if is_org and nop_source == "chs":
        # Chỉ khi chính người của tổ chức đi nộp thì khối người nộp mới mang tên/MST tổ chức đó.
        # Nộp thay theo uỷ quyền thì người được uỷ quyền là CÁ NHÂN — điền tên tổ chức vào đây là sai.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)

    nop_area = _nop_area(values, nop_source, same_person and not khac_nguoi)
    if nop_area:
        add("CongDan_maTinhThanh", _province_label(nop_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
        add("CongDan_diaChi", _plain(nop_area.get("diaChi")))

    # --- Khối CHỦ HỒ SƠ: phát ĐỦ, KHÔNG dựa vào checkbox "Người nộp là chủ hồ sơ" ---
    chs_identity = _digits(chs_so_raw)
    add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_TO_CHUC if is_org else _DOI_TUONG_CA_NHAN)
    add("ChuHoSo_tenChuHoSo", _plain(chs_ten))
    add("ChuHoSo_ngaySinhChuHoSo", _date(chs_ngay_sinh))
    add("ChuHoSo_gioiTinhChuHoSo", _gender(chs_gioi_tinh, chs_identity))
    add("ChuHoSo_danTocChuHoSo", _plain(chs_dan_toc))
    chs_ngay_cap = _date(chs_ngay_cap_raw)
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
    if not chs_area and same_person and not khac_nguoi:
        chs_area = _area(values.get("NguoiNop_NoiCuTru"))
    if chs_area:
        add("ChuHoSo_maTinhThanhCHS", _province_label(chs_area.get("tinh")))
        add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
        add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
    else:
        warnings.append(
            "Không đọc được địa chỉ chủ hồ sơ. Nút \"Người nộp là chủ hồ sơ\" của cổng KHÔNG sao chép "
            "địa chỉ, cán bộ cần nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ."
        )

    warnings.extend(_mode_warnings(values, same_person, nop_area, nop_source, ctx_id, ctx_name))
    if nop_source == "chs" and khac_nguoi:
        ten_uy_quyen = _plain(values.get("NguoiNop_HoTen"))
        warnings.append(
            "Hồ sơ có giấy uỷ quyền"
            + (f" cho {ten_uy_quyen}" if ten_uy_quyen else "")
            + ", nhưng tài khoản đang đăng nhập chính là chủ hồ sơ nên lần nộp này KHÔNG dùng uỷ "
            "quyền — hệ thống đã BỎ nhân thân của người được uỷ quyền, khối người nộp điền theo chủ "
            "hồ sơ. Nếu thực tế muốn người được uỷ quyền đi nộp thì đăng nhập bằng tài khoản của họ."
        )
    warnings.extend(_ho_so_warnings(values, chs_area))
    return out, warnings


def _mode_warnings(
    values: dict,
    same_person: bool,
    nop_area: dict | None,
    nop_source: str | None,
    ctx_id: str | None,
    ctx_name: str,
) -> list[str]:
    """Cảnh báo riêng cho từng mode người nộp — thứ cán bộ không thể tự thấy trên màn hình."""
    warnings: list[str] = []
    ho_ten_nop = _plain(values.get("NguoiNop_HoTen"))
    has_anchor = bool(ctx_id or ctx_name)

    # Chưa xác minh được người đang đăng nhập → khối người nộp để TRỐNG HẲN. Nói thẳng lý do và cách
    # gỡ, vì màn hình chỉ thấy các ô trống, không thấy vì sao.
    if nop_source is None:
        if not has_anchor:
            return [
                "Chưa đọc được tài khoản định danh đang đăng nhập trên cổng nên KHÔNG xác minh được "
                "ai đang đi nộp. Hệ thống CỐ Ý để trống toàn bộ khối \"Thông tin người nộp\" thay vì "
                "điền nhân thân của người trong giấy tờ — hai ô Họ tên/Số Căn cước phía trên là của "
                "tài khoản đăng nhập, điền các ô còn lại bằng người khác là sai lệch nhân thân. Mở "
                "lại trang sau khi đăng nhập rồi quét lại, hoặc cán bộ nhập tay."
            ]
        ai = _plain((ctx_name or "").title()) or "tài khoản đang đăng nhập"
        return [
            f"Hồ sơ đã tải lên KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập"
            + (f" (số căn cước {ctx_id})" if ctx_id else f" ({ai})")
            + ". Hệ thống CỐ Ý để trống toàn bộ khối \"Thông tin người nộp\" — điền ngày sinh, giới "
            "tính, địa chỉ của người khác vào hồ sơ mang tên người đang đăng nhập là sai lệch nhân "
            "thân. Cách gỡ: tải thêm CCCD của CHÍNH người đang đăng nhập rồi quét lại, hoặc đăng "
            "nhập bằng tài khoản của người có giấy tờ trong hồ sơ; cán bộ cũng có thể nhập tay."
        ]

    if same_person:
        # Mode B: cổng vẫn để trống khối chủ hồ sơ, cán bộ hay tưởng chỉ cần tick checkbox là xong.
        warnings.append(
            "Người nộp trùng chủ hồ sơ (hồ sơ không có giấy uỷ quyền): hệ thống đã điền ĐỦ cả hai "
            "khối. Nếu cán bộ tự tick \"Người nộp là chủ hồ sơ\", cổng có thể ghi đè phần đã điền — "
            "nên kiểm tra lại khối chủ hồ sơ sau khi tick."
        )
        return warnings

    # Mode A: hai người khác nhau — mode mặc định của thủ tục này.
    warnings.append(
        "Hồ sơ nộp thay: người đi nộp khác chủ hồ sơ (người tặng cho)"
        + (f", giấy tờ ghi người được uỷ quyền là {ho_ten_nop}" if ho_ten_nop else "")
        + ". Hai ô \"Họ và tên\" và \"Số Căn cước\" của khối người nộp là ô READONLY do cổng đổ từ "
        "tài khoản đang đăng nhập nên hệ thống KHÔNG điền (ghi vào đó là cổng xoá trắng Di động và "
        "Số Căn cước). TUYỆT ĐỐI không tick \"Người nộp là chủ hồ sơ\"."
    )

    # Ghi chú: rủi ro "đăng nhập bằng tài khoản của người khác rồi nộp hộ" KHÔNG còn phải cảnh báo ở
    # đây — tới nhánh này thì `nop_source` đã là "nop", tức tài khoản đang đăng nhập ĐÃ đối chiếu
    # khớp với người được uỷ quyền trong hồ sơ. Ca không khớp đã bị chặn và cảnh báo ở đầu hàm.

    if not _phone(values.get("NguoiNop_DienThoai")):
        warnings.append(
            "Không đọc được số điện thoại của người được uỷ quyền (giấy uỷ quyền không ghi số điện "
            "thoại). Ô \"Di động\" của khối người nộp là ô bắt buộc — cán bộ hỏi trực tiếp người nộp, "
            "KHÔNG lấy số ghi trong Văn bản tặng cho vì đó là số của chủ hồ sơ."
        )
    if not nop_area:
        warnings.append(
            "Không đọc được địa chỉ của người được uỷ quyền. Ba ô Tỉnh/Phường-Xã/Địa chỉ của khối "
            "người nộp là bắt buộc — cán bộ nhập tay theo địa chỉ thường trú ghi ở mục 1.2 của Giấy "
            "uỷ quyền."
        )
    return warnings


def _ho_so_warnings(values: dict, chs_area: dict | None) -> list[str]:
    """Cảnh báo về chính bộ giấy tờ hiến đất — các mâu thuẫn mà file mapping đã chỉ đích danh."""
    warnings: list[str] = []

    # Ngày sinh: giấy tờ thủ tục này hầu như chỉ ghi NĂM, mà ô ngày sinh của cổng cần đủ dd/mm/yyyy.
    thieu_ngay_sinh = [
        nhan
        for key, nhan in (("ChuHoSo_NgaySinh", "chủ hồ sơ"), ("NguoiNop_NgaySinh", "người nộp"))
        if values.get(key) and not _date(values.get(key))
    ]
    if thieu_ngay_sinh:
        warnings.append(
            "Giấy tờ chỉ ghi NĂM SINH nên ô \"Ngày Sinh\" của khối "
            + " và ".join(thieu_ngay_sinh)
            + " để trống — hệ thống KHÔNG tự đặt 01/01. Cần CCCD hoặc giấy tờ ghi đủ ngày-tháng-năm."
        )

    # Vợ/chồng đồng sử dụng: bước 2 không có ô nào cho người này, cán bộ dễ tưởng bị bỏ sót.
    dong_su_dung = _plain(values.get("DongSuDung_HoTen"))
    if dong_su_dung:
        warnings.append(
            f"Giấy chứng nhận còn đứng tên người đồng sử dụng ({dong_su_dung}). Bước này chỉ có MỘT "
            "khối chủ hồ sơ nên hệ thống không điền người đó — cán bộ kiểm tra hồ sơ có đủ chữ ký/uỷ "
            "quyền của cả hai người đồng sử dụng đất hay chưa."
        )

    # Tờ bản đồ lệch giữa giấy uỷ quyền và giấy chứng nhận là lỗi THẬT của hồ sơ mẫu, không tự sửa.
    so_thua = _plain(values.get("ThuaDat_SoThua"))
    to_ban_do = _plain(values.get("ThuaDat_SoToBanDo"))
    if so_thua or to_ban_do:
        warnings.append(
            "Thông tin thửa đất chỉ được lưu để đối chiếu, bước này KHÔNG có ô để điền"
            + (f" (thửa {so_thua}" if so_thua else "")
            + (f", tờ bản đồ {to_ban_do})" if so_thua and to_ban_do else (")" if so_thua else ""))
            + ". Số thửa/số tờ bản đồ hay lệch nhau giữa Giấy chứng nhận, Giấy uỷ quyền và Văn bản "
            "tặng cho — cán bộ đối chiếu bản gốc, hệ thống cố ý không tự đồng nhất."
        )

    if chs_area and not _plain(chs_area.get("xa")):
        warnings.append(
            "Không tách được Phường/Xã của chủ hồ sơ từ địa chỉ trong giấy tờ. Danh mục xã/phường của "
            "cổng chỉ nạp sau khi chọn đúng Tỉnh — cán bộ chọn lại Tỉnh rồi chọn Phường/Xã bằng tay."
        )
    return warnings
