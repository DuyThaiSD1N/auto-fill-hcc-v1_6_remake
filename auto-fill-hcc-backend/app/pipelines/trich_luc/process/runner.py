"""Compact agent pipeline for "Cấp bản sao trích lục Giấy khai sinh"."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


_CIVIL_STATUS_TITLE = re.compile(
    r"\b(?:GIẤY\s+KHAI\s+SINH|KHAI\s+SANH|GIẤY\s+CHỨNG\s+NHẬN\s+KẾT\s+HÔN|"
    r"TRÍCH\s+LỤC\s+(?:KHAI\s+SINH|KẾT\s+HÔN|KHAI\s+TỬ))\b",
    flags=re.IGNORECASE,
)
_HEADER_NUMBER = re.compile(
    r"^\s*Số\s*:\s*([A-Z0-9][A-Z0-9./-]{0,80})\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def _fields_dict(raw_fields) -> dict:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            item.get("name"): item.get("value")
            for item in raw_fields
            if isinstance(item, dict) and item.get("name")
        }
    return {}


def _header_document_number(documents: list[dict]) -> str:
    """Lấy dòng Số ở ngay trước tiêu đề giấy hộ tịch, không quét sang số CCCD trong tài liệu khác."""
    for document in documents:
        text = str(document.get("text") or "")
        for title in _CIVIL_STATUS_TITLE.finditer(text):
            prefix = text[max(0, title.start() - 500):title.start()]
            matches = list(_HEADER_NUMBER.finditer(prefix))
            if matches:
                return matches[-1].group(1).strip()
    return ""


def _compact_field_fallback(raw_fields, documents: list[dict]):
    fields = _fields_dict(raw_fields)
    if not fields.get("HoTich_So"):
        number = _header_document_number(documents)
        if number:
            fields["HoTich_So"] = number
    return fields or raw_fields


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
        "Nyc_* CHỈ lấy từ CCCD TRÙNG tên hoặc số định danh này. Nếu hồ sơ có đúng 2 CCCD khác nhau,\n"
        "CCCD còn lại BẮT BUỘC đưa vào ChuThe_*; không bỏ mất thông tin thẻ thứ hai.\n"
        "</requester_context>"
    )


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
