"""Process pipeline cho [Lào Cai - cổng iGate mới] đăng ký biến động quyền sử dụng đất (1.115668)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_dat_dai_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
