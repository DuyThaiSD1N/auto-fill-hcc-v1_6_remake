"""Compact agent pipeline for household business registration."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_kinh_doanh.process import mapper, vision
from app.pipelines.dang_ky_kinh_doanh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_kinh_doanh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    DEFAULT_PAGE,
    FIELDS,
)


_ALL_PAGES = {"__all__", "all", "tat-ca"}


def _from_to_khai(form) -> dict:
    """Tờ khai cán bộ đã nhập trên tab của Auto Fill → facts, không OCR/LLM (tệp gửi kèm nếu có cũng không đọc)."""
    from pydantic import ValidationError

    from app.core.errors import AppError
    from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.fill import GiayDeNghi

    if not isinstance(form, dict):
        raise AppError("BAD_TO_KHAI", "Tờ khai đăng ký hộ kinh doanh gửi lên không đúng dạng", 400)
    try:
        data = GiayDeNghi.model_validate(form).model_dump()
    except ValidationError as exc:
        where = ".".join(str(part) for part in exc.errors()[0].get("loc") or ())
        raise AppError("BAD_TO_KHAI", f"Tờ khai đăng ký hộ kinh doanh có ô chưa đúng ({where})", 400) from exc
    return {
        "fields": mapper.facts_from_to_khai(data),
        "extracted": {"nguon": "to-khai"},
        "errors": [],
        "ocr_text": "",
        "stats": {"ocr_latency_ms": 0, "llm_latency_ms": 0},
    }


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    opts = options or {}
    if mapper.TO_KHAI_OPTION in opts:
        res = _from_to_khai(opts[mapper.TO_KHAI_OPTION])
    else:
        res = await _from_files(files_by_role)
    page = opts.get("page") or opts.get("businessPage") or DEFAULT_PAGE
    compact = res["fields"]  # facts thô (LLM hoặc tờ khai) — dùng để map cho từng trang
    skip_start_date = bool(opts.get(mapper.SKIP_START_DATE_OPTION))  # server đặt theo tài khoản

    # Chế độ FILL TẤT CẢ 8 trang trong 1 lần (extension tự lặp fill→lưu→sang trang).
    if opts.get("allPages") or str(page).lower() in _ALL_PAGES:
        res["pages"] = mapper.enrich_all(compact, skip_start_date=skip_start_date)
        res["fields"] = res["pages"].get(DEFAULT_PAGE, [])
        if opts.get("returnFacts"):
            # Handfree (trợ lý hộ kinh doanh) cần facts thô để hỏi bổ sung mục thiếu rồi map lại; API core không gửi cờ này.
            res["facts"] = compact
        res.setdefault("extracted", {})["page"] = "__all__"
        return res

    res["fields"] = mapper.enrich(compact, page=page, skip_start_date=skip_start_date)
    res.setdefault("extracted", {})["page"] = page
    return res


async def _from_files(files_by_role: dict[str, list[dict]]) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    compact = res["fields"]
    # OCR đọc hỏng (số định danh/điện thoại sai độ dài, bảng ngành vỡ, mất vốn) → Qwen đọc ảnh dự phòng, chỉ thay
    # trường hỏng. Hồ sơ đọc ổn không gọi thêm.
    broken = vision.broken_fields({f.get("name"): f.get("value") for f in compact}, res.get("ocr_text") or "")
    if broken:
        data = await vision.read_application(runner.flatten(files_by_role))
        if data:
            patched = vision.patch(compact, broken, data)
            res.setdefault("extracted", {})["visionPatched"] = patched
        if "ChuHo_SoDinhDanh" in broken:
            raw_id = next((f.get("value") for f in compact if f.get("name") == "ChuHo_SoDinhDanh"), None)
            if raw_id and len(vision._digits(raw_id)) != 12:
                res.setdefault("errors", []).append(
                    f"Số định danh chủ hộ đọc được '{raw_id}' không đủ 12 số — đối chiếu Giấy đề nghị.")
    return res
