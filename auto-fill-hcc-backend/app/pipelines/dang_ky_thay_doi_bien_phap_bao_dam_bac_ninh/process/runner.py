"""Compact agent pipeline cho "[Tỉnh Bắc Ninh] Đăng ký thay đổi biện pháp bảo đảm" (1.011442).

TÁCH theo purpose (chọn TRƯỚC khi gọi LLM để mỗi lượt gọn, không lẫn người):
- "registration_form" (mặc định): thân Phiếu 02a.
- "authorized_person": bên ủy quyền → khối doiTuongKhac*; trả kèm ``authorizedSubject`` (loại "Người ủy quyền là:").
Hồ sơ hay là một PDF scan vài chục trang → OCR song song theo phần (``attach.phan_trang.ocr_files``) cho kịp timeout
100 s của extension.
"""

from app.pipelines._shared.compact_agent import runner

from ..attach.phan_trang import ocr_files
from . import mapper
from .prompt import EXTRA_RULES, RULES_UYQUYEN
from .schema import (
    ALIASES,
    ALLOWED,
    ALLOWED_UYQUYEN,
    COMPACT_COMP_BY_NAME,
    COMPACT_COMP_UYQUYEN,
    FIELDS,
    FIELDS_UYQUYEN,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    if str((options or {}).get("purpose") or "registration_form") == "authorized_person":
        res = await runner.run(
            files_by_role,
            fields=FIELDS_UYQUYEN,
            allowed=ALLOWED_UYQUYEN,
            comp_by_name=COMPACT_COMP_UYQUYEN,
            aliases=ALIASES,
            extra_rules=RULES_UYQUYEN,
            options=options,
            ocr_fn=ocr_files,
        )
        raw = res.get("fields") or []
        res["fields"], warnings = mapper.enrich_authorized(raw)
        res["authorizedSubject"] = mapper.authorized_subject(raw)
        if warnings:
            res.setdefault("errors", []).extend(warnings)
        return res

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=mapper.apply_ocr_fallback,
        options=options,
        max_tokens=3200,
        ocr_fn=ocr_files,
    )
    res["fields"] = mapper.enrich(res.get("fields") or [], options)
    return res
