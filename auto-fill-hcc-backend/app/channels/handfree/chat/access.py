"""Quyền sở hữu conversation của channel Handfree.

Conversation id là con trỏ trạng thái, không phải credential. Mọi API nhận id từ client
phải đối chiếu ``auth_user.id`` với JWT trước khi đọc, sửa hoặc tạo document session.
"""
from app.channels.handfree.chat import store
from app.core.errors import AppError


def ensure_conversation_owner(conv: dict, user: dict) -> dict:
    owner_id = str(((conv.get("auth_user") or {}).get("id")) or "").strip()
    user_id = str(user.get("id") or "").strip()
    if not owner_id or not user_id or owner_id != user_id:
        raise AppError(
            "CONVERSATION_FORBIDDEN",
            "Tài khoản không có quyền truy cập cuộc trò chuyện này",
            403,
        )
    return conv


async def get_owned_conversation(conv_id: str, user: dict) -> dict:
    conv = await store.get(conv_id)
    if conv is None:
        raise AppError(
            "CONVERSATION_NOT_FOUND",
            "Phiên không tồn tại hoặc đã hết hạn",
            404,
        )
    return ensure_conversation_owner(conv, user)
