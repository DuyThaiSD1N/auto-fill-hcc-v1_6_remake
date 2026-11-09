"""Process pipeline cho "Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã
hội" (1.116907) — gọi lại pipeline 1.116908 (cùng form, cùng Tờ khai Mẫu số 04): người giám hộ (mục II) là người nộp,
đối tượng (mục I) là chủ hồ sơ, hỗ trợ cài đặt "Lấy người nộp theo tờ khai". Ghi chú chỉ ghi nhóm đọc được ở mục I.7
(required_group=None) + nơi ở hiện nay khi khác nơi cư trú."""

from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.prompt import MAU_04_RULES
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.runner import run_with

EXTRA_RULES = """Thủ tục: Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã hội
(theo Nghị định 335/2026/NĐ-CP). Đầu vào gồm: Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội (Mẫu số
04), CCCD/thẻ căn cước của đối tượng và/hoặc người giám hộ, có thể có Giấy xác nhận khuyết tật, Giấy khai sinh, giấy
tờ khác.

""" + MAU_04_RULES


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    return await run_with(files_by_role, options, extra_rules=EXTRA_RULES, required_group=None)
