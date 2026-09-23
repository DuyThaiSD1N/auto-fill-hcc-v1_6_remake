"""Conversation store — phiên hội thoại toàn trình (docs/03a §1-2).

Nguồn sự thật DUY NHẤT của phiên nằm ở đây (Mongo `conversations`, TTL 24h trượt theo
updated_at — index khai ở app/db/indexes.py). FE chỉ giữ con trỏ conversation_id.
"""
import uuid
from datetime import datetime, timezone

from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_conversation(location: dict | None = None) -> dict:
    return {
        "_id": f"c-{uuid.uuid4().hex[:20]}",
        "state": "greet",
        "location": location or {},          # {province, province_slug, ward}
        # Key thuộc executionSubject.options của flow tư pháp. Chỉ authorized_person
        # bật thêm khối thông tin ủy quyền; các key còn lại dùng khối owner cơ bản.
        "execution_subject": "self",
        "procedure_key": None,
        "doc_method": None,                   # qr | scan | profile
        "upload_session_id": None,
        "form_context": {},                  # options.formContext đọc từ form cổng đang mở
        "attachment_context": {},            # cấu trúc bảng thành phần hồ sơ đọc từ DOM
        "attachment_context_url": "",        # URL nguồn để tránh dùng nhầm context của trang cũ
        "attachment_preferences": {},        # splitDocuments; mặc định thiếu = giữ nguyên file
        "client_capabilities": {},            # thương lượng contract với extension đã cài
        "fields": [],                         # kết quả pipeline (hợp đồng cũ) — Bước 6
        "fill_report": {},                    # {filled, missing, assumed} — Bước 6
        "owner_context": {},                  # định danh đọc từ trang Thông tin chủ hồ sơ
        "owner_fields": [],                   # owner + auth fields do backend quyết định theo nhánh
        "authorization_match": {},            # gate giấy ủy quyền + đúng người nhận
        "owner_fill_report": {},
        "owner_info_done": False,
        # Mục đích của lượt nhận giấy tờ hiện tại, suy ra từ CHÍNH bước wizard đang mở.
        # Không dùng owner_phase để dispatch vì công dân có thể bỏ qua bước chủ hồ sơ và
        # đi thẳng tới kê khai/thành phần hồ sơ.
        "docs_target": "",                     # owner | declaration | attachment | business
        "docs_page_context": {},               # wizardStep/formKind/attachmentTarget đã làm sạch
        "docs_dispatch_key": "",               # khóa chốt trùng theo upload-session + target
        "main_processing_started": False,
        # Chỉ bật khi extension mới bắt đầu pipeline ngay tại trang kê khai. Sau khi điền,
        # watcher sẽ chờ đúng bước Thành phần hồ sơ rồi mới chạy planner bằng cùng phiên tệp.
        "auto_attach_after_fill": False,
        "attachment_plan_started": False,
        "attach_action_in_progress": False,       # khóa race attach_ready ↔ page_status
        # Lease chỉ bật với extension công bố supportsAttachActionLease. Nếu sidebar mất sau
        # khi nhận plan mà chưa kịp report, backend được phép phát lại sau khi lease hết hạn.
        "attach_action_dispatch_id": "",
        "attach_action_lease_until": None,
        "attach_done": False,
        # Công dân có thể mở lại CHÍNH phiên giấy tờ cũ để thêm/xóa, rồi chạy lại đúng
        # pipeline của bước đã mở yêu cầu (kê khai hoặc đính kèm). Không tạo phiên rỗng và
        # không làm mất các tệp đã cung cấp trước đó.
        "supplementing_documents": False,
        "supplement_reuse_session": False,
        "documents_adjustment_target": "",     # declaration | attachment
        # HkdOnline WebForms: backend chuẩn bị một bundle 8 trang + attach; extension
        # tự resume qua full postback và báo lại đúng một business_result.
        "business_pages": {},
        "business_result": None,
        "business_prepare_started": False,
        "business_action_started": False,
        "awaiting_events": [],                # watcher FE chỉ canh đúng những event này
        "phone": None,
        "profile_id": None,
        "history": [],                        # [{role, text, state, source, ts}]
        "last_reply": None,                   # Reply đã render lượt gần nhất (khôi phục sidebar)
        "created_at": _now(),
        "updated_at": _now(),
    }


async def get(conv_id: str) -> dict | None:
    if not conv_id:
        return None
    return await get_db().conversations.find_one({"_id": conv_id})


async def save(conv: dict) -> None:
    conv["updated_at"] = _now()
    await get_db().conversations.replace_one({"_id": conv["_id"]}, conv, upsert=True)


def push_history(conv: dict, role: str, text: str, source: str = "") -> None:
    conv["history"].append({
        "role": role,
        "text": text,
        "state": conv.get("state", ""),
        "source": source,
        "ts": _now(),
    })
    # Giữ history gọn (phiên dài chủ yếu là sự kiện) — 200 lượt là quá đủ để khôi phục UI.
    if len(conv["history"]) > 200:
        conv["history"] = conv["history"][-200:]


def drop_last_bot_history(conv: dict, state: str) -> bool:
    """Xoá câu bot GẦN NHẤT nếu nó được nói ở `state` đó. Trả True khi có xoá.

    Dùng khi một lời hỏi hết hiệu lực vì trang đã sang bước khác: để lại thì khôi phục phiên
    dựng lại đúng câu đã sai bước. Chỉ soi ĐÚNG bản ghi bot cuối — câu bot cũ hơn vẫn là thứ
    công dân đã thấy và trả lời, xoá theo là viết lại lịch sử.
    """
    history = conv.get("history") or []
    for index in range(len(history) - 1, -1, -1):
        if history[index].get("role") != "bot":
            continue
        if history[index].get("state") == state:
            history.pop(index)
            return True
        return False
    return False
