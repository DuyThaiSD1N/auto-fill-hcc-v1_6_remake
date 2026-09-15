"""Engine OCR + LLM dùng chung để phân loại tệp ngay khi tải lên.

Tiếng Nói OCR chung một batch. Sau OCR, mỗi tệp luôn có một prompt và một lời gọi LLM
độc lập; cấu hình key/prompt do từng thủ tục cung cấp.
"""
import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.services import ocr
from app.services.llm import client


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationSpec:
    """Hợp đồng để một thủ tục đăng ký dùng engine phân loại chung."""

    system_prompt: str
    allowed_keys: frozenset[str]
    build_user_prompt: Callable[[str, str], str]


async def _classify_one(file: dict, ocr_result: dict,
                        spec: ClassificationSpec) -> str | None:
    """Gọi LLM cho đúng một tệp; lỗi tệp này không làm hỏng tệp khác."""
    messages = [
        {"role": "system", "content": spec.system_prompt},
        {
            "role": "user",
            "content": spec.build_user_prompt(
                file.get("name") or "file", ocr_result.get("text") or ""
            ),
        },
    ]
    try:
        raw = await client.chat(messages, max_tokens=100, enable_thinking=False)
        parsed = client.extract_json_block(raw)
        doc_key = str(parsed.get("doc_key") or "").strip().lower()
        return doc_key if doc_key in spec.allowed_keys else None
    except Exception as exc:  # noqa: BLE001 — fallback riêng cho đúng tệp bị lỗi
        logger.warning("Phân loại LLM tệp %s lỗi: %s", file.get("name"), exc)
        return None


async def classify_files(
    payload_files: list[dict],
    required_docs: list[dict],
    existing_files: list[dict],
    spec: ClassificationSpec,
    fallback: Callable[[str, list[dict]], tuple[str | None, str | None, str]],
) -> list[dict]:
    """OCR batch dùng chung, LLM từng tệp, giữ nguyên shape kết quả upload-session."""
    try:
        # Tiếng Nói hỗ trợ multipart batch: dùng chung một lượt OCR để giảm thời gian chờ.
        # Đi qua `ocr.ocr_per_file` (KHÔNG gọi thẳng adapter) để lượt OCR này VÀO CACHE theo
        # hash nội dung — bước trích xuất sau khi cán bộ bấm "đủ giấy tờ" dùng lại ngay, thay vì
        # OCR lần hai đúng vào khoảng chờ mà cán bộ cảm nhận được.
        ocr_results = await ocr.ocr_per_file(payload_files)
    except Exception as exc:  # noqa: BLE001 — OCR lỗi vẫn cho công dân tải tệp
        logger.warning("OCR Tiếng Nói phân loại upload lỗi: %s", exc)
        ocr_results = [
            {"name": f.get("name"), "type": f.get("type"), "text": "", "error": str(exc)}
            for f in payload_files
        ]

    # Giữ đúng độ dài/thứ tự input kể cả OCR service trả thiếu phần tử.
    normalized_ocr = [
        ocr_results[i] if i < len(ocr_results) else {"text": "", "error": "thiếu kết quả OCR"}
        for i in range(len(payload_files))
    ]
    # Chạy song song nhưng mỗi coroutine dựng messages/prompt riêng cho đúng một tệp.
    predicted = await asyncio.gather(*(
        _classify_one(file, result, spec)
        for file, result in zip(payload_files, normalized_ocr)
    ))

    available_keys = {item.get("key") for item in required_docs}
    out: list[dict] = []
    acc = list(existing_files)
    for result, doc_key in zip(normalized_ocr, predicted):
        text = result.get("text") or ""
        if doc_key in available_keys:
            side = None
            note = "LLM phân loại từ OCR Tiếng Nói"
        else:
            # unknown/LLM lỗi: fallback chỉ được xem OCR của chính tệp đang xử lý.
            doc_key, side, note = fallback(text, acc)
        item = {"doc_key": doc_key, "side": side, "note": note, "ocr_ok": bool(text.strip())}
        out.append(item)
        if doc_key:
            acc.append({"doc_key": doc_key, "side": side})
    return out
