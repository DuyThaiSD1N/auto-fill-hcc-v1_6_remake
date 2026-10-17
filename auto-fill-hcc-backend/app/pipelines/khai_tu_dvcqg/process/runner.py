"""Pipeline đăng ký khai tử (Cổng DVC quốc gia mới): phân vai → trích → mapper."""

import re

from app.pipelines._shared.compact_agent import runner

from . import mapper, reason
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

# Khối người mất trên tờ khai bắt đầu sau câu "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây".
_TO_KHAI_NGUOI_MAT = re.compile(r"đề\s*nghị\s+cơ\s+quan\s+đăng\s+ký\s+khai\s+tử", re.IGNORECASE)
# "Giới tính: (2) Nam Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam" — dân tộc thường chung dòng với giới tính.
_DAN_TOC = re.compile(r"dân\s*tộc\s*[:：]\s*(?:\(\d+\)\s*)?(.+?)(?=\s+quốc\s*tịch|\s+nơi\s|\s*\(\d+\)|\n|$)",
                      re.IGNORECASE)


def _dan_toc_to_khai(documents: list[dict]) -> str:
    """Dân tộc ghi trong khối người mất của tờ khai; không thấy tờ khai thì rỗng."""
    for doc in documents or []:
        text = str(doc.get("text") or "")
        anchor = _TO_KHAI_NGUOI_MAT.search(text)
        if not anchor:
            continue
        # Chỉ xét vài dòng đầu khối người mất, tránh lấy nhầm dòng của giấy khác ghép sau.
        block = "\n".join(text[anchor.end():].splitlines()[:8])
        found = _DAN_TOC.search(block)
        value = found.group(1).strip(" .,:;-") if found else ""
        if value and not re.fullmatch(r"[.…\s]*", value):
            return value
    return ""


# Ngày chết đủ ngày/tháng/năm. Tờ khai in sẵn "ngày ...30... tháng 5.... năm 1989" (dấu chấm điền chỗ
# trống), văn bản xác minh "chết ngày 30 tháng 5 năm 1989", phiếu ghi tay "Mất : 30 - 05 - 1989".
_DOT = r"[\s.…_]*"
_NGAY_CHET = (
    re.compile(rf"(?:chết|tử\s*vong|mất)[^\n]{{0,40}}?ngày{_DOT}(\d{{1,2}}){_DOT}tháng{_DOT}(\d{{1,2}}){_DOT}"
               rf"năm{_DOT}(\d{{4}})(?!\d)", re.IGNORECASE),
    re.compile(r"(?:chết|tử\s*vong|mất)\s*(?:ngày\s*)?[:：]?\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})(?!\d)",
               re.IGNORECASE),
)


def _ngay_chet_day_du(documents: list[dict], year: str) -> str:
    """Ngày chết dd/mm/yyyy cùng năm LLM đã đọc; các giấy ghi lệch nhau thì bỏ, không đoán."""
    found = set()
    for doc in documents or []:
        for pattern in _NGAY_CHET:
            for match in pattern.finditer(str(doc.get("text") or "")):
                day, month, y = int(match.group(1)), int(match.group(2)), match.group(3)
                if y == year and 1 <= day <= 31 and 1 <= month <= 12:
                    found.add(f"{day:02d}/{month:02d}/{y}")
    return found.pop() if len(found) == 1 else ""


def _get(raw_fields, name: str):
    if isinstance(raw_fields, dict):
        return raw_fields.get(name)
    for f in raw_fields:
        if isinstance(f, dict) and f.get("name") == name and f.get("value"):
            return f.get("value")
    return None


def _set(raw_fields, name: str, value) -> None:
    if isinstance(raw_fields, dict):
        raw_fields[name] = value
        return
    for f in raw_fields:
        if isinstance(f, dict) and f.get("name") == name:
            f["value"] = value
            return
    raw_fields.append({"name": name, "value": value})


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Bù tất định các ô LLM hay đọc thiếu trên tờ khai.

    - Dân tộc nằm giữa dòng giới tính / quốc tịch → LLM hay bỏ sót.
    - Ngày chết: LLM hay chỉ trả năm khi tờ khai điền ngày/tháng giữa dấu chấm, hoặc khi văn bản
      xác minh chỉ ghi "chết năm 1989" → tìm ngày đủ cùng năm trên các giấy.
    """
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields
    if not _get(raw_fields, "NguoiMat_DanToc"):
        value = _dan_toc_to_khai(documents)
        if value:
            _set(raw_fields, "NguoiMat_DanToc", value)
    # Chỉ nâng "yyyy" / "mm/yyyy" lên ngày đủ khi khớp năm (và tháng nếu LLM đã có tháng).
    partial = re.fullmatch(r"(?:(\d{1,2})[/\-.])?(\d{4})", str(_get(raw_fields, "NguoiMat_NgayMat") or "").strip())
    if partial:
        full = _ngay_chet_day_du(documents, partial.group(2))
        if full and (not partial.group(1) or int(partial.group(1)) == int(full[3:5])):
            _set(raw_fields, "NguoiMat_NgayMat", full)
    return raw_fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
        options=options,
        context_builder=reason.build_context,
    )
    enrich_options = {**(options or {}), "_reasoning_context": result.get("reasoning_context") or ""}
    result["fields"], warnings = mapper.enrich(result["fields"], enrich_options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
