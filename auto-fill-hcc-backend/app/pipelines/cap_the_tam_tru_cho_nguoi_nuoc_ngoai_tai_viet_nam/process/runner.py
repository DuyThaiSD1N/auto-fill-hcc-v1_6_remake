"""Compact agent pipeline cho thủ tục 1.003460 (Cổng DVC Bộ Công an).

Ngoài các ô tờ khai, pipeline điền còn ghi ô "Ghi chú" (cùng trang, dưới bảng Thành phần hồ sơ — ảnh ánh xạ mục 6): tệp
hồ sơ gộp nhiều giấy thì ghi rõ trang nào là giấy gì, để cán bộ tiếp nhận biết. Loại giấy từng trang đọc bằng chính luật
tiêu đề của bước đính kèm (attach/dinh_kem_khong_tach/planner.page_types) trên chữ OCR runner chung trả về.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach.dinh_kem_khong_tach import planner as attach
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.prompt import EXTRA_RULES
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

_HEADER_RE = re.compile(r"^===== (.+?) =====\n", re.MULTILINE)


def _ocr_by_file(ocr_text: str, names: list[str]) -> dict[str, str]:
    """Tách chữ OCR gộp của runner chung (``===== <tên> (<nhà OCR>) =====`` + chữ, ngăn bằng ---) về từng tệp."""
    marks = list(_HEADER_RE.finditer(ocr_text or ""))
    out: dict[str, str] = {}
    for k, mark in enumerate(marks):
        header = mark.group(1)
        name = next((n for n in names if header == n or header.startswith(f"{n} (")), None)
        if name is None:
            continue
        end = marks[k + 1].start() if k + 1 < len(marks) else len(ocr_text)
        out[name] = re.sub(r"\n+---\s*$", "", ocr_text[mark.end():end].strip()).strip()
    return out


def _label(kind: str, values: dict) -> str:
    if kind == attach.VAN_BAN:
        loai = (values.get("VanBan_Loai") or "").strip().upper().replace(" ", "")
        so = (values.get("VanBan_So") or "").strip()
        return "Văn bản đề nghị" + (f" {loai}" if loai in ("NA6", "NA7") else "") + (f" số {so}" if so else "")
    if kind == attach.CHUNG_MINH:
        so = (values.get("GPLD_So") or "").strip()
        return f"Giấy phép lao động số {so}" if so else "Giấy tờ chứng minh thuộc diện cấp thẻ"
    return {
        attach.BIA: "Danh mục thành phần hồ sơ",
        attach.TO_KHAI: "Tờ khai NA8",
        attach.HO_CHIEU: "Hộ chiếu (nhân thân, thị thực, dấu nhập cảnh)",
        attach.IDENTITY: "Thẻ căn cước",
    }.get(kind, "Giấy tờ khác")


def ghi_chu(ocr_text: str, names: list[str], values: dict) -> str | None:
    """"Hồ sơ gồm 01 file PDF (6 trang): <tên>. Tr.1: Danh mục …; Tr.2: Văn bản đề nghị NA6 số …; Tr.3–4: Tờ khai NA8; …"
    — chỉ cho tệp gộp từ hai loại giấy trở lên (tệp một giấy thì tên dòng đính kèm đã đủ rõ)."""
    lines = []
    for name, text in _ocr_by_file(ocr_text, names).items():
        kinds = attach.page_types(text)
        if len([k for k in dict.fromkeys(kinds) if k in attach.SUBSTANTIVE]) < 2:
            continue
        groups: list[list] = []  # [kind, trang đầu, trang cuối] (đếm từ 1)
        for page, kind in enumerate(kinds, 1):
            if kind == attach.BLANK:
                continue
            if groups and groups[-1][0] == kind and groups[-1][2] == page - 1:
                groups[-1][2] = page
            else:
                groups.append([kind, page, page])
        parts = [f"Tr.{a}" + (f"–{b}" if b > a else "") + f": {_label(kind, values)}" for kind, a, b in groups]
        lines.append(f"Hồ sơ gồm 01 file PDF ({len(kinds)} trang): {name}. " + "; ".join(parts) + ".")
    return " ".join(lines) or None


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=mapper.ocr_fallback,
        options=options,
    )
    names = [str(f.get("name") or "") for files in (files_by_role or {}).values() for f in files or []]
    values = {f["name"]: f.get("value") for f in res.get("fields") or [] if isinstance(f, dict) and f.get("name")}
    note = ghi_chu(str(res.get("ocr_text") or ""), [n for n in names if n], values)
    res["fields"], warnings = mapper.enrich(res["fields"], options, ghi_chu=note)
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
