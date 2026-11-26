"""Đính kèm Xóa đăng ký tạm trú — chế độ TÁCH giấy tờ theo cài đặt của extension.

Hồ sơ hay dồn nhiều giấy vào một PDF (tờ khai + biên bản thanh lý hợp đồng thuê + CCCD). LLM đọc theo TRANG trong MỘT
lượt, chia thành từng giấy; mỗi giấy thành một mục có `sourceSegments` (extension cắt đúng trang) đặt vào đúng dòng
của bảng (bảng ở chế độ không tách). Cơ chế chia trang dùng chung với Điều chỉnh thông tin về cư trú / Tách hộ; chỉ
prompt và bảng dòng là riêng. Giấy có loại rõ mà bảng không có dòng → dòng "+ Thêm mới" mang tên giấy; giấy chưa rõ
loại → dòng Tờ khai + cảnh báo. OCR / LLM lỗi → quay về chế độ không tách. Bảng theo Trường hợp (trường hợp vắng mặt /
đã đăng ký thường trú chỉ có dòng Tờ khai) và Ghi chú dòng Tờ khai dùng chung hàm của chế độ không tách.
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
from app.process.schemas import FileItem

from ..dinh_kem_khong_tach.planner import (
    CHO_O,
    LEFTOVER_ROW,
    NEW_ROW_TYPES,
    ROWS,
    TO_KHAI,
    finalize_rows,
    new_row_item,
    ocr_pages,
    plan_item,
    table_has_no_home_row,
    to_khai_note,
)
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    """Chia trang một lượt bằng cơ chế của Điều chỉnh thông tin cư trú (vá JSON, đánh dấu trang đầu giấy, xác nhận ranh
    giới mâu thuẫn) với prompt xóa đăng ký tạm trú."""
    return await _dieu_chinh._segment_all(pages_by_file, SYSTEM_PROMPT, build_user_prompt)


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

    # Trường hợp vắng mặt / đã đăng ký thường trú: bảng chỉ có dòng Tờ khai → giấy chứng minh chỗ ở đi dòng "+".
    no_home_row = table_has_no_home_row(pages_by_file, options)
    attachments: list[dict] = []
    notes: list[str] = []
    leftovers: list[str] = []
    seen: dict[str, int] = {}
    # Hai mặt thẻ của CÙNG một người (dù khác trang, khác tệp) luôn gộp thành MỘT giấy.
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        doc_type = str(doc.get("docType") or "").strip()
        if doc_type == _BLANK:
            doc_type = ""
        document_name = _document_name(name, _llm_document_name(doc) if doc else "")
        # Hai giấy cùng tên (thẻ căn cước của hai người) → đánh số: mỗi giấy một dòng "+" riêng, cán bộ phân biệt.
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        if doc_type == CHO_O and no_home_row is False:
            item = new_row_item(file_index, name, document_name, doc_type)
        elif doc_type in ROWS:
            item = plan_item(file_index, name, document_name, doc_type)
        elif doc_type in NEW_ROW_TYPES:
            item = new_row_item(file_index, name, document_name, doc_type)
        else:
            leftovers.append(document_name)
            item = plan_item(file_index, name, document_name, LEFTOVER_ROW, doc_type or "other")
        # Nhóm phủ đúng mọi phần của MỘT tệp → đính nguyên tệp, không dựng lại PDF.
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        if not whole:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        attachments.append(item)
        pages = sum(len(p["pages"]) if p["pages"] is not None else len(pages_by_file.get(p["fileIndex"], []))
                    for p in parts)
        notes.append(to_khai_note(doc, pages) if doc_type == TO_KHAI else "")

    finalize_rows(attachments, notes)
    if leftovers:
        errors.append(f"Giấy tờ chưa rõ loại đã đính vào dòng \"{ROWS[LEFTOVER_ROW]['componentName']}\": "
                      + ", ".join(leftovers))
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
