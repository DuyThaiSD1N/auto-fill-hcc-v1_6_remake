"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp mới giấy phép hành nghề trong giai đoạn chuyển
tiếp..." (cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ có nhiều dòng (mục a–h); ta gán vào các dòng thường dùng:
  a) "Đơn theo Mẫu 08 Phụ lục I ..."                         ← Đơn đề nghị cấp GPHN.
  b) "... Văn bằng chuyên môn (không áp dụng ..."            ← Bản sao văn bằng chuyên môn (bằng tốt nghiệp).
  d) "... giấy khám sức khỏe do cơ sở khám bệnh ..."         ← Giấy khám sức khỏe.
  e) "Sơ yếu lý lịch tự thuật của người hành nghề ..."       ← Sơ yếu lý lịch (Mẫu 09).
  g) "... giấy xác nhận hoàn thành quá trình thực hành ..."  ← Giấy xác nhận thực hành (Mẫu 07).
  h) "02 ảnh chân dung cỡ 04 cm ..."                         ← 02 ảnh chân dung 4x6.
(Mục c văn bằng chuyên khoa / đ tiếng Việt — trường hợp hiếm, chưa gán tự động.)
FE khớp dòng bằng TÊN giấy tờ (componentName, substring fold), tick checkbox + chọn loaiBan + set file.
Ta upload bản SCAN → loaiBan = "Scan tệp tin".

Phân loại bằng LLM — mọi dấu hiệu (kể cả dấu hiệu nhận ảnh chân dung) nằm trong prompt, KHÔNG có rule
keyword xếp loại trong code: OCR của cùng một tệp ra khác nhau giữa các lần chạy (watermark app scan,
mốc trang, chữ vụn), rule cứng khớp được lần này thì trượt lần sau. Mỗi tệp một lượt gọi riêng để kết
quả của tệp này không phụ thuộc thứ tự hay số lượng tệp khác, và không phải tin chỉ số LLM trả về.

Lưới an toàn ảnh chân dung (``_looks_like_portrait``): LLM vẫn có lúc trả other cho tệp ảnh 2 trang mà OCR chỉ
đọc ra vài chữ vụn từ nền ảnh (vd vài chữ in hoa + một dãy số có gạch nối) → ảnh rơi vào dòng Đơn kèm cảnh báo
"Chưa nhận ra loại giấy tờ". Lưới CHỈ chạy khi LLM đã trả other / lỗi và OCR của tệp chạy được: bỏ mốc trang +
watermark app scan, mọi trang còn dưới _PORTRAIT_MAX_PAGE_CHARS chữ/số → ảnh chân dung (mọi giấy khác của thủ tục
đều có tiêu đề và nhiều dòng chữ — đúng quy tắc prompt đã ghi). OCR lỗi thì không đoán, vẫn vào dòng Đơn.

