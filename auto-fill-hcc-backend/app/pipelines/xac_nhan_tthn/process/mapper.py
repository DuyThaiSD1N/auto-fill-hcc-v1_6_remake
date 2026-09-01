"""Map compact TTHN facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.xac_nhan_tthn.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import remap_area

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


def _id_match(left, right) -> bool | None:
    """Hai số định danh có cùng một người không; thiếu một bên → None (không kết luận)."""
    left_digits, right_digits = _digits(left), _digits(right)
    if left_digits and right_digits:
        return left_digits == right_digits
    return None


def _name_match(left, right) -> bool | None:
    """Hai họ tên có trùng không (bỏ dấu, gộp khoảng trắng); thiếu một bên → None."""
    left_name, right_name = _fold(left), _fold(right)
    if left_name and right_name:
        return left_name == right_name
    return None


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
            # ỦY QUYỀN: Mục I = người được ủy quyền = CCCD upload (đi nộp hộ). Có giấy ủy quyền
            # thật thì chắc chắn KHÔNG phải bản thân → luôn "Khác".
            add("quanhevoinguoiduocxacminh", "2")
            # Ô nhập cạnh "Khác": chữ quan hệ trên tờ khai; tờ khai không ghi thì chính giấy ủy
            # quyền đã nói rõ vai của người đi nộp.
            add_relation_other(values.get("ToKhaiYeuCau_QuanHe"), _RELATION_OTHER_POA)
            add("HoVaTenC", values.get("Cccd_HoTen"))
            add("NgaySinhC", values.get("Cccd_NgaySinh"))
            add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
            add("LoaiGiayToDinhDanhC", id_doc_type("Thẻ căn cước công dân", issuer))
            add("SoGiayToTuyThanC", values.get("Cccd_SoDinhDanh"))
            add("NgayCapDDC", values.get("Cccd_NgayCap"))
            add("NoiCapDDC", issuer)
            add("nycLoaiCuTru", "Thường trú")
            if residence:
                add("nycNoiCuTru", "1")
                add("nycNoiCuTru_TrongNuoc", residence)
            else:
                add("nycNoiCuTru", "1", default=True)
                add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
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
                req_id = _digits(req_sdd)
                card_id = _digits(values.get("Cccd_SoDinhDanh"))
                req_name = _fold(req_ten)
                card_name = _fold(values.get("Cccd_HoTen"))
                if req_id and card_id:
                    card_is_requester = req_id == card_id
                elif req_name and card_name:
                    card_is_requester = req_name == card_name
                else:
                    card_is_requester = True   # không đủ dữ kiện để bác bỏ
                card = values if card_is_requester else {}
                cccd_ten = req_ten or card.get("Cccd_HoTen")
                cccd_ns = card.get("Cccd_NgaySinh")  # tờ khai không ghi ngày sinh người yêu cầu
                cccd_sdd = req_sdd or card.get("Cccd_SoDinhDanh")
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

                add("HoVaTenC", cccd_ten)
                add("NgaySinhC", cccd_ns)
                add("SoDinhDanhC", cccd_sdd)
                add("LoaiGiayToDinhDanhC", id_doc_type("Thẻ căn cước công dân", noi_cap or issuer))
                add("SoGiayToTuyThanC", cccd_sdd)
                add("NgayCapDDC", ngay_cap)
                add("NoiCapDDC", noi_cap)
                add("nycLoaiCuTru", "Thường trú")
                if residence_i:
                    add("nycNoiCuTru", "1")
                    add("nycNoiCuTru_TrongNuoc", residence_i)
                else:
                    add("nycNoiCuTru", "1", default=True)
                    add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

        # --- MỤC II: Người được xác nhận ---
        if has_poa:
            # ỦY QUYỀN: Mục II = người ủy quyền (người CẦN giấy) từ giấy ủy quyền
            poa_issuer = values.get("PoA_SubjectIssuer") or default_issuer(values.get("PoA_SubjectIdDate"))
            poa_residence = _area(values.get("PoA_SubjectAddress"))
            add("HoVaTenC1", poa_subject_name)
            add("NgaySinhC1", values.get("PoA_SubjectDoB"))
            add("GioiTinhC1", values.get("PoA_SubjectGender"))
            add("QuocTichC1", "Việt Nam")
            add("SoDinhDanhC1", values.get("PoA_SubjectIdNumber"))
            add("LoaiGiayToDinhDanhC1", id_doc_type("Thẻ căn cước công dân", poa_issuer))
            add("SoGiayToTuyThanC1", values.get("PoA_SubjectIdNumber"))
            add("NgayCapDDC1", values.get("PoA_SubjectIdDate"))
            add("NoiCapDDC1", poa_issuer)
            add("nxnLoaiCuTru", "Thường trú")
            if poa_residence:
                add("nxnNoiCuTru", "1")
                add("nxnNoiCuTru_TrongNuoc", poa_residence)
            else:
                add("nxnNoiCuTru", "1", default=True)
                add("nxnNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: Mục II = người trên tờ khai (ưu tiên) hoặc CCCD upload
            # Ưu tiên: ToKhai_* → Cccd_* (từng field riêng lẻ)
            add("HoVaTenC1", values.get("ToKhai_HoTen") or values.get("Cccd_HoTen") or values.get("Gks_HoTen"))
            add("NgaySinhC1", values.get("ToKhai_NgaySinh") or values.get("Cccd_NgaySinh") or values.get("Gks_NgaySinh"))
            add("GioiTinhC1", values.get("ToKhai_GioiTinh") or values.get("Cccd_GioiTinh") or values.get("Gks_GioiTinh"))
            # Thẻ căn cước mẫu mới không in dân tộc — giấy khai sinh thường là nguồn DUY NHẤT.
            add("DanTocC1", values.get("ToKhai_DanToc") or values.get("Cccd_DanToc") or values.get("Gks_DanToc"))
            add("QuocTichC1", values.get("ToKhai_QuocTich") or values.get("Gks_QuocTich") or nationality)
            # Giấy tờ: ưu tiên tờ khai, fallback CCCD
            so_dinh_danh = values.get("ToKhai_SoDinhDanh") or values.get("Cccd_SoDinhDanh")
            ngay_cap = values.get("ToKhai_NgayCapGiayTo") or values.get("Cccd_NgayCap")
            noi_cap = values.get("ToKhai_NoiCapGiayTo") or issuer
            add("SoDinhDanhC1", so_dinh_danh)
            add("LoaiGiayToDinhDanhC1", id_doc_type("Thẻ căn cước công dân", noi_cap))
            add("SoGiayToTuyThanC1", so_dinh_danh)
            add("NgayCapDDC1", ngay_cap)
            add("NoiCapDDC1", noi_cap)
            add("nxnLoaiCuTru", "Thường trú")
            if residence:
                add("nxnNoiCuTru", "1")
                add("nxnNoiCuTru_TrongNuoc", residence)
            else:
                add("nxnNoiCuTru", "1", default=True)
                add("nxnNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

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

    return out

