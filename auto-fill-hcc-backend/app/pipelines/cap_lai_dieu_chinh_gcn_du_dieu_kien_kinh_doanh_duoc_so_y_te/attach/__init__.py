"""Attachment planner cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (cổng Bộ Y tế —
bảng thành phần hồ sơ checkbox+radio+file, engine FE `attp-row`; bật "Tách giấy tờ" thì tách PDF gộp theo trang, tắt thì
đính nguyên tệp)."""

from .planner import plan

__all__ = ["plan"]
