"""Bước riêng chuẩn hoá MỤC ĐÍCH (chạy song song agent rà soát): ghép v1 + dòng mục đích của 2 bản OCR.

Tách khỏi agent rà soát vì mục đích là câu viết tay dài, hai bản OCR thường hỏng ở chỗ KHÁC nhau; một lượt gọi
chỉ nhìn đúng dòng này sửa theo từng cụm ổn định hơn khi lẫn trong prompt rà mọi field.
"""
from __future__ import annotations

import re

from app.services import ocr_qwen
from app.services.llm import client as llm_client

PROMPT = """Bạn khôi phục câu "Mục đích sử dụng Giấy xác nhận tình trạng hôn nhân" mà người dân VIẾT TAY trên tờ khai
(hoặc dòng "Giấy này được sử dụng để: ..." in trên giấy XNTTHN cũ). Đầu vào: BẢN V1 (bước trích xuất đã lấy, từ
OCR 1) và dòng mục đích do HAI OCR độc lập đọc. Cả hai OCR đều có thể đọc sai, thường sai ở chỗ KHÁC nhau.

<tri_thuc>
- Câu thường gồm: [mở đầu: "(Để) bổ sung (vào) hồ sơ", "Bổ túc hồ sơ", "Để làm (các thủ tục)", "Làm", "Xử lý thủ
  tục", "Dùng để"] + [việc: vay vốn / vay ngân hàng; mua bán, chuyển nhượng, tặng cho, thừa kế nhà đất / quyền sử
  dụng đất / bất động sản; làm giấy tờ đất, đổi sổ đỏ; mua bán, mua, bán, sang tên xe máy / ô tô; thủ tục ngân
  hàng, hành chính; chứng nhận độc thân một giai đoạn] + có thể có tên người, khoảng ngày, "(hồ sơ) liên quan đến".
- Người xin giấy ĐỂ đăng ký kết hôn (câu kiểu "Để đăng ký kết hôn với ...") thì KHÔNG có cụm pháp lý dưới đây — tuyệt
  đối không thêm, sẽ lật ngược nghĩa.
- Khoảng 2/3 tờ khai có thêm cụm pháp lý cố định ở cuối, dạng chuẩn "không có giá trị để đăng ký kết hôn" (một số
  người viết "giá trị sử dụng", "khi đăng ký", "đăng kí"). Hay gặp thêm "trước thời kỳ hôn nhân".
- OCR chữ viết tay hay biến cụm pháp lý thành một cụm nghe xuôi mà SAI nghĩa: "không có gia đình…", "giấy tờ để
  đóng kí", "giấy ký kết đồng vay", "quá trình… kết liên", "kể cả", "giai trị", "đang kí". Một đoạn ở cuối câu bắt
  đầu bằng "không có" + chữ giống "giá trị"/"giấy"/"gia" và kết thúc gần "kết hôn" → chính là cụm pháp lý.
  Ở phần việc: "tặng cho" hay bị đọc thành "để"/"tăng cho"; "mua bán" thành "mua hàng"; "bổ sung" thành "sổ"/"bỏ
  sung hộ sổ".
  "trước thời kỳ hôn nhân" hay thành "thời hạn là hôn nhân", "thời ký kết hôn", "hoãn nhà".
</tri_thuc>

<cach_lam>
Xét TỪNG CỤM của câu (mở đầu, việc, cụm pháp lý...):
0. Cụm của V1 giống một DẠNG HỎNG đã nêu trong <tri_thuc> (vd "không có gia đình ... kết hôn") → COI LÀ HỎNG dù
   nghe xuôi tai, khôi phục về cụm chuẩn; chữ thừa dính sau cụm pháp lý (vd "với ai", "tại ...") là chữ rác.
1. Cụm của V1 có nghĩa, hợp ngữ cảnh → GIỮ NGUYÊN chữ của V1, kể cả khi OCR 2 đọc thành một cụm khác cũng có
   nghĩa (hai cách đọc đều xuôi thì không có căn cứ đổi).
2. Cụm của V1 vô nghĩa / sai ngữ cảnh / là dạng hỏng của cụm pháp lý → thay bằng cách đọc của OCR kia nếu cách đó
   có nghĩa; hai OCR đều hỏng → khôi phục theo <tri_thuc> khi chắc.
3. Bỏ chữ rác chen vào (đoạn lặp, chữ ký, chữ của dòng khác). KHÔNG xoá cả một cụm chỉ vì đọc không ra: cụm pháp
   lý hỏng → khôi phục về dạng chuẩn (không bỏ); cụm việc/đối tượng không đọc ra → giữ chữ của V1 và để "do_chac"
   = "thap".
4. KHÔNG thêm ý hay chữ mà cả hai OCR đều không có dấu vết. Giữ tên riêng, số, ngày như OCR. Viết đúng chính tả,
   hoa chữ đầu câu.
</cach_lam>

Trả NGAY một JSON trong code block, không giải thích ngoài JSON:
```json
{"muc_dich": "<câu>", "da_sua": ["<cụm cũ> → <cụm mới>"], "do_chac": "cao|thap"}
```
"do_chac" = "thap" khi còn cụm không đọc ra chắc."""

