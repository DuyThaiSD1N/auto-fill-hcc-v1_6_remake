"""Compact agent pipeline cho thủ tục 1.115557 (Lai Châu).

Hồ sơ mẫu nộp HAI bản giống hệt nhau của cùng một file scan chung 12 trang (một bản cho dòng Đơn, một bản cho dòng
Giấy chứng nhận ở bước đính kèm). Bước điền chỉ cần đọc một lần: OCR theo tệp KHÁC nhau rồi trả lại đúng thứ tự, và gạn
tài liệu trùng chữ trước khi gửi LLM (đỡ nhân đôi prompt, LLM không thấy hai bộ giấy mà tưởng hai người).
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process import mapper
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def ocr_unique(files: list[dict]) -> list[dict]:
    """OCR mỗi nội dung một lần; tệp trùng ``dataUrl`` nhận lại kết quả của bản đầu (đổi tên theo tệp của nó)."""
    from app.services import ocr

    first_index: dict[str, int] = {}
    unique: list[dict] = []
    owner: list[int] = []
    for item in files:
        key = str(item.get("dataUrl") or "")
        if not key or key not in first_index:
            if key:
                first_index[key] = len(unique)
            owner.append(len(unique))
            unique.append(item)
        else:
            owner.append(first_index[key])
    results = await ocr.ocr_per_file(unique) if unique else []
    return [{**results[slot], "name": item.get("name"), "type": item.get("type")} for item, slot in zip(files, owner)]


def drop_duplicate_documents(documents: list[dict]) -> list[dict]:
    """Bỏ tài liệu có chữ OCR trùng hệt một tài liệu trước (cùng file nộp hai lần)."""
    seen: set[str] = set()
    kept: list[dict] = []
    for document in documents:
        key = " ".join(str(document.get("text") or "").split())
        if key and key in seen:
            continue
        seen.add(key)
        kept.append(document)
    return kept


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        document_filter=drop_duplicate_documents,
        ocr_fn=ocr_unique,
    )
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
