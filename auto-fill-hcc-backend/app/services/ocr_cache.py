"""Cache OCR text theo HASH nội dung file (Mongo, collection `ocr_cache`).

Bù cho việc OCR LẠI cùng một file ở bước đính kèm sau khi đã OCR lúc fill. Khóa `_id` là
"v<ver>:<sha256(bytes file)>" — so khớp theo NỘI DUNG nên thêm/bớt/đổi tên/đổi thứ tự file đều
tự đúng (mỗi file tra riêng). Prefix version để đổi engine OCR thì bump là vô hiệu cache cũ.

BEST-EFFORT tuyệt đối: mọi lỗi cache đều nuốt, KHÔNG được làm hỏng OCR (giống traces/audit).
- Đọc: 1 query `$in` cho cả lô (khóa `_id` dùng index primary).
- Ghi: bulk upsert CHẠY NỀN (fire-and-forget) → không cộng độ trễ vào response.
"""
import asyncio
import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db.mongo import get_db

logger = logging.getLogger(__name__)

_KEY_VERSION = "v2-tiengnoi"  # Không tái sử dụng cache từ kiến trúc nhiều provider cũ.

# Giữ tham chiếu task ghi nền để không bị GC dọn giữa chừng.
_bg_tasks: set[asyncio.Task] = set()


def _decode(data_url: str) -> bytes | None:
    if not data_url:
        return None
    try:
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        return base64.b64decode(b64)
    except Exception:  # noqa: BLE001
        return None


def content_key(data_url: str) -> str | None:
    """Khóa cache từ NỘI DUNG file (dataUrl base64). None nếu không băm được (bỏ qua cache)."""
    raw = _decode(data_url)
    if raw is None:
        return None
    return f"{_KEY_VERSION}:{hashlib.sha256(raw).hexdigest()}"


def content_key_from_path(path: str) -> str | None:
    """Khóa cache cho file nằm trên ĐĨA — cùng một khóa với ``content_key`` của chính file đó.

    Upload-session truyền file bằng ``path`` (không dựng dataUrl để khỏi nạp cả file vào RAM),
    nên trước đây lượt OCR lúc nhận tệp không có khóa và KHÔNG vào được cache; lượt trích xuất
    sau đó gửi dataUrl của ĐÚNG file ấy lại thành cache miss và OCR lần hai.

    ``file_to_data_url`` base64 hóa đúng bytes đọc từ đĩa, nên băm bytes ở đây ra cùng sha256.
    Đọc theo khối để file lớn không nằm trọn trong RAM.
    """
    if not path:
        return None
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"{_KEY_VERSION}:{digest.hexdigest()}"
    except OSError as e:
        logger.warning("ocr_cache.content_key_from_path lỗi (bỏ qua): %s", e)
        return None


async def get_many(keys: list[str]) -> dict[str, dict]:
    """{key: {text, provider}} cho các key CÓ trong cache. 1 query $in. Lỗi/disabled -> {}."""
    keys = [k for k in keys if k]
    if not keys or not settings.ocr_cache_enabled:
        return {}
    try:
        # TTL monitor của Mongo chạy nền nên document có thể còn tồn tại một lúc sau khi hết hạn.
        # Chặn ngay ở tầng đọc để cache quá TTL tuyệt đối không được tái sử dụng.
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.ocr_cache_ttl_hours)
        cursor = get_db().ocr_cache.find(
            {"_id": {"$in": keys}, "created_at": {"$gte": cutoff}},
            {"text": 1, "provider": 1, "max_tokens": 1},
        )
        # `max_tokens` = trần sinh chữ của lượt OCR đã ghi. Text ghi ở trần THẤP có thể bị cắt
        # giữa chừng nên không dùng lại được cho lượt cần trần cao hơn — người gọi tự so.
        return {
            d["_id"]: {
                "text": d.get("text", ""),
                "provider": d.get("provider"),
                "max_tokens": d.get("max_tokens"),
            }
            async for d in cursor
        }
    except Exception as e:  # noqa: BLE001 — cache lỗi không được làm hỏng OCR
        logger.warning("ocr_cache.get_many lỗi (bỏ qua): %s", e)
        return {}


async def _bulk_upsert(items: list[tuple[str, str, str | None, int | None]]) -> None:
    from pymongo import UpdateOne

    now = datetime.now(timezone.utc)
    ops = [
        UpdateOne(
            {"_id": key},
            {"$set": {"text": text, "provider": provider,
                      "max_tokens": max_tokens, "created_at": now}},
            upsert=True,
        )
        for key, text, provider, max_tokens in items
    ]
    try:
        await get_db().ocr_cache.bulk_write(ops, ordered=False)
    except Exception as e:  # noqa: BLE001
        logger.warning("ocr_cache.bulk_write lỗi (bỏ qua): %s", e)


def put_many_bg(items: list[tuple[str, str, str | None, int | None]]) -> None:
    """Ghi cache CHẠY NỀN. Chỉ lưu item có text thật (bỏ rỗng/lỗi). Không có event loop -> bỏ qua.

    Mỗi item là ``(key, text, provider, max_tokens)`` — ghi kèm trần sinh chữ để lượt sau biết
    text này có đủ dày cho nhu cầu của nó hay không.
    """
    if not settings.ocr_cache_enabled:
        return
    items = [(k, t, p, m) for k, t, p, m in items if k and (t or "").strip()]
    if not items:
        return
    try:
        task = asyncio.create_task(_bulk_upsert(items))
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)
    except RuntimeError:
        # Gọi ngoài event loop (vd test đồng bộ) — bỏ qua ghi cache.
        pass
