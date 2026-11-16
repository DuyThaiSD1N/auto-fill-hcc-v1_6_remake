"""Bước phân vai trước khi trích field khai tử: người nộp (tài khoản) ↔ người yêu cầu (tờ khai) ↔ người mất.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ tính SO VỚI TÀI KHOẢN. Agent chỉ trả text
có thẻ để ghim vai cho lượt trích; không trả JSON.
"""

import re
import unicodedata

from app.config import settings
from app.pipelines._shared.cccd import id_birth_year
from app.services.llm import client

_REASON_MAX_TOKENS = 1000

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ ĐĂNG KÝ KHAI TỬ. Đọc TOÀN BỘ tài liệu. Không trích field biểu mẫu, không trả JSON.
Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): có mặt trong hồ sơ không, với
   vai gì.
2. NGƯỜI YÊU CẦU ghi trên tờ khai (nếu có tờ khai).
3. NGƯỜI MẤT = người được đăng ký khai tử.
4. QUAN HỆ của NGƯỜI NỘP với NGƯỜI MẤT, LOẠI ĐĂNG KÝ và GIẤY BÁO TỬ / GIẤY TỜ THAY THẾ.

XÁC ĐỊNH VAI:
a. TỜ KHAI ĐĂNG KÝ KHAI TỬ: người ở khối TRÊN câu "Đề nghị cơ quan đăng ký khai tử..." là NGƯỜI YÊU CẦU; người
   SAU câu đó là NGƯỜI MẤT.
b. GIẤY BÁO TỬ / trích lục khai tử / biên bản xác minh / công văn "đăng ký khai tử cho ông/bà <HỌ TÊN>" → người
   được ghi là người chết.
c. Chỉ có đúng 2 CCCD/CMND (không tờ khai, không giấy báo tử) và không thẻ nào khớp tài khoản → người SINH TRƯỚC
   (năm sinh NHỎ HƠN, già hơn) là NGƯỜI MẤT, người sinh sau là người yêu cầu. Hồ sơ không có giấy khai tử vẫn áp luật
   này, không trả "không có".
d. Người đi khai tử trên trích lục, người ký, người nhận công văn, chủ hộ không phải người mất.
e. Chủ tài khoản là người đang đăng nhập để nộp hồ sơ, còn sống: KHÔNG BAO GIỜ ghi chủ tài khoản vào <nguoi_mat>. Hồ sơ
   chỉ có thẻ của chủ tài khoản và một thẻ của người khác (không giấy khai tử) → người mang thẻ kia là người mất.

QUAN HỆ (người nộp là gì CỦA người mất) — ghi VAI CỦA NGƯỜI NỘP, không ghi vai của người mất: giấy ghi "ông nội tôi
là ...", "bố đẻ tôi là ..." → người nộp là "Cháu nội", "Con đẻ" (không ghi "Ông nội", "Bố"); "con gái tôi là ..." →
người nộp là "Mẹ" / "Cha".
- Người nộp chính là người yêu cầu trên tờ khai (trùng số định danh; thiếu số thì trùng họ tên) → lấy đúng dòng
  "Quan hệ với người đã chết" của tờ khai.
- Giấy tờ khác ghi rõ quan hệ (giấy khai sinh của người nộp ghi người mất là cha/mẹ, giấy kết hôn vợ/chồng...) →
  quan hệ đó.
- Không có giấy tờ chứng minh → "Không xác định". Không suy từ họ, tuổi, địa chỉ hay việc là người đi khai tử.

LOẠI ĐĂNG KÝ (một trong): Đăng ký đúng hạn | Đăng ký quá hạn | Đăng ký khai tử cho người chết đã lâu |
không xác định.
- Tờ khai ghi rõ "Loại đăng ký" → theo tờ khai.
- Không có giấy báo tử mà có biên bản xác minh / bản cam đoan / công văn về người chết lâu năm → "Đăng ký khai tử
  cho người chết đã lâu".
- Còn lại → "không xác định" (Python tính theo ngày chết).

GIẤY BÁO TỬ: "Giấy báo tử" khi có chính tài liệu tiêu đề GIẤY BÁO TỬ; "Giấy tờ thay thế" khi chỉ có trích lục khai
tử / biên bản xác minh / văn bản xác nhận việc chết; không có → "Không có". TRÍCH LỤC KHAI TỬ không phải giấy báo tử.

