"""Compact agent process pipeline cho "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào"."""

import asyncio
import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process import mapper, vision
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process.prompt import EXTRA_RULES
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _set(fields: list[dict], name: str, value) -> None:
    field = next((f for f in fields if f.get("name") == name), None)
    if field:
        field["value"] = value
    else:
        fields.append({"name": name, "comp": "raw", "value": value})


def _apply_vision(fields: list[dict], parsed: dict) -> list[str]:
    """Kết quả Qwen đọc ảnh ưu tiên hơn LLM đọc OCR văn bản ở các phần viết tay / chữ in trên nền hoa văn."""
    by_name = {f.get("name"): f.get("value") for f in fields}
    cars, warnings = vision.merge_vehicles(by_name.get("DeNghi_PhuongTien"), parsed)
    if cars:
        _set(fields, "DeNghi_PhuongTien", cars)
    area = dict(parsed.get("area") or {})
    if area.get("xa"):
        # Ô phường/xã khớp option theo chuỗi con; "P. X" không phải chuỗi con của "Phường X".
        area["xa"] = re.sub(r"^\s*P\.\s*", "Phường ", re.sub(r"^\s*X\.\s*", "Xã ", area["xa"]))
        llm_area = by_name.get("NguoiNop_ThuongTru")
        _set(fields, "NguoiNop_ThuongTru", {**(llm_area if isinstance(llm_area, dict) else {}), **area})
    phone = parsed.get("phone") or ""
    if 9 <= len(phone) <= 11:
        llm_phone = re.sub(r"\D", "", str(by_name.get("NguoiNop_DienThoai") or ""))
        if llm_phone and llm_phone != phone:
            # Hai lượt đọc chữ viết tay ra hai số khác nhau → không chắc số nào đúng.
            warnings.append(f"Số điện thoại viết tay khó đọc (đọc được {phone} và {llm_phone}) — đối chiếu Giấy đề nghị.")
        _set(fields, "NguoiNop_DienThoai", phone)
    return warnings


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Giấy đề nghị viết tay + giấy xe đọc thẳng từ ảnh song song với OCR + LLM; luôn chờ cả hai xong.
    res, parsed = await asyncio.gather(runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
    ), vision.read_application(runner.flatten(files_by_role)))
    vision_warnings = _apply_vision(res["fields"], parsed) if parsed else []
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    warnings = vision_warnings + warnings
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
