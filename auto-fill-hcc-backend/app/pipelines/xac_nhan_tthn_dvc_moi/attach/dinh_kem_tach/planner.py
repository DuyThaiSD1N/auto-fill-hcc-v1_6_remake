"""Đính kèm cấp Giấy XNTTHN (Cổng DVC quốc gia mới) — chế độ TÁCH giấy tờ theo cài đặt của extension.

Một tệp hay gộp nhiều giấy (tờ khai + CCCD + bản án...). LLM đọc cả hồ sơ theo TRANG trong MỘT lượt và chia thành từng
giấy; mỗi giấy thành một mục đính kèm có `sourceSegments` (extension cắt đúng các trang) đặt vào ĐÚNG dòng có sẵn của
bảng thành phần — giấy XNTTHN cũ, giấy tờ ly hôn/khai tử, ủy quyền vào dòng riêng; giấy khác vào dòng giấy tờ hôn nhân. Không sót trang: trang LLM không nhắc tới gộp
vào giấy liền trước của cùng tệp; chỉ trang LLM nói là trang trắng mới bỏ. Xã Nghĩa Hưng: bỏ các trang tờ khai;
phường Đông Hà: chỉ giữ giấy ủy quyền (cắt đúng trang).
OCR/LLM lỗi → quay về chế độ không tách. Tệp trên 2 MB vẫn nén như chế độ không tách.
"""

import asyncio
import re
import time
import unicodedata

from app.config import settings
from app.pipelines._shared.identity_merge import ho_ten_co_dau, mat_the, so_dinh_danh_the
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_merged, shrink_oversized
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import DEFAULT_ROW, DOC_TYPES, ROWS, _document_name, _llm_document_name
from ..dinh_kem_khong_tach.planner import both_sides, pair_card_sides
from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from ..nghia_hung import OMITTED_DECLARATION_NOTE, keep_only_authorization, omits_paper_declaration, only_authorization
from .prompt import CONFIRM_PROMPT, SYSTEM_PROMPT, build_confirm_prompt, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_PAGE_RE = re.compile(r"(?m)^\W*Trang\s+(\d+)\s*/\s*(\d+)\W*$")
_BLANK = "blank_page"
ROW_BY_TYPE = ROWS


def _pages(text: str) -> list[str]:
    """Text OCR → danh sách text từng trang theo mốc "Trang i/N"; không có mốc (ảnh) → một trang."""
    marks = list(_PAGE_RE.finditer(text))
    if not marks:
        return [text.strip()]
    return [text[m.end():(marks[k + 1].start() if k + 1 < len(marks) else len(text))].strip()
            for k, m in enumerate(marks)]


def _max_tokens(pages_by_file: dict[int, list[str]]) -> int:
    """Trần token theo tổng số trang của hồ sơ, đúng công thức planner form cũ."""
    return max(1200, min(6000, sum(len(p) for p in pages_by_file.values()) * 220))


async def _segment_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]
    data: dict = {}
    for attempt in range(2):  # JSON hỏng / rỗng (model thỉnh thoảng trả thiếu khóa) → hỏi lại một lần
        raw = await client.chat(messages, max_tokens=_max_tokens(pages_by_file),
                                enable_thinking=settings.agent_reasoning)
        try:
            data = client.extract_json_block(raw)
        except Exception:  # noqa: BLE001
            if attempt:
                raise
            continue
        if any(isinstance(d, dict) and d.get("pages") for d in data.get("documents") or []):
            break
    documents = [d for d in data.get("documents") or [] if isinstance(d, dict)]
    titles = _page_titles(pages_by_file, data.get("tep"))
    disputed = _disputed_starts(documents, titles)
    confirmed = await _confirm_starts(pages_by_file, disputed) if disputed else set()
    return _by_page_titles(documents, titles, {(f, p) for f, p, _ in disputed} - confirmed)


