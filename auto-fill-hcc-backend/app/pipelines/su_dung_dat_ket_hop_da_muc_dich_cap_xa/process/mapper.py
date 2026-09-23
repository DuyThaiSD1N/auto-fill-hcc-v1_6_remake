"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.115682).

SÁU QUYẾT ĐỊNH CHỦ CHỐT, rút từ `Mapping_1.115682_Su-dung-dat-ket-hop-da-muc-dich_Buoc2-Buoc3.xlsx`
và bộ hồ sơ mẫu đi kèm (Đơn Mẫu 13 + Thuyết minh Phương án + GCN AA 01695788 của ông Nguyễn Đức
Nhân, thửa 428 tờ bản đồ 264, TDP Cầu Mây 1, phường Sa Pa, tỉnh Lào Cai):

1. LUÔN PHÁT ĐỦ KHỐI CHỦ HỒ SƠ, kể cả khi người nộp trùng chủ hồ sơ. Checkbox "Người nộp là chủ hồ
   sơ" của cổng chỉ sao chép một phần, và hồ sơ mẫu của chính file mapping KHÔNG tick nó (cán bộ nộp
   thay). Cũng KHÔNG tự bấm checkbox đó: đổi trạng thái có thể làm cổng xoá dữ liệu vừa điền.

1b. ⚑ KHỐI "THÔNG TIN NGƯỜI NỘP" CHỈ ĐƯỢC ĐIỀN KHI HỒ SƠ CÓ GIẤY TỜ CỦA CHÍNH NGƯỜI ĐANG ĐĂNG NHẬP.
   Cổng chỉ prefill Họ tên + Số Căn cước từ tài khoản; 11 ô còn lại do mình điền. Điền chúng bằng
   nhân thân của người khác thì hồ sơ gửi đi mang TÊN người đăng nhập nhưng NGÀY SINH/GIỚI TÍNH/
   ĐỊA CHỈ của người khác, mà cán bộ rất khó phát hiện vì hai ô readonly phía trên vẫn đúng tên.
   `_khoi_cua_nguoi_dang_nhap` đối chiếu số căn cước tài khoản với hai khối facts; không khớp khối
   nào (hoặc không đọc được tài khoản) thì KHÔNG phát một ô `CongDan_*` nào, kèm cảnh báo chỉ rõ
   cách gỡ. Khối chủ hồ sơ KHÔNG bị ảnh hưởng — nó là của hồ sơ, không phải của phiên làm việc.

2. HAI MODE NGƯỜI NỘP được chốt bằng ĐỐI CHIẾU THẬT, không tin cờ LLM:
   • Mode A "nộp thay" — hai khối là hai người khác nhau. ⚑ Ở thủ tục này mode A là CHUYỆN THƯỜNG:
     hồ sơ mẫu do cán bộ NHÂM ĐẮC ĐẠT (Hưng Yên) nộp thay ông NGUYỄN ĐỨC NHÂN (Nghệ An).
   • Mode B "tự nộp"  — hai khối cùng một người.
   Mode quyết định việc BỔ KHUYẾT: ở mode B, ô nào của khối người nộp mà hồ sơ không ghi riêng thì
   lấy từ khối chủ hồ sơ (và ngược lại) — đúng một người nên chép là an toàn. Ở mode A thì TUYỆT ĐỐI
   không chép chéo: chép là gán nhân thân người này cho người kia.

   ⚑ MỐC CHỐT MODE là TÀI KHOẢN ĐỊNH DANH ĐANG ĐĂNG NHẬP, không phải suy đoán từ giấy tờ. Cổng
   prefill tài khoản vào hai ô readonly `CongDan_tenCongDan` / `CongDan_soCmnd`; extension đọc rồi
   gửi lên trong `options.formContext`.

3. KHÔNG PHÁT `CongDan_tenCongDan` / `CongDan_soCmnd`. Hai ô readonly đó mà bị ghi thì script cổng
   XOÁ TRẮNG "Di động" + "Số Căn cước" — điền vào chính là làm hỏng ô bắt buộc vừa điền xong.

4. LỌC Ô THEO ĐỐI TƯỢNG. Khối chủ hồ sơ có 2 nhóm ô loại trừ nhau (`ORG_ONLY_FIELDS` /
   `INDIVIDUAL_ONLY_FIELDS`): chọn "Cá nhân" thì nhóm tổ chức bị display:none và ngược lại.

