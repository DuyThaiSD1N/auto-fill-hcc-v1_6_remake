"""Quy tắc thuần của báo lỗi (quyền, mã lỗi, tên lỗi, trường trả về) — không chạm DB."""
import re
import unicodedata
from datetime import timezone

STATUSES = ("new", "doing", "done")
MAX_IMAGES = 10
MAX_TEXT = 4000
MAX_TITLE = 200
_TITLE_CUT = 70

# Ba vai trò, phân giải từ token qua phạm vi thống kê (app/dashboard/scope.py):
#   reporter : phường/xã — gửi lỗi, xem đủ lỗi của CHÍNH mình (gồm nội dung + ảnh + video).
#   viewer   : tài khoản Tỉnh — chỉ xem danh sách lỗi các xã trong tỉnh, không nội dung/ảnh/video.
#   manager  : admin — xem, sửa, đổi trạng thái mọi lỗi.
REPORTER, VIEWER, MANAGER = "reporter", "viewer", "manager"

# Tên xã thường lưu kèm cấp hành chính ("Phường Bắc Giang"); mã lỗi lấy chữ đầu của phần tên.
_KIND_PREFIX = re.compile(r"^(xã|phường|thị trấn|đặc khu|thị xã|thành phố)\s+", re.IGNORECASE)


def access_of(user: dict, scope: dict) -> str:
    if (user.get("role") or "user") == "admin":
        return MANAGER
    if scope.get("scopeKind") == "unit":
        return REPORTER
    return VIEWER


def _fold(text: str) -> str:
    raw = text.replace("Đ", "D").replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", raw) if unicodedata.category(c) != "Mn")


def code_prefix(ward: str | None, fallback: str | None = None) -> str:
    """"Phường Bắc Giang" → "BG". Không còn chữ cái nào thì dùng "HCC"."""
    name = _KIND_PREFIX.sub("", (ward or fallback or "").strip())
    letters = [w[0].upper() for w in _fold(name).split() if w[:1].isalpha()]
    return "".join(letters)[:6] or "HCC"


def format_code(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:02d}"


def make_title(text: str, procedure_label: str | None, *, video_only: bool = False) -> str:
    """Câu đầu của nội dung làm tên lỗi; admin sửa lại được trong bảng chi tiết."""
    first = re.split(r"[.!?\n]", text or "", maxsplit=1)[0].strip()
    if first:
        if len(first) <= _TITLE_CUT:
            return first
        cut = first[:_TITLE_CUT]
        return (cut.rsplit(" ", 1)[0] if " " in cut else cut) + "..."
    if procedure_label:
        return f"Lỗi thủ tục {procedure_label}"
    return "Lỗi kèm video" if video_only else "Lỗi kèm ảnh"


def iso(value):
    # Motor trả datetime không kèm múi giờ; giá trị lưu luôn là UTC.
    if not value:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _dossier(doc: dict) -> dict | None:
    d = doc.get("dossier")
    if not d:
        return None
    return {
        "dossierId": d.get("dossier_id"),
        "procedure": d.get("procedure"),
        "procedureLabel": d.get("procedure_label"),
        "startedAt": iso(d.get("started_at")),
        "experience": d.get("experience"),
    }


def _video(doc: dict) -> dict | None:
    video = doc.get("video")
    return {"type": video.get("type"), "size": video.get("size")} if video else None


def serialize(doc: dict, access: str) -> dict:
    """Trường trả về theo vai trò — cắt ở backend, giao diện không tự ẩn."""
    dossier = _dossier(doc)
    item = {
        "id": str(doc["_id"]),
        "code": doc.get("code"),
        "title": doc.get("title"),
        "status": doc.get("status"),
        "createdAt": iso(doc.get("created_at")),
        "procedureLabel": dossier["procedureLabel"] if dossier else None,
    }
    if access == VIEWER:
        item["unitName"] = doc.get("unit_name")
        return item
    item.update({
        "text": doc.get("text") or "",
        "imageCount": len(doc.get("images") or []),
        "video": _video(doc),
        "dossier": dossier,
        "updatedAt": iso(doc.get("updated_at")),
    })
    if access == MANAGER:
        item.update({
            "unitName": doc.get("unit_name"),
            "province": doc.get("province"),
            "reporterName": doc.get("reporter_name"),
        })
    return item


def serialize_log(entries: list[dict] | None) -> list[dict]:
    return [
        {"at": iso(e.get("at")), "by": e.get("by_name"), "action": e.get("action"), "to": e.get("to")}
        for e in entries or []
    ]
