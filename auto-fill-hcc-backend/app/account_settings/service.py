"""Cài đặt của CHÍNH tài khoản đang đăng nhập, dùng chung cho cả hai extension.

Lưu trong document user (`users.account_settings`) chứ không ở máy quầy: máy quầy dùng chung
nhiều cán bộ, và cán bộ đổi máy vẫn giữ cài đặt. Khoá thiếu trong DB = giá trị ở DEFAULTS —
tài khoản cũ chưa từng lưu chạy y hành vi trước khi có cài đặt.
"""
from bson import ObjectId

from app.db.mongo import get_db

FIELD = "account_settings"

DEFAULTS: dict[str, object] = {
    # Đổi tên tệp theo loại giấy tờ khi đính kèm lên cổng (extension quyết định tên tệp).
    "renameAttachmentFiles": True,
    # Handfree: lấy người nộp theo tờ khai (bỏ so khớp tài khoản đăng nhập) → options.submitterMode của pipeline.
    "submitterFromDeclaration": False,
    # Handfree: tỉ lệ cỡ chữ của khung Trợ lý (extension phóng cả khung). Khoảng 0.9–1.3 do router chặn: nhỏ hơn thì
    # chữ phụ dưới 10px khó đọc, lớn hơn thì khung 400px còn chưa tới 310px, các khối rộng bị vỡ.
    "fontScale": 1.0,
    # Handfree: giọng đọc + tốc độ cán bộ chọn. Rỗng / null = theo mặc định ở web quản trị (tab Giọng nói), giọng không
    # còn trong bảng thì BE dùng giọng dự phòng (voice/store.py) — lưu ở đây không cần kiểm lại.
    "ttsVoiceVi": "",
    "ttsVoiceHmong": "",
    "ttsTempo": None,
}


def resolve(user: dict) -> dict[str, object]:
    stored = user.get(FIELD) or {}
    if not isinstance(stored, dict):
        stored = {}
    return {key: stored.get(key, default) for key, default in DEFAULTS.items()}


async def update(user: dict, changes: dict[str, object]) -> dict[str, object]:
    changes = {key: value for key, value in changes.items() if key in DEFAULTS and value is not None}
    if not changes:
        return resolve(user)
    doc = await get_db().users.find_one_and_update(
        {"_id": ObjectId(user["id"])},
        {"$set": {f"{FIELD}.{key}": value for key, value in changes.items()}},
        projection={FIELD: 1},
        return_document=True,
    )
    return resolve(doc or {})
