"""Đính kèm bước 2 "Thành phần hồ sơ" cho thủ tục "Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn
vào cơ sở trợ giúp xã hội" (1.116907, cổng Bộ Y tế — Angular table, engine FE `attp-row`).

Bảng CHỈ MỘT dòng "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội (theo Mẫu số 04 ...)". Dùng lại
planner 1.116908 với bien_ban_row=False: tờ khai vào dòng đó (nhiều trang/nhiều ảnh cùng dòng; tệp scan chung với
biên bản vẫn đính); biên bản, CCCD và giấy tờ khác KHÔNG có dòng → không đính, chỉ dùng để điền bước 1.
"""

from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.attach.planner import (
    plan_documents,
)
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.attach.prompt import (
    build_system_prompt,
)
from app.process.schemas import FileItem

SYSTEM_PROMPT = build_system_prompt(
    "Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã hội"
)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    return await plan_documents(files, bien_ban_row=False, system_prompt=SYSTEM_PROMPT)
