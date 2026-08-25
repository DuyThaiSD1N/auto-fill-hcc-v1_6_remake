"""Compact agent pipeline for "Cấp bản sao trích lục Giấy khai sinh"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Nhóm field mô tả MỘT NGƯỜI đọc từ THẺ trong hồ sơ → (prefix, mỏ neo họ tên, mỏ neo số).
_CARD_GROUPS = (
    ("Nyc_", "Nyc_HoTen", "Nyc_SoDinhDanh"),
    ("ChuThe_", "ChuThe_HoTen", "ChuThe_SoDinhDanh"),
)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _requester_hint(options: dict) -> str:
    """Mỏ neo người yêu cầu cổng đã điền sẵn (VNeID) → giúp LLM chọn ĐÚNG CCCD người yêu cầu
    khi upload nhiều CCCD (vd mẹ đi làm bản sao khai sinh cho con: có cả CCCD mẹ lẫn con)."""
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'NGƯỜI YÊU CẦU đã đăng nhập (cổng điền sẵn từ VNeID): họ tên="{name}", số định danh="{idnum}".\n'
        "Đây CHỈ là MỎ NEO để CHỌN xem thẻ nào trong hồ sơ là của người yêu cầu.\n"
        "TUYỆT ĐỐI KHÔNG dùng tên/số định danh này (hoặc bịa ngày sinh, ngày cấp, nơi cư trú cho\n"
        "người này) làm GIÁ TRỊ của bất kỳ field nào. Mọi giá trị PHẢI đọc được trong tài liệu.\n"
        "Không có thẻ nào trong hồ sơ trùng mỏ neo → KHÔNG trả Nyc_* theo mỏ neo; vẫn trả thẻ\n"
        "đọc được vào đúng nhóm của nó (thẻ của người được đăng ký → ChuThe_*, còn lại → Nyc_*),\n"
        "không được bỏ mất thẻ có thật trong hồ sơ.\n"
        "Nếu hồ sơ có đúng 2 CCCD khác nhau và 1 thẻ đã khớp mỏ neo, CCCD còn lại BẮT BUỘC đưa vào\n"
        "ChuThe_*; không bỏ mất thông tin thẻ thứ hai.\n"
        "</requester_context>"
    )


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Loại nhóm thẻ mà hồ sơ KHÔNG hề có người đó — chốt chứng cứ sau LLM.

    LLM chỉ đọc TEXT OCR, nên mọi giá trị phải truy được về tài liệu. Lỗi thật đã gặp:
    hồ sơ chỉ có CCCD người cha + giấy khai sinh của con, nhưng LLM chép NGƯỜI ĐANG ĐĂNG
    NHẬP ở <requester_context> vào Nyc_* rồi bịa thêm ngày sinh/ngày cấp/nơi cư trú của
    người đó — khối "người yêu cầu" trên cổng bị ghi đè bằng dữ liệu không có trong hồ sơ.

    Neo theo họ tên HOẶC số định danh: chỉ cần một trong hai xuất hiện trong OCR là giữ
    (thẻ mờ, OCR rớt một mỏ neo vẫn dùng được). Không có mỏ neo nào để đối chiếu thì
    KHÔNG loại — thà giữ hơn xóa nhầm dữ liệu đọc được thật.
    """
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields

    def value_of(name):
        if isinstance(raw_fields, dict):
            return raw_fields.get(name)
        for field in raw_fields:
            if isinstance(field, dict) and field.get("name") == name:
                return field.get("value")
        return None

    ocr_text = "\n".join(str(document.get("text") or "") for document in documents)
    ocr_folded = _fold(ocr_text)
    ocr_digits = _digits(ocr_text)  # gộp mọi chữ số để số định danh có dấu cách vẫn khớp

    dropped: set[str] = set()
    for prefix, name_field, id_field in _CARD_GROUPS:
        name = _fold(value_of(name_field))
        idnum = _digits(value_of(id_field))
        if not name and not idnum:
            continue
        if (idnum and idnum in ocr_digits) or (name and name in ocr_folded):
            continue
        dropped.add(prefix)

    if not dropped:
        return raw_fields

    def is_dropped(name) -> bool:
        return any(str(name or "").startswith(prefix) for prefix in dropped)

    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if not is_dropped(name)}
    return [
        field for field in raw_fields
        if not isinstance(field, dict) or not is_dropped(field.get("name"))
    ]


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
        compact_field_fallback=_compact_field_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"], options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.trich_luc.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
