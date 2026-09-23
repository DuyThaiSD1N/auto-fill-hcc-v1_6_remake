"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.115681).

NĂM QUYẾT ĐỊNH CHỦ CHỐT, đều rút từ `Mapping_1.115681_Minh_Phuong.xlsx` (2 bản DOM thật: cá nhân +
tổ chức) và bộ hồ sơ mẫu Công ty TNHH Dịch vụ Minh Phượng:

1. CHỦ HỒ SƠ LÀ PHÁP NHÂN, KHÔNG PHẢI CON NGƯỜI. Thủ tục chỉ dành cho "tổ chức kinh tế nhận chuyển
   nhượng…" nên `ChuHoSo_maDoiTuongNopHS` mặc định là "DN"; khối chủ hồ sơ phát TÊN TỔ CHỨC + MÃ SỐ
   THUẾ + ĐỊA CHỈ TRỤ SỞ, còn 7 ô nhân thân cá nhân đang bị cổng display:none nên KHÔNG phát. Nhân
   thân người đại diện theo pháp luật chỉ được dùng khi hồ sơ thật sự không có tổ chức nào (nhánh
   "Cá nhân", ngoài phạm vi thủ tục nhưng cổng vẫn render) — lúc đó mapper kèm cảnh báo.

2. Ô "TÊN CƠ QUAN/TỔ CHỨC" CỦA KHỐI NGƯỜI NỘP LÀ MỘT PHÁP NHÂN KHÁC. Hồ sơ mẫu uỷ quyền cho Công ty
   CP đo đạc bản đồ Quân Tiến đi nộp: ô số 3 và 4 của sheet mapping ghi tên + MST của ĐƠN VỊ ĐƯỢC UỶ
   QUYỀN, không phải của Minh Phượng. Chỉ khi chính người đại diện của chủ hồ sơ đi nộp thì hai ô đó
   mới mang tên/MST chủ hồ sơ (đúng ghi chú "Nếu người nộp là chính đại diện Công ty Minh Phượng…").

3. ⚑ KHỐI "THÔNG TIN NGƯỜI NỘP" CHỈ ĐƯỢC ĐIỀN KHI HỒ SƠ CÓ GIẤY TỜ CỦA CHÍNH NGƯỜI ĐANG ĐĂNG NHẬP.
   Cổng chỉ prefill Họ tên + Số Căn cước từ tài khoản; 11 ô còn lại do mình điền. Điền chúng bằng
   nhân thân của người khác thì hồ sơ gửi đi mang TÊN người đăng nhập nhưng NGÀY SINH/GIỚI TÍNH/
   ĐỊA CHỈ của người khác, mà cán bộ rất khó phát hiện vì hai ô readonly phía trên vẫn đúng tên.
   Vì vậy `_khoi_cua_nguoi_dang_nhap` đối chiếu số căn cước tài khoản với HAI khối nhân thân của hồ
   sơ (người đại diện pháp luật và người được uỷ quyền); không khớp khối nào (hoặc không đọc được
   tài khoản) thì KHÔNG phát một ô `CongDan_*` nào, kèm cảnh báo chỉ rõ cách gỡ. Khối chủ hồ sơ
   KHÔNG bị ảnh hưởng — nó là của TỔ CHỨC, không phải của phiên đăng nhập.

4. KHÔNG PHÁT `CongDan_tenCongDan` / `CongDan_soCmnd`. Hai ô readonly đó mà bị ghi thì script cổng
   XOÁ TRẮNG "Di động" + "Số Căn cước" — điền vào chính là làm hỏng ô bắt buộc vừa điền xong.

5. GIỚI TÍNH SUY TẤT ĐỊNH TỪ SỐ CĂN CƯỚC 12 SỐ khi giấy tờ không ghi, KHÔNG suy từ họ tên hay danh
   xưng "ông/bà". Chữ số thứ 4 là mã thế kỷ + giới tính (chẵn = Nam, lẻ = Nữ). Hồ sơ mẫu:
   024188002186 → Nữ (Thân Thị Thanh), 026192004454 → Nữ (Nguyễn Thị Hằng).

