"""Mốc đổi cách ĐẾM HỒ SƠ cho bảng thống kê và báo cáo Excel.

    đến hết 14/9/2026 : cách CŨ — suy số hồ sơ từ trace (app/traces/repo.py)
    từ 15/9/2026      : cách MỚI — đếm hồ sơ ĐÃ NỘP (app/dossiers/stats.py)

Có một mốc THỨ HAI, sớm hơn một ngày và nằm gọn trong cách cũ: từ 14/9/2026 chứng thực bản
sao tách nhiều tab chỉ tính MỘT hồ sơ (xem _CERT_SINGLE_DOSSIER_FROM ở app/traces/repo.py).
Hai mốc cố ý lệch nhau nên đừng gộp làm một.

Vì sao không sửa thẳng cách cũ: báo cáo các tháng trước đã xuất Excel nộp tỉnh. Sửa tiêu chí
ở tầng đọc là mở lại kỳ cũ ra con số khác — không ai đối chiếu được nữa. Nên app/traces/repo.py
giữ NGUYÊN VẸN, mọi thứ mới nằm ở đây.

Khoảng ngày vắt qua mốc thì CẮT ĐÔI rồi cộng, chứ không lấy cả khoảng trừ đi phần mới: cách
cũ gom hồ sơ theo tập tên tệp nên không cộng trừ được — một hồ sơ có lượt ở cả hai bên mốc
tính trên cả khoảng ra 1, tính trên từng nửa ra 2.

`requests` (số LƯỢT xử lý) và thống kê tài liệu dùng lại vẫn lấy từ trace trên TOÀN khoảng,
không đụng tới: đó là chỉ số khác, không phải số hồ sơ.
"""
from datetime import datetime, timedelta, timezone

from app.dossiers import stats as dossiers_stats
from app.traces import repo as traces_repo
from app.traces.date_range import VIETNAM_TZ

# 00:00 ngày 15/9/2026 giờ Việt Nam. Đổi mốc thì đổi ĐÚNG một dòng này.
SUBMITTED_COUNT_FROM = datetime(2026, 9, 15, tzinfo=VIETNAM_TZ).astimezone(timezone.utc)

# Màn quản trị cho phép bỏ trống hai đầu khoảng ("xem tất cả") — quy về mốc hữu hạn để so
# với mốc đổi cách đếm, giống app/dashboard/router.py đang làm.
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def counting_info(date_from: datetime | None, date_to: datetime | None) -> dict:
    """Cách đếm đang áp cho khoảng này, để màn hình nói rõ với cán bộ.

    "mixed" là trường hợp dễ gây hiểu nhầm nhất (bộ lọc "Tất cả" luôn rơi vào đây): một nửa
    là ước tính theo lượt, nửa kia là hồ sơ đã nộp — không nói thì cán bộ tưởng số tụt.

    Hai đầu để trống (màn quản trị cho phép) nghĩa là không chặn — quy về mốc hữu hạn để so.
    """
    date_from = date_from or _EPOCH
    date_to = date_to or (datetime.now(timezone.utc) + timedelta(days=1))
    if date_to <= SUBMITTED_COUNT_FROM:
        mode = "legacy"
    elif date_from >= SUBMITTED_COUNT_FROM:
        mode = "submitted"
    else:
        mode = "mixed"
    return {
        "mode": mode,
        "submittedFrom": SUBMITTED_COUNT_FROM.astimezone(VIETNAM_TZ).strftime("%Y-%m-%d"),
    }


def _counts_by_bucket(stats: dict) -> dict[tuple[str, str], dict]:
    """Rút số hồ sơ theo (đơn vị, thủ tục) ra khỏi kết quả cách cũ."""
    buckets: dict[tuple[str, str], dict] = {}
    for ward in stats.get("wards") or []:
        user_id = str(ward.get("userId") or "—")
        for procedure in ward.get("procedures") or []:
            key = (user_id, str(procedure.get("key") or "—"))
            bucket = buckets.setdefault(key, {
                "count": 0,
                "estimated": 0,
                "name": ward.get("name") or user_id,
                "label": procedure.get("label") or key[1],
            })
            bucket["count"] += int(procedure.get("count") or 0)
            bucket["estimated"] += int(procedure.get("estimated") or 0)
    return buckets


