"""Đính kèm đăng ký khai sinh liên thông — chế độ TÁCH giấy tờ theo cài đặt của extension.

Cán bộ hay scan cả bộ hồ sơ thành MỘT tệp (giấy chứng sinh, giấy kết hôn, căn cước cha mẹ, tờ khai cư trú CT01...).
Chế độ không tách xếp cả tệp vào dòng giấy chứng sinh nên dòng tờ khai cư trú để trống. Ở đây LLM đọc hồ sơ theo
TRANG trong MỘT lượt và chia thành từng giấy; mỗi giấy thành một mục có `sourceSegments` (extension cắt đúng trang)
đặt vào đúng dòng như chế độ không tách: giấy chứng sinh → STT1, tờ khai cư trú → STT2, giấy khác → STT1 (tệp rời,
sau giấy chứng sinh). Cấu hình theo tài khoản (Nghĩa Lộ, Song Liễu) áp y như chế độ không tách.

Không sót trang: trang LLM không nhắc tới gộp vào giấy liền trước của cùng tệp; chỉ trang LLM nói là trang trắng mà
OCR cũng không có chữ mới bỏ. Tệp gọn một giấy → đính nguyên tệp. OCR/LLM lỗi → quay về chế độ không tách. Tệp trên
2 MB vẫn nén như chế độ không tách; extension cắt trang từ bản nén (giữ nguyên số trang).
"""

import asyncio
import re
import time

import fitz

from app.config import settings
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import (
    _decode,
    shrink_merged,
    shrink_oversized,
)
from app.pipelines.khai_sinh_lien_thong.attach import planner as base
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Mốc trang do dịch vụ OCR chèn ("───── Trang i/N ─────", app/services/ocr_tiengnoi.py). Bắt buộc có gạch trang trí:
# giấy chứng sinh in sẵn dòng chân trang "Trang 1/1" — nhận nó làm mốc là chia đôi một trang, mọi trang sau lệch số.
_PAGE_RE = re.compile(r"(?m)^\s*[─-]{3,}\s*Trang\s+(\d+)\s*/\s*(\d+)\s*[─-]{3,}\s*$")
_BLANK = "blank_page"
_DOC_TYPES = {base._DOC_BIRTH, base._DOC_RESIDENCE, base._DOC_DECLARATION, base._DOC_OTHER}
_MIN_LETTERS = 8  # số chữ cái tối thiểu để coi trang là có nội dung (số trang, dấu chấm, gạch không tính)


def _pages(text: str) -> list[str]:
    """Text OCR → text từng trang theo mốc "Trang i/N"; không có mốc (ảnh) → một trang."""
    marks = list(_PAGE_RE.finditer(text))
    if not marks:
        return [text.strip()]
    return [text[m.end():(marks[k + 1].start() if k + 1 < len(marks) else len(text))].strip()
            for k, m in enumerate(marks)]


def _pdf_page_count(file: dict) -> int | None:
    if file.get("type") != "application/pdf":
        return None
    try:
        with fitz.open(stream=_decode(file["dataUrl"]), filetype="pdf") as doc:
            return doc.page_count
    except Exception:  # noqa: BLE001 — PDF hỏng: không đối chiếu được, coi như lệch để không cắt
        return -1


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]
    max_tokens = max(800, min(4000, sum(len(p) for p in pages_by_file.values()) * 120))
    data: dict = {}
    for attempt in range(2):  # JSON hỏng / rỗng → hỏi lại một lần
        raw = await client.chat(messages, max_tokens=max_tokens, enable_thinking=settings.agent_reasoning)
        try:
            data = client.extract_json_block(raw)
        except Exception:  # noqa: BLE001
            if attempt:
                raise
            continue
        if any(isinstance(d, dict) and d.get("pages") for d in data.get("documents") or []):
            break
    return [d for d in data.get("documents") or [] if isinstance(d, dict)]


def _has_letters(pages: list[str], indexes: list[int]) -> bool:
    letters = sum(ch.isalpha() for i in indexes for ch in re.sub(r"(?i)trang\s*\d+", "", pages[i]))
    return letters >= _MIN_LETTERS


