"""Nhật ký chấp thuận xử lý dữ liệu cá nhân (Luật Bảo vệ DLCN 91/2025/QH15, Điều 4).

Chấp thuận phải có TRƯỚC khi hệ thống chạm vào giấy tờ — phiên upload OCR ngay lúc
nhận ảnh nên cổng consent đặt trước bước chọn cách gửi giấy tờ (flow `_to_ask_doc_method`).

Lưu collection `consent_logs` KHÔNG TTL: là bằng chứng pháp lý, không tự xoá theo phiên
(khác conversations/upload_sessions). Lượt ĐỒNG Ý sinh thêm PDF biên bản (consent_pdf.py)
ra `{storage_dir}/consent/<log_id>.pdf` — BE tự sinh, chống sửa; PDF lỗi vẫn lưu Mongo,
không chặn luồng. `build_entry` thuần — test flow không cần Mongo; chỉ `persist` chạm DB.
"""
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.db.mongo import get_db

logger = logging.getLogger(__name__)

# v1.2 (2026-08-07): "Mục đích xử lý" → "Mục đích chia sẻ, xử lý dữ liệu" + nói rõ dữ liệu
# chia sẻ lên Cổng DVC để nộp hồ sơ. v1.1: thêm phạm vi LƯU TRỮ hồ sơ phục vụ đối soát.
VERSION = "1.2"  # đổi khi SỬA nội dung xin phép (scope/checks) — log cũ giữ version cũ

# Việt Nam không có giờ mùa hè — offset cứng an toàn, khỏi phụ thuộc tzdata.
_VN_TZ = timezone(timedelta(hours=7))

SCOPE = (
    "Đọc và xử lý thông tin cần thiết từ giấy tờ người dân chủ động cung cấp; "
    "tự động điền biểu mẫu và chuẩn bị tệp đính kèm cho thủ tục đang thực hiện; "
    "chia sẻ dữ liệu đã trích xuất lên Cổng Dịch vụ công để nộp hồ sơ theo yêu cầu "
    "của người dân; lưu trữ hồ sơ đã xử lý (ảnh giấy tờ, kết quả đọc) trên hệ thống "
    "phục vụ đối soát và hỗ trợ giải quyết thủ tục"
)


def build_entry(conv: dict, proc: dict, accepted: bool,
                method: str = "chip", checks: list | None = None) -> dict:
    from app.chat import script_vi as vi  # import trễ — script_vi là file text, tránh vòng

    now = datetime.now(timezone.utc)
    loc = conv.get("location") or {}
    return {
        "_id": f"TLND-{secrets.token_hex(4).upper()}",
        "conversation_id": conv.get("_id", ""),
        "procedure_key": conv.get("procedure_key") or "",
        "procedure_label": proc.get("shortLabel") or proc.get("label", ""),
        "accepted": bool(accepted),
        # chip: bấm nút trên card | verbal: nói/gõ "đồng ý" (khẳng định tường minh vẫn hợp lệ)
        "method": method,
        "checks": list(checks or []),
        # Nguyên văn 2 câu cam kết TẠI THỜI ĐIỂM tick — script sửa sau này không đổi được log cũ.
        "statements": list(vi.CONSENT_CARD_TEXT["checks"]),
        "version": VERSION,
        "scope": SCOPE,
        "documents": [d.get("name", "") for d in (proc.get("requiredDocs") or [])],
        "location": {"province": loc.get("province", ""), "ward": loc.get("ward", "")},
        "auth_username": (conv.get("auth_user") or {}).get("username", ""),
        # Chủ thể dữ liệu = tài khoản VNeID đang đăng nhập trên cổng (content đọc, đến theo
        # page_status). Ưu tiên CCCD (cổng tư pháp moj) → tên → không có thì gắn theo mã phiên.
        "principal_cccd": (conv.get("portal_principal") or {}).get("cccd"),
        "principal_name": (conv.get("portal_principal") or {}).get("name"),
        "at": now,
        "at_display": now.astimezone(_VN_TZ).strftime("%H:%M ngày %d/%m/%Y"),
    }


def _consent_dir() -> Path:
    p = Path(settings.storage_dir) / "consent"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "consent")[:60]


async def persist(entry: dict) -> None:
    doc = dict(entry)
    if doc.get("accepted"):
        # PDF biên bản chỉ cho lượt đồng ý (user chốt) — bằng chứng chấp thuận như auto-fill.
        try:
            from app.chat.consent_pdf import build_consent_pdf

            fname = f"{_safe(doc['_id'])}.pdf"
            (_consent_dir() / fname).write_bytes(build_consent_pdf(doc))
            doc["pdf_path"] = str(Path("consent") / fname)
        except Exception as e:  # noqa: BLE001 — PDF là phụ, Mongo mới là bản ghi gốc
            logger.warning("[consent] sinh PDF lỗi (%s): %s", doc.get("_id"), e)
    await get_db().consent_logs.insert_one(doc)
