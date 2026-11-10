"""Lời cổng nháy ở toast (thiếu dữ liệu, sai định dạng…) khi công dân / cán bộ tự bấm trên cổng.

Toast tắt sau vài giây và hay nằm đúng dưới khung Trợ lý → mở Trợ lý ra là không thấy cổng báo gì. Extension bắt toast
cảnh báo / lỗi mới hiện (không gửi toast thành công, không gửi toast nảy ra từ chính cú bấm của trợ lý) và gửi
__event:portal_alert:{"text": …}; ở đây trợ lý nói lại nguyên lời cổng, không đổi bước.
Bật khi extension khai supportsPortalAlert; chỉ tiếng Việt (lời cổng là tiếng Việt, câu thoại chưa có bản Mông).
"""
import re

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import script_vi as vi

CAPABILITY = "supportsPortalAlert"
_MAX_CHARS = 200
# Chưa vào hồ sơ, hoặc trợ lý đang tự điền: toast do chính thao tác điền gây ra, kết quả điền đã có câu báo riêng.
_SILENT_STATES = {"greet", "confirm_procedure", "filling", "owner_filling"}


def handle(conv: dict, intent):
    """Sự kiện portal_alert → Reply (rỗng = im lặng); sự kiện khác → None."""
    if intent.kind != "event" or intent.value != "portal_alert":
        return None
    from app.channels.handfree.chat.flow import Reply

    text = re.sub(r"\s+", " ", str((intent.payload or {}).get("text") or "")).strip()[:_MAX_CHARS]
    if (not text or (conv.get("lang") or "vi") != "vi"
            or (conv.get("client_capabilities") or {}).get(CAPABILITY) is not True
            or conv.get("state") in _SILENT_STATES or conv.get("attach_action_in_progress")):
        return Reply()
    return Reply(*field_review._say(vi.PORTAL_ALERT, text=text))