def _segments(pages_by_file: dict[int, list[str]], documents: list[dict]) -> list[dict]:
    """Giấy LLM chia → đoạn trang (0-based) theo tệp; trang không ai nhận gộp vào giấy liền trước, không sót trang."""
    taken: dict[int, set[int]] = {i: set() for i in pages_by_file}
    segments: list[dict] = []
    for doc in documents:
        try:
            file_index = int(doc.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        if file_index not in pages_by_file:
            continue
        count = len(pages_by_file[file_index])
        pages = []
        for page in doc.get("pages") or []:
            try:
                index = int(page) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= index < count and index not in taken[file_index] and index not in pages:
                pages.append(index)
        if not pages:
            continue
        if str(doc.get("docType") or "").strip() == _BLANK:
            # LLM gọi "trang trắng" mà OCR có chữ → không bỏ: để vòng dưới gộp vào giấy liền trước.
            if not _has_letters(pages_by_file[file_index], pages):
                taken[file_index].update(pages)
            continue
        taken[file_index].update(pages)
        segments.append({"fileIndex": file_index, "pages": sorted(pages), "doc": doc})
    for file_index, pages in pages_by_file.items():
        for index in range(len(pages)):
            if index in taken[file_index]:
                continue
            before = [s for s in segments if s["fileIndex"] == file_index and min(s["pages"]) < index]
            if before:
                max(before, key=lambda s: max(s["pages"]))["pages"].append(index)
            else:
                segments.append({"fileIndex": file_index, "pages": [index], "doc": {}})
    for segment in segments:
        segment["pages"].sort()
    return sorted(segments, key=lambda s: (s["fileIndex"], s["pages"][0]))


def _safe_name(value: str) -> str:
    """Tên tệp cổng liên thông nhận: chữ, số, dấu cách, "-" (xem base._SAFE_STEM); tối đa 50 ký tự."""
    text = re.sub(r"[^\w\s-]|_", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()[:50].strip()


def _fit_split_slot_budget(raw_files: list[dict], attachments: list[dict], replaced: dict[str, dict],
                           page_counts: dict[int, int]) -> list[tuple[int, int]]:
    """Ước dung lượng mỗi dòng theo tỉ lệ số trang mỗi phần cắt; trả [(fileIndex, đích byte)] cần nén cả tệp.

    Cổng chặn TỔNG mỗi dòng 2,6 MB. Chỉ nén được cả tệp nguồn (extension cắt trang từ bản nén), nên mỗi tệp góp vào
    dòng vượt ngân sách được nén theo cùng tỉ lệ thu nhỏ của dòng chặt nhất mà nó có mặt.
    """
    def size(i: int) -> int:
        entry = replaced.get(str(i))
        if entry:
            return entry["bytes"]
        try:
            return len(_decode(raw_files[i]["dataUrl"]))
        except Exception:  # noqa: BLE001 — dataUrl hỏng: không nén được, coi như 0 để không chặn cả dòng
            return 0

    ratio: dict[int, float] = {}
    for slot in {item.get("slotIndex") for item in attachments}:
        share: dict[int, float] = {}
        for item in attachments:
            if item.get("slotIndex") != slot:
                continue
            for segment in item.get("sourceSegments") or [{"fileIndex": item["fileIndex"], "pageIndexes": None}]:
                i = segment["fileIndex"]
                pages = segment.get("pageIndexes")
                part = len(pages) / max(1, page_counts.get(i, 1)) if pages else 1.0
                share[i] = share.get(i, 0.0) + part
        total = sum(size(i) * part for i, part in share.items())
        if total <= base.SLOT_BUDGET_BYTES:
            continue
        for i in share:
            ratio[i] = min(ratio.get(i, 1.0), base.SLOT_BUDGET_BYTES / total)
    return [(i, int(size(i) * r)) for i, r in sorted(ratio.items())]


async def _shrink_files(raw_files: list[dict], targets: list[tuple[int, int]], replaced: dict[str, dict],
                        errors: list[str]) -> None:
    async def one(i: int, limit: int) -> None:
        try:
            entry = await asyncio.to_thread(base._shrink_to_limit, raw_files[i], limit)
        except Exception as e:  # noqa: BLE001 — nén hỏng thì để nguyên, cổng tự báo nếu từ chối
            errors.append(f"Không nén được {raw_files[i].get('name')}: {e}")
            return
        current = (replaced.get(str(i)) or {}).get("bytes")
        if current is None or entry["bytes"] < current:
            replaced[str(i)] = entry
        if entry["bytes"] > limit:
            errors.append(
                f"Tệp {raw_files[i].get('name')} nén hết mức vẫn {entry['bytes'] / 1e6:.1f} MB; dòng giấy tờ có thể "
                "vượt giới hạn 2,6 MB của cổng, cần bớt giấy tờ đính kèm."
            )

    await asyncio.gather(*(one(i, limit) for i, limit in targets))


def _slot_item(file_index: int, file_name: str, document_name: str, doc_type: str, slot: int) -> dict:
    if slot == 0:
        return {
            "fileIndex": file_index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": base._BIRTH_PROOF_LABEL,
            "target": "fixed-slot",
            "slotIndex": 0,
            "slotKey": "birth_proof",
            "slotName": base._BIRTH_PROOF_LABEL,
            "needsAddComponent": False,
            "repeatUpload": True,
            "detectedType": base._BIRTH_PROOF_LABEL if doc_type == base._DOC_BIRTH else base._DOC_OTHER,
        }
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": base._RESIDENCE_FORM_LABEL,
        "target": "fixed-slot",
        "slotIndex": 1,
        "slotKey": "residence_form",
        "slotName": base._RESIDENCE_FORM_LABEL,
        "needsAddComponent": False,
        "detectedType": base._RESIDENCE_FORM_LABEL,
    }


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    omit_declaration = (options or {}).get(base.OMIT_BIRTH_DECLARATION_OPTION) is True
    only_birth_proof = (options or {}).get(base.ONLY_BIRTH_PROOF_OPTION) is True
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    split_notes: list[str] = []
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if not str(result.get("text") or "").strip():
            continue
        pages = _pages(str(result["text"]))
        real = _pdf_page_count(file)
        if real is not None and real != len(pages):
            # Số trang OCR lệch PDF thật → cắt theo số trang OCR là đính nhầm trang; đính nguyên tệp.
            split_notes.append(f"Không tách trang {file.get('name')}: OCR đọc {len(pages)} trang, tệp có {real} trang.")
            continue
        pages_by_file[index] = pages

    started = time.monotonic()
    try:
        if not pages_by_file:
            raise ValueError("không có chữ OCR để chia trang")
        documents = await _segment_all(pages_by_file)
        if not documents:
            raise ValueError("LLM không chia được giấy tờ")
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        shrink_task.cancel()
        result = await base.plan_khai_sinh_attachments(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *split_notes, *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)
    errors.extend(split_notes)

    replace_files = await shrink_task
    segments = _segments(pages_by_file, documents)
    covered = {s["fileIndex"] for s in segments}
    # Tệp không đọc được chữ (ảnh lạ, docx...) → đính nguyên tệp vào dòng giấy chứng sinh như chế độ không tách.
    segments += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(raw_files)) if i not in covered]
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))
    parts_of_file = {i: sum(1 for s in segments if s["fileIndex"] == i) for i in range(len(raw_files))}
    page_counts = {i: len(p) for i, p in pages_by_file.items()}
    whole_names = base._original_document_names(raw_files)

    used_names: set[str] = set()

    def unique(name: str) -> str:
        candidate, n = name, 2
        while base._fold(candidate) in used_names:
            candidate = f"{name} {n}"
            n += 1
        used_names.add(base._fold(candidate))
        return candidate

    birth: list[dict] = []
    other: list[dict] = []
    residence: list[dict] = []
    omitted_declarations: list[str] = []
    only_omitted: list[str] = []
    classified: list[dict] = []
    for s in segments:
        doc_type = str(s["doc"].get("docType") or "").strip()
        if doc_type not in _DOC_TYPES:
            doc_type = base._DOC_OTHER
        file_index = s["fileIndex"]
        whole = s["pages"] is None or parts_of_file[file_index] == 1
        if whole:
            document_name = unique(whole_names[file_index])
        else:
            llm_name = _safe_name(s["doc"].get("documentName") or "")
            if not llm_name or base._is_messy_stem(llm_name):
                llm_name = base._DOC_TYPE_NAMES[doc_type]
            document_name = unique(llm_name)
        page_label = "cả tệp" if whole else [p + 1 for p in s["pages"]]
        classified.append({"fileName": raw_files[file_index]["name"], "pages": page_label,
                           "docType": doc_type, "documentName": document_name})

        # Tờ khai đăng ký khai sinh chỉ tách riêng khi có cấu hình địa bàn; còn lại đi như giấy khác (STT1).
        if doc_type == base._DOC_DECLARATION and omit_declaration:
            omitted_declarations.append(document_name)
            continue
        if doc_type == base._DOC_DECLARATION:
            doc_type = base._DOC_OTHER
        if only_birth_proof and doc_type == base._DOC_OTHER:
            only_omitted.append(document_name)
            continue
        slot = 1 if doc_type == base._DOC_RESIDENCE else 0
        item = _slot_item(file_index, raw_files[file_index]["name"], document_name, doc_type, slot)
        if not whole:
            item["sourceSegments"] = [{"fileIndex": file_index, "pageIndexes": s["pages"]}]
        if doc_type == base._DOC_BIRTH:
            birth.append(item)
        elif doc_type == base._DOC_RESIDENCE:
            residence.append(item)
        else:
            # Cổng chặn TỔNG dung lượng mỗi dòng; chỉ giấy tờ KHÁC được rơi sang STT2 khi cổng báo quá dung lượng.
            item["fallbackSlotIndex"] = 1
            item["fallbackSlotKey"] = "residence_form"
            item["fallbackSlotName"] = base._RESIDENCE_FORM_LABEL
            other.append(item)

    if len(residence) > 1:
        for item in residence:
            item["repeatUpload"] = True  # nhiều tờ khai → thêm từng tệp rời vào cùng hàng STT2
    attachments = birth + other + residence

    for name in omitted_declarations:
        errors.append(f"{base.OMITTED_DECLARATION_NOTE}: {name}")
    if only_omitted:
        errors.append(f"{base.ONLY_BIRTH_PROOF_NOTE}: " + ", ".join(only_omitted))
    if not birth:
        errors.append(
            "Không tìm thấy giấy chứng sinh (hoặc văn bản người làm chứng/giấy cam đoan về việc sinh) "
            "trong các file đã tải lên"
            + ("; đã đính các giấy tờ khác vào ô giấy chứng sinh, cần bổ sung giấy chứng sinh." if other else ".")
        )

    targets = _fit_split_slot_budget(raw_files, attachments, replace_files, page_counts)
    await _shrink_files(raw_files, targets, replace_files, errors)
    await shrink_merged(raw_files, attachments, replace_files, errors)

    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "documentSplitEnabled": True,
            "classified": classified,
            "omittedDeclarations": omitted_declarations,
            "onlyBirthProofOmitted": only_omitted,
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
