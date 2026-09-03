"""Đính kèm cho thủ tục Chứng thực bản sao từ bản chính.

OCR toàn bộ file trong một batch, phân đoạn mọi trang bằng đúng một request LLM, sau đó hậu xử lý
tất định: phủ đủ trang, gom các phần cùng giấy tờ và gom CCCD theo đúng số định danh/chủ thể.
"""
import base64
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.naming import GENERIC_DOCUMENT_TYPE as _GENERIC_DOCUMENT_TYPE
from app.pipelines.chung_thuc_ban_sao.attach import preserve_prompt, prompt
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

DEFAULT_COPY_CERTIFICATION_COMPONENT = (
    "Bản chính giấy tờ, văn bản làm cơ sở để chứng thực bản sao và bản sao cần chứng thực. "
    "Trường hợp người yêu cầu chứng thực chỉ xuất trình bản chính thì cơ quan, tổ chức tiến hành "
    "chụp từ bản chính để thực hiện chứng thực, trừ trường hợp cơ quan, tổ chức không có phương "
    "tiện để chụp. Bản sao từ bản chính để thực hiện chứng thực phải có đầy đủ các trang đã ghi "
    "thông tin của bản chính."
)

logger = logging.getLogger(__name__)

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_IDENTITY_DOCUMENT_TYPES = {"Căn cước công dân"}
_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t \u2500-\u257f-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)"
    r"[\t \u2500-\u257f-]*$"
)
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_FACE_FRONT_MARKERS = (
    "can cuoc cong dan", "citizen identity", "identity card", "ho va ten", "full name",
    "ngay sinh", "date of birth", "gia tri den", "date of expiry",
)
_FACE_BACK_MARKERS = (
    "dac diem nhan dang", "personal identification", "cuc truong cuc canh sat",
    "director general", "idvnm",
)


def _looks_like_identity_document(haystack: str) -> bool:
    if (
        "can cuoc cong dan" in haystack
        or "the can cuoc" in haystack
        or "cccd" in haystack
        or "chung minh nhan dan" in haystack
    ):
        return True

    # Mặt sau CCCD thường không có tiêu đề "Căn cước công dân" hay nhãn "Số định danh cá nhân".
    # OCR vẫn giữ MRZ IDVNM cùng các cụm nhận dạng/vân tay; nhận diện riêng trường hợp này để
    # planner có thể đối chiếu 9 số cuối trong MRZ với số 12 chữ số ở mặt trước và gộp đúng 2 mặt.
    # Bắt buộc IDVNM + thêm một tín hiệu mặt sau để không biến giấy tờ chỉ nhắc chuỗi MRZ thành CCCD.
    if "idvnm" in haystack and any(marker in haystack for marker in (
        "dac diem nhan dang",
        "personal identification",
        "ngon tro trai",
        "left index finger",
        "ngon tro phai",
        "right index finger",
    )):
        return True

    # Một số giấy tờ hộ tịch/đất đai cũng có "số định danh cá nhân" của đương sự.
    # Chỉ dùng tín hiệu này khi có thêm các cụm đặc trưng của chính thẻ CCCD.
    if "so dinh danh ca nhan" not in haystack:
        return False
    identity_markers = [
        "co gia tri den",
        "date of expiry",
        "noi thuong tru",
        "place of residence",
        "que quan",
        "place of origin",
        "dac diem nhan dang",
    ]
    return sum(1 for marker in identity_markers if marker in haystack) >= 2