def _page_numbers(doc: dict) -> list[int]:
    out = []
    for page in doc.get("pages") or []:
        try:
            out.append(int(page))
        except (TypeError, ValueError):
            continue
    return out


def _file_index(doc: dict) -> int | None:
    try:
        return int(doc.get("fileIndex"))
    except (TypeError, ValueError):
        return None


def _fold_title(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "")).replace("đ", "d").replace("Đ", "D")
    return " ".join("".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower().split())


def _page_titles(pages_by_file: dict[int, list[str]], files) -> dict[int, list[str]]:
    """Tiêu đề từng trang LLM liệt kê ở "tep" (trang đầu giấy → tên loại giấy, trang khác → ""); bỏ tệp lệch số trang."""
    titles: dict[int, list[str]] = {}
    for item in files if isinstance(files, list) else []:
        file_index = _file_index(item) if isinstance(item, dict) else None
        page_titles = item.get("tieuDeTrang") if isinstance(item, dict) else None
        if file_index in pages_by_file and isinstance(page_titles, list) \
                and len(page_titles) == len(pages_by_file[file_index]):
            titles[file_index] = [str(t or "").strip() for t in page_titles]
    return titles


def _owners(documents: list[dict], file_index: int) -> dict[int, dict]:
    owner: dict[int, dict] = {}
    for doc in documents:
        if _file_index(doc) == file_index:
            for page in _page_numbers(doc):
                owner.setdefault(page, doc)
    return owner


def _title_starts(page_titles: list[str], owner: dict[int, dict]) -> list[int]:
    """Trang mở giấy theo tiêu đề. Trang giữa một phần tử "documents" mang đúng tiêu đề trang đầu / tên của phần tử đó
    là trang tiếp theo của cùng giấy (tiêu đề in lặp, hoặc model đặt tiêu đề lệch sang trang 2), không mở giấy mới."""
    starts = []
    for k, title in enumerate(page_titles):
        doc = owner.get(k + 1)
        first = min(_page_numbers(doc)) if doc else 0
        repeated = 0 < first < k + 1 and _fold_title(title) in (
            _fold_title(page_titles[first - 1]), _fold_title(doc.get("documentName")))
        if k == 0 or (title and not repeated):
            starts.append(k + 1)
    return starts


def _disputed_starts(documents: list[dict], titles: dict[int, list[str]]) -> list[tuple[int, int, int]]:
    """(tệp, trang, trang đầu giấy liền trước theo tiêu đề) khi tiêu đề nói trang mở giấy mới mà "documents" để chung
    với trang trước. So với trang đầu giấy theo TIÊU ĐỀ: phần tử "documents" có thể lệch trang (bắt đầu ở mặt sau giấy
    trước)."""
    out = []
    for file_index, page_titles in titles.items():
        owner = _owners(documents, file_index)
        starts = _title_starts(page_titles, owner)
        for previous, page in zip(starts, starts[1:]):
            doc = owner.get(page)
            if doc is not None and str(doc.get("docType") or "").strip() != _BLANK \
                    and min(_page_numbers(doc)) < page:
                out.append((file_index, page, previous))
    return out


async def _confirm_starts(pages_by_file: dict[int, list[str]], disputed: list[tuple[int, int, int]]) -> set:
    """Hỏi LLM riêng từng trang mâu thuẫn: giấy độc lập (bản cam đoan sau giấy khai sinh) hay một phần của giấy trước
    (trang ghi chú in kèm, phụ lục, trang ký). Lỗi → tin tiêu đề (tách), không mất trang nào."""
    items = [{"id": n, "giayTruoc": pages_by_file[f][first - 1][:1200], "trangSau": pages_by_file[f][page - 1][:1500]}
             for n, (f, page, first) in enumerate(disputed)]
    messages = [
        {"role": "system", "content": CONFIRM_PROMPT},
        {"role": "user", "content": build_confirm_prompt(items)},
    ]
    try:
        raw = await client.chat(messages, max_tokens=200 + 40 * len(items), enable_thinking=settings.agent_reasoning)
        answers = client.extract_json_block(raw).get("answers") or []
        yes = {int(a["id"]) for a in answers if isinstance(a, dict) and a.get("giayMoi") is True}
    except Exception:  # noqa: BLE001
        yes = set(range(len(disputed)))
    return {(disputed[i][0], disputed[i][1]) for i in yes if 0 <= i < len(disputed)}


