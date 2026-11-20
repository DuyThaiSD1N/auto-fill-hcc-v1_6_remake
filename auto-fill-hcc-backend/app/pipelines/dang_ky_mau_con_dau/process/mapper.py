"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 2.001428 (Cổng DVC Bộ Công an).

Thứ tự nguồn theo file mapping (sheet "Ma trận đối chiếu"):
- Cơ quan, tổ chức (ô 1–8, 17, 20, 21): Văn bản đề nghị (Mẫu số 03) → Quyết định thành lập → Công văn đồng ý khắc dấu.
- Người nộp (ô 9–16): người ở mục 6 văn bản đề nghị (không có mục 6 thì người đứng đầu ở mục 2). Số giấy tờ, ngày sinh,
  giới tính, ngày cấp ưu tiên thẻ CCCD của CHÍNH người đó; nơi cấp ưu tiên dòng "Nơi cấp" của văn bản (đúng nhãn) khi
  văn bản ghi cùng số giấy tờ.

Ô (2) "Loại hình cơ quan/tổ chức": văn bản ghi số định danh của cơ quan → "có mã định danh" + ô (3); để trống → "Cơ quan
tổ chức khác" (mapping, cần người nộp xác nhận). Ô (17) "Loại hình con dấu" chỉ suy khi chắc: cơ quan nhà nước (có thể
dùng dấu Quốc huy) không phát.

Ô (5) và ô (8) mang ``waitMs``: danh sách nạp qua API (Phường/xã theo Tỉnh; Loại hình cơ quan nạp lại sau Nơi tiếp nhận)
nên extension phải chờ thêm rồi thử lại, không bỏ ngay (bản chạy thật 18/11 hụt cả hai ô).
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _gender,
    _issuer,
    _phone,
    _plain,
    _same_person,
)
# Email: làm sạch chung các thủ tục Bộ Công an (dấu phẩy OCR, tên miền đọc lệch), user 19/11/2026.
from app.pipelines._shared.formatting import clean_email as _email
from app.pipelines.dang_ky_mau_con_dau.process.schema import (
    CON_DAU_BCH_TRUNG_UONG,
    CON_DAU_DANG_TRUNG_UONG,
    CON_DAU_KHAC,
    LOAI_HINH_CO_MA,
    LOAI_HINH_KHAC,
    TRUONG_HOP_DANG,
    TRUONG_HOP_OPTIONS,
    UI_COMP_BY_NAME,
    WAIT_MS,
)

NOI_DUNG_MAC_DINH = "Đăng ký mẫu con dấu mới"
# Giấy tờ không ghi cách nhận kết quả: điền xong người nộp tự chọn rồi mới sang trang đính kèm (user 18/11/2026).
RESULT_WARNING = (
    "Chọn Hình thức nhận kết quả (*) ở mục Nhận kết quả: Trực tiếp hoặc Qua dịch vụ bưu chính công ích; chọn bưu chính "
    "thì nhập Địa chỉ nhận kết quả, rồi bấm \"Đồng ý và tiếp tục\" sang trang Thành phần hồ sơ để đính kèm."
)

# "Kính gửi: Phòng Cảnh sát QLHC về TTXH, Công an tỉnh An Bình" → "Công an tỉnh An Bình".
_POLICE_RE = re.compile(r"c[ôo]ng\s+an\s+(t[ỉi]nh|th[àa]nh\s+ph[ốo]|tp\.?)\s+([^,;.\n]+)", re.IGNORECASE)
_PASSPORT_RE = re.compile(r"^[A-Z]\d{7,8}$")
# Tên tổ chức đảng: đảng ủy / đảng bộ / chi bộ / cấp ủy (tỉnh ủy, thành ủy…) / ban cán sự, đảng đoàn. So trên chữ đã bỏ
# dấu nên "đăng ký" cũng thành "dang" — chỉ bắt cụm đi kèm "uy"/"bo"/"doan" để "Trung tâm Đăng kiểm" không lọt.
_PARTY_RE = re.compile(r"\b(dang uy|dang bo|chi bo|dang doan|ban can su dang|tinh uy|thanh uy|huyen uy|quan uy)\b")
_PARTY_CENTRAL_RE = re.compile(r"^(tinh uy|thanh uy)\b|\bdang uy\b.*\btrung uong\b")
# OCR hay đọc "Trường" (trường học) thành "Trưởng" (bộ mẫu thật: dòng tên ở mục 1). Chỉ sửa khi đứng trước tên loại
# trường — "Trưởng" đứng đó không có nghĩa.
_SCHOOL_OCR_RE = re.compile(
    r"\bTrưởng(?=\s+(?:PT[A-Z]*|TH[A-Z]*|Tiểu học|Mầm non|Mẫu giáo|Trung học|Phổ thông|Cao đẳng|Đại học|Chính trị|"
    r"Dân tộc|Bồi dưỡng|Trung cấp|Quân sự|Sĩ quan|Cán bộ)\b)"
)
# Văn bản đề nghị cũng có dòng "V/v đề nghị đăng ký mẫu con dấu" → LLM có khi đọc nhầm nó thành công văn đồng ý khắc dấu.
_REQUEST_SUBJECT = "de nghi dang ky mau con dau"


