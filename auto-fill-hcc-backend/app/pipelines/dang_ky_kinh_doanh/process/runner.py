"""Compact agent pipeline for household business registration."""

import asyncio
import contextlib
import copy

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_kinh_doanh.process import mapper, ten_ho, vision
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
    # Điền đợt 2 (lớp soát chạy nền trong lúc extension đính kèm) cần OCR từng tài liệu, field TRƯỚC mapper và lượt đọc
    # ảnh — runner chung chỉ trả chuỗi OCR đã nối.
    page = opts.get("page") or opts.get("businessPage") or DEFAULT_PAGE
    all_pages = bool(opts.get("allPages")) or str(page).lower() in _ALL_PAGES
    read: dict | None = {} if opts.get("_secondPass") and all_pages else None
    if mapper.TO_KHAI_OPTION in opts:
        res = _from_to_khai(opts[mapper.TO_KHAI_OPTION])
        read = None  # tờ khai cán bộ nhập tay, không có giấy để soát
    else:
        res = await _from_files(files_by_role, read)
    compact = res["fields"]  # facts thô (LLM hoặc tờ khai) — dùng để map cho từng trang
    skip_start_date = bool(opts.get(mapper.SKIP_START_DATE_OPTION))  # server đặt theo tài khoản
    line_mode = str(opts.get(mapper.LINE_DETAIL_OPTION) or "")  # server đặt theo tài khoản

    # Chế độ FILL TẤT CẢ 8 trang trong 1 lần (extension tự lặp fill→lưu→sang trang).
    if all_pages:
        res["pages"] = mapper.enrich_all(compact, skip_start_date=skip_start_date, line_mode=line_mode)
        res["fields"] = res["pages"].get(DEFAULT_PAGE, [])
        if opts.get("returnFacts"):
            # Handfree (trợ lý hộ kinh doanh) cần facts thô để hỏi bổ sung mục thiếu rồi map lại; API core không gửi cờ này.
            res["facts"] = compact
        res.setdefault("extracted", {})["page"] = "__all__"
        if read and read.get("documents"):
            from ..thanh_tra import dot_hai

            raw_fields = copy.deepcopy(compact)

            def second(base_fields):
                return dot_hai.patch(read["documents"], raw_fields, opts, vision=read.get("vision"),
                                     skip_start_date=skip_start_date)

            # Đợt soát không được chạy (quá tải, lỗi ghi trạng thái) thì nơi gọi huỷ lượt đọc ảnh còn chạy dở.
            second.cancel = lambda: _cancel(read.get("vision"))
            # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
            res["_second_pass"] = second
        elif read:
            _cancel(read.get("vision"))
        return res

    res["fields"] = mapper.enrich(compact, page=page, skip_start_date=skip_start_date, line_mode=line_mode)
    res.setdefault("extracted", {})["page"] = page
    return res


def _cancel(task) -> None:
    if isinstance(task, asyncio.Future) and not task.done():
        task.cancel()


async def _from_files(files_by_role: dict[str, list[dict]], read: dict | None = None) -> dict:
    # Qwen đọc ảnh chạy SONG SONG với OCR + LLM: hồ sơ đọc hỏng không phải chờ thêm một lượt nối tiếp; hồ sơ đọc ổn
    # thì hủy lượt ảnh ngay khi biết, không chờ — trừ khi có đợt soát (``read`` khác None): lượt ảnh là nguồn đọc độc lập
    # của đợt soát, để chạy tiếp ở nền.
    vision_task = asyncio.create_task(vision.read_application(runner.flatten(files_by_role)))

    async def keep_documents(documents: list[dict], _opts: dict) -> str:
        read["documents"] = documents
        return ""

    try:
        res = await runner.run(
            files_by_role,
            fields=FIELDS,
            allowed=ALLOWED,
            comp_by_name=COMPACT_COMP_BY_NAME,
            aliases=ALIASES,
            extra_rules=EXTRA_RULES,
            context_builder=keep_documents if read is not None else None,
        )
    except BaseException:
        vision_task.cancel()
        raise
    compact = res["fields"]
    # Tên viết tay hay lệch dấu → hỏi riêng một lượt nhỏ, chạy song song phần còn lại.
    ten = next((f for f in compact if f.get("name") == "HoKinhDoanh_Ten" and f.get("value")), None)
    ten_task = asyncio.create_task(ten_ho.fix_diacritics(ten["value"])) if ten else None
    # Đơn bỏ trống tỉnh/xã của trụ sở / địa chỉ thuế → LLM hay lấy tỉnh/xã CCCD; đối chiếu lại với OCR.
    fixed = mapper.fix_addresses_from_ocr(compact, res.get("ocr_text") or "")
    if fixed:
        res.setdefault("extracted", {})["addressFixed"] = fixed
    # OCR đọc hỏng (số định danh/điện thoại sai độ dài, bảng ngành vỡ / mã cụt, mất vốn) → lấy kết quả Qwen đọc ảnh,
    # chỉ thay trường hỏng.
    broken = vision.broken_fields({f.get("name"): f.get("value") for f in compact}, res.get("ocr_text") or "")
    if not broken and read is not None:
        read["vision"] = vision_task
    elif not broken:
        vision_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await vision_task
    else:
        data = await vision_task
        if read is not None:
            read["vision"] = data
        if data:
            patched = vision.patch(compact, broken, data)
            res.setdefault("extracted", {})["visionPatched"] = patched
        if "ChuHo_SoDinhDanh" in broken:
            raw_id = next((f.get("value") for f in compact if f.get("name") == "ChuHo_SoDinhDanh"), None)
            if raw_id and len(vision._digits(raw_id)) != 12:
                res.setdefault("errors", []).append(
                    f"Số định danh chủ hộ đọc được '{raw_id}' không đủ 12 số — đối chiếu Giấy đề nghị.")
    if ten_task and (fixed_name := await ten_task):
        ten["value"] = fixed_name
        res.setdefault("extracted", {})["tenHoSuaDau"] = True
    return res
