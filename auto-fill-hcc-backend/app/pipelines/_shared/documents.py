"""Shared document helpers that do not import OCR/LLM stacks."""


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
