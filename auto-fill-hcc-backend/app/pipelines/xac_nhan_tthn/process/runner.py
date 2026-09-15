"""Compact agent process pipeline for "Xác nhận tình trạng hôn nhân"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xac_nhan_tthn.process import mapper
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tthn.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _looks_like_person_name(value: str) -> bool:
    words = value.split()
    return 2 <= len(words) <= 7 and not re.search(r"[\d/:<>]", value)


def _card_name_from_ocr(documents: list[dict], card_id: str) -> str:
    """Họ tên IN trên mặt trước thẻ có đúng số định danh ``card_id``.

    Neo theo SỐ trên thẻ ("Số / No.: 0361..."), rồi lấy dòng "Họ và tên / Full name" đứng NGAY SAU số
    đó — một file có thể chứa nhiều thẻ, lấy tên đầu tiên trong file là ghép nhầm người.
    """
    digits = re.sub(r"\D+", "", card_id or "")
    if len(digits) != 12:
        return ""
    for document in documents:
        lines = [line.strip() for line in str(document.get("text") or "").splitlines()]
        anchored = False
        for index, line in enumerate(lines):
            folded = _fold(line)
            if not anchored:
                if ("so / no" in folded or folded.startswith("so:") or "so/no" in folded) and digits in re.sub(r"\D+", "", line):
                    anchored = True
                continue
            if "full name" in folded or folded.startswith("ho va ten"):
                inline = line.split(":", 1)[1].strip() if ":" in line else ""
                candidate = inline or next((nxt for nxt in lines[index + 1:] if nxt), "")
                return candidate if _looks_like_person_name(candidate) else ""
            if "so / no" in folded:   # sang thẻ khác mà chưa thấy tên → thôi
                break
    return ""


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """LLM thỉnh thoảng bỏ sót Cccd_HoTen dù OCR mặt trước thẻ có đủ (vd hồ sơ CCCD + giấy kết hôn,
    OCR mặt sau nằm trước mặt trước). Thiếu tên thì cả mục I lẫn mục II ra trống họ tên → đọc lại
    tên in trên đúng thẻ có số Cccd_SoDinhDanh. Có tên rồi thì không đụng tới.
    """
    if isinstance(raw_fields, dict):
        if raw_fields.get("Cccd_HoTen") or not raw_fields.get("Cccd_SoDinhDanh"):
            return raw_fields
        name = _card_name_from_ocr(documents, str(raw_fields.get("Cccd_SoDinhDanh")))
        return {**raw_fields, "Cccd_HoTen": name} if name else raw_fields
    if isinstance(raw_fields, list):
        by_name = {f.get("name"): f.get("value") for f in raw_fields if isinstance(f, dict)}
        if by_name.get("Cccd_HoTen") or not by_name.get("Cccd_SoDinhDanh"):
            return raw_fields
        name = _card_name_from_ocr(documents, str(by_name.get("Cccd_SoDinhDanh")))
        return [*raw_fields, {"name": "Cccd_HoTen", "value": name}] if name else raw_fields
    return raw_fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"], options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.xac_nhan_tthn.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
