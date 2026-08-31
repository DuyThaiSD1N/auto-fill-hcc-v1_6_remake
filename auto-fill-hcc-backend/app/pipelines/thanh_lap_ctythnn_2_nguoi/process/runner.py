"""Compact agent pipeline cho thu tuc thanh lap cong ty TNHH hai thanh vien tro len."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process import mapper
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.prompt import EXTRA_RULES
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    DEFAULT_PAGE,
    FIELDS,
)


_ALL_PAGES = {"__all__", "all", "tat-ca"}


# Trần token ĐẦU RA. Mặc định của shared runner là 1800 — ĐO THỰC TẾ trên hồ sơ mẫu (Thương Huyền
# Nhi, 5 file) thì không đủ: JSON bị cắt giữa chừng ở field áp chót, `json.loads` ném lỗi và MẤT
# SẠCH cả bộ field (không phải mất một field — cả lượt trích trả về rỗng). Loại hình này trả nhiều
# hơn CTCP: bảng ngành nghề (hồ sơ mẫu 11 dòng), mảng thành viên (mỗi người ~15 khoá) và đoạn
# "quyền hạn của người đại diện" trích nguyên văn từ Điều lệ.
#
# KHÔNG nâng cao hơn nữa được: model chính có ngữ cảnh 32.768 token, mà riêng input của hồ sơ mẫu
# (OCR 5 file ~94k ký tự + prompt) đã ăn gần hết. ĐO TRÊN CỔNG LLM THẬT với đúng hồ sơ đó:
#   5000 → HTTP 400 "maximum context length" → rơi sang fallback OpenAI
#   3500 → HTTP 400 → rơi sang fallback OpenAI
#   2500 → model chính nhận, JSON nén dài ~3.1k ký tự, parse đủ field
# Nên trần đặt 2500. Cặp đôi với quy tắc "JSON nén" ở prompt.py: chính nó cắt ~40% token đầu ra so
# với JSON thụt lề, đủ chỗ cho cả bảng ngành nghề 11 dòng + 2 thành viên + đoạn quyền hạn.
# Hồ sơ nhiều giấy hơn nữa mà vẫn 400 thì client tự rơi sang fallback OpenAI, không mất lượt.
_MAX_OUTPUT_TOKENS = 2500


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        max_tokens=_MAX_OUTPUT_TOKENS,
    )
    opts = options or {}
    page = opts.get("page") or opts.get("businessPage") or DEFAULT_PAGE
    compact = res["fields"]

    if opts.get("allPages") or str(page).lower() in _ALL_PAGES:
        res["pages"] = mapper.enrich_all(compact)
        res["fields"] = res["pages"].get(DEFAULT_PAGE, [])
        res.setdefault("extracted", {})["page"] = "__all__"
        return res

    res["fields"] = mapper.enrich(compact, page=page)
    res.setdefault("extracted", {})["page"] = page
    return res
