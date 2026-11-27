"""Đính kèm TÁCH giấy tờ cho thủ tục tách thửa hoặc hợp thửa đất (iGate Ninh Bình, 1.012784) — cài đặt "Có tách hồ sơ
khi đính kèm" bật.

Bộ hồ sơ hay là MỘT bản scan gộp (Đơn, Giấy chứng nhận, Bản vẽ, Giấy phép đo đạc), có khi chụp lặp lại cùng trang Đơn nhiều
lần. LLM đọc đầu từng trang trong MỘT lượt, chỉ ra trang nào mở giấy mới và loại giấy đó; mỗi giấy thành một mục đính kèm có
`sourceSegments` (extension cắt đúng các trang), đặt vào chỗ của loại giấy — cùng bảng với chế độ không tách:

  ban_ve, giay_phep_do_dac -> dòng 1 | gcn -> dòng 2 | van_ban_cqctq -> dòng 3 | don_tach_thua, giấy không rõ loại -> dòng 4
  authorization, identity -> "+ Thêm giấy tờ" (không tạo được dòng thì FE đính chung dòng 4)

Trang trắng bỏ; trang nối tiếp thuộc giấy liền trước; hai mặt CCCD là một giấy. Trang CHỤP LẶP gần y hệt một trang đã giữ
trong cùng tệp (so chữ OCR, duplicate_pages) bỏ, chỉ nộp một bản (ảnh ánh xạ: "các trang 2, 4, 6 là bản chụp lặp lại của
trang 1"). Hàm chia trang dùng lại của đính chính GCN Tuyên Quang (cùng nền iGate). Tệp không cắt được (ảnh, số trang OCR
lệch PDF) đính nguyên tệp một lần vào chỗ của giấy chính; LLM chia giấy lỗi → gọi chế độ không tách.
"""

import re
import time
from difflib import SequenceMatcher

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import splittable_pages
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach.dinh_kem_tach.planner import (
    _clean_name,
    _is_blank,
    _label,
    _page_ocr,
)
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import (
    _DON_ROW,
    _OTHER,
    _PRIORITY,
    _TYPE_NAME,
    _normalize_doc_type,
    attachment_item,
    missing_warnings,
    place_label,
)
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Trang chụp lặp: so theo TỪ của chữ OCR đã bỏ dấu. Hai lần OCR cùng một ảnh/trang lệch vài chữ nên lấy ngưỡng 0,9; trang
# quá ít chữ (trang "Những thay đổi…" trống, mặt sau thẻ) giống nhau theo mẫu in chứ không phải chụp lặp → không xét.
_DUP_RATIO = 0.9
_DUP_MIN_WORDS = 40


def _words(page: str) -> list[str]:
    return re.findall(r"\w+", _fold(page or ""))


def duplicate_pages(pages: list[str]) -> dict[int, int]:
    """{trang chụp lặp: trang gốc đã giữ} trong một tệp (0-based)."""
    out: dict[int, int] = {}
    kept: list[tuple[int, list[str]]] = []
    for index, page in enumerate(pages):
        words = _words(page)
        if len(words) < _DUP_MIN_WORDS:
            continue
        for original, other in kept:
            matcher = SequenceMatcher(None, words, other, autojunk=False)
            if matcher.real_quick_ratio() >= _DUP_RATIO and matcher.quick_ratio() >= _DUP_RATIO \
                    and matcher.ratio() >= _DUP_RATIO:
                out[index] = original
                break
        else:
            kept.append((index, words))
    return out


def parse_documents(data: dict, page_counts: dict[int, int]) -> dict[int, list[tuple[int, str, str]]]:
    """JSON LLM → {tệp: [(trang đầu 0-based, docType, tên)]} theo trang tăng dần; bỏ số trang ngoài tệp."""
    out: dict[int, list[tuple[int, str, str]]] = {}
    for item in data.get("tep") or []:
        if not isinstance(item, dict):
            continue
        try:
            file_index = int(item.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        count = page_counts.get(file_index) or 0
        if not count or file_index in out:
            continue
        docs: list[tuple[int, str, str]] = []
        for doc in item.get("giayTo") or []:
            if not isinstance(doc, dict):
                continue
            try:
                page = int(doc.get("trangDau")) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= page < count:
                docs.append((page, _normalize_doc_type(doc.get("docType")), _clean_name(doc.get("ten"))))
        out[file_index] = sorted(docs, key=lambda doc: doc[0])
    return out


async def _segment(units: dict[int, list[str]]) -> dict[int, list[tuple[int, str, str]]]:
    payload = [
        {"fileIndex": index, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": _page_ocr(page)} for n, page in enumerate(pages)]}
        for index, pages in units.items()
    ]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_user_prompt(payload)}]
    total = sum(len(pages) for pages in units.values())
    for attempt in range(2):  # JSON hỏng → hỏi lại một lần
        # temperature 0: cùng tệp phải ra cùng cách chia giữa các lần chạy.
        raw = await client.chat(messages, temperature=0, max_tokens=max(400, min(4000, 120 + 60 * total)),
                                enable_thinking=settings.agent_reasoning)
        try:
            return parse_documents(client.extract_json_block(raw), {i: len(p) for i, p in units.items()})
        except Exception:  # noqa: BLE001
            if attempt:
                raise
    return {}