⚑ KHÔNG BỎ SÓT TỆP: tệp LLM không xếp được (other) hoặc lượt gọi lỗi → đính vào dòng Đơn (tờ khai),
giữ nguyên tên tệp gốc để cán bộ nhận ra. attp-row gộp nhiều tệp vào cùng một dòng theo componentName.
CCCD (thẻ thật) KHÔNG có dòng riêng trên bảng nhưng người dân vẫn nộp kèm (đơn Mẫu 08 liệt kê "Căn cước
công dân công chứng") → cũng dồn vào dòng Đơn, đặt tên "Bản sao Căn cước công dân". Bản cũ bỏ qua CCCD
nên hồ sơ trace req_8328e84774f7 chỉ đính 5/6 tệp.

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments``): tệp PDF nhiều trang được LLM xếp loại TỪNG
TRANG và đánh dấu trang mở đầu giấy mới (kèm tiêu đề in trên giấy); mỗi giấy thành một tệp riêng chỉ gồm đúng các
trang của nó (``sourceSegments``, extension cắt PDF) vào dòng của loại đó. Chia theo giấy, không theo loại: hai văn
bằng khác nhau, hay giấy xác nhận thực hành và quyết định đi kèm, là các tệp riêng (cùng dòng nếu cùng loại), tên tệp
= tiêu đề giấy. Không bỏ trang nào (ảnh chân dung không có chữ, bỏ trang ít chữ là mất ảnh). Tệp một trang, tệp không
có chữ, số trang OCR lệch PDF, hoặc LLM trả lệch số trang → phân loại cả tệp như chế độ thường. TẮT / extension cũ
không gửi cờ → hành vi cũ.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.lao_cai_tach_giay_to import split_pages
from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.attach import prompt
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested, splittable_pages
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"
# Trang LLM trả other mà ít chữ (mặt sau in xuyên, trang chỉ có dấu/chức danh) là trang nối tiếp của giấy liền trước.
_SHORT_OTHER_CHARS = 200
# Cổng BYT cắt / từ chối tên tệp từ 50 ký tự (tính cả đuôi ".pdf").
_TITLE_MAX = 45
# Lưới an toàn ảnh chân dung: trang còn dưới số chữ/số này VÀ không quá số từ này sau khi bỏ mốc trang + watermark
# app scan là trang không có câu chữ (vài mẩu vụn); một câu ngắn có nghĩa đã vượt số từ.
_PORTRAIT_MAX_PAGE_CHARS = 40
_PORTRAIT_MAX_PAGE_WORDS = 5
_SCAN_NOISE_RE = re.compile(
    r"scanned\s+with|cam\s*scanner|\bcs\b|left\s+image|right\s+image|\bimage\b|trang\s*\d+\s*/\s*\d+",
    re.IGNORECASE,
)

_DON = "don_de_nghi"          # mục a
_VANBANG = "van_bang"         # mục b
_SUCKHOE = "suc_khoe"         # mục d
_SYLL = "so_yeu_ly_lich"      # mục e
_THUCHANH = "thuc_hanh"       # mục g
_ANH = "anh_chan_dung"        # mục h
_CCCD = "cccd"
_OTHER = "other"

# Mỗi loại giấy tờ → 1 dòng (mục a–h). componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp
# substring fold vào tên dòng lấy từ DOM). loaiBan = "Scan tệp tin" (đều là file scan/PDF).
_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn theo Mẫu 08 Phụ lục I",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đề nghị cấp giấy phép hành nghề (Mẫu 08 PL I NĐ 96/2023)",
    },
    _VANBANG: {
        "componentName": "Văn bằng chuyên môn",  # mục b — bản sao văn bằng chuyên môn.
        "loaiBan": _LOAI_BAN,
        "documentName": "Bản sao văn bằng chuyên môn (bằng tốt nghiệp/cử nhân)",
    },
    _SUCKHOE: {
        "componentName": "giấy khám sức khỏe do cơ sở khám bệnh",  # mục d.
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy khám sức khỏe",
    },
    _SYLL: {
        "componentName": "Sơ yếu lý lịch tự thuật của người hành nghề",
        "loaiBan": _LOAI_BAN,
        "documentName": "Sơ yếu lý lịch tự thuật của người hành nghề (Mẫu 09 PL I)",
    },
    _THUCHANH: {
        "componentName": "giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07",  # mục g.
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 PL I)",
    },
    _ANH: {
        "componentName": "02 ảnh chân dung cỡ 04 cm",  # mục h.
        "loaiBan": _LOAI_BAN,
        "documentName": "02 ảnh chân dung 4x6 nền trắng",
    },
}
# CCCD KHÔNG có dòng riêng trên bảng thành phần hồ sơ → dồn vào dòng Đơn với tên này (đã nhận đúng loại
# nên không cần cảnh báo như tệp other).
_CCCD_DOCUMENT_NAME = "Bản sao Căn cước công dân"
_ALLOWED_DOC_TYPES = set(_ROWS) | {_CCCD, _OTHER}


def _canon(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "_", _fold(str(value or ""))).strip("_")


