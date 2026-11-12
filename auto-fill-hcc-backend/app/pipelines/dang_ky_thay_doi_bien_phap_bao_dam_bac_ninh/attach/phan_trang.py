"""Đọc bộ hồ sơ theo TRANG cho 1.011442 Bắc Ninh — dùng chung cho chế độ tách và không tách.

Hồ sơ mẫu là MỘT PDF scan 35 trang (Phiếu 02a hai bản, HĐ sửa đổi + lời chứng, HĐ thế chấp gốc, Giấy giới thiệu, GCN +
trang bổ sung, ba văn bản của ngân hàng). Phân loại cả tệp bằng vài nghìn chữ đầu thì sót các giấy phía sau, nên:

1. OCR song song: PDF dài cắt tối đa ``_OCR_MAX_PARTS`` phần gửi đồng thời (OCR một request ~3,5 s/trang, extension
   cắt request ở 100 s), ghép lại và ĐÁNH LẠI số trang "Trang i/n" theo tệp gốc.
2. LLM đọc đầu từng trang trong MỘT lượt, trả trang MỞ mỗi giấy + loại giấy. Giấy kéo dài tới trang mở giấy kế tiếp
   nên không sót / chồng trang.
3. LLM lỗi → đọc tiêu đề đầu trang bằng từ khoá (``keyword_documents``).
"""

import asyncio
import base64
import json
import math
import re
import unicodedata

from app.config import settings
from app.services.llm import client

from . import catalog

OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_OCR_MAX_PARTS = 6
_OCR_MIN_PAGES_PER_PART = 6
_PAGE_HEADER_RE = re.compile(r"(?im)^([\t ─-╿-]*)(trang|page)\s+(\d+)\s*/\s*(\d+)")
_PAGE_SPLIT_RE = re.compile(r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$")
# Trang trắng / mặt sau: OCR chỉ ra vài chữ rác → không được mở giấy mới.
_MIN_PAGE_CHARS = 40
_PAGE_HEAD_CHARS = 700


def fold(text) -> str:
    t = str(text or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


# ── 1. OCR song song ──

def _split_pdf(file: dict) -> list[tuple[int, dict]] | None:
    """PDF dài → [(trang đầu 0-based, phần)]; None = OCR nguyên tệp (ảnh, PDF ngắn, đọc lỗi)."""
    header, sep, b64 = str(file.get("dataUrl") or "").partition(",")
    if not sep or "pdf" not in header.lower():
        return None
    try:
        import fitz  # pymupdf

        src = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
    except Exception:  # noqa: BLE001
        return None
    try:
        pages = src.page_count
        parts = min(_OCR_MAX_PARTS, pages // _OCR_MIN_PAGES_PER_PART)
        if parts < 2:
            return None
        size = math.ceil(pages / parts)
        chunks = []
        for start in range(0, pages, size):
            out = fitz.open()
            try:
                out.insert_pdf(src, from_page=start, to_page=min(start + size, pages) - 1)
                # no_new_id: bytes cố định giữa các lần cắt → lượt điền và lượt đính kèm trúng cùng cache OCR.
                data = base64.b64encode(out.tobytes(no_new_id=True)).decode("ascii")
            finally:
                out.close()
            chunks.append((start, {**file, "name": f"{file.get('name')}#trang{start + 1}", "dataUrl": f"{header},{data}"}))
        return chunks
    finally:
        src.close()


def renumber_pages(text: str, offset: int, total: int) -> str:
    """Header "Trang i/n" của MỘT phần → số trang trên tệp gốc. Phần không có header → coi là một trang."""
    if not _PAGE_HEADER_RE.search(text or ""):
        return f"───── Trang {offset + 1}/{total} ─────\n{text or ''}"
    return _PAGE_HEADER_RE.sub(lambda m: f"{m.group(1)}{m.group(2)} {int(m.group(3)) + offset}/{total}", text)


async def ocr_files(files: list[dict]) -> list[dict]:
    """Thay ``ocr.ocr_per_file``: cùng đầu vào/đầu ra, PDF dài OCR song song theo phần (mỗi phần vẫn qua cache)."""
    from app.services import ocr

    split = [_split_pdf(f) for f in files]
    whole = [f for f, chunks in zip(files, split) if chunks is None]
    jobs = [ocr.ocr_per_file(whole)] if whole else []
    jobs += [ocr.ocr_per_file([chunk]) for chunks in split if chunks for _, chunk in chunks]
    done = iter(await asyncio.gather(*jobs))
    whole_results = iter(next(done) if whole else [])

    results: list[dict] = []
    for f, chunks in zip(files, split):
        if chunks is None:
            results.append(next(whole_results))
            continue
        total = 0
        try:
            import fitz  # pymupdf

            with fitz.open(stream=base64.b64decode(str(f.get("dataUrl")).partition(",")[2]), filetype="pdf") as doc:
                total = doc.page_count
        except Exception:  # noqa: BLE001
            total = 0
        parts = [(start, next(done)[0]) for start, _ in chunks]
        errors = [p["error"] for _, p in parts if p.get("error")]
        item = {
            "name": f.get("name"),
            "type": f.get("type"),
            "text": "\n".join(renumber_pages(str(p.get("text") or ""), start, total) for start, p in parts).strip(),
            "provider": (parts[0][1].get("provider") if parts else None) or "tiengnoi",
        }
        if errors:
            item["error"] = "; ".join(errors)
        results.append(item)
    return results


def split_pages(text: str) -> list[str]:
    """Text OCR theo trang (header "───── Trang i/n ─────"). Không có header → 1 trang."""
    matches = list(_PAGE_SPLIT_RE.finditer(text or ""))
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


def is_blank(page: str) -> bool:
    return len(re.findall(r"\w", page or "")) < _MIN_PAGE_CHARS


# ── 2. LLM chia giấy theo trang ──

SEGMENT_SYSTEM_PROMPT = f"""
<persona>
Bạn chia bộ hồ sơ scan của thủ tục "Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với
đất" (cổng dịch vụ công tỉnh Bắc Ninh) thành từng GIẤY TỜ và gán loại cho mỗi giấy. Mỗi tệp gồm các trang theo thứ tự,
mỗi trang kèm phần đầu chữ OCR.
</persona>

<loai_giay>
{catalog.llm_options()}
</loai_giay>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy. Mỗi giấy kéo dài tới trước trang mở giấy kế tiếp.
2. Trang MỞ GIẤY MỚI khi là trang đầu của văn bản KHÁC: có quốc hiệu / tên cơ quan ban hành và tiêu đề riêng (PHIẾU
   YÊU CẦU, HỢP ĐỒNG, GIẤY GIỚI THIỆU, GIẤY ỦY QUYỀN, QUYẾT ĐỊNH, công văn "Số: …/…" kèm "Về …", GIẤY CHỨNG NHẬN...),
   là thẻ căn cước, hoặc cùng loại nhưng khác số hiệu / là BẢN THỨ HAI của cùng phiếu.
3. Trang tiếp của cùng văn bản KHÔNG mở giấy mới: trang mở đầu bằng số trang ("2", "3"…), số điều/mục ("Điều 2",
   "6. Cách thức nhận kết quả"), phần chữ ký, "Nơi nhận", chân trang "MẪU SỐ …" lặp lại.
4. "LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN" là phần cuối của HỢP ĐỒNG liền trước → CÙNG giấy với hợp đồng đó, không mở giấy mới.
5. Giấy chứng nhận quyền sử dụng đất gồm nhiều trang (trang có "Nội dung thay đổi và cơ sở pháp lý", "II. Thửa đất,
   nhà ở…", sơ đồ thửa, "TRANG BỔ SUNG GIẤY CHỨNG NHẬN") → MỘT giấy loại gcn.
6. Hợp đồng SỬA ĐỔI, BỔ SUNG hợp đồng thế chấp → hd_sua_doi; hợp đồng thế chấp GỐC (tiêu đề "HỢP ĐỒNG THẾ CHẤP…",
   không có chữ "sửa đổi, bổ sung") → hop_dong_the_chap.
7. Công văn / quyết định của ngân hàng về đổi tên, chấm dứt hoạt động, sắp xếp mạng lưới, thay đổi địa điểm (căn cứ
   cho việc thay đổi bên nhận bảo đảm) → vb_can_cu_khac; quyết định GIAO NHIỆM VỤ cho chi nhánh thực hiện đăng ký →
   vb_giao_nhiem_vu.
8. Mặt trước + mặt sau CCCD của cùng một người là MỘT giấy. Trang trắng / chỉ vài chữ rời rạc thuộc giấy liền trước.
9. Không chắc có phải giấy mới không → KHÔNG tách. Không chắc loại → "khac".
10. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

<output_contract>
{{"giayTo":[{{"fileIndex":0,"trangDau":1,"loai":"phieu_02a","ten":"Phiếu yêu cầu đăng ký thay đổi"}},
{{"fileIndex":0,"trangDau":5,"loai":"hd_sua_doi","ten":"Hợp đồng sửa đổi, bổ sung hợp đồng thế chấp"}}]}}
"trangDau" đếm từ 1 trong tệp; "loai" là đúng một nhãn trong <loai_giay>; "ten" là tên tiếng Việt ngắn (≤ 50 ký tự),
cụ thể theo nội dung (vd thêm số hiệu văn bản), hai giấy khác nhau không trùng tên.
</output_contract>
""".strip()


def _page_head(page: str) -> str:
    if is_blank(page):
        return "(trang trắng / mặt sau, không có nội dung)"
    return re.sub(r"\s+", " ", page).strip()[:_PAGE_HEAD_CHARS]


def build_segment_user_prompt(pages_by_file: dict[int, list[str]]) -> str:
    payload = [
        {"fileIndex": i, "soTrang": len(pages), "trang": [{"trang": n + 1, "ocr": _page_head(t)} for n, t in enumerate(pages)]}
        for i, pages in pages_by_file.items()
    ]
    return "HỒ SƠ:\n" + json.dumps(payload, ensure_ascii=False)


def documents_from_starts(pages_by_file: dict[int, list[str]], starts: list[dict]) -> list[dict]:
    """[{fileIndex, trangDau, loai, ten}] → giấy {fileIndex, pages (0-based), label, name}; phủ đủ mọi trang.

    Trang 1 luôn mở giấy (thiếu thì giấy đầu kéo về trang 1); trang mở giấy là trang trắng / ngoài tệp bị bỏ."""
    by_file: dict[int, dict[int, dict]] = {}
    for item in starts:
        if not isinstance(item, dict):
            continue
        try:
            file_index = int(item.get("fileIndex"))
            page = int(item.get("trangDau")) - 1
        except (TypeError, ValueError):
            continue
        pages = pages_by_file.get(file_index)
        if not pages or not 0 <= page < len(pages):
            continue
        if page > 0 and is_blank(pages[page]):
            continue
        by_file.setdefault(file_index, {}).setdefault(page, {
            "label": catalog.normalize(item.get("loai")),
            "name": " ".join(str(item.get("ten") or "").split())[:60],
        })
    documents: list[dict] = []
    for file_index, pages in pages_by_file.items():
        marks = by_file.get(file_index) or {}
        if marks and 0 not in marks:
            first = min(marks)
            marks = {0: marks.pop(first), **marks}
        if not marks:
            marks = {0: {"label": "khac", "name": ""}}
        order = sorted(marks)
        for first, end in zip(order, [*order[1:], len(pages)]):
            documents.append({"fileIndex": file_index, "pages": list(range(first, end)), **marks[first]})
    return documents


async def segment_documents(pages_by_file: dict[int, list[str]]) -> list[dict]:
    """Một lượt LLM chia + gán loại cho mọi giấy của mọi tệp. Lỗi (JSON hỏng hai lần / rỗng) → raise."""
    messages = [
        {"role": "system", "content": SEGMENT_SYSTEM_PROMPT},
        {"role": "user", "content": build_segment_user_prompt(pages_by_file)},
    ]
    total = sum(len(p) for p in pages_by_file.values())
    starts: list = []
    for attempt in range(2):  # JSON hỏng → hỏi lại một lần
        raw = await client.chat(messages, temperature=0, max_tokens=max(400, min(3000, 200 + 60 * total)),
                                enable_thinking=settings.agent_reasoning)
        try:
            starts = client.extract_json_block(raw).get("giayTo") or []
        except Exception:  # noqa: BLE001
            if attempt:
                raise
            continue
        if starts:
            break
    if not starts:
        raise ValueError("LLM không trả giấy tờ nào")
    return documents_from_starts(pages_by_file, starts)


# ── 3. Dự phòng: tiêu đề đầu trang ──

def keyword_page_label(page: str) -> str | None:
    """Nhãn nếu ĐẦU trang là tiêu đề mở một giấy; None = trang tiếp của giấy trước."""
    h = fold(page)[:450]
    if not h or is_blank(page):
        return None
    if "loi chung cua cong chung vien" in h:
        return None
    if "phieu yeu cau dang ky thay doi" in h:
        return "phieu_02a"
    if "hop dong sua doi" in h and "bo sung" in h:
        return "hd_sua_doi"
    if "chuyen giao quyen doi no" in h:
        return "vb_chuyen_giao"
    if "trang bo sung giay chung nhan" in h or "giay chung nhan quyen su dung dat" in h:
        return "gcn"
    if "hop dong the chap" in h:
        return "hop_dong_the_chap"
    if "giay gioi thieu" in h or "giay uy quyen" in h or "van ban uy quyen" in h or "hop dong uy quyen" in h:
        return "van_ban_dai_dien"
    if "giay chung nhan dang ky doanh nghiep" in h or "giay chung nhan dang ky hoat dong chi nhanh" in h:
        return "gcn_dkdn"
    if "danh muc" in h and ("01d" in h or "02d" in h):
        return "danh_muc_01d"
    if any(m in h for m in ("can cuoc cong dan", "citizen identity", "chung minh nhan dan", "idvnm")):
        return "cccd"
    if "quyet dinh" in h or re.search(r"so:?\s*\d+\s*/\s*[a-z]", h):
        return "vb_can_cu_khac"
    return None


def keyword_label_by_filename(name: str) -> str:
    h = fold(name)
    if any(k in h for k in ("cccd", "can cuoc", "cmnd")):
        return "cccd"
    if "phieu" in h or "02a" in h:
        return "phieu_02a"
    if "sua doi" in h or "bo sung" in h:
        return "hd_sua_doi"
    if "the chap" in h:
        return "hop_dong_the_chap"
    if "gioi thieu" in h or "uy quyen" in h:
        return "van_ban_dai_dien"
    if any(k in h for k in ("gcn", "so do", "so hong", "chung nhan")):
        return "gcn"
    return "khac"


def keyword_documents(pages_by_file: dict[int, list[str]], names: dict[int, str] | None = None) -> list[dict]:
    starts: list[dict] = []
    for file_index, pages in pages_by_file.items():
        for n, page in enumerate(pages):
            label = keyword_page_label(page)
            if label is None and n == 0:
                label = keyword_label_by_filename((names or {}).get(file_index, ""))
            if label is not None:
                starts.append({"fileIndex": file_index, "trangDau": n + 1, "loai": label, "ten": ""})
    return documents_from_starts(pages_by_file, starts)


async def read_documents(raw_files: list[dict]) -> tuple[dict[int, list[str]], list[dict], list[str], dict]:
    """OCR + chia giấy cho mọi tệp → (trang theo tệp, giấy, lỗi, thống kê). Tệp không OCR được → một giấy nhãn theo
    tên tệp. ``documents[*]["source"]`` = "llm" | "keyword"."""
    import time

    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in OCR_TYPES]
    t0 = time.monotonic()
    results = await ocr_files([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        text = str(result.get("text") or "")
        if text.strip():
            pages_by_file[index] = split_pages(text)

    names = {i: str(f.get("name") or "") for i, f in enumerate(raw_files)}
    t1 = time.monotonic()
    documents: list[dict] = []
    source = "llm"
    if pages_by_file:
        try:
            documents = await segment_documents(pages_by_file)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi thì đọc tiêu đề đầu trang
            errors.append(f"attachment_agent: {exc}")
            documents = keyword_documents(pages_by_file, names)
            source = "keyword"
    llm_ms = int((time.monotonic() - t1) * 1000)
    for doc in documents:
        doc["source"] = source
    for i, name in names.items():
        if i not in pages_by_file:
            documents.append({"fileIndex": i, "pages": None, "label": keyword_label_by_filename(name), "name": "",
                              "source": "filename"})
    documents.sort(key=lambda d: (d["fileIndex"], (d["pages"] or [0])[0]))
    stats = {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms}
    return pages_by_file, documents, errors, stats
