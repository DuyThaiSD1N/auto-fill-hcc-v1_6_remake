"""Đính kèm Xác nhận thông tin về cư trú — chế độ TÁCH giấy tờ theo cài đặt của extension.

Hồ sơ hay dồn nhiều giấy vào một PDF (tờ khai + giấy kết hôn; CCCD hai người một tệp). LLM đọc theo TRANG trong MỘT
lượt, chia thành từng giấy; mỗi giấy thành một mục có `sourceSegments` (extension cắt đúng trang) đặt vào đúng dòng
của bảng (bảng phẳng, chỉ dòng Tờ khai hiện sẵn — xem chế độ không tách). Cơ chế chia trang dùng chung với Điều chỉnh
thông tin về cư trú / Tách hộ (cùng trang cổng); chỉ prompt và bảng dòng là riêng. Giấy không phải tờ khai (chỗ ở hợp
pháp, hợp đồng, giấy kết hôn, CCCD, ủy quyền, giấy chưa rõ loại) → dòng "+" mang tên giấy, thẻ của hai người là hai
dòng. OCR / LLM lỗi → quay về chế độ không tách.
"""

import time

from app.pipelines._shared.identity_merge import ho_ten_co_dau, mat_the, so_dinh_danh_the
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_tach import planner as _dieu_chinh
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_khong_tach.planner import (
    _document_name,
    _llm_document_name,
    both_sides,
    pair_card_sides,
)
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import _BLANK, _OCR_TYPES, _segments
from app.pipelines.tach_ho.attach.dinh_kem_khong_tach.planner import finalize_rows
from app.process.schemas import FileItem

from ..dinh_kem_khong_tach.planner import (
    DOC_TYPES,
    OTHER,
    ROWS,
    missing_warnings,
    new_row_item,
    ocr_pages,
    plan_item,
)
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    """Chia trang một lượt bằng cơ chế của Điều chỉnh thông tin cư trú (vá JSON, đánh dấu trang đầu giấy, xác nhận ranh
    giới mâu thuẫn) với prompt của thủ tục này."""
    return await _dieu_chinh._segment_all(pages_by_file, SYSTEM_PROMPT, build_user_prompt)


def _kind(doc: dict) -> str:
    kind = str(doc.get("docType") or "").strip()
    if kind == _BLANK:
        return ""
    return kind if kind in DOC_TYPES else OTHER


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            pages_by_file[index] = ocr_pages(str(result["text"]))

    started = time.monotonic()
    try:
        if not pages_by_file:
            raise RuntimeError("OCR không đọc được tệp nào")
        documents = await _segment_all(pages_by_file)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    names = [str(f.get("name") or f"file-{i + 1}") for i, f in enumerate(raw_files)]
    segments = _segments(pages_by_file, documents)
    covered = {s["fileIndex"] for s in segments}
    segments += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(names)) if i not in covered]
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))
    parts_of_file = {i: sum(1 for s in segments if s["fileIndex"] == i) for i in range(len(names))}

    # Số định danh đọc từ OCR của từng đoạn: khoá ghép hai mặt thẻ (họ tên LLM đọc có thể lệch giữa hai mặt).
    for s in segments:
        pages = pages_by_file.get(s["fileIndex"], [])
        text = "\n".join(pages if s["pages"] is None else [pages[i] for i in s["pages"] if i < len(pages)])
        s["doc"] = {**s["doc"], "_soThe": so_dinh_danh_the(text), "_matTheOcr": mat_the(text),
                    "chuThe": ho_ten_co_dau(s["doc"].get("chuThe") or "", text)}

    attachments: list[dict] = []
    unknown: list[str] = []
    seen: dict[str, int] = {}
    # Hai mặt thẻ của CÙNG một người (dù khác trang, khác tệp) luôn gộp thành MỘT giấy.
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        kind = _kind(doc) or OTHER
        document_name = _document_name(name, _llm_document_name(doc) if doc else "")
        # Hai giấy cùng tên (thẻ căn cước của hai người) → đánh số: mỗi giấy một dòng "+" riêng, cán bộ phân biệt.
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        if kind in ROWS:
            item = plan_item(file_index, name, document_name, kind)
        else:
            if kind == OTHER:
                unknown.append(document_name)
            item = new_row_item(file_index, name, document_name, kind)
        # Nhóm phủ đúng mọi phần của MỘT tệp → đính nguyên tệp, không dựng lại PDF.
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        if not whole:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        attachments.append(item)

    finalize_rows(attachments)
    errors.extend(missing_warnings(attachments))
    if unknown:
        errors.append("Giấy tờ chưa rõ loại đã đính vào dòng \"+\" (giấy tờ khác): " + ", ".join(unknown))
    return {
        "attachments": attachments,
        "extracted": {
            "documents": names,
            "segments": [
                {"fileName": item["fileName"], "documentName": item["documentName"], "row": item["detectedType"],
                 "pages": [[s["fileIndex"], [p + 1 for p in s["pageIndexes"] or []] or "cả tệp"]
                           for s in item.get("sourceSegments") or []] or "cả tệp"}
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