def _add_new_counts(buckets: dict[tuple[str, str], dict], rows: list[dict]) -> None:
    """Cộng phần đếm theo mốc nộp thật. Phần này CHÍNH XÁC nên estimated luôn là 0."""
    for row in rows:
        key = (str(row.get("userId") or "—"), str(row.get("procedure") or "—"))
        bucket = buckets.setdefault(key, {
            "count": 0,
            "estimated": 0,
            "name": row.get("name") or key[0],
            "label": row.get("label") or key[1],
        })
        bucket["count"] += int(row.get("count") or 0)


def _rebuild(base: dict, buckets: dict[tuple[str, str], dict]) -> dict:
    """Dựng lại wards/procedures/tổng từ số hồ sơ đã gộp, giữ nguyên phần còn lại của `base`.

    `base` là kết quả cách cũ trên TOÀN khoảng — chỉ mượn lại `requests`, tên đơn vị và khối
    thống kê tài liệu. Riêng số hồ sơ bị thay hoàn toàn bằng `buckets`.

    Đơn vị/thủ tục có lượt xử lý nhưng 0 hồ sơ vẫn được liệt kê (count = 0): bảng "Theo đơn vị"
    cần thấy đơn vị có hoạt động mà chưa nộp được hồ sơ nào.
    """
    requests_by_bucket: dict[tuple[str, str], int] = {}
    names: dict[str, str] = {}
    extras: dict[str, dict] = {}
    labels: dict[tuple[str, str], str] = {}
    for ward in base.get("wards") or []:
        user_id = str(ward.get("userId") or "—")
        names[user_id] = ward.get("name") or user_id
        # Thống kê quản trị gắn thêm `role` vào từng dòng đơn vị sau khi tổng hợp. Dựng lại
        # mà bỏ rơi các khóa lạ là màn quản trị mất cột phân loại tài khoản.
        extras[user_id] = {
            key: value for key, value in ward.items()
            if key not in {"userId", "name", "total", "exact", "estimated", "requests", "procedures"}
        }
        for procedure in ward.get("procedures") or []:
            key = (user_id, str(procedure.get("key") or "—"))
            requests_by_bucket[key] = requests_by_bucket.get(key, 0) + int(procedure.get("requests") or 0)
            labels[key] = procedure.get("label") or key[1]

    wards: dict[str, dict] = {}
    procedures: dict[str, dict] = {}
    total_dossiers = 0
    estimated_dossiers = 0

    for key in sorted(set(requests_by_bucket) | set(buckets)):
        user_id, procedure_key = key
        bucket = buckets.get(key) or {}
        count = int(bucket.get("count") or 0)
        estimated = int(bucket.get("estimated") or 0)
        requests = requests_by_bucket.get(key, 0)
        label = bucket.get("label") or labels.get(key) or procedure_key
        ward = wards.setdefault(user_id, {
            **extras.get(user_id, {}),
            "userId": user_id,
            "name": names.get(user_id) or bucket.get("name") or user_id,
            "total": 0,
            "exact": 0,
            "estimated": 0,
            "requests": 0,
            "procedures": [],
        })
        ward["total"] += count
        ward["exact"] += count - estimated
        ward["estimated"] += estimated
        ward["requests"] += requests
        ward["procedures"].append({
            "key": procedure_key,
            "label": label,
            "count": count,
            "exact": count - estimated,
            "estimated": estimated,
            "requests": requests,
        })
        proc = procedures.setdefault(procedure_key, {
            "key": procedure_key,
            "label": label,
            "count": 0,
            "requests": 0,
            "exact": 0,
            "estimated": 0,
        })
        proc["count"] += count
        proc["requests"] += requests
        proc["exact"] += count - estimated
        proc["estimated"] += estimated
        total_dossiers += count
        estimated_dossiers += estimated

    for ward in wards.values():
        ward["procedures"].sort(key=lambda item: (-item["count"], item["label"]))

    exact_dossiers = total_dossiers - estimated_dossiers
    if estimated_dossiers == 0:
        quality = "exact"
    elif exact_dossiers == 0:
        quality = "estimated"
    else:
        quality = "mixed"

    return {
        **base,
        "wards": sorted(wards.values(), key=lambda ward: (-ward["total"], ward["name"])),
        "procedures": sorted(procedures.values(), key=lambda proc: (-proc["count"], proc["label"])),
        "totalDossiers": total_dossiers,
        "exactDossiers": exact_dossiers,
        "estimatedDossiers": estimated_dossiers,
        "dataQuality": quality,
    }


