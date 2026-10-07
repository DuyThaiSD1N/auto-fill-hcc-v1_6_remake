"""Bước phân vai trước khi trích field: người nộp (tài khoản) ↔ người có nội dung thay đổi ↔ việc đăng ký.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ (Bản thân / Khác) tính SO VỚI TÀI
KHOẢN. Agent chỉ trả text có thẻ để ghim vai cho lượt trích; không trả JSON.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 900

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ THAY ĐỔI, CẢI CHÍNH, BỔ SUNG THÔNG TIN HỘ TỊCH, XÁC ĐỊNH LẠI DÂN TỘC.
Đọc TOÀN BỘ tài liệu. Không trích field biểu mẫu, không trả JSON. Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): có mặt trong hồ sơ không,
   với vai gì.
2. NGƯỜI CÓ NỘI DUNG THAY ĐỔI = người mà thông tin hộ tịch được đề nghị sửa.
3. GIẤY TỜ HỘ TỊCH ĐÃ ĐĂNG KÝ cần sửa và LOẠI VIỆC.
4. QUAN HỆ của NGƯỜI NỘP với người có nội dung thay đổi: Bản thân hoặc Khác.

XÁC ĐỊNH NGƯỜI CÓ NỘI DUNG THAY ĐỔI, theo thứ tự:
a. TỜ KHAI: người ở khối sau câu "... cho người có tên dưới đây". Họ tên là tên ĐANG CÓ trong sổ hộ tịch,
   KHÔNG phải tên mới nêu ở dòng "Nội dung".
b. Giấy ủy quyền: BÊN ỦY QUYỀN.
c. Không có tờ khai: người được đăng ký trên giấy hộ tịch chính (giấy khai sinh / trích lục khai sinh → người
   được khai sinh, không phải cha/mẹ/người đi khai; khai tử → người chết).
d. Không có cả a, b, c nhưng hồ sơ có giấy tờ của CHỦ TÀI KHOẢN (tài liệu chứa đúng số định danh trong
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

QUAN HỆ:
- Người nộp CHÍNH LÀ người có nội dung thay đổi (trùng số định danh; thiếu số thì trùng họ tên VÀ ngày sinh)
  → "Bản thân". Người có nội dung thay đổi đã chết → không bao giờ "Bản thân".
- Người nộp là người khác (khác số định danh hoặc khác họ tên) → "Khác".
- Không đủ thông tin để so → "Không xác định". Không suy từ họ, tuổi, địa chỉ.

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
Họ tên: ...
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
</viec_dang_ky>
<quan_he>
Kết luận: Bản thân|Khác|Không xác định
Căn cứ: ...
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


def _document_hints(documents: list[dict], options: dict | None) -> str:
    """Mỏ neo tất định: tài liệu nào chứa đúng số định danh của tài khoản."""
    name, number = requester_context(options)
    hits = [
        str(index)
        for index, document in enumerate(documents, start=1)
        if number and number in _digits(document.get("text"))
    ]
    return "\n".join([
        "<requester_context>",
        f'Họ tên chủ tài khoản (người nộp): "{name or "không có"}".',
        f'Số định danh chủ tài khoản: "{number or "không có"}".',
        "Tài liệu chứa đúng số định danh này: " + (", ".join(hits) if hits else "không có") + ".",
        "Tài khoản là MỐC để tính quan hệ, không phải dữ liệu của người có nội dung thay đổi.",
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
