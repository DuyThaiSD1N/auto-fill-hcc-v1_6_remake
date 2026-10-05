"""Chuẩn hoá MỤC ĐÍCH sau bước trích xuất — một lượt LLM nhỏ, chỉ chạy khi đã trích được mục đích.

Mục đích là câu VIẾT TAY dài; OCR hay biến cụm "không có giá trị để đăng ký kết hôn" thành một câu nghe xuôi mà sai
nghĩa, và đọc lệch chữ ở phần việc ("mua bán" → "mua hàng"). Bước trích xuất chép nguyên chữ OCR nên không tự sửa
được. Bước này chỉ nhìn đúng câu đó (kèm dòng mục đích trong OCR) và khôi phục theo từng cụm. Lỗi/timeout/không chắc
→ giữ nguyên câu đã trích.
"""
from __future__ import annotations

import re
import unicodedata

from app.services.llm import client

PROMPT = """Bạn khôi phục câu "Mục đích sử dụng Giấy xác nhận tình trạng hôn nhân" mà người dân VIẾT TAY trên tờ khai
(hoặc dòng "Giấy này được sử dụng để: ..." in trên giấy XNTTHN cũ). Đầu vào: CÂU ĐÃ TRÍCH (bước trích xuất lấy từ OCR)
và DÒNG OCR chứa mục đích. OCR chữ viết tay hay đọc sai; câu đã trích thường lặp lại đúng lỗi của OCR.

<tri_thuc>
- Câu thường gồm: [mở đầu: "(Để) bổ sung (vào) hồ sơ", "Bổ túc hồ sơ", "Để làm (các thủ tục)", "Làm", "Xử lý thủ
  tục", "Dùng để"] + [việc: vay vốn / vay ngân hàng; mua bán, chuyển nhượng, tặng cho, thừa kế nhà đất / quyền sử
  dụng đất / bất động sản; làm giấy tờ đất, đổi sổ đỏ; mua bán, mua, bán, sang tên xe máy / ô tô; thủ tục ngân
  hàng, hành chính; chứng nhận độc thân một giai đoạn; chế độ an sinh, trợ cấp] + có thể có tên người, khoảng ngày,
  nước đến, "(hồ sơ) liên quan đến".
- Người xin giấy ĐỂ đăng ký kết hôn (câu kiểu "Để đăng ký kết hôn với ...") thì KHÔNG có cụm pháp lý dưới đây — tuyệt
  đối không thêm, sẽ lật ngược nghĩa.
- Khoảng 2/3 tờ khai có thêm cụm pháp lý cố định ở cuối, dạng chuẩn "không có giá trị để đăng ký kết hôn" (một số
  người viết "giá trị sử dụng", "khi đăng ký", "đăng kí"). Hay gặp thêm "trước thời kỳ hôn nhân".
- OCR chữ viết tay hay biến cụm pháp lý thành một cụm nghe xuôi mà SAI nghĩa: "không có gia đình…", "giấy tờ để
  đóng kí", "giấy ký kết đồng vay", "quá trình… kết liên", "kể cả", "giai trị", "đang kí". Một đoạn ở cuối câu bắt
  đầu bằng "không có" + chữ giống "giá trị"/"giấy"/"gia" và kết thúc gần "kết hôn" → chính là cụm pháp lý.
  Ở phần việc: "tặng cho" hay bị đọc thành "để"/"tăng cho"; "mua bán" thành "mua hàng"; "bổ sung" thành "sổ"/"bỏ
  sung hộ sổ"/"bố xung"; "chế độ" thành "chỗ để". "trước thời kỳ hôn nhân" hay thành "thời hạn là hôn nhân",
  "thời ký kết hôn", "hoãn nhà".
</tri_thuc>

<cach_lam>
Xét TỪNG CỤM của câu (mở đầu, việc, đối tượng, cụm pháp lý...):
1. Cụm giống một DẠNG HỎNG đã nêu trong <tri_thuc> (kể cả khi nghe xuôi tai) → khôi phục về cụm chuẩn.
2. Cụm có nghĩa, hợp ngữ cảnh → GIỮ NGUYÊN chữ (chỉ sửa chính tả rõ ràng: "Bố Xung" → "bổ sung", "kí" giữ nguyên).
3. Cụm vô nghĩa mà DÒNG OCR đọc khác ở chỗ đó thành chữ có nghĩa → lấy chữ của DÒNG OCR.
4. Bỏ chữ rác chen vào (đoạn lặp, chữ ký, chữ của dòng khác). KHÔNG xoá một cụm có nghĩa, KHÔNG bỏ tên riêng, nước
   đến, số, ngày (kể cả trong ngoặc). Cụm đọc không ra → giữ chữ của câu đã trích và để "do_chac" = "thap".
5. KHÔNG thêm ý hay chữ không có dấu vết trên OCR. Viết đúng chính tả, hoa chữ đầu câu.
</cach_lam>

Trả NGAY một JSON trong code block, không giải thích ngoài JSON:
```json
{"muc_dich": "<câu>", "do_chac": "cao|thap"}
```
"do_chac" = "thap" khi còn cụm không đọc ra chắc."""

