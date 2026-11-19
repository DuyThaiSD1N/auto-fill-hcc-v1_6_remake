"""Compact agent pipeline cho thủ tục 1.001194 (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.prompt import EXTRA_RULES
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def photo_fields(files: list[dict], texts: dict[int, str]) -> tuple[list[dict], list[str]]:
    """Hai ô tải ảnh đầu trang (JPEG dưới 2 MB, comp ``bca-photo``): ảnh chân dung 4x6 ``filename46`` (luật chung hộ
    chiếu 1.001456 — tệp ảnh gần như không chữ) + ảnh trang nhân thân hộ chiếu ``filenamehc`` (trang có MRZ, luật của
    thẻ tạm trú 1.003460 — cùng cổng, cùng hai ô). → (ô, câu báo); câu báo của ô không gắn được do mapper.enrich nhắc."""
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import mapper as ho_chieu_mapper
    from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach.dinh_kem_khong_tach import (
        planner as tam_tru_attach,
    )
    from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import ocr_pages

    photo, notes = ho_chieu_mapper.portrait_field(files, texts)
    passport_page, passport_note = tam_tru_attach.passport_page_field(
        files, {i: ocr_pages(t) for i, t in texts.items() if (t or "").strip()})
    if not photo:
        notes = [n for n in notes if n != ho_chieu_mapper.PORTRAIT_WARNING]
    if passport_note:
        notes = [*notes, passport_note]
    return [f for f in (photo, passport_page) if f], notes


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.services import ocr

    files = runner.flatten(files_by_role)
    # Giữ chữ OCR theo TỪNG tệp (runner chung chỉ trả bản gộp) để nhận ra ảnh chân dung / trang hộ chiếu.
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
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    # User 19/11/2026: ảnh chân dung tự gắn như hộ chiếu / thẻ tạm trú (cổng bắt buộc ô ảnh đầu trang).
    texts = {index: text_by_file.get(id(file), "") for index, file in enumerate(files)}
    photos, notes = photo_fields(files, texts)
    if photos:
        names = {f["name"] for f in photos}
        res["fields"] = [*photos, *res["fields"]]
        # Gắn được cả hai ô thì bỏ câu "2 ô ảnh tải tay"; còn thiếu ô nào thì nhắc đúng ô đó.
        if names >= {"filename46", "filenamehc"}:
            keep = None
        elif "filename46" in names:
            keep = mapper.PASSPORT_PAGE_WARNING
        else:
            keep = mapper.PHOTO_ONLY_WARNING
        warnings = [w for w in (keep if w == mapper.PHOTO_WARNING else w for w in warnings) if w]
    warnings = [*notes, *warnings]
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
