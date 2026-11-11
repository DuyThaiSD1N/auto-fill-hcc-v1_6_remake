"""Bước phân vai trước khi trích field đăng ký khai sinh: người nộp (tài khoản) ↔ con ↔ mẹ ↔ cha.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ (Cha / Mẹ / Khác) tính SO VỚI TÀI KHOẢN.
Agent chỉ trả text có thẻ để ghim vai cho lượt trích; không trả JSON.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 1100

LOAI_KHAI_SINH_OPTIONS = (
    "Đã xác định được cả cha lẫn mẹ",
    "Chưa xác định được mẹ",
    "Chưa xác định được cha",
    "Chưa xác định được cả cha lẫn mẹ",
    "Trẻ bị bỏ rơi",
)

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ ĐĂNG KÝ KHAI SINH. Đọc TOÀN BỘ tài liệu. Không trích field biểu mẫu, không trả JSON.
Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): có mặt trong hồ sơ không,
   với vai gì.
2. CON = người được đăng ký khai sinh; MẸ; CHA.
3. QUAN HỆ của NGƯỜI NỘP với CON.
4. LOẠI KHAI SINH và người được khai sinh đã có hồ sơ, giấy tờ cá nhân hay chưa.

XÁC ĐỊNH VAI, theo thứ tự nguồn:
a. TỜ KHAI ĐĂNG KÝ KHAI SINH: người sau câu "Đề nghị cơ quan đăng ký khai sinh cho người dưới đây" là CON; các
   dòng "Họ, chữ đệm, tên người mẹ" / "người cha" là MẸ / CHA. Hồ sơ CÓ tờ khai mà tờ khai để trống dòng người cha →
   CHA "Không xác định" và loại khai sinh "Chưa xác định được cha", KHÔNG lấy cha từ giấy chứng sinh / bản cam đoan
   (tương tự mẹ). Quy tắc này CHỈ áp khi hồ sơ có tờ khai.
b. GIẤY CHỨNG SINH: con là "Dự định đặt tên con" (tên có thể bị gạch sửa tay — lấy tên khớp tờ khai), mẹ là
   người sinh; giấy chứng sinh KHÔNG có dòng cha, nên KHÔNG phải căn cứ để kết luận "Chưa xác định được cha".
   Hồ sơ không có tờ khai thì KHÔNG được ghi "Tờ khai để trống".
c. GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ: chồng là CHA, vợ là MẸ. Hồ sơ KHÔNG có tờ khai mà có giấy kết hôn với VỢ trùng
   MẸ (người sinh trên giấy chứng sinh) → CHA = CHỒNG trên giấy kết hôn (con sinh trong thời kỳ hôn nhân), loại khai
   sinh "Đã xác định được cả cha lẫn mẹ". Giấy chứng sinh không ghi cha KHÔNG có nghĩa là chưa xác định được cha.
d. Giấy cam đoan / văn bản người làm chứng về việc sinh; trích lục khai tử của cha/mẹ (người đó ĐÃ CHẾT).
e. CCCD: gán vào đúng người có cùng họ tên / số định danh ở các giấy trên; không gán theo giới tính khi giấy tờ đã
   ghi rõ tên cha/mẹ. Người đi khai tử, người làm chứng, cán bộ ký không phải cha/mẹ/con.
f. Hồ sơ KHÔNG có tờ khai, KHÔNG có giấy kết hôn mà có CCCD của một người NAM (không phải người nộp, không phải
   người làm chứng / người đi khai tử) → người đó là CHA (người dân nộp CCCD của cha để khai phần cha), loại khai
   sinh "Đã xác định được cả cha lẫn mẹ".

QUAN HỆ (người nộp là gì CỦA CON):
- Người nộp là MẸ → "Mẹ"; là CHA → "Cha". Đối chiếu người nộp với cha/mẹ: số trùng → cùng người. Giấy tờ cũ (giấy
  kết hôn, CMND) ghi CMND 9 số còn tài khoản là số định danh 12 số → hai số KHÁC LOẠI, không đem so; họ tên trùng →
  cùng người, "Có trong hồ sơ: Có".
- Người nộp CHÍNH LÀ người được khai sinh (tự đăng ký cho mình, tờ khai ghi "Chính tôi"/"Bản thân") → "Bản thân".
- Người nộp là người khác (ông, bà, anh, chị, người được ủy quyền...) → "Khác" và ghi rõ ở "Quan hệ cụ thể" theo
  đúng giấy tờ (vd dòng quan hệ trên tờ khai khi người yêu cầu trên tờ khai chính là người nộp). Không giấy nào nói
  người nộp là gì của con → "Quan hệ cụ thể: Không có"; KHÔNG ghi câu giải thích hay "Người nộp hồ sơ" vào dòng này.
- Không đủ thông tin → "Không xác định". Không suy từ họ, tuổi, địa chỉ.

LOẠI KHAI SINH (một trong): Đã xác định được cả cha lẫn mẹ | Chưa xác định được mẹ | Chưa xác định được cha |
Chưa xác định được cả cha lẫn mẹ | Trẻ bị bỏ rơi.
- Có biên bản trẻ bị bỏ rơi → "Trẻ bị bỏ rơi". Giấy tờ ghi đủ họ tên cha và mẹ (kể cả cha/mẹ đã chết) → "Đã xác định
  được cả cha lẫn mẹ". Phần cha để trống / không có thông tin cha → "Chưa xác định được cha" (tương tự với mẹ).

ĐÃ CÓ HỒ SƠ, GIẤY TỜ CÁ NHÂN: "Có" khi người được khai sinh đã có CCCD / giấy tờ cá nhân của chính mình hoặc giấy
cam đoan ghi "đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân"; trẻ sơ sinh có giấy chứng sinh → "Không".

Chỉ trả TEXT theo đúng các khối dưới đây, không markdown/code fence, không JSON. Mỗi nhãn một dòng,
"Căn cứ" tối đa 25 từ:
<nguoi_nop>
Họ tên: ...
Số định danh: ...
Có trong hồ sơ: Có|Không
Vai trong hồ sơ: ...
</nguoi_nop>
<con>
Họ tên: ...
Số định danh: ...
Ngày sinh: ...
Nguồn: ...
</con>
<me>
Họ tên: ...
Số định danh: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
</me>
<cha>
Họ tên: ...
Số định danh: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
</cha>
<quan_he>
Kết luận: Mẹ|Cha|Bản thân|Khác|Không xác định
Quan hệ cụ thể: <TÊN quan hệ ngắn: Ông nội, Bà ngoại, Anh ruột, Người được ủy quyền...>|Không có
Căn cứ: ...
</quan_he>
<loai_khai_sinh>
Kết luận: ...
Đã có hồ sơ, giấy tờ cá nhân: Có|Không
Căn cứ: ...
</loai_khai_sinh>
""".strip()

