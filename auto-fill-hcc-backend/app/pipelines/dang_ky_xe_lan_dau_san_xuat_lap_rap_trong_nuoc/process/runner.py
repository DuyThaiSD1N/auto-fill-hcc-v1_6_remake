"""Compact agent pipeline cho thủ tục 1.012575 (Cổng DVC Bộ Công an).

Ba ô tải ảnh đầu trang kê khai (user 24/11/2026, ảnh trang thật): "Ảnh phương tiện (*)", "Ảnh chứng từ nguồn gốc mặt
trước (*)", "Ảnh chứng từ nguồn gốc mặt sau (*)" (.jpg / .png dưới 2 MB) — cùng khuôn với xe nhập khẩu 1.013066
(``dang_ky_xe_lan_dau_nhap_khau.process.runner``: comp ``bca-photo``, ``match`` theo chữ trên ô). Khác ở chứng từ nguồn
gốc: xe sản xuất, lắp ráp trong nước là Phiếu kiểm tra chất lượng xuất xưởng (mặt trước = trang có tiêu đề phiếu, mặt
sau = trang thông số kỹ thuật / trang liền sau trong cùng tệp). Auto Fill gắn ở lượt điền lẫn lượt "Đính kèm"
(attach/planner.py); trợ lý chỉ gắn ở nút "Đính kèm giấy tờ" (``options.pagePhotosAtAttach``).
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import runner as xe_runner
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process import mapper
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

ORIGIN_LABEL = "Phiếu kiểm tra chất lượng xuất xưởng"
_PHIEU_RE = re.compile(r"kiem tra chat luong xuat xuong")
# Giấy khai ĐKX10 / hóa đơn / LPTB có thể nhắc "số seri phiếu kiểm tra chất lượng xuất xưởng" ở giữa trang; trang phiếu
# thì in tiêu đề ở đầu.
_TITLE_HEAD = 400
# Mặt sau phiếu: bảng thông số kỹ thuật, không lặp tiêu đề.
_SPEC_HINTS = ("thong so ky thuat", "khoi luong ban than", "kich thuoc", "chieu dai co so", "khoang sang gam",
               "vet banh", "co lop", "cong suat lon nhat", "ty so nen", "dung tich xi lanh")


def phieu_xuat_xuong_page(page: str) -> bool:
    """Trang của Phiếu kiểm tra chất lượng xuất xưởng (mặt trước có tiêu đề, mặt sau là bảng thông số kỹ thuật)."""
    text = fold(page)
    if xe_runner._OTHER_DOC_RE.search(text[:_TITLE_HEAD]):
        return False
    if _PHIEU_RE.search(text[:_TITLE_HEAD]):
        return True
    if xe_runner._OTHER_DOC_RE.search(text):
        return False
    return bool(_PHIEU_RE.search(text)) or sum(h in text for h in _SPEC_HINTS) >= 3


def photo_fields(files: list[dict], texts: dict[int, str]) -> tuple[list[dict], list[str]]:
    return xe_runner.photo_fields(files, texts, is_origin=phieu_xuat_xuong_page, origin=ORIGIN_LABEL)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.services import ocr

    files = runner.flatten(files_by_role)
    # Giữ chữ OCR theo TỪNG tệp (runner chung chỉ trả bản gộp) để nhận ra ảnh xe / trang phiếu xuất xưởng.
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
        options=options,
        ocr_fn=_ocr,
    )
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    photos, notes = ([], []) if options.get("pagePhotosAtAttach") else photo_fields(
        files, {i: text_by_file.get(id(f), "") for i, f in enumerate(files)})
    res["fields"] = [*photos, *res["fields"]]
    warnings = [*notes, *(mapper.TRA_CUU_NO_PHOTO_WARNING if w == mapper.TRA_CUU_WARNING else w for w in warnings)]
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
