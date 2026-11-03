"""Pipeline cấp bản sao trích lục hộ tịch (Cổng DVC quốc gia mới): phân vai → trích → mapper.

Thiếu ngày đăng ký sau lượt trích → Qwen nhìn thẳng ảnh đọc riêng ngày đó: OCR văn bản hay rơi mất dòng viết tay
"<nơi>, ngày ... tháng ... năm ..." trên khối ký tên của giấy hộ tịch mẫu cũ (giấy chứng nhận kết hôn, khai sinh).
"""

import asyncio
import base64
import logging
import re
from contextlib import ExitStack
from datetime import date

from app.monitor import recorder as mon
from app.pipelines._shared.compact_agent import runner
from app.services import ocr_qwen
from app.services.llm.client import extract_json_block
from app.services.ocr_tiengnoi import _open_input

from . import mapper, reason
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

logger = logging.getLogger(__name__)

# Giấy hộ tịch nằm ở mấy trang đầu hồ sơ; chặn trần để hồ sơ dài không vượt context model.
_VISION_MAX_PAGES = 6
_VISION_MAX_TOKENS = 200
_VISION_TIMEOUT_S = 90
# Field cho biết lượt trích đã thấy giấy hộ tịch / mục "Đã đăng ký tại" → đáng đọc thêm ngày đăng ký.
_REGISTRATION_HINT_KEYS = ("GiayTo_TenGiayTo", "GiayTo_CoQuanDangKy", "GiayTo_So", "GiayTo_QuyenSo")

REGISTRATION_DATE_PROMPT = """Ảnh là các trang hồ sơ xin bản sao trích lục hộ tịch. Tìm GIẤY HỘ TỊCH đã đăng ký trước đây (%DOC%) của %NAME%
— giấy khai sinh, giấy chứng nhận kết hôn, trích lục...; KHÔNG phải tờ khai, CCCD/CMND, giấy ủy quyền, trang chứng thực.
Đọc NGÀY ĐĂNG KÝ của giấy đó: nhãn "Ngày, tháng, năm đăng ký" / "Ngày đăng ký"; giấy không có nhãn này thì là ngày ở dòng
"<nơi>, ngày ... tháng ... năm ..." ngay trên khối ký tên "T/M ỦY BAN NHÂN DÂN" / "TM. UBND".
KHÔNG lấy ngày sinh, ngày cấp CMND/CCCD, ngày chứng thực. Không thấy giấy, hoặc thiếu ngày/tháng/năm → "".
Trả DUY NHẤT JSON {"ngay_dang_ky": "dd/mm/yyyy"}."""


def _page_images(files: list[dict]) -> list[bytes]:
    images: list[bytes] = []
    for f in files:
        if runner._is_docx(f):
            continue
        with ExitStack() as stack:
            _, src, mime = _open_input(f, stack)
            raw = src if isinstance(src, bytes) else src.read()
        images.extend(ocr_qwen._page_images(raw, str(mime or "").lower()))
        if len(images) >= _VISION_MAX_PAGES:
            return images[:_VISION_MAX_PAGES]
    return images


def _parse_date(value) -> date | None:
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(value or "").strip())
    if not match:
        return None
    try:
        return date(int(match[3]), int(match[2]), int(match[1]))
    except ValueError:
        return None


def plausible_registration_date(value, values: dict) -> str:
    """Ngày model đọc ra → "dd/mm/yyyy" khi hợp lý: có thật, không ở tương lai, không trước ngày sinh và không
    trùng ngày sinh / ngày cấp thẻ của người được cấp (hai ngày dễ vớ nhầm nhất trên cùng trang)."""
    registered = _parse_date(value)
    if not registered or registered > date.today():
        return ""
    birth = _parse_date(values.get("NguoiDuocCap_NgaySinh"))
    if birth and registered < birth:
        return ""
    if registered in {birth, _parse_date(values.get("NguoiDuocCap_NgayCap"))}:
        return ""
    return registered.strftime("%d/%m/%Y")


async def read_registration_date(files: list[dict], values: dict) -> str:
    try:
        async with mon.span("llm.vision_ngay_dang_ky") as span:
            images = await asyncio.to_thread(_page_images, files)
            if not images:
                return ""
            span.attrs["pages"] = len(images)
            prompt = (REGISTRATION_DATE_PROMPT
                      .replace("%DOC%", str(values.get("GiayTo_TenGiayTo") or "loại ghi trong hồ sơ"))
                      .replace("%NAME%", str(values.get("NguoiDuocCap_HoTen") or "người được cấp")))
            content = [{"type": "text", "text": prompt}] + [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}}
                for b in images
            ]
            res = await ocr_qwen.chat([{"role": "user", "content": content}], max_tokens=_VISION_MAX_TOKENS,
                                      timeout_s=_VISION_TIMEOUT_S, ocr_server=True)
            span.attrs["usage"] = res.get("usage")
            data = extract_json_block(res.get("content") or "") or {}
            mon.output("vision_ngay_dang_ky", data)
            return plausible_registration_date(data.get("ngay_dang_ky") if isinstance(data, dict) else "", values)
    except Exception as exc:  # noqa: BLE001 — lỗi lượt phụ không được làm hỏng luồng chính
        logger.warning("Qwen đọc ngày đăng ký trích lục lỗi, giữ kết quả OCR + LLM: %s", exc)
        return ""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=reason.build_context,
    )
    values = {f.get("name"): f.get("value") for f in result.get("fields") or [] if isinstance(f, dict)}
    if not values.get("GiayTo_NgayDangKy") and any(values.get(k) for k in _REGISTRATION_HINT_KEYS):
        registered = await read_registration_date(runner.flatten(files_by_role), values)
        if registered:
            result["fields"] = [f for f in result.get("fields") or [] if f.get("name") != "GiayTo_NgayDangKy"]
            result["fields"].append({"name": "GiayTo_NgayDangKy", "comp": COMPACT_COMP_BY_NAME["GiayTo_NgayDangKy"],
                                     "value": registered})
            result.setdefault("extracted", {})["visionPatched"] = ["GiayTo_NgayDangKy"]
    enrich_options = {**(options or {}), "_reasoning_context": result.get("reasoning_context") or "",
                      "_ocr_text": result.get("ocr_text") or ""}
    result["fields"], warnings = mapper.enrich(result["fields"], enrich_options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