def _by_page_titles(documents: list[dict], titles: dict[int, list[str]], rejected: set) -> list[dict]:
    """Ranh giới giấy theo tiêu đề từng trang ("tep"): model đọc tiêu đề từng trang đúng nhưng khi chia "documents" hay
    dồn giấy sau vào giấy trước (bản cam đoan sau trang ghi chú giấy khai sinh). Mỗi trang có tiêu đề mở một giấy, trừ
    trang mâu thuẫn mà lượt xác nhận nói là một phần của giấy trước (`rejected`). Tên / loại / mặt thẻ lấy từ phần tử
    "documents" bắt đầu đúng trang đó; phần bị tách ra mang tên theo tiêu đề. Tệp không có tiêu đề → giữ "documents"."""
    out = [d for d in documents if _file_index(d) not in titles]
    for file_index, page_titles in titles.items():
        owner = _owners(documents, file_index)
        blank = {p for p, d in owner.items() if str(d.get("docType") or "").strip() == _BLANK}
        starts = [p for p in _title_starts(page_titles, owner) if (file_index, p) not in rejected]
        for a, b in zip(starts, [*starts[1:], len(page_titles) + 1]):
            # Trang LLM gọi là trắng giữ nguyên phần tử riêng: _segments quyết bỏ (trắng thật) hay gộp (có chữ).
            out += [{**owner[p], "fileIndex": file_index, "pages": [p]} for p in range(a, b) if p in blank]
            pages = [p for p in range(a, b) if p not in blank]
            if not pages:
                continue
            doc = owner.get(pages[0])
            if doc is not None and min(_page_numbers(doc)) == pages[0]:
                meta = dict(doc)
                if len({id(owner[p]) for p in pages if p in owner}) > 1 and meta.get("matThe") in ("truoc", "sau"):
                    meta["matThe"] = "ca_hai"  # hai mặt thẻ LLM để hai phần tử nhưng cùng một giấy theo tiêu đề
            else:
                meta = {"docType": "", "documentName": page_titles[pages[0] - 1], "matThe": "", "chuThe": ""}
            out.append({**meta, "fileIndex": file_index, "pages": pages})
    return out


_CHU_TOI_THIEU = 8   # số chữ cái tối thiểu để coi trang là có nội dung (số trang, dấu chấm, gạch không tính)


def _co_chu(pages: list[str], indexes: list[int]) -> bool:
    letters = sum(ch.isalpha() for i in indexes for ch in re.sub(r"(?i)trang\s*\d+", "", pages[i]))
    return letters >= _CHU_TOI_THIEU


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
            # LLM gọi "trang trắng" mà OCR có chữ (mặt sau bản sao có dấu, trang ký...) → không bỏ trang: để vòng
            # dưới gộp vào giấy liền trước như trang không ai nhận.
            if not _co_chu(pages_by_file[file_index], pages):
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


