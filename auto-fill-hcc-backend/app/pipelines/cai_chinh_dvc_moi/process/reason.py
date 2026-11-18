"""Bước phân vai trước khi trích field: người nộp (tài khoản) ↔ người có nội dung thay đổi ↔ việc đăng ký.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ (Bản thân / Khác) tính SO VỚI TÀI
KHOẢN. Agent chỉ trả text có thẻ để ghim vai cho lượt trích; không trả JSON.
"""

import re
import unicodedata
from datetime import date

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 1400

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ THAY ĐỔI, CẢI CHÍNH, BỔ SUNG THÔNG TIN HỘ TỊCH, XÁC ĐỊNH LẠI DÂN TỘC.
Đọc TOÀN BỘ tài liệu. Không trích field biểu mẫu, không trả JSON. Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): có mặt trong hồ sơ không,
   với vai gì.
2. NGƯỜI CÓ NỘI DUNG THAY ĐỔI = CHỦ của giấy tờ hộ tịch được đề nghị sửa (người được khai sinh trên giấy khai
   sinh đó, vợ / chồng trên giấy kết hôn...), KHÔNG phải người có tên hay năm sinh được sửa. Sửa tên / năm sinh
   của cha, mẹ trên giấy khai sinh của con → người có nội dung thay đổi là CON; người cha / mẹ dù đã chết cũng
   không phải người có nội dung thay đổi.
3. GIẤY TỜ HỘ TỊCH ĐÃ ĐĂNG KÝ cần sửa và LOẠI VIỆC.
4. QUAN HỆ của NGƯỜI NỘP với người có nội dung thay đổi: Bản thân hoặc Khác.

XÁC ĐỊNH NGƯỜI CÓ NỘI DUNG THAY ĐỔI, theo thứ tự:
a. TỜ KHAI: người ở khối sau câu "... cho người có tên dưới đây". Họ tên là tên ĐANG CÓ trong sổ hộ tịch,
   KHÔNG phải tên mới nêu ở dòng "Nội dung". Có tờ khai thì LUÔN theo người này, kể cả khi hồ sơ kèm giấy khai
   sinh / trích lục khai tử / CCCD của chính cha, mẹ, vợ, chồng: các giấy đó là GIẤY CĂN CỨ ghi giá trị đúng của
   thông tin cần sửa, không phải giấy cần sửa. "Giấy hộ tịch cần sửa" khi đó là giấy của người ở tờ khai.
b. Giấy ủy quyền: BÊN ỦY QUYỀN — kể cả khi thông tin cần sửa là tên / năm sinh của CHA, MẸ ghi trên giấy của
   bên ủy quyền (cha, mẹ khi đó chỉ là nội dung bị sửa).
c. Không có tờ khai, có BẢN CAM ĐOAN viết "trong giấy khai sinh (giấy hộ tịch) CỦA TÔI ...": NGƯỜI CAM ĐOAN — chủ
   giấy hộ tịch cần sửa. Thông tin cha / mẹ / vợ / chồng ghi trên giấy đó chỉ là nội dung bị sửa, không biến cha,
   mẹ thành người có nội dung thay đổi.
d. Không có tờ khai: người được đăng ký trên giấy hộ tịch chính (giấy khai sinh / trích lục khai sinh → người
   được khai sinh, không phải cha/mẹ/người đi khai; khai tử → người chết).
e. Không có cả a, b, c, d nhưng hồ sơ có giấy tờ của CHỦ TÀI KHOẢN (tài liệu chứa đúng số định danh trong
   <requester_context>) → chủ tài khoản làm cho BẢN THÂN: người có nội dung thay đổi = chủ tài khoản, lấy họ
   tên / số định danh / ngày sinh từ giấy tờ đó, ghi đúng "Nguồn: giấy tờ chủ tài khoản".

