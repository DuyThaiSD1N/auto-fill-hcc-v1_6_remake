"""Khôi phục hồ sơ handfree đang làm dở (chưa nộp) khi phiên bị gián đoạn: tắt máy / trình duyệt, cổng văng ra.

- service.py   — luồng chung: lưu mốc, gợi ý, khôi phục giấy tờ, nạp lại dữ liệu từng bước.
- base.py      — lớp adapter chung; mỗi họ cổng một file con (tu_phap_cu.py …), chọn ở registry.py.
- store.py     — collection `dossier_resume` (TTL 30 phút).
- replay.py    — chặn tác vụ OCR/LLM của bước đang được nạp lại trong lượt chat.

Chỉ bật khi extension khai `supportsResume` và thủ tục nằm trong danh sách thí điểm (registry.PILOT_PROCEDURES).
"""
from app.channels.handfree.chat.resume.registry import CAPABILITY
from app.channels.handfree.chat.resume.replay import skip_pipeline
from app.channels.handfree.chat.resume.service import (
    after_turn, before_turn, checkpoint, discard, on_close, on_form_snapshot,
)

__all__ = ["CAPABILITY", "after_turn", "before_turn", "checkpoint", "discard", "on_close", "on_form_snapshot",
           "skip_pipeline"]
