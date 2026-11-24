"""Điền đợt 2 của hộ kinh doanh: soát lại lượt trích rồi tính lại các trang (8 trang HkdOnline) có ô đổi.

Khác các thủ tục khác (vá ô trên form đã điền): extension đính kèm hồ sơ TRƯỚC, trong lúc đó lớp soát chạy; đính xong mới
điền 8 trang nên kết quả là NGUYÊN danh sách ô của từng trang có đổi (mỗi ô kèm "page"), extension dùng thay trang đó."""

import asyncio

from ..process import mapper
from . import review


def _fields(values: dict) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


async def patch(documents: list[dict], raw_fields: list[dict], options: dict, *, vision=None,
                skip_start_date: bool = False) -> dict:
    """``raw_fields``: field lượt trích trước mapper (đúng thứ lượt đầu đưa vào mapper.enrich_all); ``vision``: kết quả
    hoặc tác vụ lượt đọc ảnh giấy đề nghị."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    try:
        verdict = await review(documents, values, {**(options or {}), "_vision": vision})
    finally:
        # Thanh tra chỉ chờ lượt đọc ảnh có hạn; xong đợt soát thì không ai cần nó nữa.
        if isinstance(vision, asyncio.Future) and not vision.done():
            vision.cancel()
    before = mapper.enrich_all(_fields(values), skip_start_date=skip_start_date)
    after = mapper.enrich_all(_fields(verdict.values), skip_start_date=skip_start_date)
    fields = [{**field, "page": page} for page, items in after.items() if items != before.get(page) for field in items]
    # "facts": field sau phán quyết (trước mapper) — handfree hỏi bổ sung mục thiếu rồi map lại từ đây.
    return {"fields": fields, "rulings": verdict.rulings, "timing": verdict.timing, "facts": _fields(verdict.values)}
