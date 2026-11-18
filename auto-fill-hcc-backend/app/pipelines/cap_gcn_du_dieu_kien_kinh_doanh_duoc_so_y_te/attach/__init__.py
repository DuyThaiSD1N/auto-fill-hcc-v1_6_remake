"""Attachment planner cho "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (cổng Bộ Y tế — bảng thành phần hồ sơ
checkbox + loại bản + file, engine FE `attp-row`; bật "Tách giấy tờ" thì chia PDF gộp theo trang, tắt thì đính nguyên
tệp)."""

from .planner import plan

__all__ = ["plan"]
