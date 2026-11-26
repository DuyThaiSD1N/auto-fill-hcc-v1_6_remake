"""Process pipeline cho [Lào Cai - cổng iGate mới] giao đất ở không đấu giá (1.115684)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
