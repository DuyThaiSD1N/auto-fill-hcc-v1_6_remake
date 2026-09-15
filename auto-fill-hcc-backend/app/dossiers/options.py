"""Đọc khóa hồ sơ Auto Fill từ `options` mà extension gửi lên.

Auto Fill KHÔNG có conversation như Handfree, nên extension tự sinh `dossierId` (UUID) và
giữ trong `autofill_session_<tabId>` — sống qua reload, chết theo tab/đăng xuất/đổi thủ tục/
"Tạo phiên mới"/bấm nộp. Xem popup.js.

Trường này là TÙY CHỌN: extension bản cũ trên chợ không gửi, và khi đó mọi thứ chạy y như
trước (trace không có dossier_id, không có document nào trong `dossiers`).

ĐỪNG nhầm với `options.sessionId`: cái đó là request_id của LƯỢT QUÉT, cố ý đổi mỗi lần quét
lại để planner đính kèm bám đúng lượt mới nhất (popup.js). Nó không phải danh tính hồ sơ.
"""

_MAX_LEN = 64


def dossier_id_from_options(options: dict | None) -> str | None:
    """Chuỗi sạch hoặc None. Chặn độ dài để client không bơm khóa rác vào index."""
    raw = str((options or {}).get("dossierId") or "").strip()
    if not raw or len(raw) > _MAX_LEN:
        return None
    return raw
