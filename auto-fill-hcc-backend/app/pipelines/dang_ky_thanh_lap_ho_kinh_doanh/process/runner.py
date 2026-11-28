"""Pipeline đăng ký thành lập hộ kinh doanh (1.001612, Cổng DVC quốc gia mới).

Đọc giấy như bản HkdOnline (OCR + LLM, Qwen đọc ảnh song song làm dự phòng cho trường OCR hỏng, sửa dấu tên hộ, sửa
tỉnh/xã trụ sở + địa chỉ thuế theo OCR) — chỉ GỌI các hàm của ``dang_ky_kinh_doanh``, không sửa luồng đó — rồi mapper
riêng phát bộ ô SurveyJS và chọn radio chủ hộ tự nộp / người được ủy quyền theo tài khoản.

Không cần quét tờ khai: cán bộ nhập Giấy đề nghị trên tab "Tạo tờ khai đăng ký hộ kinh doanh" (chọn người nộp trước) →
extension gửi ``options.giayDeNghi``, runner map thẳng ra dữ kiện, tệp (nếu có) chỉ còn để đính kèm.
"""

import asyncio
import contextlib

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_kinh_doanh.process import ten_ho, vision
from app.pipelines.dang_ky_kinh_doanh.process.mapper import fix_addresses_from_ocr

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALLOWED, COMPACT_COMP_BY_NAME, FIELDS, ToKhaiDvcqg


async def _read(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    vision_task = asyncio.create_task(vision.read_application(runner.flatten(files_by_role)))
    try:
        res = await runner.run(
            files_by_role,
            fields=FIELDS,
            allowed=ALLOWED,
            comp_by_name=COMPACT_COMP_BY_NAME,
            aliases={},
            extra_rules=EXTRA_RULES,
            options=options,
        )
    except BaseException:
        vision_task.cancel()
        raise
    compact = res["fields"]
    # Tên viết tay hay lệch dấu → hỏi riêng một lượt nhỏ, chạy song song phần còn lại.
    ten = next((f for f in compact if f.get("name") == "HoKinhDoanh_Ten" and f.get("value")), None)
    ten_task = asyncio.create_task(ten_ho.fix_diacritics(ten["value"])) if ten else None
    # Đơn bỏ trống tỉnh/xã trụ sở / địa chỉ thuế → LLM hay lấy tỉnh/xã CCCD; đối chiếu lại với OCR.
    fixed = fix_addresses_from_ocr(compact, res.get("ocr_text") or "")
    if fixed:
        res.setdefault("extracted", {})["addressFixed"] = fixed
    # OCR đọc hỏng (số định danh / điện thoại sai độ dài, bảng ngành vỡ, mất vốn) → lấy kết quả Qwen đọc ảnh cho riêng
    # trường hỏng; đọc ổn thì huỷ lượt ảnh.
    broken = vision.broken_fields({f.get("name"): f.get("value") for f in compact}, res.get("ocr_text") or "")
    if not broken:
        vision_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await vision_task
    else:
        data = await vision_task
        if data:
            res.setdefault("extracted", {})["visionPatched"] = vision.patch(compact, broken, data)
    if ten_task and (fixed_name := await ten_task):
        ten["value"] = fixed_name
        res.setdefault("extracted", {})["tenHoSuaDau"] = True
    return res


def _from_to_khai(form) -> dict:
    """Tờ khai cán bộ nhập trên tab của Auto Fill → dữ kiện, không OCR/LLM (tệp gửi kèm nếu có cũng không đọc).
    Thiếu lựa chọn người nộp / ô sai dạng → 400: tab bắt chọn người nộp trước khi lưu nên không gặp ở luồng thường."""
    from pydantic import ValidationError

    from app.core.errors import AppError

    if not isinstance(form, dict):
        raise AppError("BAD_TO_KHAI", "Tờ khai đăng ký hộ kinh doanh gửi lên không đúng dạng", 400)
    try:
        data = ToKhaiDvcqg.model_validate(form).model_dump()
    except ValidationError as exc:
        where = ".".join(str(part) for part in exc.errors()[0].get("loc") or ())
        if where.startswith("nguoiNop"):
            raise AppError("BAD_TO_KHAI", "Tờ khai chưa chọn người nộp hồ sơ trên cổng (chủ hộ hay người được ủy "
                                          "quyền) — mở lại tờ khai, chọn rồi bấm Lưu", 400) from exc
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
        result = _from_to_khai(opts[mapper.TO_KHAI_OPTION])
    else:
        result = await _read(files_by_role, opts)
    result["fields"], warnings = mapper.enrich(result["fields"], {**opts, "_ocr_text": result.get("ocr_text") or ""})
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
