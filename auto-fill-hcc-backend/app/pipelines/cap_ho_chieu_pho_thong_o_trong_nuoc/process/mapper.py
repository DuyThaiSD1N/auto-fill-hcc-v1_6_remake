"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.001456 (Cổng DVC Bộ Công an).

Thứ tự nguồn theo file mapping (cột "Dữ liệu được lấy từ"):
- Họ / Chữ đệm và tên: Tờ khai mục 1 (đã tách sẵn hai phần) → CCCD → hộ chiếu (tách chữ đầu làm Họ).
- Nơi sinh: hộ chiếu → tờ khai, đổi tên tỉnh cũ sang tỉnh sau sắp xếp 2025 (hộ chiếu 2018 ghi "THÁI BÌNH" → "Hưng Yên");
  tên nước ngoài giữ nguyên (danh mục cổng có cả quốc gia).
- Ngày cấp / nơi cấp CCCD: thẻ CCCD (khi cùng số với tờ khai) → tờ khai mục 4; nơi cấp suy theo ngày cấp nếu thẻ
  không có mặt sau.
- Địa chỉ thường trú: tờ khai mục 8 (đã ghi theo đơn vị hành chính mới) → CCCD (đơn vị cũ, đổi qua remap_area). Mapping
  xếp CCCD trước nhưng ghi rõ phải "chuẩn hoá theo ĐVHC mới như tờ khai" — tờ khai có sẵn bản đúng nên dùng trước.
- Hộ chiếu gần nhất (số, ngày cấp, nơi cấp): hộ chiếu → tờ khai mục 13.
- Còn lại (SĐT, tạm trú, nghề nghiệp, cha/mẹ/vợ chồng, nội dung đề nghị, loại chip, nơi nhận): tờ khai.

