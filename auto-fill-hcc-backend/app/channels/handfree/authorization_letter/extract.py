"""Đọc căn cước hai bên → danh sách người cho màn "Kiểm tra thông tin" của giấy ủy quyền."""
import logging
import re

from app.channels.handfree.authorization_letter import prompt
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_ui_date
from app.services import ocr
from app.services.llm import client

logger = logging.getLogger(__name__)

# Tên trường trả cho FE — khớp ô ở màn Kiểm tra thông tin.
FIELDS = ("hoTen", "ngaySinh", "soDinhDanh", "ngayCap", "noiCap", "noiThuongTru")
_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
# Một tệp có thể là PDF chứa cả hai mặt thẻ (hoặc giấy của cả hai người) nên để rộng; vẫn cắt để một
# tệp lỗi (OCR ra cả chục trang rác) không đẩy prompt vượt ngữ cảnh.
_MAX_TEXT_PER_FILE = 8000
_MAX_TOKENS = 1500


def _text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _indexes(value, n_files: int) -> list[int]:
    out: list[int] = []
    for item in value if isinstance(value, list) else []:
        try:
            i = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= i < n_files and i not in out:
            out.append(i)
    return out


def normalize_person(raw: dict, n_files: int) -> dict:
    """Chuẩn hoá định dạng + đánh dấu ô cần xem lại. KHÔNG đổi nội dung LLM đọc được."""
    person = {k: _text(raw.get(k)) for k in FIELDS}
    unsure = {str(x) for x in (raw.get("chuaChac") or []) if str(x) in FIELDS}
    for key in ("ngaySinh", "ngayCap"):
        person[key] = normalize_ui_date(person[key]) if person[key] else ""
        if person[key] and not _DATE_RE.match(person[key]):
            unsure.add(key)
    kind = _text(raw.get("loaiGiay")).lower()
    if kind in ("can_cuoc", "cmnd"):
        digits = re.sub(r"\D", "", person["soDinhDanh"])
        # CCCD/căn cước 12 số, CMND 9 hoặc 12 số — lệch là OCR đọc thiếu/thừa.
        if person["soDinhDanh"] and (digits != person["soDinhDanh"].replace(" ", "")
                                     or len(digits) not in ((12,) if kind == "can_cuoc" else (9, 12))):
            unsure.add("soDinhDanh")
        person["soDinhDanh"] = digits or person["soDinhDanh"]
    person["noiCap"] = normalize_issuer(person["noiCap"])
    if not person["noiCap"] and kind == "can_cuoc" and _DATE_RE.match(person["ngayCap"]):
        # Cơ quan cấp căn cước xác định theo LUẬT từ ngày cấp (Bộ Công an từ 01/7/2024, trước đó Cục
        # Cảnh sát QLHC về TTXH) — dùng chung quy tắc với mọi pipeline; vẫn tô vàng để cán bộ nhìn thẻ.
        person["noiCap"] = default_issuer(person["ngayCap"])
        unsure.add("noiCap")
    for key in FIELDS:
        if not person[key]:
            unsure.add(key)
    person["loaiGiay"] = kind or "khac"
    person["tepNguon"] = _indexes(raw.get("tepNguon"), n_files)
    person["chuaChac"] = [k for k in FIELDS if k in unsure]
    return person


def normalize_result(data: dict, n_files: int) -> dict:
    people = [normalize_person(p, n_files) for p in (data.get("people") or []) if isinstance(p, dict)]
    # Người không đọc được gì (LLM trả object rỗng cho tệp rác) không phải một bên của giấy.
    people = [p for p in people if p["hoTen"] or p["soDinhDanh"]]
    used = {i for p in people for i in p["tepNguon"]}
    unused = sorted(set(_indexes(data.get("tepKhongDung"), n_files)) | (set(range(n_files)) - used))
    return {"people": people, "unusedFiles": unused}


async def extract_people(files: list[dict]) -> dict:
    """files: [{name, type, dataUrl}] theo thứ tự tệp trong phiên tải ảnh."""
    if not files:
        return {"people": [], "unusedFiles": [], "ocrFailed": []}
    results = await ocr.ocr_per_file(files)
    texts = [(r.get("text") or "")[:_MAX_TEXT_PER_FILE] if not r.get("error") else "" for r in results]
    failed = [i for i, r in enumerate(results) if r.get("error")]
    if not any(t.strip() for t in texts):
        return {"people": [], "unusedFiles": list(range(len(files))), "ocrFailed": failed}
    messages = [{"role": "system", "content": prompt.SYSTEM},
                {"role": "user", "content": prompt.user_message(texts)}]
    data: dict = {}
    # Thử lại MỘT lần khi LLM trả không phải JSON (thỉnh thoảng gặp): cán bộ đang đứng chờ tại quầy,
    # rơi về "tự nhập tay" vì một lượt trả lời hỏng thì phí cả bước đọc ảnh.
    for attempt in (1, 2):
        raw = await client.chat(messages, max_tokens=_MAX_TOKENS, purpose="giay_uy_quyen.extract")
        try:
            data = client.extract_json_block(raw)
            break
        except ValueError:
            logger.warning("[giay-uy-quyen] LLM không trả JSON (lượt %s, %s tệp): %r",
                           attempt, len(files), (raw or "")[:200])
    out = normalize_result(data if isinstance(data, dict) else {}, len(files))
    out["ocrFailed"] = failed
    return out