def _org_name(value) -> str | None:
    text = _text(value)
    return _SCHOOL_OCR_RE.sub("Trường", text) if text else None


def _drop_request_as_letter(values: dict) -> dict:
    """Bỏ CongVan_* khi đó thực ra là chính văn bản đề nghị (cùng số, hoặc trích yếu "đề nghị đăng ký mẫu con dấu")."""
    letter_no = fold(_plain(values.get("CongVan_So")) or "")
    request_no = fold(_plain(values.get("VanBan_So")) or "")
    subject = fold(_plain(values.get("CongVan_TrichYeu")) or "")
    if (letter_no and letter_no == request_no) or _REQUEST_SUBJECT in subject:
        return {key: value for key, value in values.items() if not key.startswith("CongVan_")}
    return values


def _text(value) -> str | None:
    """Chuỗi một dòng; ô chấm chấm / "trống" / "không" coi như không có."""
    text = _plain(value)
    if not text or not re.search(r"[0-9A-Za-zÀ-ỹ]", text):
        return None
    if fold(text) in ("trong", "khong", "khong co", "khong ap dung"):
        return None
    return text


def _lines(value) -> list[str]:
    """Danh sách nhiều dòng (giữ "- " đầu dòng, dấu câu cuối). LLM gộp một dòng "…; - …" thì tách lại."""
    if not isinstance(value, str):
        return []
    lines = [" ".join(line.split()) for line in value.replace("\r", "\n").split("\n")]
    lines = [line for line in lines if re.search(r"[0-9A-Za-zÀ-ỹ]", line)]
    if len(lines) == 1 and re.search(r";\s*-\s", lines[0]):
        parts = re.split(r";\s*(?=-\s)", lines[0])
        lines = [part + ";" for part in parts[:-1]] + [parts[-1]]
    return lines


def _short_date(value) -> str | None:
    """dd/mm/yyyy → d/m/yyyy như văn bản hành chính ("ngày 15/9/2026")."""
    date = _date(value)
    if not date:
        return None
    day, month, year = date.split("/")
    return f"{int(day)}/{int(month)}/{year}"


def _doc_number(value) -> str | None:
    """Số CCCD 12 / CMND 9 chữ số; hộ chiếu một chữ cái + 7–8 số."""
    text = _plain(value)
    if not text:
        return None
    compact = re.sub(r"[\s.]", "", text).upper()
    if _PASSPORT_RE.match(compact):
        return compact
    digits = re.sub(r"\D", "", text)
    return digits if len(digits) in (12, 9) else None


def _org_id(value) -> str | None:
    """Mã định danh điện tử của cơ quan, tổ chức: giữ chữ và số, bỏ khoảng trắng."""
    text = _text(value)
    if not text:
        return None
    compact = re.sub(r"\s", "", text)
    return compact if re.search(r"\d", compact) and len(compact) >= 5 else None


def _police(value) -> str | None:
    match = _POLICE_RE.search(_plain(value) or "")
    if not match:
        return None
    kind = "thành phố" if fold(match.group(1)).startswith(("thanh", "tp")) else "tỉnh"
    name = match.group(2).strip()
    return f"Công an {kind} {name}" if name else None


def _police_of_province(province) -> str | None:
    label = province_label(province)
    if not label:
        return None
    kind, _, name = label.partition(" ")
    if kind == "Thành":  # "Thành phố X"
        return "Công an thành phố " + label[len("Thành phố "):]
    return f"Công an tỉnh {name}"


def _truong_hop(name: str | None, llm_choice) -> str | None:
    if name and _PARTY_RE.search(fold(name)):
        return TRUONG_HOP_DANG
    wanted = fold(_plain(llm_choice) or "")
    if not wanted:
        return None
    return next((option for option in TRUONG_HOP_OPTIONS if fold(option) == wanted), None)


