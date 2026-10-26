"""Biên bản chấp thuận xử lý dữ liệu cá nhân kênh Handfree — dựng bằng bộ chung app/consent/pdf.py (thể thức Nghị
định 30, nguyên văn thẻ đã hiển thị, toàn văn Điều 4 Luật 91/2025/QH15).

Khác Auto Fill: người dân ở quầy không đăng nhập → biên bản định danh theo tài khoản VNeID đọc từ cổng (nếu có), MÃ
PHIÊN hội thoại, nơi làm thủ tục và tài khoản quầy; chỉ sinh cho lượt ĐỒNG Ý (lượt từ chối chỉ nằm trong Mongo).
"""
from datetime import datetime, timezone

from app.consent.pdf import VN_TZ, principal_text, render


def build_consent_pdf(entry: dict) -> tuple[bytes, str]:
    """entry = bản ghi consent_logs (chat/consent.py build_entry). Trả (PDF, mã SHA-256 nội dung)."""
    loc = entry.get("location") or {}
    place = ", ".join(x for x in (loc.get("ward"), loc.get("province")) if x) or "(chưa chọn)"
    at = entry.get("at") or datetime.now(timezone.utc)
    at = (at if at.tzinfo else at.replace(tzinfo=timezone.utc)).astimezone(VN_TZ)
    card = entry.get("notice") or {}
    notice = {
        "intro": card.get("intro_md"),
        "documents_title": "Giấy tờ được đọc trong thủ tục này:",
        "documents": list(entry.get("documents") or []),
        "scope": card.get("scope_md"),
        "purpose": card.get("purpose_md"),
    } if card else None
    checks = entry.get("checks") or []
    statements = [(s, i < len(checks) and bool(checks[i])) for i, s in enumerate(entry.get("statements") or [])]
    accept = card.get("accept_label") or "Đồng ý"
    method = (f"Bấm nút “{accept}” trên thẻ xác nhận" if entry.get("method") != "verbal"
              else "Nói hoặc gõ đồng ý trong khung trò chuyện")
    record = {
        "so": entry.get("_id") or "",
        "place": loc.get("ward") or loc.get("province") or "",
        "at": at,
        "version": entry.get("version"),
        "info": [
            ("Chủ thể dữ liệu (VNeID)", principal_text(entry.get("principal_cccd"), entry.get("principal_name"))),
            ("Mã phiên hội thoại", entry.get("conversation_id") or ""),
            ("Thủ tục", entry.get("procedure_label") or "(chưa xác định)"),
            ("Nơi làm thủ tục", place),
            ("Tài khoản quầy", entry.get("auth_username") or "(không đăng nhập)"),
            ("Kênh thực hiện", "Trợ lý nhân dân toàn trình (Handfree) — người dân thao tác bằng giọng nói, nút bấm"),
        ],
        "notice": notice,
        "statements": statements,
        "prechecked": bool(entry.get("prechecked")),
        "result": [
            ("Kết quả", "ĐỒNG Ý" if entry.get("accepted") else "KHÔNG ĐỒNG Ý"),
            ("Phương thức xác nhận", method),
            ("Thời điểm máy chủ ghi nhận", f"{entry.get('at_display') or f'{at:%H:%M ngày %d/%m/%Y}'} (giờ Việt Nam)"),
        ],
        "lang_note": ("Màn hình xác nhận hiển thị kèm bản dịch tiếng Mông để hỗ trợ người dân hiểu; bản tiếng Việt là "
                      "bản có giá trị pháp lý.") if entry.get("lang") == "hmong" else None,
    }
    return render(record)
