"""Prompt liệt kê giấy tờ trong từng tệp — "Đăng ký việc nuôi con nuôi trong nước" (2.001263), chế độ KHÔNG tách.
Định nghĩa loại giấy lấy nguyên văn từ prompt chế độ tách."""

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
    split_prompt_blocks,
)

from ..dinh_kem_tach import prompt as _tach

__all__ = ["DOC_TYPES", "SYSTEM_PROMPT", "build_user_prompt"]

DOC_TYPES = split_prompt_blocks(_tach.SYSTEM_PROMPT, "allowed_types", "type_definitions")

SYSTEM_PROMPT = build_system_prompt(
    "Đăng ký việc nuôi con nuôi trong nước",
    DOC_TYPES,
    '{"documents":[{"index":0,"docTypes":["adoption_application","identity"],"documentName":"Đơn xin nhận con nuôi"},'
    '{"index":1,"docTypes":["family_condition"],"documentName":"Xác nhận thu nhập"}]}',
    (
        "Không cần phân biệt giấy tờ của cha mẹ nuôi hay của trẻ/mẹ đẻ đối với identity, health, marital_status: hệ "
        "thống tự đối chiếu số định danh với đơn.",
        "documentName: tên giấy tờ ở trang đầu tệp theo tiêu đề in trên giấy, ≤ 50 ký tự, không dùng tên tệp; không "
        "xác định được → \"\".",
    ),
)