_TAGS = ("nguoi_nop", "con", "me", "cha", "quan_he", "loai_khai_sinh")


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
        "Tài khoản là MỐC để tính quan hệ, không phải dữ liệu của con/mẹ/cha.",
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


# Mặt trước thẻ: "Số / No.: <12 số>" rồi "Họ và tên / Full name:" (tên cùng dòng hoặc dòng kế) rồi "Giới tính / Sex".
_CARD_NAME_RE = re.compile(r"full name[ \t]*:[ \t]*(?:\n[ \t]*)?([^\n]*)", re.IGNORECASE)
_CARD_NUMBER_RE = re.compile(r"(?<!\d)(\d{12})(?!\d)")
_CARD_SEX_RE = re.compile(r"(?:giới tính|sex)[ \t]*:[ \t]*(nam|nữ)", re.IGNORECASE)
# Có các giấy này thì cha đã có nguồn rõ hơn (tờ khai, giấy kết hôn) hoặc thẻ nam có thể là người làm chứng / đi khai tử.
_FATHER_SOURCE_MARKERS = ("to khai", "ket hon", "lam chung", "khai tu")


def _male_cards(text: str) -> list[tuple[str, str]]:
    """(họ tên, số định danh) của các mặt trước thẻ CCCD / căn cước ghi giới tính Nam."""
    cards = []
    for match in _CARD_NAME_RE.finditer(text):
        name = match.group(1).strip()
        numbers = _CARD_NUMBER_RE.findall(text[max(0, match.start() - 200):match.start()])
        sex = _CARD_SEX_RE.search(text[match.end():match.end() + 250])
        if name and numbers and sex and _fold(sex.group(1)) == "nam" and not _fold(name).startswith("ngay sinh"):
            cards.append((name, numbers[-1]))
    return cards