def detect_document_type(text: str, file_name: str = "") -> str:
    haystack = _fold((text or "") + "\n" + (file_name or ""))
    if "quyet dinh" in haystack:
        return "Quyết định"
    if "bien ban" in haystack:
        return "Biên bản"
    if "cong van" in haystack:
        return "Công văn"
    if "to trinh" in haystack:
        return "Tờ trình"
    if "hop dong" in haystack:
        return "Hợp đồng"
    if "van ban uy quyen" in haystack or "giay uy quyen" in haystack:
        return "Văn bản ủy quyền"
    if "don de nghi" in haystack or "don xin" in haystack:
        return "Đơn đề nghị"
    if "xac nhan tinh trang hon nhan" in haystack:
        return "Giấy xác nhận tình trạng hôn nhân"
    if (
        "giay chung nhan ket hon" in haystack
        or ("ket hon" in haystack and ("vo" in haystack or "chong" in haystack or "ben nam" in haystack or "ben nu" in haystack))
    ):
        return "Giấy chứng nhận kết hôn"
    if "giay khai sinh" in haystack or "trich luc khai sinh" in haystack:
        return "Giấy khai sinh"
    if "giay chung sinh" in haystack:
        return "Giấy chứng sinh"
    if "giay bao tu" in haystack or "bao tu" in haystack:
        return "Giấy báo tử"
    if "ban chinh" in haystack and "giay to" in haystack:
        return "Bản chính giấy tờ"
    if (
        "giay chung nhan quyen su dung dat" in haystack
        or "quyen su dung dat" in haystack
        or "cnqsd" in haystack
        or "gcnqsd" in haystack
        or ("thua dat" in haystack and "so vao so" in haystack)
    ):
        return "Giấy chứng nhận quyền sử dụng đất"
    if _looks_like_identity_document(haystack):
        return "Căn cước công dân"
    if "so ho khau" in haystack:
        return "Sổ hộ khẩu"
    if "trich luc" in haystack:
        return "Trích lục hộ tịch"
    return ""


def canonical_document_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "tai lieu chung thuc":
        return _GENERIC_DOCUMENT_TYPE
    if "quyet dinh" in text:
        return "Quyết định"
    if "bien ban" in text:
        return "Biên bản"
    if "cong van" in text:
        return "Công văn"
    if "to trinh" in text:
        return "Tờ trình"
    if "hop dong" in text:
        return "Hợp đồng"
    if "uy quyen" in text:
        return "Văn bản ủy quyền"
    if "don de nghi" in text or "don xin" in text:
        return "Đơn đề nghị"
    if "xac nhan tinh trang hon nhan" in text:
        return "Giấy xác nhận tình trạng hôn nhân"
    if "ket hon" in text:
        return "Giấy chứng nhận kết hôn"
    if "khai sinh" in text:
        return "Giấy khai sinh"
    if "chung sinh" in text:
        return "Giấy chứng sinh"
    if "bao tu" in text:
        return "Giấy báo tử"
    if "quyen su dung dat" in text or "cnqsd" in text or "gcnqsd" in text:
        return "Giấy chứng nhận quyền sử dụng đất"
    if "can cuoc" in text or "cccd" in text or "chung minh nhan dan" in text or text == "cmnd":
        return "Căn cước công dân"
    if "so ho khau" in text:
        return "Sổ hộ khẩu"
    if "trich luc" in text:
        return "Trích lục hộ tịch"
    return normalize_document_name(value, _GENERIC_DOCUMENT_TYPE)