def _loai_con_dau(name: str | None, truong_hop: str | None) -> str | None:
    """Ô (17). Cơ quan nhà nước có thể dùng dấu Quốc huy → không đoán; tổ chức đảng phân cấp theo tên."""
    if not truong_hop or truong_hop == TRUONG_HOP_OPTIONS[1]:
        return None
    if truong_hop == TRUONG_HOP_DANG:
        folded = fold(name or "")
        if "ban chap hanh trung uong" in folded:
            return CON_DAU_BCH_TRUNG_UONG
        if _PARTY_CENTRAL_RE.search(folded):
            return CON_DAU_DANG_TRUNG_UONG
    return CON_DAU_KHAC


def _documents(values: dict) -> str | None:
    """Ô (21): nguyên văn mục 5 văn bản đề nghị; thiếu thì dựng từ số/ngày/trích yếu của công văn + quyết định."""
    lines = _lines(values.get("VanBan_TaiLieuKemTheo"))
    if lines:
        return "\n".join(lines)
    built = []
    for kind, prefix in (("Công văn", "CongVan_"), ("Quyết định", "QuyetDinh_")):
        number = _text(values.get(prefix + "So"))
        if not number:
            continue
        line = f"- {kind} số {number}"
        if _short_date(values.get(prefix + "Ngay")):
            line += f", ngày {_short_date(values.get(prefix + 'Ngay'))}"
        if _text(values.get(prefix + "CoQuanBanHanh")):
            line += f" của {_text(values.get(prefix + 'CoQuanBanHanh'))}"
        subject = _text(values.get(prefix + "TrichYeu"))
        if subject:
            subject = re.sub(r"^(v/v|về việc)\s*", "", subject, flags=re.IGNORECASE)
            line += f" về việc {subject[0].lower() + subject[1:]}"
        built.append(line)
    if not built:
        return None
    return "\n".join([line + ";" for line in built[:-1]] + [built[-1] + "."])


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _drop_request_as_letter(_by_name(fields))
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in WAIT_MS:
            field["waitMs"] = WAIT_MS[name]
        out.append(field)
        seen.add(name)

    has_request = any(key.startswith("VanBan_") for key in values)

    # Người nộp: mục 6, không có thì người đứng đầu (mục 2).
    person = "VanBan_NguoiNop_" if _text(values.get("VanBan_NguoiNop_HoTen")) else "VanBan_NguoiDungDau_"
    if person == "VanBan_NguoiDungDau_" and not _text(values.get("VanBan_NguoiDungDau_HoTen")):
        person = None

    def vb(field: str):
        return values.get(person + field) if person else None

    submitter = _text(vb("HoTen"))
    # Thẻ CCCD của người KHÁC người nộp (nộp nhầm thẻ người đứng đầu / văn thư) → bỏ cả bộ Cccd_*.
    if values.get("Cccd_HoTen") and submitter and not _same_person(values.get("Cccd_HoTen"), submitter):
        values = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
        warnings.append("Thẻ căn cước tải lên không phải của người nộp hồ sơ ghi trong văn bản đề nghị — đã bỏ qua thẻ.")

    # ── Phần 1: cơ quan tiếp nhận ──
    area = _area(values.get("VanBan_DiaChiToChuc"))
    if area and not (area.get("tinh") or area.get("xa")):
        area = None  # chuỗi trần không tách được tỉnh/xã → không đổ cả dòng vào ô chi tiết
    police = _police(values.get("VanBan_KinhGui")) or _police_of_province(area.get("tinh") if area else None)
    add("CongDan__fs_BCANoiNopHS", police)

    # ── Phần 2: thông tin cơ bản — cơ quan, tổ chức ──
    org_id = _org_id(values.get("VanBan_SoDinhDanhToChuc"))
    if org_id:
        add("CongDan__fsLoaiHinhToChuc", LOAI_HINH_CO_MA)
        add("CongDan__fs_BCAMaDinhDanh", org_id)
    elif has_request:
        add("CongDan__fsLoaiHinhToChuc", LOAI_HINH_KHAC)
        warnings.append(
            "Văn bản đề nghị không ghi số định danh của cơ quan, tổ chức — đã chọn \"Cơ quan tổ chức khác\"; nếu cơ "
            "quan đã có mã định danh điện tử thì chọn lại \"Cơ quan tổ chức có mã định danh\" và nhập mã."
        )
    org_name = _org_name(values.get("VanBan_TenToChuc")) or _org_name(values.get("VanBan_TenCoQuanBanHanh"))
    add("CongDan__fs_BCATenCQDangKy", org_name)
    truong_hop = _truong_hop(org_name, values.get("VanBan_LoaiHinhToChuc"))
    add("CongDan__fs_BCATruongHop", truong_hop)
    if area:
        add("CongDan__fs_BCADiaChiCQDangKy", _plain(area.get("diaChi")))
        add("CongDan__fs_BCAQueQuanMaTinh", province_label(area.get("tinh")))
        add("CongDan__fs_BCAQueQuanMaPX", _plain(area.get("xa")))

    # ── Người nộp hồ sơ ──
    cccd_number = _doc_number(values.get("Cccd_SoDinhDanh"))
    vb_number = _doc_number(vb("SoGiayTo"))
    number = cccd_number or vb_number
    issue_date = _date(values.get("Cccd_NgayCap")) if cccd_number else None
    issue_date = issue_date or (_date(vb("NgayCap")) if vb_number == number else None)
    issuer = (_issuer(vb("NoiCap")) if vb_number and vb_number == number else None) or _issuer(values.get("Cccd_NoiCap"))
    if not issuer and issue_date:
        issuer = default_issuer(issue_date)
    add("CongDan_tenCongDan", submitter or _text(values.get("Cccd_HoTen")))
    add("CongDan_diDong", _phone(values.get("VanBan_NguoiNop_DienThoai")) or _phone(values.get("VanBan_DienThoaiToChuc")))
    add("CongDan_email", _email(values.get("VanBan_EmailToChuc")))
    add("CongDan_soCmnd", number)
    add("CongDan__fs_BCANgayCapCMND", issue_date)
    add("CongDan__fs_BCANoiCapCMND", issuer)
    add("CongDan__fsNgaySinh", _date(values.get("Cccd_NgaySinh")) or _date(vb("NgaySinh")))
    add("CongDan__fsDangKyDauGioiTinh", _gender(values.get("Cccd_GioiTinh")) or _gender(vb("GioiTinh")))

    # ── Loại hình con dấu ──
    seal = _loai_con_dau(org_name, truong_hop)
    add("CongDan__fs_BCALoaiHinhConDau", seal)

    # ── Phần 4: thành phần hồ sơ ──
    content = _text(values.get("VanBan_NoiDungDeNghi"))
    reason = _text(values.get("VanBan_LyDo"))
    if reason:
        reason = re.sub(r"^l[ýy]\s*do\s*:?\s*", "", reason, flags=re.IGNORECASE)
    if not content and (reason or has_request):
        content = NOI_DUNG_MAC_DINH
    if content:
        add("CongDan__fs_BCANoiDungYeuCauGQ", content + (f"\nLý do: {reason}" if reason else ""))
    add("CongDan__fs_BCATenGiayToTaiLieu", _documents(values))

    # ── Cảnh báo ──
    if has_request and "CongDan__fs_BCATruongHop" not in seen:
        warnings.append("Không xác định được loại hình cơ quan, tổ chức — chọn tay ô Loại hình Cơ quan/Tổ chức (*).")
    if seal:
        warnings.append(f"Loại hình con dấu chọn theo tên cơ quan (\"{seal}\") — kiểm tra lại trước khi nộp.")
    elif has_request:
        warnings.append("Chọn tay ô Loại hình con dấu (*) (cơ quan nhà nước có thể dùng con dấu có hình Quốc huy).")
    if has_request and not area:
        warnings.append("Không tách được tỉnh, xã trong địa chỉ cơ quan — chọn tay Tỉnh/thành phố, Phường/xã và nhập Địa chỉ.")
    if has_request and "CongDan__fs_BCATenGiayToTaiLieu" not in seen:
        warnings.append(
            "Không đọc được danh sách tài liệu gửi kèm (mục 5 văn bản đề nghị) — nhập tay ô Các giấy tờ tài liệu có "
            "trong hồ sơ (*), hoặc tải thêm quyết định thành lập / văn bản đồng ý khắc dấu."
        )
    if "CongDan_diDong" not in seen:
        warnings.append("Giấy tờ không có số điện thoại liên hệ — ô Số điện thoại liên hệ (*) cần nhập tay.")
    warnings.append(RESULT_WARNING)
    return out, warnings