5. ⚠⚠ KHÔNG BÊ CẢNH BÁO "LỆCH TỈNH" CỦA 1.115685 SANG ĐÂY. Ở thủ tục này hồ sơ mẫu có BA TỈNH khác
   nhau cùng lúc (thửa đất Lào Cai — thường trú chủ hồ sơ Nghệ An — thường trú người nộp Hưng Yên)
   và đó là hoàn toàn bình thường. Thứ đáng cảnh báo ở đây là điều ngược lại: nơi thường trú của chủ
   hồ sơ TRÙNG KHÍT địa chỉ thửa đất trong khi Giấy chứng nhận KHÔNG hề ghi nơi thường trú — dấu
   hiệu đã chép nhầm mục 2.e của GCN sang ô địa chỉ chủ hồ sơ.

6. ĐỐI CHIẾU HAI CON SỐ DIỆN TÍCH KẾT HỢP. Hồ sơ mẫu lệch thật: Đơn Mẫu 13 mục 5.2 ghi 258,5 m²,
   Thuyết minh mục IV.2 ghi 267,8 m² (bảng cơ cấu ngay dưới của chính Thuyết minh lại ghi 258,5 m²).
   Mapper KHÔNG tự chọn hộ và KHÔNG sửa số — chỉ nói ra để cán bộ soát, vì đây là dữ liệu quyết định
   nghĩa vụ tài chính. Cùng chỗ đó kiểm luôn trần 50% của Điều 99 Nghị định 102/2024/NĐ-CP.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_DOI_TUONG_TO_CHUC = "Tổ chức"
_DOI_TUONG_CA_NHAN = "Cá nhân"

# Độ dài hợp lệ của số giấy tờ định danh: CCCD/thẻ Căn cước 12 số, CMND cũ 9 số.
_DO_DAI_DINH_DANH_HOP_LE = (9, 12)

# Mẫu đơn theo Nghị định 102/2024/NĐ-CP cho thủ tục sử dụng đất kết hợp đa mục đích.
_MAU_DON_YEU_CAU = "13"

# Điều 99 Nghị định 102/2024/NĐ-CP: diện tích đất sử dụng kết hợp không vượt quá 50% diện tích đất
# sử dụng vào mục đích chính. Hồ sơ mẫu cố ý dừng ở 48% (258,5 / 538,0).
_TRAN_TY_LE_KET_HOP = 0.50

