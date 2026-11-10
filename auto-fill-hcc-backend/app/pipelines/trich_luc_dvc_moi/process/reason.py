"""Bước phân vai trước khi trích field: người nộp (tài khoản) ↔ người được cấp ↔ giấy hộ tịch.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ phải tính SO VỚI TÀI KHOẢN.
Agent chỉ trả text có thẻ để ghim vai cho lượt trích; không trả JSON, không thay lượt trích.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 900

QUAN_HE_OPTIONS = (
    "Bản thân", "Vợ", "Chồng", "Con đẻ", "Bố đẻ", "Mẹ đẻ", "Bố nuôi", "Mẹ nuôi", "Con nuôi",
    "Ông", "Bà", "Cháu ruột", "Anh ruột", "Chị ruột", "Khác",
)

_ROLE_PROMPT = """
<vai_tro>
Bạn là agent PHÂN VAI hồ sơ CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH / BẢN SAO GIẤY KHAI SINH.
Đọc TOÀN BỘ tài liệu. Không trích field biểu mẫu, không trả JSON. Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): người này có mặt trong
   hồ sơ không, với vai gì.
2. NGƯỜI ĐƯỢC CẤP bản sao = người được đăng ký trên giấy hộ tịch cần cấp bản sao.
3. LOẠI trích lục cần cấp (khai sinh, kết hôn, khai tử, giám hộ, ...).
4. QUAN HỆ của NGƯỜI NỘP với NGƯỜI ĐƯỢC CẤP.
</vai_tro>

<xac_dinh_nguoi_duoc_cap>
Theo thứ tự:
a. TỜ KHAI cấp bản sao: người ở khối sau câu "cho người có tên dưới đây".
b. GIẤY ỦY QUYỀN xin cấp bản sao: BÊN ỦY QUYỀN là người được cấp (trừ khi giấy ghi rõ xin cho người khác).
c. Giấy hộ tịch trong hồ sơ: giấy khai sinh → người được khai sinh (CON, không phải cha/mẹ/người đi khai);
   trích lục khai tử → người đã chết; giấy chứng nhận kết hôn có hai chủ thể và là giấy CHUNG của hai vợ chồng
   → người nộp là vợ hoặc chồng trên giấy thì LUÔN chọn người nộp (kể cả khi tờ khai nêu tên người kia), không
   thì người tờ khai nêu tên, cuối cùng mới mặc định người chồng.
   Có giấy hộ tịch thì LUÔN xác định được người được cấp theo mục này, không cần tờ khai: chỉ có giấy hộ tịch
   của người nộp (vd khai sinh của chính người nộp, kể cả kèm CCCD người nộp) → người nộp.
   Riêng khi có GIẤY KHAI SINH của người nộp kèm trích lục khai tử / kết hôn của CHA hoặc MẸ ghi trên giấy khai
   sinh đó → giấy khai sinh của người nộp chỉ để chứng minh quan hệ, người được cấp là cha / mẹ đó. (Giấy kết
   hôn mà người nộp là vợ / chồng vẫn theo quy tắc giấy kết hôn ở trên.)
d. Chỉ có giấy chứng sinh / tờ khai cư trú CT01 → người con trên giấy chứng sinh / người ở mục 1 CT01.
e. Hồ sơ KHÔNG có tờ khai, giấy ủy quyền hay giấy hộ tịch nào, chỉ có thẻ CCCD/CMND: có đúng một thẻ của người
   KHÁC người nộp → người đó; chỉ có thẻ của người nộp → "Không xác định" (thẻ người nộp chỉ chứng minh người
   đi làm thủ tục).
</xac_dinh_nguoi_duoc_cap>

<xac_dinh_loai>
Chỉ khi giấy tờ GHI RÕ, theo thứ tự:
1. Mục yêu cầu trên tờ khai ("Đề nghị cơ quan cấp bản sao trích lục ...") / giấy ủy quyền nêu tên loại → LẤY
   ĐÚNG loại đó, kể cả khi hồ sơ kèm giấy hộ tịch loại KHÁC. Giấy kèm theo chỉ là giấy chứng minh, không đổi
   loại: tờ khai xin "Khai sinh" kèm trích lục khai tử của chính người đó (để mở thừa kế) → vẫn "khai sinh".
2. Mục yêu cầu không nêu loại → hồ sơ có chính giấy hộ tịch loại đó của người được cấp.
3. Mục yêu cầu chỉ ghi "Bản sao" / để trống và không có giấy hộ tịch → "không xác định".
Không đoán từ tuổi, tên file hay ngữ cảnh.
</xac_dinh_loai>

