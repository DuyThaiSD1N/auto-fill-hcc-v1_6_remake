"""Process pipeline cho [Lào Cai - cổng iGate mới] sử dụng đất kết hợp đa mục đích (1.115682)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