⚑ ĐỊA GIỚI: mọi địa chỉ đều đi qua `remap_area`, nên giấy tờ in địa giới TRƯỚC 01/7/2025 vẫn ra đúng
danh mục hiện hành của cổng ("Yên Bái / Xã Âu Lâu" → "Lào Cai / Phường Âu Lâu"; "Yên Bái / Phường
Đồng Tâm" → "Lào Cai / Phường Yên Bái"). Đây chính là hai ô sheet mapping còn để ngỏ.

Lọc ô theo đối tượng: khối chủ hồ sơ có 2 nhóm ô loại trừ nhau (`ORG_ONLY_FIELDS` /
`INDIVIDUAL_ONLY_FIELDS`); chọn "Cá nhân" thì nhóm tổ chức bị display:none và ngược lại. Phát ô đang
ẩn chỉ làm engine báo "không điền được" một cách vô cớ.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

# Option value thật của <select name="ChuHoSo_maDoiTuongNopHS"> trên cổng — sheet mapping, ô số 19:
# "CN = Cá nhân; DN = Doanh nghiệp/ Tổ chức; CQ = Cơ quan nhà nước; TC = Tổ chức khác".
_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_DOANH_NGHIEP = "DN"
_DOI_TUONG_CO_QUAN = "CQ"
_DOI_TUONG_TO_CHUC_KHAC = "TC"

# LLM trả nhãn tiếng Việt (schema `ChuHoSo_LoaiDoiTuong`) → option value của cổng.
_DOI_TUONG_BY_LABEL = {
    "ca nhan": _DOI_TUONG_CA_NHAN,
    "doanh nghiep": _DOI_TUONG_DOANH_NGHIEP,
    "co quan nha nuoc": _DOI_TUONG_CO_QUAN,
    "to chuc khac": _DOI_TUONG_TO_CHUC_KHAC,
}

# LLM hay trả nhãn chung chung ("Tổ chức") → đoán lại theo CHÍNH tên tổ chức, vì chọn sai ô này là
# cổng hiện nhầm nhóm ô bắt buộc. Thứ tự kiểm quan trọng: tổ chức chính trị - xã hội xét TRƯỚC cơ
# quan nhà nước ("cơ quan Ủy ban Mặt trận…" dính cả hai lưới).
_TO_CHUC_KHAC_HINTS = (
    "mat tran to quoc", "mttq", "hoi nong dan", "hoi lien hiep", "hoi cuu chien binh", "doan thanh nien",
    "cong doan", "lien doan lao dong", "hoi phu nu", "to chuc chinh tri", "cong dong dan cu",
)
_CO_QUAN_HINTS = (
    "uy ban nhan dan", "ubnd", "chi cuc", "ban quan ly", "van phong dang ky", "benh vien", "tram y te",
    "cong an", "vien kiem sat", "toa an", "kho bac", "tinh uy", "dang uy",
)
# Thủ tục 1.115681 chỉ áp dụng cho TỔ CHỨC KINH TẾ nên lưới doanh nghiệp là lưới hay trúng nhất.
_DOANH_NGHIEP_HINTS = (
    "cong ty", "doanh nghiep", "tap doan", "tong cong ty", "ngan hang", "hop tac xa", "chi nhanh",
    "xi nghiep", "nha may",
)


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
    """Địa chỉ thường là object {quocGia,tinh,xa,diaChi}; chuỗi trần thì dồn vào diaChi.

    `remap_area` là chỗ quy đổi địa giới cũ → mới, thứ bắt buộc phải có ở thủ tục này vì Giấy chứng
    nhận ĐKDN và các quyết định còn in "Xã Âu Lâu, Thành phố Yên Bái, Tỉnh Yên Bái".
    """
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
    """Mã số thuế giữ được dấu '-' của mã đơn vị phụ thuộc (vd 5200921208-001)."""
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
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1988") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _gender(value, identity: str | None) -> str | None:
    """Nam/Nữ. Nhận giá trị giấy tờ ghi rõ, nếu không thì suy từ chữ số thứ 4 của căn cước 12 số."""
    folded = _fold(_plain(value) or "")
    if folded in ("nam", "male", "m"):
        return "Nam"
    if folded in ("nu", "female", "f"):
        return "Nữ"
    if identity and len(identity) == 12 and identity.isdigit():
        return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"
    return None


def _is_org(values: dict) -> bool:
    """Chủ hồ sơ có phải pháp nhân không.

    Thủ tục 1.115681 theo định nghĩa chỉ áp dụng cho TỔ CHỨC KINH TẾ, nên chỉ cần thấy tên tổ chức
    hoặc mã số doanh nghiệp là chốt tổ chức. Nhãn `ChuHoSo_LoaiDoiTuong` = "Cá nhân" chỉ được nghe
    theo khi hồ sơ THẬT SỰ không trích ra tổ chức nào — tránh việc LLM đọc nhầm một dòng rồi kéo cả
    hồ sơ doanh nghiệp sang nhánh cá nhân (cổng sẽ ẩn mất 2 ô tên/MST và hiện 7 ô nhân thân trống).
    """
    if values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"):
        return True
    return _DOI_TUONG_BY_LABEL.get(_fold(values.get("ChuHoSo_LoaiDoiTuong"))) not in (
        None,
        _DOI_TUONG_CA_NHAN,
    )


def _org_option(loai_doi_tuong, org_name) -> str:
    """Option "Đối tượng nộp hồ sơ" cho chủ hồ sơ là TỔ CHỨC.

    Ưu tiên nhãn LLM đọc được; nhãn lạ (trống hoặc "Tổ chức" chung chung) thì đoán theo tên tổ chức.
    Không đoán ra được thì "DN" — thủ tục này chỉ dành cho TỔ CHỨC KINH TẾ, nên doanh nghiệp là
    mặc định đúng nhất, khác với các thủ tục đất đai chung (ở đó mặc định là "Tổ chức khác").
    """
    mapped = _DOI_TUONG_BY_LABEL.get(_fold(loai_doi_tuong))
    if mapped and mapped != _DOI_TUONG_CA_NHAN:
        return mapped
    name = _fold(org_name)
    if any(hint in name for hint in _TO_CHUC_KHAC_HINTS):
        return _DOI_TUONG_TO_CHUC_KHAC
    if any(hint in name for hint in _CO_QUAN_HINTS):
        return _DOI_TUONG_CO_QUAN
    if any(hint in name for hint in _DOANH_NGHIEP_HINTS):
        return _DOI_TUONG_DOANH_NGHIEP
    return _DOI_TUONG_DOANH_NGHIEP


def _account_anchor(options: dict | None) -> tuple[str | None, str]:
    """Nhân thân TÀI KHOẢN ĐANG ĐĂNG NHẬP, do extension đọc từ 2 ô readonly của cổng."""
    ctx = (options or {}).get("formContext") or {}
    ctx_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    ctx_name = _fold(_plain(ctx.get("applicantFullname")) or "")
    return ctx_id, ctx_name


def _match(left_id, left_name, right_id, right_name) -> bool | None:
    """So hai người: số định danh trước, rồi tới họ tên đã bỏ dấu. None = không đủ căn cứ.

    Số định danh là bằng chứng mạnh nhất nên được xét TRƯỚC: hai người có thể trùng họ tên nhưng
    không bao giờ trùng số căn cước. Họ tên so bản đã bỏ dấu vì bản scan hay rơi dấu và hay VIẾT HOA
    TOÀN BỘ ("THÂN THỊ THANH" ở Giấy chứng nhận ĐKDN so với "bà Thân Thị Thanh" ở Đơn đề nghị).
    """
    if left_id and right_id:
        return left_id == right_id
    if left_name and right_name:
        return left_name == right_name
    return None


def _khoi_cua_nguoi_dang_nhap(values: dict, ctx_id: str | None, ctx_name: str) -> str | None:
    """Khối facts nào LÀ NHÂN THÂN CỦA CHÍNH TÀI KHOẢN ĐANG ĐĂNG NHẬP.

    Trả "ddn" (người đại diện theo pháp luật của chủ hồ sơ), "nop" (người được uỷ quyền), hoặc
    None = KHÔNG XÁC MINH ĐƯỢC.

    ⚑ ĐÂY LÀ CỬA DUY NHẤT MỞ KHỐI "THÔNG TIN NGƯỜI NỘP", và cũng là thứ quyết định ô "Tên cơ quan/tổ
    chức" của khối đó mang pháp nhân nào (xem docstring module, điểm 2 và 3). Cổng chỉ prefill Họ
    tên + Số Căn cước của tài khoản; 11 ô còn lại do mình điền. Nếu điền chúng bằng nhân thân của
    một người KHÁC thì hồ sơ nộp lên mang tên người đang đăng nhập nhưng ngày sinh/giới tính/địa chỉ
    của người khác — sai lệch nhân thân ngay trên hồ sơ gửi cơ quan nhà nước, và cán bộ rất khó phát
    hiện vì hai ô readonly ở trên vẫn đúng tên mình.

    Thứ tự xét: người được uỷ quyền TRƯỚC, vì hồ sơ mẫu của thủ tục này nộp qua uỷ quyền và người
    đại diện pháp luật thường KHÔNG phải người ngồi nộp.
    """
    if not (ctx_id or ctx_name):
        return None
    for source, id_key, name_key in (
        ("nop", "NguoiNop_SoDinhDanh", "NguoiNop_HoTen"),
        ("ddn", "NguoiDaiDien_SoDinhDanh", "NguoiDaiDien_HoTen"),
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


def _cung_mot_nguoi(values: dict) -> bool:
    """Người được uỷ quyền có TRÙNG người đại diện theo pháp luật không (hồ sơ tự nộp).

    Chỉ True khi đối chiếu được và ra TRÙNG, hoặc khi khối người nộp TRỐNG HẲN (hồ sơ không có giấy
    uỷ quyền nên chỉ khai người đại diện một lần). Thiếu căn cứ mà khối người nộp CÓ khai thì coi là
    hai người khác nhau — ngả về "khác" là phía an toàn: cùng lắm bỏ trống vài ô cho cán bộ nhập
    tay, còn ngả nhầm sang "trùng" thì gán luôn nhân thân người này cho người kia.
    """
    nop_id = _digits(values.get("NguoiNop_SoDinhDanh"))
    nop_name = _fold(_plain(values.get("NguoiNop_HoTen")) or "")
    matched = _match(
        nop_id,
        nop_name,
        _digits(values.get("NguoiDaiDien_SoDinhDanh")),
        _fold(_plain(values.get("NguoiDaiDien_HoTen")) or ""),
    )
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
    # Khối nào là nhân thân của chính tài khoản đang đăng nhập. None = chưa xác minh được ⇒ KHÔNG
    # phát bất kỳ ô nào của khối "Thông tin người nộp" (xem `_khoi_cua_nguoi_dang_nhap`).
    nop_source = _khoi_cua_nguoi_dang_nhap(values, ctx_id, ctx_name)
    # Hồ sơ không có uỷ quyền (hoặc người được uỷ quyền chính là người đại diện) → được phép bổ
    # khuyết chéo giữa hai khối nhân thân vì đúng một con người.
    cung_nguoi = _cung_mot_nguoi(values)

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

    ten_to_chuc_chs = _plain(values.get("ChuHoSo_TenToChuc"))
    ma_so_thue_chs = _tax_code(values.get("ChuHoSo_MaSoThue"))

    # ---------------------------------------------------------------- khối NGƯỜI NỘP
    # `pick` chỉ lấy từ ĐÚNG khối facts của người đang đăng nhập; chưa xác minh được thì trả None để
    # không ô nào được phát. Bổ khuyết chéo chỉ xảy ra khi hai khối là MỘT người.
    def pick(nop_key: str, ddn_key: str):
        nop_raw = values.get(nop_key)
        ddn_raw = values.get(ddn_key)
        if nop_source == "nop":
            return (nop_raw or ddn_raw) if cung_nguoi else nop_raw
        if nop_source == "ddn":
            return (ddn_raw or nop_raw) if cung_nguoi else ddn_raw
        return None

    nop_identity = _digits(pick("NguoiNop_SoDinhDanh", "NguoiDaiDien_SoDinhDanh"))
    nop_ngay_cap = _date(pick("NguoiNop_NgayCap", "NguoiDaiDien_NgayCap"))
    # Nơi cấp mặc định CHỈ khi hồ sơ thật sự có giấy tờ định danh của người đó — không thì là bịa.
    nop_noi_cap = normalize_issuer(_plain(pick("NguoiNop_NoiCap", "NguoiDaiDien_NoiCap")))
    if not nop_noi_cap and nop_identity:
        nop_noi_cap = default_issuer(nop_ngay_cap)

    add("CongDan_ngaySinhCongDan", _date(pick("NguoiNop_NgaySinh", "NguoiDaiDien_NgaySinh")))
    add("CongDan_gioiTinhCongDan", _gender(pick("NguoiNop_GioiTinh", "NguoiDaiDien_GioiTinh"), nop_identity))
    add("CongDan_danTocCongDan", _plain(pick("NguoiNop_DanToc", "NguoiDaiDien_DanToc")))
    add("CongDan_ngayCapCmnd", nop_ngay_cap)
    add("CongDan_noiCapCmnd", nop_noi_cap)
    # Liên lạc: ưu tiên số/địa chỉ thư của CHÍNH người nộp. Chỉ khi người đại diện của tổ chức tự đi
    # nộp thì mới được dùng số của tổ chức — lúc đó họ đại diện cho chính tổ chức đó. Nộp thay theo
    # uỷ quyền mà mượn số 0912282787 của Giấy chứng nhận ĐKDN là điền số của người khác (sheet
    # mapping, ghi chú ô số 14).
    lien_lac_to_chuc = nop_source == "ddn"
    add("CongDan_diDong", _phone(
        pick("NguoiNop_DienThoai", "NguoiNop_DienThoai")
        or (values.get("ChuHoSo_DienThoai") if lien_lac_to_chuc else None)
    ))
    add("CongDan_email", _plain(
        pick("NguoiNop_Email", "NguoiNop_Email")
        or (values.get("ChuHoSo_Email") if lien_lac_to_chuc else None)
    ))
    add("CongDan_fax", _plain(
        pick("NguoiNop_Fax", "NguoiNop_Fax")
        or (values.get("ChuHoSo_Fax") if lien_lac_to_chuc else None)
    ))

    # ⚑ Ô "Tên cơ quan/tổ chức" + "MSDN/MST" của khối người nộp: pháp nhân của NGƯỜI ĐI NỘP.
    #   • nộp thay theo uỷ quyền → đơn vị được uỷ quyền (hồ sơ mẫu: Cty CP đo đạc bản đồ Quân Tiến);
    #   • người đại diện của chủ hồ sơ tự nộp → chính tổ chức chủ hồ sơ.
    if nop_source == "nop":
        add("CongDan_tenCoQuanToChuc", _plain(values.get("NguoiNop_TenToChuc")))
        add("CongDan_maSoThueNguoiNop", _tax_code(values.get("NguoiNop_MaSoThue")))
    elif nop_source == "ddn" and is_org:
        add("CongDan_tenCoQuanToChuc", ten_to_chuc_chs)
        add("CongDan_maSoThueNguoiNop", ma_so_thue_chs)

    nop_area = None
    if nop_source is not None:
        nop_area = _area(pick("NguoiNop_NoiCuTru", "NguoiDaiDien_NoiThuongTru"))
    if nop_area:
        add("CongDan_maTinhThanh", _province_label(nop_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
        add("CongDan_diaChi", _plain(nop_area.get("diaChi")))

    # ---------------------------------------------------------------- khối CHỦ HỒ SƠ
    # Phát ĐỦ, KHÔNG dựa vào checkbox "Người nộp là chủ hồ sơ" (hồ sơ uỷ quyền không được tick).
    if is_org:
        add("ChuHoSo_maDoiTuongNopHS", _org_option(values.get("ChuHoSo_LoaiDoiTuong"), ten_to_chuc_chs))
        add("ChuHoSo_tenCoQuanToChucCHS", ten_to_chuc_chs)
        add("ChuHoSo_maSoThueChuHoSo", ma_so_thue_chs)
    else:
        # Ngoài phạm vi thủ tục (chỉ dành cho tổ chức kinh tế) nhưng cổng vẫn render nhánh cá nhân —
        # điền theo người đại diện để cán bộ còn sửa, kèm cảnh báo ở `_ho_so_warnings`.
        ddn_identity = _digits(values.get("NguoiDaiDien_SoDinhDanh"))
        ddn_ngay_cap = _date(values.get("NguoiDaiDien_NgayCap"))
        ddn_noi_cap = normalize_issuer(_plain(values.get("NguoiDaiDien_NoiCap")))
        if not ddn_noi_cap and ddn_identity:
            ddn_noi_cap = default_issuer(ddn_ngay_cap)
        add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_CA_NHAN)
        add("ChuHoSo_tenChuHoSo", _plain(values.get("NguoiDaiDien_HoTen")))
        add("ChuHoSo_ngaySinhChuHoSo", _date(values.get("NguoiDaiDien_NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo", _gender(values.get("NguoiDaiDien_GioiTinh"), ddn_identity))
        add("ChuHoSo_danTocChuHoSo", _plain(values.get("NguoiDaiDien_DanToc")))
        add("ChuHoSo_soCMNDChuHoSo", ddn_identity)
        add("ChuHoSo_ngayCapCMNDCHS", ddn_ngay_cap)
        add("ChuHoSo_noiCapCMNDCHS", ddn_noi_cap)

    add("ChuHoSo_diDongLienLacCHS", _phone(values.get("ChuHoSo_DienThoai")))
    add("ChuHoSo_emailChuHoSo", _plain(values.get("ChuHoSo_Email")))
    add("ChuHoSo_faxChuHoSo", _plain(values.get("ChuHoSo_Fax")))

    # 3 ô địa chỉ này là thứ checkbox của cổng KHÔNG copy → luôn phát từ dữ liệu trích được.
    # Tổ chức thì lấy TRỤ SỞ CHÍNH; nhánh cá nhân thì lấy nơi thường trú người đại diện.
    chs_area = _area(values.get("ChuHoSo_TruSoChinh")) or _area(values.get("ChuHoSo_DiaChiLienHe"))
    if not is_org:
        chs_area = _area(values.get("NguoiDaiDien_NoiThuongTru")) or chs_area
    if chs_area:
        add("ChuHoSo_maTinhThanhCHS", _province_label(chs_area.get("tinh")))
        add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
        add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
    else:
        warnings.append(
            "Không đọc được địa chỉ trụ sở chính của tổ chức chủ hồ sơ. Nút \"Người nộp là chủ hồ "
            "sơ\" của cổng KHÔNG sao chép địa chỉ, cán bộ cần nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối "
            "chủ hồ sơ."
        )

    warnings.extend(_mode_warnings(values, nop_source, nop_area, cung_nguoi, ctx_id, ctx_name, seen))
    warnings.extend(_ho_so_warnings(values, is_org, chs_area))
    return out, warnings


def _mode_warnings(
    values: dict,
    nop_source: str | None,
    nop_area: dict | None,
    cung_nguoi: bool,
    ctx_id: str | None,
    ctx_name: str,
    seen: set[str],
) -> list[str]:
    """Cảnh báo riêng cho khối người nộp — thứ cán bộ không thể tự thấy trên màn hình."""
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
        return [
            "Hồ sơ đã tải lên KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập"
            + (f" (số căn cước {ctx_id})" if ctx_id else f" ({_plain(ctx_name.title()) or 'tài khoản đang đăng nhập'})")
            + ". Hệ thống CỐ Ý để trống toàn bộ khối \"Thông tin người nộp\" — điền ngày sinh, giới "
            "tính, địa chỉ của người khác vào hồ sơ mang tên người đang đăng nhập là sai lệch nhân "
            "thân. Cách gỡ: tải thêm CCCD của CHÍNH người đang đăng nhập rồi quét lại, hoặc đăng "
            "nhập bằng tài khoản của người được ủy quyền ghi trong Giấy ủy quyền; cán bộ cũng có thể "
            "nhập tay."
        ]

    if nop_source == "nop" and not cung_nguoi:
        # Mode A — mode mặc định của thủ tục này.
        warnings.append(
            "Hồ sơ nộp thay theo ủy quyền: người đi nộp"
            + (f" ({ho_ten_nop})" if ho_ten_nop else "")
            + " KHÔNG phải tổ chức chủ hồ sơ. Hai ô \"Họ và tên\" và \"Số Căn cước\" của khối người "
            "nộp là ô READONLY do cổng đổ từ tài khoản đang đăng nhập nên hệ thống KHÔNG điền (ghi "
            "vào đó là cổng xoá trắng Di động và Số Căn cước). TUYỆT ĐỐI không tick \"Người nộp là "
            "chủ hồ sơ\" — tick là cổng chép đè thông tin người nộp sang khối chủ hồ sơ."
        )
        if "CongDan_tenCoQuanToChuc" not in seen:
            warnings.append(
                "Không đọc được tên đơn vị của người được ủy quyền nên ô \"Tên cơ quan/tổ chức\" của "
                "khối người nộp để trống. ⚠ Ô này là ĐƠN VỊ ĐI NỘP THAY (theo mục \"Bên được ủy "
                "quyền\" của Giấy ủy quyền), KHÔNG phải tổ chức chủ hồ sơ — cán bộ nhập tay, đừng "
                "chép tên chủ hồ sơ sang."
            )
        if "CongDan_maSoThueNguoiNop" not in seen:
            warnings.append(
                "Ô \"MSDN/MST\" của khối người nộp để trống vì hồ sơ không kèm Giấy chứng nhận đăng ký "
                "doanh nghiệp của đơn vị được ủy quyền. Ô này KHÔNG bắt buộc; nếu cần điền thì lấy mã "
                "số thuế của chính đơn vị đi nộp, TUYỆT ĐỐI không mượn mã số doanh nghiệp của chủ hồ sơ."
            )
    elif nop_source == "ddn":
        warnings.append(
            "Người đại diện theo pháp luật của tổ chức đang trực tiếp đăng nhập nộp hồ sơ nên khối "
            "\"Thông tin người nộp\" được điền theo chính người đó, kèm tên và mã số thuế của tổ chức "
            "chủ hồ sơ. Nếu hồ sơ có Giấy ủy quyền cho đơn vị khác thì lần nộp này KHÔNG dùng ủy "
            "quyền — muốn dùng thì đăng nhập bằng tài khoản của người được ủy quyền."
        )

    if "CongDan_diDong" not in seen:
        warnings.append(
            "Không đọc được số điện thoại của người đi nộp. Ô \"Di động\" của khối người nộp là ô BẮT "
            "BUỘC (*) — cán bộ hỏi trực tiếp người nộp. ⚠ KHÔNG lấy số điện thoại trên Giấy chứng "
            "nhận đăng ký doanh nghiệp vì đó là số của tổ chức chủ hồ sơ."
        )
    if not nop_area:
        warnings.append(
            "Không đọc được địa chỉ của người đi nộp. Ba ô Tỉnh/Phường-Xã/Số nhà-Đường-Tổ của khối "
            "người nộp đều BẮT BUỘC (*) — cán bộ nhập tay theo căn cước của người nộp, hoặc theo địa "
            "chỉ trụ sở đơn vị được ủy quyền ghi trong Giấy ủy quyền."
        )
    return warnings


def _ho_so_warnings(values: dict, is_org: bool, chs_area: dict | None) -> list[str]:
    """Cảnh báo về chính bộ giấy tờ — các mâu thuẫn mà file mapping đã chỉ đích danh."""
    warnings: list[str] = []

    if not is_org:
        warnings.append(
            "Thủ tục 1.115681 chỉ dành cho TỔ CHỨC KINH TẾ nhận chuyển nhượng quyền sử dụng đất, "
            "nhưng hồ sơ không trích ra được tên tổ chức hay mã số doanh nghiệp nào nên hệ thống tạm "
            "để \"Đối tượng nộp hồ sơ\" là Cá nhân. Cán bộ kiểm tra lại: nhiều khả năng còn thiếu "
            "Giấy chứng nhận đăng ký doanh nghiệp của tổ chức đứng đơn."
        )

    # Người đại diện đã thay đổi so với Quyết định chấp thuận chủ trương — lỗi THẬT của hồ sơ mẫu.
    if values.get("QDChapThuan_So") and values.get("NguoiDaiDien_HoTen"):
        warnings.append(
            "Quyết định chấp thuận chủ trương đầu tư"
            + (f" số {_plain(values.get('QDChapThuan_So'))}" if _plain(values.get("QDChapThuan_So")) else "")
            + " được cấp trước, có thể còn ghi NGƯỜI ĐẠI DIỆN CŨ của tổ chức. Hệ thống lấy người đại "
            "diện theo Giấy chứng nhận đăng ký doanh nghiệp mới nhất — cán bộ đối chiếu lại hai giấy "
            "trước khi tiếp nhận."
        )

    # Mâu thuẫn nơi thường trú của người đại diện giữa Đơn đề nghị và Giấy chứng nhận ĐKDN.
    ddn_area = _area(values.get("NguoiDaiDien_NoiThuongTru"))
    if is_org and ddn_area:
        warnings.append(
            "Đã trích được nơi thường trú của người đại diện theo pháp luật nhưng bước này KHÔNG có ô "
            "để điền (cổng ẩn hết nhóm nhân thân cá nhân khi \"Đối tượng nộp hồ sơ\" là Doanh nghiệp/"
            "Tổ chức). Giá trị chỉ lưu để đối chiếu — lưu ý Đơn đề nghị và Giấy chứng nhận đăng ký "
            "doanh nghiệp hay ghi địa chỉ thường trú KHÁC nhau."
        )

    # Ngày sinh: giấy tờ hay chỉ ghi NĂM, mà ô ngày sinh của cổng cần đủ dd/mm/yyyy.
    thieu_ngay_sinh = [
        nhan
        for key, nhan in (
            ("NguoiNop_NgaySinh", "người nộp"),
            ("NguoiDaiDien_NgaySinh", "người đại diện theo pháp luật"),
        )
        if values.get(key) and not _date(values.get(key))
    ]
    if thieu_ngay_sinh:
        warnings.append(
            "Giấy tờ chỉ ghi NĂM SINH của "
            + " và ".join(thieu_ngay_sinh)
            + " nên ô \"Ngày Sinh\" để trống — hệ thống KHÔNG tự đặt 01/01. Cần căn cước hoặc giấy "
            "tờ ghi đủ ngày-tháng-năm."
        )

    # Bên chuyển nhượng: ba hộ dân có đất, cán bộ dễ tưởng bị bỏ sót vì bước 2 không có ô nào.
    danh_sach_thua = _plain(values.get("KhuDat_DanhSachThua"))
    tong_dien_tich = _plain(values.get("KhuDat_TongDienTich"))
    if danh_sach_thua or tong_dien_tich:
        warnings.append(
            "Thông tin thửa đất và bên chuyển nhượng chỉ được lưu để đối chiếu — bước \"Thông tin "
            "người nộp\" KHÔNG có ô nào cho phần nghiệp vụ"
            + (f" (tổng diện tích đề nghị nhận chuyển nhượng {tong_dien_tich} m²)" if tong_dien_tich else "")
            + ". Các hộ đứng tên trên Giấy chứng nhận là BÊN CHUYỂN NHƯỢNG, không phải chủ hồ sơ. "
            "Phần kê khai này nằm ở eForm bước sau."
        )

    if chs_area and not _plain(chs_area.get("xa")):
        warnings.append(
            "Không tách được Phường/Xã trong địa chỉ trụ sở chủ hồ sơ. Danh mục xã/phường của cổng "
            "chỉ nạp sau khi chọn đúng Tỉnh — cán bộ chọn lại Tỉnh rồi chọn Phường/Xã bằng tay. Lưu "
            "ý Giấy chứng nhận đăng ký doanh nghiệp và các quyết định còn in địa giới TRƯỚC 01/7/2025."
        )
    return warnings
