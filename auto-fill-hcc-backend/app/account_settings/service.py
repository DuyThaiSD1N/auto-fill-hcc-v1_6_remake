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
