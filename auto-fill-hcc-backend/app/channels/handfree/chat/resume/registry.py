"""Chọn adapter khôi phục theo họ cổng (flowProfile của thủ tục). Họ cổng mới: thêm một file adapter + một dòng ở đây."""
from app.channels.handfree.chat.resume.base import ResumeAdapter
from app.channels.handfree.chat.resume.tu_phap_cu import TuPhapCuAdapter
from app.channels.handfree.procedure_registry import get_procedure

CAPABILITY = "supportsResume"
# Thí điểm: chỉ các thủ tục này mới lưu / gợi ý khôi phục.
PILOT_PROCEDURES = frozenset({"ket-hon"})
_FAMILIES: dict[str, ResumeAdapter] = {TuPhapCuAdapter.family: TuPhapCuAdapter()}


def adapter_for(conv: dict) -> ResumeAdapter | None:
    key = str(conv.get("procedure_key") or "")
    if key not in PILOT_PROCEDURES or not (conv.get("client_capabilities") or {}).get(CAPABILITY):
        return None
    # Câu thoại khôi phục chưa có bản Mông: ghép vào lượt Mông là giọng Mông đọc chữ Việt.
    if (conv.get("lang") or "vi") == "hmong":
        return None
    return _FAMILIES.get(str((get_procedure(key) or {}).get("flowProfile") or ""))