async def dossier_stats(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    experience: str = "autofill",
) -> dict:
    """Thay thế traces_repo.stats_by_user_ids, có áp mốc đổi cách đếm.

    Khoảng nằm trọn trước mốc → trả thẳng kết quả cách cũ, không thêm một truy vấn nào.
    """
    base = await traces_repo.stats_by_user_ids(
        user_ids=user_ids, date_from=date_from, date_to=date_to, experience=experience,
    )
    if date_to <= SUBMITTED_COUNT_FROM:
        return base

    buckets: dict[tuple[str, str], dict] = {}
    if date_from < SUBMITTED_COUNT_FROM:
        # Phải chạy LẠI trên đúng nửa trước mốc: số hồ sơ của `base` tính trên cả khoảng nên
        # đã gộp lẫn các lượt sau mốc vào.
        old = await traces_repo.stats_by_user_ids(
            user_ids=user_ids,
            date_from=date_from,
            date_to=SUBMITTED_COUNT_FROM,
            experience=experience,
        )
        buckets = _counts_by_bucket(old)

    _add_new_counts(buckets, await dossiers_stats.submitted_counts(
        user_ids=user_ids,
        date_from=max(date_from, SUBMITTED_COUNT_FROM),
        date_to=date_to,
        experience=experience,
    ))
    return _rebuild(base, buckets)


async def admin_stats(
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    scope: str = "all",
    experience: str | None = "autofill",
) -> dict:
    """Thay thế traces_repo.stats cho màn Thống kê của trang quản trị.

    Khác `dossier_stats`: phạm vi ở đây là VAI TRÒ tài khoản ("all" / "official") chứ không
    phải một tập đơn vị, và hai đầu khoảng có thể bỏ trống (xem tất cả).
    """
    base = await traces_repo.stats(
        date_from=date_from, date_to=date_to, scope=scope, experience=experience,
    )
    start = date_from or _EPOCH
    end = date_to or (datetime.now(timezone.utc) + timedelta(days=1))
    if end <= SUBMITTED_COUNT_FROM:
        return base

    buckets: dict[tuple[str, str], dict] = {}
    if start < SUBMITTED_COUNT_FROM:
        old = await traces_repo.stats(
            date_from=date_from, date_to=SUBMITTED_COUNT_FROM, scope=scope, experience=experience,
        )
        buckets = _counts_by_bucket(old)

    _add_new_counts(buckets, await dossiers_stats.submitted_counts(
        # scope "all" → None = không giới hạn tài khoản. Chỉ "official" mới cần liệt kê id,
        # và lấy đúng bộ lọc vai trò mà cách cũ đang dùng để hai bên mốc cùng một phạm vi.
        user_ids=None if scope == "all" else await traces_repo.stats_scope_user_ids(scope),
        date_from=max(start, SUBMITTED_COUNT_FROM),
        date_to=end,
        experience=experience,
    ))
    return _rebuild(base, buckets)


async def daily_dossier_counts(
    *,
    user_ids: list[str],
    date_from: datetime,
    date_to: datetime,
    experience: str = "autofill",
) -> list[dict]:
    """Thay thế traces_repo.daily_dossier_counts_by_user_ids, có áp mốc đổi cách đếm.

    Hai nửa không bao giờ chồng ngày lên nhau (nửa cũ dừng trước 00:00 ngày 14/9, nửa mới bắt
    đầu từ đó) nhưng vẫn cộng theo khóa để an toàn nếu sau này mốc rơi vào giữa ngày.
    """
    counts: dict[tuple[str, str], int] = {}

    def absorb(rows: list[dict]) -> None:
        for row in rows:
            day = str(row.get("date") or "")
            if not day:
                continue
            key = (str(row.get("userId") or "—"), day)
            counts[key] = counts.get(key, 0) + int(row.get("count") or 0)

    if date_from < SUBMITTED_COUNT_FROM:
        absorb(await traces_repo.daily_dossier_counts_by_user_ids(
            user_ids=user_ids,
            date_from=date_from,
            date_to=min(date_to, SUBMITTED_COUNT_FROM),
            experience=experience,
        ))
    if date_to > SUBMITTED_COUNT_FROM:
        absorb(await dossiers_stats.submitted_daily_counts(
            user_ids=user_ids,
            date_from=max(date_from, SUBMITTED_COUNT_FROM),
            date_to=date_to,
            experience=experience,
        ))
    return [
        {"userId": user_id, "date": day, "count": count}
        for (user_id, day), count in sorted(counts.items())
    ]
