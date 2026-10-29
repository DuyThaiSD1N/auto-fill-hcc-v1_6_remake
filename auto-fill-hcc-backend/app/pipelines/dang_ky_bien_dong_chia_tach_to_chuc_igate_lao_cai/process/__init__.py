"""Process pipeline cho [Lào Cai - cổng iGate mới] đăng ký biến động do chia, tách, hợp nhất, sáp nhập tổ chức (1.115670)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