# Biến thể THỬ: Qwen là nguồn chính, Vintern chỉ bù khi Qwen thiếu dòng.
PROMPT_QWEN = PROMPT.split("<cach_lam>")[0] + """<cach_lam>
OCR 2 (Qwen) là NGUỒN CHÍNH: lấy câu của OCR 2 làm gốc và GIỮ chữ của nó.
1. Chỉ sửa những chữ của OCR 2 vô nghĩa / sai ngữ cảnh / là dạng hỏng của cụm pháp lý → khôi phục theo <tri_thuc>,
   hoặc theo chữ tương ứng của OCR 1 nếu chữ đó có nghĩa.
2. OCR 2 thiếu dòng / thiếu cụm / không thấy dòng mục đích → bù bằng OCR 1 (hoặc BẢN V1).
3. Bỏ chữ rác chen vào. KHÔNG thêm ý hay chữ mà cả hai OCR đều không có dấu vết. Giữ tên riêng, số, ngày. Viết
   đúng chính tả, hoa chữ đầu câu.
</cach_lam>

Trả NGAY một JSON trong code block, không giải thích ngoài JSON:
```json
{"muc_dich": "<câu>", "da_sua": ["<cụm cũ> → <cụm mới>"], "do_chac": "cao|thap"}
```"""

_STOP = r"(?=T[ôo]i\s+cam\s+đoan|Làm\s+tại|Người\s+yêu\s+cầu|Giấy\s+này\s+có\s+giá\s+trị|$)"
# Dòng mục đích của TỜ KHAI (lần xin này) và dòng "được sử dụng để" của giấy XNTTHN CŨ (lần xin trước).
_FORM_LINE_RE = re.compile(r"M[ụu]c\s*đ[íi]ch\s*s[ửu]\s*d[ụu]ng[^\n:]*:\s*(?:\(5\))?(.*?)" + _STOP, re.S | re.I)
_OLD_CERT_LINE_RE = re.compile(r"được\s+sử\s+dụng\s+để\s*:?\s*(.*?)" + _STOP, re.S | re.I)


def purpose_line(text: str) -> str:
    """Dòng mục đích trong một bản OCR (chọn đầu vào cho LLM, không quyết giá trị).

    Ưu tiên dòng của tờ khai; dòng "được sử dụng để" của giấy XNTTHN cũ chỉ dùng khi hồ sơ không có tờ khai —
    đó là mục đích của lần xin trước, có thể khác lần này.
    """
    for pattern in (_FORM_LINE_RE, _OLD_CERT_LINE_RE):
        found = [" ".join(m.group(1).split()) for m in pattern.finditer(text or "")]
        found = [f for f in found if f]
        if found:
            return max(found, key=len)[:400]
    return ""


async def chuan_hoa(v1_purpose: str, vintern_text: str, qwen_text: str, mode: str = "gop",
                    ocr2_line: str | None = None) -> dict | None:
    """→ {muc_dich, da_sua, do_chac, ms} hoặc None khi hồ sơ không có dòng mục đích.

    ``ocr2_line``: bản đọc thứ hai đã có sẵn câu mục đích (Qwen trích xuất thẳng từ ảnh) → dùng thay cho việc tìm
    dòng trong OCR toàn văn."""
    line1 = purpose_line(vintern_text)
    line2 = ocr2_line if ocr2_line is not None else purpose_line(qwen_text)
    if not (v1_purpose or line1 or line2):
        return None
    user = (f"BẢN V1: {v1_purpose or '(trống)'}\nOCR 1 (Vintern): {line1 or '(không thấy dòng)'}\n"
            f"OCR 2 (Qwen): {line2 or '(không thấy dòng)'}")
    system = PROMPT_QWEN if mode == "qwen" else PROMPT
    resp = await ocr_qwen.chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                               max_tokens=600, timeout_s=120)
    try:
        out = llm_client.extract_json_block(resp["content"])
    except Exception:  # noqa: BLE001
        out = {"muc_dich": None, "_raw": resp["content"][:500]}
    return {**out, "ocr1": line1, "ocr2": line2, "ms": resp["ms"]}
