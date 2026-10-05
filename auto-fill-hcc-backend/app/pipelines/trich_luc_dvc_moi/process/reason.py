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
Bạn là agent PHÂN VAI hồ sơ CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH / BẢN SAO GIẤY KHAI SINH.
Đọc TOÀN BỘ tài liệu. Không trích field biểu mẫu, không trả JSON. Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): người này có mặt trong
   hồ sơ không, với vai gì.
2. NGƯỜI ĐƯỢC CẤP bản sao = người được đăng ký trên giấy hộ tịch cần cấp bản sao.
3. LOẠI trích lục cần cấp (khai sinh, kết hôn, khai tử, giám hộ, ...).
4. QUAN HỆ của NGƯỜI NỘP với NGƯỜI ĐƯỢC CẤP.

XÁC ĐỊNH NGƯỜI ĐƯỢC CẤP, theo thứ tự:
a. TỜ KHAI cấp bản sao: người ở khối sau câu "cho người có tên dưới đây".
b. GIẤY ỦY QUYỀN xin cấp bản sao: BÊN ỦY QUYỀN là người được cấp (trừ khi giấy ghi rõ xin cho người khác).
c. Giấy hộ tịch trong hồ sơ: giấy khai sinh → người được khai sinh (CON, không phải cha/mẹ/người đi khai);
   trích lục khai tử → người đã chết; giấy chứng nhận kết hôn có hai chủ thể → chọn người nộp nếu người nộp
   là vợ hoặc chồng trên giấy, không thì người tờ khai nêu tên, cuối cùng mới mặc định người chồng.
d. Chỉ có giấy chứng sinh / tờ khai cư trú CT01 → người con trên giấy chứng sinh / người ở mục 1 CT01.
e. Chỉ có CCCD: một thẻ khớp tài khoản và không có ai khác → chính người nộp; có thêm đúng một thẻ
   người khác → người đó.

XÁC ĐỊNH LOẠI: chỉ khi giấy tờ GHI RÕ — mục yêu cầu trên tờ khai / giấy ủy quyền nêu tên loại, hoặc hồ sơ có
chính giấy hộ tịch loại đó của người được cấp. Mục yêu cầu chỉ ghi "Bản sao" / để trống và không có giấy hộ
tịch → "không xác định". Không đoán từ tuổi, tên file hay ngữ cảnh.

XÁC ĐỊNH QUAN HỆ (người nộp là gì CỦA người được cấp), theo thứ tự:
1. Người nộp CHÍNH LÀ người được cấp (trùng số định danh; thiếu số thì trùng họ tên VÀ ngày sinh)
   → "Bản thân". Người được cấp đã chết (trích lục khai tử) thì KHÔNG BAO GIỜ là "Bản thân".
2. Tờ khai ghi "Quan hệ với người được cấp bản sao: X" VÀ người yêu cầu trên tờ khai CHÍNH LÀ người nộp
   → X (quy về một nhãn trong danh sách).
3. Giấy hộ tịch ghi người nộp ở một vai quanh người được cấp (trùng số hoặc họ tên): là cha trên giấy
   khai sinh của người được cấp → "Bố đẻ"; mẹ → "Mẹ đẻ"; là vợ/chồng trên giấy kết hôn → "Vợ"/"Chồng";
   người được cấp là cha/mẹ trên giấy khai sinh CỦA người nộp → "Con đẻ".
4. Quan hệ thật nhưng không có nhãn riêng (em ruột, cô, chú, dì, cậu...) → "Khác" và ghi rõ ở
   "Quan hệ khác".
5. Người nộp không xuất hiện trong hồ sơ, hoặc giấy tờ không chứng minh được quan hệ → "Không xác định".
   TUYỆT ĐỐI không suy quan hệ từ họ, tuổi, quê quán, địa chỉ hay việc ở chung hộ. Là người đi khai sinh /
   người đi khai tử / người ký / bên được ủy quyền KHÔNG chứng minh quan hệ (giấy không ghi quan hệ thì
   vẫn là "Không xác định").
6. Kết luận khác "Không xác định" thì "Căn cứ" phải nêu đúng DÒNG giấy tờ ghi quan hệ đó (vd "Giấy khai
   sinh tài liệu 1: người mẹ = người nộp"); không nêu được dòng nào thì kết luận "Không xác định".
Nhãn hợp lệ: Bản thân, Vợ, Chồng, Con đẻ, Bố đẻ, Mẹ đẻ, Bố nuôi, Mẹ nuôi, Con nuôi, Ông, Bà, Cháu ruột,
Anh ruột, Chị ruột, Khác, Không xác định.

QUY TẮC GIỮ ĐÚNG NGƯỜI:
- Dòng "Giấy tờ tùy thân" trên GIẤY KHAI SINH là của người đi khai sinh, không phải của con.
- Mỗi thông tin đi cùng đúng một người; không ghép họ tên người này với số/ngày sinh người khác.
- Không chắc thì ghi "Không xác định".

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
Loại trích lục cần cấp: khai sinh|kết hôn|khai tử|giám hộ|chấm dứt giám hộ|nhận cha mẹ con|nuôi con nuôi|thay đổi cải chính|ghi chú ly hôn|giám sát giám hộ|chấm dứt giám sát giám hộ|không xác định
Tài liệu nguồn: ...
Căn cứ: ...
</giay_to_ho_tich>
<quan_he>
Kết luận: ...
Quan hệ khác: ...
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
        "- Khối <nguoi_duoc_cap> \"Không xác định\" thì bỏ toàn bộ NguoiDuocCap_*.\n"
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