Chỉ trả TEXT theo đúng các khối dưới đây, không markdown/code fence, không JSON. Mỗi nhãn một dòng,
"Căn cứ" tối đa 25 từ:
<nguoi_nop>
Họ tên: ...
Số định danh: ...
Có trong hồ sơ: Có|Không
Vai trong hồ sơ: ...
</nguoi_nop>
<nguoi_yeu_cau>
Họ tên: ...
Số định danh: ...
Quan hệ ghi trên tờ khai: ...
</nguoi_yeu_cau>
<nguoi_mat>
Họ tên: ...
Số định danh: ...
Ngày sinh: ...
Nguồn: ...
Căn cứ phân vai: ...
</nguoi_mat>
<quan_he>
Kết luận: ...
Căn cứ: ...
</quan_he>
<loai_dang_ky>
Kết luận: ...
Giấy báo tử: Giấy báo tử|Giấy tờ thay thế|Không có
Căn cứ: ...
</loai_dang_ky>
""".strip()

_TAGS = ("nguoi_nop", "nguoi_yeu_cau", "nguoi_mat", "quan_he", "loai_dang_ky")


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
        "Tài khoản là MỐC để tính quan hệ, không phải dữ liệu của người mất.",
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


# Có giấy khai tử thì không áp luật hai thẻ; có giấy khai sinh thì số định danh trên giấy đó (trẻ nhỏ) không phải thẻ.
_NOT_TWO_CARDS = ("to khai dang ky khai tu", "giay bao tu", "trich luc khai tu", "giay khai sinh", "trich luc khai sinh")


def _two_card_choice(documents: list[dict], options: dict | None) -> tuple[str, str] | None:
    """Luật c của prompt: hồ sơ không có giấy khai tử / giấy khai sinh, chỉ có đúng hai số thẻ 12 chữ số → thẻ không
    phải của tài khoản, hoặc (không thẻ nào của tài khoản) thẻ của người sinh trước là người mất.
    Trả (số định danh người mất, khối <nguoi_mat>)."""
    text = "\n".join(str(document.get("text") or "") for document in documents or [])
    if any(marker in _fold(text) for marker in _NOT_TWO_CARDS):
        return None
    numbers = sorted(set(re.findall(r"(?<!\d)0\d{11}(?!\d)", text)))
    if len(numbers) != 2:
        return None
    _, account = requester_context(options)
    if account in numbers:
        number = next(n for n in numbers if n != account)
    else:
        years = {n: id_birth_year(n) for n in numbers}
        if None in years.values() or len(set(years.values())) == 1:
            return None
        number = min(numbers, key=lambda n: years[n])
    return number, "\n".join([
        f"Họ tên: người mang thẻ số {number}",
        f"Số định danh: {number}",
        f"Năm sinh: {id_birth_year(number) or ''}",
        "Nguồn: CCCD",
        "Căn cứ phân vai: hồ sơ không có giấy khai tử, chỉ có hai thẻ — thẻ không phải của tài khoản / người sinh trước",
    ])


_TWO_CARD_BASIS = ("2 cccd", "hai cccd", "2 the", "hai the", "2 cmnd", "luat c")


def _render_context(raw: str, options: dict | None, documents: list[dict] | None = None) -> str:
    blocks = {tag: section(raw, tag) for tag in _TAGS}
    agent = blocks["nguoi_mat"]
    choice = _two_card_choice(documents or [], options)
    if choice:
        chosen = _digits(labeled_value(agent, "Số định danh"))
        undecided = not labeled_value(agent, "Họ tên") and not chosen
        # Agent tự viện dẫn luật hai thẻ của prompt mà chốt người sinh sau (tự mâu thuẫn): theo đúng luật agent đã dẫn.
        # Agent chốt vì căn cứ khác thì giữ.
        inverted = bool(chosen) and chosen != choice[0] and any(basis in _fold(agent) for basis in _TWO_CARD_BASIS)
        # Người đang đăng nhập nộp hồ sơ không thể là người mất (luật e).
        _, account = requester_context(options)
        is_account = bool(account) and chosen == account
        if undecided or inverted or is_account:
            blocks["nguoi_mat"] = choice[1]
            # Khối người yêu cầu của agent đang ghi chính người mất → bỏ, để lượt trích không lấy nhầm.
            if _digits(labeled_value(blocks["nguoi_yeu_cau"], "Số định danh")) == choice[0]:
                blocks["nguoi_yeu_cau"] = ""
    elif _digits(labeled_value(agent, "Số định danh")) and _digits(labeled_value(agent, "Số định danh")) == requester_context(
            options)[1]:
        # Agent ghi chủ tài khoản (người đang nộp) vào khối người mất: sai chắc chắn → bỏ người đó, giữ các khối khác.
        blocks["nguoi_mat"] = ("Họ tên: chưa xác định — KHÔNG phải chủ tài khoản (người nộp); người mất là người KHÁC được "
                               "giấy tờ ghi là đã chết hoặc được đề nghị đăng ký khai tử")
    if not blocks["nguoi_mat"]:
        return ""
    name, number = requester_context(options)
    body = "\n".join(f"<{tag}>\n{value or 'Không xác định'}\n</{tag}>" for tag, value in blocks.items())
    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Kết quả phân vai đã phân tích trước. Dùng làm chuẩn, KHÔNG tự đổi người:\n"
        f"{body}\n"
        f"Tài khoản người nộp: {name or '?'} — {number or '?'}.\n"
        "- NguoiMat_* CHỈ thuộc <nguoi_mat>; không lấy của người yêu cầu, người đi khai tử, người ký.\n"
        "- NguoiYeuCau_* chép từ khối người yêu cầu của tờ khai (chỉ để đối chiếu với tài khoản).\n"
        "- Gbt_* theo <loai_dang_ky>: \"Không có\" thì bỏ toàn bộ Gbt_*.\n"
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
