"""Map compact TTHN facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.xac_nhan_tthn.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import prefer_printed_street, upper_person_name

_DEFAULT_PURPOSE = "Sử dụng vào mục đích khác"
_DIVORCED_STATUS = "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai"
_WIDOWED_STATUS = "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai"
_MARRIED_STATUS = "Hiện tại đang có vợ/chồng"
_NEVER_MARRIED_STATUS = "Hiện tại chưa đăng ký kết hôn với ai"
# Option =5 của cổng: xác nhận CHƯA ĐKKH TRONG MỘT KHOẢNG THỜI GIAN đã qua, dù HIỆN TẠI đã có
# vợ/chồng. Nhãn lấy nguyên văn từ bảng đã đối chiếu với cổng ở app/pipelines/ket_hon/process/
# mapper.py (_TINH_TRANG_HON_NHAN["5"]) — kể cả khoảng trắng lạ trước dấu "…" thứ tư.
_PERIOD_MARRIED_STATUS = (
    "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng"
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _date_key(value) -> tuple | None:
    """dd/mm/yyyy -> tuple so sánh được; sai định dạng trả None (không kết luận)."""
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(value or "").strip())
    if not match:
        return None
    day, month, year = match.groups()
    return (int(year), int(month), int(day))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _normalize_commune_label(value) -> str:
    """Mở rộng viết tắt đơn vị hành chính để khớp option trên cổng."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    for pattern, prefix in (
        (r"^p(?:\.\s*|\s+)(.+)$", "Phường"),
        (r"^x(?:\.\s*|\s+)(.+)$", "Xã"),
    ):
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return f"{prefix} {match.group(1).strip()}"
    return text


def _id_doc_type_for(number, issuer) -> str:
    """Loại giấy tờ tùy thân theo SỐ: 9 chữ số là CMND cũ, CCCD/Căn cước luôn 12 chữ số.

    Số 12 chữ số (hoặc chưa rõ) mới phân loại tiếp theo nơi cấp (Bộ Công an → Thẻ Căn cước,
    Cục Cảnh sát → Thẻ căn cước công dân). Nhãn "Chứng minh nhân dân" giống option của eForm hộ tịch
    đang dùng ở trích lục.
    """
    if len(_digits(number)) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type("Thẻ căn cước công dân", issuer or "")


