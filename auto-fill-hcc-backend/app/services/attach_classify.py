"""Module RIÊNG cho bước PHÂN LOẠI TÀI LIỆU ĐÍNH KÈM (chỉ path attach, không đụng form-fill).

Gộp 2 tối ưu, tất cả tunable qua settings:
- OCR nhanh: cắt N trang đầu (pdf_utils) + provider chọn qua cờ `attach_classify_ocr`
  (tiengnoi batch — thử nghiệm; lỗi → tự fallback về dispatcher raw).
- LLM classify NÉN: input cắt ngắn + output rút gọn {"d":[{"t","n"}]} (bỏ index, map theo THỨ TỰ).

Thủ tục chỉ cung cấp phần thân prompt (persona + rule + loại giấy tờ); module tự gắn output_contract.
"""
import json
import re

from app.config import settings
from app.services import ocr_raw, ocr_tiengnoi
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

# Hợp đồng output NÉN — module tự append vào system prompt của thủ tục. Parser dưới đọc đúng cái này.
OUTPUT_CONTRACT = """
<output_contract>
Trả về DUY NHẤT 1 JSON object, KHÔNG markdown, KHÔNG giải thích, không ký tự thừa.
Mảng "d" khớp ĐÚNG THỨ TỰ tài liệu vào — mỗi tài liệu đúng 1 phần tử, KHÔNG cần index.
Schema: {"d":[{"t":"<loại giấy tờ>","n":"<tên hiển thị ngắn>"}]}
- "t" = loại giấy tờ (detectedType). "n" = tên hiển thị ngắn (documentName).
</output_contract>
""".strip()


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def build_user_prompt(docs: list[dict], char_limit: int) -> str:
    """Input NÉN: chỉ OCR text theo THỨ TỰ (bỏ fileName vì tên file không đáng tin)."""
    items = [{"text": _truncate(d.get("text", ""), char_limit)} for d in docs]
    return (
        "DANH SÁCH OCR (theo ĐÚNG THỨ TỰ tài liệu):\n"
        f"{json.dumps(items, ensure_ascii=False)}\n\n"
        'Trả {"d":[{"t":"...","n":"..."}]} đúng thứ tự, mỗi tài liệu 1 phần tử.'
    )


def _coerce(item: dict) -> dict[str, str]:
    return {
        "detectedType": str(item.get("t") or item.get("detectedType") or "").strip(),
        "documentName": str(item.get("n") or item.get("documentName") or "").strip(),
    }


async def classify(system_body: str, docs: list[dict]) -> dict[int, dict[str, str]]:
    """docs: [{index, text, ...}] → {index: {detectedType, documentName}}. Map THEO THỨ TỰ."""
    if not docs:
        return {}
    messages = [
        {"role": "system", "content": system_body.strip() + "\n\n" + OUTPUT_CONTRACT},
        {"role": "user", "content": build_user_prompt(docs, settings.attach_classify_char_limit)},
    ]
    raw = await client.chat(messages, max_tokens=settings.attach_classify_max_tokens, enable_thinking=False)
    parsed = client.extract_json_block(raw)
    arr = parsed.get("d") or parsed.get("documents") or []

    out: dict[int, dict[str, str]] = {}
    # Đủ số lượng → map thẳng theo vị trí (bền nhất, không tin index của LLM).
    if len(arr) == len(docs):
        for pos, item in enumerate(arr):
            out[docs[pos]["index"]] = _coerce(item)
        return out
    # Lệch số lượng (LLM gộp/sót) → gán best-effort theo vị trí có sẵn.
    for pos, item in enumerate(arr):
        if pos < len(docs):
            out[docs[pos]["index"]] = _coerce(item)
    return out


async def ocr_for_classify(files: list[dict]) -> list[dict]:
    """OCR cho classify, CÓ ĐỌC CACHE theo hash file gốc (text đầy đủ do bước fill lưu).

    Hit → dùng text đầy đủ (classify tự cắt char_limit sau); miss → mới cắt N trang đầu + OCR.
    KHÔNG ghi cache ở đây (text đã cắt là một phần, không được đè lên text đầy đủ ở cùng key —
    cache đầy đủ chỉ do luồng fill `ocr.ocr_per_file` ghi). Trả [{name,type,text,error?}].
    """
    from app.services import ocr_cache

    keys = [ocr_cache.content_key((f or {}).get("dataUrl") or "") for f in files]
    cached = await ocr_cache.get_many([k for k in keys if k]) if settings.ocr_cache_enabled else {}

    miss_files = [f for f, k in zip(files, keys) if not k or k not in cached]
    fresh = await _ocr_trimmed(miss_files) if miss_files else []

    results: list[dict] = []
    fresh_iter = iter(fresh)
    for f, k in zip(files, keys):
        if k and k in cached:
            results.append({
                "name": (f or {}).get("name"), "type": (f or {}).get("type"),
                "text": cached[k]["text"],
            })
        else:
            results.append(next(fresh_iter))
    return results


async def _ocr_trimmed(files: list[dict]) -> list[dict]:
    """OCR cắt N trang đầu + chọn MODE (độc lập cờ RAW_BY_GEMINI toàn cục):
    - "tiengnoi": vintern-v5 (batch 1 request). Lỗi/down → fallback Vision vnekyc.
    - "vnekyc"/"raw": gọi THẲNG ocr_raw, KHÔNG qua dispatcher nên KHÔNG bị RAW_BY_GEMINI đổi.
    """
    trimmed = trim_files_for_classify(files, settings.attach_classify_max_pages)
    if settings.attach_classify_ocr == "tiengnoi":
        results = None
        try:
            results = await ocr_tiengnoi.ocr_per_file(trimmed)
        except Exception:  # noqa: BLE001 — tiengnoi raise (down/timeout) → fallback toàn bộ sang raw
            results = None
        if results is not None:
            # tiengnoi lúc quá tải trả ok=true nhưng text RỖNG (không raise) → phải fallback raw CHO
            # TỪNG file rỗng, nếu không cả lô thành generic. Chỉ ghi đè khi raw đọc ra text thật.
            empty_idx = [i for i, r in enumerate(results) if not (str(r.get("text") or "")).strip()]
            if empty_idx:
                try:
                    raw_res = await ocr_raw.ocr_per_file([trimmed[i] for i in empty_idx])
                    for j, i in enumerate(empty_idx):
                        if j < len(raw_res) and str(raw_res[j].get("text") or "").strip():
                            results[i] = raw_res[j]
                except Exception:  # noqa: BLE001 — raw cũng lỗi → giữ kết quả tiengnoi (rỗng), không chặn
                    pass
            return results
    return await ocr_raw.ocr_per_file(trimmed)