def build_plan_items(
    files: list[dict],
    pages_by_file: dict[int, list[str]],
    documents: dict[int, list[tuple[int, str, str]]],
) -> tuple[list[dict], list[str], list[dict]]:
    """``pages_by_file``: trang OCR của tệp cắt được (>1 trang khớp PDF); tệp có chữ mà không cắt được mang 1 "trang"."""
    attachments: list[dict] = []
    warnings: list[str] = []
    segments: list[dict] = []
    seen_names: dict[str, int] = {}
    present: set[str] = set()

    def add(file_index: int, doc_type: str, name: str, pages: list[int] | None) -> None:
        file_name = str(files[file_index].get("name") or f"file-{file_index + 1}")
        document_name = name or (file_name if doc_type == _OTHER else _TYPE_NAME[doc_type])
        # Hai giấy cùng tên (CCCD hai người, hai Giấy chứng nhận khi hợp thửa…) → đánh số để cổng và cán bộ phân biệt.
        key = _fold(document_name)
        seen_names[key] = seen_names.get(key, 0) + 1
        if seen_names[key] > 1:
            document_name = f"{document_name} {seen_names[key]}"
        item = attachment_item(file_index, file_name, doc_type, document_name)
        if pages is not None:
            item["sourceSegments"] = [{"fileIndex": file_index, "pageIndexes": pages}]
        attachments.append(item)
        segments.append({"fileName": file_name, "documentName": document_name, "docType": doc_type,
                         "place": place_label(doc_type), "pages": "cả tệp" if pages is None else [p + 1 for p in pages]})
        if doc_type == _OTHER:
            where = f"{file_name}, {_label(pages)}" if pages is not None else file_name
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ '{document_name}' ({where}) — tạm đính vào dòng "
                            f"{_DON_ROW} (Đơn đề nghị tách thửa, hợp thửa); cán bộ kiểm tra lại.")

    for index in range(len(files)):
        pages = pages_by_file.get(index) or []
        docs = documents.get(index) or []
        present.update(doc_type for _, doc_type, _ in docs)
        file_name = str(files[index].get("name") or f"file-{index + 1}")
        if len(pages) <= 1:
            # Ảnh / tệp không cắt được: nguyên tệp MỘT lần vào chỗ của giấy chính, như chế độ không tách.
            types = [doc_type for _, doc_type, _ in docs]
            doc_type = next((item for item in _PRIORITY if item in types), _OTHER)
            place = place_label(doc_type)
            others = sorted({place_label(item) for item in types if item != _OTHER} - {place})
            name = file_name if others else next((n for _, item, n in docs if item == doc_type), "")
            add(index, doc_type, name, None)
            if others:
                warnings.append(f"'{file_name}' gộp nhiều giấy tờ nhưng không tách được trang — đính nguyên tệp một lần "
                                f"vào {place}, không tách sang {', '.join(others)}.")
            continue
        duplicates = duplicate_pages(pages)
        starts: dict[int, tuple[str, str]] = {}
        for page, doc_type, name in docs:
            starts.setdefault(page, (doc_type, name))
        starts.setdefault(0, (_OTHER, ""))
        bounds = sorted(starts) + [len(pages)]
        for first, end in zip(bounds, bounds[1:]):
            kept = [p for p in range(first, end) if not _is_blank(pages[p]) and p not in duplicates]
            if not kept:
                continue  # đoạn toàn trang trắng / trang chụp lặp
            doc_type, name = starts[first]
            whole = kept == list(range(len(pages)))
            add(index, doc_type, name, None if whole else kept)
        if duplicates:
            dropped = ", ".join(f"trang {page + 1} (lặp trang {original + 1})"
                                for page, original in sorted(duplicates.items()))
            warnings.append(f"'{file_name}': bỏ {dropped} — trang chụp lặp lại, chỉ đính một bản.")

    if files:
        warnings.extend(missing_warnings(present))
    return attachments, warnings, segments


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        text = str(result.get("text") or "")
        if not text.strip():
            continue
        # Không cắt được (số trang OCR lệch PDF) → cả tệp là một "trang" trích đoạn đại diện.
        pages_by_file[index] = splittable_pages(file, text) or [representative_excerpt(text, 6000)]

    started = time.monotonic()
    try:
        documents = await _segment(pages_by_file) if pages_by_file else {}
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"Tách giấy tờ: {exc} — đính nguyên tệp.", *errors, *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, segments = build_plan_items(raw_files, pages_by_file, documents)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "tachGiayTo": segments,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
