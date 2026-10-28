"""Tách tệp scan nhiều giấy tờ cho nhóm thủ tục hộ kinh doanh (cổng HkdOnline).

Cán bộ hay scan cả bộ hồ sơ thành một PDF (Giấy đề nghị + CCCD + giấy tờ trụ sở / GCN / thông báo thuế…), còn
planner từng thủ tục phân loại NGUYÊN TỆP nên cả bộ vào một loại đính kèm. Khi cán bộ bật "Tách tệp có nhiều giấy
tờ" (``splitDocuments``):

1. OCR tệp gốc một lần; LLM đọc đầu từng trang, chỉ ra trang nào MỞ một giấy mới.
2. Cắt mỗi đoạn thành một PDF con, chạy CHÍNH planner của thủ tục trên các PDF con (chữ OCR nạp sẵn qua
   ``ocr.preset_texts``) → mỗi giấy nhận loại đính kèm riêng.
3. Đổi kế hoạch về tệp gốc bằng ``sourceSegments``; extension cắt trang trước khi tải lên cổng.

Prompt chung mô tả đặc điểm giấy tờ HKD; từng thủ tục truyền thêm danh sách giấy tờ của mình (``doc_hints``).
LLM chia lỗi / tệp ảnh / số trang OCR lệch PDF → planner chạy trên tệp gốc như cũ.
"""

import base64
import json
import re
import time
from pathlib import Path

import fitz  # pymupdf

from app.config import settings
from app.process.schemas import FileItem