LOẠI VIỆC — chọn MỘT trong bốn: Cải chính / Thay đổi / Bổ sung / Xác định lại dân tộc:
1. Ưu tiên dòng "Đề nghị cơ quan đăng ký việc ..." của tờ khai (mục (4), phần người yêu cầu ghi sau chữ "việc";
   KHÔNG dùng tiêu đề tờ khai vì tiêu đề in sẵn đủ bốn việc). Dòng đó có chữ "cải chính" / "thay đổi" / "bổ sung"
   / "xác định lại dân tộc" → lấy đúng việc đó, KHÔNG xét lại theo nội dung, lý do.
   Vd "Cải chính giấy khai sinh" → Cải chính, kể cả khi nội dung là đổi tên.
   Dòng đó ghi "xác định lại" một thông tin KHÁC dân tộc (quốc tịch, họ tên, ngày sinh…) → KHÔNG phải "Xác định lại
   dân tộc": lý do là sai sót / ghi nhầm → Cải chính; theo nguyện vọng → Thay đổi.
2. Còn lại — không có tờ khai, dòng đó trống, hoặc dòng đó ghi việc khác bốn việc trên (vd "Xác định lại quốc
   tịch", "xác định lại họ tên"; "xác định lại" mà không phải DÂN TỘC thì KHÔNG phải "Xác định lại dân tộc") →
   kết luận theo BẢN CHẤT nội dung + lý do:
   - Cải chính: sửa thông tin đã đăng ký bị SAI SÓT (lý do sai sót khi đăng ký, ghi nhầm, không khớp giấy tờ gốc).
   - Thay đổi: đổi họ, chữ đệm, tên... theo nguyện vọng khi thông tin cũ không sai.
   - Bổ sung: ghi thêm thông tin còn TRỐNG trong sổ hộ tịch.
   - Xác định lại dân tộc: CHỈ khi nội dung là DÂN TỘC.
   Vd dòng đề nghị ghi "Xác định lại quốc tịch", lý do "ghi nhầm khi đăng ký" → Cải chính.
"không xác định" CHỈ khi hồ sơ không có cả dòng đề nghị, nội dung lẫn lý do.

QUAN HỆ — so người nộp với NGƯỜI CÓ NỘI DUNG THAY ĐỔI (khối <nguoi_thay_doi>), KHÔNG so với người yêu cầu tờ
khai. Người nộp trùng người yêu cầu tờ khai CHỈ cho biết người nộp tự đứng tên tờ khai, KHÔNG phải căn cứ
"Bản thân":
- Người nộp CHÍNH LÀ người có nội dung thay đổi (trùng số định danh; thiếu số thì trùng họ tên VÀ ngày sinh)
  → "Bản thân". Người có nội dung thay đổi đã chết → không bao giờ "Bản thân".
- Người nộp là người khác (khác số định danh hoặc khác họ tên) → "Khác".
- Người nộp là người yêu cầu tờ khai mà tờ khai ghi quan hệ khác "Bản thân" (mẹ đẻ, cha, chồng...) → "Khác".
- Không đủ thông tin để so → "Không xác định". Không suy từ họ, tuổi, địa chỉ.
- Ba dòng "... tờ khai" trong khối <quan_he> CHỈ chép từ TỜ KHAI: "Quan hệ trên tờ khai" = chữ ghi sau dấu hai
  chấm của dòng "Quan hệ với người được thay đổi, cải chính..." (vd "Chồng", "Mẹ đẻ"); "Người yêu cầu tờ khai" /
  "Số định danh người yêu cầu tờ khai" = họ tên / số định danh trên dòng "Họ, chữ đệm, tên người yêu cầu" và
  dòng giấy tờ tùy thân ngay dưới. Không có tờ khai hoặc dòng đó trống → "không có". Giấy ủy quyền, bản cam đoan, giấy hộ tịch KHÔNG dùng cho ba dòng này.
- Ba dòng "... giấy ủy quyền" CHỈ đọc từ GIẤY ỦY QUYỀN mà BÊN ỦY QUYỀN là người có nội dung thay đổi; không có
  giấy đó → "không có". "Người được ủy quyền" / "Số định danh người được ủy quyền" = họ tên / số giấy tờ của bên
  ĐƯỢC ủy quyền (dòng "Ủy quyền cho" ghi nhầm tên bên ủy quyền thì lấy tên bên được ủy quyền ở phần nội dung).
  "Quan hệ trên giấy ủy quyền" CHỈ khi giấy ủy quyền GHI RÕ chữ quan hệ giữa hai bên (vd dòng "Mối quan hệ giữa
  người ủy quyền và người được ủy quyền: mẹ"): = NGƯỜI ĐƯỢC ỦY QUYỀN là gì CỦA người có nội dung thay đổi (vd "Mẹ",
  "Chồng", "Anh trai"); chữ đó không rõ chiều thì xác định chiều theo ngày sinh hai bên (cha / mẹ sinh trước con).
  Giấy KHÔNG ghi chữ quan hệ → "không có", TUYỆT ĐỐI không suy quan hệ từ tuổi, họ, địa chỉ. Họ tên / số chép ĐÚNG
  chữ trên giấy ủy quyền, KHÔNG chép từ <requester_context>. "Người được ủy quyền là người nộp": "Có" khi số giấy
  tờ của bên được ủy quyền trùng số định danh chủ tài khoản (OCR có thể thừa / thiếu / sai một chữ số) hoặc cùng
  người theo họ tên chủ tài khoản (bỏ qua dấu, cách viết tên dân tộc); <requester_context> không có họ tên lẫn số
  định danh hoặc không đủ căn cứ → "Không".

THÔNG TIN CẦN SỬA — CHỈ khi KHÔNG có tờ khai mà có BẢN CAM ĐOAN: bản cam đoan thường viết "Trong <giấy hộ tịch
cần sửa> của tôi thì <thông tin> là A, nhưng trong <giấy tờ khác: căn cước, giấy khai sinh / chứng tử của người
đó...> là B". Mỗi thông tin một dòng: ĐANG GHI = A (giá trị trên giấy cần sửa), ĐÚNG THEO = B. Giấy cần sửa có
trong hồ sơ thì soát: A phải đúng là giá trị in trên giấy đó. Thông tin hai bên ghi GIỐNG nhau thì không liệt kê.

QUY TẮC GIỮ ĐÚNG NGƯỜI:
- Dòng "Giấy tờ tùy thân" trên GIẤY KHAI SINH là của người đi khai sinh, không phải của con.
- Mỗi thông tin đi cùng đúng một người; không ghép họ tên người này với số/ngày sinh người khác.

Chỉ trả TEXT theo đúng bốn khối dưới đây, không markdown/code fence, không JSON. Mỗi nhãn một dòng,
"Căn cứ" tối đa 25 từ:
<nguoi_nop>
Họ tên: ...
Số định danh: ...
Có trong hồ sơ: Có|Không
Vai trong hồ sơ: ...
</nguoi_nop>
<nguoi_thay_doi>
Giấy hộ tịch cần sửa: <loại giấy> của <họ tên CHỦ giấy>
Họ tên: <đúng chủ giấy ở dòng trên>
Số định danh: ...
Ngày sinh: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</nguoi_thay_doi>
<viec_dang_ky>
Giấy tờ hộ tịch đã đăng ký: khai sinh|khai tử|kết hôn|giám hộ|giám sát giám hộ|nhận cha mẹ con|không xác định
Loại việc: Cải chính|Thay đổi|Bổ sung|Xác định lại dân tộc|không xác định
Căn cứ: ...
Thông tin cần sửa: (chỉ khi không có tờ khai mà có bản cam đoan; không có thì bỏ dòng này và các dòng "- ...")
- <thông tin>: đang ghi <A> | đúng theo <tên giấy khác>: <B>
</viec_dang_ky>
<quan_he>
Căn cứ: ...
Kết luận: Bản thân|Khác|Không xác định
Quan hệ trên tờ khai: ...
Người yêu cầu tờ khai: ...
Số định danh người yêu cầu tờ khai: ...
Quan hệ trên giấy ủy quyền: ...
Người được ủy quyền: ...
Số định danh người được ủy quyền: ...
Người được ủy quyền là người nộp: Có|Không
</quan_he>
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


def _one_edit_apart(a: str, b: str) -> bool:
    """Hai dãy số lệch đúng một chữ số (thừa / thiếu / sai một chữ số)."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long = sorted((a, b), key=len)
    return any(long[:i] + long[i + 1:] == short for i in range(len(long)))



# Họ tên / tên riêng ngắn thì thêm / bớt 1 ký tự đã là tên khác (Văn A / Văn An) → chỉ nhận gần đúng với họ tên đủ
# dài; tên riêng 2 chữ cái chỉ nhận thay 1 chữ cái, từ 3 chữ cái mới nhận cả thêm / bớt.
_NEAR_NAME_MIN_CHARS = 12
_NEAR_GIVEN_NAME_MIN_CHARS = 3


def name_match(name: str, text: str) -> str:
    """Họ tên có trong một dòng chữ không: "exact" (bỏ dấu, nguyên từ), "near" (lệch 1 ký tự — OCR đọc nhầm một chữ
    cái), "" (không có). Lớp soát dùng để biết một dòng / một thẻ có phải của người có nội dung thay đổi."""
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
            if not long_enough or near or not _one_edit_apart(window, joined):
                continue
            near = given >= _NEAR_GIVEN_NAME_MIN_CHARS or (given == 2 and len(window) == len(joined))
    return "near" if near else ""

_SUBJECT_ANCHOR_RE = re.compile(r"cho\s+người\s+có\s+tên\s+dưới\s+đây", re.IGNORECASE)
_NAME_LABEL_RE = re.compile(r"Họ,?\s*chữ\s*đệm,?\s*(?:và\s+)?tên\s*:\s*(.*)", re.IGNORECASE)
_BIRTH_LABEL_RE = re.compile(r"Ngày,?\s*tháng,?\s*năm\s*sinh\s*:\s*([0-9][0-9/.\-\s]*[0-9])", re.IGNORECASE)
_NEXT_LABEL_RE = re.compile(r"\s*(?:Ngày,?\s*tháng|Giới\s*tính|Dân\s*tộc|Quốc\s*tịch|Nơi\s*cư\s*trú|Giấy\s*tờ)",
                            re.IGNORECASE)
_ANCHOR_SPAN = 400


def _declaration_subjects(documents: list[dict]) -> list[str]:
    """Họ tên + ngày sinh ở khối "cho người có tên dưới đây" của tờ khai — chép bằng mã để model không lẫn với chủ của
    giấy căn cứ (giấy khai sinh / khai tử / CCCD của cha, mẹ, vợ, chồng) kèm trong hồ sơ."""
    out = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        for anchor in _SUBJECT_ANCHOR_RE.finditer(text):
            span = text[anchor.end():anchor.end() + _ANCHOR_SPAN]
            name = _NAME_LABEL_RE.search(span)
            value = _NEXT_LABEL_RE.split(name.group(1))[0].strip(" .:,;…-") if name else ""
            if not value:
                continue
            birth = _BIRTH_LABEL_RE.search(span)
            line = f'tài liệu {index}: "{value[:60]}"' + (f', sinh "{birth.group(1).strip()}"' if birth else "")
            if line not in out:
                out.append(line)
    return out


def _document_hints(documents: list[dict], options: dict | None) -> str:
    """Mỏ neo tất định: tài liệu nào chứa đúng (hoặc gần đúng, OCR lệch một chữ số) số định danh của tài khoản; người
    ở khối "cho người có tên dưới đây" của tờ khai."""
    name, number = requester_context(options)
    hits, near = [], []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if number and number in _digits(text):
            hits.append(str(index))
        elif len(number) == 12 and any(_one_edit_apart(number, run) for run in re.findall(r"\d{11,13}", text)):
            near.append(str(index))
    subjects = _declaration_subjects(documents)
    return "\n".join([
        "<requester_context>",
        f'Họ tên chủ tài khoản (người nộp): "{name or "không có"}".',
        f'Số định danh chủ tài khoản: "{number or "không có"}".',
        "Tài liệu chứa đúng số định danh này: " + (", ".join(hits) if hits else "không có") + ".",
        "Tài liệu chứa số GẦN trùng (OCR lệch một chữ số, vẫn là chủ tài khoản): "
        + (", ".join(near) if near else "không có") + ".",
        "Tài khoản là MỐC để tính quan hệ, không phải dữ liệu của người có nội dung thay đổi.",
        "</requester_context>",
    ] + ([
        # Chỉ thêm khi có tờ khai: hồ sơ không tờ khai giữ nguyên ngữ cảnh cũ.
        "<to_khai_context>",
        "Khối \"cho người có tên dưới đây\" của tờ khai ghi: " + "; ".join(subjects) + ".",
        "Người có nội dung thay đổi là người đó (quy tắc a; dòng chép bằng mã, đọc lại OCR nếu tên chép lệch chữ), dù "
        "thông tin cần sửa là của cha, mẹ, vợ, chồng.",
        "</to_khai_context>",
    ] if subjects else []))


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
    blocks = {tag: section(raw, tag) for tag in ("nguoi_nop", "nguoi_thay_doi", "viec_dang_ky", "quan_he")}
    if not blocks["nguoi_thay_doi"] and not blocks["viec_dang_ky"]:
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
        "- NguoiThayDoi_* CHỈ lấy của đúng người ở <nguoi_thay_doi>; không lấy của người nộp, cha/mẹ, "
        "người đi khai, người ủy quyền khác.\n"
        "- ViecDangKy / HoSo_LoaiGiayTo theo <viec_dang_ky>; khối đó \"không xác định\" thì bỏ field tương ứng.\n"
        "- Khối <nguoi_thay_doi> \"Không xác định\" thì bỏ toàn bộ NguoiThayDoi_*.\n"
        "</phan_vai_da_xac_dinh>"
    )


_BIRTH_CERT_HEAD_RE = re.compile(r"^\W*(giay khai sinh|trich luc khai sinh)")
_BIRTH_LINE_RE = re.compile(r"ngay,? thang,? nam sinh|^ngay sinh")
_BIRTH_DATE_RE = re.compile(r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})")


def holder_birth(text) -> date | None:
    """Ngày sinh của người được khai sinh trên một giấy khai sinh / trích lục khai sinh: dòng "Ngày, tháng, năm sinh"
    đầu tiên sau tiêu đề giấy."""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    start = next((i for i, line in enumerate(lines) if _BIRTH_CERT_HEAD_RE.match(_fold(line))), None)
    for line in lines[start:] if start is not None else []:
        if _BIRTH_LINE_RE.search(_fold(line)):
            found = _BIRTH_DATE_RE.search(line)
            try:
                return date(int(found.group(3)), int(found.group(2)), int(found.group(1))) if found else None
            except ValueError:
                return None
    return None


def _birth_certificates_note(documents: list[dict], context: str) -> str:
    """Khối sự thật do mã đọc: mỗi giấy khai sinh trong hồ sơ là của người sinh năm nào, cùng / khác năm sinh người có
    nội dung thay đổi. Hồ sơ cải chính HỌ TÊN có giấy cần sửa ghi TÊN CŨ, kèm giấy khai sinh của cha / mẹ in mới rõ chữ:
    model hay chọn giấy theo tên nên lấy nhầm số / ngày đăng ký của giấy cha / mẹ."""
    subject = _DATE_TEXT_RE.search(labeled_value(section(context, "nguoi_thay_doi"), "Ngày sinh") or "")
    rows = []
    for index, document in enumerate(documents, start=1):
        birth = holder_birth(document.get("text"))
        if not birth:
            continue
        relation = ""
        if subject:
            same = birth.year == int(subject.group(3))
            relation = (" — CÙNG năm sinh với người có nội dung thay đổi" if same
                        else " — KHÁC năm sinh: giấy của người khác (cha / mẹ...), không lấy HoSo_* ở đây")
        rows.append(f"- Tài liệu {index} ({document.get('name') or ''}): người được khai sinh sinh "
                    f"{birth.strftime('%d/%m/%Y')}{relation}")
    if len(rows) < 2:
        return ""
    return ("\n\n<giay_khai_sinh_trong_ho_so>\nMã đọc sẵn dòng ngày sinh của từng giấy khai sinh. Giấy cần sửa là giấy "
            "CÙNG năm sinh, kể cả khi họ tên trên giấy khác (tên cũ đang xin cải chính / OCR đọc lệch):\n"
            + "\n".join(rows) + "\n</giay_khai_sinh_trong_ho_so>")


_DATE_TEXT_RE = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})")
_REGISTRATION_FIELDS = ("HoSo_So", "HoSo_QuyenSo", "HoSo_NgayDangKy", "HoSo_NoiDangKy")


def _as_date(text) -> date | None:
    found = _BIRTH_DATE_RE.search(str(text or ""))
    try:
        return date(int(found.group(3)), int(found.group(2)), int(found.group(1))) if found else None
    except ValueError:
        return None


def _carries(text: str, name: str, value) -> bool:
    if name == "HoSo_NgayDangKy":
        target = _as_date(value)
        return bool(target) and any(_as_date("/".join(groups)) == target for groups in _BIRTH_DATE_RE.findall(text))
    number = " ".join(str(value or "").split())
    return bool(re.search(r"\d", number)) and bool(re.search(rf"(?<![\w/]){re.escape(number)}(?![\w/])", text))


def drop_other_holder_registration(values: dict, documents: list[dict], context: str = "") -> dict:
    """Số / ngày đăng ký lượt trích chỉ có trên giấy khai sinh của người sinh KHÁC NĂM với người có nội dung thay đổi
    (giấy khai sinh của cha / mẹ kèm làm căn cứ), trong khi hồ sơ có giấy khai sinh CÙNG năm sinh → bỏ cả bộ HoSo_*
    (thà thiếu còn hơn sai: ô trống thì cán bộ tự điền / thanh tra đợt 2 bổ sung). Trả bản sao ``values``."""
    # Ngày sinh theo khối phân vai trước: lượt trích có lúc chép ngày sinh của cha / mẹ vào NguoiThayDoi_NgaySinh.
    born = _as_date(labeled_value(section(context, "nguoi_thay_doi"), "Ngày sinh")
                    or values.get("NguoiThayDoi_NgaySinh"))
    if not born or not documents:
        return values
    births = {index: holder_birth(document.get("text")) for index, document in enumerate(documents)}
    if not any(birth and birth.year == born.year for birth in births.values()):
        return values
    homes = {index for index, document in enumerate(documents) for name in ("HoSo_So", "HoSo_NgayDangKy")
             if values.get(name) and _carries(str(document.get("text") or ""), name, values[name])}
    if homes and all(births.get(index) and births[index].year != born.year for index in homes):
        return {name: value for name, value in values.items() if name not in _REGISTRATION_FIELDS}
    return values


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
    context = _render_context(_drop_unquoted_authorization_relation(raw, documents), options)
    return context + _birth_certificates_note(documents, context) if context else context


def _drop_unquoted_authorization_relation(raw: str, documents: list[dict]) -> str:
    """Quan hệ trên giấy ủy quyền chỉ giữ khi OCR có dòng ghi quan hệ chứa đúng chữ đó: giấy ủy quyền không ghi quan
    hệ thì model hay tự suy (từ tuổi hai bên) ra quan hệ không có trên giấy."""
    relation = _fold(labeled_value(section(raw, "quan_he"), "Quan hệ trên giấy ủy quyền"))
    lines = [_fold(line) for d in documents for line in str(d.get("text") or "").splitlines()]
    if relation and any("quan he" in line and re.search(rf"(?<!\w){re.escape(relation)}(?!\w)", line)
                        for line in lines):
        return raw
    return re.sub(r"(?im)^([ \t]*Quan hệ trên giấy ủy quyền[ \t]*:).*$", r"\1 không có", raw)
