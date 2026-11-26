"""Đọc bộ hồ sơ theo TRANG cho 1.115462 Bắc Ninh — dùng chung cho chế độ tách và không tách.

Dùng lại OCR song song + cắt trang của 1.011442 cùng cổng (``ocr_files``, ``split_pages``, ``is_blank``); chỉ viết riêng
prompt chia giấy, bảng nhãn và từ khoá dự phòng:

1. OCR song song (PDF dài cắt tối đa 6 phần), đánh lại "Trang i/n" theo tệp gốc.
2. LLM đọc đầu từng trang trong MỘT lượt, trả trang MỞ mỗi giấy + loại giấy. Giấy kéo dài tới trang mở giấy kế tiếp
   nên không sót / chồng trang.
3. LLM lỗi → đọc tiêu đề đầu trang bằng từ khoá (``keyword_documents``).
"""

import json
import re

from app.config import settings
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_bac_ninh.attach.phan_trang import (
    OCR_TYPES,
    fold,
    is_blank,
    ocr_files,
    split_pages,
)
from app.services.llm import client

from . import catalog

__all__ = ["OCR_TYPES", "ocr_files", "split_pages", "is_blank", "read_documents"]

_PAGE_HEAD_CHARS = 700

SEGMENT_SYSTEM_PROMPT = f"""
<persona>
Bạn chia bộ hồ sơ scan của thủ tục "Xác nhận tiếp tục sử dụng đất nông nghiệp" (cổng dịch vụ công tỉnh Bắc Ninh) thành
từng GIẤY TỜ và gán loại cho mỗi giấy. Mỗi tệp gồm các trang theo thứ tự, mỗi trang kèm phần đầu chữ OCR.
</persona>

<loai_giay>
{catalog.llm_options()}
</loai_giay>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy. Mỗi giấy kéo dài tới trước trang mở giấy kế tiếp.
2. Trang MỞ GIẤY MỚI khi là trang đầu của văn bản KHÁC: có quốc hiệu / tên cơ quan ban hành và tiêu đề riêng (ĐƠN XIN
   XÁC NHẬN, GIẤY CHỨNG NHẬN, GIẤY ỦY QUYỀN, HỢP ĐỒNG...), là thẻ căn cước, hoặc cùng loại nhưng khác người / khác số
   hiệu.
3. Trang "II- XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ" ngay sau Đơn Mẫu 09 → CÙNG giấy don_09, không mở giấy mới.
4. Giấy chứng nhận gồm bìa đỏ ("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", số seri) + trang "CHỨNG NHẬN … Theo bảng liệt kê"
   / sơ đồ thửa / "Những thay đổi sau khi cấp" → MỘT giấy loại gcn.
5. Đơn NHẮC tới số phát hành / số vào sổ của giấy chứng nhận nhưng KHÔNG phải giấy chứng nhận → don_09.
6. Trang lời chứng chứng thực chữ ký ("Lời chứng chứng thực chữ ký…", "Mẫu số 05") ngay sau Giấy ủy quyền → CÙNG giấy
   uy_quyen, không mở giấy mới. Trang ký cuối văn bản → cùng giấy.
7. Mặt trước + mặt sau CCCD của cùng một người là MỘT giấy. Trang trắng / chỉ vài chữ rời rạc thuộc giấy liền trước.
8. Không chắc có phải giấy mới không → KHÔNG tách. Không chắc loại → "khac".
9. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

<output_contract>
{{"giayTo":[{{"fileIndex":0,"trangDau":1,"loai":"don_09","ten":"Đơn xin xác nhận tiếp tục sử dụng đất nông nghiệp"}},
{{"fileIndex":0,"trangDau":3,"loai":"gcn","ten":"Giấy chứng nhận quyền sử dụng đất"}}]}}
"trangDau" đếm từ 1 trong tệp; "loai" là đúng một nhãn trong <loai_giay>; "ten" là tên tiếng Việt ngắn (≤ 50 ký tự),
cụ thể theo nội dung, hai giấy khác nhau không trùng tên.
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


# ── Dự phòng: tiêu đề đầu trang ──

def keyword_page_label(page: str) -> str | None:
    """Nhãn nếu ĐẦU trang là tiêu đề mở một giấy; None = trang tiếp của giấy trước."""
    h = fold(page)[:450]
    if not h or is_blank(page):
        return None
    # Trang xác nhận UBND xã (thuộc Đơn) / lời chứng chứng thực (thuộc Giấy ủy quyền) không mở giấy mới.
    if any(m in h for m in ("xac nhan cua uy ban nhan dan", "loi chung chung thuc", "chung thuc chu ky")):
        return None
    if "don xin xac nhan" in h or "mau so 09" in h or "su dung dat nong nghiep" in h:
        return "don_09"
    if "giay uy quyen" in h or "van ban uy quyen" in h or "hop dong uy quyen" in h:
        return "uy_quyen"
    if "giay chung nhan" in h and "quyen su dung dat" in h:
        return "gcn"
    if any(m in h for m in ("can cuoc cong dan", "citizen identity", "identity card", "personal identification",
                            "chung minh nhan dan", "idvnm")):
        return "cccd"
    return None


def keyword_label_by_filename(name: str) -> str:
    h = fold(name)
    if any(k in h for k in ("cccd", "can cuoc", "cmnd")):
        return "cccd"
    if "uy quyen" in h:
        return "uy_quyen"
    if "don" in h.split() or "mau 09" in h or "mau so 09" in h:
        return "don_09"
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
    tên tệp. ``documents[*]["source"]`` = "llm" | "keyword" | "filename"."""
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