def _item(file_index: int, file_name: str, document_name: str, doc_type: str, sources: list[dict] | None) -> dict:
    row = ROW_BY_TYPE.get(doc_type, DEFAULT_ROW)
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type if doc_type in DOC_TYPES else "other",
        "noChooserClick": True,
        **row,
    }
    if sources is not None:
        item["sourceSegments"] = sources
    return item


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            pages_by_file[index] = _pages(str(result["text"]))

    started = time.monotonic()
    try:
        documents = await _segment_all(pages_by_file) if pages_by_file else []
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        shrink_task.cancel()
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"attachment_agent (tách): {exc}", *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    segments = _segments(pages_by_file, documents)
    omitted: dict[int, int] = {}  # tệp → số đoạn tờ khai đã bỏ
    if omits_paper_declaration(options):
        for segment in [s for s in segments if str(s["doc"].get("docType") or "").strip() == "declaration"]:
            segments.remove(segment)
            omitted[segment["fileIndex"]] = omitted.get(segment["fileIndex"], 0) + 1
            pages = ", ".join(str(p + 1) for p in segment["pages"])
            errors.append(f"{OMITTED_DECLARATION_NOTE}: bỏ trang {pages} của {names[segment['fileIndex']]}")
    covered = {s["fileIndex"] for s in segments} | set(omitted)
    segments += [{"fileIndex": i, "pages": None, "doc": {}} for i in range(len(names)) if i not in covered]
    segments.sort(key=lambda s: (s["fileIndex"], (s["pages"] or [0])[0]))
    # Đoạn tờ khai đã bỏ vẫn tính là một phần của tệp → phần còn lại phải cắt trang, không đính nguyên tệp.
    parts_of_file = {i: sum(1 for s in segments if s["fileIndex"] == i) + omitted.get(i, 0) for i in range(len(names))}

    # Số định danh đọc từ OCR của từng đoạn: khoá ghép hai mặt thẻ (họ tên LLM đọc có thể lệch giữa hai mặt).
    # Cả đoạn LLM bỏ sót (vd tệp mặt sau thẻ chụp riêng) cũng đọc mặt thẻ từ OCR để còn ghép với mặt trước.
    for s in segments:
        pages = pages_by_file.get(s["fileIndex"], [])
        text = "\n".join(pages if s["pages"] is None else [pages[i] for i in s["pages"] if i < len(pages)])
        s["doc"] = {**s["doc"], "_soThe": so_dinh_danh_the(text), "_matTheOcr": mat_the(text),
                    "chuThe": ho_ten_co_dau(s["doc"].get("chuThe") or "", text)}

    attachments: list[dict] = []
    seen: dict[str, int] = {}
    # Hai mặt thẻ của CÙNG một người (dù khác trang, khác tệp) luôn gộp thành MỘT giấy.
    for group in pair_card_sides([s["doc"] for s in segments]):
        parts = [segments[i] for i in group]
        doc = both_sides(parts[0]["doc"]) if len(parts) > 1 else parts[0]["doc"]
        file_index = parts[0]["fileIndex"]
        name = names[file_index]
        document_name = _document_name(name, _llm_document_name(doc) if doc else "")
        # Hai giấy cùng tên (CCCD hai người...) → đánh số để cổng và cán bộ phân biệt được.
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        # Nhóm phủ đúng mọi phần của MỘT tệp (vd tệp CCCD 2 trang = 2 mặt) → đính nguyên tệp, không dựng lại PDF.
        whole = {p["fileIndex"] for p in parts} == {file_index} and parts_of_file[file_index] == len(parts)
        sources = None if whole else [{"fileIndex": p["fileIndex"], "pageIndexes": p["pages"]} for p in parts]
        attachments.append(_item(file_index, name, document_name, str(doc.get("docType") or "").strip(), sources))

    if only_authorization(options):
        keep_only_authorization(attachments)

    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        # Đông Hà: hồ sơ không có ủy quyền thì không đính gì — extension coi là xong, không báo lỗi.
        "nothingToAttach": (only_authorization(options) and not attachments) or None,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "segments": [
                {"fileName": item["fileName"], "documentName": item["documentName"], "slotIndex": item["slotIndex"],
                  "pages": [[s["fileIndex"], [p + 1 for p in s["pageIndexes"] or []] or "cả tệp"]
                            for s in item.get("sourceSegments") or []] or "cả tệp"}
                for item in attachments
            ],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
