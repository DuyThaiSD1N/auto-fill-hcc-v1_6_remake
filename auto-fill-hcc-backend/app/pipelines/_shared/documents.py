"""Shared document helpers that do not import OCR/LLM stacks."""
import re

# Vạch chia trang các provider OCR chèn vào: "───── Trang 3/24 ─────" / "--- Trang 3/24 ---".
_PAGE_SPLIT_RE = re.compile(r"[─\-]{3,}\s*Trang\s+\d+\s*/\s*\d+\s*[─\-]{3,}", re.IGNORECASE)


def split_ocr_pages(text: str) -> list[str]:
    """Tách OCR của MỘT tệp theo vạch chia trang; tệp không có vạch → một trang duy nhất."""
    raw = str(text or "")
    return [p for p in _PAGE_SPLIT_RE.split(raw) if p.strip()] or ([raw] if raw.strip() else [])


def representative_excerpt(text: str, limit: int = 3000) -> str:
    """Trích đoạn ĐẠI DIỆN của một tệp nhiều trang để LLM phân loại, thay cho cắt N ký tự đầu.

    Tệp gộp nhiều trang (bộ hồ sơ thiết kế, bản vẽ scan) hay có vài trang đầu OCR ra chữ rác lặp
    lại hàng chục lần ("…CƠ QUAN… CÔNG AN…"); cắt ký tự đầu là LLM chỉ thấy rác rồi đoán bừa (đã
    gặp: bộ hồ sơ thiết kế 24 trang bị nhận là căn cước). Ở đây: bỏ dòng trùng lặp trên toàn tệp,
    rồi lấy phần ĐẦU của TỪNG trang (tiêu đề thường nằm đầu trang) chia đều theo hạn mức.
    """
    pages = split_ocr_pages(text)
    seen: set[str] = set()
    cleaned: list[str] = []
    for page in pages:
        lines = []
        for line in page.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if not line or line in seen:
                continue
            seen.add(line)
            lines.append(line)
        if lines:
            cleaned.append(" ".join(lines))
    if not cleaned:
        return ""
    whole = " | ".join(cleaned)
    if len(whole) <= limit or len(cleaned) == 1:
        return whole if len(whole) <= limit else whole[:limit] + "..."
    # Chừa chỗ cho nhãn "[Trang n]" để đủ hạn mức vẫn phủ được tới trang cuối.
    per_page = max(80, limit // len(cleaned) - 14)
    parts, used = [], 0
    for index, page in enumerate(cleaned, start=1):
        chunk = page if len(page) <= per_page else page[:per_page] + "…"
        if used + len(chunk) > limit:
            break
        parts.append(f"[Trang {index}] {chunk}")
        used += len(chunk) + 12
    return " | ".join(parts)


def join_ocr_documents(documents: list[dict]) -> str:
    """Combine OCR text with file headers for trace/debug output."""
    parts = []
    for d in documents:
        name = d.get("name") or "(không tên)"
        provider = d.get("provider")
        header = f"{name} ({provider})" if provider else name
        text = (d.get("text") or "").strip()
        parts.append(f"===== {header} =====\n{text}")
    return "\n\n---\n\n".join(parts)