def _normalize_doc_type(value: Any) -> str:
    """Khớp ĐÚNG nhãn trong allowed_types. Nhãn lạ → other.

    Không khớp chuỗi con: bản cũ dò `"anh" in text` nên nhãn "thuc_hanh" (chứa "anh") bị đổi thành
    anh_chan_dung — giấy xác nhận thực hành bị lái sang dòng ảnh.
    """
    canon = _canon(value)
    return next((doc_type for doc_type in _ALLOWED_DOC_TYPES if _canon(doc_type) == canon), _OTHER)


async def _classify_one(index: int, file_name: str, text: str) -> tuple[int, str]:
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(file_name, text)},
    ]
    # temperature 0: cùng tệp phải ra cùng loại giữa các lần chạy (ảnh chân dung từng lúc ra other lúc ra ảnh).
    raw = await client.chat(messages, temperature=0, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), None) or parsed
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    """Một lượt gọi cho MỖI tệp — lỗi của tệp này không kéo theo tệp khác."""
    if not documents:
        return {}
    outcomes = await asyncio.gather(
        *(_classify_one(d["index"], d["name"], d["text"]) for d in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document['name']}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


async def _classify_pages(pages_by_file: dict[int, list[str]]) -> dict[int, list[dict]]:
    """LLM xếp loại TỪNG TRANG + đánh dấu trang mở đầu giấy mới → {tệp: [giấy gồm các trang liền nhau]}."""
    total = sum(len(p) for p in pages_by_file.values())
    messages = [
        {"role": "system", "content": prompt.SPLIT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_split_user_prompt(pages_by_file)},
    ]
    # temperature 0: cùng tệp phải ra cùng cách chia giữa các lần chạy.
    raw = await client.chat(messages, temperature=0, max_tokens=max(400, min(3000, 150 + 40 * total)),
                            enable_thinking=settings.agent_reasoning)
    out: dict[int, list[dict]] = {}
    for item in client.extract_json_block(raw).get("tep", []) or []:
        try:
            idx = int(item.get("fileIndex"))
        except Exception:  # noqa: BLE001
            continue
        if idx in pages_by_file and idx not in out:
            docs = _parse_docs(item.get("trang"), len(pages_by_file[idx]))
            # Lệch số trang → không biết trang nào thuộc giấy nào, tệp đó phân loại cả tệp như chế độ thường.
            if docs:
                out[idx] = docs
    return out


def _parse_docs(raw_pages: Any, page_count: int) -> list[dict] | None:
    """Kết quả từng trang (loại + cờ giấy mới) → các giấy liền nhau, trang 0-based. Thiếu/thừa/lệch số trang → None.

    Giấy mới bắt đầu khi LLM đánh giayMoi hoặc khi loại đổi so với trang trước."""
    if not isinstance(raw_pages, list) or len(raw_pages) != page_count:
        return None
    docs: list[dict] = []
    for page, raw in enumerate(raw_pages):
        if not isinstance(raw, dict):
            return None
        try:
            if int(raw.get("trang", page + 1)) != page + 1:
                return None
        except Exception:  # noqa: BLE001
            return None
        doc_type = _normalize_doc_type(raw.get("docType"))
        if not docs or raw.get("giayMoi") is True or docs[-1]["docType"] != doc_type:
            docs.append({"docType": doc_type, "pages": [page], "title": raw.get("tenGiay")})
        else:
            docs[-1]["pages"].append(page)
    return docs


def _textless_page(page: str) -> bool:
    """Trang không có câu chữ: bỏ watermark app scan / nhãn ảnh / mốc trang, còn dưới _PORTRAIT_MAX_PAGE_CHARS chữ/số
    và không quá _PORTRAIT_MAX_PAGE_WORDS từ."""
    rest = _SCAN_NOISE_RE.sub(" ", page or "")
    return (len(re.findall(r"\w", rest)) < _PORTRAIT_MAX_PAGE_CHARS
            and len(re.findall(r"\w+", rest)) <= _PORTRAIT_MAX_PAGE_WORDS)


def _looks_like_portrait(text: str) -> bool:
    """Mọi trang OCR của tệp đều không có câu chữ → ảnh chân dung (chỉ dùng khi LLM đã trả other / lỗi)."""
    return all(_textless_page(page) for page in split_pages(text or ""))


def _merge_short_other(docs: list[dict], pages: list[str]) -> list[dict]:
    """Giấy other mà mọi trang đều ít chữ (mặt sau in xuyên, trang chỉ có dấu/chức danh) là phần nối của giấy
    liền trước, không thành tệp riêng."""
    out: list[dict] = []
    for doc in docs:
        short = all(len(re.findall(r"\w", pages[p] or "")) < _SHORT_OTHER_CHARS for p in doc["pages"])
        if doc["docType"] == _OTHER and short and out:
            out[-1] = {**out[-1], "pages": out[-1]["pages"] + doc["pages"]}
        else:
            out.append(doc)
    return out


def _clip_title(value: Any) -> str:
    text = " ".join(re.sub(r"[()\[\]{}.]", " ", str(value or "")).split()).strip(" -,;:")
    if len(text) > _TITLE_MAX:
        text = text[:_TITLE_MAX].rsplit(" ", 1)[0]
    return text


def _doc_title(value: Any, fallback: str) -> str:
    """Tiêu đề LLM đọc trên giấy làm tên tệp: bỏ ngoặc/dấu chấm, ≤ _TITLE_MAX ký tự; trống → tên mặc định của dòng
    (cũng cắt cho vừa)."""
    return _clip_title(value) or _clip_title(fallback)


def _split_file_items(file: dict, idx: int, pages: list[str], docs: list[dict]) -> tuple[list[dict], str, dict]:
    """Tệp đã chia theo giấy → MỖI GIẤY một mục chỉ gồm đúng các trang của nó (hai giấy cùng loại là hai tệp trong
    cùng dòng), xếp theo thứ tự dòng a–h; CCCD và giấy chưa rõ loại vào dòng Đơn như chế độ thường."""
    file_name = str(file.get("name") or f"file-{idx + 1}")
    # Giấy other ĐỨNG ĐẦU tệp mà mọi trang không có câu chữ là ảnh chân dung (prompt tách quy tắc 4); không có giấy
    # liền trước để nối vào nên nếu để other thì ảnh rơi vào dòng Đơn.
    if docs and docs[0]["docType"] == _OTHER and all(_textless_page(pages[p]) for p in docs[0]["pages"]):
        docs = [{**docs[0], "docType": _ANH}, *docs[1:]]
    docs = _merge_short_other(docs, pages)
    row_order = list(_ROWS)
    order = sorted(docs, key=lambda d: (row_order.index(d["docType"]) if d["docType"] in _ROWS else len(row_order),
                                        d["pages"][0]))
    items: list[dict] = []
    seen_names: dict[tuple[str, str], int] = {}
    for doc in order:
        doc_type = doc["docType"]
        if doc_type in _ROWS:
            item = _build_row_item(file, idx, doc_type)
        else:
            item = _build_row_item(file, idx, _DON, detected_type=doc_type)
        name = _doc_title(doc["title"], item["documentName"])
        # Hai giấy cùng tiêu đề trong một dòng → đánh số để cán bộ và bộ chống trùng của extension phân biệt.
        key = (item["componentName"], name.casefold())
        seen_names[key] = seen_names.get(key, 0) + 1
        item["documentName"] = name if seen_names[key] == 1 else f"{name} {seen_names[key]}"
        if len(docs) > 1:
            item["sourceSegments"] = [{"fileIndex": idx, "pageIndexes": doc["pages"]}]
        items.append(item)
    entry = {"fileName": file_name, "docType": ",".join(d["docType"] for d in docs), "source": "llm-pages",
             "tachGiayTo": [{"docType": d["docType"], "pages": [p + 1 for p in d["pages"]],
                             "tenGiay": d.get("title")} for d in docs]}
    warning = ""
    if any(d["docType"] == _OTHER for d in docs):
        warning = (f"Chưa nhận ra loại giấy tờ của một số trang trong tệp '{file_name}' — đã đính vào dòng Đơn "
                   "(mục a), cán bộ kiểm tra lại.")
    return items, warning, entry


def _build_row_item(file: dict, file_index: int, doc_type: str, *, detected_type: str | None = None) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        # Tệp dồn vào dòng Đơn giữ TÊN GỐC: engine attp-row đặt tên tệp theo documentName, đặt tên
        # "Đơn đề nghị…" cho một tệp lạ là cán bộ không phân biệt được hai tệp cùng dòng.
        "documentName": (
            file_name if detected_type == _OTHER
            else _CCCD_DOCUMENT_NAME if detected_type == _CCCD
            else row["documentName"]
        ),
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": detected_type or doc_type,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    page_types: dict[int, list[dict]] | None = None,
    pages_by_file: dict[int, list[str]] | None = None,
    ocr_texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """``ocr_texts``: chữ OCR của các tệp OCR chạy được (tệp OCR lỗi không có mặt) — cho lưới an toàn ảnh chân dung."""
    llm_types = llm_types or {}
    page_types = page_types or {}
    pages_by_file = pages_by_file or {}
    ocr_texts = ocr_texts or {}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    fallback: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        if idx in page_types and idx in pages_by_file:
            split_items, warning, entry = _split_file_items(file, idx, pages_by_file[idx], page_types[idx])
            items.extend(split_items)
            warnings.extend([warning] if warning else [])
            classified.append(entry)
            continue
        doc_type = llm_types.get(idx, _OTHER)
        source = "llm" if idx in llm_types else "fallback"
        if doc_type == _OTHER and idx in ocr_texts and _looks_like_portrait(ocr_texts[idx]):
            doc_type, source = _ANH, "textless"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type == _CCCD:
            items.append(_build_row_item(file, idx, _DON, detected_type=_CCCD))
            classified.append({"fileName": file_name, "docType": _CCCD, "source": source, "fallbackRow": _DON})
            continue

        # Không xếp được loại → dồn vào dòng Đơn chứ KHÔNG bỏ: bảng không có dòng "giấy tờ khác", mà
        # bỏ tệp là hồ sơ thiếu giấy người dân đã đưa.
        items.append(_build_row_item(file, idx, _DON, detected_type=_OTHER))
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "fallbackRow": _DON})
        fallback.append(file_name)

    if fallback:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm chung vào dòng Đơn (mục a) để không bỏ sót — cán bộ "
            f"kiểm tra lại: {', '.join(fallback)}."
        )
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = session
    split = split_requested(options)
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    # Gửi MỌI tệp cho LLM, kể cả tệp OCR RỖNG: ảnh chân dung thường không có chữ nào, bỏ qua tệp rỗng
    # là để tệp ảnh không bao giờ được xếp loại.
    texts = {
        idx: str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        for idx, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    }

    t1 = time.monotonic()
    pages_by_file: dict[int, list[str]] = {}
    page_types: dict[int, list[dict]] = {}
    if split:
        # Chỉ tệp NHIỀU trang mới có thể gộp nhiều giấy; tệp một trang giữ phân loại cả tệp (nhận ảnh chân dung).
        pages_by_file = {
            idx: pages for idx, text in texts.items()
            if len(pages := splittable_pages(raw_files[idx], text)) > 1
        }
        if pages_by_file:
            try:
                page_types = await _classify_pages(pages_by_file)
            except Exception as exc:  # noqa: BLE001 — chia trang hỏng thì phân loại cả tệp
                errors.append(f"Tách giấy tờ: {exc} — đính nguyên tệp.")
    llm_docs = [
        {"index": idx, "name": str(raw_files[idx].get("name") or ""), "text": text}
        for idx, text in texts.items()
        if idx not in page_types
    ]
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    # Tệp OCR lỗi không đưa vào lưới ảnh chân dung: chữ rỗng vì lỗi không chứng minh được tệp là ảnh.
    ocr_ok = {
        idx: text for idx, text in texts.items()
        if (r := ocr_by_name.get(raw_files[idx].get("name"))) is not None and not r.get("error")
    }
    attachments, warnings, classified = build_plan_items(raw_files, llm_types, page_types, pages_by_file, ocr_ok)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
            "splitDocuments": split,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