_STOP = r"(?=T[ôo]i\s+cam\s+đoan|Làm\s+tại|Người\s+yêu\s+cầu|Giấy\s+này\s+có\s+giá\s+trị|$)"
# Dòng mục đích của TỜ KHAI (lần xin này) và dòng "được sử dụng để" của giấy XNTTHN CŨ (lần xin trước).
_FORM_LINE_RE = re.compile(r"M[ụu]c\s*đ[íi]ch\s*s[ửu]\s*d[ụu]ng[^\n:]*:\s*(?:\(5\))?(.*?)" + _STOP, re.S | re.I)
_OLD_CERT_LINE_RE = re.compile(r"được\s+sử\s+dụng\s+để\s*:?\s*(.*?)" + _STOP, re.S | re.I)


def purpose_line(ocr_text: str) -> str:
    """Dòng mục đích trong OCR — chỉ để làm ĐẦU VÀO cho LLM, không quyết giá trị. Ưu tiên dòng của tờ khai; dòng của
    giấy XNTTHN cũ là mục đích lần xin trước, chỉ dùng khi hồ sơ không có tờ khai."""
    for pattern in (_FORM_LINE_RE, _OLD_CERT_LINE_RE):
        found = [" ".join(m.group(1).split()) for m in pattern.finditer(ocr_text or "")]
        found = [f for f in found if f]
        if found:
            return max(found, key=len)[:400]
    return ""


def _fold(text) -> str:
    text = unicodedata.normalize("NFD", str(text or "")).replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in text if unicodedata.category(c) != "Mn").lower())


def _flips_marriage(old: str, new: str) -> bool:
    """Xin giấy ĐỂ đăng ký kết hôn mà câu mới thêm "không có giá trị ..." → lật ngược nghĩa."""
    o, n = _fold(old), _fold(new)
    return "dangkykethon" in o and "khong" not in o and "khongcogiatri" in n


async def normalize(fields: list[dict], ocr_text: str) -> None:
    """Thay giá trị ô Purpose (tại chỗ) bằng câu đã chuẩn hoá; giữ nguyên khi lỗi, không chắc hay lật nghĩa."""
    row = next((f for f in fields if f.get("name") == "Purpose" and str(f.get("value") or "").strip()), None)
    if row is None:
        return
    old = str(row["value"]).strip()
    user = f"CÂU ĐÃ TRÍCH: {old}\nDÒNG OCR: {purpose_line(ocr_text) or '(không thấy dòng)'}"
    try:
        raw = await client.chat([{"role": "system", "content": PROMPT}, {"role": "user", "content": user}],
                                max_tokens=600, purpose="purpose")
        out = client.extract_json_block(raw)
    except Exception:  # noqa: BLE001 — bước phụ: lỗi LLM không được làm hỏng kết quả trích xuất
        return
    new = str(out.get("muc_dich") or "").strip()
    if not new or out.get("do_chac") == "thap" or _flips_marriage(old, new):
        return
    row["value"] = new