<doi_chieu_nguoi>
Áp dụng khi so người yêu cầu trên tờ khai, cha / mẹ / vợ / chồng / người đi khai trên giấy hộ tịch với người
nộp, và người nộp với người được cấp. Tờ khai thường viết tay, OCR hay đọc lệch họ tên (sai dấu, sai một chữ)
và số giấy tờ (lệch 1–2 chữ số, thiếu / thừa một số), nên KHÔNG đòi trùng tuyệt đối:
- Số giấy tờ TRÙNG HOÀN TOÀN → LUÔN là cùng một người, dù họ tên lệch bao nhiêu (tên lệch là do OCR / viết tay).
- So số theo TỪNG chữ số. CÙNG MỘT NGƯỜI khi số giấy tờ trùng hoặc chỉ lệch tối đa 2 chữ số; HOẶC họ tên trùng
  hoặc chỉ lệch dấu / một chữ VÀ có thêm ít nhất một dấu hiệu khớp (số giấy tờ gần đúng, ngày / năm sinh, dòng
  "Thông tin khác", CCCD của người đó trong hồ sơ, chữ ký). <requester_context> đã liệt kê sẵn tài liệu có số
  trùng / lệch 1–2 chữ số và dòng có họ tên chủ tài khoản — dùng các dòng đó làm dấu hiệu.
- Dòng ghi người đó KHÔNG kèm số giấy tờ (cha / mẹ / vợ / chồng / người được khai sinh / người đi khai trên giấy
  hộ tịch mẫu cũ) → so HỌ TÊN ĐẦY ĐỦ: trùng hoặc chỉ lệch dấu với chủ tài khoản, không có dấu hiệu khác người
  (vd năm sinh khác năm sinh trên CCCD người nộp trong hồ sơ) → CÙNG MỘT NGƯỜI. Khác tên riêng → khác người.
- Số CMND cũ (9 số) và số định danh / CCCD (12 số) là hai loại giấy khác nhau của cùng một người: KHÔNG so với
  nhau, khác nhau không phải dấu hiệu khác người → đối chiếu bằng họ tên, ngày / năm sinh.
