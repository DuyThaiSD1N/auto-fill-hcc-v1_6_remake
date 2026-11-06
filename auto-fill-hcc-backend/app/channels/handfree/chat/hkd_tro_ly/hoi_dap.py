"""Hiểu câu trả lời của công dân (một lượt LLM), rồi kiểm dạng từng giá trị trước khi ghi.

LLM nhận cả danh sách mục nên một câu nói ghi được nhiều mục cùng lúc, sửa được mục đã trả lời trước đó. Kiểm dạng là
tất định: số điện thoại / số định danh sai độ dài thì không ghi mà hỏi lại kèm số đã nghe; ngày phải là ngày thật;
địa chỉ ghi từng phần (tỉnh, xã, số nhà) nghe được.
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from app.channels.handfree.chat.field_review.agent import _valid_date, spoken_digits
from app.channels.handfree.chat.hkd_tro_ly import hoi_dap_prompt as prompt
from app.channels.handfree.chat.intents import fold
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

ACTIONS = {"tra_loi", "bo_qua", "tam_dung", "nhac_lai", "dong_y", "khong_ro"}
# Dạng giá trị trong prompt cho từng loại mục.
_KIND_FORMAT = {
    "text": "chu", "email": "chu", "address": "diachi", "phone": "so", "id12": "so", "money": "tien",
    "date": "ngay", "int": "nguyen", "yesno": "coKhong", "gender": "gioiTinh", "chu_the": "chuThe",
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
# Model đôi khi ghi câu có/không bằng chữ (vd "giong" cho câu "có giống … không") → quy về true/false.
_YES = {"true", "co", "dung", "phai", "giong", "yes"}
_NO = {"false", "khong", "khong phai", "khac", "no"}


@dataclass
class Parsed:
    action: str
    values: dict = field(default_factory=dict)        # mục → giá trị đã chuẩn hoá
    bad_digits: dict = field(default_factory=dict)    # mục → dãy số nghe được nhưng sai độ dài
    nganh_text: str = ""


def _phone_ok(digits: str) -> bool:
    return (len(digits) == 10 and digits.startswith("0")) or (len(digits) == 11 and digits.startswith("02"))


def _fold_char(c: str) -> str:
    return unicodedata.normalize("NFD", c.replace("đ", "d").replace("Đ", "D"))[0].lower()


def _with_accents(part: str, text: str) -> str:
    """Model hay trả phần địa chỉ KHÔNG DẤU ("so 10 duong mau") hoặc viết thường hết ("liên chiểu") → lấy lại đúng đoạn
    đó trong lời công dân (gấp từng ký tự nên vị trí khớp 1-1). Chỉ chép lại chữ công dân đã nói, không đoán."""
    if not part or not (part.isascii() or part == part.lower()) or not text or text.isascii():
        return part
    source = re.sub(r"\s+", " ", text)
    i = "".join(_fold_char(c) for c in source).find("".join(_fold_char(c) for c in part))
    return source[i:i + len(part)] if i >= 0 else part


def _clean_address(value, allow_same: bool, text: str = ""):
    if allow_same and isinstance(value, str) and value.strip().lower().startswith("giong"):
        return "giong"
    if not isinstance(value, dict):
        return None
    # llm/client.py đổi khoá "chiTietDuoiXa" của model về "diaChi" (quy ước code/mapper) — nhận cả hai.
    value = {**value, "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa")}
    out = {k: _with_accents(re.sub(r"\s+", " ", str(value.get(k) or "")).strip()[:300], text)
           for k in ("tinh", "xa", "diaChi")}
    if not any(out.values()):
        return None  # hỏi lần lượt tỉnh → xã → số nhà: một phần cũng ghi, phần còn thiếu hỏi tiếp
    out["quocGia"] = "Việt Nam"
    return out


def check(kind: str, raw, text: str, asking: bool, allow_same: bool = False):
    """Giá trị LLM trả cho một mục → (giá trị chuẩn | None, dãy số sai độ dài | "")."""
    if kind in ("phone", "id12"):
        heard = re.sub(r"\D", "", str(raw or ""))
        # Công dân đọc từng chữ số cho đúng mục đang hỏi → chép tất định (model nhỏ hay rơi/đảo chữ số).
        spoken = spoken_digits(text) if asking else ""
        ok = _phone_ok if kind == "phone" else (lambda d: len(d) == 12)
        for digits in (spoken, heard):
            if digits and ok(digits):
                return digits, ""
        return None, (spoken or heard)
    if kind == "email":
        value = re.sub(r"\s+", "", str(raw or "")).lower()
        return (value if _EMAIL.match(value) else None), ""
    if kind == "address":
        return _clean_address(raw, allow_same, text), ""
    if kind == "money":
        digits = re.sub(r"\D", "", str(raw or ""))
        return (int(digits) if digits and int(digits) > 0 else None), ""
    if kind == "int":
        digits = re.sub(r"\D", "", str(raw or ""))
        return (int(digits) if digits and int(digits) < 100000 else None), ""
    if kind == "date":
        value = _valid_date(str(raw or ""))
        if value and int(value[-4:]) > date.today().year + 2:
            return None, ""
        return (value or None), ""
    if kind == "yesno":
        if isinstance(raw, bool):
            return raw, ""
        word = fold(str(raw or ""))
        return (True if word in _YES else False if word in _NO else None), ""
    if kind == "gender":
        value = str(raw or "").strip()
        return (value if value in ("Nam", "Nữ") else None), ""
    if kind == "chu_the":
        value = str(raw or "").strip()
        return (value if value in ("ca_nhan", "ho_gia_dinh") else None), ""
    value = re.sub(r"\s+", " ", str(raw or "")).strip()[:200]
    return (value or None), ""


def _value_text(value) -> str:
    if value in (None, "", {}):
        return "(chưa có)"
    if isinstance(value, dict):
        return ", ".join(v for v in (value.get("diaChi"), value.get("xa"), value.get("tinh")) if v)
    return str(value)


async def interpret(text: str, asking: str, question: str, slots: list[dict], values: dict,
                    location: str) -> Parsed:
    """slots: [{key, label, kind, same?}] các mục đang mở để ghi; values: giá trị hiện có theo mục."""
    lines = []
    for s in slots:
        same = " (cho phép \"giống\")" if s.get("same") else ""
        lines.append(f"- {s['key']} — {s['label']} — {_KIND_FORMAT.get(s['kind'], 'chu')}{same} — "
                     f"{_value_text(values.get(s['key']))}")
    system = prompt.SYSTEM.format(today=date.today().strftime("%d/%m/%Y"), location=location or "(không rõ)",
                                  asking=asking, question=question, slots="\n".join(lines))
    try:
        raw = await llm_chat([{"role": "system", "content": system},
                              {"role": "user", "content": prompt.USER.format(text=str(text or "")[:600])}],
                             temperature=0.0, max_tokens=400, purpose="hkd_hoi_dap")
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001 — LLM best-effort, vòng hỏi phải sống tiếp
        logger.warning("[hkd_hoi_dap] LLM lỗi: %s", e)
        return Parsed("khong_ro")
    if not isinstance(data, dict):
        return Parsed("khong_ro")
    action = str(data.get("hanhDong") or "")
    out = Parsed(action if action in ACTIONS else "khong_ro",
                 nganh_text=re.sub(r"\s+", " ", str(data.get("nganhMoTa") or "")).strip()[:600])
    kinds = {s["key"]: s for s in slots}
    given = data.get("giaTri") if isinstance(data.get("giaTri"), dict) else {}
    if kinds.get(asking, {}).get("kind") == "address" and asking not in given:
        # Câu trả lời ngắn cho một phần địa chỉ ("Tân An") model hay ghi {"xa": …} ngay ở giaTri, quên bọc trong mã mục.
        loose = {k: given.pop(k) for k in ("tinh", "xa", "diaChi", "chiTietDuoiXa") if k in given}
        if loose:
            given[asking] = loose
    for key, raw_value in given.items():
        spec = kinds.get(key)
        if not spec:
            continue
        if raw_value in (False, "", None) and spec["kind"] != "yesno" and key == asking:
            # Model ghi "không có" thành false / chuỗi rỗng cho mục đang hỏi → công dân không có thông tin này.
            out.action = "bo_qua"
            continue
        value, bad = check(spec["kind"], raw_value, text, key == asking, bool(spec.get("same")))
        if value is not None:
            out.values[key] = value
        elif bad:
            out.bad_digits[key] = bad
    if out.values and out.action in ("khong_ro", "nhac_lai"):
        out.action = "tra_loi"
    return out


async def pick(text: str, question: str, options: list[str]) -> tuple[int | None, bool]:
    """Công dân chọn một dòng trong danh sách đang hiện (vd ngành chính) → (chỉ số 0.., muốn đổi danh sách)."""
    system = prompt.PICK_SYSTEM.format(question=question,
                                       options="\n".join(f"{i} — {o}" for i, o in enumerate(options, 1)))
    try:
        raw = await llm_chat([{"role": "system", "content": system},
                              {"role": "user", "content": prompt.USER.format(text=str(text or "")[:600])}],
                             temperature=0.0, max_tokens=80, purpose="hkd_chon")
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001 — LLM best-effort, hỏi lại
        logger.warning("[hkd_hoi_dap] LLM chọn lỗi: %s", e)
        return None, False
    if not isinstance(data, dict):
        return None, False
    choice = data.get("chon")
    index = choice - 1 if isinstance(choice, int) and 1 <= choice <= len(options) else None
    return index, data.get("doiDanhSach") is True
