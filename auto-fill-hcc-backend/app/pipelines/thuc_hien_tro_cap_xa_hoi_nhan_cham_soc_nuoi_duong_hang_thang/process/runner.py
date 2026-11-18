"""Compact agent process pipeline cho "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh
phí nhận chăm sóc, nuôi dưỡng hằng tháng"."""

import copy
import re

from app.pipelines._shared.area_remap import province_for_ward
from app.pipelines._shared.compact_agent import runner
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process import mapper
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.prompt import EXTRA_RULES
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _counter_context(options: dict) -> str:
    """Xã / phường của tài khoản quầy (nơi nhận hồ sơ) cho quy tắc địa chỉ "gần giống xã quầy thì lấy xã quầy"."""
    raw = re.sub(r"^\s*(hcc|tt\s*hcc|ubnd)\s+", "", str((options or {}).get("counterWard") or "").strip(), flags=re.I)
    hit = province_for_ward(re.split(r"\s*[-–,]\s*|\s+tỉnh\s+", raw)[0].strip()) if raw else None
    if not hit:
        return ""
    province, ward = hit
    return f"\n\n<xa_quay>\nXã / phường của tài khoản quầy đang nhận hồ sơ: {ward}, {province}.\n</xa_quay>"


_UNLOCK = ("data[fullname]", "data[identityNumber]")


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # LLM chỉ trích người khai thay + đối tượng + bên được ủy quyền từ giấy tờ; mốc tài khoản (formContext) chỉ dùng
    # ở mapper để chọn người nộp, không đưa vào prompt.
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}

    async def build_context(documents: list[dict], opts: dict) -> str:
        read["documents"] = documents
        return _counter_context(opts)

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=build_context,
    )
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    # Họ tên + CCCD Phần I cổng khoá (disabled) theo tài khoản VNeID, có khi để trống → luôn kèm enableInput để cán bộ
    # sửa / nhập được. Không có giá trị thì phát "dom-expect": extension chỉ bỏ khoá + tô đỏ ô trống, không ghi gì.
    present = set()
    for field in mapped_fields:
        if field.get("name") in _UNLOCK and field.get("occurrence") in (None, 0):
            field["enableInput"] = True
            present.add(field["name"])
    mapped_fields += [{"name": name, "comp": "dom-expect", "value": "", "enableInput": True}
                      for name in _UNLOCK if name not in present]
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    if raw_fields and read.get("documents"):
        from ..thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields, options)
    return res
