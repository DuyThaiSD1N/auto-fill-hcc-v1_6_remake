"""Mở khoá họ tên + CC/CCCD người nộp trên form Form.io (iGate) cho mọi thủ tục.

Cổng đổ hai ô này từ tài khoản VNeID đang đăng nhập rồi khoá (disabled) → cán bộ không sửa được khi
người nộp thực tế khác tài khoản. Extension đã có cờ ``enableInput`` (bỏ disabled cả component trước khi
ghi); ở đây gắn cờ đó cho hai ô, ô pipeline không phát thì thêm ``dom-expect`` để chỉ mở khoá, KHÔNG ghi
đè giá trị cổng đã đổ. Extension cũ không biết ``enableInput`` → ``dom-expect`` không làm gì với ô khoá.
"""
from __future__ import annotations

SUBMITTER_LOCKED_NAMES = ("data[fullname]", "data[identityNumber]")


def unlock_locked_submitter(fields):
    """Sửa TẠI CHỖ và trả lại chính danh sách. Chỉ áp cho bộ field Form.io (tên dạng ``data[...]``)."""
    if not isinstance(fields, list):
        return fields
    items = [f for f in fields if isinstance(f, dict)]
    if not any(str(f.get("name") or "").startswith("data[") for f in items):
        return fields
    seen = set()
    for field in items:
        name = field.get("name")
        if name in SUBMITTER_LOCKED_NAMES:
            field["enableInput"] = True
            seen.add(name)
    for name in SUBMITTER_LOCKED_NAMES:
        if name not in seen:
            fields.append({"name": name, "comp": "dom-expect", "value": "", "enableInput": True})
    return fields