- KHÁC NGƯỜI khi cả họ tên lẫn số giấy tờ đều khác rõ (khác tên riêng, số lệch nhiều chữ số).
- Không đủ dấu hiệu → "Không xác định". "Căn cứ" nêu dấu hiệu đã dùng (vd "số giấy tờ trùng tài khoản, tên
  lệch một chữ do OCR").
<vi_du>
Tên, số minh họa, không có thật:
- Tài khoản "Trần Văn Bình" — 001090000123; tờ khai: người yêu cầu "Trần Văn Bính" — 001090000123, quan hệ "Bố"
  → số trùng hoàn toàn → cùng người → Kết luận "Bố đẻ".
- Tài khoản "Phạm Thị Hoa" — 031185000456; tờ khai: người yêu cầu "Phạm Thi Hòa" — 031185000465, quan hệ "Con"
  → số lệch 2 chữ số, tên chỉ lệch dấu → cùng người → Kết luận "Con đẻ".
- Tài khoản "Lê Văn Cường" — 024080000789; tờ khai: người yêu cầu "Nguyễn Thị Dung" — 024195000321, quan hệ "Mẹ"
  → khác tên riêng, số lệch nhiều chữ số → khác người → không lấy quan hệ trên tờ khai.
</vi_du>
</doi_chieu_nguoi>

<xac_dinh_quan_he>
Người nộp là gì CỦA người được cấp. Có hai nhánh: "Bản thân", hoặc không phải bản thân. Nhánh không phải bản
thân chỉ ra nhãn cụ thể khi giấy tờ ghi rõ quan hệ đó; không ghi thì "Không xác định".
Theo thứ tự — "CHÍNH LÀ" / "trùng" xét theo <doi_chieu_nguoi>:
1. Người nộp CHÍNH LÀ người được cấp (giấy không ghi số thì so họ tên theo <doi_chieu_nguoi>)
   → "Bản thân". Người được cấp đã chết (trích lục khai tử) thì KHÔNG BAO GIỜ là "Bản thân".
2. Tờ khai ghi "Quan hệ với người được cấp bản sao: X" VÀ người yêu cầu trên tờ khai CHÍNH LÀ người nộp
   (= dòng "Đối chiếu với người nộp" là "cùng người") → X (quy về một nhãn trong danh sách). Đã đối chiếu là
   "cùng người" thì KHÔNG so lại họ tên ở bước này.
3. Giấy hộ tịch ghi người nộp ở một vai quanh người được cấp (trùng số hoặc họ tên): là cha trên giấy
   khai sinh của người được cấp → "Bố đẻ"; mẹ → "Mẹ đẻ"; là vợ/chồng trên giấy kết hôn → "Vợ"/"Chồng";
   người được cấp là cha/mẹ trên giấy khai sinh CỦA người nộp → "Con đẻ"; người nộp là người đi khai và giấy
   ghi "Quan hệ với người chết / người được khai sinh: X" → X. Dòng "Quan hệ với ..." đó là quan hệ của NGƯỜI ĐI
   KHAI: người đi khai không phải người nộp thì không lấy.
4. Quan hệ thật nhưng không có nhãn riêng (em ruột, cô, chú, dì, cậu...) → "Khác" và ghi rõ ở
   "Quan hệ khác".
5. Người nộp không xuất hiện trong hồ sơ (sau khi theo <doi_chieu_nguoi>), hoặc không giấy nào ghi quan hệ của
   người nộp với người được cấp → "Không xác định". Không suy quan hệ từ họ, tuổi, quê quán, địa chỉ hay việc ở
   chung hộ; chỉ là người đi khai sinh / khai tử, người ký, bên được ủy quyền mà giấy không ghi quan hệ thì chưa đủ.
6. Kết luận khác "Không xác định" thì phải nêu "Vai người nộp trên giấy" và chép NGUYÊN VĂN (đúng từng chữ OCR,
   không diễn giải, không thêm tên tài liệu) một dòng làm "Dòng giấy ghi quan hệ":
   - cha / mẹ / vợ / chồng: dòng ghi TÊN NGƯỜI NỘP ở vai đó (vd dòng "Họ, chữ đệm, tên người mẹ: ..." trên giấy
     khai sinh của người được cấp) → Bố đẻ / Mẹ đẻ / Vợ / Chồng (hoặc Bố nuôi / Mẹ nuôi khi giấy ghi nuôi).
   - con: người nộp là người được khai sinh trên giấy có cha / mẹ là người được cấp → dòng ghi TÊN NGƯỜI NỘP là
     người được khai sinh → Con đẻ.
   - người yêu cầu tờ khai: dòng "Quan hệ với người được cấp bản sao ..." của tờ khai.
   - người đi khai có dòng quan hệ: người đi khai CHÍNH LÀ người nộp → dòng "Quan hệ với người chết / người được
     khai sinh: ...".
   Chỉ là người đi khai không kèm dòng quan hệ, người ký, bên được ủy quyền, hoặc chỉ cùng họ / năm sinh / quê
   → vai "người đi khai" / "bên được ủy quyền" / "không có" và Kết luận "Không xác định".
Nhãn hợp lệ: Bản thân, Vợ, Chồng, Con đẻ, Bố đẻ, Mẹ đẻ, Bố nuôi, Mẹ nuôi, Con nuôi, Ông, Bà, Cháu ruột,
Anh ruột, Chị ruột, Khác, Không xác định.
</xac_dinh_quan_he>

<giu_dung_nguoi>
- Dòng "Giấy tờ tùy thân" trên GIẤY KHAI SINH là của người đi khai sinh, không phải của con.
- Mỗi thông tin đi cùng đúng một người; không ghép họ tên người này với số/ngày sinh người khác.
- Không chắc một thông tin thuộc ai thì ghi "Không xác định". Riêng câu hỏi "có phải cùng một người" thì
  theo <doi_chieu_nguoi> — tên lệch do OCR không phải là "không chắc".
</giu_dung_nguoi>

<dinh_dang_tra_ve>
Chỉ trả TEXT theo đúng bốn khối dưới đây, không markdown/code fence, không JSON. Mỗi nhãn một dòng,
"Căn cứ" tối đa 25 từ, chỉ ghi kết luận:
<nguoi_nop>
Họ tên: ...
Số định danh: ...
Có trong hồ sơ: Có|Không
Vai trong hồ sơ: ...
</nguoi_nop>
<nguoi_duoc_cap>
Họ tên: ...
Số định danh: ...
Ngày sinh: ...
Giới tính: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</nguoi_duoc_cap>
<giay_to_ho_tich>
Loại ghi trên tờ khai: <chép đúng chữ sau "Đề nghị cơ quan cấp bản sao trích lục" / loại nêu trong giấy ủy quyền> (không có → không có)
Loại trích lục cần cấp: khai sinh|kết hôn|khai tử|giám hộ|chấm dứt giám hộ|nhận cha mẹ con|nuôi con nuôi|thay đổi cải chính|ghi chú ly hôn|giám sát giám hộ|chấm dứt giám sát giám hộ|không xác định
Tài liệu nguồn: ...
Căn cứ: ...
</giay_to_ho_tich>
<quan_he>
Người yêu cầu tờ khai: <họ tên> — <số giấy tờ tùy thân> (không có tờ khai → không có)
Quan hệ ghi trên tờ khai: <chép đúng chữ sau "Quan hệ với người được cấp bản sao..."> (không có → không có)
Đối chiếu với người nộp: cùng người|khác người|không xác định — <dấu hiệu theo <doi_chieu_nguoi>: số trùng / lệch mấy chữ số, tên trùng / lệch>
Vai người nộp trên giấy: cha|mẹ|vợ|chồng|con|người yêu cầu tờ khai|người đi khai có dòng quan hệ|người đi khai|bên được ủy quyền|không có
Dòng giấy ghi quan hệ: <chép NGUYÊN VĂN một dòng OCR theo quy tắc 6 trong <xac_dinh_quan_he>> (không có → không có)
Kết luận: ...
Quan hệ khác: ...
Căn cứ: ...
</quan_he>
</dinh_dang_tra_ve>
""".strip()


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    return re.sub(r"\s+", " ", text).strip()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def requester_context(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return (
        str(ctx.get("applicantFullname") or "").strip(),
        _digits(ctx.get("applicantIdentityNumber")),
    )


_NAME_LINES_MAX = 4


def _near_number(text: str, number: str) -> bool:
    """Có dãy số cùng độ dài lệch 1–2 chữ số với số tài khoản (số viết tay / OCR đọc lệch)."""
    for run in re.findall(r"\d[\d .]*\d", str(text or "")):
        digits = _digits(run)
        for start in range(0, len(digits) - len(number) + 1):
            if 0 < sum(a != b for a, b in zip(digits[start:start + len(number)], number)) <= 2:
                return True
    return False


def _within_one_edit(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:] or (len(a) == len(b) and a[i + 1:] == b[i + 1:])


# Họ tên / tên riêng ngắn thì thêm / bớt 1 ký tự đã là tên khác (Văn A / Văn An, Văn An / Văn Anh) → chỉ nhận
# gần đúng với họ tên đủ dài; tên riêng 2 chữ cái chỉ nhận thay 1 chữ cái (OCR đọc nhầm Ưa / Ưu), từ 3 chữ cái
# mới nhận cả thêm / bớt.
_NEAR_NAME_MIN_CHARS = 12
_NEAR_GIVEN_NAME_MIN_CHARS = 3


def name_match(name: str, text: str) -> str:
    """Họ tên có trong một dòng chữ không: "exact" (bỏ dấu, nguyên từ), "near" (lệch 1 ký tự — OCR đọc
    nhầm một chữ cái), "" (không có)."""
    target = _fold(name).split()
    words = re.findall(r"[a-z0-9]+", _fold(text))
    if len(target) < 2 or not words:
        return ""
    joined = " ".join(target)
    long_enough = len(joined) >= _NEAR_NAME_MIN_CHARS
    given = len(target[-1])
    near = False
    for size in (len(target), len(target) - 1, len(target) + 1):
        for start in range(0, len(words) - size + 1):
            window = " ".join(words[start:start + size])
            if window == joined:
                return "exact"
            if not long_enough or near or not _within_one_edit(window, joined):
                continue
            near = given >= _NEAR_GIVEN_NAME_MIN_CHARS or (given == 2 and len(window) == len(joined))
    return "near" if near else ""


def _name_lines(documents: list[dict], name: str) -> list[str]:
    """Dòng OCR chứa họ tên chủ tài khoản (bỏ dấu, nguyên từ; hoặc lệch 1 ký tự) — dòng cha/mẹ/vợ/chồng thường
    không kèm số."""
    lines = []
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            match = name_match(name, line)
            if match:
                note = "" if match == "exact" else " (gần đúng, lệch 1 ký tự)"
                lines.append(f'tài liệu {index}: "{line.strip()[:120]}"{note}')
                if len(lines) >= _NAME_LINES_MAX:
                    return lines
    return lines


def _document_hints(documents: list[dict], options: dict | None) -> str:
    """Mỏ neo tất định: tài liệu nào chứa số định danh (đúng / lệch 1–2 chữ số) và dòng nào chứa họ tên tài khoản."""
    name, number = requester_context(options)
    hits = [
        str(index)
        for index, document in enumerate(documents, start=1)
        if number and number in _digits(document.get("text"))
    ]
    near = [
        str(index)
        for index, document in enumerate(documents, start=1)
        if number and str(index) not in hits and _near_number(document.get("text"), number)
    ]
    name_lines = _name_lines(documents, name) if name else []
    return "\n".join([
        "<requester_context>",
        f'Họ tên chủ tài khoản (người nộp): "{name or "không có"}".',
        f'Số định danh chủ tài khoản: "{number or "không có"}".',
        "Tài liệu chứa đúng số định danh này: " + (", ".join(hits) if hits else "không có") + ".",
        "Tài liệu chứa số lệch 1–2 chữ số so với số này: " + (", ".join(near) if near else "không có") + ".",
        "Dòng ghi họ tên chủ tài khoản (bỏ dấu): " + ("; ".join(name_lines) if name_lines else "không có") + ".",
        "Tài khoản là MỐC để tính quan hệ, không phải dữ liệu của người được cấp.",
        "</requester_context>",
    ])


def _build_user_content(documents: list[dict], options: dict | None) -> str:
    body = "\n\n---\n\n".join(
        f"===== Tài liệu {index}: {document.get('name') or '(không tên)'} =====\n"
        f"{str(document.get('text') or '').strip()}"
        for index, document in enumerate(documents, start=1)
    )
    return f"{_document_hints(documents, options)}\n\nOCR hồ sơ:\n\n{body}"


def section(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*([\s\S]*?)\s*(?:</{tag}>|$)", str(text or ""), flags=re.IGNORECASE)
    if not match:
        return ""
    # Khối bị cắt cụt (hết token) không có thẻ đóng: chỉ giữ tới thẻ mở kế tiếp.
    return re.split(r"\n\s*<[a-z_]+>", match.group(1))[0].strip()


def labeled_value(block: str, label: str) -> str:
    # [ \t]* thay \s*: nhãn để trống không được nuốt sang dòng kế tiếp.
    match = re.search(rf"(?im)^[ \t]*{re.escape(label)}[ \t]*:[ \t]*(.*?)[ \t]*$", block or "")
    value = match.group(1).strip() if match else ""
    return "" if _fold(value) in {"", "...", "khong xac dinh", "khong co", "khong ro"} else value


def _render_context(raw: str, options: dict | None) -> str:
    blocks = {tag: section(raw, tag) for tag in ("nguoi_nop", "nguoi_duoc_cap", "giay_to_ho_tich", "quan_he")}
    if not blocks["nguoi_duoc_cap"] and not blocks["giay_to_ho_tich"]:
        return ""
    name, number = requester_context(options)
    body = "\n".join(
        f"<{tag}>\n{value or 'Không xác định'}\n</{tag}>" for tag, value in blocks.items()
    )
    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Kết quả phân vai đã phân tích trước. Dùng làm chuẩn, KHÔNG tự đổi người:\n"
        f"{body}\n"
        f"Tài khoản người nộp: {name or '?'} — {number or '?'}.\n"
        "- NguoiDuocCap_* CHỈ lấy của đúng người ở <nguoi_duoc_cap>; không lấy của người nộp, cha/mẹ, "
        "người đi khai, người ủy quyền khác.\n"
        "- GiayTo_* CHỈ lấy theo loại trích lục ở <giay_to_ho_tich> và đúng người được cấp.\n"
        "- Khối <nguoi_duoc_cap> CHỈ có đúng một dòng \"Không xác định\" (không có Họ tên) thì bỏ toàn bộ "
        "NguoiDuocCap_*. Khối có Họ tên thì PHẢI trích NguoiDuocCap_* đọc được trên giấy; một dòng trong khối ghi "
        "\"Không xác định\" (vd số định danh, giới tính) chỉ là thông tin đó chưa có, không bỏ cả khối.\n"
        "</phan_vai_da_xac_dinh>"
    )


async def build_context(documents: list[dict], options: dict | None = None) -> str:
    if not documents:
        return ""
    raw = await client.chat_text(
        [
            {"role": "system", "content": _ROLE_PROMPT},
            {"role": "user", "content": _build_user_content(documents, options)},
        ],
        max_tokens=_REASON_MAX_TOKENS,
        temperature=0,
        enable_thinking=settings.agent_reasoning,
    )
    return _render_context(raw, options)