Ngày sinh cha / mẹ / vợ chồng: tờ khai thường chỉ ghi NĂM → gửi kèm ``dateFormat`` ("Năm" / "Tháng/Năm") để extension
chọn định dạng ở nút cạnh ô ngày trước khi gõ (form-builder mặc định Ngày/Tháng/Năm).
"""

import re
from datetime import date

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import canonical_province, province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.schema import (
    DE_NGHI_HET_HAN,
    DE_NGHI_HET_TRANG,
    DE_NGHI_HU_HONG,
    DE_NGHI_KHAC,
    DE_NGHI_LAN_DAU,
    DE_NGHI_MAT,
    DE_NGHI_SAP_HET_HAN,
    NOI_CAP_DKQL,
    NOI_CAP_HO_CHIEU,
    NOI_CAP_QLHC,
    UI_COMP_BY_NAME,
    WAIT_MS,
)
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _email,
    _issuer,
    _phone,
    _plain,
    _same_person,
)

_PASSPORT_RE = re.compile(r"^[A-Z]\d{7,8}$")
_OCR_DIGITS = str.maketrans("OQDSIL|ZBG", "0005111286")
# Dòng 2 MRZ hộ chiếu (ICAO 9303 TD3): số hộ chiếu 9 ký tự + chữ số kiểm tra + quốc tịch + ngày sinh yymmdd.
_MRZ_LINE2_RE = re.compile(r"([A-Z0-9<]{9})(\d)[A-Z<]{3}\d{6}")
_FORM_MARK = r"\s*(?:\[\s*[xX✓✔]\s*\]|☑|☒|✓|✔|\(\s*[xX]\s*\))"
_CHIP_NO_RE = re.compile(r"kh[ôo]ng\s+g[ắa]n\s+ch[íi]p\s+đi[ệe]n\s+t[ửu]" + _FORM_MARK, re.IGNORECASE)
_CHIP_YES_RE = re.compile(r"c[óo]\s+g[ắa]n\s+ch[íi]p\s+đi[ệe]n\s+t[ửu]" + _FORM_MARK, re.IGNORECASE)
_REQUEST_LINE_RE = re.compile(
    r"14\.\s*N[ộo]i\s+dung\s+đ[ềe]\s+ngh[ịi]\s*(?:\(\d\))?\s*:?\s*(.+?)\s*(?:C[ấa]p\s+h[ộo]\s+chi[ếe]u\s+(?:kh[ôo]ng|c[óo])\s+g[ắa]n|\n|$)",
    re.IGNORECASE,
)
_OLD_PASSPORT_RE = re.compile(r"13\.\s*H[ộo]\s+chi[ếe]u\s+ph[ổo]\s+th[ôo]ng.{0,60}?s[ốo]\s*:?\s*([A-Z][A-Z0-9]{6,9})\b",
                              re.IGNORECASE)
_YEAR_RE = re.compile(r"^(?:năm\s*)?(\d{4})$", re.IGNORECASE)
_MONTH_YEAR_RE = re.compile(r"^(\d{1,2})\s*[/\-.]\s*(\d{4})$")
# Bảng remap không có Hà Tây (nhập Hà Nội 2008) → lookup tỉnh trả nhầm tỉnh khác.
_OLD_PROVINCE_FIX = {"ha tay": "Hà Nội"}
_POLICE_UNIT_RE = re.compile(r"c[ôo]ng\s+an\s+(t[ỉi]nh|th[àa]nh\s+ph[ốo]|tp\.?)\s+([^,;.\n()]+)", re.IGNORECASE)

PORTRAIT_WARNING = (
    "Chưa thấy ảnh chân dung 4x6 trong giấy tờ tải lên — cổng bắt buộc ô Ảnh chân dung ở đầu biểu mẫu (ảnh nền trắng, "
    "định dạng .jpg, dưới 2 MB). Tải thêm ảnh chân dung rồi điền lại để hệ thống tự gắn (ảnh .png / .heic / .webp hệ "
    "thống tự đổi sang .jpg), hoặc bấm Tải ảnh trên cổng. Ảnh dán trên tờ khai không được cắt tự động."
)
REFUND_WARNING = (
    "Mục Đăng ký thông tin hoàn tiền (*): nhập Số tài khoản, Tên chủ tài khoản, Tên ngân hàng của người đề nghị "
    "(giấy tờ không có)."
)


# ── Ảnh chân dung 4x6 (ô tải ảnh đầu trang kê khai) ──
# Cổng chỉ nhận .jpg dưới 2 MB. Tệp ảnh người dùng tải lên có thể là .png / .webp / .bmp (HEIC đã đổi sang JPG lúc nhận
# tệp, app/services/heic.py) → đổi hết sang JPEG, cạnh dài tối đa 1200 px, hạ chất lượng tới khi dưới ngưỡng.
PORTRAIT_MAX_BYTES = 1_900_000
PORTRAIT_MAX_SIDE = 1200
PORTRAIT_FILE_NAME = "anh_chan_dung_4x6.jpg"
_IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|webp|bmp|gif|tiff?|jfif)$", re.IGNORECASE)
_PORTRAIT_NAME_RE = re.compile(r"(chan\s*dung|4\s*x\s*6|anh\s*the|portrait|avatar|anh\s*46|chan_dung|anh_the)")
# Ảnh chân dung gần như không có chữ; giấy tờ chụp (tờ khai, hộ chiếu, CCCD) luôn có hàng chục chữ trở lên.
_PORTRAIT_MAX_LETTERS = 40


def _pdf_single_image(data: bytes) -> bytes | None:
    """Ảnh gốc trong PDF MỘT trang chỉ chứa MỘT ảnh phủ kín trang, None với PDF khác.

    Bước đính kèm của Auto Fill đổi mọi ảnh sang PDF trước khi gửi (popup.js toPdfForAttach → lib/imageToPdf.js: trang
    đúng cỡ ảnh, ảnh vẽ kín trang) → ảnh chân dung tới planner dưới dạng PDF. Lấy lại đúng ảnh đã nhúng; PDF scan giấy
    nhiều trang / có chữ không lọt điều kiện này."""
    import fitz

    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            if doc.page_count != 1:
                return None
            page = doc[0]
            images = page.get_images(full=True)
            if len(images) != 1 or page.get_text("text").strip():
                return None
            xref = images[0][0]
            rects = page.get_image_rects(xref)
            page_area = abs(page.rect)
            if not rects or not page_area or abs(rects[0]) < 0.9 * page_area:
                return None
            try:
                return doc.extract_image(xref)["image"]
            except Exception:  # noqa: BLE001 — ảnh mã hoá lạ → vẽ lại trang
                return page.get_pixmap(dpi=150).tobytes("png")
    except Exception:  # noqa: BLE001
        return None


def _image_bytes(file: dict) -> bytes | None:
    data_url = str(file.get("dataUrl") or "")
    mime = str(file.get("type") or "").lower()
    if data_url.startswith("data:"):
        mime = data_url[5:].split(";", 1)[0].split(",", 1)[0].lower() or mime
    name = str(file.get("name") or "")
    is_pdf = mime == "application/pdf" or name.lower().endswith(".pdf")
    if not (is_pdf or mime.startswith("image/") or _IMAGE_EXT_RE.search(name)):
        return None
    try:
        import base64

        data = base64.b64decode(data_url.split(",", 1)[1] if "," in data_url else data_url)
    except Exception:  # noqa: BLE001
        return None
    return _pdf_single_image(data) if is_pdf else data


def _portrait_shape(data: bytes) -> tuple[float, float] | None:
    """(tỉ lệ rộng/cao, độ sáng trung bình viền ngoài 0–255) — None khi không mở được ảnh."""
    import io

    from PIL import Image, ImageOps, ImageStat

    try:
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image).convert("L")
            width, height = image.size
            if not width or not height:
                return None
            band = max(1, min(width, height) // 12)
            strips = [image.crop((0, 0, width, band)), image.crop((0, 0, band, height)),
                      image.crop((width - band, 0, width, height))]
            brightness = sum(ImageStat.Stat(s).mean[0] for s in strips) / len(strips)
            return width / height, brightness
    except Exception:  # noqa: BLE001
        return None


def find_portrait(files: list[dict], texts: dict[int, str] | None = None) -> int | None:
    """Chỉ số tệp ảnh chân dung trong bộ giấy, None khi không có.

    Tên tệp có "chân dung" / "4x6" / "ảnh thẻ" / "portrait" → nhận ngay (vẫn phải là ảnh, ít chữ). Không thì nhận ảnh
    dọc (rộng/cao 0,55–0,9), gần như không có chữ OCR, viền sáng (nền trắng / sáng). Nhiều ảnh khớp → ảnh có tỉ lệ gần
    4x6 nhất."""
    texts = texts or {}
    best: tuple[int, float, int] | None = None  # (ưu tiên tên, độ lệch tỉ lệ, chỉ số)
    for index, file in enumerate(files or []):
        data = _image_bytes(file)
        if not data:
            continue
        letters = len(re.findall(r"[0-9A-Za-zÀ-ỹ]", texts.get(index, "") or ""))
        if letters > _PORTRAIT_MAX_LETTERS:
            continue
        shape = _portrait_shape(data)
        if not shape:
            continue
        ratio, brightness = shape
        by_name = bool(_PORTRAIT_NAME_RE.search(fold(str(file.get("name") or ""))))
        if not by_name and not (0.55 <= ratio <= 0.9 and brightness >= 150):
            continue
        rank = (0 if by_name else 1, abs(ratio - 2 / 3), index)
        if best is None or rank < best:
            best = rank
    return best[2] if best else None


def portrait_jpeg(data: bytes, max_side: int = PORTRAIT_MAX_SIDE) -> bytes:
    """Ảnh bất kỳ PIL mở được → JPEG RGB (nền trong suốt thành trắng), xoay theo EXIF, dưới PORTRAIT_MAX_BYTES.
    ``max_side``: cạnh dài tối đa (ảnh trang nhân thân hộ chiếu của thẻ tạm trú 1.003460 cần nét hơn ảnh 4x6)."""
    import io

    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            image = Image.new("RGB", rgba.size, (255, 255, 255))
            image.paste(rgba, mask=rgba.split()[-1])
        else:
            image = image.convert("RGB")
        image.thumbnail((max_side, max_side))
        out = b""
        while True:
            for quality in (92, 85, 75, 65):
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality)
                out = buffer.getvalue()
                if len(out) <= PORTRAIT_MAX_BYTES:
                    return out
            if min(image.size) < 200:
                return out
            image = image.resize((int(image.width * 0.8), int(image.height * 0.8)))


def portrait_field(files: list[dict], texts: dict[int, str] | None = None) -> tuple[dict | None, list[str]]:
    """(ô ``filename46`` comp ``bca-photo`` mang sẵn ảnh JPEG, câu báo). Không có ảnh → (None, [PORTRAIT_WARNING])."""
    import base64

    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.schema import PORTRAIT_FIELD

    index = find_portrait(files, texts)
    if index is None:
        return None, [PORTRAIT_WARNING]
    source = files[index]
    source_name = str(source.get("name") or f"file-{index + 1}")
    try:
        jpeg = portrait_jpeg(_image_bytes(source) or b"")
    except Exception:  # noqa: BLE001
        return None, [f"Không đọc được ảnh chân dung '{source_name}' — tải lại ảnh dạng .jpg (dưới 2 MB) ở ô Ảnh chân "
                      "dung đầu biểu mẫu."]
    field = {
        "name": PORTRAIT_FIELD,
        "comp": "bca-photo",
        "value": {"name": PORTRAIT_FILE_NAME, "type": "image/jpeg",
                  "dataUrl": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")},
        "sourceFileName": source_name,
    }
    # Ảnh .jpg mà Auto Fill đã gói vào PDF lúc đính kèm (tên "<ảnh>.pdf") không phải do người dùng lưu sai định dạng.
    converted = not re.search(r"\.(jpe?g|pdf)$", source_name, re.IGNORECASE)
    note = (f"Đã gắn ảnh '{source_name}' vào ô Ảnh chân dung đầu biểu mẫu"
            + (" (đã tự đổi sang định dạng .jpg)" if converted else "")
            + " — kiểm tra đúng ảnh chân dung 4x6 nền trắng của người đề nghị. Lần sau nên chụp / lưu ảnh dạng .jpg.")
    return field, [note]


def _text(value) -> str | None:
    """Chuỗi một dòng; ô chấm chấm / "trống" / "không" coi như không có."""
    text = _plain(value)
    if not text or not re.search(r"[0-9A-Za-zÀ-ỹ]", text):
        return None
    if fold(text) in ("trong", "khong", "khong co", "khong ap dung"):
        return None
    return text


def _passport_number(value) -> str | None:
    """Số hộ chiếu một chữ cái + 7 chữ số. OCR hay đọc nhầm chữ số thành chữ (bộ mẫu 18/11: "C5222637" → "CS222637" trên
    trang nhân thân, "CS5222637" ở mục 13 tờ khai) → đổi chữ dễ nhầm về số; thừa đúng một chữ chen sau chữ đầu thì bỏ."""
    compact = re.sub(r"[\s.\-]", "", _plain(value) or "").upper()
    match = re.fullmatch(r"([A-Z])([A-Z0-9]{7,8})", compact)
    if not match:
        return None
    head, tail = match.groups()
    if tail.isdigit():
        return head + tail
    if len(tail) == 8 and tail[0].isalpha() and tail[1:].isdigit():
        tail = tail[1:]
    tail = tail.translate(_OCR_DIGITS)
    return head + tail if re.fullmatch(r"\d{7}", tail) else None


def _mrz_check(text: str) -> int:
    total = 0
    for i, char in enumerate(text):
        value = int(char) if char.isdigit() else (ord(char) - 55 if char.isalpha() else 0)
        total += value * (7, 3, 1)[i % 3]
    return total % 10


def _mrz_number(value) -> str | None:
    """Số hộ chiếu ở 9 ký tự đầu dòng MRZ thứ hai, chỉ nhận khi đúng chữ số kiểm tra ICAO 9303 (ký tự thứ 10)."""
    compact = re.sub(r"\s", "", str(value or "")).upper()
    match = _MRZ_LINE2_RE.search(compact)
    if not match or _mrz_check(match.group(1)) != int(match.group(2)):
        return None
    number = match.group(1).rstrip("<")
    return number if _PASSPORT_RE.match(number) else None


def _id_number(value) -> str | None:
    digits = re.sub(r"\D", "", _plain(value) or "")
    return digits if len(digits) in (12, 9) else None


def _split_name(full) -> tuple[str | None, str | None]:
    words = (_plain(full) or "").split()
    if len(words) < 2:
        return None, None
    return words[0], " ".join(words[1:])


def _partial_date(value) -> tuple[str, str | None] | None:
    """(giá trị gõ vào ô, định dạng cần chọn): dd/mm/yyyy → mặc định; mm/yyyy → "Tháng/Năm"; yyyy → "Năm"."""
    full = _date(value)
    if full:
        return full, None
    text = _plain(value) or ""
    match = _MONTH_YEAR_RE.match(text)
    if match and 1 <= int(match.group(1)) <= 12:
        return f"{int(match.group(1)):02d}/{match.group(2)}", "Tháng/Năm"
    match = _YEAR_RE.match(text)
    if match:
        return match.group(1), "Năm"
    return None


def _birth_place(value) -> str | None:
    """Tên tỉnh trần theo danh mục sau sắp xếp ("Thái Bình" → "Hưng Yên"); không phải tỉnh VN thì giữ nguyên (tên nước)."""
    text = _text(value)
    if not text:
        return None
    bare = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    if fold(bare) in _OLD_PROVINCE_FIX:
        return _OLD_PROVINCE_FIX[fold(bare)]
    remapped = remap_area({"tinh": bare, "xa": "", "diaChi": ""}) or {}
    current = canonical_province(remapped.get("tinh")) or canonical_province(bare)
    if current:
        return current
    return bare.title() if bare.isupper() else bare


def _id_issuer(issuer: str | None, issue_date: str | None) -> tuple[str | None, str | None]:
    """(option ô Nơi cấp CCCD, cảnh báo). Cơ quan đầy đủ → chữ viết tắt của danh mục cổng."""
    name = issuer or (default_issuer(issue_date) if issue_date else None)
    folded = fold(name or "")
    if "quan ly hanh chinh" in folded or "qlhc" in folded:
        return NOI_CAP_QLHC, None
    if "dang ky quan ly cu tru" in folded or "dkql" in folded:
        return NOI_CAP_DKQL, None
    if folded:
        return None, f"Nơi cấp CCCD ghi \"{name}\" — chọn tay ô Nơi cấp nếu danh mục của cổng có."
    return None, None


def _passport_issuer(value) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = fold(text)
    if "xuat nhap canh" in folded and "phong" not in folded:
        return NOI_CAP_HO_CHIEU
    return text


def _request(text: str | None, has_old_passport: bool, expiry: str | None) -> tuple[str | None, str | None]:
    """(option ô 14, chi tiết đề nghị) theo nguyên văn mục 14 tờ khai."""
    folded = fold(text or "")
    if folded:
        if "lan dau" in folded:
            return DE_NGHI_LAN_DAU, None
        if re.search(r"\b(bi mat|do mat|mat ho chieu|hc bi mat)\b", folded):
            return DE_NGHI_MAT, None
        if "hu hong" in folded:
            return DE_NGHI_HU_HONG, None
        if "het trang" in folded:
            return DE_NGHI_HET_TRANG, None
        if "sap het han" in folded:
            return DE_NGHI_SAP_HET_HAN, None
        if "het han" in folded:
            return DE_NGHI_HET_HAN, None
        detail = re.sub(r"^\s*đề\s*nghị\s*khác\s*[.:;,\-\s]*", "", text or "", flags=re.IGNORECASE)
        detail = _text(detail.strip(" .:;,-"))
        return DE_NGHI_KHAC, detail
    if not has_old_passport:
        return DE_NGHI_LAN_DAU, None
    if expiry:
        day, month, year = (int(part) for part in expiry.split("/"))
        if date(year, month, day) < date.today():
            return DE_NGHI_HET_HAN, None
    return None, None


def _chip(value) -> str | None:
    folded = fold(_plain(value) or "").replace("_", " ")
    if not folded:
        return None
    if "khong" in folded:
        return "khong_chip"
    return "co_chip" if "chip" in folded or folded in ("co", "x") else None


def _police_unit(*values) -> str | None:
    """"Phòng Quản lý XNC-Công an tỉnh Lai Châu" → "Công an tỉnh Lai Châu" (option cổng: "Phòng Quản lý XNC- Công an
    tỉnh …" — khớp lỏng theo cụm này); "Cục Quản lý xuất nhập cảnh" giữ nguyên."""
    for value in values:
        text = _plain(value) or ""
        match = _POLICE_UNIT_RE.search(text)
        if match:
            kind = "thành phố" if fold(match.group(1)).startswith(("thanh", "tp")) else "tỉnh"
            return f"Công an {kind} {match.group(2).strip()}"
        if re.search(r"\bcuc quan ly xuat nhap canh\b", fold(text)):
            return NOI_CAP_HO_CHIEU
    return None


def _pickup_in_person(value) -> bool | None:
    """Địa chỉ nhận hộ chiếu là cơ quan Công an / XNC → nhận trực tiếp; địa chỉ khác → bưu chính; trống → None."""
    folded = fold(_plain(value) or "")
    if not folded:
        return None
    return bool(re.search(r"\b(xnc|xuat nhap canh|cong an)\b", folded))


def ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    """compact_field_fallback: LLM có lượt bỏ sót mục 14 / ô loại chip / số hộ chiếu (chạy thật bộ mẫu 18/11) dù OCR
    đọc đủ → field còn trống thì đọc thẳng từ chữ OCR. Dòng MRZ luôn dò lại vì chữ số kiểm tra cho số hộ chiếu chắc nhất."""
    if isinstance(raw_fields, dict):
        fields = dict(raw_fields)
    else:
        fields = {item.get("name"): item.get("value") for item in raw_fields or []
                  if isinstance(item, dict) and item.get("name")}
    for doc in documents or []:
        text = str(doc.get("text") or "")
        if not _text(fields.get("HoChieu_MRZ")) and _mrz_number(text):
            fields["HoChieu_MRZ"] = _MRZ_LINE2_RE.search(re.sub(r"\s", "", text).upper()).group(0)
        if not re.search(r"t[ờo]\s+khai", text, re.IGNORECASE) or "hộ chiếu" not in text.lower():
            continue
        if not _text(fields.get("ToKhai_NoiDungDeNghi")):
            match = _REQUEST_LINE_RE.search(text)
            if match and _text(match.group(1)):
                fields["ToKhai_NoiDungDeNghi"] = match.group(1).strip()
        if not _text(fields.get("ToKhai_LoaiHoChieu")):
            if _CHIP_NO_RE.search(text):
                fields["ToKhai_LoaiHoChieu"] = "khong_chip"
            elif _CHIP_YES_RE.search(text):
                fields["ToKhai_LoaiHoChieu"] = "co_chip"
        if not _text(fields.get("ToKhai_HoChieuCu_So")):
            match = _OLD_PASSPORT_RE.search(text)
            if match:
                fields["ToKhai_HoChieuCu_So"] = match.group(1)
    return fields


NO_ACCOUNT_WARNING = (
    "Chưa đối chiếu được giấy tờ với tài khoản VNeID đang đăng nhập (không đọc được ô Họ và tên / Số CCCD trên form) — "
    "kiểm tra giấy tờ đúng là của chủ tài khoản trước khi nộp."
)


ACCOUNT_MISMATCH_CODE = "account_mismatch"


def _id_label(number: str | None) -> str:
    return f"người có số định danh {number}" if number else "người khác"


def account_block(values: dict, options: dict | None) -> dict | None:
    """``{code, message, accountName, documentName}`` khi giấy tờ là của người KHÁC chủ tài khoản VNeID đang đăng nhập,
    ngược lại None.

    Cổng khoá Họ và tên / Số CCCD / cha mẹ… theo CSDLQG của tài khoản đăng nhập (extension gửi hai ô readonly
    ``CongDan_tenCongDan`` / ``CongDan_soCmnd`` qua ``options.formContext``) → điền giấy của người khác chỉ ra form trộn
    hai người, không nộp được. So số định danh trước; số khác mà tên vẫn trùng thì coi là OCR đọc lệch số, không chặn.
    ``message`` là câu hiện thẳng cho người dùng (Auto Fill hiện nguyên câu; trợ lý ghép tên vào mẫu câu riêng).
    """
    context = (options or {}).get("formContext") or {}
    account_id = _id_number(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    account_name = _text(context.get("applicantFullname"))
    doc_name = " ".join(filter(None, (_text(values.get("ToKhai_Ho")), _text(values.get("ToKhai_ChuDemTen"))))) \
        or _text(values.get("Cccd_HoTen")) or _text(values.get("HoChieu_HoTen"))
    doc_id = _id_number(values.get("ToKhai_SoDinhDanh")) or _id_number(values.get("Cccd_SoDinhDanh"))
    if account_id and doc_id and len(account_id) == len(doc_id):
        mismatch = account_id != doc_id and not (account_name and doc_name and _same_person(account_name, doc_name))
    elif account_name and doc_name:
        mismatch = not _same_person(account_name, doc_name)
    else:
        return None
    if not mismatch:
        return None
    account = account_name.upper() if account_name else _id_label(account_id)
    document = doc_name.upper() if doc_name else _id_label(doc_id)
    return {
        "code": ACCOUNT_MISMATCH_CODE,
        "accountName": account,
        "documentName": document,
        "message": (
            f"Chưa điền: giấy tờ tải lên là của {document}, còn tài khoản VNeID đang đăng nhập là của {account}. "
            f"Vui lòng tải giấy tờ đúng của {account} (chủ tài khoản VNeID), hoặc đăng nhập VNeID của {document} "
            "rồi làm lại."
        ),
    }


def has_account_anchor(options: dict | None) -> bool:
    context = (options or {}).get("formContext") or {}
    return any(context.get(key) for key in ("applicantIdentityNumber", "identityNumber", "applicantFullname"))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    if has_account_anchor(options):
        blocked = account_block(values, options)
        if blocked:
            return [], [blocked["message"]]
        account_warnings: list[str] = []
    else:
        account_warnings = [NO_ACCOUNT_WARNING]
    out: list[dict] = []
    warnings: list[str] = account_warnings
    seen: set[str] = set()

    def add(name: str, value, **extra) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in WAIT_MS:
            field["waitMs"] = WAIT_MS[name]
        field.update({key: val for key, val in extra.items() if val})
        out.append(field)
        seen.add(name)

    has_form = any(key.startswith("ToKhai_") for key in values)
    form_name = " ".join(filter(None, (_text(values.get("ToKhai_Ho")), _text(values.get("ToKhai_ChuDemTen")))))
    applicant = form_name or _text(values.get("Cccd_HoTen")) or _text(values.get("HoChieu_HoTen"))
    # Giấy của người KHÁC (nộp nhầm thẻ / hộ chiếu người thân) → bỏ cả bộ của giấy đó.
    for prefix, label in (("Cccd_", "Thẻ căn cước"), ("HoChieu_", "Hộ chiếu")):
        holder = values.get(prefix + "HoTen")
        if holder and applicant and not _same_person(holder, applicant):
            values = {key: value for key, value in values.items() if not key.startswith(prefix)}
            warnings.append(f"{label} tải lên không phải của người đề nghị ghi trong tờ khai — đã bỏ qua.")

    # ── Thông tin nhân thân ──
    ho, chu_dem_ten = _text(values.get("ToKhai_Ho")), _text(values.get("ToKhai_ChuDemTen"))
    if not (ho and chu_dem_ten):
        ho, chu_dem_ten = _split_name(values.get("Cccd_HoTen") or values.get("HoChieu_HoTen"))
    add("CongDan__fsBCAHoCongDan", ho)
    add("CongDan__fsBCAChuDemTen", chu_dem_ten)
    add("CongDan__fs_BCANoiKhaiSinhCD", _birth_place(values.get("HoChieu_NoiSinh")) or _birth_place(values.get("ToKhai_NoiSinh")))

    form_id = _id_number(values.get("ToKhai_SoDinhDanh"))
    card_id = _id_number(values.get("Cccd_SoDinhDanh"))
    card_ok = bool(card_id) and (not form_id or card_id == form_id)
    issue_date = (_date(values.get("Cccd_NgayCap")) if card_ok else None) or _date(values.get("ToKhai_NgayCap"))
    add("CongDan__fs_BCANgayCapCCCD", issue_date)
    if len(card_id or form_id or "") == 12:  # CMND 9 số do Công an tỉnh cũ cấp → danh mục tên cũ, không đoán
        issuer, issuer_warning = _id_issuer(_issuer(values.get("Cccd_NoiCap")) if card_ok else None, issue_date)
        add("CongDan__fs_BCANoiCapCCCD", issuer)
        if issuer_warning:
            warnings.append(issuer_warning)
    add("CongDan_diDong", _phone(values.get("ToKhai_DienThoai")))
    add("CongDan_email", _email(values.get("ToKhai_Email")))

    # ── Địa chỉ thường trú (mục 8) / tạm trú (mục 9) ──
    resident = _area(values.get("ToKhai_ThuongTru"))
    if not (resident and (resident.get("tinh") or resident.get("xa"))):
        resident = _area(values.get("Cccd_NoiThuongTru")) or resident
    if resident and (resident.get("tinh") or resident.get("xa")):
        add("CongDan__fs_BCAQueQuanMaTinh", province_label(canonical_province(resident.get("tinh")) or resident.get("tinh")))
        add("CongDan__fs_BCAQueQuanMaQH", _plain(resident.get("xa")))
        add("CongDan__fs_BCAQueQuanChiTiet", _plain(resident.get("diaChi")))
    elif has_form:
        warnings.append("Không tách được tỉnh, xã của địa chỉ thường trú — chọn tay Tỉnh/Thành phố, Phường/Xã (mục 8).")
    temporary = _area(values.get("ToKhai_TamTru"))
    if temporary and (temporary.get("tinh") or temporary.get("xa")):
        add("CongDan__fs_BCANoiOHienTaiMaTinh",
            province_label(canonical_province(temporary.get("tinh")) or temporary.get("tinh")))
        add("CongDan__fs_BCANoiOHienTaiMaQH", _plain(temporary.get("xa")))
        add("CongDan__fs_BCADiaChiThuongTruCD", _plain(temporary.get("diaChi")))

    # ── Nghề nghiệp, cơ quan, thân nhân (mục 10 – 12) ──
    add("CongDan__fs_BCANgheNghiepCD", _text(values.get("ToKhai_NgheNghiep")))
    add("CongDan__fs_BCADiaChiCoQuanCD", _text(values.get("ToKhai_CoQuan")))
    for source, target in (("ToKhai_Cha_NgaySinh", "CongDan__fs_BCANgaySinhChaCD"),
                           ("ToKhai_Me_NgaySinh", "CongDan__fs_BCANgaySinhMeCD")):
        parsed = _partial_date(values.get(source))
        if parsed:
            add(target, parsed[0], dateFormat=parsed[1])
    spouse = _text(values.get("ToKhai_VoChong_HoTen"))
    add("CongDan__fsBCAHoVaTenVoChong", spouse)
    parsed = _partial_date(values.get("ToKhai_VoChong_NgaySinh")) if spouse else None
    if parsed:
        add("CongDan__fs_BCANgaySinhVoChong", parsed[0], dateFormat=parsed[1])

    # ── Hộ chiếu gần nhất (mục 13) + nội dung đề nghị (mục 14) ──
    passport = _mrz_number(values.get("HoChieu_MRZ")) or _passport_number(values.get("HoChieu_So"))
    form_passport = _passport_number(values.get("ToKhai_HoChieuCu_So"))
    number = passport or form_passport
    add("CongDan__fs_BCAHoChieuPT", number)
    if number:
        # Ngày cấp mục 13 chỉ dùng khi tờ khai nói về CÙNG cuốn hộ chiếu đã tải lên (hoặc không có hộ chiếu).
        form_issued = _date(values.get("ToKhai_HoChieuCu_NgayCap")) if form_passport in (None, number) else None
        add("CongDan__fs_BCANgayCapHoChieuPT",
            (_date(values.get("HoChieu_NgayCap")) if passport else None) or form_issued)
        add("CongDan__fs_BCANoiCapHCGanNhat", _passport_issuer(values.get("HoChieu_NoiCap")) if passport else None)
        if passport and form_passport and form_passport != passport:
            warnings.append(f"Số hộ chiếu trên tờ khai ({form_passport}) khác hộ chiếu tải lên ({passport}) — đã điền theo "
                            "hộ chiếu, kiểm tra lại mục 13.")
    request, detail = _request(_text(values.get("ToKhai_NoiDungDeNghi")), bool(number),
                               _date(values.get("HoChieu_NgayHetHan")) if passport else None)
    add("CongDan__fs_BCANoiDungDeNghi", request)
    add("CongDan__fs_BCAChiTietDeNghi", detail)
    if not request:
        warnings.append("Không đọc được Nội dung đề nghị (mục 14) — chọn tay ô 14. Nội dung đề nghị Cấp hộ chiếu (*).")

    chip = _chip(values.get("ToKhai_LoaiHoChieu"))
    if chip == "khong_chip":
        add("CongDan__fsBCAHoKhongChieuGanChip", True)
    else:
        add("CongDan__fsBCAHoChieuGanChip", True)
        if not chip:
            warnings.append("Tờ khai không thấy rõ ô loại hộ chiếu được đánh dấu — đã chọn \"Cấp hộ chiếu có gắn chip "
                            "điện tử\"; đổi lại nếu người đề nghị chọn hộ chiếu không gắn chip.")

    # ── Nơi tiếp nhận + nơi nhận hộ chiếu (mục 17) ──
    # Ô 17 chỉ có cơ quan đã chọn ở bước "Chọn trường hợp hồ sơ" (chạy thật 18/11: danh sách chỉ một mục, theo cơ quan
    # đã chọn) → không phát, chỉ nhắc khi tờ khai ghi đơn vị nhận khác.
    unit = _police_unit(values.get("ToKhai_DonViTiepNhan"), values.get("ToKhai_DiaChiNhanHoChieu"))
    if unit:
        warnings.append(f"Tờ khai ghi nộp / nhận hộ chiếu tại {unit} — kiểm tra ô 17. Cơ quan tiếp nhận (cổng lấy theo cơ "
                        "quan đã chọn ở bước chọn trường hợp hồ sơ).")
    pickup = _pickup_in_person(values.get("ToKhai_DiaChiNhanHoChieu"))
    if pickup:
        add("CongDan__fs_BCANoiNhanHoChieu", True)
    elif pickup is False:
        warnings.append(
            f"Tờ khai ghi nhận hộ chiếu tại \"{_plain(values.get('ToKhai_DiaChiNhanHoChieu'))}\" — tick \"Nhận qua bưu "
            "chính\" rồi chọn Tỉnh thành, Phường xã, nhập Địa chỉ nhận hộ chiếu."
        )

    # ── Cảnh báo ô bắt buộc giấy tờ không có ──
    if "CongDan_diDong" not in seen:
        warnings.append("Giấy tờ không có số điện thoại — ô 7. Số điện thoại (*) cần nhập tay.")
    if "CongDan_email" not in seen:
        warnings.append("Giấy tờ không có email — ô Email (*) cần nhập tay.")
    if "CongDan__fs_BCANoiKhaiSinhCD" not in seen and (has_form or "HoChieu_So" in values):
        warnings.append("Không đọc được nơi sinh — chọn tay ô Nơi sinh (theo giấy khai sinh) (*).")
    for source, label in (("ToKhai_Cha_NgaySinh", "Cha"), ("ToKhai_Me_NgaySinh", "Mẹ")):
        if has_form and not _partial_date(values.get(source)):
            warnings.append(f"Tờ khai không ghi ngày/năm sinh của {label} — nhập tay ô Ngày sinh ({label}) (*).")
    warnings.append(PORTRAIT_WARNING)
    warnings.append(REFUND_WARNING)
    return out, warnings