# Header trang dịch vụ OCR chèn vào text: "───── Trang 2/4 ─────".
_PAGE_HEADER_RE = re.compile(r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$")
# Trang trắng / mặt sau hoa văn: OCR chỉ ra vài chữ rác ("Qwen", "(1)", câu lạc đề, hoặc riêng dòng quốc hiệu ~27 ký
# tự) → không được mở giấy mới; model hay tách nó thành một giấy riêng. Trang đầu giấy thật (kể cả mặt sau CCCD có
# dòng MRZ) luôn hàng trăm ký tự.
_MIN_PAGE_CHARS = 40
_PAGE_OCR_CHARS = 1200

SYSTEM_PROMPT = """
<persona>
Bạn chia bộ hồ sơ scan của thủ tục HỘ KINH DOANH thành từng GIẤY TỜ riêng. Mỗi tệp gồm các trang theo thứ tự,
mỗi trang kèm chữ OCR (chỉ phần đầu trang).
</persona>

<giay_to_cua_thu_tuc>
%DOC_HINTS%
</giay_to_cua_thu_tuc>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy.
2. Một trang MỞ GIẤY MỚI khi nó là trang đầu của một văn bản KHÁC với giấy trước: có quốc hiệu và tiêu đề văn
   bản riêng (GIẤY ĐỀ NGHỊ, THÔNG BÁO, GIẤY CHỨNG NHẬN, HỢP ĐỒNG, BIÊN BẢN, GIẤY ỦY QUYỀN...), là thẻ căn cước/CCCD,
   hoặc cùng loại nhưng khác người/khác số hiệu.
3. Mẫu đơn hộ kinh doanh (Giấy đề nghị, Thông báo) dài nhiều trang và trang sau KHÔNG có quốc hiệu: trang mở đầu
   bằng số mục ("2. Trụ sở...", "3. Ngành, nghề...", "5.2."), bảng ngành nghề, bảng thành viên hộ gia đình, phần
   "Tôi xin cam kết", chữ ký "CHỦ HỘ KINH DOANH", chú thích cuối trang, số trang đứng đầu → CÙNG giấy trước. Tiêu
   đề mục in hoa bên trong đơn (vd "ĐĂNG KÝ THAY ĐỔI TÊN HỘ KINH DOANH", "ĐĂNG KÝ THAY ĐỔI NGÀNH, NGHỀ KINH
   DOANH") là một mục của đơn, KHÔNG phải giấy mới.
4. Mặt trước + mặt sau CCCD của CÙNG một người là MỘT giấy. Mặt sau Giấy chứng nhận, các trang tiếp của Giấy
   chứng nhận quyền sử dụng đất (sơ đồ thửa, những thay đổi sau khi cấp), trang ký của hợp đồng → cùng giấy.
5. Trang trắng hoặc không đọc được thuộc giấy liền trước. Trang chỉ có vài chữ rời rạc, không có tiêu đề văn bản và
   nội dung (vd chỉ một dòng quốc hiệu, chữ lẻ, câu không liên quan hồ sơ — OCR đọc nhầm nền hoa văn) là mặt sau
   hoặc trang trắng → thuộc giấy liền trước.
6. Không chắc → KHÔNG tách. Tách sai tệ hơn không tách.
7. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

<output_contract>
{"tep":[{"fileIndex":0,"trangDau":[1,4]}]}
Mỗi tệp đầu vào đúng một phần tử "tep"; "trangDau" là số trang (đếm từ 1) MỞ giấy mới, tăng dần.
</output_contract>
""".strip()


def split_requested(options: dict | None) -> bool:
    """Cán bộ bật "Tách tệp có nhiều giấy tờ" và extension cắt được trang (Auto Fill không gửi
    supportsSourceSegments nhưng luôn cắt được). Extension cũ không gửi splitDocuments → không tách."""
    opts = options or {}
    return opts.get("splitDocuments") is True and opts.get("supportsSourceSegments") is not False


def split_pages(text: str) -> list[str]:
    """Text OCR theo trang (header "───── Trang i/n ─────"). Không có header → 1 trang."""
    matches = list(_PAGE_HEADER_RE.finditer(text or ""))
    if not matches:
        return [text or ""]
    total = max(int(m.group(2)) for m in matches)
    pages = [""] * max(total, len(matches))
    for pos, match in enumerate(matches):
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        number = int(match.group(1))
        if 1 <= number <= len(pages):
            pages[number - 1] = text[match.end():end].strip()
    return pages


def _join_pages(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{page}" for n, page in enumerate(pages))


def _is_blank(page: str) -> bool:
    return len(re.findall(r"\w", page or "")) < _MIN_PAGE_CHARS


def _page_ocr(page: str) -> str:
    # Chữ rác của trang trắng (vd riêng dòng quốc hiệu) kéo model coi là giấy mới rồi bỏ sót ranh giới kế tiếp.
    if _is_blank(page):
        return "(trang trắng / mặt sau, không có nội dung)"
    return re.sub(r"\s+", " ", page).strip()[:_PAGE_OCR_CHARS]


def _user_prompt(pages_by_file: dict[int, list[str]]) -> str:
    payload = [
        {"fileIndex": i, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": _page_ocr(t)} for n, t in enumerate(pages)]}
        for i, pages in pages_by_file.items()
    ]
    return "HỒ SƠ:\n" + json.dumps(payload, ensure_ascii=False)


def page_starts(data: dict, pages_by_file: dict[int, list[str]]) -> dict[int, list[int]]:
    """JSON LLM → {tệp: [trang đầu 0-based]}; trang 1 luôn mở giấy, bỏ số trang ngoài tệp và trang trắng."""
    out: dict[int, list[int]] = {}
    for item in data.get("tep") or []:
        if not isinstance(item, dict):
            continue
        try:
            file_index = int(item.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        pages = pages_by_file.get(file_index) or []
        if not pages or file_index in out:
            continue
        starts = {0}
        for value in item.get("trangDau") or []:
            try:
                page = int(value) - 1
            except (TypeError, ValueError):
                continue
            if 0 < page < len(pages) and not _is_blank(pages[page]):
                starts.add(page)
        out[file_index] = sorted(starts)
    return out


async def _segment(pages_by_file: dict[int, list[str]], doc_hints: str) -> dict[int, list[int]]:
    from app.services.llm import client

    system = SYSTEM_PROMPT.replace("%DOC_HINTS%", doc_hints.strip())
    messages = [{"role": "system", "content": system}, {"role": "user", "content": _user_prompt(pages_by_file)}]
    total = sum(len(p) for p in pages_by_file.values())
    for attempt in range(2):  # JSON hỏng → hỏi lại một lần
        # temperature 0: chỉ ra số trang, cần ổn định giữa các lần chạy cùng tệp.
        raw = await client.chat(messages, temperature=0, max_tokens=max(300, min(2000, 100 + 20 * total)),
                                enable_thinking=settings.agent_reasoning)
        try:
            return page_starts(client.extract_json_block(raw), pages_by_file)
        except Exception:  # noqa: BLE001
            if attempt:
                raise
    return {}


def _pdf_bytes(file: dict) -> bytes | None:
    header, sep, payload = str(file.get("dataUrl") or "").partition(",")
    if not sep or "pdf" not in (header.lower() + str(file.get("type") or "").lower()):
        return None
    try:
        return base64.b64decode(payload)
    except ValueError:
        return None


def _cut_pdf(raw: bytes, pages: list[int]) -> str:
    """PDF con gồm các trang (0-based, liền nhau) → data URL."""
    with fitz.open(stream=raw, filetype="pdf") as doc, fitz.open() as out:
        out.insert_pdf(doc, from_page=pages[0], to_page=pages[-1])
        data = out.tobytes(garbage=3, deflate=True)
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def build_segments(raw_files: list[dict], texts: dict[int, str], starts: dict[int, list[int]]) -> list[dict]:
    """Đoạn = một giấy: {source, pages (0-based; None = cả tệp), file (tệp ảo cho planner), text}."""
    segments: list[dict] = []
    for index, file in enumerate(raw_files):
        text = texts.get(index)
        pages = split_pages(text) if text else []
        file_starts = starts.get(index) or [0]
        raw = _pdf_bytes(file) if len(file_starts) > 1 else None
        count = None
        if raw is not None:
            with fitz.open(stream=raw, filetype="pdf") as doc:
                count = doc.page_count
        if raw is None or count != len(pages):
            # Không tách được (ảnh, một giấy, số trang OCR lệch PDF) → nguyên tệp.
            segments.append({"source": index, "pages": None, "file": file, "text": text})
            continue
        stem = Path(str(file.get("name") or f"file-{index + 1}")).stem
        for first, end in zip(file_starts, [*file_starts[1:], count]):
            part = list(range(first, end))
            label = f"{first + 1}" if len(part) == 1 else f"{first + 1}-{end}"
            segments.append({
                "source": index,
                "pages": part,
                "file": {**file, "name": f"{stem}_trang_{label}.pdf", "type": "application/pdf",
                         "dataUrl": _cut_pdf(raw, part)},
                "text": _join_pages(pages[first:end]),
            })
    return segments


def _on_source(item: dict, segment: dict) -> dict:
    out = {k: v for k, v in item.items() if k not in ("sourceSegments", "sourceFileIndexes")}
    out["fileIndex"] = segment["source"]
    if segment["pages"] is not None:
        out["sourceSegments"] = [{"fileIndex": segment["source"], "pageIndexes": segment["pages"]}]
    return out


def remap_plan(attachments: list[dict], segments: list[dict]) -> list[dict]:
    """Kế hoạch trên tệp ảo (planner HKD trả đúng một mục mỗi tệp) → kế hoạch trên tệp gốc."""
    out: list[dict] = []
    used: set[int] = set()
    for item in attachments:
        try:
            v = int(item.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        if 0 <= v < len(segments):
            used.add(v)
            out.append(_on_source(item, segments[v]))
    for v, segment in enumerate(segments):
        if v not in used:
            # Không bỏ giấy nào: đoạn planner không trả mục → loại "Khác" của cổng.
            out.append(_on_source({
                "fileIndex": v,
                "fileName": segment["file"].get("name"),
                "documentName": "Giấy tờ khác",
                "componentName": "Khác",
                "target": "new",
                "needsAddComponent": False,
                "detectedType": "Khác",
                "category": "OTHERS",
            }, segment))
    return out


async def plan_with_split(plan_fn, files: list[FileItem], options: dict | None = None,
                          session: dict | None = None, *, doc_hints: str = "") -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl, "role": f.role} for f in files]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(raw_files)
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts = {i: str(r.get("text") or "") for i, r in enumerate(ocr_results)
             if not r.get("error") and str(r.get("text") or "").strip()}
    pages_by_file = {i: split_pages(t) for i, t in texts.items() if len(split_pages(t)) > 1}

    errors: list[str] = []
    started = time.monotonic()
    starts: dict[int, list[int]] = {}
    try:
        if pages_by_file:
            starts = await _segment(pages_by_file, doc_hints)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì planner chạy trên tệp gốc
        errors.append(f"Tách giấy tờ: {exc} — đính nguyên tệp.")
    split_ms = int((time.monotonic() - started) * 1000)

    segments = build_segments(raw_files, texts, starts)
    virtual = [FileItem(**seg["file"]) for seg in segments]
    with ocr.preset_texts({seg["file"]["dataUrl"]: seg["text"] for seg in segments if seg["text"]}):
        result = await plan_fn(virtual, options, session)

    result["attachments"] = remap_plan(result.get("attachments") or [], segments)
    result["errors"] = [*errors, *(result.get("errors") or [])]
    result["extracted"] = {
        **(result.get("extracted") or {}),
        "tachGiayTo": [
            {"fileName": raw_files[seg["source"]]["name"],
             "pages": "cả tệp" if seg["pages"] is None else [p + 1 for p in seg["pages"]]}
            for seg in segments
        ],
    }
    stats = dict(result.get("stats") or {})
    stats["ocr_latency_ms"] = int(stats.get("ocr_latency_ms") or 0) + ocr_ms
    stats["llm_latency_ms"] = int(stats.get("llm_latency_ms") or 0) + split_ms
    stats["total_latency_ms"] = int(stats.get("total_latency_ms") or 0) + ocr_ms + split_ms
    result["stats"] = stats
    return result
