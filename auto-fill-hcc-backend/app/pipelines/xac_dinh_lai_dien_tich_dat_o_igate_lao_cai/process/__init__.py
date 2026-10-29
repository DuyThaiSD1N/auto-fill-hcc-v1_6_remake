"""Process pipeline cho [Lào Cai - cổng iGate mới] xác định lại diện tích đất ở (1.115685)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.xac_dinh_lai_dien_tich_dat_o_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