def _coerce_llm_document_info(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        detected = canonical_document_type(str(value.get("detectedType") or value.get("type") or ""))
        raw_name = str(value.get("documentName") or value.get("name") or value.get("title") or "")
        document_name = normalize_document_name(raw_name, detected) if raw_name else ""
        return {"detectedType": detected, "documentName": document_name}

    detected = canonical_document_type(str(value or ""))
    return {"detectedType": detected, "documentName": ""}


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    source = str(base or "").strip()
    if len(source) > 50:
        # Cắt trước khi gọi helper chung, nếu không phần tên đã bị helper cắt mất và không thể biết
        # ký tự cuối là một từ dở dang hay một từ hoàn chỉnh.
        head = source[:48].rstrip()
        source = head.rsplit(" ", 1)[0].strip() or head
    raw = normalize_document_name(source, fallback)
    normalized = raw
    if len(raw) >= 50:
        # normalize_document_name giới hạn cứng 50 ký tự. Cắt lại ở ranh giới từ để tên trên
        # cổng không thành "Nguyễn Quố" trong khi vẫn tuân thủ giới hạn của biểu mẫu.
        compact = raw[:50].rstrip()
        normalized = compact.rsplit(" ", 1)[0].strip() or compact
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized

    stem = normalized[:45].strip() or fallback[:45].strip() or _GENERIC_DOCUMENT_TYPE
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


def _truncate_page_text(text: str, limit: int = 2400) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _decode_data_url(data_url: str) -> bytes:
    _, separator, payload = str(data_url or "").partition(",")
    if not separator:
        return b""
    payload += "=" * (-len(payload) % 4)
    return base64.b64decode(payload)


def _pdf_page_count(file: dict) -> int:
    is_pdf = "pdf" in str(file.get("type") or "").lower() or str(file.get("name") or "").lower().endswith(".pdf")
    if not is_pdf:
        return 1
    try:
        document = fitz.open(stream=_decode_data_url(file.get("dataUrl") or ""), filetype="pdf")
        try:
            return max(1, document.page_count)
        finally:
            document.close()
    except Exception:  # noqa: BLE001 - dữ liệu test/định dạng lạ vẫn phải có fallback một trang
        return 1


def _split_ocr_pages(text: str, expected_count: int) -> tuple[list[dict], bool]:
    """Tách OCR theo header Trang n/m; không có header thì không cho LLM đoán ranh giới."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "pageTo": expected_count, "ocrText": _truncate_page_text(value)}], expected_count == 1

    pages_by_number: dict[int, str] = {}
    declared_total = expected_count
    for position, match in enumerate(matches):
        page_number = int(match.group(1))
        declared_total = max(declared_total, int(match.group(2)))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(value)
        pages_by_number[page_number] = value[match.end():end].strip()
    return [
        {"pageNumber": page, "ocrText": _truncate_page_text(pages_by_number.get(page, ""))}
        for page in range(1, max(1, declared_total) + 1)
    ], True


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Phân đoạn mọi file bằng đúng một request LLM."""
    if not documents:
        return []
    page_total = sum(len(item.get("pages") or []) for item in documents)
    raw = await client.chat(
        [
            {"role": "system", "content": prompt.SYSTEM_PROMPT},
            {"role": "user", "content": prompt.build_user_prompt(documents)},
        ],
        max_tokens=max(settings.attach_classify_max_tokens, min(5000, page_total * 220)),
        enable_thinking=False,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


async def _classify_source_files_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Giữ nguyên mỗi file và đặt đúng một tên bằng prompt riêng, vẫn chỉ một request LLM."""
    if not documents:
        return []
    page_total = sum(len(item.get("pages") or []) for item in documents)
    raw = await client.chat(
        [
            {"role": "system", "content": preserve_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": preserve_prompt.build_user_prompt(documents)},
        ],
        max_tokens=max(settings.attach_classify_max_tokens, min(3000, page_total * 140)),
        enable_thinking=False,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fallback_segment(file_index: int, page_from: int, page_to: int, file_name: str) -> dict:
    suffix = f" trang {page_from}" if page_from == page_to else f" trang {page_from}-{page_to}"
    return {
        "fileIndex": file_index,
        "pageFrom": page_from,
        "pageTo": page_to,
        "detectedType": "",
        "documentName": f"{file_name}{suffix}",
        "subjectName": "",
        "identityNumber": "",
        "logicalKey": "",
    }


def _validated_segments(
    raw_segments: list[dict], raw_files: list[dict], file_meta: dict[int, dict], errors: list[str]
) -> list[dict]:
    """Không tin khoảng trang từ LLM: loại chồng trang, bù trang thiếu và giữ đúng fileIndex."""
    by_file: dict[int, list[dict]] = {index: [] for index in range(len(raw_files))}
    for raw in raw_segments:
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index not in by_file:
            continue
        page_count = file_meta[file_index]["pageCount"]
        page_from = _coerce_int(raw.get("pageFrom")) or 1
        page_to = _coerce_int(raw.get("pageTo")) or page_count
        if not 1 <= page_from <= page_to <= page_count:
            errors.append(f"Phân đoạn fileIndex={file_index} có khoảng trang không hợp lệ: {page_from}-{page_to}.")
            continue
        by_file[file_index].append({
            "fileIndex": file_index,
            "pageFrom": page_from,
            "pageTo": page_to,
            "detectedType": str(raw.get("detectedType") or raw.get("type") or "").strip(),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
            "subjectName": str(raw.get("subjectName") or "").strip(),
            "identityNumber": re.sub(r"\D+", "", str(raw.get("identityNumber") or "")),
            "logicalKey": str(raw.get("logicalKey") or "").strip(),
        })

    valid: list[dict] = []
    for file_index, file in enumerate(raw_files):
        meta = file_meta[file_index]
        page_count = meta["pageCount"]
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not meta["pageBoundariesAvailable"]:
            first = items[0] if items else _fallback_segment(file_index, 1, page_count, file.get("name") or "file")
            valid.append({**first, "pageFrom": 1, "pageTo": page_count})
            continue

        occupied: set[int] = set()
        accepted: list[dict] = []
        for item in items:
            pages = set(range(item["pageFrom"], item["pageTo"] + 1))
            if occupied & pages:
                errors.append(
                    f"Phân đoạn fileIndex={file_index} bị chồng trang; bỏ đoạn {item['pageFrom']}-{item['pageTo']}."
                )
                continue
            occupied.update(pages)
            accepted.append(item)

        missing = [page for page in range(1, page_count + 1) if page not in occupied]
        start = previous = None
        for page in missing + [None]:
            if page is not None and start is None:
                start = previous = page
            elif page is not None and page == previous + 1:
                previous = page
            else:
                if start is not None:
                    accepted.append(_fallback_segment(
                        file_index, start, previous, str(file.get("name") or f"file-{file_index + 1}")
                    ))
                start = previous = page
        valid.extend(sorted(accepted, key=lambda item: item["pageFrom"]))
    return sorted(valid, key=lambda item: (item["fileIndex"], item["pageFrom"]))


def _preserve_source_file_segments(
    segments: list[dict],
    raw_files: list[dict],
    file_meta: dict[int, dict],
    *,
    is_identity_segment: Callable[[dict], bool],
    long_name_fallback: str,
) -> list[dict]:
    """Co kết quả phân đoạn về đúng một đoạn đầy đủ cho mỗi file nguồn.

    Prompt giữ nguyên phải trả một object cho mỗi file; helper này ép lại toàn bộ page range để
    backend không bao giờ yêu cầu FE cắt PDF. Nếu provider vẫn trả sai nhiều object, ưu tiên nhãn
    giấy tờ chính để tránh đưa nguyên file hỗn hợp vào ô CCCD.
    """
    by_file: dict[int, list[dict]] = {index: [] for index in range(len(raw_files))}
    for segment in segments:
        file_index = _coerce_int(segment.get("fileIndex"))
        if file_index in by_file:
            by_file[file_index].append(segment)

    preserved: list[dict] = []
    for file_index, file in enumerate(raw_files):
        page_count = int(file_meta[file_index]["pageCount"] or 1)
        items = sorted(by_file[file_index], key=lambda item: (item["pageFrom"], item["pageTo"]))
        if not items:
            preserved.append(_fallback_segment(
                file_index, 1, page_count, str(file.get("name") or f"file-{file_index + 1}")
            ))
            continue

        non_identity = [item for item in items if not is_identity_segment(item)]
        primary = non_identity[0] if non_identity else items[0]
        identity_flags = {is_identity_segment(item) for item in items}
        detected_types = {
            _fold(canonical_document_type(item.get("detectedType") or item.get("documentName") or ""))
            for item in items
            if canonical_document_type(item.get("detectedType") or item.get("documentName") or "")
            != _GENERIC_DOCUMENT_TYPE
        }
        logical_keys = {_fold(item.get("logicalKey") or "") for item in items if item.get("logicalKey")}
        is_mixed = len(identity_flags) > 1 or len(detected_types) > 1 or len(logical_keys) > 1

        detected = str(primary.get("detectedType") or primary.get("documentName") or "").strip()
        document_name = str(primary.get("documentName") or "").strip()
        if is_mixed:
            document_name = long_name_fallback
        document_name = normalize_document_name(
            document_name or str(file.get("name") or f"file-{file_index + 1}"),
            canonical_document_type(detected),
        )
        if len(document_name) > 40:
            document_name = long_name_fallback

        preserved.append({
            **primary,
            "fileIndex": file_index,
            "pageFrom": 1,
            "pageTo": page_count,
            "documentName": document_name,
            # File hỗn hợp là một nguồn nguyên vẹn, không được gom tiếp với file khác theo một
            # logicalKey/CCCD chỉ xuất hiện ở vài trang bên trong.
            "subjectName": "" if is_mixed else str(primary.get("subjectName") or ""),
            "identityNumber": "" if is_mixed else str(primary.get("identityNumber") or ""),
            "logicalKey": "" if is_mixed else str(primary.get("logicalKey") or ""),
        })
    return preserved


def _segment_text(segment: dict, page_text_by_file: dict[int, dict[int, str]], full_text_by_file: dict[int, str]) -> str:
    pages = page_text_by_file.get(segment["fileIndex"]) or {}
    if not pages:
        return full_text_by_file.get(segment["fileIndex"], "")
    return "\n".join(
        pages.get(page, "") for page in range(segment["pageFrom"], segment["pageTo"] + 1)
    ).strip()


def _source_segment(segment: dict, page_count: int) -> dict:
    indexes = None
    if segment["pageFrom"] != 1 or segment["pageTo"] != page_count:
        indexes = list(range(segment["pageFrom"] - 1, segment["pageTo"]))
    return {"fileIndex": segment["fileIndex"], "pageIndexes": indexes}


def _face_rank(text: str) -> int:
    folded = _fold(text)
    has_front = any(marker in folded for marker in _FACE_FRONT_MARKERS)
    has_back = any(marker in folded for marker in _FACE_BACK_MARKERS)
    if has_front and not has_back:
        return 0
    if has_back and not has_front:
        return 1
    return 2


def _identity_number(text: str) -> str:
    match = _CCCD_RE.search(str(text or ""))
    return match.group(0) if match else ""


def _identity_key(record: dict, known_numbers: list[str]) -> str:
    llm_number = re.sub(r"\D+", "", record.get("identityNumber") or "")
    if len(llm_number) == 12:
        return f"id:{llm_number}"
    direct = _identity_number(record["ocrText"])
    if direct:
        return f"id:{direct}"
    digits = re.sub(r"\D+", "", record["ocrText"])
    for number in known_numbers:
        if number in digits or number[-9:] in digits:
            return f"id:{number}"
    subject = _fold(record.get("subjectName") or "")
    return f"name:{subject}" if len(subject.split()) >= 2 else ""


def _logical_group_key(record: dict) -> str:
    if record["isIdentity"]:
        return record.get("identityKey") or ""
    explicit = _fold(record.get("logicalKey") or "")
    if explicit:
        subject = _fold(record.get("subjectName") or "")
        return f"doc:{_fold(record['detectedType'])}:{subject}:{explicit}"
    # Chỉ tự suy nhóm với loại nhiều trang phổ biến và có đúng chủ thể; các loại khác giữ riêng để
    # không vô tình gộp hai quyết định/giấy chứng nhận độc lập của cùng một người.
    detected = _fold(record.get("detectedType") or "")
    subject = _fold(record.get("subjectName") or "")
    if "hoc ba" in detected and len(subject.split()) >= 2:
        return f"doc:hoc-ba:{subject}"
    return ""


def _select_primary_index(detected_by_index: dict[int, str], count: int) -> int:
    if count <= 1:
        return 0
    for idx in range(count):
        detected = detected_by_index.get(idx) or ""
        if detected and detected not in _IDENTITY_DOCUMENT_TYPES and detected != "Tài liệu chứng thực":
            return idx
    for idx in range(count):
        detected = detected_by_index.get(idx) or ""
        if detected and detected not in _IDENTITY_DOCUMENT_TYPES:
            return idx
    return 0


def build_plan_items(files: list[dict], ocr_results: list[dict], llm_types: dict[int, Any] | None = None) -> list[dict]:
    llm_types = llm_types or {}
    # OCR service cam kết results[] khớp thứ tự input. Không map bằng fileName: người dùng có thể tải
    # nhiều file cùng tên "image.pdf", khi đó dict theo tên sẽ lấy nhầm OCR của file cuối cho mọi file.
    by_index = {index: item for index, item in enumerate(ocr_results)}
    docs: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = by_index.get(idx, {})
        llm_info = _coerce_llm_document_info(llm_types[idx]) if idx in llm_types else {"detectedType": "", "documentName": ""}
        llm_detected = llm_info["detectedType"]
        rule_detected = detect_document_type(str(ocr_item.get("text") or ""), file_name)
        detected = llm_detected if llm_detected and llm_detected != _GENERIC_DOCUMENT_TYPE else rule_detected
        if not detected and llm_detected:
            detected = llm_detected
        if not detected:
            detected = _GENERIC_DOCUMENT_TYPE

        document_name = llm_info["documentName"] or normalize_document_name(file_name, detected)
        component_base_name = llm_info["documentName"] or detected
        docs.append(
            {
                "index": idx,
                "fileName": file_name,
                "detectedType": detected,
                "documentName": document_name,
                "componentBaseName": component_base_name,
            }
        )

    detected_by_index = {doc["index"]: doc["detectedType"] for doc in docs}
    primary_index = _select_primary_index(detected_by_index, len(docs))
    ordered_docs = [doc for doc in docs if doc["index"] == primary_index] + [
        doc for doc in docs if doc["index"] != primary_index
    ]

    used_document_names: set[str] = set()
    used_component_names: set[str] = set()
    items: list[dict] = []
    for doc in ordered_docs:
        idx = doc["index"]
        file_name = doc["fileName"]
        detected = doc["detectedType"]
        document_name = _unique_document_name(doc.get("documentName") or detected, used_document_names, detected)

        if idx == primary_index:
            component_name = DEFAULT_COPY_CERTIFICATION_COMPONENT
            target = "existing"
            component_index = 1
        else:
            base = doc.get("componentBaseName") or document_name
            if _fold(base) == _fold(_GENERIC_DOCUMENT_TYPE):
                # OCR trống/không phân loại được → base = "Tài liệu chứng thực" cho MỌI file.
                # Nếu đánh số tên THÀNH PHẦN bằng bộ đếm RIÊNG sẽ lệch pha với documentName và
                # sinh tên trần "Tài liệu chứng thực" — bị FE (khớp substring 2 chiều ở
                # attachmentKeyMatches) coi là trùng của "Tài liệu chứng thực 2/3…" nên bỏ sót
                # file (4/7). Dùng THẲNG documentName đã đánh số duy nhất làm tên thành phần →
                # mỗi file 1 thành phần riêng, các tên không lồng nhau.
                component_name = document_name
                used_component_names.add(_fold(component_name))
            else:
                component_name = _unique_document_name(base, used_component_names, detected)
            target = "new"
            component_index = None

        items.append(
            {
                "fileIndex": idx,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": component_name,
                "target": target,
                "componentIndex": component_index,
                "needsAddComponent": target == "new",
                "detectedType": detected,
            }
        )

    return items


def build_segment_plan_items(
    files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
) -> tuple[list[dict], list[dict]]:
    """Dựng attachment theo TÀI LIỆU LOGIC, không theo số file người dùng tải lên."""
    records: list[dict] = []
    for order, segment in enumerate(segments):
        file_index = segment["fileIndex"]
        file = files[file_index]
        ocr_text = _segment_text(segment, page_text_by_file, full_text_by_file)
        llm_detected = canonical_document_type(segment.get("detectedType") or "")
        rule_detected = detect_document_type(ocr_text, "")
        # LLM đọc toàn bộ ngữ cảnh tài liệu nên nhãn LLM đã có là nguồn quyết định. Rule chỉ làm
        # fallback khi LLM không phân loại được; tuyệt đối không lấy một dòng có chữ "CCCD" trong
        # giấy cam đoan/danh sách đất để ghi đè cả tài liệu thành thẻ căn cước.
        detected = llm_detected if llm_detected != _GENERIC_DOCUMENT_TYPE else rule_detected
        detected = detected or _GENERIC_DOCUMENT_TYPE
        subject_name = str(segment.get("subjectName") or "").strip()
        raw_name = str(segment.get("documentName") or "").strip()
        if not raw_name:
            raw_name = detected if detected != _GENERIC_DOCUMENT_TYPE else str(file.get("name") or "")
        records.append({
            "order": order,
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "segment": segment,
            "ocrText": ocr_text,
            "detectedType": detected,
            "documentName": raw_name,
            "subjectName": subject_name,
            "identityNumber": str(segment.get("identityNumber") or ""),
            "logicalKey": str(segment.get("logicalKey") or ""),
            "isIdentity": detected == "Căn cước công dân",
        })

    known_numbers: list[str] = []
    for record in records:
        if not record["isIdentity"]:
            continue
        candidate = re.sub(r"\D+", "", record.get("identityNumber") or "")
        number = candidate if len(candidate) == 12 else _identity_number(record["ocrText"])
        if number and number not in known_numbers:
            known_numbers.append(number)
    for record in records:
        if record["isIdentity"]:
            record["identityKey"] = _identity_key(record, known_numbers)
        record["groupKey"] = _logical_group_key(record)

    groups: list[list[dict]] = []
    group_position: dict[str, int] = {}
    for record in records:
        key = record.get("groupKey") or f"single:{record['order']}"
        if key not in group_position:
            group_position[key] = len(groups)
            groups.append([])
        groups[group_position[key]].append(record)

    # Hai mặt CCCD phải theo thứ tự trước→sau; các giấy tờ khác giữ thứ tự file/trang người dùng tải.
    for group in groups:
        if group and group[0]["isIdentity"]:
            group.sort(key=lambda record: (_face_rank(record["ocrText"]), record["order"]))
        else:
            group.sort(key=lambda record: record["order"])

    def group_name(group: list[dict]) -> str:
        if group[0]["isIdentity"]:
            subject = next((record["subjectName"] for record in group if record["subjectName"]), "")
            if subject:
                return f"CCCD {subject}"
            named = next((record["documentName"] for record in group if record["documentName"]), "")
            return named or "Căn cước công dân"
        return next((record["documentName"] for record in group if record["documentName"]), group[0]["detectedType"])

    # Ô bắt buộc STT1 ưu tiên một giấy tờ không phải CCCD; mọi nhóm còn lại thêm thành phần riêng.
    primary_group_index = next(
        (index for index, group in enumerate(groups) if group and not group[0]["isIdentity"]),
        0,
    ) if groups else 0
    ordered_groups = ([groups[primary_group_index]] + [
        group for index, group in enumerate(groups) if index != primary_group_index
    ]) if groups else []

    used_document_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    for group_index, group in enumerate(ordered_groups):
        primary = group[0]
        detected = primary["detectedType"]
        document_name = _unique_document_name(group_name(group), used_document_names, detected)
        sources = [
            _source_segment(record["segment"], file_meta[record["fileIndex"]]["pageCount"])
            for record in group
        ]
        item = {
            "fileIndex": sources[0]["fileIndex"],
            "fileName": primary["fileName"],
            "documentName": document_name,
            "componentName": DEFAULT_COPY_CERTIFICATION_COMPONENT if group_index == 0 else document_name,
            "target": "existing" if group_index == 0 else "new",
            "componentIndex": 1 if group_index == 0 else None,
            "needsAddComponent": group_index != 0,
            "detectedType": detected,
        }
        if len(sources) > 1 or sources[0].get("pageIndexes") is not None:
            item["sourceSegments"] = sources
        attachments.append(item)

        for record in group:
            classified.append({
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "pageFrom": record["segment"]["pageFrom"],
                "pageTo": record["segment"]["pageTo"],
                "detectedType": record["detectedType"],
                "documentName": document_name,
                "logicalGroup": record.get("groupKey") or None,
                "target": item["target"],
                "componentIndex": item["componentIndex"],
            })
    return attachments, sorted(classified, key=lambda item: (item["fileIndex"], item["pageFrom"]))


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho chung-thuc-ban-sao (gọi qua registry.get_attach_pipeline)."""
    _ = session
    options = options or {}
    split_documents = options.get("splitDocuments") is True
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [
        (file_index, file)
        for file_index, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    ]

    t0 = time.monotonic()
    # Cần OCR đầy đủ để tách PDF hỗn hợp. Vẫn chỉ gọi một batch OCR cho toàn bộ file hỗ trợ.
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            # OCR lỗi thường do dịch vụ OCR chập chờn (502/timeout) — KHÔNG phải lỗi hồ sơ.
            # File vẫn được đính kèm (tên fallback qua build_plan_items), nên KHÔNG đẩy vào
            # `errors` để tránh hiện "Cảnh báo xử lý" gây hoang mang cho cán bộ; chỉ log để debug.
            logger.warning("OCR phân loại lỗi (%s): %s", r.get("name"), r["error"])

    # Kết quả OCR khớp thứ tự input. Không map theo tên vì hai file "image.pdf" là hai nguồn khác nhau.
    ocr_by_index = {
        file_index: result
        for (file_index, _), result in zip(ocr_pairs, ocr_results)
    }
    file_meta: dict[int, dict[str, Any]] = {}
    page_text_by_file: dict[int, dict[int, str]] = {}
    full_text_by_file: dict[int, str] = {}
    llm_docs: list[dict[str, Any]] = []
    for file_index, file in enumerate(raw_files):
        text = str(ocr_by_index.get(file_index, {}).get("text") or "")
        page_count = _pdf_page_count(file)
        pages, boundaries_available = _split_ocr_pages(text, page_count)
        if boundaries_available and pages:
            page_count = max(page_count, max(int(page.get("pageNumber") or 1) for page in pages))
        file_meta[file_index] = {
            "pageCount": page_count,
            "pageBoundariesAvailable": boundaries_available,
        }
        full_text_by_file[file_index] = text
        page_text_by_file[file_index] = {
            int(page.get("pageNumber") or 1): str(page.get("ocrText") or "")
            for page in pages
        }
        if text.strip():
            llm_docs.append({
                "fileIndex": file_index,
                "pageCount": page_count,
                "pageBoundariesAvailable": boundaries_available,
                "pages": pages,
            })

    t1 = time.monotonic()
    raw_segments: list[dict] = []
    if llm_docs:
        try:
            raw_segments = await (
                _classify_documents_with_llm(llm_docs)
                if split_documents
                else _classify_source_files_with_llm(llm_docs)
            )
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)
    if not split_documents:
        segments = _preserve_source_file_segments(
            segments,
            raw_files,
            file_meta,
            is_identity_segment=lambda segment: canonical_document_type(
                segment.get("detectedType") or segment.get("documentName") or ""
            ) in _IDENTITY_DOCUMENT_TYPES,
            long_name_fallback="Hồ sơ chứng thực",
        )
    attachments, classified = build_segment_plan_items(
        raw_files,
        segments,
        file_meta,
        page_text_by_file,
        full_text_by_file,
    )
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]
    indexed_ocr_results = []
    for file_index, file in enumerate(raw_files):
        result = ocr_by_index.get(file_index)
        if not result:
            continue
        indexed_ocr_results.append({
            **result,
            "name": f"fileIndex={file_index} · {file['name']}",
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [
                raw_files[file_index]["name"]
                for file_index, result in ocr_by_index.items()
                if result.get("text")
            ],
            "llmDocuments": [raw_files[doc["fileIndex"]]["name"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
            "documentSplitEnabled": split_documents,
            "documentPromptMode": "split" if split_documents else "preserve",
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        # Cho trace (AttachmentPlanResp tự lược 2 field này khỏi HTTP response).
        "ocr_text": join_ocr_documents(indexed_ocr_results),
        "llm_output": {"documents": raw_segments},
        "errors": errors,
    }


# Bí danh tương thích tên cũ (router/shim cũ gọi plan_copy_certification_attachments).
plan_copy_certification_attachments = plan