# Chênh lệch tương đối giữa hai nguồn diện tích kết hợp mà vẫn coi là do làm tròn, không phải lệch
# dữ liệu (258,5 vs 267,8 lệch 3,6% nên vẫn vượt ngưỡng này và bị cảnh báo).
_NGUONG_LECH_DIEN_TICH = 0.005


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
    """Mã số thuế giữ được dấu '-' của mã đơn vị phụ thuộc (vd 5200170752-001)."""
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
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1982") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _dien_tich(value) -> float | None:
    """Diện tích m² từ giấy tờ Việt: "258,5", "538,0 m2", "1.234,5 m²" → float.

    Dấu phẩy là dấu thập phân, dấu chấm là phân cách hàng nghìn (ngược quy ước Anh - Mỹ) nên phải
    bỏ dấu chấm TRƯỚC rồi mới đổi dấu phẩy thành dấu chấm.
    """
    text = _plain(value)
    if not text:
        return None
    match = re.search(r"\d[\d.,]*", text)
    if not match:
        return None
    raw = match.group(0).rstrip(".,")
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _so_dep(value: float) -> str:
    """In lại diện tích theo kiểu Việt để cảnh báo đọc giống hệt con số trong giấy."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


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
    không bao giờ trùng CCCD. Họ tên so bản đã bỏ dấu vì OCR chữ viết tay hay rơi dấu.
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
      • Khối người nộp TRỐNG HẲN (không số, không tên) → TRÙNG. Hồ sơ chỉ khai một người thì đó là
        người sử dụng đất tự đi nộp.
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

    Trả "chs" (khối chủ hồ sơ), "nop" (khối người đi nộp thay), hoặc None = KHÔNG XÁC MINH ĐƯỢC.

    ⚑ ĐÂY LÀ CỬA DUY NHẤT MỞ KHỐI "THÔNG TIN NGƯỜI NỘP". Cổng chỉ prefill Họ tên + Số Căn cước của
    tài khoản; 11 ô còn lại (ngày sinh, giới tính, dân tộc, ngày/nơi cấp, tỉnh, phường-xã, địa chỉ,
    di động, email, fax) do mình điền. Nếu điền chúng bằng nhân thân của một người KHÁC thì hồ sơ
    nộp lên mang tên người đang đăng nhập nhưng ngày sinh/giới tính/địa chỉ của người khác — sai
    lệch nhân thân ngay trên hồ sơ gửi cơ quan nhà nước, và cán bộ rất khó phát hiện vì hai ô
    readonly ở trên vẫn đúng tên mình.

    ⚠ Ở thủ tục này ca hay gặp nhất là CÁN BỘ NỘP THAY mà hồ sơ chỉ có giấy tờ của người dân — khi
    đó hàm này trả None và cả khối người nộp để trống, đúng như hồ sơ mẫu của file mapping (các ô
    của cán bộ Nhâm Đắc Đạt do cổng tự đổ từ tài khoản, không lấy từ giấy tờ nào).
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


def _canh_bao_dinh_danh(so: str | None, vai: str) -> str | None:
    """Số định danh sai độ dài → phát nhưng phải nói ra."""
    if not so or len(so) in _DO_DAI_DINH_DANH_HOP_LE:
        return None
    return (
        f"Số giấy tờ định danh của {vai} đọc được là \"{so}\" ({len(so)} chữ số) — không đúng định "
        "dạng CCCD 12 số hay CMND 9 số. Có thể đã đọc nhầm sang số phát hành Giấy chứng nhận, số "
        "vào sổ cấp Giấy chứng nhận hoặc số thửa. Hệ thống vẫn điền đúng con số ghi trong giấy tờ, "
        "cán bộ phải đối chiếu thẻ gốc/CSDLQG về dân cư rồi sửa lại trước khi nộp."
    )


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
        # Ô đang bị cổng ẩn theo "Đối tượng nộp hồ sơ" thì không phát (xem docstring, điểm 4).
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
    # ⚠ KHÔNG phát CongDan_tenCongDan / CongDan_soCmnd: hai ô readonly, ghi vào là cổng xoá trắng
    # "Di động" + "Số Căn cước" (xem docstring, điểm 3). `nop_ten`/`nop_identity` chỉ dùng để suy ra
    # nơi cấp mặc định và để cảnh báo.
    add("CongDan_ngaySinhCongDan", _date(nop_ngay_sinh))
    add("CongDan_gioiTinhCongDan", _plain(nop_gioi_tinh))
    add("CongDan_danTocCongDan", _plain(nop_dan_toc))
    add("CongDan_ngayCapCmnd", nop_ngay_cap)
    add("CongDan_noiCapCmnd", nop_noi_cap)
    add("CongDan_diDong", _phone(nop_dien_thoai))
    add("CongDan_email", _plain(nop_email))
    add("CongDan_fax", _plain(nop_fax))
    if is_org and nop_source == "chs":
        # Chỉ khi chính người của tổ chức đi nộp thì khối người nộp mới mang tên/MST tổ chức đó.
        # Nộp thay theo ủy quyền thì người được ủy quyền là CÁ NHÂN — điền tên tổ chức vào đây là sai.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)

    nop_area = _nop_area(values, nop_source, same_person and not khac_nguoi)
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
    add("ChuHoSo_noiCapCMNDCHS", chs_noi_cap)
    add("ChuHoSo_ngayCapCMNDCHS", chs_ngay_cap)
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
            "Không đọc được nơi thường trú của chủ hồ sơ. Nút \"Người nộp là chủ hồ sơ\" của cổng "
            "KHÔNG sao chép địa chỉ, cán bộ cần nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ "
            "theo mục 2 của Đơn Mẫu số 13 hoặc mục II.2 của Thuyết minh Phương án — TUYỆT ĐỐI "
            "không lấy địa chỉ thửa đất trên Giấy chứng nhận."
        )

    for so, vai in ((chs_identity, "chủ hồ sơ"), (nop_identity, "người nộp")):
        canh_bao = _canh_bao_dinh_danh(so, vai)
        if canh_bao:
            warnings.append(canh_bao)

    warnings.extend(_canh_bao_dien_tich_ket_hop(values))
    warnings.extend(_canh_bao_mau_don(values))
    warnings.extend(_canh_bao_nham_dia_chi_thua_dat(values, chs_area))
    warnings.extend(_mode_warnings(values, same_person, nop_area, nop_source, ctx_id, ctx_name))
    return out, warnings


def _canh_bao_dien_tich_ket_hop(values: dict) -> list[str]:
    """Hai con số quyết định hồ sơ mà cán bộ không thấy được trên màn hình bước 2.

    (a) Đơn Mẫu 13 và Thuyết minh Phương án lệch nhau về diện tích kết hợp — có thật ở hồ sơ mẫu.
    (b) Diện tích kết hợp vượt 50% tổng diện tích thửa (Điều 99 Nghị định 102/2024/NĐ-CP).
    """
    warnings: list[str] = []
    dt_don = _dien_tich(values.get("KetHop_DienTich"))
    dt_thuyet_minh = _dien_tich(values.get("KetHop_DienTichTheoThuyetMinh"))
    tong = _dien_tich(values.get("ThuaDat_TongDienTich"))

    if dt_don and dt_thuyet_minh:
        lech = abs(dt_don - dt_thuyet_minh) / max(dt_don, dt_thuyet_minh)
        if lech > _NGUONG_LECH_DIEN_TICH:
            warnings.append(
                f"LỆCH DIỆN TÍCH SỬ DỤNG KẾT HỢP giữa hai giấy tờ: Đơn Mẫu số 13 mục 5.2 ghi "
                f"{_so_dep(dt_don)} m², còn Thuyết minh Phương án mục IV.2 ghi "
                f"{_so_dep(dt_thuyet_minh)} m². Đây là con số quyết định phạm vi được phép sử dụng "
                "kết hợp và nghĩa vụ tài chính — hệ thống KHÔNG tự chọn hộ và KHÔNG sửa số. Cán bộ "
                "đối chiếu lại với bảng cơ cấu sử dụng đất trong Thuyết minh (bảng này hay khớp với "
                "Đơn) rồi yêu cầu người dân chỉnh lại cho thống nhất trước khi nộp."
            )

    dt_ket_hop = dt_don or dt_thuyet_minh
    if dt_ket_hop and tong:
        if dt_ket_hop > tong:
            warnings.append(
                f"Diện tích sử dụng kết hợp đọc được ({_so_dep(dt_ket_hop)} m²) LỚN HƠN tổng diện "
                f"tích thửa đất ({_so_dep(tong)} m²) — chắc chắn có chỗ đọc sai hoặc hồ sơ ghi sai. "
                "Cán bộ đối chiếu lại mục 4.2 và mục 5.2 của Đơn Mẫu số 13 với Giấy chứng nhận."
            )
        elif dt_ket_hop > tong * _TRAN_TY_LE_KET_HOP:
            ty_le = dt_ket_hop / tong * 100
            warnings.append(
                f"Diện tích sử dụng kết hợp ({_so_dep(dt_ket_hop)} m²) chiếm {ty_le:.1f}% tổng diện "
                f"tích thửa ({_so_dep(tong)} m²), vượt mức 50%. Cán bộ đối chiếu Điều 99 Nghị định "
                "102/2024/NĐ-CP và Điều 218 Luật Đất đai 2024 về giới hạn diện tích được sử dụng "
                "kết hợp trước khi tiếp nhận — hệ thống chỉ nêu, không tự điều chỉnh con số."
            )
    return warnings


def _canh_bao_mau_don(values: dict) -> list[str]:
    """Đơn phải theo Mẫu số 13 của Nghị định 102/2024/NĐ-CP — dùng mẫu khác thì nói ra, không sửa."""
    mau_so = _plain(values.get("Don_MauSo"))
    if not mau_so or _MAU_DON_YEU_CAU in re.sub(r"\D", " ", mau_so).split():
        return []
    return [
        f"Đơn trong hồ sơ in tiêu đề \"{mau_so}\", trong khi thủ tục sử dụng đất kết hợp đa mục đích "
        "dùng \"Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 13\" ban hành kèm Nghị "
        "định 102/2024/NĐ-CP. Hệ thống vẫn đính đúng tệp người dân nộp và KHÔNG tự sửa mẫu — cán bộ "
        "đề nghị người dân lập lại đơn theo đúng mẫu nếu nơi tiếp nhận yêu cầu."
    ]


def _canh_bao_nham_dia_chi_thua_dat(values: dict, chs_area: dict | None) -> list[str]:
    """Nơi thường trú chủ hồ sơ TRÙNG KHÍT địa chỉ thửa đất → dấu hiệu chép nhầm từ Giấy chứng nhận.

    ⚠ Cố ý NGƯỢC với 1.115685: ở đó lệch tỉnh mới là bất thường. Ở thủ tục này người xin sử dụng kết
    hợp rất hay thường trú tỉnh khác (hồ sơ mẫu: thường trú Nghệ An, thửa đất Lào Cai) nên LỆCH là
    bình thường, còn TRÙNG KHÍT cả ba cấp mới đáng soát: Giấy chứng nhận KHÔNG ghi nơi thường trú,
    chỉ ghi địa chỉ thửa đất ở mục 2.e — nếu LLM lấy nhầm mục đó thì hai địa chỉ sẽ giống hệt nhau.

    Vẫn chỉ là CẢNH BÁO, không chặn: người dân sống ngay trên thửa đất vẫn có thật.
    """
    thua_dat = _area(values.get("ThuaDat_DiaChi"))
    if not thua_dat or not chs_area:
        return []
    keys = ("tinh", "xa", "diaChi")
    if any(not _fold(thua_dat.get(k)) for k in keys):
        return []
    if any(_fold(thua_dat.get(k)) != _fold(chs_area.get(k)) for k in keys):
        return []
    return [
        "Nơi thường trú của chủ hồ sơ đang TRÙNG KHÍT địa chỉ thửa đất "
        f"({_plain(thua_dat.get('diaChi'))}, {_plain(thua_dat.get('xa'))}, "
        f"{_plain(thua_dat.get('tinh'))}). Giấy chứng nhận KHÔNG ghi nơi thường trú — nó chỉ ghi "
        "địa chỉ thửa đất ở mục 2.e — nên hai địa chỉ giống hệt nhau có thể là do lấy nhầm nguồn. "
        "Cán bộ đối chiếu lại mục 2 \"Địa chỉ/trụ sở chính\" của Đơn Mẫu số 13, mục II.2 của Thuyết "
        "minh và CCCD; ở thủ tục này người sử dụng đất thường trú ở tỉnh KHÁC nơi có thửa đất là "
        "chuyện bình thường."
    ]


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
            "Hồ sơ đã tải lên KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập"
            + (f" (số căn cước {ctx_id})" if ctx_id else f" ({ai})")
            + ". Đây là ca RẤT HAY GẶP ở thủ tục này — cán bộ một cửa nộp thay người dân. Hệ thống "
            "CỐ Ý để trống toàn bộ khối \"Thông tin người nộp\" (cổng đã tự đổ Họ tên + Số Căn cước "
            "từ tài khoản); cán bộ tự nhập ngày sinh, giới tính, địa chỉ, di động của CHÍNH MÌNH, "
            "KHÔNG lấy của chủ hồ sơ. Nếu chính người dân tự nộp thì tải thêm CCCD của người đó rồi "
            "quét lại."
        ]

    if same_person:
        warnings.append(
            "Người nộp trùng chủ hồ sơ (hồ sơ không có văn bản ủy quyền) — người sử dụng đất tự đi "
            "nộp. Hệ thống đã điền ĐỦ cả hai khối. Nếu cán bộ tự tick \"Người nộp là chủ hồ sơ\", "
            "cổng có thể ghi đè phần đã điền — nên kiểm tra lại khối chủ hồ sơ sau khi tick."
        )
        return warnings

    # Mode A: hai người khác nhau — ở thủ tục này là chuyện thường, vẫn phải soát kỹ.
    so_uy_quyen = _plain(values.get("UyQuyen_SoGiay"))
    warnings.append(
        "Hồ sơ nộp thay: người đi nộp khác chủ hồ sơ"
        + (f" (giấy tờ ghi người nộp là {ho_ten_nop}" if ho_ten_nop else "")
        + (f", văn bản ủy quyền số {so_uy_quyen})" if ho_ten_nop and so_uy_quyen else (")" if ho_ten_nop else ""))
        + ". Hai ô \"Họ và tên\" và \"Số Căn cước\" của khối người nộp là ô READONLY do cổng đổ từ "
        "tài khoản đang đăng nhập nên hệ thống KHÔNG điền (ghi vào đó là cổng xoá trắng Di động và "
        "Số Căn cước). TUYỆT ĐỐI không tick \"Người nộp là chủ hồ sơ\" — tick là cổng sao chép nhân "
        "thân người nộp đè lên khối chủ hồ sơ."
    )

    if not _phone(values.get("NguoiNop_DienThoai")):
        warnings.append(
            "Không đọc được số điện thoại của người đi nộp. Ô \"Di động\" của khối người nộp là ô "
            "bắt buộc (*) và là số nhận tin nhắn tiến độ hồ sơ — cán bộ nhập số của CHÍNH người "
            "đang đăng nhập, KHÔNG lấy số của chủ hồ sơ."
        )
    if not nop_area:
        warnings.append(
            "Không đọc được nơi thường trú của người đi nộp. Ba ô Tỉnh/Phường-Xã/Địa chỉ của khối "
            "người nộp là bắt buộc — cán bộ nhập tay theo CCCD của chính người đang đăng nhập, "
            "KHÔNG lấy địa chỉ của chủ hồ sơ và KHÔNG lấy địa chỉ thửa đất."
        )
    return warnings