def _is_self_request(options: dict | None, cccd_name, cccd_id) -> bool:
    """Người yêu cầu có TRÙNG người trên CCCD upload không?

    So với tên + CCCD mà cổng đã điền sẵn cho NGƯỜI YÊU CẦU (formContext, lấy từ VNeID).
    Ưu tiên số căn cước; thiếu thì so tên (bỏ dấu). Thiếu cả hai → mặc định coi là bản thân
    (giữ hành vi cũ, an toàn cho ca tự làm phổ biến).
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    upload_id = _digits(cccd_id)
    if applicant_id and upload_id:
        return applicant_id == upload_id
    applicant_name = _fold(ctx.get("applicantFullname"))
    upload_name = _fold(cccd_name)
    if applicant_name and upload_name:
        return applicant_name == upload_name
    return True


# Vai HÀNH CHÍNH của cán bộ trên giấy tờ — KHÔNG phải quan hệ nhân thân của người đi xin giấy.
# Giấy XÁC NHẬN TTHN đã cấp mở đầu bằng "Xét đề nghị của ông/bà: <tên>, là công chức tư pháp hộ
# tịch..." — đó là CÁN BỘ đề nghị cấp giấy, không phải người yêu cầu. Agent rất hay bắt nhầm dòng
# này thành ToKhaiYeuCau_*, kéo theo mục I mang tên cán bộ mà số định danh lại của người được cấp.
_OFFICER_RELATION_MARKERS = (
    "cong chuc", "can bo", "chuyen vien", "tu phap ho tich", "ho tich",
    "uy ban nhan dan", "ubnd", "chu tich", "nguoi ky",
)


def _is_officer_relation(value) -> bool:
    """Chữ ở dòng quan hệ là chức danh cán bộ chứ không phải quan hệ nhân thân."""
    folded = _fold(value)
    return bool(folded) and any(marker in folded for marker in _OFFICER_RELATION_MARKERS)


_SELF_RELATION_WORDS = ("ban than", "tu khai")


def _classify_relation(value) -> str | None:
    """Quy đổi CHỮ trên tờ khai (dòng "Quan hệ với người được cấp...") sang mã radio cổng.

    "1" = Bản thân, "2" = Khác (bố/mẹ/con/vợ/chồng/anh/chị/em/cháu/... — bất kỳ chữ nào KHÁC
    "Bản thân"/"Tự khai"). Tờ khai không ghi dòng này thì trả None để caller lùi về so tên/CCCD.
    """
    folded = _fold(value)
    if not folded:
        return None
    if any(word in folded for word in _SELF_RELATION_WORDS):
        return "1"
    return "2"


_CCCD_LEN = 12          # số định danh cá nhân luôn đúng 12 chữ số
_ID_OCR_SLIP_MAX = 2    # số chữ số OCR được phép đọc thừa/thiếu so với thẻ


def _is_subsequence(short: str, long: str) -> bool:
    """`short` có phải `long` sau khi XÓA bớt vài ký tự (giữ nguyên thứ tự) không."""
    it = iter(long)
    return all(ch in it for ch in short)


def _is_ocr_slip_of_card(left_digits: str, right_digits: str) -> bool:
    """Hai chuỗi số là CÙNG một số trên thẻ, chỉ khác vì OCR đọc RƠI (hoặc nhân đôi) vài chữ số.

    Tờ khai viết tay hay bị OCR nuốt mất một chữ số: "046175013623" ra "04617503623". Chuỗi thiếu
    số đó không phải số định danh hợp lệ của BẤT KỲ ai (không đủ 12 chữ số), nên coi nó là số của
    một người khác là vô nghĩa — nhưng so bằng `==` thì nó vẫn "khác số" và kéo theo cả mục I:
    tên viết tay sai được giữ lại, ô quan hệ tick "Khác", và ô số định danh nhận 11 chữ số mà cổng
    chắc chắn từ chối.

    Chỉ nhận khi một bên là số thẻ ĐỦ 12 chữ số và chuỗi ngắn hơn nằm gọn trong nó theo đúng thứ
    tự (chỉ XÓA, không đổi chữ số nào) — lệch tối đa 2 chữ số. Ràng buộc này rất chặt: một số 11
    chữ số ngẫu nhiên chỉ có cỡ 12 phần 10^11 cơ hội lọt qua, nên không thể vô tình ghép nhân thân
    của hai người khác nhau. OCR đọc NHẦM chữ số (5 thành 6) vẫn bị coi là khác người như cũ.
    """
    short, long = sorted((left_digits, right_digits), key=len)
    if len(long) != _CCCD_LEN or len(short) == _CCCD_LEN:
        return False
    if not 0 < len(long) - len(short) <= _ID_OCR_SLIP_MAX:
        return False
    return _is_subsequence(short, long)


def _id_match(left, right) -> bool | None:
    """Hai số định danh có cùng một người không; thiếu một bên → None (không kết luận)."""
    left_digits, right_digits = _digits(left), _digits(right)
    if not (left_digits and right_digits):
        return None
    if left_digits == right_digits:
        return True
    return True if _is_ocr_slip_of_card(left_digits, right_digits) else False


def _is_one_digit_misread(left, right) -> bool:
    """Hai số 12 chữ số chỉ lệch ĐÚNG MỘT vị trí — dấu hiệu OCR đọc nhầm một chữ số viết tay.

    Cố ý KHÔNG gộp vào `_id_match`: ở đó đọc nhầm chữ số vẫn tính là khác người (quyết định quan
    hệ, mượn tên). Hàm này chỉ dùng kèm một bằng chứng độc lập khác (năm sinh / họ) ở chỗ gọi.
    """
    left_digits, right_digits = _digits(left), _digits(right)
    if len(left_digits) != _CCCD_LEN or len(right_digits) != _CCCD_LEN:
        return False
    return sum(a != b for a, b in zip(left_digits, right_digits)) == 1


def _birth_year(value) -> int | None:
    key = _date_key(value)
    if key:
        return key[0]
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return int(match.group(0)) if match else None


def _family_name(value) -> str:
    parts = _fold(value).split()
    return parts[0] if parts else ""


def _name_match(left, right) -> bool | None:
    """Hai họ tên có trùng không (bỏ dấu, gộp khoảng trắng); thiếu một bên → None."""
    left_name, right_name = _fold(left), _fold(right)
    if left_name and right_name:
        return left_name == right_name
    return None


def _is_foreign_area(area) -> bool:
    """Dia chi nay o NUOC NGOAI (quoc gia khac Viet Nam)."""
    if not isinstance(area, dict):
        return False
    quoc_gia = _fold(area.get("quocGia"))
    return bool(quoc_gia) and quoc_gia not in ("viet nam", "vietnam", "vn")


def _poa_subject_card(values: dict) -> dict:
    """Thẻ căn cước CỦA NGƯỜI ỦY QUYỀN (người cần giấy), gom từ PoA_SubjectCccd* hoặc Cccd_*.

    Chỉ nhận thẻ khi số trên thẻ khớp số trên giấy ủy quyền (trùng hẳn, hoặc OCR rơi/đọc nhầm một
    chữ số), hoặc giấy ủy quyền không ghi số. Số khác hẳn = thẻ của người khác → bỏ, không ghép
    nhân thân hai người.
    """
    poa_id = values.get("PoA_SubjectIdNumber")

    def belongs(card_id) -> bool:
        if not _digits(card_id):
            return False
        if not _digits(poa_id):
            return True
        return _id_match(card_id, poa_id) is True or _is_one_digit_misread(card_id, poa_id)

    if values.get("PoA_SubjectCccdSoDinhDanh") and belongs(values.get("PoA_SubjectCccdSoDinhDanh")):
        return {
            "HoTen": values.get("PoA_SubjectCccdHoTen"),
            "SoDinhDanh": values.get("PoA_SubjectCccdSoDinhDanh"),
            "NgaySinh": values.get("PoA_SubjectCccdNgaySinh"),
            "GioiTinh": values.get("PoA_SubjectCccdGioiTinh"),
            "NgayCap": values.get("PoA_SubjectCccdNgayCap"),
            "NoiCap": values.get("PoA_SubjectCccdNoiCap") or (
                default_issuer(values.get("PoA_SubjectCccdNgayCap"))
                if values.get("PoA_SubjectCccdNgayCap") else None),
            "NoiCuTru": _area(values.get("PoA_SubjectCccdNoiCuTru")),
        }
    # Agent đôi khi đặt thẻ người ủy quyền vào Cccd_* (vd hồ sơ chỉ kèm đúng một thẻ): số trùng hẳn
    # số trên giấy ủy quyền mới nhận — thẻ người đi nộp cũng nằm ở Cccd_*.
    if _digits(poa_id) and _id_match(values.get("Cccd_SoDinhDanh"), poa_id) is True:
        return {
            "HoTen": values.get("Cccd_HoTen"),
            "SoDinhDanh": values.get("Cccd_SoDinhDanh"),
            "NgaySinh": values.get("Cccd_NgaySinh"),
            "GioiTinh": values.get("Cccd_GioiTinh"),
            "NgayCap": values.get("Cccd_NgayCap"),
            "NoiCap": values.get("Cccd_NoiCap"),
            "NoiCuTru": _area(values.get("Cccd_NoiCuTru")),
        }
    # Không có thẻ người ủy quyền: vẫn dùng địa chỉ in trên thẻ nếu agent chỉ trả riêng field đó.
    return {"NoiCuTru": _area(values.get("PoA_SubjectCccdNoiCuTru"))}


def _add_residence(add, prefix: str, area, default: bool = False) -> None:
    """Phat muc "Noi cu tru" cho mot nguoi (prefix = nyc / nxn).

    Dia chi o NUOC NGOAI phai tick "Khac" (radio "2") roi dien vao o nhap tu do, KHONG tick
    "Trong nuoc": nhanh trong nuoc chi co dropdown Tinh/Xa cua Viet Nam nen "Tokyo"/"Tam A"
    khong khop option nao -- hai dropdown do giu nguyen gia tri cong tu dien san (vd "Phuong
    Tu Liem / Ha Noi"), ra mot dia chi lai vua sai vua trong nhu that.
    """
    if not area:
        add(f"{prefix}NoiCuTru", "1", default=True)
        add(f"{prefix}NoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
        return
    if _is_foreign_area(area):
        add(f"{prefix}NoiCuTru", "2")
        full_addr = ", ".join(
            part for part in (area.get("diaChi"), area.get("xa"), area.get("tinh")) if part
        )
        add(f"{prefix}NoiCuTru_NuocNgoai", {"quocGia": area.get("quocGia"), "diaChi": full_addr},
            default=default)
        return
    add(f"{prefix}NoiCuTru", "1")
    add(f"{prefix}NoiCuTru_TrongNuoc", area, default=default)


def _card_name_when_same_person(values: dict, khai_sdd, khai_ten=None) -> str | None:
    """Họ tên lấy theo THẺ CĂN CƯỚC khi tờ khai và thẻ nói về CÙNG MỘT CÁI TÊN.

    Tờ khai là bản VIẾT TAY nên OCR tên rất hay sai: rơi dấu hoặc đọc nhầm chữ ("Thiết" → "Thiệt",
    "Phượng" → "Phương", "Tú" → "Tí"). Thẻ căn cước là bản IN, đọc gần như chắc chắn đúng — và đây
    mới là tên phải khớp với CSDLQG về dân cư khi cổng đối chiếu.

    Bằng chứng duy nhất được chấp nhận là SỐ ĐỊNH DANH khớp — 12 chữ số, không phải phép so tên
    dễ đụng hàng. Thiếu số ở một bên hoặc số của hai người khác nhau thì giữ nguyên thứ tự nguồn
    cũ, KHÔNG đoán: mượn tên của người khác sang là ghép ra một nhân thân lai.

    Tên hai bên CHỈ KHÁC DẤU cũng là cùng một cái tên, nhưng KHÔNG dùng làm căn cứ ở đây: bản scan
    mờ thì OCR của chính tấm thẻ cũng đọc sai dấu, mà mapper chỉ thấy field đã trích, không còn tài
    liệu gốc nào để kiểm chứng bản nào mới đúng.
    """
    if _id_match(khai_sdd, values.get("Cccd_SoDinhDanh")) is not True:
        return None
    return values.get("Cccd_HoTen") or None


def _card_value_when_same_person(values: dict, khai_sdd, card_field: str):
    """Giá trị IN trên thẻ (ngày sinh, giới tính…) khi số định danh tờ khai trùng số trên thẻ.

    Cùng căn cứ với `_card_name_when_same_person`: chữ viết tay hay bị OCR đọc sai ("02/05" →
    "21/05"), còn thẻ là bản in đúng CSDLQG. Không trùng số → None, caller giữ thứ tự nguồn cũ.
    """
    if _id_match(khai_sdd, values.get("Cccd_SoDinhDanh")) is not True:
        return None
    return values.get(card_field) or None


def _card_id_when_id_matches(values: dict, khai_sdd):
    """Số định danh điền vào form: số 12 chữ số IN trên thẻ thắng số đọc từ tờ khai.

    Cùng lý do như `_card_name_when_same_person`, và ở đây còn bắt buộc: số đọc từ tờ khai chỉ khác
    số trên thẻ khi OCR rơi mất chữ số (xem `_is_ocr_slip_of_card`), tức là một chuỗi KHÔNG đủ 12
    chữ số — điền vào cổng là chắc chắn bị chặn. Không khớp thẻ thì giữ nguyên số trên tờ khai.
    """
    if _id_match(khai_sdd, values.get("Cccd_SoDinhDanh")) is not True:
        return khai_sdd
    return values.get("Cccd_SoDinhDanh") or khai_sdd


def _same_person(left_name, left_id, right_name, right_id) -> bool:
    """Hai khối khai có phải CÙNG một người không. Số định danh chốt trước, rồi mới tới tên.

    Thiếu dữ kiện ở một bên → False: chỗ gọi dùng hàm này để MƯỢN dữ liệu từ khối kia, mượn nhầm
    ra nhân thân lai hai người nên phải im lặng bỏ qua thay vì đoán.
    """
    by_id = _id_match(left_id, right_id)
    if by_id is not None:
        return by_id
    return _name_match(left_name, right_name) is True


def _relation_code(req_name, req_id, subject_name, subject_id, declared, fallback_self: bool) -> str | None:
    """Mã ô tích "(5) Quan hệ với người được cấp Giấy XNTTHN": "1" = Bản thân, "2" = Khác.

    Chốt bằng chính hai người ĐANG được điền vào form: mục I (người yêu cầu) so với mục II
    (người được cấp). Trùng người → "Bản thân"; khác người → "Khác" (caller điền thêm chữ
    quan hệ vào ô cạnh option). Thứ tự bằng chứng:

    1. SỐ ĐỊNH DANH — mạnh nhất; hai bên đều có số thì chốt theo số, kể cả khi tên trùng
       (trùng tên khác số là hai người khác nhau, rất phổ biến với tên Việt).
    2. CHỮ QUAN HỆ trên tờ khai (chỉ khi khối "người yêu cầu" đáng tin) — dùng khi thiếu số
       ở một bên, vì lời khai chính chủ đáng tin hơn phép so tên.
    3. HỌ TÊN — chốt cuối khi không có số lẫn chữ quan hệ.
    4. Không có dữ kiện nào → "1" nếu người yêu cầu chính là tài khoản VNeID đang đăng nhập
       (fallback_self), ngược lại None để người dùng tự chọn.
    """
    by_id = _id_match(req_id, subject_id)
    if by_id is not None:
        return "1" if by_id else "2"
    declared_code = _classify_relation(declared)
    if declared_code:
        return declared_code
    by_name = _name_match(req_name, subject_name)
    if by_name is not None:
        return "1" if by_name else "2"
    return "1" if fallback_self else None


# Tick "Khác" là cổng bắt buộc điền chữ quan hệ vào ô kẻ chấm ngay cạnh. Khi hồ sơ chỉ chứng minh
# được "hai người khác nhau" mà không nói quan hệ gì (không tờ khai, hoặc OCR rơi mất dòng quan
# hệ), không có cách nào suy ra quan hệ thật → điền chữ trung tính và đánh dấu default để
# extension tô VIỀN VÀNG cho người dùng sửa lại.
_RELATION_OTHER_FALLBACK = "Người thân"
# Có giấy ủy quyền thì quan hệ suy ra được từ chính tờ giấy, không phải đoán.
_RELATION_OTHER_POA = "Người được ủy quyền"


def _drop_birth_cert_leak(values: dict) -> None:
    """Bỏ khối ToKhaiYeuCau_*/ToKhai_* thật ra là CHA/MẸ đọc nhầm trên GIẤY KHAI SINH.

    Hồ sơ "CCCD + giấy khai sinh của chính mình" (kèm GKS để chứng minh dân tộc/ngày sinh, thứ thẻ
    căn cước mẫu mới không in) chỉ nói về MỘT người: người đó vừa là người yêu cầu vừa là người
    được cấp. Nhưng GKS còn in tên cha, tên mẹ, người đi khai sinh — trích lục mẫu mới in cả SỐ
    ĐỊNH DANH của cha/mẹ — nên agent hay đẩy họ sang khối "người yêu cầu"; mục I liền mang tên
    cha/mẹ và ô quan hệ tick "Khác" thay vì "Bản thân".

    Chỉ dọn khi tờ khai KHÔNG ghi dòng quan hệ: có dòng đó nghĩa là hồ sơ có TỜ KHAI thật với người
    khai hộ thật (trường hợp C), không phải ca này — không được đụng vào.
    """
    parents = [values.get("Gks_ChaHoTen"), values.get("Gks_MeHoTen")]
    if not any(parents) or _classify_relation(values.get("ToKhaiYeuCau_QuanHe")):
        return
    subject = values.get("Gks_HoTen")
    for prefix in ("ToKhaiYeuCau_", "ToKhai_"):
        name = values.get(f"{prefix}HoTen")
        # Trùng tên cha/mẹ là chắc chắn đọc nhầm. Ngoài ra, khi người được khai sinh chính là chủ
        # thẻ trong hồ sơ thì hồ sơ không có người thứ hai — mọi tên lạ lọt vào đây đều của GKS.
        leaked = any(_name_match(name, parent) for parent in parents) or (
            _name_match(subject, values.get("Cccd_HoTen")) is True
            and _name_match(name, subject) is False
        )
        if leaked:
            for key in [k for k in values if k.startswith(prefix)]:
                values.pop(key)


_RELATION_OTHER_PREFIX_RE = re.compile(r"^(?:là|la)\s+", re.IGNORECASE)


def _relation_other_text(value) -> str:
    """Chữ điền vào ô nhập cạnh option "Khác" của mục quan hệ.

    Giữ nguyên chữ trên tờ khai, chỉ dọn nhiễu OCR của dòng kẻ chấm và bỏ tiền tố "là"
    (nhãn trên cổng đã là "Khác:" nên "là con đẻ" → "Con đẻ"). Quan hệ là bản thân →
    trả "" để không điền gì vào ô "Khác".
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"[\s.·•…\-–—]+$", "", text).strip()
    text = _RELATION_OTHER_PREFIX_RE.sub("", text).strip()
    if not text or any(word in _fold(text) for word in _SELF_RELATION_WORDS):
        return ""
    return text[:1].upper() + text[1:]


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _normalize_commune_label(
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or ""
        ),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    remapped = remap_area(out)
    if isinstance(remapped, dict):
        remapped = {**remapped, "xa": _normalize_commune_label(remapped.get("xa"))}
    return remapped


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields for TTHN.

    Bốn trường hợp:

    A. BẢN THÂN (không có giấy ủy quyền, CCCD upload = người đăng nhập):
       - Mục I (người yêu cầu) = CCCD upload.
       - Mục II (người được xác nhận) = CCCD upload (cùng người).
       - Quan hệ = "1" (Bản thân).

    B. ỦY QUYỀN (có PoA_SubjectName từ giấy ủy quyền):
       - Người ủy quyền (Section I giấy ủy quyền) = người CẦN giấy → Mục II form.
       - Người được ủy quyền (Section II giấy ủy quyền) = người ĐI NỘP = CCCD upload → Mục I form.
       - Quan hệ = "2" (Khác).

    C. THÂN NHÂN NỘP HỘ, KHÔNG giấy ủy quyền (tờ khai ghi RIÊNG khối "người yêu cầu" ở đầu tờ khai
       khác người ở Section II — vd con đứng khai hộ cha mẹ):
       - Mục I = khối "người yêu cầu" đầu tờ khai (ToKhaiYeuCau_*), ƯU TIÊN CAO NHẤT — không lấy
         nhầm sang thông tin người được cấp (ToKhai_*) như trước.
       - Mục II = người được cấp (ToKhai_*/Cccd_*) như bình thường.
       - Quan hệ: "1" nếu số định danh/tên người yêu cầu trùng người được cấp, ngược lại "2"
         (Khác) kèm chữ quan hệ điền vào ô kẻ chấm cạnh option.

    D. CCCD-MISMATCH / KHÔNG có nguồn nào cho Mục I (không có khối người yêu cầu riêng, không có
       CCCD upload nào khớp):
       - Mục I: không đè (để cổng giữ thông tin người đăng nhập từ VNeID), chỉ set default loại cư trú.
       - Mục II = CCCD upload/tờ khai (người cần giấy).
       - Quan hệ: so mục I với mục II như case C ("1" khi cùng người, "2" khi khác người);
         không đủ dữ kiện cả hai phép so thì để trống (user tự chọn).
    """
    values = _by_name(fields)
    _drop_birth_cert_leak(values)
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
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    def add_relation_other(declared, fallback: str = _RELATION_OTHER_FALLBACK) -> None:
        """Ô kẻ chấm cạnh option "Khác": chữ trên tờ khai, thiếu thì chữ trung tính (viền vàng).

        Ô này chỉ được cổng render SAU khi tick "Khác" nên luôn phát ngay sau radio quan hệ.
        """
        text = _relation_other_text(declared)
        add("quanhekhac", text or fallback, default=not text)

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))
    # Đây là TỜ KHAI, không phải ảnh CCCD → nhân thân có thể LLM chỉ đặt ở ToKhai_*.
    # Vẫn coi là có người để không rụng cả khối khi thiếu Cccd_* (xem cổng bên dưới).
    has_tokhai = bool(values.get("ToKhai_SoDinhDanh") or values.get("ToKhai_HoTen"))
    # GIẤY KHAI SINH của chính người xin giấy: nguồn nhân thân hợp lệ cho mục II (dân tộc, giới
    # tính, ngày sinh) khi hồ sơ chỉ có nó — sau _drop_birth_cert_leak thì đây chắc chắn là người
    # được cấp, không phải cha/mẹ.
    has_gks = bool(values.get("Gks_HoTen"))
    # Khối "người yêu cầu" ghi RIÊNG ở đầu tờ khai — CÓ THỂ khác người được cấp ở Section II
    # (thân nhân đứng nộp hộ mà không kèm giấy ủy quyền chính thức).
    # Khối "người yêu cầu" chỉ đáng tin khi nó THẬT SỰ đến từ tờ khai. TỜ KHAI luôn ghi giấy tờ tùy
    # thân của người yêu cầu ngay dưới tên ("CC/CCCD số ... cấp ngày ... tại ..."), nên một cái TÊN
    # TRƠ TRỌI — không số định danh, không ngày/nơi cấp, không cả dòng quan hệ — gần như luôn là tên
    # bắt nhầm ở tài liệu khác: cán bộ ký giấy XNTTHN cũ, người làm chứng, người ký thay.
    #
    # Không chặn thì mục I ra ĐÚNG MỘT CÁI TÊN: nhân thân của thẻ trong hồ sơ đã bị guard bên dưới
    # giữ lại (thẻ là của người khác), phần còn lại vẫn là dữ liệu VNeID của người đăng nhập → một
    # mục I lai ba nguồn. Chốt này KHÔNG dựa vào ToKhaiYeuCau_QuanHe vì agent hay bỏ hẳn field đó.
    declared_requester_evidence = any(
        values.get(name) for name in (
            "ToKhaiYeuCau_SoDinhDanh",
            "ToKhaiYeuCau_NgayCapGiayTo",
            "ToKhaiYeuCau_NoiCapGiayTo",
        )
    ) or bool(
        values.get("ToKhaiYeuCau_QuanHe")
        and not _is_officer_relation(values.get("ToKhaiYeuCau_QuanHe"))
    )
    # Dòng "Xét đề nghị của ông/bà ..." trên giấy XNTTHN ĐÃ CẤP là cán bộ tư pháp hộ tịch, không phải
    # người yêu cầu → bỏ hẳn khối này, để mục I lùi về CCCD trong hồ sơ.
    has_declared_requester = bool(
        (values.get("ToKhaiYeuCau_HoTen") or values.get("ToKhaiYeuCau_SoDinhDanh"))
        and not _is_officer_relation(values.get("ToKhaiYeuCau_QuanHe"))
        and declared_requester_evidence
    )

    # --- Thông tin từ CCCD của người đi nộp (hoặc bản thân); thiếu thì lấy từ tờ khai ---
    issuer = (
        values.get("Cccd_NoiCap")
        or values.get("ToKhai_NoiCapGiayTo")
        or default_issuer(values.get("Cccd_NgayCap") or values.get("ToKhai_NgayCapGiayTo"))
    )
    nationality = values.get("Cccd_QuocTich") or "Việt Nam"
    # Tờ khai phản ánh nơi cư trú hiện tại; CCCD chỉ là nguồn dự phòng.
    residence = _area(values.get("ToKhai_NoiCuTru") or values.get("Cccd_NoiCuTru"))

    is_self = _is_self_request(options, values.get("Cccd_HoTen"), values.get("Cccd_SoDinhDanh"))

    # Phát hiện trường hợp ủy quyền: có PoA_SubjectName từ giấy ủy quyền
    poa_subject_name = values.get("PoA_SubjectName")
    has_poa = bool(poa_subject_name)
    declared_self = values.get("ToKhai_LaBanThan") is True or _fold(
        values.get("ToKhai_LaBanThan")
    ) in {"true", "1", "co"}

    # =========================================================
    # MỤC I & II cá nhân: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có CCCD + không có PoA → bỏ qua Mục I/II, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    # MỤC I & II: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có → bỏ qua thông tin cá nhân, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    if has_cccd or has_poa or has_tokhai or has_declared_requester or has_gks:

        # --- MỤC I: Người yêu cầu ---
        # Ô "Quan hệ với người được xác minh" LUÔN được add() TRƯỚC khối nhân thân (HoVaTenC...):
        # cổng dựng lại Mục I mỗi khi đổi option quan hệ, tick SAU sẽ xóa mất dữ liệu vừa điền.
        if has_poa:
            # NGUOI YEU CAU = nguoi GHI TREN TO KHAI, khong phai nguoi cam ho so di nop.
            #
            # Giay uy quyen kieu "nop ho + ky thay" KHONG doi vai nguoi yeu cau: to khai van ghi
            # ten nguoi uy quyen o dong "Ho, chu dem, ten nguoi yeu cau" va quan he "Ban than".
            # Ban cu luon lay chu the CCCD upload lam muc I va luon tick "Khac", nen moi ho so co
            # uy quyen deu ra SAI NGUOI o muc I kem o tich sai -- ma nhin van hop le.
            tk_req_name = values.get("ToKhaiYeuCau_HoTen")
            req_is_subject = bool(
                tk_req_name and poa_subject_name
                and _fold(tk_req_name) == _fold(poa_subject_name)
            )
            if tk_req_name:
                relation_code_poa = _classify_relation(values.get("ToKhaiYeuCau_QuanHe")) or (
                    "1" if req_is_subject else "2"
                )
                add("quanhevoinguoiduocxacminh", relation_code_poa)
                if relation_code_poa == "2":
                    add_relation_other(values.get("ToKhaiYeuCau_QuanHe"), _RELATION_OTHER_POA)
                # Nguoi yeu cau CHINH LA nguoi duoc cap -> dung chung mot bo giay to voi muc II,
                # khong muon so ho chieu ghi tren to khai roi ghep voi loai giay to the can cuoc.
                if req_is_subject:
                    req_id = values.get("PoA_SubjectIdNumber") or values.get("ToKhaiYeuCau_SoDinhDanh")
                    req_ngay_cap = values.get("PoA_SubjectIdDate")
                    req_noi_cap = values.get("PoA_SubjectIssuer")
                else:
                    req_id = values.get("ToKhaiYeuCau_SoDinhDanh")
                    req_ngay_cap = values.get("ToKhaiYeuCau_NgayCapGiayTo")
                    req_noi_cap = values.get("ToKhaiYeuCau_NoiCapGiayTo")
                add("HoVaTenC", upper_person_name(
                    _card_name_when_same_person(values, req_id, tk_req_name) or tk_req_name))
                add("NgaySinhC",
                    _card_value_when_same_person(values, req_id, "Cccd_NgaySinh")
                    or values.get("ToKhaiYeuCau_NgaySinh"))
                req_id = _card_id_when_id_matches(values, req_id)
                add("SoDinhDanhC", req_id)
                if req_id:
                    add("LoaiGiayToDinhDanhC",
                        _id_doc_type_for(req_id, req_noi_cap))
                add("SoGiayToTuyThanC", req_id)
                add("NgayCapDDC", req_ngay_cap)
                add("NoiCapDDC", req_noi_cap)
                add("nycLoaiCuTru", "Thường trú")
                residence_req = _area(values.get("ToKhaiYeuCau_NoiCuTru"))
            else:
                # To khai khong ghi nguoi yeu cau -> nguoi di nop dung ten minh, giu hanh vi cu.
                add("quanhevoinguoiduocxacminh", "2")
                add_relation_other(values.get("ToKhaiYeuCau_QuanHe"), _RELATION_OTHER_POA)
                add("HoVaTenC", upper_person_name(values.get("Cccd_HoTen")))
                add("NgaySinhC", values.get("Cccd_NgaySinh"))
                add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
                add("LoaiGiayToDinhDanhC", _id_doc_type_for(values.get("Cccd_SoDinhDanh"), issuer))
                add("SoGiayToTuyThanC", values.get("Cccd_SoDinhDanh"))
                add("NgayCapDDC", values.get("Cccd_NgayCap"))
                add("NoiCapDDC", issuer)
                add("nycLoaiCuTru", "Thường trú")
                residence_req = _area(values.get("Cccd_NoiCuTru"))
            _add_residence(add, "nyc", residence_req)
        else:
            # KHÔNG ỦY QUYỀN: Mục I ưu tiên khối "người yêu cầu" ghi RIÊNG ở đầu tờ khai
            # (ToKhaiYeuCau_*) — người này có thể KHÁC người được cấp (Section II/ToKhai_*), vd
            # thân nhân đứng khai hộ. Không có khối đó thì mới lùi về CCCD upload. Không có nguồn
            # nào cả thì KHÔNG đè field — để cổng giữ nguyên dữ liệu VNeID của người đăng nhập.
            req_ten = values.get("ToKhaiYeuCau_HoTen")
            req_sdd = values.get("ToKhaiYeuCau_SoDinhDanh")
            if has_declared_requester:
                # Thẻ trong hồ sơ thường là của NGƯỜI ĐƯỢC CẤP, không phải người đứng khai. Mượn bừa
                # thì mục I ra tên một người ghép với số định danh của người khác — sai kiểu đó trông
                # vẫn hợp lệ nên không ai soát ra. Chỉ mượn khi thẻ khớp chính người yêu cầu.
                by_id = _id_match(req_sdd, values.get("Cccd_SoDinhDanh"))
                by_name = _name_match(req_ten, values.get("Cccd_HoTen"))
                if by_id is not None:
                    card_is_requester = by_id
                elif by_name is not None:
                    card_is_requester = by_name
                else:
                    card_is_requester = True   # không đủ dữ kiện để bác bỏ
                card = values if card_is_requester else {}
                # Cùng lý do như mục II: khối "người yêu cầu" cũng là chữ VIẾT TAY, nên khi số
                # định danh của họ trùng số trên thẻ trong hồ sơ thì lấy tên IN trên thẻ.
                cccd_ten = (_card_name_when_same_person(values, req_sdd, req_ten)
                            or req_ten or card.get("Cccd_HoTen"))
                # Ngày sinh người yêu cầu: tờ khai CÓ ghi ngay dưới tên (ToKhaiYeuCau_NgaySinh).
                # Thiếu field đó thì Section II vẫn dùng được KHI hai khối là cùng một người (hồ sơ
                # tự khai, hoặc nhờ người khác nộp hộ nhưng người yêu cầu vẫn là chính chủ) — lúc
                # này thẻ trong hồ sơ là của người ĐI NỘP nên không được mượn ngày sinh của nó.
                if _same_person(
                    req_ten, req_sdd,
                    values.get("ToKhai_HoTen"), values.get("ToKhai_SoDinhDanh"),
                ):
                    tokhai_ns = values.get("ToKhai_NgaySinh")
                else:
                    tokhai_ns = None
                cccd_ns = (
                    _card_value_when_same_person(values, req_sdd, "Cccd_NgaySinh")
                    or values.get("ToKhaiYeuCau_NgaySinh")
                    or tokhai_ns
                    or card.get("Cccd_NgaySinh")
                )
                cccd_sdd = _card_id_when_id_matches(values, req_sdd) or card.get("Cccd_SoDinhDanh")
                ngay_cap = values.get("ToKhaiYeuCau_NgayCapGiayTo") or card.get("Cccd_NgayCap")
                noi_cap = values.get("ToKhaiYeuCau_NoiCapGiayTo") or (issuer if card_is_requester else None)
                residence_i = _area(values.get("ToKhaiYeuCau_NoiCuTru")) or (residence if card_is_requester else None)
            elif has_cccd:
                cccd_ten = values.get("Cccd_HoTen")
                cccd_ns = values.get("Cccd_NgaySinh")
                cccd_sdd = values.get("Cccd_SoDinhDanh")
                ngay_cap = values.get("Cccd_NgayCap")
                noi_cap = issuer
                residence_i = residence
            else:
                cccd_ten = cccd_ns = cccd_sdd = ngay_cap = noi_cap = residence_i = None

            if cccd_ten or cccd_sdd:
                # Quan hệ chốt bằng chính hai người sắp được điền: mục I (cccd_*) so với mục II
                # (ToKhai_*/Cccd_* — đúng biểu thức dùng ở khối mục II bên dưới). Trùng số định
                # danh hoặc trùng tên → "Bản thân"; khác người → "Khác" + chữ quan hệ ở ô kẻ chấm.
                # Chữ quan hệ trên tờ khai chỉ được tin khi khối "người yêu cầu" là thật.
                # Nhân thân mục I có thể đã MƯỢN thẻ trong hồ sơ (card_is_requester) — mượn xong
                # thì số định danh mục I trùng mục II một cách máy móc. So quan hệ phải dùng đúng
                # dữ kiện tờ khai tự khai ra, nếu không mọi hồ sơ nộp hộ đều thành "Bản thân".
                relation_code = _relation_code(
                    req_ten if has_declared_requester else cccd_ten,
                    req_sdd if has_declared_requester else cccd_sdd,
                    values.get("ToKhai_HoTen") or values.get("Cccd_HoTen") or values.get("Gks_HoTen"),
                    values.get("ToKhai_SoDinhDanh") or values.get("Cccd_SoDinhDanh"),
                    values.get("ToKhaiYeuCau_QuanHe") if has_declared_requester else None,
                    fallback_self=bool(is_self or declared_self),
                )
                if relation_code:
                    add("quanhevoinguoiduocxacminh", relation_code)
                # Chọn "Khác" thì cổng mở thêm ô nhập free-text ngay cạnh: điền đúng chữ quan hệ
                # trên tờ khai ("là con đẻ" → "Con đẻ"). Ô này chỉ tồn tại sau khi tick "Khác" nên
                # phải phát NGAY SAU radio quan hệ.
                if relation_code == "2":
                    add_relation_other(values.get("ToKhaiYeuCau_QuanHe") if has_declared_requester else None)

                add("HoVaTenC", upper_person_name(cccd_ten))
                add("NgaySinhC", cccd_ns)
                add("SoDinhDanhC", cccd_sdd)
                add("LoaiGiayToDinhDanhC", _id_doc_type_for(cccd_sdd, noi_cap or issuer))
                add("SoGiayToTuyThanC", cccd_sdd)
                add("NgayCapDDC", ngay_cap)
                add("NoiCapDDC", noi_cap)
                add("nycLoaiCuTru", "Thường trú")
                _add_residence(add, "nyc", residence_i)

        # --- MỤC II: Người được xác nhận ---
        if has_poa:
            # ỦY QUYỀN: Mục II = người ủy quyền (người CẦN giấy) từ giấy ủy quyền
            poa_issuer = values.get("PoA_SubjectIssuer") or default_issuer(values.get("PoA_SubjectIdDate"))
            # Giay uy quyen chi ghi VAN TAT (ten, nam sinh, so CCCD). To khai lai mo ta DAY DU
            # chinh nguoi uy quyen -> cung mot nguoi thi lay them ngay sinh du ngay/thang, gioi
            # tinh, dan toc tu do. Bo qua la muc II trong 3 o ma can bo phai go tay.
            #
            # KHONG muon khoi GIAY TO cua to khai: ho so ra nuoc ngoai co to khai ghi HO CHIEU
            # (so + ngay cap) trong khi giay uy quyen ghi so CCCD -> ghep ngay cap ho chieu vao
            # so the can cuoc la sai giay to ma nhin van hop le.
            _tk_id = _digits(values.get("ToKhai_SoDinhDanh"))
            _poa_id = _digits(values.get("PoA_SubjectIdNumber"))
            # Tờ khai viết tay: OCR hay đọc nhầm MỘT chữ số CCCD ("…3446" → "…3466") và cả tên
            # ("Phạm Minh Kha" → "Phạm Nhung Khae"). Lệch đúng một chữ số chỉ được coi là cùng người
            # khi có thêm bằng chứng độc lập: cùng năm sinh hoặc cùng họ.
            _tk_year = _birth_year(values.get("ToKhai_NgaySinh"))
            _poa_year = _birth_year(values.get("PoA_SubjectDoB"))
            tk_misread_poa_id = _is_one_digit_misread(_tk_id, _poa_id) and bool(
                (_tk_year and _poa_year and _tk_year == _poa_year)
                or (_family_name(values.get("ToKhai_HoTen"))
                    and _family_name(values.get("ToKhai_HoTen")) == _family_name(poa_subject_name))
            )
            tk_is_poa_subject = bool(
                (_fold(values.get("ToKhai_HoTen"))
                 and _fold(values.get("ToKhai_HoTen")) == _fold(poa_subject_name))
                or (_tk_id and _poa_id and _tk_id == _poa_id)
                or tk_misread_poa_id
            )

            card = _poa_subject_card(values)

            def _tk(name):
                return values.get(name) if tk_is_poa_subject else None

            def add_with_declaration_fallback(ui_name, primary, declared_name) -> None:
                """Nguồn chắc chắn (thẻ / giấy ủy quyền) trước; thiếu thì lấy TỜ KHAI.

                Tờ khai mục II vốn chính là người cần giấy, nên "không khớp" gần như luôn là OCR đọc sai
                chữ viết tay. Vẫn điền để cán bộ khỏi gõ tay, nhưng chưa xác nhận được cùng người thì
                đánh dấu default → extension tô viền vàng để soát lại.
                """
                if primary:
                    add(ui_name, primary)
                    return
                declared = values.get(declared_name)
                add(ui_name, declared, default=not tk_is_poa_subject)

            # Họ tên / số / ngày cấp / nơi cấp / giới tính: THẺ CĂN CƯỚC của người ủy quyền (bản IN,
            # đúng dữ liệu CSDLQG đối chiếu) → giấy ủy quyền → tờ khai.
            add("HoVaTenC1", upper_person_name(
                card.get("HoTen")
                or _card_name_when_same_person(
                    values, values.get("PoA_SubjectIdNumber"), poa_subject_name)
                or poa_subject_name))
            # Giấy ủy quyền thường chỉ ghi NĂM sinh; tờ khai (cùng người) có đủ ngày/tháng.
            add_with_declaration_fallback(
                "NgaySinhC1",
                card.get("NgaySinh") or _tk("ToKhai_NgaySinh") or values.get("PoA_SubjectDoB"),
                "ToKhai_NgaySinh",
            )
            add_with_declaration_fallback(
                "GioiTinhC1", card.get("GioiTinh") or values.get("PoA_SubjectGender"), "ToKhai_GioiTinh")
            add_with_declaration_fallback(
                "DanTocC1", _tk("ToKhai_DanToc") or values.get("PoA_SubjectDanToc"), "ToKhai_DanToc")
            add("QuocTichC1", "Việt Nam")
            subject_id = card.get("SoDinhDanh") or values.get("PoA_SubjectIdNumber")
            subject_issuer = card.get("NoiCap") or poa_issuer
            add("SoDinhDanhC1", subject_id)
            add("LoaiGiayToDinhDanhC1", _id_doc_type_for(subject_id, subject_issuer))
            add("SoGiayToTuyThanC1", subject_id)
            add("NgayCapDDC1", card.get("NgayCap") or values.get("PoA_SubjectIdDate"))
            add("NoiCapDDC1", subject_issuer)
            add("nxnLoaiCuTru", "Thường trú")
            # Nơi cư trú: TỜ KHAI (đúng mẫu đang điền) thắng "chỗ ở hiện tại" trên giấy ủy quyền — giấy
            # ủy quyền hay ghi nơi tạm trú lúc ký (vd người ở TP HCM ủy quyền về Đà Lạt), không phải nơi
            # cư trú khai cho giấy XNTTHN, và thường khác tỉnh nên tỉnh/xã không khớp option. Chưa chắc
            # cùng người thì vẫn lấy tờ khai nhưng viền vàng.
            declared_residence = _area(values.get("ToKhai_NoiCuTru"))
            poa_residence = declared_residence or _area(values.get("PoA_SubjectAddress"))
            poa_residence = prefer_printed_street(poa_residence, card.get("NoiCuTru"))
            _add_residence(
                add, "nxn", poa_residence,
                default=bool(declared_residence) and not tk_is_poa_subject,
            )
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: Mục II = người trên tờ khai (ưu tiên) hoặc CCCD upload
            # Ưu tiên: ToKhai_* → Cccd_* (từng field riêng lẻ)
            # Tên: thẻ căn cước THẮNG tờ khai khi số định danh hai bên trùng nhau (xem
            # _card_name_when_same_person) — cùng người thì bản IN đáng tin hơn bản viết tay.
            # Không trùng số thì giữ nguyên thứ tự cũ: tờ khai → thẻ → giấy khai sinh.
            add("HoVaTenC1", upper_person_name(
                _card_name_when_same_person(
                    values, values.get("ToKhai_SoDinhDanh"), values.get("ToKhai_HoTen"))
                or values.get("ToKhai_HoTen") or values.get("Cccd_HoTen") or values.get("Gks_HoTen")))
            # Ngày sinh + giới tính: cùng quy tắc với họ tên — thẻ căn cước trùng số với tờ khai thì lấy
            # bản IN trên thẻ; không trùng số thì giữ thứ tự tờ khai → thẻ → giấy khai sinh.
            tk_sdd = values.get("ToKhai_SoDinhDanh")
            card_is_subject = _id_match(tk_sdd, values.get("Cccd_SoDinhDanh")) is True
            add("NgaySinhC1",
                _card_value_when_same_person(values, tk_sdd, "Cccd_NgaySinh")
                or values.get("ToKhai_NgaySinh") or values.get("Cccd_NgaySinh") or values.get("Gks_NgaySinh"))
            add("GioiTinhC1",
                _card_value_when_same_person(values, tk_sdd, "Cccd_GioiTinh")
                or values.get("ToKhai_GioiTinh") or values.get("Cccd_GioiTinh") or values.get("Gks_GioiTinh"))
            # Thẻ căn cước mẫu mới không in dân tộc — giấy khai sinh thường là nguồn DUY NHẤT.
            add("DanTocC1", values.get("ToKhai_DanToc") or values.get("Cccd_DanToc") or values.get("Gks_DanToc"))
            add("QuocTichC1", values.get("ToKhai_QuocTich") or values.get("Gks_QuocTich") or nationality)
            # Giấy tờ: ưu tiên tờ khai, fallback CCCD
            so_dinh_danh = (
                _card_id_when_id_matches(values, values.get("ToKhai_SoDinhDanh"))
                or values.get("Cccd_SoDinhDanh")
            )
            ngay_cap = values.get("ToKhai_NgayCapGiayTo") or values.get("Cccd_NgayCap")
            noi_cap = values.get("ToKhai_NoiCapGiayTo") or issuer
            add("SoDinhDanhC1", so_dinh_danh)
            add("LoaiGiayToDinhDanhC1", _id_doc_type_for(so_dinh_danh, noi_cap))
            add("SoGiayToTuyThanC1", so_dinh_danh)
            add("NgayCapDDC1", ngay_cap)
            add("NoiCapDDC1", noi_cap)
            add("nxnLoaiCuTru", "Thường trú")
            # Thẻ căn cước trong hồ sơ là của CHÍNH người được cấp (trùng số) → sửa tên đường đọc sai
            # từ chữ viết tay theo bản in trên thẻ.
            if card_is_subject:
                residence = prefer_printed_street(residence, _area(values.get("Cccd_NoiCuTru")))
            _add_residence(add, "nxn", residence)

    # =========================================================
    # TÌNH TRẠNG HÔN NHÂN: ưu tiên TỜ KHAI → fallback GIẤY TỜ CHỨNG MINH
    # =========================================================
    death_number = values.get("DeathCert_Number")
    death_date = values.get("DeathCert_Date")
    death_agency = values.get("DeathCert_Agency")
    divorce_number = values.get("DivorceDecision_Number")
    divorce_date = values.get("DivorceDecision_Date")
    divorce_agency = values.get("DivorceDecision_Agency")
    def add_marriage_raw_inputs(number, date, agency) -> None:
        """Ô con của vùng động (=2 và =5) được render sau khi chọn option → phát thêm theo DOM name.

        Cả hai vùng dùng CHUNG bộ ô "Số / Ngày cấp / Cơ quan cấp giấy chứng nhận kết hôn" nên dùng
        lại y nguyên; chỉ vùng =5 có thêm hai mốc thời gian, extension điền theo vị trí.
        """
        add("soGiayTo", number)
        date_match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(date or "").strip())
        if date_match:
            day, month, year = date_match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            add("ngayCapGiayTo-day", day)
            add("ngayCapGiayTo-month", month)
            add("ngayCapGiayTo-year", year)
            add("ngayCapGiayTo-name-date-input", f"{year}-{month}-{day}")
        add("coQuanCapGiayTo", agency)

    marriage_spouse = values.get("Marriage_SpouseName")
    marriage_number = values.get("Marriage_Number")
    marriage_date = values.get("Marriage_Date")
    marriage_agency = values.get("Marriage_Agency")
    declared_status = _fold(values.get("TinhTrangHonNhanC1"))
    period_from = values.get("Period_TuNgay")
    period_to = values.get("Period_DenNgay")
    has_marriage = any((marriage_spouse, marriage_number, marriage_date, marriage_agency))

    # Hôn nhân HIỆN TẠI đăng ký SAU mốc ly hôn/khai tử của cuộc hôn nhân trước → người này đã kết
    # hôn LẠI. Chỉ kết luận khi cả hai mốc đều đọc được đúng dd/mm/yyyy; thiếu mốc nào thì để False
    # và giữ nguyên thứ tự ưu tiên cũ.
    _prior_end_keys = [key for key in (_date_key(divorce_date), _date_key(death_date)) if key]
    _marriage_key = _date_key(marriage_date)
    remarried_after_prior = bool(
        has_marriage and _marriage_key and _prior_end_keys and _marriage_key > max(_prior_end_keys)
    )

    # Ưu tiên 0: tờ khai xin xác nhận CHƯA ĐKKH TRONG MỘT KHOẢNG THỜI GIAN ĐÃ QUA mà HIỆN TẠI đã có
    # vợ/chồng (vd bổ sung hồ sơ mua bán đất diễn ra trước khi cưới). Cổng có option RIÊNG cho ca này
    # (=5); chọn nhầm "Hiện tại đang có vợ/chồng" (=2) là mất sạch khoảng thời gian — đúng cái người
    # dân cần xác nhận — và form cũng không hiện hai ô mốc thời gian để điền.
    if period_from and period_to and has_marriage:
        add("TinhTrangHonNhanC1", _PERIOD_MARRIED_STATUS)
        period_detail = {
            "voChongHoTen": marriage_spouse,
            "thoiDiemBatDau": period_from,
            "thoiDiemKetThuc": period_to,
        }
        period_detail = {key: value for key, value in period_detail.items() if value not in (None, "")}
        add("nxnLoaiTinhTrangHonNhan=5", period_detail)
        add_marriage_raw_inputs(marriage_number, marriage_date, marriage_agency)

    # Ưu tiên 0.5: hồ sơ có bản án ly hôn / giấy khai tử của vợ chồng CŨ nhưng giấy kết hôn hiện tại
    # lại đăng ký SAU mốc đó → đã kết hôn lại. Hai option =3/=4 đều kết thúc bằng "hiện tại chưa
    # đăng ký kết hôn với ai" nên chọn chúng là khai SAI sự thật; đúng phải là "Hiện tại đang có
    # vợ/chồng" (=2). Chỉ áp dụng khi tờ khai KHÔNG tự khai trạng thái (có khai thì theo tờ khai).
    elif remarried_after_prior and not declared_status:
        add("TinhTrangHonNhanC1", _MARRIED_STATUS)
        marriage_detail = {
            "voChongHoTen": marriage_spouse,
            "soGiayTo": marriage_number,
            "ngayCapGiayTo": marriage_date,
            "coQuanCapGiayTo": marriage_agency,
        }
        marriage_detail = {key: value for key, value in marriage_detail.items() if value not in (None, "")}
        if marriage_detail:
            add("nxnLoaiTinhTrangHonNhan=2", marriage_detail)
            add_marriage_raw_inputs(marriage_number, marriage_date, marriage_agency)

    # Ưu tiên 1: TỜ KHAI khai báo rõ ràng tình trạng hôn nhân
    elif declared_status and declared_status != "":
        if declared_status == _fold(_WIDOWED_STATUS):
            # GÓA: từ tờ khai, bổ sung giấy tử nếu có
            add("TinhTrangHonNhanC1", _WIDOWED_STATUS)
            if death_number and death_date and death_agency:
                add("nxnLoaiTinhTrangHonNhan=4", {
                    "soBanAnQuyetDinhLyHon": death_number,
                    "ngayCapBanAnQuyetDinhLyHon": death_date,
                    "coQuanCapBanAnQuyetDinhLyHon": death_agency,
                })
        elif declared_status == _fold(_DIVORCED_STATUS):
            # ĐÃ LY HÔN: từ tờ khai, bổ sung giấy ly hôn nếu có
            add("TinhTrangHonNhanC1", _DIVORCED_STATUS)
            if divorce_number and divorce_date and divorce_agency:
                add("nxnLoaiTinhTrangHonNhan=3", {
                    "soBanAnQuyetDinhLyHon": divorce_number,
                    "ngayCapBanAnQuyetDinhLyHon": divorce_date,
                    "coQuanCapBanAnQuyetDinhLyHon": divorce_agency,
                })
        elif declared_status == _fold(_MARRIED_STATUS):
            # HIỆN ĐANG CÓ VỢ/CHỒNG: từ tờ khai, bổ sung giấy kết hôn nếu có
            add("TinhTrangHonNhanC1", _MARRIED_STATUS)
            marriage_detail = {
                "voChongHoTen": marriage_spouse,
                "soGiayTo": marriage_number,
                "ngayCapGiayTo": marriage_date,
                "coQuanCapGiayTo": marriage_agency,
            }
            marriage_detail = {key: value for key, value in marriage_detail.items() if value not in (None, "")}
            if marriage_detail:
                add("nxnLoaiTinhTrangHonNhan=2", marriage_detail)
                add_marriage_raw_inputs(marriage_number, marriage_date, marriage_agency)
        elif declared_status == _fold(_NEVER_MARRIED_STATUS):
            # CHƯA KẾT HÔN: từ tờ khai
            add("TinhTrangHonNhanC1", _NEVER_MARRIED_STATUS)
    
    # Ưu tiên 2: FALLBACK sang GIẤY TỜ CHỨNG MINH khi tờ khai không có
    elif death_number and death_date and death_agency:
        # GÓA: vợ/chồng đã chết (từ giấy tử)
        add("TinhTrangHonNhanC1", _WIDOWED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=4", {
            "soBanAnQuyetDinhLyHon": death_number,
            "ngayCapBanAnQuyetDinhLyHon": death_date,
            "coQuanCapBanAnQuyetDinhLyHon": death_agency,
        })
    elif divorce_number and divorce_date and divorce_agency:
        # ĐÃ LY HÔN (từ giấy ly hôn)
        add("TinhTrangHonNhanC1", _DIVORCED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=3", {
            "soBanAnQuyetDinhLyHon": divorce_number,
            "ngayCapBanAnQuyetDinhLyHon": divorce_date,
            "coQuanCapBanAnQuyetDinhLyHon": divorce_agency,
        })
    elif marriage_number and marriage_date:
        # HIỆN ĐANG CÓ VỢ/CHỒNG (từ giấy kết hôn)
        add("TinhTrangHonNhanC1", _MARRIED_STATUS)
        marriage_detail = {
            "voChongHoTen": marriage_spouse,
            "soGiayTo": marriage_number,
            "ngayCapGiayTo": marriage_date,
            "coQuanCapGiayTo": marriage_agency,
        }
        marriage_detail = {key: value for key, value in marriage_detail.items() if value not in (None, "")}
        add("nxnLoaiTinhTrangHonNhan=2", marriage_detail)
        add_marriage_raw_inputs(marriage_number, marriage_date, marriage_agency)

    # =========================================================
    # MỤC ĐÍCH & TRẢ KẾT QUẢ
    # =========================================================
    add("mucdich", _DEFAULT_PURPOSE)
    # Mục đích cụ thể từ tờ khai/giấy XNTTHN cũ → ô "Nhập mục đích" free-text.
    add("nhapmucdichkhac", values.get("Purpose"))
    add("TraKQ", "1")
    # Ô (17) "Số lượng bản sao" là bắt buộc trên cổng nhưng tờ khai giấy không có mục này → mặc
    # định 1 bản, đánh dấu default để extension tô viền vàng cho cán bộ sửa nếu người dân xin nhiều.
    add("SoLuong", "1", default=True)

    return out

