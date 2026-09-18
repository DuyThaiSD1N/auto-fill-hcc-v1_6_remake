"""Danh mục giọng đọc TTS cho Handfree — khai Ở ĐÂY, không rải trong env.

Trước đây mỗi ngôn ngữ chỉ có ĐÚNG MỘT giọng, chốt cứng bằng TTS_VOICE / TTS_VOICE_HMONG:
đổi giọng phải sửa .env rồi restart, và đổi là đổi cho MỌI phường. Giờ tách hai việc:

  - DANH MỤC (có những giọng nào, tên gọi ra sao) — hằng trong file này, vì đó là năng lực
    của server TTS, không phải tuỳ chọn triển khai;
  - LỰA CHỌN (máy quầy này dùng giọng nào) — lưu ở màn Cài đặt của extension, gửi kèm mỗi
    lần mở /ws/tts.

Env chỉ còn giữ MẶC ĐỊNH cho máy chưa chọn gì.

Tiếng Việt và tiếng Mông dùng CHUNG một server TTS, chỉ khác voiceId — nên thêm giọng là
thêm một dòng ở đây, không phải đấu nối dịch vụ mới.
"""
from app.config import settings

# Giọng nam tiếng Việt CHƯA có id từ nhà cung cấp TTS. Điền TTS_VOICE_VI_MALE vào .env là ô
# chọn tự hiện trên màn Cài đặt — KHÔNG phải sửa code, KHÔNG phải phát hành lại extension.
_VI_MALE_LABEL = "Giọng nam"


def _catalog() -> dict[str, list[dict]]:
    """Dựng lúc GỌI chứ không lúc import: env đọc sau khi settings đã nạp."""
    return {
        "vi": [
            {"id": settings.tts_voice, "label": "Cô Phương Nhi", "gender": "nu"},
            {"id": settings.tts_voice_vi_male, "label": _VI_MALE_LABEL, "gender": "nam"},
        ],
        # Hai giọng tiếng Mông đều có sẵn trên server.
        "hmong": [
            
            {"id": "xi", "label": "Cô Xi", "gender": "nu"},
            {"id": "vuado", "label": "Anh Dơ", "gender": "nam"},
        ],
    }


def voices_for(lang: str) -> list[dict]:
    """Các giọng dùng được của một ngôn ngữ. Giọng chưa có id thì KHÔNG trả về — màn Cài đặt
    dựa vào danh sách này nên ô chọn tự ẩn khi chỉ còn một giọng."""
    entries = _catalog().get(_norm_lang(lang)) or []
    return [entry for entry in entries if (entry.get("id") or "").strip()]


def default_voice(lang: str) -> str:
    """Giọng khi máy quầy chưa chọn gì (env). Env trỏ vào giọng không có trong danh mục thì
    vẫn dùng — đó là chủ ý của người deploy, danh mục chỉ phục vụ phần hiển thị."""
    return settings.tts_voice_hmong if _norm_lang(lang) == "hmong" else settings.tts_voice


def resolve_voice(lang: str, requested: str | None) -> str:
    """Giọng cuối cùng gửi lên server TTS.

    Client CHỈ được chọn trong danh mục: id lạ thì rơi về mặc định. Không kiểm ở đây là mở
    đường cho trang web bất kỳ bơm voiceId tuỳ ý qua query string của WebSocket.
    """
    wanted = str(requested or "").strip()
    if wanted and any(entry["id"] == wanted for entry in voices_for(lang)):
        return wanted
    return default_voice(lang)


def _norm_lang(lang: str) -> str:
    return "hmong" if str(lang or "").strip().lower() == "hmong" else "vi"
