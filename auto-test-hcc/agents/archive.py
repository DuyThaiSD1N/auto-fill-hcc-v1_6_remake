"""Đọc req đã lưu trữ từ kho "Quản lý nội bộ" (AUTOTEST_ARCHIVE_URL), cho req mà backend production đã xoá khỏi Mongo + đĩa.

Backend production gửi mỗi lượt sang kho rồi xoá tệp gốc, OCR, fields, câu trả lời LLM khỏi Mongo khoảng 30 phút sau lượt cuối.
Kho giữ đủ: GET /api/runs/<mã req> trả processRequests (fields, options, tệp), runs.autofill.trace / steps (lượt LLM có raw,
OCR theo sha), ocrTexts, formReview; tệp gốc tải ở /api/records/<bundleId>/files/<sha256>. Tài khoản chỉ cần vai trò viewer.

Tài khoản đọc từ server.env (gitignore), chỉ nằm trong RAM của dịch vụ. Module này chỉ đọc, không ghi gì vào kho.
"""
from __future__ import annotations

import threading
from pathlib import Path

import httpx

from config import ARCHIVE_PASSWORD, ARCHIVE_URL, ARCHIVE_USER

_lock = threading.Lock()
_client: httpx.Client | None = None


class ArchiveError(Exception):
    pass


def enabled() -> bool:
    return bool(ARCHIVE_URL and ARCHIVE_USER and ARCHIVE_PASSWORD)


def _login(client: httpx.Client) -> None:
    try:
        response = client.post("/api/auth/login", json={"username": ARCHIVE_USER, "password": ARCHIVE_PASSWORD})
    except httpx.HTTPError as reason:
        raise ArchiveError(f"Không gọi được kho lưu trữ: {reason}") from reason
    if response.status_code != 200:
        raise ArchiveError(f"Đăng nhập kho lưu trữ bị từ chối (HTTP {response.status_code}): kiểm tra AUTOTEST_ARCHIVE_USER / _PASSWORD.")


def _session() -> httpx.Client:
    global _client
    with _lock:
        if _client is None:
            _client = httpx.Client(base_url=ARCHIVE_URL.rstrip("/"), timeout=120, headers={"X-Vault-Client": "1"})
            _login(_client)
        return _client


def _get(path: str, stream_to: Path | None = None) -> httpx.Response | None:
    """GET có đăng nhập lại một lần khi phiên hết hạn. 404 trả None."""
    client = _session()
    for attempt in (1, 2):
        try:
            if stream_to is None:
                response = client.get(path)
            else:
                with client.stream("GET", path) as response:
                    if response.status_code == 200:
                        partial = stream_to.with_name(stream_to.name + ".part")
                        with partial.open("wb") as handle:
                            for chunk in response.iter_bytes():
                                handle.write(chunk)
                        partial.replace(stream_to)
        except httpx.HTTPError as reason:
            raise ArchiveError(f"Không đọc được kho lưu trữ: {reason}") from reason
        if response.status_code == 401 and attempt == 1:
            with _lock:
                _login(client)
            continue
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ArchiveError(f"Kho lưu trữ trả HTTP {response.status_code} cho {path.split('?')[0]}")
        return response
    return None


def get_run(request_id: str) -> dict | None:
    """Gói dữ liệu của một lượt theo mã req. None nếu kho không có."""
    response = _get(f"/api/runs/{request_id}")
    return response.json() if response is not None else None


def list_records(**params) -> dict:
    """Danh sách bản ghi của kho (mới nhất trước). Lọc được: type (request | conversation | upload_session), userId,
    procedure, kind, dateFrom, dateTo (YYYY-MM-DD giờ VN), q, page, pageSize. Hàng ``request`` có ``edited`` = số ô
    người dùng sửa trên form (từ ảnh chụp form)."""
    query = str(httpx.QueryParams({k: v for k, v in params.items() if v not in (None, "")}))
    response = _get(f"/api/records?{query}")
    return response.json() if response is not None else {"items": [], "total": 0}


def get_record(record_id: str) -> dict | None:
    """Một bản ghi: {meta, bundle, versions}. Bản ghi hội thoại có bundle.doc = document conversations lúc lưu."""
    response = _get(f"/api/records/{record_id}")
    return response.json() if response is not None else None


def find_conversation(conversation_id: str, user_id: str | None, day: str | None) -> dict | None:
    """Document hội thoại handfree (bundle.doc) của ``conversation_id``. API kho không lọc theo mã hội thoại nên lọc theo
    tài khoản + ngày rồi so mã; không có tài khoản thì không dò (quét cả kho quá chậm)."""
    if not conversation_id or not user_id:
        return None
    for page in (1, 2, 3):
        res = list_records(type="conversation", userId=user_id, dateFrom=day, dateTo=day, pageSize=100, page=page)
        items = res.get("items") or []
        for item in items:
            if item.get("conversationId") == conversation_id or item.get("key") == conversation_id:
                record = get_record(item["id"]) or {}
                return (record.get("bundle") or {}).get("doc")
        if len(items) < 100:
            return None
    return None


def download(bundle_id: str, sha256: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if _get(f"/api/records/{bundle_id}/files/{sha256}", stream_to=target) is None or not target.is_file():
        raise ArchiveError(f"Kho lưu trữ không có tệp {sha256[:12]}… của lượt này.")
