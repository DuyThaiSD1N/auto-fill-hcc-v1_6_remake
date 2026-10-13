"""Bước suy luận trước khi trích field XNTTHN: phân vai (người nộp = tài khoản ↔ người yêu cầu ↔ người được cấp),
quan hệ, và CHUẨN HOÁ MỤC ĐÍCH sử dụng.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ tính SO VỚI TÀI KHOẢN. Mục đích là câu viết tay
OCR hay đọc lệch → khôi phục ngay ở bước này để lượt trích không phải chép lại chữ hỏng. Agent chỉ trả text có thẻ;
không trả JSON.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 1400

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN (XNTTHN). Đọc TOÀN BỘ tài liệu. Không trích field
biểu mẫu, không trả JSON. Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): có mặt trong hồ sơ không, vai gì.
2. NGƯỜI YÊU CẦU ghi ở khối ĐẦU tờ khai (trước câu "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân...").
3. NGƯỜI ĐƯỢC CẤP = người cần giấy XNTTHN.
4. QUAN HỆ của NGƯỜI NỘP với NGƯỜI ĐƯỢC CẤP.
5. MỤC ĐÍCH sử dụng giấy, đã khôi phục câu chữ.

XÁC ĐỊNH NGƯỜI ĐƯỢC CẤP (theo thứ tự):
a. Tờ khai: người có tên SAU câu "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây".
b. Không có tờ khai mà có GIẤY ỦY QUYỀN: BÊN ỦY QUYỀN (người cần giấy) là người được cấp; bên được ủy quyền là người
   đi nộp hộ.
c. Không có cả hai: người đứng tên trên giấy XNTTHN cũ / thẻ CCCD duy nhất của hồ sơ.
Vợ/chồng (đã chết, đã ly hôn hay hiện tại), người làm chứng, cán bộ ký không phải người được cấp.

QUAN HỆ (người nộp là gì CỦA người được cấp):
- Người nộp chính là người được cấp (trùng số định danh; thiếu số thì họ tên lệch tối đa một ký tự do OCR) → "Bản thân".
- Người nộp CHÍNH LÀ người yêu cầu trên tờ khai (đối chiếu với <requester_context>) → lấy dòng "Quan hệ với người được
  cấp..." của tờ khai; dòng ghi "Tự khai", "Bản thân", "Chính mình" → "Bản thân".
- Dòng quan hệ trên tờ khai là quan hệ của NGƯỜI YÊU CẦU ghi trên tờ khai, KHÔNG phải của người nộp. Người nộp KHÁC người
  yêu cầu (vd cán bộ / người khác nộp hộ bằng tài khoản của mình, "Có trong hồ sơ: Không") → TUYỆT ĐỐI không dùng dòng
  đó; không có giấy tờ nào nói người nộp là gì của người được cấp → "Không xác định".
- Người nộp là bên được ủy quyền → "Người được ủy quyền".
- Giấy tờ khác ghi rõ quan hệ → quan hệ đó (vd "Con", "Mẹ").
- Không có căn cứ → "Không xác định". Không suy từ họ, tuổi, địa chỉ.

MỤC ĐÍCH — đọc dòng "Mục đích sử dụng Giấy xác nhận tình trạng hôn nhân" của tờ khai (không có tờ khai thì dòng "Giấy
này được sử dụng để: ..." của giấy XNTTHN cũ). Hồ sơ không có dòng nào như vậy → "Loại: không xác định", "Nội dung:
Không có"; TUYỆT ĐỐI không tự đặt mục đích. Câu VIẾT TAY, OCR hay đọc sai:
- Câu thường gồm: [mở đầu: "(Để) bổ sung (vào) hồ sơ", "Bổ túc hồ sơ", "Để làm (các thủ tục)", "Dùng để"] + [việc:
  vay vốn / vay ngân hàng; mua bán, chuyển nhượng, tặng cho, thừa kế nhà đất / quyền sử dụng đất; làm giấy tờ đất;
  mua bán, sang tên xe; thủ tục ngân hàng, hành chính; chế độ an sinh, trợ cấp] + có thể có tên người, khoảng ngày,
  nước đến.
- Khoảng 2/3 tờ khai có thêm cụm pháp lý ở cuối, dạng chuẩn "không có giá trị để đăng ký kết hôn" (một số người viết
  "giá trị sử dụng", "khi đăng ký"). OCR hay biến cụm này thành chữ nghe xuôi mà SAI nghĩa ("không có gia đình…",
  "giấy tờ để đóng kí", "giai trị"): đoạn cuối câu bắt đầu bằng "không có" + chữ giống "giá trị"/"giấy"/"gia" và kết
  thúc gần "kết hôn" → chính là cụm pháp lý. Người xin giấy ĐỂ đăng ký kết hôn thì KHÔNG có cụm này — tuyệt đối
  không thêm, sẽ lật ngược nghĩa.
- Phần việc hay đọc lệch: "tặng cho" thành "tăng cho"; "mua bán" thành "mua hàng"; "bổ sung" thành "bố xung"/"bỏ
  sung"; "chế độ" thành "chỗ để"; "trước thời kỳ hôn nhân" thành "thời hạn là hôn nhân".
- Khôi phục TỪNG CỤM: cụm giống dạng hỏng đã nêu → về cụm chuẩn; cụm có nghĩa → giữ nguyên chữ (chỉ sửa chính tả rõ
  ràng); bỏ chữ rác chen vào. KHÔNG xoá cụm có nghĩa, KHÔNG bỏ tên riêng, nước đến, số, ngày; KHÔNG thêm ý không có
  dấu vết trên OCR. Viết đúng chính tả, hoa chữ đầu câu. GIỮ TRỌN câu, kể cả cụm "không có giá trị ...".
- Loại (dòng "Nơi đăng ký kết hôn ở nước ngoài" ghi "không nêu" → Loại BẮT BUỘC là "khac"):
  "ket_hon_co_quan_dai_dien" = câu NÊU RÕ đăng ký kết hôn tại Cơ quan đại diện Việt Nam ở nước ngoài (đại sứ
  quán, lãnh sự quán Việt Nam); "ket_hon_nuoc_ngoai" = câu NÊU RÕ đăng ký kết hôn tại cơ quan có thẩm quyền CỦA NƯỚC
  NGOÀI / ở một nước ngoài; "khac" = mọi trường hợp còn lại, kể cả đăng ký kết hôn tại Việt Nam, câu không nêu nơi
  đăng ký, hay việc khác có nhắc chữ "kết hôn". Vd "Vay vốn ngân hàng để đăng ký kết hôn" → "khac" (việc là vay vốn,
  không nêu nơi đăng ký ở nước ngoài); "Để đăng ký kết hôn với công dân Hàn Quốc tại Hàn Quốc" →
  "ket_hon_nuoc_ngoai"; "Để đăng ký kết hôn tại Đại sứ quán Việt Nam tại Nhật Bản" → "ket_hon_co_quan_dai_dien".

Chỉ trả TEXT theo đúng các khối dưới đây, không markdown/code fence, không JSON. Mỗi nhãn một dòng, "Căn cứ" tối đa
25 từ:
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
<nguoi_duoc_cap>
Họ tên: ...
Số định danh: ...
Ngày sinh: ...
Nguồn: ...
Căn cứ phân vai: ...
</nguoi_duoc_cap>
<quan_he>
Kết luận: Bản thân|<quan hệ cụ thể>|Không xác định
Căn cứ: ...
</quan_he>
<muc_dich>
Nội dung: <câu mục đích đã khôi phục>|Không có
Nơi đăng ký kết hôn ở nước ngoài nêu trong câu: <tên nước / cơ quan đại diện ở nước ngoài>|không nêu
Loại: khac|ket_hon_nuoc_ngoai|ket_hon_co_quan_dai_dien|không xác định
Độ chắc: cao|thap
</muc_dich>
""".strip()

_TAGS = ("nguoi_nop", "nguoi_yeu_cau", "nguoi_duoc_cap", "quan_he", "muc_dich")


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
    blocks = {tag: section(raw, tag) for tag in _TAGS}
    if not blocks["nguoi_duoc_cap"]:
        return ""
    name, number = requester_context(options)
    body = "\n".join(f"<{tag}>\n{value or 'Không xác định'}\n</{tag}>" for tag, value in blocks.items())
    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Kết quả phân vai đã phân tích trước. Dùng làm chuẩn, KHÔNG tự đổi người:\n"
        f"{body}\n"
        f"Tài khoản người nộp: {name or '?'} — {number or '?'}.\n"
        "- NguoiDuocCap_* CHỈ thuộc <nguoi_duoc_cap>; không lấy của người nộp hộ, vợ/chồng, người làm chứng.\n"
        "- NguoiYeuCau_* chép từ khối người yêu cầu của tờ khai (chỉ để đối chiếu với tài khoản).\n"
        "- Mục đích đã chuẩn hoá ở <muc_dich> — không trích lại.\n"
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
