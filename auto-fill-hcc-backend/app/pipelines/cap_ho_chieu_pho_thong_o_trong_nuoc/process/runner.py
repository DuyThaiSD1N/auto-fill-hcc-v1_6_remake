"""Compact agent pipeline cho thủ tục 1.001456 (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import mapper
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.prompt import EXTRA_RULES
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.services import ocr

    files = runner.flatten(files_by_role)
    # Giữ chữ OCR theo TỪNG tệp (runner chung chỉ trả bản gộp) để nhận ra ảnh chân dung: ảnh gần như không có chữ.
    text_by_file: dict[int, str] = {}

    async def _ocr(ocr_files: list[dict]) -> list[dict]:
        results = await ocr.ocr_per_file(ocr_files)
        for file, result in zip(ocr_files, results):
            text_by_file[id(file)] = str(result.get("text") or "")
        return results

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=mapper.ocr_fallback,
        options=options,
        ocr_fn=_ocr,
    )
    raw_fields = res["fields"]
    res["fields"], warnings = mapper.enrich(raw_fields, options)
    # Giấy tờ của người khác chủ tài khoản VNeID → không điền; `blocked` để Auto Fill / trợ lý hiện câu báo dễ hiểu thay
    # cho thông báo chung "không đọc được giấy tờ".
    blocked = mapper.account_block(mapper._by_name(raw_fields), options) if mapper.has_account_anchor(options) else None
    if blocked:
        res["blocked"] = blocked
    else:
        # Ảnh chân dung 4x6 (ô tải ảnh đầu trang, cổng bắt buộc): tệp ảnh trong bộ giấy → JPEG, phát đầu danh sách.
        texts = {index: text_by_file.get(id(file), "") for index, file in enumerate(files)}
        photo, notes = mapper.portrait_field(files, texts)
        warnings = [w for w in warnings if w != mapper.PORTRAIT_WARNING]
        if photo:
            res["fields"] = [photo, *res["fields"]]
        warnings = [*notes, *warnings]
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
