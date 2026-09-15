"""Đếm hồ sơ theo MỐC NỘP THẬT — cách đếm áp dụng từ 15/9/2026 (xem app/stats/cutover.py).

Khác hẳn cách cũ ở app/traces/repo.py: bên đó SUY RA số hồ sơ từ trace (gom các lượt
điền/đính kèm có tập tên tệp trùng/lồng nhau) nên kết quả luôn mang nhãn "ước tính". Ở đây
một hồ sơ là một document trong `dossiers` — có vòng đời bắt đầu → bấm nộp → đóng — và
CHỈ hồ sơ đã có mốc nộp mới được tính. Hồ sơ làm dở không vào số liệu (vẫn còn ở Nhật ký
hồ sơ để nhìn tỷ lệ bỏ dở).

MỘT HỒ SƠ = MỘT, kể cả bấm nộp nhiều lần. Chứng thực bản sao tách nhiều tab dùng CHUNG một
khóa hồ sơ và bấm nộp N lần; cách cũ tính N hồ sơ, từ nay tính 1. Vì vậy ở đây đếm số
DOCUMENT chứ không đếm số phần tử `submit_events` — đừng đổi thành $sum submit_count.

Mốc ngày của hồ sơ = LẦN NỘP ĐẦU TIÊN, không phải lần cuối. `submit_clicked_at` bị ghi đè
mỗi lần bấm, nên lấy nó làm mốc thì một hồ sơ đã chốt của hôm qua có thể nhảy sang hôm nay
chỉ vì cán bộ bấm nộp lại — con số của ngày cũ không được phép chạy ngược về sau.
"""
from datetime import datetime

from app.db.mongo import get_db

# Mốc nộp sớm nhất của hồ sơ. `submit_events` có từ bản 1.18; document cũ hơn (nếu có) chỉ
# mang `submit_clicked_at` nên phải dự phòng, không thì rơi mất khỏi thống kê.
_FIRST_SUBMIT = {
    "$set": {
        "_first_submit": {
            "$ifNull": [{"$min": "$submit_events.at"}, "$submit_clicked_at"]
        }
    }
}


def _match(user_ids: list[str] | None, date_from: datetime, experience: str | None) -> dict:
    """Lọc thô bằng INDEX trước khi tính mốc nộp đầu.

    Chặn dưới đặt trên `submit_clicked_at` (đã có index) là an toàn: nó luôn ≥ lần nộp đầu,
    nên hồ sơ nào có lần nộp đầu trong khoảng thì chắc chắn lọt qua đây. KHÔNG đặt chặn trên
    ở đây — hồ sơ nộp lần đầu trong khoảng rồi bấm lại sau khoảng sẽ bị loại oan.
    """
    query: dict = {"submit_clicked_at": {"$ne": None, "$gte": date_from}}
    if user_ids is not None:
        query["user_id"] = {"$in": user_ids}
    if experience:
        query["experience"] = experience
    return query


def _unique_ids(user_ids: list[str] | None) -> list[str] | None:
    """None = KHÔNG giới hạn đơn vị (thống kê quản trị phạm vi toàn hệ thống).

    Khác hẳn danh sách RỖNG, nghĩa là "phạm vi không có đơn vị nào" → không có gì để đếm.
    Trộn hai thứ này là bảng thống kê phường sẽ lòi ra số liệu của cả nước.
    """
    if user_ids is None:
        return None
    return list(dict.fromkeys(str(value) for value in user_ids if value))


async def submitted_counts(
    *,
    user_ids: list[str] | None,
    date_from: datetime,
    date_to: datetime,
    experience: str | None = "autofill",
) -> list[dict]:
    """[{userId, procedure, label, name, count}] — số hồ sơ ĐÃ NỘP theo đơn vị × thủ tục."""
    ids = _unique_ids(user_ids)
    if ids is not None and not ids:
        return []
    pipeline = [
        {"$match": _match(ids, date_from, experience)},
        _FIRST_SUBMIT,
        {"$match": {"_first_submit": {"$gte": date_from, "$lt": date_to}}},
        {
            "$group": {
                "_id": {
                    "userId": {"$ifNull": ["$user_id", "—"]},
                    "procedure": {"$ifNull": ["$procedure", "—"]},
                },
                "name": {"$first": {"$ifNull": ["$name", {"$ifNull": ["$username", "—"]}]}},
                "label": {"$first": {"$ifNull": ["$procedure_label", "$procedure"]}},
                "count": {"$sum": 1},
            }
        },
    ]
    rows = await get_db().dossiers.aggregate(pipeline, allowDiskUse=True).to_list(length=100000)
    return [
        {
            "userId": str(row["_id"]["userId"]),
            "procedure": str(row["_id"]["procedure"]),
            "label": row.get("label") or str(row["_id"]["procedure"]),
            "name": row.get("name") or str(row["_id"]["userId"]),
            "count": int(row.get("count") or 0),
        }
        for row in rows
    ]


async def submitted_daily_counts(
    *,
    user_ids: list[str] | None,
    date_from: datetime,
    date_to: datetime,
    experience: str | None = "autofill",
) -> list[dict]:
    """[{userId, date, count}] — hồ sơ đã nộp theo NGÀY nộp đầu tiên, múi giờ Việt Nam.

    Cùng hợp đồng với traces_repo.daily_dossier_counts_by_user_ids để biểu đồ theo ngày ghép
    được hai bên mốc mà không phải đổi tầng trên.
    """
    ids = _unique_ids(user_ids)
    if ids is not None and not ids:
        return []
    pipeline = [
        {"$match": _match(ids, date_from, experience)},
        _FIRST_SUBMIT,
        {"$match": {"_first_submit": {"$gte": date_from, "$lt": date_to}}},
        {
            "$group": {
                "_id": {
                    "userId": {"$ifNull": ["$user_id", "—"]},
                    "day": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$_first_submit",
                            "timezone": "+07:00",
                        }
                    },
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.userId": 1, "_id.day": 1}},
    ]
    rows = await get_db().dossiers.aggregate(pipeline, allowDiskUse=True).to_list(length=100000)
    return [
        {
            "userId": str(row["_id"]["userId"]),
            "date": str(row["_id"]["day"]),
            "count": int(row.get("count") or 0),
        }
        for row in rows
        if row["_id"].get("day")
    ]
