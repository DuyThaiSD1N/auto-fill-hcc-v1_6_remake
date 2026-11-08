"""Tác vụ nền nào được thay bằng dữ liệu đã lưu trong lượt chat hiện tại.

Flow vẫn đi đúng đường cũ (đặt state, bật tác vụ OCR/LLM). Tác vụ thuộc tập này tự bỏ qua, còn lượt chat nạp
kết quả đã lưu rồi chạy sự kiện "*_ready" ngay trong lượt — không có tác vụ nền nào ghi đè hội thoại song song.
asyncio.create_task chép ngữ cảnh lúc tạo, nên tác vụ bật trong lượt thấy đúng tập của lượt đó.
"""
from contextvars import ContextVar

_KINDS: ContextVar[frozenset[str]] = ContextVar("resume_replay_kinds", default=frozenset())


def set_kinds(kinds) -> None:
    _KINDS.set(frozenset(kinds))


def skip_pipeline(kind: str) -> bool:
    """`kind` theo pipeline_runner: owner | process | attach."""
    return kind in _KINDS.get()