def _father_from_male_card(blocks: dict, documents: list[dict] | None, options: dict | None) -> dict:
    """Hồ sơ chỉ có giấy chứng sinh + CCCD (không tờ khai, không giấy kết hôn): giấy chứng sinh không có dòng cha nên
    LLM hay kết luận "Chưa xác định được cha" dù có nộp CCCD của cha. Đúng MỘT thẻ nam không phải người nộp / mẹ /
    con, tên không xuất hiện ở giấy khác → đó là cha."""
    if not documents or labeled_value(blocks["cha"], "Họ tên") or not labeled_value(blocks["me"], "Họ tên"):
        return blocks
    co_ho_so = labeled_value(blocks["loai_khai_sinh"], "Đã có hồ sơ, giấy tờ cá nhân")
    if _fold(co_ho_so) == "co":
        return blocks  # người được khai sinh đã có CCCD: thẻ nam có thể là của chính người đó
    texts = [str(document.get("text") or "") for document in documents]
    folded = [_fold(text) for text in texts]
    if any(marker in text for text in folded for marker in _FATHER_SOURCE_MARKERS):
        return blocks
    _, account_id = requester_context(options)
    excluded_ids = {account_id} | {_digits(labeled_value(blocks[tag], "Số định danh")) for tag in ("me", "con")}
    excluded_names = {_fold(labeled_value(blocks[tag], "Họ tên")) for tag in ("me", "con")} - {""}
    candidates: dict[str, str] = {}
    for index, text in enumerate(texts):
        for name, number in _male_cards(text):
            if number in excluded_ids or _fold(name) in excluded_names:
                continue
            if any(_fold(name) in other for other_index, other in enumerate(folded) if other_index != index):
                return blocks  # tên có ở giấy khác (ủy quyền...) → vai không chắc, để nguyên phân vai của LLM
            candidates[number] = name
    if len(candidates) != 1:
        return blocks
    number, name = next(iter(candidates.items()))
    return {
        **blocks,
        "cha": f"Họ tên: {name}\nSố định danh: {number}\nTrạng thái: còn sống\nNguồn: CCCD",
        "loai_khai_sinh": (
            "Kết luận: Đã xác định được cả cha lẫn mẹ\n"
            f"Đã có hồ sơ, giấy tờ cá nhân: {co_ho_so or 'Không'}\n"
            "Căn cứ: hồ sơ không có tờ khai, có CCCD của cha"
        ),
    }


def _render_context(raw: str, options: dict | None, documents: list[dict] | None = None) -> str:
    blocks = {tag: section(raw, tag) for tag in _TAGS}
    if not any(blocks[tag] for tag in ("con", "me", "cha")):
        return ""
    blocks = _father_from_male_card(blocks, documents, options)
    name, number = requester_context(options)
    body = "\n".join(f"<{tag}>\n{value or 'Không xác định'}\n</{tag}>" for tag, value in blocks.items())
    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Kết quả phân vai đã phân tích trước. Dùng làm chuẩn, KHÔNG tự đổi người giữa con / mẹ / cha:\n"
        f"{body}\n"
        f"Tài khoản người nộp: {name or '?'} — {number or '?'}.\n"
        "- Con_* CHỈ thuộc <con>; Me_* CHỈ thuộc <me>; Cha_* CHỈ thuộc <cha>. Khối nào \"Không xác định\" thì bỏ "
        "toàn bộ field của vai đó.\n"
        "- Mỗi người lấy giấy tờ tùy thân của CHÍNH người đó; người đi khai tử, người làm chứng không phải cha/mẹ.\n"
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
    return _render_context(raw, options, documents)
